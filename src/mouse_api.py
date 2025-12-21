"""Mouse movement API implementations

Supports multiple mouse movement backends:
- talon: Cross-platform using Talon's ctrl.mouse_move (default)
- windows_mouse_event: Windows win32api.mouse_event (legacy API)
- windows_send_input: Windows SendInput (modern, recommended for Windows)
- macos_warp: macOS CGWarpMouseCursorPosition
- linux_x11: Linux X11 XWarpPointer

Each API provides two movement modes:
- Absolute: Move cursor to screen position (for desktop use, pos.to())
- Relative: Move cursor by delta (for gaming with infinite rotation, pos.by())
"""

import platform
from typing import Callable, Tuple, Optional
from talon import ctrl, settings


# Available mouse APIs
MOUSE_APIS = {
    'platform': 'Auto-detect best platform-specific API',
    'talon': 'Talon ctrl.mouse_move (default, cross-platform)',
    'windows_mouse_event': 'Windows win32api.mouse_event (legacy API)',
    'windows_send_input': 'Windows SendInput (modern, recommended)',
    'macos_warp': 'macOS CGWarpMouseCursorPosition',
    'linux_x11': 'Linux X11 XWarpPointer',
}

# Track availability of each API
_windows_mouse_event_available = False
_windows_send_input_available = False
_macos_warp_available = False
_linux_x11_available = False

# Check platform-specific availability
if platform.system() == "Windows":
    try:
        import win32api, win32con  # type: ignore
        _windows_mouse_event_available = True
    except ImportError:
        pass

    try:
        import ctypes
        from ctypes import wintypes
        _windows_send_input_available = True
    except ImportError:
        pass

elif platform.system() == "Darwin":
    try:
        import Quartz  # type: ignore
        _macos_warp_available = True
    except ImportError:
        pass

elif platform.system() == "Linux":
    try:
        from Xlib import display  # type: ignore
        _linux_x11_available = True
    except ImportError:
        pass


def _get_platform_api() -> str:
    """Auto-detect the best platform-specific mouse API

    Returns the recommended API name for the current platform.
    Falls back to 'talon' if no platform-specific API is available.
    """
    if platform.system() == "Windows":
        if _windows_send_input_available:
            return "windows_send_input"
        elif _windows_mouse_event_available:
            return "windows_mouse_event"
    elif platform.system() == "Darwin":
        if _macos_warp_available:
            return "macos_warp"
    elif platform.system() == "Linux":
        if _linux_x11_available:
            return "linux_x11"

    return "talon"


def _make_talon_mouse_move() -> Tuple[Callable[[float, float], None], Callable[[float, float], None]]:
    """Cross-platform Talon mouse movement

    Returns (absolute_func, relative_func)
    Uses ctrl.mouse_move for absolute and actions.mouse_nudge for relative.

    Note: int() wrapping is required because Talon's mouse APIs work in integer pixels.
    Subpixel accumulation is handled by SubpixelAdjuster in core.py, which only calls
    these functions when we've accumulated >= 1 pixel of movement.
    """
    from talon import actions

    def move_absolute(x: float, y: float) -> None:
        ctrl.mouse_move(int(x), int(y))

    def move_relative(dx: float, dy: float) -> None:
        actions.mouse_nudge(int(dx), int(dy))

    return move_absolute, move_relative


def _make_windows_mouse_event_mouse_move() -> Tuple[Callable[[float, float], None], Callable[[float, float], None]]:
    """Windows mouse_event (legacy API)

    Returns (absolute_func, relative_func)
    """
    import win32api, win32con  # type: ignore
    import ctypes

    def move_absolute(x: float, y: float) -> None:
        # Get screen dimensions
        screen_width = win32api.GetSystemMetrics(0)
        screen_height = win32api.GetSystemMetrics(1)

        # Convert to absolute coordinates (0-65535 range)
        # mouse_event with ABSOLUTE flag uses normalized coordinates
        abs_x = int(((x + 0.5) * 65536) / screen_width)
        abs_y = int(((y + 0.5) * 65536) / screen_height)

        win32api.mouse_event(
            win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_MOVE,
            abs_x,
            abs_y
        )

    def move_relative(dx: float, dy: float) -> None:
        # Apply user-configurable scale for sensitivity control
        scale = settings.get("user.mouse_rig_relative_scale", 1.0)

        # Relative movement using mickeys (device units)
        win32api.mouse_event(
            win32con.MOUSEEVENTF_MOVE,
            int(dx * scale),
            int(dy * scale)
        )

    return move_absolute, move_relative


def _make_windows_send_input_mouse_move() -> Tuple[Callable[[float, float], None], Callable[[float, float], None]]:
    """Windows SendInput (modern, recommended for Windows)

    Returns (absolute_func, relative_func)
    """
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

    def move_absolute(x: float, y: float) -> None:
        # Convert to absolute coordinates (0-65535 range)
        screen_width = ctypes.windll.user32.GetSystemMetrics(0)
        screen_height = ctypes.windll.user32.GetSystemMetrics(1)

        # SendInput uses normalized coordinates where (0,0) is top-left and (65535,65535) is bottom-right
        # Need to add 0.5 to x to center the pixel, and the range is 0-65535 not 0-65536
        abs_x = int(((x + 0.5) * 65536) / screen_width)
        abs_y = int(((y + 0.5) * 65536) / screen_height)

        input_struct = INPUT(type=INPUT_MOUSE)
        input_struct.mi.dx = abs_x
        input_struct.mi.dy = abs_y
        input_struct.mi.dwFlags = MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE

        ctypes.windll.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))

    def move_relative(dx: float, dy: float) -> None:
        # Apply user-configurable scale for sensitivity control
        scale = settings.get("user.mouse_rig_relative_scale", 1.0)

        # Relative movement (no ABSOLUTE flag)
        input_struct = INPUT(type=INPUT_MOUSE)
        input_struct.mi.dx = int(dx * scale)
        input_struct.mi.dy = int(dy * scale)
        input_struct.mi.dwFlags = MOUSEEVENTF_MOVE

        ctypes.windll.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))

    return move_absolute, move_relative


def _make_macos_warp_mouse_move() -> Tuple[Callable[[float, float], None], Callable[[float, float], None]]:
    """macOS CoreGraphics mouse movement

    Returns (absolute_func, relative_func)
    Note: macOS only supports absolute positioning, so relative mode
    implements relative movement on top of absolute positioning.
    """
    import Quartz  # type: ignore

    def move_absolute(x: float, y: float) -> None:
        Quartz.CGWarpMouseCursorPosition((x, y))

    def move_relative(dx: float, dy: float) -> None:
        # Get current position and add delta
        current_x, current_y = ctrl.mouse_pos()
        Quartz.CGWarpMouseCursorPosition((current_x + dx, current_y + dy))

    return move_absolute, move_relative


def _make_linux_x11_mouse_move() -> Tuple[Callable[[float, float], None], Callable[[float, float], None]]:
    """Linux X11 mouse movement

    Returns (absolute_func, relative_func)
    Note: X11 only supports absolute positioning, so relative mode
    implements relative movement on top of absolute positioning.
    """
    from Xlib import display  # type: ignore

    disp = display.Display()
    root = disp.screen().root

    def move_absolute(x: float, y: float) -> None:
        root.warp_pointer(int(x), int(y))
        disp.sync()

    def move_relative(dx: float, dy: float) -> None:
        # Get current position and add delta
        from talon import ctrl
        current_x, current_y = ctrl.mouse_pos()
        root.warp_pointer(int(current_x + dx), int(current_y + dy))
        disp.sync()

    return move_absolute, move_relative


def get_mouse_move_functions(absolute_override: Optional[str] = None, relative_override: Optional[str] = None) -> Tuple[Callable[[float, float], None], Callable[[float, float], None]]:
    """Get the appropriate mouse move functions based on settings

    Args:
        absolute_override: Optional override for absolute API (rarely needed)
        relative_override: Optional override for relative API (takes precedence over settings)

    Returns tuple of (absolute_func, relative_func) where:
    - absolute_func: Takes (x, y) screen coordinates (always uses Talon's ctrl.mouse_move)
    - relative_func: Takes (dx, dy) delta for relative movement (uses mouse_rig_api setting)

    Falls back to Talon's mouse_move if the requested API is unavailable.
    """
    # Always use Talon for absolute positioning
    absolute_api = absolute_override if absolute_override is not None else "talon"

    # Get relative API from settings
    relative_api = relative_override if relative_override is not None else settings.get("user.mouse_rig_api", "platform")

    # Resolve 'platform' to actual API for relative movement
    if relative_api == "platform":
        relative_api = _get_platform_api()

    # Get absolute function (always Talon)
    absolute_func = _get_api_function(absolute_api, is_absolute=True)

    # Get relative function
    relative_func = _get_api_function(relative_api, is_absolute=False)

    return absolute_func, relative_func


def _get_api_function(api_type: str, is_absolute: bool) -> Callable[[float, float], None]:
    """Get a single mouse move function for the specified API

    Args:
        api_type: The API type string
        is_absolute: True for absolute positioning, False for relative movement

    Returns:
        The appropriate mouse move function
    """
    # Validate API type
    if api_type not in MOUSE_APIS:
        api_type = "talon"

    # Select appropriate API
    if api_type == "windows_mouse_event":
        if not _windows_mouse_event_available:
            print("[Mouse Rig] windows_mouse_event API requires pywin32, falling back to talon")
            api_type = "talon"
        else:
            abs_func, rel_func = _make_windows_mouse_event_mouse_move()
            return abs_func if is_absolute else rel_func

    elif api_type == "windows_send_input":
        if not _windows_send_input_available:
            print("[Mouse Rig] windows_send_input API not available, falling back to talon")
            api_type = "talon"
        else:
            abs_func, rel_func = _make_windows_send_input_mouse_move()
            return abs_func if is_absolute else rel_func

    elif api_type == "macos_warp":
        if not _macos_warp_available:
            print("[Mouse Rig] macos_warp API requires pyobjc-framework-Quartz, falling back to talon")
            api_type = "talon"
        else:
            abs_func, rel_func = _make_macos_warp_mouse_move()
            return abs_func if is_absolute else rel_func

    elif api_type == "linux_x11":
        if not _linux_x11_available:
            print("[Mouse Rig] linux_x11 API requires python-xlib, falling back to talon")
            api_type = "talon"
        else:
            abs_func, rel_func = _make_linux_x11_mouse_move()
            return abs_func if is_absolute else rel_func

    # Default to talon
    abs_func, rel_func = _make_talon_mouse_move()
    return abs_func if is_absolute else rel_func
