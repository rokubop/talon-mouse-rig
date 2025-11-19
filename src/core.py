"""Core utilities for mouse rig V2 - reused from V1

This module contains low-level utilities that are proven and stable:
- Vec2 class for 2D vectors
- Easing functions
- Mouse movement API
- SubpixelAdjuster for smooth movement
"""

import math
from typing import Tuple, Union, Optional, Callable
from dataclasses import dataclass
from talon import app
from .mouse_api import get_mouse_move_function


# ============================================================================
# MOUSE MOVEMENT API
# ============================================================================

# Mouse move function - initialized after Talon is ready
_mouse_move = None


def _initialize_mouse_move():
    global _mouse_move
    _mouse_move = get_mouse_move_function()


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

    def to_cardinal(self) -> Optional[str]:
        """Convert vector to cardinal/intercardinal direction string

        Returns one of: "right", "left", "up", "down",
                       "up_right", "up_left", "down_right", "down_left"
        or None if vector is zero.

        Uses a threshold to distinguish between pure cardinal directions
        (within 22.5° of an axis) and intercardinal/diagonal directions.

        Examples:
            Vec2(1, 0).to_cardinal() -> "right"
            Vec2(-1, 0).to_cardinal() -> "left"
            Vec2(0, -1).to_cardinal() -> "up"
            Vec2(0, 1).to_cardinal() -> "down"
            Vec2(1, -1).to_cardinal() -> "up_right"  # 45° diagonal
            Vec2(0.9, -0.2).to_cardinal() -> "right"  # Within 22.5° of right
            Vec2(0, 0).to_cardinal() -> None
        """
        if self.x == 0 and self.y == 0:
            return None

        # Threshold for pure cardinal vs intercardinal
        # tan(67.5°) ≈ 2.414, which is halfway between pure cardinal (90°) and diagonal (45°)
        # This means directions within ±22.5° of an axis are considered pure cardinal
        threshold = 2.414

        # Pure cardinal directions (within 22.5° of axis)
        if abs(self.x) > abs(self.y) * threshold:
            return "right" if self.x > 0 else "left"
        if abs(self.y) > abs(self.x) * threshold:
            return "up" if self.y < 0 else "down"

        # Intercardinal/diagonal directions
        if self.x > 0 and self.y < 0:
            return "up_right"
        elif self.x < 0 and self.y < 0:
            return "up_left"
        elif self.x > 0 and self.y > 0:
            return "down_right"
        elif self.x < 0 and self.y > 0:
            return "down_left"

        # Fallback (shouldn't happen)
        return "right"

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


def ease_in_2(t: float) -> float:
    return t ** 2


def ease_out_2(t: float) -> float:
    return 1 - (1 - t) ** 2


def ease_in_out_2(t: float) -> float:
    return 2 * t ** 2 if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


def ease_in_3(t: float) -> float:
    return t ** 3


def ease_out_3(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out_3(t: float) -> float:
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def ease_in_4(t: float) -> float:
    return t ** 4


def ease_out_4(t: float) -> float:
    return 1 - (1 - t) ** 4


def ease_in_out_4(t: float) -> float:
    return 8 * t ** 4 if t < 0.5 else 1 - (-2 * t + 2) ** 4 / 2


EASING_FUNCTIONS = {
    "linear": ease_linear,
    "ease_in": ease_in,
    "ease_out": ease_out,
    "ease_in_out": ease_in_out,
    "ease_in_2": ease_in_2,
    "ease_out_2": ease_out_2,
    "ease_in_out_2": ease_in_out_2,
    "ease_in_3": ease_in_3,
    "ease_out_3": ease_out_3,
    "ease_in_out_3": ease_in_out_3,
    "ease_in_4": ease_in_4,
    "ease_out_4": ease_out_4,
    "ease_in_out_4": ease_in_out_4,
}


def get_easing_function(name: str) -> Callable[[float], float]:
    """Get easing function by name, defaults to linear"""
    return EASING_FUNCTIONS.get(name, ease_linear)
