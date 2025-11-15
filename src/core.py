"""Core utilities for mouse rig - vectors, easing, mouse movement"""

import math
import time
import platform
from typing import Tuple, Union, Optional, Callable, TYPE_CHECKING
from dataclasses import dataclass
from talon import ctrl, app, settings

if TYPE_CHECKING:
    from .state import RigState

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

# Default easing when .ease() is called without arguments
DEFAULT_EASING = "ease_out"


# ============================================================================
# ERROR MESSAGE HELPERS
# ============================================================================

def _get_speed_operations_help() -> str:
    """Get help text for available speed operations"""
    return (
        "    rig.speed(value)                                        # Set speed\n"
        "    rig.speed.to(value)                                     # With effects support\n"
        "    rig.speed.by(delta)                                     # Add/subtract\n"
        "    rig.speed.mul(factor)                                   # Multiply\n"
        "    rig.speed.div(divisor)                                  # Divide\n"
        "    rig.speed.to(20).over(500)                              # Transition over time\n"
        "    rig.speed.to(20).over(500, 'ease_in_out')               # With easing\n"
        "    rig.speed.mul(2).hold(1000)                             # Temporary boost\n"
        "    rig.speed.mul(2).over(300).hold(1000).revert(300)       # Full lifecycle\n"
        "    rig.speed.to(30).rate(10)                               # Rate-based (10/sec)"
    )

def _get_accel_operations_help() -> str:
    """Get help text for available accel operations"""
    return (
        "    rig.accel(value)                                        # Set acceleration\n"
        "    rig.accel.to(value)                                     # With effects support\n"
        "    rig.accel.by(delta)                                     # Add/subtract\n"
        "    rig.accel.mul(factor)                                   # Multiply\n"
        "    rig.accel.div(divisor)                                  # Divide\n"
        "    rig.accel.to(10).over(500)                              # Transition\n"
        "    rig.accel.to(10).over(500).hold(1000).revert(500)       # Temporary effect"
    )

def _get_pos_operations_help() -> str:
    """Get help text for available pos operations"""
    return (
        "    rig.pos.to(x, y)                                        # Move to position\n"
        "    rig.pos.to(x, y).over(1000)                             # Glide over time\n"
        "    rig.pos.to(x, y).over(1000, 'ease_in_out')              # With easing\n"
        "    rig.pos.by(dx, dy)                                      # Move by offset\n"
        "    rig.pos.by(dx, dy).over(500).revert(500)                # Move and return"
    )

def _get_direction_operations_help() -> str:
    """Get help text for available direction operations"""
    return (
        "    rig.direction(x, y)                                     # Set direction (legacy)\n"
        "    rig.direction.to(x, y)                                  # Set to absolute vector\n"
        "    rig.direction.to(1, 0).over(500)                        # Smooth rotation over time\n"
        "    rig.direction.to(1, 0).over(500, 'ease_in_out')         # With easing\n"
        "    rig.direction.to(1, 0).rate(90)                         # Rotate at 90°/sec\n"
        "    rig.direction.by(45)                                    # Rotate 45° (relative)\n"
        "    rig.direction.by(-90).over(500)                         # Rotate -90° smoothly\n"
        "    rig.direction.by(180).rate(90)                          # Rotate 180° at 90°/sec\n"
        "    rig.reverse()                                           # 180° turn (shorthand)"
    )

def _error_cannot_chain_property(builder_type: str, property_name: str) -> str:
    """Generate error message for invalid property chaining"""
    help_map = {
        "speed": _get_speed_operations_help(),
        "accel": _get_accel_operations_help(),
        "pos": _get_pos_operations_help(),
        "direction": _get_direction_operations_help(),
    }

    # Get the "current" property from builder_type (e.g., "direction" from "direction")
    current_prop = builder_type.split()[0] if ' ' in builder_type else builder_type

    help_text = help_map.get(current_prop, f"# See documentation for {current_prop} operations")

    return (
        f"Cannot chain '{property_name}' after '{builder_type}'.\n\n"
        f"Note: The core properties (speed, direction, pos, accel) cannot be chained together.\n"
        f"Use separate statements instead:\n"
        f"    rig = actions.user.mouse_rig()\n"
        f"    rig.{current_prop}(...)  # Set {current_prop}\n"
        f"    rig.{property_name}(...)  # Set {property_name}\n\n"
        f"You can chain these with .{current_prop}:\n"
        f"{help_text}"
    )

def _error_unknown_builder_attribute(builder_type: str, attribute_name: str, valid_methods: str) -> str:
    """Generate error message for unknown attribute on builder"""
    return (
        f"'{builder_type}' has no attribute '{attribute_name}'.\n\n"
        f"Available methods: {valid_methods}"
    )


# ============================================================================
# TRANSITION CLASSES (for .over() support)
# ============================================================================

class Transition:
    """Base class for transitions that happen over time"""
    def __init__(self, duration_ms: float, easing: str = "linear"):
        self.duration_ms = duration_ms
        self.start_time = time.perf_counter()
        self.easing = easing
        self.easing_fn = EASING_FUNCTIONS.get(easing, ease_linear)
        self.complete = False
        self.on_complete: Optional[Callable] = None

    def progress(self) -> float:
        """Get progress [0, 1] with easing applied"""
        elapsed = (time.perf_counter() - self.start_time) * 1000
        if elapsed >= self.duration_ms:
            if not self.complete:
                self.complete = True
                # Fire callback on first completion
                if self.on_complete:
                    try:
                        self.on_complete()
                    except Exception as e:
                        print(f"Error in transition callback: {e}")
            return 1.0
        t = elapsed / self.duration_ms
        return self.easing_fn(t)

    def update(self, rig_state: 'RigState') -> None:
        """Override in subclasses"""
        pass


class SpeedTransition(Transition):
    """Transition for speed changes over time"""
    def __init__(self, start_speed: float, target_speed: float, duration_ms: float, easing: str = "linear"):
        super().__init__(duration_ms, easing)
        self.start_speed = start_speed
        self.target_speed = target_speed

    def update(self, rig_state: 'RigState') -> None:
        p = self.progress()
        rig_state._speed = lerp(self.start_speed, self.target_speed, p)


class DirectionTransition(Transition):
    """Transition for direction changes over time"""
    def __init__(self, start_dir: Vec2, target_dir: Vec2, duration_ms: float, easing: str = "linear", interpolation: str = "slerp"):
        super().__init__(duration_ms, easing)
        self.start_dir = start_dir
        self.target_dir = target_dir
        self.interpolation = interpolation

        # Calculate angle for shortest arc interpolation (used by slerp)
        dot = start_dir.dot(target_dir)
        dot = clamp(dot, -1.0, 1.0)
        self.angle = math.acos(dot)

        # Determine rotation direction using cross product (used by slerp)
        cross = start_dir.x * target_dir.y - start_dir.y * target_dir.x
        self.direction = 1 if cross >= 0 else -1

    def update(self, rig_state: 'RigState') -> None:
        p = self.progress()

        if self.angle < EPSILON:
            # Already at target
            rig_state._direction = self.target_dir
            return

        if self.interpolation == "lerp":
            # Linear interpolation of direction vectors
            x = self.start_dir.x + (self.target_dir.x - self.start_dir.x) * p
            y = self.start_dir.y + (self.target_dir.y - self.start_dir.y) * p

            # Normalize to keep it as a unit direction vector
            length = math.sqrt(x * x + y * y)
            if length > EPSILON:
                rig_state._direction = Vec2(x / length, y / length)
            # else: keep current direction unchanged (can happen at midpoint of 180° turn)
        else:
            # Slerp for smooth rotation (default)
            current_angle = self.angle * p * self.direction

            # Rotate start_dir by current_angle
            cos_a = math.cos(current_angle)
            sin_a = math.sin(current_angle)

            new_x = self.start_dir.x * cos_a - self.start_dir.y * sin_a
            new_y = self.start_dir.x * sin_a + self.start_dir.y * cos_a

            rig_state._direction = Vec2(new_x, new_y).normalized()


class ReverseTransition(Transition):
    """Transition for 180° direction reversal with speed fade"""
    def __init__(self, start_speed: float, duration_ms: float, easing: str = "linear"):
        super().__init__(duration_ms, easing)
        self.start_speed = abs(start_speed)
        self.direction_flipped = False

    def update(self, rig_state: 'RigState') -> None:
        # Flip direction immediately on first update
        if not self.direction_flipped:
            rig_state._direction = Vec2(-rig_state._direction.x, -rig_state._direction.y)
            self.direction_flipped = True
        
        # Transition speed from -start_speed to +start_speed
        p = self.progress()
        new_speed = lerp(-self.start_speed, self.start_speed, p)
        rig_state._speed = new_speed
        print(f"ReverseTransition: p={p:.3f}, speed={new_speed:.2f} (start_speed={self.start_speed:.2f})")


class PositionTransition(Transition):
    """Transition for position glides"""
    def __init__(self, start_pos: Vec2, target_offset: Vec2, duration_ms: float, easing: str = "linear"):
        super().__init__(duration_ms, easing)
        self.start_pos = start_pos
        self.target_offset = target_offset
        self.last_offset = Vec2(0, 0)

    def update(self, rig_state: 'RigState') -> Vec2:
        """Returns the delta to apply this frame"""
        p = self.progress()
        current_offset = self.target_offset * p
        delta = current_offset - self.last_offset
        self.last_offset = current_offset
        return delta
