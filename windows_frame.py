"""Stable native Windows frame colors for Fusion Studio. See README.md."""
from __future__ import annotations

import ctypes
import sys
from weakref import WeakSet

from PySide6 import QtCore, QtWidgets


# DWM COLORREF values use 0x00BBGGRR. These neutral colors match the Qt palette.
FRAME_ATTRIBUTES = ((20, 1), (34, 0x303030), (35, 0x181818), (36, 0xD4D4D4))


class FixedWindowsFrame(QtCore.QObject):
    """Keep native title bars dark without replacing native window controls."""

    def __init__(self, app):
        super().__init__(app)
        self.reported = WeakSet()
        self.failures = set()
        self.set_attribute = ctypes.WinDLL("dwmapi").DwmSetWindowAttribute
        self.set_attribute.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                       ctypes.c_void_p, ctypes.c_uint32]
        self.set_attribute.restype = ctypes.c_long
        app.installEventFilter(self)

    def apply(self, widget):
        hwnd = int(widget.effectiveWinId())
        if not hwnd:
            return
        first = widget not in self.reported
        if first:
            print(f"[Window frame 2/3] Applying fixed dark colors to {type(widget).__name__}", flush=True)
        applied = 0
        for attribute, color in FRAME_ATTRIBUTES:
            value = ctypes.c_uint32(color)
            result = self.set_attribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value))
            if result >= 0:
                applied += 1
            elif (attribute, result) not in self.failures:
                self.failures.add((attribute, result))
                print(f"[Window frame] Attribute {attribute} unavailable: HRESULT 0x{result & 0xffffffff:08X}", flush=True)
        if first:
            self.reported.add(widget)
            print(f"[Window frame 3/3] Ready: {applied}/{len(FRAME_ATTRIBUTES)} attributes applied", flush=True)

    def eventFilter(self, watched, event):
        if (event.type() in (QtCore.QEvent.Type.Show, QtCore.QEvent.Type.WinIdChange,
                             QtCore.QEvent.Type.ActivationChange, QtCore.QEvent.Type.PaletteChange)
                and isinstance(watched, QtWidgets.QWidget)
                and watched.isWindow()
                and watched.windowType() in (QtCore.Qt.WindowType.Window, QtCore.Qt.WindowType.Dialog)
                and watched.testAttribute(QtCore.Qt.WidgetAttribute.WA_WState_Created)):
            self.apply(watched)
        return False


def install_fixed_windows_frame(app):
    """Install once for native Windows Qt; other platforms keep their own decorations."""
    if sys.platform != "win32" or app.platformName() != "windows":
        return None
    if getattr(app, "_fixed_windows_frame", None) is not None:
        return app._fixed_windows_frame
    print("[Window frame 1/3] Input files: None (fixed dark colors in memory)", flush=True)
    print("[Window frame 1/3] Output files: None (native window appearance only)", flush=True)
    try:
        app._fixed_windows_frame = FixedWindowsFrame(app)
    except (OSError, AttributeError) as error:
        print(f"[Window frame] Native appearance unavailable: {error}", flush=True)
        return None
    for widget in app.topLevelWidgets():
        if (widget.windowType() in (QtCore.Qt.WindowType.Window, QtCore.Qt.WindowType.Dialog)
                and widget.testAttribute(QtCore.Qt.WidgetAttribute.WA_WState_Created)):
            app._fixed_windows_frame.apply(widget)
    return app._fixed_windows_frame
