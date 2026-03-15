from __future__ import annotations

import contextlib
import ctypes
import logging
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

import psutil

logger = logging.getLogger(__name__)

try:
    from pywinauto import Application
    from pywinauto.keyboard import send_keys
except ImportError:  # pragma: no cover - optional automation dependency
    Application = None
    send_keys = None

try:
    import win32clipboard
except ImportError:  # pragma: no cover - optional automation dependency
    win32clipboard = None

_SW_RESTORE: Final = 9
_VK_CONTROL: Final = 0x11
_VK_RETURN: Final = 0x0D
_VK_TAB: Final = 0x09
_VK_W: Final = 0x57
_VK_L: Final = 0x4C
_VK_F: Final = 0x46
_VK_T: Final = 0x54
_VK_V: Final = 0x56
_VK_SHIFT: Final = 0x10
_VK_C: Final = 0x43
_VK_ESCAPE: Final = 0x1B
_WM_CHAR: Final = 0x0102
_WM_KEYDOWN: Final = 0x0100
_WM_KEYUP: Final = 0x0101
_KF_FLAG_DEFAULT: Final = 0

_FOLDER_IDS: Final[dict[str, str]] = {
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
}


@dataclass(frozen=True, slots=True)
class AppLaunchSpec:
    command: tuple[str, ...] | None = None
    uri: str | None = None
    executable_candidates: tuple[Path, ...] = ()


_APP_SPECS: Final[dict[str, AppLaunchSpec]] = {
    "notepad": AppLaunchSpec(command=("notepad.exe",)),
    "calculator": AppLaunchSpec(command=("calc.exe",)),
    "paint": AppLaunchSpec(command=("mspaint.exe",)),
    "explorer": AppLaunchSpec(command=("explorer.exe",)),
    "command prompt": AppLaunchSpec(command=("cmd.exe",)),
    "powershell": AppLaunchSpec(command=("powershell.exe",)),
    "task manager": AppLaunchSpec(command=("taskmgr.exe",)),
    "settings": AppLaunchSpec(uri="ms-settings:"),
    "snipping tool": AppLaunchSpec(command=("SnippingTool.exe",)),
    "edge": AppLaunchSpec(
        executable_candidates=(
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        )
    ),
    "chrome": AppLaunchSpec(
        executable_candidates=(
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        )
    ),
    "visual studio code": AppLaunchSpec(
        executable_candidates=(
            Path.home() / "AppData/Local/Programs/Microsoft VS Code/Code.exe",
            Path(r"C:\Program Files\Microsoft VS Code\Code.exe"),
        )
    ),
    "telegram": AppLaunchSpec(
        executable_candidates=(
            Path.home() / "AppData/Roaming/Telegram Desktop/Telegram.exe",
            Path.home() / "OneDrive/Documents/shortcuts/Downloads/Telegram Desktop/Telegram.exe",
        )
    ),
    "whatsapp": AppLaunchSpec(
        executable_candidates=(
            Path.home() / "AppData/Local/WhatsApp/WhatsApp.exe",
            Path(r"C:\Program Files\WindowsApps\WhatsApp.exe"),
        )
    ),
    "spotify": AppLaunchSpec(
        executable_candidates=(
            Path.home() / "AppData/Roaming/Spotify/Spotify.exe",
            Path.home() / "AppData/Local/Microsoft/WindowsApps/Spotify.exe",
        )
    ),
    "discord": AppLaunchSpec(
        executable_candidates=(
            Path.home() / "AppData/Local/Discord/Update.exe",
            Path.home() / "AppData/Local/Discord/app-1.0.0/Discord.exe",
        )
    ),
}

_APP_PROCESS_NAMES: Final[dict[str, tuple[str, ...]]] = {
    "notepad": ("notepad.exe",),
    "calculator": ("calculatorapp.exe", "win32calc.exe"),
    "paint": ("mspaint.exe",),
    "explorer": ("explorer.exe",),
    "command prompt": ("cmd.exe", "conhost.exe"),
    "powershell": ("powershell.exe", "pwsh.exe"),
    "task manager": ("taskmgr.exe",),
    "settings": ("systemsettings.exe",),
    "snipping tool": ("snippingtool.exe",),
    "edge": ("msedge.exe",),
    "chrome": ("chrome.exe",),
    "visual studio code": ("code.exe",),
    "telegram": ("telegram.exe",),
    "whatsapp": ("whatsapp.exe",),
    "spotify": ("spotify.exe",),
    "discord": ("discord.exe", "update.exe"),
}


class _Guid(ctypes.Structure):
    _fields_: ClassVar = [
        ("data1", ctypes.c_ulong),
        ("data2", ctypes.c_ushort),
        ("data3", ctypes.c_ushort),
        ("data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_uuid(cls, value: uuid.UUID) -> _Guid:
        data = value.bytes_le
        return cls(
            int.from_bytes(data[0:4], "little"),
            int.from_bytes(data[4:6], "little"),
            int.from_bytes(data[6:8], "little"),
            (ctypes.c_ubyte * 8)(*data[8:16]),
        )


class WindowController:
    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        self._ole32 = ctypes.WinDLL("ole32", use_last_error=True)

    def launch_app(self, app_name: str) -> subprocess.Popen[str] | None:
        spec = _APP_SPECS.get(app_name)
        if spec is None:
            raise ValueError(f"Unsupported app `{app_name}`.")

        logger.info(
            "Launching Windows app",
            extra={"event": "windows_app_launching", "app_name": app_name},
        )
        if spec.uri is not None:
            os.startfile(spec.uri)
            return None
        if spec.command is not None:
            return subprocess.Popen(list(spec.command))

        for candidate in spec.executable_candidates:
            if candidate.exists():
                if app_name == "discord" and candidate.name.lower() == "update.exe":
                    return subprocess.Popen([str(candidate), "--processStart", "Discord.exe"])
                return subprocess.Popen([str(candidate)])
        raise FileNotFoundError(f"{app_name} executable not found on this machine.")

    def close_app(self, app_name: str) -> int:
        process_names = _APP_PROCESS_NAMES.get(app_name)
        if process_names is None:
            raise ValueError(f"Unsupported app `{app_name}`.")

        terminated = 0
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name not in process_names:
                continue
            try:
                proc.terminate()
                proc.wait(timeout=5)
                terminated += 1
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.TimeoutExpired):
                continue

        logger.info(
            "Closing Windows app",
            extra={"event": "windows_app_closed", "app_name": app_name, "terminated": terminated},
        )
        return terminated

    def open_folder(self, target_name: str) -> Path:
        target = self.resolve_path(target_name, must_exist=True)
        if not target.is_dir():
            raise FileNotFoundError(f"`{target}` folder nahi hai.")
        open_path_in_explorer(target)
        return target

    def create_folder(self, folder_name: str, *, base_dir: Path | None = None) -> Path:
        target = self._build_target_path(folder_name, base_dir=base_dir)
        target.mkdir(parents=True, exist_ok=True)
        logger.info("Folder created", extra={"event": "folder_created", "path": str(target)})
        return target

    def create_file(self, file_name: str, *, base_dir: Path | None = None) -> Path:
        target = self._build_target_path(file_name, base_dir=base_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        logger.info("File created", extra={"event": "file_created", "path": str(target)})
        return target

    def rename_path(self, source_name: str, new_name: str) -> Path:
        source = self.resolve_path(source_name, must_exist=True)
        target = source.with_name(new_name)
        source.rename(target)
        logger.info(
            "Path renamed",
            extra={
                "event": "path_renamed",
                "source_path": str(source),
                "target_path": str(target),
            },
        )
        return target

    def move_path(self, source_name: str, destination_name: str) -> Path:
        source = self.resolve_path(source_name, must_exist=True)
        destination = self.resolve_path(destination_name, must_exist=False)
        destination_parent = destination if destination.exists() and destination.is_dir() else None
        final_target = destination / source.name if destination_parent else destination
        final_target.parent.mkdir(parents=True, exist_ok=True)
        moved_path = Path(shutil.move(str(source), str(final_target)))
        logger.info(
            "Path moved",
            extra={
                "event": "path_moved",
                "source_path": str(source),
                "target_path": str(moved_path),
            },
        )
        return moved_path

    def resolve_path(self, target_name: str, *, must_exist: bool) -> Path:
        normalized = target_name.strip().strip("\"'")
        lowered = normalized.lower()
        if lowered in _FOLDER_IDS:
            resolved = known_folder_path(lowered)
            if must_exist and not resolved.exists():
                raise FileNotFoundError(f"`{resolved}` nahi mila.")
            return resolved

        target = Path(normalized)
        candidates: list[Path] = []
        if target.is_absolute():
            candidates.append(target)
        else:
            cwd = Path.cwd()
            candidates.append(cwd / target)
            for folder_key in ("desktop", "downloads", "documents"):
                try:
                    candidates.append(known_folder_path(folder_key) / target)
                except FileNotFoundError:
                    continue

        if must_exist:
            for candidate in candidates:
                if candidate.exists():
                    return candidate
            raise FileNotFoundError(f"`{target_name}` path nahi mila.")

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def foreground_process_name(self) -> str | None:
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = ctypes.c_ulong()
        self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None
        try:
            return psutil.Process(pid.value).name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def focus_window_for_processes(self, process_names: tuple[str, ...]) -> int | None:
        process_targets = {name.lower() for name in process_names}
        windows: list[int] = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def enum_callback(hwnd, _lparam):
            if not self._user32.IsWindowVisible(hwnd):
                return True
            if self._user32.GetWindowTextLengthW(hwnd) == 0:
                return True
            pid = ctypes.c_ulong()
            self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if not pid.value:
                return True
            try:
                process_name = psutil.Process(pid.value).name().lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return True
            if process_name in process_targets:
                windows.append(int(hwnd))
            return True

        self._user32.EnumWindows(enum_callback, 0)
        if not windows:
            return None

        hwnd = windows[0]
        self._user32.ShowWindow(hwnd, _SW_RESTORE)
        self._user32.SetForegroundWindow(hwnd)
        if Application is not None:
            try:
                app = Application(backend="uia").connect(handle=hwnd)
                app.window(handle=hwnd).set_focus()
            except Exception:
                pass
        logger.info(
            "Focused window for processes",
            extra={"event": "window_focused", "hwnd": hwnd, "process_names": process_names},
        )
        return hwnd

    def close_active_tab(self, process_names: tuple[str, ...]) -> bool:
        hwnd = self._browser_window_for_processes(process_names)
        if hwnd is None:
            return False
        self._send_browser_keys(hwnd, "^w", (_VK_CONTROL,), _VK_W)
        logger.info(
            "Active browser tab close sent",
            extra={"event": "browser_tab_close_sent", "process_names": process_names, "hwnd": hwnd},
        )
        return True

    def open_url_in_active_browser(self, process_names: tuple[str, ...], url: str) -> bool:
        hwnd = self._browser_window_for_processes(process_names)
        if hwnd is None:
            return False
        self._focus_address_bar(hwnd)
        time.sleep(0.12)
        self._paste_into_focused_browser(hwnd, url)
        self._press_browser_enter(hwnd)
        logger.info(
            "URL typed into active browser",
            extra={
                "event": "browser_live_url_opened",
                "url": url,
                "process_names": process_names,
                "hwnd": hwnd,
            },
        )
        return True

    def focus_address_bar_in_browser(self, process_names: tuple[str, ...]) -> bool:
        hwnd = self._browser_window_for_processes(process_names)
        if hwnd is None:
            return False
        self._focus_address_bar(hwnd)
        logger.info(
            "Focused browser address bar",
            extra={
                "event": "browser_address_bar_focused",
                "process_names": process_names,
                "hwnd": hwnd,
            },
        )
        return True

    def open_new_tab_in_browser(
        self,
        process_names: tuple[str, ...],
        url: str = "about:blank",
    ) -> bool:
        hwnd = self._browser_window_for_processes(process_names)
        if hwnd is None:
            return False
        self._send_browser_keys(hwnd, "^t", (_VK_CONTROL,), _VK_T)
        time.sleep(0.2)
        normalized_url = url.strip()
        if normalized_url and normalized_url.lower() != "about:blank":
            self._paste_into_focused_browser(hwnd, normalized_url)
            self._press_browser_enter(hwnd)
        logger.info(
            "Opened browser new tab",
            extra={
                "event": "browser_new_tab_opened",
                "process_names": process_names,
                "hwnd": hwnd,
                "url": normalized_url or "about:blank",
            },
        )
        return True

    def switch_browser_tab(
        self,
        process_names: tuple[str, ...],
        *,
        direction: str = "next",
    ) -> bool:
        hwnd = self._browser_window_for_processes(process_names)
        if hwnd is None:
            return False
        if direction == "previous":
            if send_keys is not None:
                send_keys("^+{TAB}", pause=0.02)
            else:
                self._post_hotkey(hwnd, (_VK_CONTROL, _VK_SHIFT), _VK_TAB)
        else:
            self._send_browser_keys(hwnd, "^{TAB}", (_VK_CONTROL,), _VK_TAB)
        logger.info(
            "Switched browser tab",
            extra={
                "event": "browser_tab_switched",
                "process_names": process_names,
                "hwnd": hwnd,
                "direction": direction,
            },
        )
        return True

    def search_on_page_in_browser(self, process_names: tuple[str, ...], query: str) -> bool:
        hwnd = self._browser_window_for_processes(process_names)
        if hwnd is None:
            return False
        self._send_browser_keys(hwnd, "^f", (_VK_CONTROL,), _VK_F)
        time.sleep(0.15)
        self._paste_into_focused_browser(hwnd, query)
        self._press_browser_enter(hwnd)
        logger.info(
            "Triggered browser in-page search",
            extra={
                "event": "browser_page_search",
                "process_names": process_names,
                "hwnd": hwnd,
                "query": query,
            },
        )
        return True

    def current_browser_title_and_url(
        self,
        process_names: tuple[str, ...],
    ) -> tuple[str, str] | None:
        hwnd = self._browser_window_for_processes(process_names)
        if hwnd is None:
            return None
        title = self._window_title(hwnd)
        url = self._copy_browser_url(hwnd)
        cleaned_title = title.removesuffix(" - Microsoft Edge")
        cleaned_title = cleaned_title.removesuffix(" - Google Chrome").strip()
        logger.info(
            "Read browser title and URL",
            extra={
                "event": "browser_page_info_read",
                "process_names": process_names,
                "hwnd": hwnd,
                "title": cleaned_title,
                "url": url,
            },
        )
        return cleaned_title or title, url

    def _build_target_path(self, raw_target: str, *, base_dir: Path | None) -> Path:
        target = Path(raw_target.strip().strip("\"'"))
        if target.is_absolute():
            return target
        return (base_dir or Path.cwd()) / target

    def _browser_window_for_processes(self, process_names: tuple[str, ...]) -> int | None:
        foreground_name = self.foreground_process_name()
        if foreground_name in {name.lower() for name in process_names}:
            hwnd = int(self._user32.GetForegroundWindow())
            if hwnd:
                return hwnd
        hwnd = self.focus_window_for_processes(process_names)
        if hwnd is not None:
            time.sleep(0.25)
        return hwnd

    def _window_title(self, hwnd: int) -> str:
        length = int(self._user32.GetWindowTextLengthW(hwnd))
        buffer = ctypes.create_unicode_buffer(length + 1)
        self._user32.GetWindowTextW(hwnd, buffer, length + 1)
        return str(buffer.value)

    def _type_text(self, hwnd: int, text: str) -> None:
        for char in text:
            self._user32.PostMessageW(hwnd, _WM_CHAR, ord(char), 0)
            time.sleep(0.005)

    def _post_key(self, hwnd: int, key: int) -> None:
        self._user32.PostMessageW(hwnd, _WM_KEYDOWN, key, 0)
        time.sleep(0.01)
        self._user32.PostMessageW(hwnd, _WM_KEYUP, key, 0)

    def _post_hotkey(self, hwnd: int, modifiers: tuple[int, ...], key: int) -> None:
        for modifier in modifiers:
            self._user32.PostMessageW(hwnd, _WM_KEYDOWN, modifier, 0)
        self._user32.PostMessageW(hwnd, _WM_KEYDOWN, key, 0)
        self._user32.PostMessageW(hwnd, _WM_KEYUP, key, 0)
        for modifier in reversed(modifiers):
            self._user32.PostMessageW(hwnd, _WM_KEYUP, modifier, 0)

    def _send_browser_keys(
        self,
        hwnd: int,
        sequence: str,
        fallback_modifiers: tuple[int, ...],
        fallback_key: int,
    ) -> None:
        if send_keys is not None:
            send_keys(sequence, pause=0.02)
            return
        self._post_hotkey(hwnd, fallback_modifiers, fallback_key)

    def _focus_address_bar(self, hwnd: int) -> None:
        self._send_browser_keys(hwnd, "^l", (_VK_CONTROL,), _VK_L)

    def _press_browser_enter(self, hwnd: int) -> None:
        if send_keys is not None:
            send_keys("{ENTER}", pause=0.02)
            return
        self._post_key(hwnd, _VK_RETURN)

    def _type_into_focused_browser(self, hwnd: int, text: str) -> None:
        if send_keys is not None:
            send_keys(text, with_spaces=True, pause=0.01)
            return
        self._type_text(hwnd, text)

    def _paste_into_focused_browser(self, hwnd: int, text: str) -> None:
        previous_clipboard = self._read_clipboard_text()
        if win32clipboard is None:
            self._type_into_focused_browser(hwnd, text)
            return
        self._set_clipboard_text(text)
        self._send_browser_keys(hwnd, "^v", (_VK_CONTROL,), _VK_V)
        time.sleep(0.05)
        if previous_clipboard is not None:
            self._set_clipboard_text(previous_clipboard)

    def _copy_browser_url(self, hwnd: int) -> str:
        previous_clipboard = self._read_clipboard_text()
        if win32clipboard is not None:
            self._set_clipboard_text("")
        self._focus_address_bar(hwnd)
        time.sleep(0.15)
        self._send_browser_keys(hwnd, "^c", (_VK_CONTROL,), _VK_C)
        copied = self._wait_for_clipboard_text(previous_clipboard)
        self._send_browser_keys(hwnd, "{ESC}", tuple(), _VK_ESCAPE)
        if previous_clipboard:
            self._set_clipboard_text(previous_clipboard)
        return copied

    def _wait_for_clipboard_text(
        self,
        previous_text: str | None,
        timeout_seconds: float = 2.0,
    ) -> str:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            current = self._read_clipboard_text()
            if current and current != previous_text:
                return current
            time.sleep(0.05)
        return self._read_clipboard_text() or ""

    def _read_clipboard_text(self) -> str | None:
        if win32clipboard is None:
            return None
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                return str(win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT))
        except Exception:
            return None
        finally:
            with contextlib.suppress(Exception):
                win32clipboard.CloseClipboard()
        return None

    def _set_clipboard_text(self, text: str) -> None:
        if win32clipboard is None:
            return
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            with contextlib.suppress(Exception):
                win32clipboard.CloseClipboard()


def browser_process_names(browser_name: str) -> tuple[str, ...]:
    if browser_name == "chrome":
        return ("chrome.exe",)
    return ("msedge.exe",)


def browser_executable(browser_name: str) -> Path:
    spec = _APP_SPECS[browser_name]
    for path in spec.executable_candidates:
        if path.exists():
            return path
    raise FileNotFoundError(f"{browser_name} executable not found.")


def start_url_in_browser(browser_name: str, url: str) -> None:
    executable = browser_executable(browser_name)
    subprocess.Popen([str(executable), url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(
        "Browser launched with URL",
        extra={"event": "browser_url_launch", "browser_name": browser_name, "url": url},
    )


def known_folder_path(folder_key: str) -> Path:
    folder_id = _FOLDER_IDS.get(folder_key.lower())
    if folder_id is None:
        raise FileNotFoundError(f"Unknown known folder `{folder_key}`.")

    guid = _Guid.from_uuid(uuid.UUID(folder_id))
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    out_path = ctypes.c_void_p()
    result = shell32.SHGetKnownFolderPath(
        ctypes.byref(guid),
        _KF_FLAG_DEFAULT,
        None,
        ctypes.byref(out_path),
    )
    if result != 0:
        raise FileNotFoundError(f"Windows known folder `{folder_key}` resolve nahi hua.")
    try:
        return Path(ctypes.wstring_at(out_path))
    finally:
        ole32.CoTaskMemFree(out_path)


def open_path_in_explorer(path: Path) -> None:
    os.startfile(path)
    logger.info(
        "Opened path in Explorer",
        extra={"event": "explorer_path_opened", "path": str(path)},
    )
