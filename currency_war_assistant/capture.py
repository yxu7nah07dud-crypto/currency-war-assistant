"""Window-only WGC capture. No keyboard, mouse, process-memory or game input APIs."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import threading
import time

import numpy as np


@dataclass(frozen=True)
class Window:
    hwnd: int
    title: str
    width: int
    height: int


def _user32():
    dll = ctypes.WinDLL("user32", use_last_error=True)
    dll.IsWindow.argtypes = [wintypes.HWND]
    dll.IsIconic.argtypes = [wintypes.HWND]
    dll.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    dll.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    dll.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    dll.IsWindowVisible.argtypes = [wintypes.HWND]
    return dll


def find_game_windows() -> list[Window]:
    user = _user32()
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def callback(hwnd, _):
        if user.IsWindowVisible(hwnd):
            text = ctypes.create_unicode_buffer(user.GetWindowTextLengthW(hwnd) + 1)
            user.GetWindowTextW(hwnd, text, len(text))
            if text.value in ("崩坏：星穹铁道", "Honkai: Star Rail", "崩壞：星穹鐵道"):
                rect = wintypes.RECT()
                user.GetWindowRect(hwnd, ctypes.byref(rect))
                found.append(Window(int(hwnd), text.value, rect.right - rect.left, rect.bottom - rect.top))
        return True

    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.EnumWindows(callback, 0)
    return found


class CaptureUnavailable(RuntimeError):
    pass


class WindowCapture:
    def __init__(self):
        self.window = None
        self._frame = None
        self._at = 0.0
        self._lock = threading.Lock()
        self._control = None
        self._capture = None
        self.closed = True

    def start(self, window: Window):
        from windows_capture import WindowsCapture
        self.stop()
        self.window = window
        self.closed = False
        self._frame = None
        self._capture = WindowsCapture(
            cursor_capture=False, draw_border=None, secondary_window=False,
            minimum_update_interval=250, window_hwnd=window.hwnd,
        )

        @self._capture.event
        def on_frame_arrived(frame, control):
            now = time.monotonic()
            if now - self._at < 0.25:
                return
            image = np.ascontiguousarray(frame.frame_buffer[:, :, :3]).copy()
            with self._lock:
                self._frame = image
                self._at = now

        @self._capture.event
        def on_closed():
            self.closed = True

        self._control = self._capture.start_free_threaded()

    def latest(self):
        if not self.window or self.closed or not _user32().IsWindow(self.window.hwnd):
            raise CaptureUnavailable("游戏窗口已关闭，请重新选择窗口。")
        if _user32().IsIconic(self.window.hwnd):
            raise CaptureUnavailable("游戏已最小化，观察已暂停。恢复游戏后自动继续。")
        with self._lock:
            if self._frame is None:
                raise CaptureUnavailable("等待游戏画面。如果一直黑屏，请使用无边框窗口。")
            image, at = self._frame.copy(), self._at
        if time.monotonic() - at > 10:
            raise CaptureUnavailable("游戏画面已停止更新，暂不生成新建议。")
        if image.size == 0 or image.std() < 3:
            raise CaptureUnavailable("捕获到黑屏，请把游戏切换为无边框窗口。")
        return image, at

    def stop(self):
        control, self._control = self._control, None
        if control is not None:
            control.stop()
        self.closed = True


def set_overlay_capture_exclusion(hwnd: int) -> bool:
    """Exclude only our own overlay from capture; this is not a protection bypass."""
    user = _user32()
    user.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
    return bool(user.SetWindowDisplayAffinity(hwnd, 0x11))
