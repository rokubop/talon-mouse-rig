"""Core utilities for mouse rig V2 - reused from V1

This module contains low-level utilities that are proven and stable:
- Vec2 class for 2D vectors
- Easing functions
- Mouse movement API (Talon vs Windows raw input)
- SubpixelAdjuster for smooth movement
"""

import math
import time
import platform
from typing import Tuple, Union, Optional, Callable
from dataclasses import dataclass
from talon import ctrl, app, settings


# ============================================================================
# MOUSE MOVEMENT API SETUP
# ============================================================================

_windows_raw_available = False
if platform.system() == "Windows":
    try:
        import win32api, win32con
        _windows_raw_available = True
    except ImportError:
        pass


def _make_talon_mouse_move():
    def move(x: float, y: float) -> None:
        ctrl.mouse_move(int(x), int(y))
    return move


def _make_windows_raw_mouse_move():
    def move(x: float, y: float) -> None:
        current_x, current_y = ctrl.mouse_pos()
        dx = int(x - current_x)
        dy = int(y - current_y)
        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy)
    return move


# Mouse move function - initialized after Talon is ready
_mouse_move = None


def _initialize_mouse_move():
    global _mouse_move
    movement_type = settings.get("user.mouse_rig_movement_type", "talon")
    if movement_type == "windows_raw" and _windows_raw_available:
        _mouse_move = _make_windows_raw_mouse_move()
    else:
        _mouse_move = _make_talon_mouse_move()


app.register("ready", _initialize_mouse_move)


def mouse_move(x: float, y: float) -> None:
    """Move mouse to absolute position"""
    if _mouse_move is None:
        _initialize_mouse_move()
    _mouse_move(x, y)


# ============================================================================
# VECTOR UTILITIES
# ============================================================================

# Small value for floating point comparisons (avoid division by zero, etc.)
EPSILON = 1e-10


@dataclass
class Vec2:
    """2D vector"""
    x: float
    y: float

    def __add__(self, other: 'Vec2') -> 'Vec2':
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vec2') -> 'Vec2':
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> 'Vec2':
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> 'Vec2':
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> 'Vec2':
        return Vec2(self.x / scalar, self.y / scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalized(self) -> 'Vec2':
        mag = self.magnitude()
        if mag < EPSILON:
            return Vec2(0, 0)
        return Vec2(self.x / mag, self.y / mag)

    def dot(self, other: 'Vec2') -> float:
        return self.x * other.x + self.y * other.y

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @staticmethod
    def from_tuple(t: Union[Tuple[float, float], 'Vec2']) -> 'Vec2':
        if isinstance(t, Vec2):
            return t
        return Vec2(t[0], t[1])


def normalize_vector(x: float, y: float) -> Tuple[float, float]:
    """Normalize a vector to unit length"""
    mag = math.sqrt(x ** 2 + y ** 2)
    if mag < EPSILON:
        return (0.0, 0.0)
    return (x / mag, y / mag)


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation"""
    return a + (b - a) * t


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max"""
    return max(min_val, min(max_val, value))


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
        """Reset accumulated fractional errors"""
        self.x_frac = 0.0
        self.y_frac = 0.0


# ============================================================================
# EASING FUNCTIONS
# ============================================================================

def ease_linear(t: float) -> float:
    return t


def ease_in(t: float) -> float:
    return 1 - math.cos(t * math.pi / 2)


def ease_out(t: float) -> float:
    return math.sin(t * math.pi / 2)


def ease_in_out(t: float) -> float:
    return (1 - math.cos(t * math.pi)) / 2


def ease_smoothstep(t: float) -> float:
    return t * t * (3 - 2 * t)


EASING_FUNCTIONS = {
    "linear": ease_linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
    "smoothstep": ease_smoothstep,
}


def get_easing_function(name: str) -> Callable[[float], float]:
    """Get easing function by name, defaults to linear"""
    return EASING_FUNCTIONS.get(name, ease_linear)
