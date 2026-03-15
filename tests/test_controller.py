from __future__ import annotations

from pathlib import Path

from ava.app.controller import AvaController
from ava.app.state import AssistantState
from ava.automation.browser import BrowserController
from ava.automation.executor import ActionExecutor
from ava.automation.sacrificial_browser import BrowserPageState, PageSearchResult, PlaybackResult
from ava.automation.windows import WindowController
from ava.config.settings import Settings
from ava.intents.router import IntentRouter
from ava.memory.bootstrap import initialize_database
from ava.memory.database import build_engine, build_session_factory
from ava.memory.journal import ActionJournalStore
from ava.safety.policy import SafetyPolicy


class FakeWindowController(WindowController):
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.opened_apps: list[str] = []
        self.closed_apps: list[str] = []
        self.closed_tabs = 0
        self.opened_folders: list[str] = []
        self.live_browser_title = "Example"
        self.live_browser_url = "https://example.com"

    def launch_app(self, app_name: str):  # type: ignore[override]
        self.opened_apps.append(app_name)
        return None

    def close_app(self, app_name: str) -> int:  # type: ignore[override]
        self.closed_apps.append(app_name)
        return 1

    def create_folder(self, folder_name: str, *, base_dir: Path | None = None) -> Path:  # type: ignore[override]
        return super().create_folder(folder_name, base_dir=self.base_dir)

    def create_file(self, file_name: str, *, base_dir: Path | None = None) -> Path:  # type: ignore[override]
        return super().create_file(file_name, base_dir=self.base_dir)

    def open_folder(self, target_name: str) -> Path:  # type: ignore[override]
        self.opened_folders.append(target_name)
        target = self.base_dir / target_name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def rename_path(self, source_name: str, new_name: str) -> Path:  # type: ignore[override]
        source = self.base_dir / source_name
        target = source.with_name(new_name)
        source.rename(target)
        return target

    def move_path(self, source_name: str, destination_name: str) -> Path:  # type: ignore[override]
        source = self.base_dir / source_name
        destination = self.base_dir / destination_name
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / source.name
        source.rename(target)
        return target

    def close_active_tab(self, process_names: tuple[str, ...]) -> bool:  # type: ignore[override]
        self.closed_tabs += 1
        return True

    def open_url_in_active_browser(self, process_names: tuple[str, ...], url: str) -> bool:  # type: ignore[override]
        self.live_browser_title = url
        self.live_browser_url = url
        return True

    def focus_address_bar_in_browser(self, process_names: tuple[str, ...]) -> bool:  # type: ignore[override]
        return True

    def open_new_tab_in_browser(  # type: ignore[override]
        self,
        process_names: tuple[str, ...],
        url: str = "about:blank",
    ) -> bool:
        self.live_browser_title = url
        self.live_browser_url = url
        return True

    def switch_browser_tab(  # type: ignore[override]
        self,
        process_names: tuple[str, ...],
        *,
        direction: str = "next",
    ) -> bool:
        return True

    def search_on_page_in_browser(self, process_names: tuple[str, ...], query: str) -> bool:  # type: ignore[override]
        return True

    def current_browser_title_and_url(  # type: ignore[override]
        self,
        process_names: tuple[str, ...],
    ) -> tuple[str, str] | None:
        return self.live_browser_title, self.live_browser_url


class FakeSacrificialBrowserController:
    def __init__(self) -> None:
        self.current_page = BrowserPageState(
            title="about:blank",
            url="about:blank",
            tab_count=1,
            active_tab_index=0,
            browser_name="edge",
            isolated=True,
        )

    def open_website(self, url: str, *, confirmed: bool = False) -> BrowserPageState:
        self.current_page = BrowserPageState(
            title=url,
            url=url,
            tab_count=self.current_page.tab_count,
            active_tab_index=self.current_page.active_tab_index,
            browser_name="edge",
            isolated=True,
        )
        return self.current_page

    def open_new_tab(self, url: str = "about:blank") -> BrowserPageState:
        self.current_page = BrowserPageState(
            title=url,
            url=url,
            tab_count=self.current_page.tab_count + 1,
            active_tab_index=self.current_page.tab_count,
            browser_name="edge",
            isolated=True,
        )
        return self.current_page

    def close_current_tab(self, *, confirmed: bool = False) -> BrowserPageState:
        if not confirmed:
            raise PermissionError("confirm chahiye")
        remaining_tabs = max(1, self.current_page.tab_count - 1)
        active_index = max(0, remaining_tabs - 1)
        self.current_page = BrowserPageState(
            title="remaining",
            url="https://remaining.example",
            tab_count=remaining_tabs,
            active_tab_index=active_index,
            browser_name="edge",
            isolated=True,
        )
        return self.current_page

    def focus_address_bar(self) -> BrowserPageState:
        return self.current_page

    def switch_tab(self, *, direction: str = "next") -> BrowserPageState:
        return self.current_page

    def search_on_page(self, query: str) -> PageSearchResult:
        return PageSearchResult(query=query, match_count=3, page=self.current_page)

    def current_page_state(self) -> BrowserPageState:
        return self.current_page

    def open_youtube(self) -> BrowserPageState:
        self.current_page = BrowserPageState(
            title="YouTube",
            url="https://www.youtube.com",
            tab_count=1,
            active_tab_index=0,
            browser_name="edge",
            isolated=True,
        )
        return self.current_page

    def search_youtube(self, search_query: str) -> BrowserPageState:
        self.current_page = BrowserPageState(
            title="YouTube results",
            url=f"https://www.youtube.com/results?search_query={search_query}",
            tab_count=1,
            active_tab_index=0,
            browser_name="edge",
            isolated=True,
        )
        return self.current_page

    def search_and_play_youtube_playlist(self, search_query: str) -> PlaybackResult:
        self.current_page = BrowserPageState(
            title="YouTube",
            url="https://www.youtube.com/watch?v=test",
            tab_count=1,
            active_tab_index=0,
            browser_name="edge",
            isolated=True,
        )
        return PlaybackResult(search_query=search_query, playing=True, page=self.current_page)

    def open_instagram_login(self, *, confirmed: bool = False) -> BrowserPageState:
        if not confirmed:
            raise PermissionError("confirm chahiye")
        self.current_page = BrowserPageState(
            title="Instagram",
            url="https://www.instagram.com/accounts/login/",
            tab_count=1,
            active_tab_index=0,
            browser_name="edge",
            isolated=True,
        )
        return self.current_page

    def open_whatsapp_web(self, *, confirmed: bool = False) -> BrowserPageState:
        if not confirmed:
            raise PermissionError("confirm chahiye")
        self.current_page = BrowserPageState(
            title="WhatsApp Web",
            url="https://web.whatsapp.com/",
            tab_count=1,
            active_tab_index=0,
            browser_name="edge",
            isolated=True,
        )
        return self.current_page


def _build_controller(
    tmp_path: Path,
    *,
    browser_command_mode: str = "live",
    sacrificial_controller: FakeSacrificialBrowserController | None = None,
) -> AvaController:
    settings = Settings(_env_file=None, browser_command_mode=browser_command_mode)
    state = AssistantState()
    engine = build_engine(tmp_path / "ava.db")
    initialize_database(engine)
    journal = ActionJournalStore(build_session_factory(engine))
    window_controller = FakeWindowController(tmp_path)
    browser_controller = BrowserController(
        settings,
        window_controller=window_controller,
        sacrificial_controller=sacrificial_controller,
    )
    executor = ActionExecutor(
        browser_controller=browser_controller,
        window_controller=window_controller,
    )
    return AvaController(
        settings=settings,
        state=state,
        intent_router=IntentRouter(),
        safety_policy=SafetyPolicy(),
        journal=journal,
        executor=executor,
    )


def test_controller_creates_folder(tmp_path: Path) -> None:
    controller = _build_controller(tmp_path)

    result = controller.handle_text_command('Ava, "phase4-notes" folder banao')

    assert result.response_text == "Folder bana diya: phase4-notes"
    assert (tmp_path / "phase4-notes").exists()


def test_controller_requires_confirmation_for_sensitive_command(tmp_path: Path) -> None:
    controller = _build_controller(tmp_path)

    first = controller.handle_text_command("https://example.com login open karo")
    second = controller.handle_text_command("haan")

    assert first.confirmation_required is True
    assert "confirm" in first.response_text.lower()
    assert second.response_text == "https://example.com khol diya."


def test_controller_requires_confirmation_for_move(tmp_path: Path) -> None:
    controller = _build_controller(tmp_path)
    (tmp_path / "source-folder").mkdir()

    first = controller.handle_text_command('"source-folder" ko "dest-folder" move karo')
    second = controller.handle_text_command("haan")

    assert first.confirmation_required is True
    assert "confirm" in first.response_text.lower()
    assert second.response_text == "Move kar diya: source-folder"
    assert (tmp_path / "dest-folder" / "source-folder").exists()


def test_controller_routes_browser_commands_into_isolated_session(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )

    open_result = controller.handle_text_command("YouTube kholo")
    search_result = controller.handle_text_command('Is page par "YouTube" search karo')

    assert open_result.response_text == "YouTube khol diya."
    assert search_result.response_text == "Current page par `YouTube` search kar diya."


def test_controller_routes_youtube_search_into_isolated_session(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )

    result = controller.handle_text_command("YouTube par lofi hip hop playlist search karo")

    assert result.response_text == "YouTube par `lofi hip hop playlist` search kar diya."


def test_controller_retries_youtube_search_from_sticky_browser_context(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )

    controller.handle_text_command("YouTube par lofi hip hop playlist search karo")
    result = controller.handle_text_command("dobara search karo", source="voice")

    assert result.response_text == "YouTube par `lofi hip hop playlist` search kar diya."
    assert controller.state.active_browser_task is not None
    assert controller.state.active_browser_task.query == "lofi hip hop playlist"
    assert fake_sacrificial.current_page.url.endswith("search_query=lofi+hip+hop+playlist")


def test_controller_recovers_search_nahi_hui_from_sticky_browser_context(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )

    controller.handle_text_command("YouTube par lofi hip hop playlist search karo")
    result = controller.handle_text_command(
        "YouTube khul gaya but search nahi hui",
        source="voice",
    )

    assert result.response_text == "YouTube par `lofi hip hop playlist` search kar diya."


def test_controller_recovers_bare_search_from_sticky_browser_context(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )

    controller.handle_text_command("YouTube par lofi hip hop playlist search karo")
    result = controller.handle_text_command("search", source="voice")

    assert result.response_text == "YouTube par `lofi hip hop playlist` search kar diya."


def test_controller_overrides_malformed_youtube_retry_phrase_with_context(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )

    controller.handle_text_command("YouTube par lofi hip hop playlist search karo")
    result = controller.handle_text_command(
        "YouTube khul gaya but woh hip hop playlist search nahi hui karo",
        source="voice",
    )

    assert result.response_text == "YouTube par `lofi hip hop playlist` search kar diya."


def test_controller_requires_confirmation_for_close_tab_in_isolated_mode(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )
    controller.handle_text_command("new tab kholo")

    first = controller.handle_text_command("current tab band karo")
    second = controller.handle_text_command("haan")

    assert first.confirmation_required is True
    assert "confirm" in first.response_text.lower()
    assert second.response_text == "Current browser tab band kar diya."


def test_controller_requires_confirmation_for_instagram_login(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )

    first = controller.handle_text_command("Instagram login page kholo")
    second = controller.handle_text_command("haan")

    assert first.confirmation_required is True
    assert "confirm" in first.response_text.lower()
    assert second.response_text == "Instagram login page khol diya."


def test_controller_requires_confirmation_for_whatsapp_web(tmp_path: Path) -> None:
    fake_sacrificial = FakeSacrificialBrowserController()
    controller = _build_controller(
        tmp_path,
        browser_command_mode="isolated",
        sacrificial_controller=fake_sacrificial,
    )

    first = controller.handle_text_command("WhatsApp Web kholo")
    second = controller.handle_text_command("haan")

    assert first.confirmation_required is True
    assert "confirm" in first.response_text.lower()
    assert second.response_text == "WhatsApp Web khol diya."
