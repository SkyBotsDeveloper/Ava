from __future__ import annotations

from pathlib import Path

from ava.app.controller import AvaController
from ava.app.state import AssistantState
from ava.automation.browser import BrowserController
from ava.automation.executor import ActionExecutor
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
        return True


def _build_controller(tmp_path: Path) -> AvaController:
    settings = Settings(_env_file=None)
    state = AssistantState()
    engine = build_engine(tmp_path / "ava.db")
    initialize_database(engine)
    journal = ActionJournalStore(build_session_factory(engine))
    window_controller = FakeWindowController(tmp_path)
    browser_controller = BrowserController(settings, window_controller=window_controller)
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
