"""Window decoration controls, restricted to the assistant's own Tk window."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys


class WindowChrome:
    CAPTION = 0x00C00000
    THICKFRAME = 0x00040000
    FRAME_BITS = CAPTION | THICKFRAME

    def __init__(self, root):
        self.root = root
        self.borderless = False
        self._frame_bits = None
        self._drag = None
        self._resize = None
        self._user = None
        if sys.platform == "win32":
            self._user = ctypes.WinDLL("user32", use_last_error=True)
            self._user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            self._user.GetAncestor.restype = wintypes.HWND
            self._get_style = self._user.GetWindowLongPtrW
            self._get_style.argtypes = [wintypes.HWND, ctypes.c_int]
            self._get_style.restype = ctypes.c_ssize_t
            self._set_style = self._user.SetWindowLongPtrW
            self._set_style.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
            self._set_style.restype = ctypes.c_ssize_t
            self._user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
            self._user.SetWindowPos.restype = wintypes.BOOL
            for name in ("GetWindowRect", "GetClientRect"):
                function = getattr(self._user, name)
                function.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
                function.restype = wintypes.BOOL
        root.bind("<Map>", self._mapped, add="+")

    def hwnd(self):
        self.root.update_idletasks()
        return self._user.GetAncestor(self.root.winfo_id(), 2)

    def style(self):
        return self._get_style(self.hwnd(), -16)

    def set_borderless(self, enabled):
        """Retain taskbar, Alt+Tab and minimizing while hiding native decoration."""
        previous_mode = self.borderless
        self.borderless = bool(enabled)
        try:
            self._apply_borderless(enabled)
        except Exception:
            self.borderless = previous_mode
            raise

    def _apply_borderless(self, enabled):
        enabled = bool(enabled)
        if self._user is None:
            self.root.overrideredirect(enabled)
        else:
            hwnd = self.hwnd()
            current = self._get_style(hwnd, -16)
            if self._frame_bits is None:
                if not enabled:
                    return
                # Tk may not have installed its managed frame during the first
                # idle callback. Remember the regular frame for Esc/unticking.
                regular = self.CAPTION | (self.THICKFRAME if any(self.root.resizable()) else 0)
                self._frame_bits = (current & self.FRAME_BITS) or regular
            desired = (current & ~self.FRAME_BITS) if enabled else (
                (current & ~self.FRAME_BITS) | self._frame_bits)
            if current != desired:
                width, height = self.root.winfo_width(), self.root.winfo_height()
                ctypes.set_last_error(0)
                previous = self._set_style(hwnd, -16, desired)
                error = ctypes.get_last_error()
                if previous == 0 and error:
                    raise ctypes.WinError(error)
                # Refresh the cached frame without changing location, stacking
                # order, or focus. This never touches any game-window handle.
                if not self._user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0037):
                    raise ctypes.WinError(ctypes.get_last_error())
                self.set_size(width, height)
        self.borderless = enabled

    def _mapped(self, event):
        if event.widget is self.root and self.borderless:
            self.root.after_idle(self._restore_mode)

    def _restore_mode(self):
        if self.borderless:
            self.set_borderless(True)

    def set_size(self, width, height):
        if self._user is None:
            self.root.geometry(f"{width}x{height}")
            return
        hwnd = self.hwnd()
        outer, client = wintypes.RECT(), wintypes.RECT()
        if not self._user.GetWindowRect(hwnd, ctypes.byref(outer)) or not self._user.GetClientRect(hwnd, ctypes.byref(client)):
            raise ctypes.WinError(ctypes.get_last_error())
        # Tk caches the native frame margins. Resizing through geometry() after
        # removing the frame would add those old margins on every drag.
        width += (outer.right - outer.left) - (client.right - client.left)
        height += (outer.bottom - outer.top) - (client.bottom - client.top)
        if not self._user.SetWindowPos(hwnd, None, 0, 0, width, height, 0x0016):
            raise ctypes.WinError(ctypes.get_last_error())

    def bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self.begin_drag)
        widget.bind("<B1-Motion>", self.drag)
        widget.bind("<ButtonRelease-1>", self.end_drag)

    def begin_drag(self, event):
        self._drag = (event.x_root, event.y_root,
                      self.root.winfo_x(), self.root.winfo_y())

    def drag(self, event):
        if self._drag:
            px, py, x, y = self._drag
            x, y = x + event.x_root - px, y + event.y_root - py
            if self._user:
                if not self._user.SetWindowPos(self.hwnd(), None, x, y, 0, 0, 0x0015):
                    raise ctypes.WinError(ctypes.get_last_error())
            else:
                self.root.geometry(f"{x:+d}{y:+d}")

    def end_drag(self, event=None):
        self._drag = None

    def bind_resize(self, widget):
        widget.bind("<ButtonPress-1>", self.begin_resize)
        widget.bind("<B1-Motion>", self.resize)
        widget.bind("<ButtonRelease-1>", self.end_resize)

    def begin_resize(self, event):
        self._resize = (event.x_root, event.y_root,
                        self.root.winfo_width(), self.root.winfo_height())

    def resize(self, event):
        if self._resize:
            px, py, width, height = self._resize
            min_width, min_height = self.root.minsize()
            width = max(min_width, width + event.x_root - px)
            height = max(min_height, height + event.y_root - py)
            self.set_size(width, height)

    def end_resize(self, event=None):
        self._resize = None
