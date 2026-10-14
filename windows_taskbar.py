"""Windows taskbar window identity and relaunch metadata. See README.md."""
from __future__ import annotations

import ctypes
from pathlib import Path
import sys
from uuid import UUID


class GUID(ctypes.Structure):
    _fields_ = [("data1", ctypes.c_uint32), ("data2", ctypes.c_uint16),
                ("data3", ctypes.c_uint16), ("data4", ctypes.c_ubyte * 8)]


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", ctypes.c_uint32)]


class VariantData(ctypes.Union):
    _fields_ = [("pointer", ctypes.c_void_p),
                ("storage", ctypes.c_ubyte * (16 if ctypes.sizeof(ctypes.c_void_p) == 8 else 8))]


class PROPVARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_uint16), ("reserved1", ctypes.c_uint16),
                ("reserved2", ctypes.c_uint16), ("reserved3", ctypes.c_uint16),
                ("data", VariantData)]


def _check(result, operation):
    if result < 0:
        raise OSError(f"{operation}: HRESULT 0x{result & 0xffffffff:08X}")


class WindowPropertyStore:
    """Own an IPropertyStore reference; caller keeps its HWND alive."""

    def __init__(self, hwnd):
        self.pointer = ctypes.c_void_p()
        iid = GUID.from_buffer_copy(UUID("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99").bytes_le)
        get_store = ctypes.WinDLL("shell32").SHGetPropertyStoreForWindow
        get_store.argtypes = [ctypes.c_void_p, ctypes.POINTER(GUID),
                              ctypes.POINTER(ctypes.c_void_p)]
        get_store.restype = ctypes.c_long
        _check(get_store(hwnd, ctypes.byref(iid), ctypes.byref(self.pointer)), "Get window property store")
        self.table = ctypes.cast(self.pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents

    @staticmethod
    def key(pid):
        return PROPERTYKEY(GUID.from_buffer_copy(
            UUID("9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3").bytes_le), pid)

    def set_string(self, pid, value):
        key = self.key(pid)
        buffer = ctypes.create_unicode_buffer(value)
        variant = PROPVARIANT()
        variant.vt = 31  # VT_LPWSTR; SetValue copies this caller-owned string.
        variant.data.pointer = ctypes.cast(buffer, ctypes.c_void_p).value
        method = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                   ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))(self.table[6])
        _check(method(self.pointer, ctypes.byref(key), ctypes.byref(variant)), "Set taskbar property")

    def get_string(self, pid):
        key, variant = self.key(pid), PROPVARIANT()
        method = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                   ctypes.POINTER(PROPERTYKEY), ctypes.POINTER(PROPVARIANT))(self.table[5])
        _check(method(self.pointer, ctypes.byref(key), ctypes.byref(variant)), "Read taskbar property")
        clear = ctypes.WinDLL("ole32").PropVariantClear
        clear.argtypes = [ctypes.POINTER(PROPVARIANT)]
        clear.restype = ctypes.c_long
        try:
            return ctypes.wstring_at(variant.data.pointer) if variant.vt == 31 else None
        finally:
            clear(ctypes.byref(variant))

    def commit(self):
        method = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p)(self.table[7])
        _check(method(self.pointer), "Commit taskbar properties")

    def close(self):
        if self.pointer:
            method = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(self.table[2])
            method(self.pointer)
            self.pointer = ctypes.c_void_p()


def set_window_taskbar_properties(hwnd, app_id, icon_path: Path, relaunch_command, report=print):
    """Set the window's grouping/pinned icon, instead of inheriting Python's icon."""
    if sys.platform != "win32":
        return
    icon_path = Path(icon_path).resolve()
    report(f"[Taskbar window 1/3] Input file: {icon_path}")
    report("[Taskbar window 1/3] Output files: None (Windows window properties in memory)")
    if not icon_path.is_file():
        raise FileNotFoundError(icon_path)
    ole32 = ctypes.WinDLL("ole32")
    ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    ole32.CoInitializeEx.restype = ctypes.c_long
    result = ole32.CoInitializeEx(None, 2)
    if result < 0 and result != -2147417850:  # RPC_E_CHANGED_MODE: already initialized by Qt.
        _check(result, "Initialize Windows COM")
    store = None
    try:
        store = WindowPropertyStore(hwnd)
        # Set relaunch metadata before ID, which triggers the taskbar grouping refresh.
        properties = [(2, relaunch_command), (4, "TTP Selection Studio"),
                      (3, f"{icon_path},0"), (5, app_id)]
        for index, (pid, value) in enumerate(properties, 1):
            report(f"[Taskbar window 2/3] Setting property {pid} ({index}/{len(properties)})")
            store.set_string(pid, value)
        store.commit()
        for pid, value in properties:
            if store.get_string(pid) != value:
                raise OSError(f"Windows did not retain taskbar property {pid}")
        report("[Taskbar window 3/3] Complete: window identity and pixel relaunch icon verified")
    finally:
        if store is not None:
            store.close()
        if result >= 0:
            ole32.CoUninitialize()
