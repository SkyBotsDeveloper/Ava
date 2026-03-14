from __future__ import annotations

import ctypes
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Final

import psutil

logger = logging.getLogger(__name__)

try:
    from pywinauto import Application
    from pywinauto.keyboard import send_keys
except ImportError:  # pragma: no cover - optional automation dependency
    Application = None
    send_keys = None

_SW_RESTORE: Final = 9
_VK_CONTROL: Final = 0x11
_VK_MENU: Final = 0x12
_VK_RETURN: Final = 0x0D
_VK_W: Final = 0x57
_VK_L: Final = 0x4C
_KEYEVENTF_KEYUP: Final = 0x0002
_WM_CHAR: Final = 0x0102
_WM_KEYDOWN: Final = 0x0100
_WM_KEYUP: Final = 0x0101

_APP_LAUNCH_COMMANDS: Final[dict[str, list[str]]] = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "command prompt": ["cmd.exe"],
}
_APP_PROCESS_NAMES: Final[dict[str, tuple[str, ...]]] = {
    "notepad": ("notepad.exe",),
    "calculator": ("calculatorapp.exe", "win32calc.exe"),
    "paint": ("mspaint.exe",),
    "explorer": ("explorer.exe",),
    "command prompt": ("cmd.exe", "conhost.exe"),
}


class WindowController:
    def __init__(self) -> None:
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    def launch_app(self, app_name: str) -> subprocess.Popen[str]:
        command = _APP_LAUNCH_COMMANDS.get(app_name)
        if command is None:
            raise ValueError(f"Unsupported app `{app_name}`.")
        logger.info(
            "Launching Windows app",
            extra={"event": "windows_app_launching", "app_name": app_name, "command": command},
        )
        return subprocess.Popen(command)

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

    def create_folder(self, folder_name: str, *, base_dir: Path | None = None) -> Path:
        target = (base_dir or Path.cwd()) / folder_name
        target.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Folder created",
            extra={"event": "folder_created", "path": str(target)},
        )
        return target

    def create_file(self, file_name: str, *, base_dir: Path | None = None) -> Path:
        target = (base_dir or Path.cwd()) / file_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch(exist_ok=True)
        logger.info(
            "File created",
            extra={"event": "file_created", "path": str(target)},
        )
        return target

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
        if send_keys is not None:
            send_keys("^w", pause=0.02)
        else:
            self._post_hotkey(hwnd, (_VK_CONTROL,), _VK_W)
        logger.info(
            "Active browser tab close sent",
            extra={"event": "browser_tab_close_sent", "process_names": process_names, "hwnd": hwnd},
        )
        return True

    def open_url_in_active_browser(self, process_names: tuple[str, ...], url: str) -> bool:
        hwnd = self._browser_window_for_processes(process_names)
        if hwnd is None:
            return False
        if send_keys is not None:
            send_keys("^l", pause=0.02)
            time.sleep(0.12)
            send_keys(url, with_spaces=True, pause=0.01)
            send_keys("{ENTER}", pause=0.02)
        else:
            self._post_hotkey(hwnd, (_VK_CONTROL,), _VK_L)
            time.sleep(0.12)
            self._type_text(hwnd, url)
            time.sleep(0.05)
            self._post_key(hwnd, _VK_RETURN)
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

    def _send_hotkey(self, modifiers: tuple[int, ...], key: int) -> None:
        for modifier in modifiers:
            self._user32.keybd_event(modifier, 0, 0, 0)
        self._user32.keybd_event(key, 0, 0, 0)
        time.sleep(0.04)
        self._user32.keybd_event(key, 0, _KEYEVENTF_KEYUP, 0)
        for modifier in reversed(modifiers):
            self._user32.keybd_event(modifier, 0, _KEYEVENTF_KEYUP, 0)

    def _tap_key(self, key: int) -> None:
        self._user32.keybd_event(key, 0, 0, 0)
        time.sleep(0.03)
        self._user32.keybd_event(key, 0, _KEYEVENTF_KEYUP, 0)

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


def browser_process_names(browser_name: str) -> tuple[str, ...]:
    if browser_name == "chrome":
        return ("chrome.exe",)
    return ("msedge.exe",)


def browser_executable(browser_name: str) -> Path:
    candidates = {
        "edge": (
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ),
        "chrome": (
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ),
    }
    for path in candidates.get(browser_name, ()):
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


def open_path_in_explorer(path: Path) -> None:
    os.startfile(path)
    logger.info(
        "Opened path in Explorer",
        extra={"event": "explorer_path_opened", "path": str(path)},
    )
