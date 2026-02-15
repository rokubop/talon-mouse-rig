"""Mouse movement and scroll API implementations

Supports multiple mouse movement backends:
- talon: Cross-platform using Talon's ctrl.mouse_move (default)
- windows_mouse_event: Windows win32api.mouse_event (legacy API)
- windows_send_input: Windows SendInput (modern, recommended for Windows)
- macos_warp: macOS CGWarpMouseCursorPosition
- linux_x11: Linux X11 XWarpPointer

Each API provides two movement modes:
- Absolute: Move cursor to screen position (for desktop use, pos.to())
- Relative: Move cursor by delta (for gaming with infinite rotation, pos.by())

Scroll APIs use the same backends with sub-line precision via native platform
APIs. Talon's actions.mouse_scroll() quantizes small floats to zero, breaking
smooth direction transitions at low scroll speeds. Native APIs accumulate
fractional values and emit when crossing integer thresholds.
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
        scale = settings.get("user.mouse_rig_scale", 1.0)

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
        scale = settings.get("user.mouse_rig_scale", 1.0)

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


# ============================================================================
# SCROLL API
# ============================================================================
# All scroll functions: signature (dx: float, dy: float) -> None
# dx/dy are in line units. Native functions accumulate fractionally and
# emit when crossing integer thresholds.
# Sign conventions:
#   positive dy = scroll DOWN, positive dx = scroll RIGHT


def _make_talon_mouse_scroll() -> Callable[[float, float], None]:
    """Cross-platform Talon scroll (fallback)

    Accumulates fractional lines and only calls actions.mouse_scroll when
    we have >= 1 line, avoiding Talon's quantization of small float values.
    """
    from talon import actions

    accum_x = [0.0]
    accum_y = [0.0]

    def scroll(dx: float, dy: float) -> None:
        accum_x[0] += dx
        accum_y[0] += dy

        emit_x = int(accum_x[0])
        emit_y = int(accum_y[0])

        if emit_x != 0 or emit_y != 0:
            accum_x[0] -= emit_x
            accum_y[0] -= emit_y
            actions.mouse_scroll(x=emit_x, y=emit_y)

    return scroll


def _make_windows_send_input_mouse_scroll() -> Callable[[float, float], None]:
    """Windows SendInput scroll with sub-line accumulation

    Uses MOUSEEVENTF_WHEEL for vertical and MOUSEEVENTF_HWHEEL for horizontal.
    WHEEL_DELTA = 120 units per line. Accumulates fractional lines in closure.
    """
    import ctypes
    from ctypes import wintypes

    INPUT_MOUSE = 0
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_HWHEEL = 0x1000
    WHEEL_DELTA = 120

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

    accum_x = [0.0]
    accum_y = [0.0]

    def scroll(dx: float, dy: float) -> None:
        accum_x[0] += dx * WHEEL_DELTA
        accum_y[0] += dy * WHEEL_DELTA

        # Vertical scroll
        delta_y = int(accum_y[0])
        if delta_y != 0:
            accum_y[0] -= delta_y
            input_struct = INPUT(type=INPUT_MOUSE)
            # WHEEL positive = scroll UP, our positive dy = scroll DOWN → negate
            input_struct.mi.mouseData = (-delta_y) & 0xFFFFFFFF
            input_struct.mi.dwFlags = MOUSEEVENTF_WHEEL
            ctypes.windll.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))

        # Horizontal scroll
        delta_x = int(accum_x[0])
        if delta_x != 0:
            accum_x[0] -= delta_x
            input_struct = INPUT(type=INPUT_MOUSE)
            # HWHEEL positive = scroll RIGHT, matches our positive dx convention
            input_struct.mi.mouseData = delta_x & 0xFFFFFFFF
            input_struct.mi.dwFlags = MOUSEEVENTF_HWHEEL
            ctypes.windll.user32.SendInput(1, ctypes.byref(input_struct), ctypes.sizeof(INPUT))

    return scroll


def _make_windows_mouse_event_mouse_scroll() -> Callable[[float, float], None]:
    """Windows mouse_event scroll with sub-line accumulation (legacy API)"""
    import win32api, win32con  # type: ignore

    WHEEL_DELTA = 120
    accum_x = [0.0]
    accum_y = [0.0]

    def scroll(dx: float, dy: float) -> None:
        accum_x[0] += dx * WHEEL_DELTA
        accum_y[0] += dy * WHEEL_DELTA

        # Vertical scroll
        delta_y = int(accum_y[0])
        if delta_y != 0:
            accum_y[0] -= delta_y
            # WHEEL positive = scroll UP, our positive dy = scroll DOWN → negate
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -delta_y)

        # Horizontal scroll
        delta_x = int(accum_x[0])
        if delta_x != 0:
            accum_x[0] -= delta_x
            # HWHEEL positive = scroll RIGHT, matches our positive dx convention
            win32api.mouse_event(win32con.MOUSEEVENTF_HWHEEL, 0, 0, delta_x)

    return scroll


def _make_macos_warp_mouse_scroll() -> Callable[[float, float], None]:
    """macOS CoreGraphics scroll with pixel-level precision"""
    import Quartz  # type: ignore

    accum_x = [0.0]
    accum_y = [0.0]

    def scroll(dx: float, dy: float) -> None:
        accum_x[0] += dx
        accum_y[0] += dy

        # Use pixel units (kCGScrollEventUnitPixel = 1) for sub-line precision
        # CGEventCreateScrollWheelEvent: positive = scroll UP, our positive dy = DOWN → negate
        delta_y = int(accum_y[0] * 10)  # Scale lines to pixel-ish units
        delta_x = int(accum_x[0] * 10)

        if delta_y != 0 or delta_x != 0:
            if delta_y != 0:
                accum_y[0] -= delta_y / 10.0
            if delta_x != 0:
                accum_x[0] -= delta_x / 10.0
            event = Quartz.CGEventCreateScrollWheelEvent(
                None, 1, 2, -delta_y, delta_x  # unit=pixel, axes=2
            )
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    return scroll


def _make_linux_x11_mouse_scroll() -> Callable[[float, float], None]:
    """Linux X11 scroll via XTest fake button events

    Buttons: 4=up, 5=down, 6=left, 7=right. Accumulates to whole lines.
    """
    from Xlib import display, X  # type: ignore
    from Xlib.ext import xtest  # type: ignore

    disp = display.Display()
    accum_x = [0.0]
    accum_y = [0.0]

    def scroll(dx: float, dy: float) -> None:
        accum_x[0] += dx
        accum_y[0] += dy

        # Vertical: button 4=up, 5=down
        while abs(accum_y[0]) >= 1.0:
            button = 5 if accum_y[0] > 0 else 4  # positive dy = down = button 5
            xtest.fake_input(disp, X.ButtonPress, button)
            xtest.fake_input(disp, X.ButtonRelease, button)
            accum_y[0] -= 1.0 if accum_y[0] > 0 else -1.0

        # Horizontal: button 6=left, 7=right
        while abs(accum_x[0]) >= 1.0:
            button = 7 if accum_x[0] > 0 else 6  # positive dx = right = button 7
            xtest.fake_input(disp, X.ButtonPress, button)
            xtest.fake_input(disp, X.ButtonRelease, button)
            accum_x[0] -= 1.0 if accum_x[0] > 0 else -1.0

        disp.sync()

    return scroll


def get_mouse_scroll_function(override: Optional[str] = None) -> Callable[[float, float], None]:
    """Get the appropriate mouse scroll function based on settings

    Uses mouse_rig_scroll_api setting. If set to "default", falls back to mouse_rig_api.

    Args:
        override: Optional API override (takes precedence over settings)

    Returns:
        scroll_func(dx_lines, dy_lines) -> None
    """
    if override is not None:
        api = override
    else:
        api = settings.get("user.mouse_rig_scroll_api", "default")
        if api == "default":
            api = settings.get("user.mouse_rig_api", "platform")

    if api == "platform":
        api = _get_platform_api()

    return _get_scroll_function(api)


def _get_scroll_function(api_type: str) -> Callable[[float, float], None]:
    """Get a scroll function for the specified API"""
    if api_type not in MOUSE_APIS:
        api_type = "talon"

    if api_type == "windows_send_input":
        if not _windows_send_input_available:
            api_type = "talon"
        else:
            return _make_windows_send_input_mouse_scroll()

    elif api_type == "windows_mouse_event":
        if not _windows_mouse_event_available:
            api_type = "talon"
        else:
            return _make_windows_mouse_event_mouse_scroll()

    elif api_type == "macos_warp":
        if not _macos_warp_available:
            api_type = "talon"
        else:
            return _make_macos_warp_mouse_scroll()

    elif api_type == "linux_x11":
        if not _linux_x11_available:
            api_type = "talon"
        else:
            return _make_linux_x11_mouse_scroll()

    return _make_talon_mouse_scroll()
