"""Mouse movement API implementations

Supports multiple mouse movement backends:
- talon: Cross-platform using Talon's ctrl.mouse_move (default)
- windows_raw: Windows win32api.mouse_event (relative movement)
- windows_sendinput: Windows SendInput (modern, absolute positioning)
- macos: macOS CGWarpMouseCursorPosition
- linux_x11: Linux X11 XWarpPointer
"""

import platform
from typing import Callable
from talon import ctrl, settings


# Available mouse APIs
MOUSE_APIS = {
    'talon': 'Talon ctrl.mouse_move (default, cross-platform)',
    'windows_raw': 'Windows win32api.mouse_event (relative movement)',
    'windows_sendinput': 'Windows SendInput (modern, recommended for Windows)',
    'macos': 'macOS CGWarpMouseCursorPosition (direct positioning)',
    'linux_x11': 'Linux X11 XWarpPointer (direct positioning)',
}

# Track availability of each API
_windows_raw_available = False
_windows_sendinput_available = False
_macos_available = False
_linux_x11_available = False

# Check platform-specific availability
if platform.system() == "Windows":
    try:
        import win32api, win32con  # type: ignore
        _windows_raw_available = True
    except ImportError:
        pass

    try:
        import ctypes
        from ctypes import wintypes
        _windows_sendinput_available = True
    except ImportError:
        pass

elif platform.system() == "Darwin":
    try:
        import Quartz  # type: ignore
        _macos_available = True
    except ImportError:
        pass

elif platform.system() == "Linux":
    try:
        from Xlib import display  # type: ignore
        _linux_x11_available = True
    except ImportError:
        pass


def _make_talon_mouse_move() -> Callable[[float, float], None]:
    """Cross-platform Talon mouse movement"""
    def move(x: float, y: float) -> None:
        ctrl.mouse_move(int(x), int(y))
    return move


def _make_windows_raw_mouse_move() -> Callable[[float, float], None]:
    """Windows mouse_event (relative movement)"""
    import win32api, win32con  # type: ignore

    def move(x: float, y: float) -> None:
        current_x, current_y = ctrl.mouse_pos()
        dx = int(x - current_x)
        dy = int(y - current_y)
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy)
    return move


def _make_windows_sendinput_mouse_move() -> Callable[[float, float], None]:
    """Windows SendInput (modern, absolute positioning)"""
    import ctypes
    from ctypes import wintypes

    # Constants
    INPUT_MOUSE = 0
    MOUSEEVENTF_ABSOLUTE = 0x8000
    MOUSEEVENTF_MOVE = 0x0001

    # Structures
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("mi", MOUSEINPUT)]
        _anonymous_ = ("_input",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("_input", _INPUT)
        ]

    def move(x: float, y: float) -> None:
        # Convert to absolute coordinates (0-65535 range)
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        abs_x = int((x * 65535) / screen_width)
        abs_y = int((y * 65535) / screen_height)

        input_struct = INPUT(type=INPUT_MOUSE)
        input_struct.mi.dx = abs_x
        input_struct.mi.dy = abs_y
        input_struct.mi.dwFlags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE

        ctypes.windll.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))

    return move


def _make_macos_mouse_move() -> Callable[[float, float], None]:
    """macOS CoreGraphics mouse movement"""
    import Quartz  # type: ignore

    def move(x: float, y: float) -> None:
        Quartz.CGWarpMouseCursorPosition((x, y))

    return move


def _make_linux_x11_mouse_move() -> Callable[[float, float], None]:
    """Linux X11 mouse movement"""
    from Xlib import display  # type: ignore

    disp = display.Display()
    root = disp.screen().root

    def move(x: float, y: float) -> None:
        root.warp_pointer(int(x), int(y))
        disp.sync()

    return move


def get_mouse_move_function() -> Callable[[float, float], None]:
    """Get the appropriate mouse move function based on settings

    Returns a function that takes (x, y) coordinates and moves the mouse.
    Falls back to Talon's mouse_move if the requested API is unavailable.
    """
    api_type = settings.get("user.mouse_rig_api", "talon")

    # Validate API type
    if api_type not in MOUSE_APIS:
        available = ', '.join(f"'{k}'" for k in MOUSE_APIS.keys())
        print(f"[Mouse Rig] Invalid mouse_rig_api: '{api_type}'")
        print(f"[Mouse Rig] Available options: {available}")
        print(f"[Mouse Rig] Falling back to 'talon'")
        return _make_talon_mouse_move()

    # Select appropriate API
    if api_type == "windows_raw":
        if not _windows_raw_available:
            print("[Mouse Rig] windows_raw API requires pywin32, falling back to talon")
            return _make_talon_mouse_move()
        return _make_windows_raw_mouse_move()

    elif api_type == "windows_sendinput":
        if not _windows_sendinput_available:
            print("[Mouse Rig] windows_sendinput API not available, falling back to talon")
            return _make_talon_mouse_move()
        return _make_windows_sendinput_mouse_move()

    elif api_type == "macos":
        if not _macos_available:
            print("[Mouse Rig] macos API requires pyobjc-framework-Quartz, falling back to talon")
            return _make_talon_mouse_move()
        return _make_macos_mouse_move()

    elif api_type == "linux_x11":
        if not _linux_x11_available:
            print("[Mouse Rig] linux_x11 API requires python-xlib, falling back to talon")
            return _make_talon_mouse_move()
        return _make_linux_x11_mouse_move()

    else:  # talon (default)
        return _make_talon_mouse_move()
