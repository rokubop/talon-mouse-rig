"""Core utilities - imports from rig-core + mouse-specific helpers

Vec2/easing/math come from rig-core at runtime via _build_classes().
Mouse-specific: SubpixelAdjuster, mouse API wrappers.
"""

from typing import Tuple, Optional
from talon import app
from .mouse_api import get_mouse_move_functions, get_mouse_scroll_function


# ============================================================================
# RIG-CORE IMPORTS - set by _build_classes()
# ============================================================================

Vec2 = None
is_vec2 = None
EPSILON = None
get_easing_function = None
EASING_FUNCTIONS = None
lerp = None
clamp = None
normalize_vector = None


def _build_classes(core):
    global Vec2, is_vec2, EPSILON, get_easing_function, EASING_FUNCTIONS
    global lerp, clamp, normalize_vector
    Vec2 = core.Vec2
    is_vec2 = core.is_vec2
    EPSILON = core.EPSILON
    get_easing_function = core.get_easing_function
    EASING_FUNCTIONS = core.EASING_FUNCTIONS
    lerp = core.lerp
    clamp = core.clamp
    normalize_vector = core.normalize_vector


# ============================================================================
# MOUSE MOVEMENT API (mouse-specific)
# ============================================================================

_mouse_move_absolute = None
_mouse_move_relative = None
_mouse_scroll = None


def _initialize_mouse_move():
    global _mouse_move_absolute, _mouse_move_relative, _mouse_scroll
    _mouse_move_absolute, _mouse_move_relative = get_mouse_move_functions()
    _mouse_scroll = get_mouse_scroll_function()


def get_mouse_move_with_overrides(absolute_override: Optional[str] = None, relative_override: Optional[str] = None):
    """Get mouse move functions with optional API overrides

    Used by builders that have API overrides set via rig.api().

    Args:
        absolute_override: Override for absolute API
        relative_override: Override for relative API

    Returns:
        Tuple of (absolute_func, relative_func)
    """
    if absolute_override is None and relative_override is None:
        if _mouse_move_absolute is None:
            _initialize_mouse_move()
        return _mouse_move_absolute, _mouse_move_relative

    return get_mouse_move_functions(absolute_override, relative_override)


def get_mouse_scroll_with_override(override: Optional[str] = None):
    """Get mouse scroll function with optional API override

    Args:
        override: Optional API override

    Returns:
        scroll_func(dx, dy) -> None
    """
    if override is None:
        if _mouse_scroll is None:
            _initialize_mouse_move()
        return _mouse_scroll

    return get_mouse_scroll_function(override)


app.register("ready", _initialize_mouse_move)


def mouse_move(x: float, y: float) -> None:
    """Move mouse to absolute screen position"""
    if _mouse_move_absolute is None:
        _initialize_mouse_move()
    _mouse_move_absolute(x, y)


def mouse_move_relative(dx: float, dy: float) -> None:
    """Move mouse by relative delta"""
    if _mouse_move_relative is None:
        _initialize_mouse_move()
    _mouse_move_relative(dx, dy)


def mouse_scroll_native(dx: float, dy: float) -> None:
    """Scroll using native platform API with sub-line precision"""
    if _mouse_scroll is None:
        _initialize_mouse_move()
    _mouse_scroll(dx, dy)


# ============================================================================
# MOUSE-SPECIFIC: SCROLL EMIT THRESHOLD
# ============================================================================

SCROLL_EMIT_THRESHOLD = 0.001


# ============================================================================
# MOUSE-SPECIFIC: SUBPIXEL ADJUSTER
# ============================================================================

class SubpixelAdjuster:
    """
    Accumulates fractional pixel movements to prevent rounding errors.

    When moving the mouse in small increments (e.g., 0.3 pixels per frame),
    naive int() conversion would lose the fractional part each frame,
    causing the mouse to drift from its intended path. This class tracks
    the accumulated fractional error and applies corrections.
    """
    def __init__(self):
        self.x_frac = 0.0
        self.y_frac = 0.0

    def adjust(self, dx: float, dy: float) -> Tuple[int, int]:
        """Convert float deltas to integer pixels while tracking fractional error"""
        self.x_frac += dx
        self.y_frac += dy

        dx_int = int(self.x_frac)
        dy_int = int(self.y_frac)

        self.x_frac -= dx_int
        self.y_frac -= dy_int

        return dx_int, dy_int

    def reset(self):
        self.x_frac = 0.0
        self.y_frac = 0.0
