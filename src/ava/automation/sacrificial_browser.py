from __future__ import annotations

import json
import logging
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import urlopen

from ava.automation.models import AutomationStrategy
from ava.automation.windows import browser_executable
from ava.config.settings import Settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - optional dependency
    PlaywrightError = RuntimeError
    sync_playwright = None

_SENSITIVE_HOSTS = {"web.whatsapp.com"}
_SENSITIVE_LOGIN_HOSTS = {"instagram.com", "www.instagram.com"}


@dataclass(slots=True, frozen=True)
class IsolatedBrowserSessionInfo:
    browser_name: str
    executable_path: Path
    user_data_dir: Path
    remote_debugging_port: int
    strategy: AutomationStrategy = AutomationStrategy.DOM_AUTOMATION


@dataclass(slots=True, frozen=True)
class BrowserPageState:
    title: str
    url: str
    tab_count: int
    active_tab_index: int
    browser_name: str
    isolated: bool = True

    def as_dict(self) -> dict[str, str | int | bool]:
        return {
            "title": self.title,
            "url": self.url,
            "tab_count": self.tab_count,
            "active_tab_index": self.active_tab_index,
            "browser_name": self.browser_name,
            "isolated": self.isolated,
        }


@dataclass(slots=True, frozen=True)
class PageSearchResult:
    query: str
    match_count: int
    page: BrowserPageState

    def as_dict(self) -> dict[str, str | int | bool]:
        return {"query": self.query, "match_count": self.match_count, **self.page.as_dict()}


@dataclass(slots=True, frozen=True)
class PlaybackResult:
    search_query: str
    playing: bool
    page: BrowserPageState
    selected_href: str | None = None

    def as_dict(self) -> dict[str, str | int | bool]:
        payload = {
            "search_query": self.search_query,
            "playing": self.playing,
            **self.page.as_dict(),
        }
        if self.selected_href is not None:
            payload["selected_href"] = self.selected_href
        return payload


def normalize_browser_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        raise ValueError("Browser URL khaali nahi ho sakti.")
    parsed = urlparse(candidate)
    if parsed.scheme:
        return candidate
    if candidate.startswith("www."):
        return f"https://{candidate}"
    if "." in candidate.split("/")[0]:
        return f"https://{candidate}"
    return candidate


def requires_browser_confirmation(*, action_name: str, url: str | None = None) -> bool:
    if action_name == "close_current_tab":
        return True
    if url is None:
        return False
    parsed = urlparse(normalize_browser_url(url))
    host = parsed.netloc.lower()
    if host in _SENSITIVE_HOSTS:
        return True
    if host in _SENSITIVE_LOGIN_HOSTS and "login" in parsed.path.lower():
        return True
    return False


def choose_isolated_browser(preferred_browser: str) -> str:
    candidates = [preferred_browser, "edge", "chrome"]
    seen: set[str] = set()
    for browser_name in candidates:
        if browser_name in seen:
            continue
        seen.add(browser_name)
        try:
            browser_executable(browser_name)
            return browser_name
        except FileNotFoundError:
            continue
    raise FileNotFoundError("Na Edge mila, na Chrome. Isolated browser launch nahi ho sakta.")


def next_tab_index(current_index: int, tab_count: int, direction: str) -> int:
    if tab_count <= 0:
        raise ValueError("Tab count zero nahi ho sakta.")
    if direction not in {"next", "previous"}:
        raise ValueError("Direction `next` ya `previous` honi chahiye.")
    step = 1 if direction == "next" else -1
    return (current_index + step) % tab_count


class SacrificialBrowserController:
    def __init__(
        self,
        settings: Settings,
        *,
        browser_name: str | None = None,
        temp_root: Path | None = None,
    ) -> None:
        self.settings = settings
        self.browser_name = browser_name
        self.temp_root = temp_root
        self._session: IsolatedBrowserSessionInfo | None = None
        self._process: subprocess.Popen[str] | None = None
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._page: Any = None

    def __enter__(self) -> SacrificialBrowserController:
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.stop()

    @property
    def session_info(self) -> IsolatedBrowserSessionInfo:
        if self._session is None:
            raise RuntimeError("Isolated browser session abhi start nahi hui.")
        return self._session

    def start(self, url: str = "about:blank") -> IsolatedBrowserSessionInfo:
        if self._session is not None:
            return self._session
        if sync_playwright is None:
            raise RuntimeError("Playwright install nahi hai. `pip install playwright` chahiye.")

        browser_name = choose_isolated_browser(self.browser_name or self.settings.preferred_browser)
        executable = browser_executable(browser_name)
        remote_port = self._reserve_port()
        user_data_dir = Path(
            tempfile.mkdtemp(
                prefix=f"ava-{browser_name}-isolated-",
                dir=str(self.temp_root) if self.temp_root else None,
            )
        )
        launch_url = normalize_browser_url(url)
        args = [
            str(executable),
            f"--remote-debugging-port={remote_port}",
            f"--user-data-dir={user_data_dir}",
            "--new-window",
            "--no-first-run",
            "--no-default-browser-check",
            launch_url,
        ]
        self._process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        endpoint = self._wait_for_cdp_endpoint(remote_port)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.connect_over_cdp(endpoint)
        if not self._browser.contexts:
            raise RuntimeError("Browser CDP context create nahi hua.")
        self._context = self._browser.contexts[0]
        self._page = self._stabilize_session(launch_url)
        self._session = IsolatedBrowserSessionInfo(
            browser_name=browser_name,
            executable_path=executable,
            user_data_dir=user_data_dir,
            remote_debugging_port=remote_port,
        )
        logger.info(
            "Started isolated browser session",
            extra={
                "event": "isolated_browser_started",
                "browser_name": browser_name,
                "user_data_dir": str(user_data_dir),
                "remote_debugging_port": remote_port,
            },
        )
        return self._session

    def stop(self) -> None:
        user_data_dir = self._session.user_data_dir if self._session is not None else None
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
        self._process = None
        self._session = None
        if user_data_dir is not None:
            shutil.rmtree(user_data_dir, ignore_errors=True)

    def open_website(self, url: str, *, confirmed: bool = False) -> BrowserPageState:
        target = normalize_browser_url(url)
        if requires_browser_confirmation(action_name="open_url", url=target) and not confirmed:
            raise PermissionError("Is browser action ke liye confirmation chahiye.")
        page = self._active_page()
        page.goto(target, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        self._page = page
        logger.info(
            "Opened website in isolated browser",
            extra={"event": "isolated_browser_opened_url", "url": target},
        )
        return self.current_page_state()

    def focus_address_bar(self) -> BrowserPageState:
        page = self._active_page()
        page.bring_to_front()
        page.keyboard.press("Control+L")
        logger.info("Focused address bar", extra={"event": "isolated_browser_address_bar_focused"})
        return self.current_page_state()

    def navigate_to_url(self, url: str, *, confirmed: bool = False) -> BrowserPageState:
        target = normalize_browser_url(url)
        if requires_browser_confirmation(action_name="navigate", url=target) and not confirmed:
            raise PermissionError("Is browser navigation ke liye confirmation chahiye.")
        page = self._active_page()
        page.bring_to_front()
        page.keyboard.press("Control+L")
        page.keyboard.type(target, delay=20)
        page.keyboard.press("Enter")
        try:
            page.wait_for_url(f"**{urlparse(target).netloc}**", timeout=20_000)
        except PlaywrightError:
            page.goto(target, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        self._page = page
        logger.info(
            "Navigated isolated browser URL",
            extra={"event": "isolated_browser_navigated", "url": target},
        )
        return self.current_page_state()

    def open_new_tab(self, url: str = "about:blank") -> BrowserPageState:
        target = normalize_browser_url(url)
        page = self._context.new_page()
        page.goto(target, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        page.bring_to_front()
        self._page = page
        logger.info(
            "Opened isolated browser tab",
            extra={"event": "isolated_browser_tab_opened", "url": target},
        )
        return self.current_page_state()

    def close_current_tab(self, *, confirmed: bool = False) -> BrowserPageState:
        if not confirmed:
            raise PermissionError("Current tab band karne se pehle confirmation chahiye.")
        pages = self._pages()
        if len(pages) < 2:
            raise RuntimeError("Current tab close verify karne ke liye kam se kam 2 tabs chahiye.")
        page = self._active_page()
        current_url = page.url
        page.close()
        pages = self._pages()
        self._page = pages[-1]
        self._page.bring_to_front()
        logger.info(
            "Closed isolated browser tab",
            extra={"event": "isolated_browser_tab_closed", "closed_url": current_url},
        )
        return self.current_page_state()

    def switch_tab(
        self,
        *,
        index: int | None = None,
        direction: str = "next",
    ) -> BrowserPageState:
        pages = self._pages()
        active_page = self._active_page()
        current_index = pages.index(active_page)
        target_index = (
            index if index is not None else next_tab_index(current_index, len(pages), direction)
        )
        target_page = pages[target_index]
        target_page.bring_to_front()
        self._page = target_page
        logger.info(
            "Switched isolated browser tab",
            extra={
                "event": "isolated_browser_tab_switched",
                "from_index": current_index,
                "to_index": target_index,
            },
        )
        return self.current_page_state()

    def search_on_page(self, query: str) -> PageSearchResult:
        if not query.strip():
            raise ValueError("Search query khaali nahi ho sakti.")
        page = self._active_page()
        match_count = int(
            page.evaluate(
                """
                (query) => {
                  const text = (document.body?.innerText || "").toLowerCase();
                  const normalized = query.toLowerCase();
                  if (!normalized) return 0;
                  return text.split(normalized).length - 1;
                }
                """,
                query,
            )
        )
        logger.info(
            "Searched text on page",
            extra={
                "event": "isolated_browser_page_searched",
                "query": query,
                "matches": match_count,
            },
        )
        return PageSearchResult(
            query=query,
            match_count=match_count,
            page=self.current_page_state(),
        )

    def current_page_state(self) -> BrowserPageState:
        pages = self._pages()
        page = self._active_page()
        self._page = page
        return BrowserPageState(
            title=page.title(),
            url=page.url,
            tab_count=len(pages),
            active_tab_index=pages.index(page),
            browser_name=self.session_info.browser_name,
        )

    def open_youtube(self) -> BrowserPageState:
        return self.open_website("https://www.youtube.com")

    def search_and_play_youtube_playlist(self, search_query: str) -> PlaybackResult:
        self.open_website(
            f"https://www.youtube.com/results?search_query={quote_plus(search_query + ' playlist')}"
        )
        page = self._active_page()
        page.wait_for_url("**/results?*", timeout=30_000)
        candidate = page.locator(
            "ytd-playlist-renderer a#video-title, "
            "ytd-video-renderer a#video-title, "
            "a[href*='/playlist'], "
            "a[href*='/watch']"
        ).first
        candidate.wait_for(state="visible", timeout=30_000)
        selected_href = candidate.get_attribute("href")
        candidate.click()
        page.wait_for_load_state("domcontentloaded", timeout=30_000)
        time.sleep(2.0)
        is_playing = bool(
            page.evaluate(
                """
                () => {
                  const video = document.querySelector('video');
                  if (!video) return false;
                  const maybePromise = video.play();
                  if (maybePromise && typeof maybePromise.catch === 'function') {
                    maybePromise.catch(() => {});
                  }
                  return !video.paused;
                }
                """
            )
        )
        current_state = self.current_page_state()
        logger.info(
            "YouTube playlist searched and playback attempted",
            extra={
                "event": "isolated_browser_youtube_playlist",
                "search_query": search_query,
                "playing": is_playing,
                "selected_href": urljoin("https://www.youtube.com", selected_href or ""),
                "page_title": current_state.title,
                "page_url": current_state.url,
            },
        )
        return PlaybackResult(
            search_query=search_query,
            playing=is_playing,
            page=current_state,
            selected_href=urljoin("https://www.youtube.com", selected_href or ""),
        )

    def open_instagram_login(self, *, confirmed: bool = False) -> BrowserPageState:
        return self.open_website("https://www.instagram.com/accounts/login/", confirmed=confirmed)

    def open_whatsapp_web(self, *, confirmed: bool = False) -> BrowserPageState:
        return self.open_website("https://web.whatsapp.com", confirmed=confirmed)

    def _active_page(self) -> Any:
        if self._session is None:
            self.start()
        pages = self._pages()
        if self._page is not None and not self._page.is_closed():
            return self._page
        self._page = pages[-1]
        return self._page

    def _pages(self) -> list[Any]:
        if self._context is None:
            raise RuntimeError("Isolated browser context available nahi hai.")
        pages = [page for page in self._context.pages if not page.is_closed()]
        if not pages:
            page = self._context.new_page()
            pages.append(page)
        return pages

    def _stabilize_session(self, launch_url: str) -> Any:
        pages = self._pages()
        primary = pages[0]
        for extra_page in pages[1:]:
            try:
                extra_page.close()
            except Exception:
                continue
        primary.goto(launch_url, wait_until="domcontentloaded", timeout=30_000)
        primary.wait_for_load_state("domcontentloaded", timeout=30_000)
        primary.bring_to_front()
        return primary

    @staticmethod
    def _reserve_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            return int(sock.getsockname()[1])

    @staticmethod
    def _wait_for_cdp_endpoint(port: int, timeout_seconds: float = 20.0) -> str:
        deadline = time.time() + timeout_seconds
        last_error: Exception | None = None
        version_url = f"http://127.0.0.1:{port}/json/version"
        while time.time() < deadline:
            try:
                with urlopen(version_url, timeout=1.0) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    websocket_url = payload.get("webSocketDebuggerUrl")
                    if websocket_url:
                        return f"http://127.0.0.1:{port}"
            except (OSError, URLError, json.JSONDecodeError) as exc:
                last_error = exc
                time.sleep(0.25)
        raise RuntimeError(f"Browser CDP endpoint ready nahi hua: {last_error}")
