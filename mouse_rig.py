"""
Talon Mouse Rig - Continuous motion-based mouse control system (PRD 5)

A fluent, stateful mouse control API with:
- Continuous movement (direction + speed)
- Smooth transitions with easing
- Rate-based and time-based changes
- Temporary effects with lifecycle (.over()/.hold()/.revert())
- Named effects (modifiers) and forces (independent entities)
- Acceleration-based movement
- Position control (glides)
- State management and baking

Core Properties:
    rig.speed      # Speed scalar
    rig.accel      # Acceleration scalar
    rig.direction  # Direction vector
    rig.pos        # Position

Basic Usage:
    rig = actions.user.mouse_rig()
    rig.direction(1, 0)          # Set direction (right)
    rig.speed(10)                # Set base speed
    rig.speed.to(20).over(500)   # Ramp to 20 over 500ms

Value Modifiers:
    .to(value)      # Set to absolute value
    .by(delta)      # Add/subtract relative value
    .mul(factor)    # Multiply by factor
    .div(divisor)   # Divide by divisor

Timing:
    Time-based:
        .over(duration, easing?)  # Animate over fixed duration

    Rate-based (no easing, constant rate):
        .rate(value)              # Context-aware rate
        .rate.accel(value)        # Via acceleration
        .rate.speed(value)        # Via speed (position only)

Temporary Effects (auto-remove after lifecycle):
    .over(duration)                # Fade in over duration
    .hold(duration)                # Maintain for duration
    .revert(duration?, easing?)    # Revert to original

    Examples:
        rig.speed.mul(2).revert(500)                     # Instant apply, revert over 500ms
        rig.speed.mul(2).hold(1000)                      # Hold 1s, instant revert
        rig.speed.mul(2).over(300).hold(1000).revert(500) # Fade in, hold, fade out

Named Modifiers (relative changes to base, stoppable):
    rig.modifier("boost").speed.mul(2)              # Multiply base by 2
    rig.modifier("boost").stop()                    # Immediate stop
    rig.modifier("boost").stop(500, "ease_out")     # Fade out over 500ms
    rig.modifier.stop_all()                         # Stop all modifiers

    Constraints: Only .mul(), .by(), .div() allowed
    Modifiers recalculate when base changes

Named Forces (independent entities, absolute values only):
    rig.force("wind").speed(5)                      # Set force speed
    rig.force("wind").direction(0, 1)               # Set force direction
    rig.force("gravity").accel(9.8)                 # Set force acceleration
    rig.force("wind").stop(500)                     # Fade out over 500ms
    rig.force.stop_all()                            # Stop all forces

    Constraints: Only .to() or direct setters allowed
    Forces remain constant regardless of base changes

State Management:
    rig.state.speed       # Computed speed (base + modifiers)
    rig.state.accel       # Computed acceleration
    rig.state.direction   # Current direction
    rig.state.pos         # Current position
    rig.state.velocity    # Total velocity vector

    rig.base.speed        # Base speed only
    rig.base.accel        # Base acceleration only
    rig.base.direction    # Base direction only

Baking & Stopping:
    rig.bake()                      # Flatten modifiers into base, clear all
    rig.stop()                      # Bake, clear, speed=0 (instant)
    rig.stop(500, "ease_out")       # Bake, clear, decelerate over 500ms

Lambda Support:
    rig.speed.by(lambda state: state.speed * 0.5).revert(1000)  # +50% boost

Direction:
    rig.direction(1, 0)              # Right
    rig.direction(0, 1)              # Down
    rig.direction(-1, -1)            # Up-left diagonal
    rig.direction(1, 0).over(500)    # Smooth rotation
    rig.direction(1, 0).rate(90)     # Rotate at 90°/sec
    rig.reverse()                    # 180° turn

Position:
    rig.pos.to(100, 200)             # Instant move
    rig.pos.to(100, 200).over(1000)  # Glide over 1s
    rig.pos.by(50, 0)                # Move by offset

Complete Examples:
    # Speed boost pad
    rig.speed.mul(1.5).hold(2000).revert(1000)

    # Thrust control (repeatable)
    rig.force("thrust").accel(10)             # Key down
    rig.force("thrust").stop(2000)            # Key up

    # Gravity
    rig.force("gravity").speed(9.8).direction(0, 1)
    rig.force("gravity").stop(500)

    # Dynamic boost based on current speed
    rig.speed.by(lambda state: state.speed * 0.5).revert(1000)
"""

from talon import Module, actions, ctrl, cron, settings, app
from typing import Tuple, Literal, Optional, Callable, Union
from dataclasses import dataclass
import math
import time
import platform

mod = Module()

# Settings
mod.setting(
    "mouse_rig_frame_interval",
    type=int,
    default=16,
    desc="Frame interval in milliseconds (default 16ms = ~60fps)"
)
mod.setting(
    "mouse_rig_max_speed",
    type=float,
    default=15.0,
    desc="Default maximum speed limit (pixels per frame)"
)
mod.setting(
    "mouse_rig_epsilon",
    type=float,
    default=0.01,
    desc="Epsilon for floating point comparisons"
)
mod.setting(
    "mouse_rig_default_turn_rate",
    type=float,
    default=180.0,
    desc="Default turn rate in degrees per second (used with .rate() without args)"
)
mod.setting(
    "mouse_rig_movement_type",
    type=str,
    default="talon",
    desc="Mouse movement type: 'talon' (ctrl.mouse_move) or 'windows_raw' (win32api.mouse_event)"
)
mod.setting(
    "mouse_rig_scale",
    type=float,
    default=1.0,
    desc="Movement scale multiplier (1.0 = normal, 2.0 = double speed/distance, 0.5 = half speed/distance)"
)

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
    """Initialize the mouse move function based on settings"""
    global _mouse_move
    movement_type = settings.get("user.mouse_rig_movement_type", "talon")
    if movement_type == "windows_raw" and _windows_raw_available:
        _mouse_move = _make_windows_raw_mouse_move()
    else:
        _mouse_move = _make_talon_mouse_move()

app.register("ready", _initialize_mouse_move)

# ============================================================================
# UTILITIES
# ============================================================================

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
        if mag < 1e-10:
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
    if mag < 1e-10:
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
        """
        Convert float deltas to integer pixels while tracking fractional error.

        Returns:
            (dx_int, dy_int): Integer pixel deltas to apply this frame
        """
        # Accumulate fractional movement
        self.x_frac += dx
        self.y_frac += dy

        # Extract integer part (floor towards zero)
        dx_int = int(self.x_frac)
        dy_int = int(self.y_frac)

        # Keep the fractional remainder for next frame
        self.x_frac -= dx_int
        self.y_frac -= dy_int

        return dx_int, dy_int


# Easing functions
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
    """Transition for direction changes over time (shortest arc)"""
    def __init__(self, start_dir: Vec2, target_dir: Vec2, duration_ms: float, easing: str = "linear"):
        super().__init__(duration_ms, easing)
        self.start_dir = start_dir
        self.target_dir = target_dir

        # Calculate angle for shortest arc interpolation
        dot = start_dir.dot(target_dir)
        dot = clamp(dot, -1.0, 1.0)
        self.angle = math.acos(dot)

        # Determine rotation direction using cross product
        cross = start_dir.x * target_dir.y - start_dir.y * target_dir.x
        self.direction = 1 if cross >= 0 else -1

    def update(self, rig_state: 'RigState') -> None:
        p = self.progress()

        if self.angle < 1e-6:
            # Already at target
            rig_state._direction = self.target_dir
            return

        # Slerp for smooth rotation
        current_angle = self.angle * p * self.direction

        # Rotate start_dir by current_angle
        cos_a = math.cos(current_angle)
        sin_a = math.sin(current_angle)

        new_x = self.start_dir.x * cos_a - self.start_dir.y * sin_a
        new_y = self.start_dir.x * sin_a + self.start_dir.y * cos_a

        rig_state._direction = Vec2(new_x, new_y).normalized()


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


# ============================================================================
# EFFECT SYSTEM (temporary property modifications with lifecycle)
# ============================================================================

class Effect:
    """
    Represents a temporary property modification with lifecycle phases.

    Effects have three optional phases:
    - in: fade in the effect value over duration
    - hold: maintain the effect value for duration
    - out: fade out the effect value over duration

    Effects auto-remove when their lifecycle completes.
    """
    def __init__(self,
                 property_name: str,  # "speed" or "accel"
                 operation: str,      # "to", "by", "mul", "div"
                 value: float,
                 name: Optional[str] = None):
        self.property_name = property_name
        self.operation = operation
        self.value = value
        self.name = name  # Optional name for stopping early

        # Lifecycle configuration
        self.in_duration_ms: Optional[float] = None
        self.in_easing: str = "linear"
        self.hold_duration_ms: Optional[float] = None
        self.out_duration_ms: Optional[float] = None
        self.out_easing: str = "linear"

        # Runtime state
        self.phase: str = "not_started"  # "in", "hold", "out", "complete"
        self.phase_start_time: Optional[float] = None
        self.base_value: Optional[float] = None  # Value before effect was applied
        self.current_multiplier: float = 0.0  # 0 to 1, how much of the effect is active
        self.complete = False

        # For stopping
        self.stop_requested = False
        self.stop_duration_ms: Optional[float] = None
        self.stop_easing: str = "linear"
        self.stop_start_time: Optional[float] = None

    def start(self, current_value: float) -> None:
        """Start the effect lifecycle"""
        self.base_value = current_value

        if self.in_duration_ms is not None:
            self.phase = "in"
            self.phase_start_time = time.perf_counter()
        elif self.hold_duration_ms is not None:
            self.phase = "hold"
            self.phase_start_time = time.perf_counter()
            self.current_multiplier = 1.0
        elif self.out_duration_ms is not None:
            # Start at full strength if only out phase
            self.phase = "out"
            self.phase_start_time = time.perf_counter()
            self.current_multiplier = 1.0
        else:
            # No lifecycle specified
            if self.name:
                # Named modifiers without lifecycle persist indefinitely at full strength
                self.phase = "hold"
                self.current_multiplier = 1.0
            else:
                # Unnamed effects without lifecycle complete immediately
                self.phase = "complete"
                self.complete = True

    def update(self, current_base_value: float) -> float:
        """
        Update effect and return the modified value.

        Args:
            current_base_value: The current base value of the property (without this effect)

        Returns:
            The modified value with this effect applied
        """
        if self.complete:
            return current_base_value

        # Handle stop request
        if self.stop_requested:
            return self._update_stop(current_base_value)

        # Normal lifecycle progression
        current_time = time.perf_counter()
        elapsed_ms = (current_time - self.phase_start_time) * 1000 if self.phase_start_time else 0

        if self.phase == "in":
            if elapsed_ms >= self.in_duration_ms:
                # Move to next phase
                self.current_multiplier = 1.0
                if self.hold_duration_ms is not None:
                    self.phase = "hold"
                    self.phase_start_time = current_time
                elif self.out_duration_ms is not None:
                    self.phase = "out"
                    self.phase_start_time = current_time
                else:
                    self.phase = "complete"
                    self.complete = True
                    return current_base_value
            else:
                # Update multiplier with easing
                t = elapsed_ms / self.in_duration_ms
                easing_fn = EASING_FUNCTIONS.get(self.in_easing, ease_linear)
                self.current_multiplier = easing_fn(t)

        elif self.phase == "hold":
            # Check if we have a duration specified
            if self.hold_duration_ms is not None:
                if elapsed_ms >= self.hold_duration_ms:
                    # Move to next phase
                    if self.out_duration_ms is not None:
                        self.phase = "out"
                        self.phase_start_time = current_time
                    else:
                        self.phase = "complete"
                        self.complete = True
                        return current_base_value
            # else: persist indefinitely at full strength (named modifiers without timing)
            # Multiplier stays at 1.0 during hold

        elif self.phase == "out":
            if elapsed_ms >= self.out_duration_ms:
                self.phase = "complete"
                self.complete = True
                return current_base_value
            else:
                # Fade out
                t = elapsed_ms / self.out_duration_ms
                easing_fn = EASING_FUNCTIONS.get(self.out_easing, ease_linear)
                self.current_multiplier = 1.0 - easing_fn(t)

        # Apply effect based on operation and current multiplier
        return self._apply_effect(current_base_value)

    def _apply_effect(self, base_value: float) -> float:
        """Apply the effect to the base value based on operation and multiplier"""
        if self.current_multiplier == 0.0:
            return base_value

        if self.operation == "to":
            # Interpolate from base to target
            return lerp(base_value, self.value, self.current_multiplier)

        elif self.operation == "by":
            # Add offset scaled by multiplier
            return base_value + (self.value * self.current_multiplier)

        elif self.operation == "mul":
            # Multiply: lerp from 1.0 to factor
            factor = lerp(1.0, self.value, self.current_multiplier)
            return base_value * factor

        elif self.operation == "div":
            # Divide: lerp from 1.0 to 1/divisor
            divisor = lerp(1.0, self.value, self.current_multiplier)
            if divisor != 0:
                return base_value / divisor
            return base_value

        return base_value

    def _update_stop(self, current_base_value: float) -> float:
        """Handle graceful stop with optional duration"""
        if self.stop_duration_ms is None or self.stop_duration_ms == 0:
            # Immediate stop
            self.complete = True
            return current_base_value

        # Graceful stop over duration
        if self.stop_start_time is None:
            self.stop_start_time = time.perf_counter()

        elapsed_ms = (time.perf_counter() - self.stop_start_time) * 1000
        if elapsed_ms >= self.stop_duration_ms:
            self.complete = True
            return current_base_value

        # Fade out the current multiplier (from 1.0 to 0.0)
        t = elapsed_ms / self.stop_duration_ms
        easing_fn = EASING_FUNCTIONS.get(self.stop_easing, ease_linear)
        self.current_multiplier = 1.0 - easing_fn(t)

        return self._apply_effect(current_base_value)

    def request_stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Request the effect to stop, optionally over a duration"""
        self.stop_requested = True
        self.stop_duration_ms = duration_ms if duration_ms is not None else 0
        self.stop_easing = easing


# ============================================================================
# FORCE SYSTEM (independent entities with vector addition)
# ============================================================================

class Force:
    """
    Independent entity with its own speed, acceleration, and direction.
    Forces combine with base rig via vector addition.
    """
    def __init__(self, name: str, rig_state: 'RigState'):
        self.name = name
        self.rig_state = rig_state

        # Force properties - default to rig's current direction
        self._speed = 0.0
        self._accel = 0.0
        self._direction = rig_state._direction  # Inherit rig's direction

        # Integrated velocity from acceleration
        self._velocity = 0.0

        # Stopping state
        self.stop_requested = False
        self.stop_duration_ms: Optional[float] = None
        self.stop_easing = "linear"
        self.stop_start_time: Optional[float] = None
        self.stop_initial_speed = 0.0
        self.stop_initial_velocity = 0.0
        self.complete = False

    def update(self, dt: float) -> Vec2:
        """
        Update force and return its velocity vector contribution.

        Args:
            dt: Delta time in seconds

        Returns:
            Velocity vector from this force
        """
        if self.complete:
            return Vec2(0, 0)

        # Handle stop request
        if self.stop_requested:
            return self._update_stop(dt)

        # Integrate acceleration into velocity
        if abs(self._accel) > 1e-6:
            self._velocity += self._accel * dt

        # Total speed is base speed + integrated velocity
        total_speed = self._speed + self._velocity

        # Return velocity vector
        return self._direction * total_speed

    def _update_stop(self, dt: float) -> Vec2:
        """Handle gradual stopping of the force"""
        if self.stop_duration_ms is None or self.stop_duration_ms == 0:
            # Immediate stop
            self.complete = True
            return Vec2(0, 0)

        # Initialize stop
        if self.stop_start_time is None:
            self.stop_start_time = time.perf_counter()
            self.stop_initial_speed = self._speed
            self.stop_initial_velocity = self._velocity

        elapsed_ms = (time.perf_counter() - self.stop_start_time) * 1000

        if elapsed_ms >= self.stop_duration_ms:
            self.complete = True
            return Vec2(0, 0)

        # Fade out both speed and velocity
        t = elapsed_ms / self.stop_duration_ms
        easing_fn = EASING_FUNCTIONS.get(self.stop_easing, ease_linear)
        multiplier = 1.0 - easing_fn(t)

        current_speed = self.stop_initial_speed * multiplier
        current_velocity = self.stop_initial_velocity * multiplier
        total_speed = current_speed + current_velocity

        return self._direction * total_speed

    def request_stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Request the force to stop, optionally over a duration"""
        self.stop_requested = True
        self.stop_duration_ms = duration_ms if duration_ms is not None else 0
        self.stop_easing = easing


# ============================================================================
# BUILDER CLASSES (for fluent API)
# ============================================================================

class SpeedBuilder:
    """Builder for speed operations with .over() support"""
    def __init__(self, rig_state: 'RigState', target_speed: float, instant: bool = False):
        self.rig_state = rig_state
        self.target_speed = target_speed
        self._easing = "linear"
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._duration_ms: Optional[float] = None
        self._wait_duration_ms: Optional[float] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Ignore errors during cleanup

    def _execute(self):
        """Execute the configured operation"""
        if self._duration_ms is not None:
            # Create transition with all configured options
            transition = SpeedTransition(
                self.rig_state._speed,
                self.target_speed,
                self._duration_ms,
                self._easing
            )
            self.rig_state.start()  # Ensure ticking is active
            self.rig_state._speed_transition = transition
            self.rig_state._brake_transition = None  # Cancel any active brake

            # Register callback with transition if set
            if self._then_callback:
                transition.on_complete = self._then_callback
        elif self._should_execute_instant:
            # Instant execution
            # Clamp speed to valid range
            value = max(0.0, self.target_speed)
            max_speed = self.rig_state.limits_max_speed
            if max_speed is not None:
                value = min(value, max_speed)

            self.rig_state._speed = value
            self.rig_state._speed_transition = None
            self.rig_state._brake_transition = None

            # Execute callback immediately or after wait duration
            if self._wait_duration_ms is not None and self._then_callback:
                # Wait for duration, then execute callback
                job = cron.after(f"{self._wait_duration_ms}ms", self._then_callback)
                self.rig_state._pending_wait_jobs.append(job)
            elif self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float) -> 'SpeedBuilder':
        """Ramp to target speed over time"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant change with delay: rig.speed(10).wait(500).then(callback)\n"
                "  - For transition over time: rig.speed(10).over(500).then(callback)"
            )
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        return self

    def wait(self, duration_ms: float) -> 'SpeedBuilder':
        """Set speed immediately and wait for duration before executing .then() callback"""
        if self._duration_ms is not None:
            raise ValueError(
                "Cannot use .wait() after .over() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant change with delay: rig.speed(10).wait(500).then(callback)\n"
                "  - For transition over time: rig.speed(10).over(500).then(callback)"
            )
        self._wait_duration_ms = duration_ms
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'SpeedBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def then(self, callback: Callable) -> 'SpeedBuilder':
        """Execute callback after speed change completes"""
        self._then_callback = callback
        return self


class SpeedAdjustBuilder:
    """Builder for speed.add() and speed.subtract() operations"""
    def __init__(self, rig_state: 'RigState', delta: float, instant: bool = False):
        self.rig_state = rig_state
        self.delta = delta
        self._easing = "linear"
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._duration_ms: Optional[float] = None
        self._wait_duration_ms: Optional[float] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Ignore errors during cleanup

    def _execute(self):
        """Execute the configured operation"""
        if self._duration_ms is not None:
            # Create transition with all configured options
            current_speed = self.rig_state._speed
            target_speed = current_speed + self.delta

            # Clamp to limits (speed must be non-negative)
            target_speed = max(0.0, target_speed)
            max_speed = self.rig_state.limits_max_speed
            if max_speed is not None:
                target_speed = min(target_speed, max_speed)

            transition = SpeedTransition(
                current_speed,
                target_speed,
                self._duration_ms,
                self._easing
            )
            self.rig_state.start()  # Ensure ticking is active
            self.rig_state._speed_transition = transition
            self.rig_state._brake_transition = None

            # Register callback with transition if set
            if self._then_callback:
                transition.on_complete = self._then_callback
        elif self._should_execute_instant:
            # Instant execution
            current_speed = self.rig_state._speed
            new_speed = current_speed + self.delta
            new_speed = max(0.0, new_speed)

            max_speed = self.rig_state.limits_max_speed
            if max_speed is not None:
                new_speed = min(new_speed, max_speed)

            self.rig_state._speed = new_speed

            # Execute callback immediately or after wait duration
            if self._wait_duration_ms is not None and self._then_callback:
                # Wait for duration, then execute callback
                job = cron.after(f"{self._wait_duration_ms}ms", self._then_callback)
                self.rig_state._pending_wait_jobs.append(job)
            elif self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float) -> 'SpeedAdjustBuilder':
        """Ramp by delta over time"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant adjustment with delay: rig.speed.add(5).wait(500).then(callback)\n"
                "  - For transition over time: rig.speed.add(5).over(500).then(callback)"
            )
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        return self

    def wait(self, duration_ms: float) -> 'SpeedAdjustBuilder':
        """Apply adjustment immediately and wait for duration before executing .then() callback"""
        if self._duration_ms is not None:
            raise ValueError(
                "Cannot use .wait() after .over() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant adjustment with delay: rig.speed.add(5).wait(500).then(callback)\n"
                "  - For transition over time: rig.speed.add(5).over(500).then(callback)"
            )
        self._wait_duration_ms = duration_ms
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'SpeedAdjustBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def then(self, callback: Callable) -> 'SpeedAdjustBuilder':
        """Execute callback after speed adjustment completes"""
        self._then_callback = callback
        return self


class SpeedMultiplyBuilder:
    """Builder for speed.multiply() operations"""
    def __init__(self, rig_state: 'RigState', factor: float, instant: bool = False):
        self.rig_state = rig_state
        self.factor = factor
        self._easing = "linear"
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._duration_ms: Optional[float] = None
        self._wait_duration_ms: Optional[float] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Ignore errors during cleanup

    def _execute(self):
        """Execute the configured operation"""
        if self._duration_ms is not None:
            # Create transition with all configured options
            current_speed = self.rig_state._speed
            target_speed = current_speed * self.factor

            # Clamp to limits (speed must be non-negative)
            target_speed = max(0.0, target_speed)
            max_speed = self.rig_state.limits_max_speed
            if max_speed is not None:
                target_speed = min(target_speed, max_speed)

            transition = SpeedTransition(
                current_speed,
                target_speed,
                self._duration_ms,
                self._easing
            )
            self.rig_state.start()  # Ensure ticking is active
            self.rig_state._speed_transition = transition
            self.rig_state._brake_transition = None

            # Register callback with transition if set
            if self._then_callback:
                transition.on_complete = self._then_callback
        elif self._should_execute_instant:
            # Instant execution
            current_speed = self.rig_state._speed
            new_speed = current_speed * self.factor
            new_speed = max(0.0, new_speed)

            max_speed = self.rig_state.limits_max_speed
            if max_speed is not None:
                new_speed = min(new_speed, max_speed)

            self.rig_state._speed = new_speed

            # Execute callback immediately or after wait duration
            if self._wait_duration_ms is not None and self._then_callback:
                # Wait for duration, then execute callback
                job = cron.after(f"{self._wait_duration_ms}ms", self._then_callback)
                self.rig_state._pending_wait_jobs.append(job)
            elif self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float) -> 'SpeedMultiplyBuilder':
        """Ramp to multiplied speed over time"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant multiplication with delay: rig.speed.multiply(2).wait(500).then(callback)\n"
                "  - For transition over time: rig.speed.multiply(2).over(500).then(callback)"
            )
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        return self

    def wait(self, duration_ms: float) -> 'SpeedMultiplyBuilder':
        """Apply multiplication immediately and wait for duration before executing .then() callback"""
        if self._duration_ms is not None:
            raise ValueError(
                "Cannot use .wait() after .over() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant multiplication with delay: rig.speed.multiply(2).wait(500).then(callback)\n"
                "  - For transition over time: rig.speed.multiply(2).over(500).then(callback)"
            )
        self._wait_duration_ms = duration_ms
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'SpeedMultiplyBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def then(self, callback: Callable) -> 'SpeedMultiplyBuilder':
        """Execute callback after speed multiply completes"""
        self._then_callback = callback
        return self


class SpeedDivideBuilder:
    """Builder for speed.divide() operations"""
    def __init__(self, rig_state: 'RigState', divisor: float, instant: bool = False):
        self.rig_state = rig_state
        self.divisor = divisor
        self._easing = "linear"
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._duration_ms: Optional[float] = None
        self._wait_duration_ms: Optional[float] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Ignore errors during cleanup

    def _execute(self):
        """Execute the configured operation"""
        if self._duration_ms is not None:
            # Create transition with all configured options
            current_speed = self.rig_state._speed

            if abs(self.divisor) < 1e-10:
                raise ValueError("Cannot divide speed by zero")

            target_speed = current_speed / self.divisor

            # Clamp to limits (speed must be non-negative)
            target_speed = max(0.0, target_speed)
            max_speed = self.rig_state.limits_max_speed
            if max_speed is not None:
                target_speed = min(target_speed, max_speed)

            transition = SpeedTransition(
                current_speed,
                target_speed,
                self._duration_ms,
                self._easing
            )
            self.rig_state.start()  # Ensure ticking is active
            self.rig_state._speed_transition = transition
            self.rig_state._brake_transition = None

            # Register callback with transition if set
            if self._then_callback:
                transition.on_complete = self._then_callback
        elif self._should_execute_instant:
            # Instant execution
            if abs(self.divisor) < 1e-10:
                return  # Silently ignore division by zero during cleanup

            current_speed = self.rig_state._speed
            new_speed = current_speed / self.divisor
            new_speed = max(0.0, new_speed)

            max_speed = self.rig_state.limits_max_speed
            if max_speed is not None:
                new_speed = min(new_speed, max_speed)

            self.rig_state._speed = new_speed

            # Execute callback immediately or after wait duration
            if self._wait_duration_ms is not None and self._then_callback:
                # Wait for duration, then execute callback
                job = cron.after(f"{self._wait_duration_ms}ms", self._then_callback)
                self.rig_state._pending_wait_jobs.append(job)
            elif self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float) -> 'SpeedDivideBuilder':
        """Ramp to divided speed over time"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant division with delay: rig.speed.divide(2).wait(500).then(callback)\n"
                "  - For transition over time: rig.speed.divide(2).over(500).then(callback)"
            )
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        return self

    def wait(self, duration_ms: float) -> 'SpeedDivideBuilder':
        """Apply division immediately and wait for duration before executing .then() callback"""
        if self._duration_ms is not None:
            raise ValueError(
                "Cannot use .wait() after .over() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant division with delay: rig.speed.divide(2).wait(500).then(callback)\n"
                "  - For transition over time: rig.speed.divide(2).over(500).then(callback)"
            )
        self._wait_duration_ms = duration_ms
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'SpeedDivideBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def then(self, callback: Callable) -> 'SpeedDivideBuilder':
        """Execute callback after speed divide completes"""
        self._then_callback = callback
        return self


class SpeedController:
    """Controller for speed operations (accessed via rig.speed)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, value: float) -> SpeedBuilder:
        """Set speed instantly or return builder for .over()"""
        return SpeedBuilder(self.rig_state, value, instant=True)

    def add(self, delta: float) -> SpeedAdjustBuilder:
        """Add to current speed (legacy - use .by() for new code)"""
        return SpeedAdjustBuilder(self.rig_state, delta, instant=True)

    def subtract(self, delta: float) -> SpeedAdjustBuilder:
        """Subtract from current speed (legacy - use .by() with negative for new code)"""
        return self.add(-delta)

    def sub(self, delta: float) -> SpeedAdjustBuilder:
        """Subtract from current speed (shorthand for subtract)"""
        return self.subtract(delta)

    def multiply(self, factor: float) -> SpeedMultiplyBuilder:
        """Multiply current speed by factor (legacy - use .mul() for new code)"""
        return SpeedMultiplyBuilder(self.rig_state, factor, instant=True)

    def mul(self, factor: float) -> 'PropertyEffectBuilder':
        """Multiply speed by factor (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "mul", factor)

    def divide(self, divisor: float) -> SpeedDivideBuilder:
        """Divide current speed by divisor (legacy - use .div() for new code)"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide speed by zero")

        return SpeedDivideBuilder(self.rig_state, divisor, instant=True)

    def div(self, divisor: float) -> 'PropertyEffectBuilder':
        """Divide speed by divisor (can use with .over(), .hold(), .revert())"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide speed by zero")
        return PropertyEffectBuilder(self.rig_state, "speed", "div", divisor)

    def to(self, value: float) -> 'PropertyEffectBuilder':
        """Set speed to absolute value (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "to", value)

    def by(self, delta: float) -> 'PropertyEffectBuilder':
        """Add delta to speed (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", delta)


class AccelController:
    """Controller for acceleration operations (accessed via rig.accel)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, value: float) -> 'PropertyEffectBuilder':
        """Set acceleration instantly or return builder for transitions/effects"""
        # Immediate set
        self.rig_state._accel = value
        self.rig_state.start()
        return PropertyEffectBuilder(self.rig_state, "accel", "to", value, instant_done=True)

    def to(self, value: float) -> 'PropertyEffectBuilder':
        """Set accel to absolute value (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "accel", "to", value)

    def by(self, delta: float) -> 'PropertyEffectBuilder':
        """Add delta to accel (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "accel", "by", delta)

    def mul(self, factor: float) -> 'PropertyEffectBuilder':
        """Multiply accel by factor (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "accel", "mul", factor)

    def div(self, divisor: float) -> 'PropertyEffectBuilder':
        """Divide accel by divisor (can use with .over(), .hold(), .revert())"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide accel by zero")
        return PropertyEffectBuilder(self.rig_state, "accel", "div", divisor)


class PropertyEffectBuilder:
    """
    Universal builder for property effects supporting both permanent (.over())
    and temporary (.revert()/.hold()) modifications.

    Supports lambda values for dynamic calculation at execution time.
    """
    def __init__(self, rig_state: 'RigState', property_name: str, operation: str, value: Union[float, Callable], instant_done: bool = False):
        self.rig_state = rig_state
        self.property_name = property_name  # "speed" or "accel"
        self.operation = operation  # "to", "by", "mul", "div"
        self.value = value  # Can be float or callable
        self._instant_done = instant_done  # Already executed immediately

        # Timing configuration
        self._in_duration_ms: Optional[float] = None
        self._hold_duration_ms: Optional[float] = None
        self._out_duration_ms: Optional[float] = None
        self._in_easing: str = "linear"
        self._out_easing: str = "linear"

        # Named modifier
        self._effect_name: Optional[str] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass

    def _execute(self):
        """Execute the configured operation"""
        if self._instant_done:
            return  # Already executed

        # Determine if this is permanent or temporary
        # Temporary = has .revert() or .hold() specified OR is a named modifier
        is_temporary = (self._hold_duration_ms is not None or
                       self._out_duration_ms is not None or
                       self._effect_name is not None)

        if self._in_duration_ms is not None and not is_temporary:
            # Permanent transition over time (just .over() without .hold()/.revert())
            if self.property_name == "speed":
                current = self.rig_state._speed
                target = self._calculate_target_value(current)
                transition = SpeedTransition(current, target, self._in_duration_ms, self._in_easing)
                self.rig_state.start()
                self.rig_state._speed_transition = transition
            # TODO: Add accel transition if needed

        elif is_temporary:
            # Create and register temporary effect
            effect = Effect(self.property_name, self.operation, self.value, self._effect_name)
            effect.in_duration_ms = self._in_duration_ms  # Can be None for instant application
            effect.in_easing = self._in_easing
            effect.hold_duration_ms = self._hold_duration_ms

            # PRD5: .hold() alone implies instant revert after hold period
            if self._hold_duration_ms is not None and self._out_duration_ms is None:
                effect.out_duration_ms = 0
            else:
                effect.out_duration_ms = self._out_duration_ms
            effect.out_easing = self._out_easing

            self.rig_state.start()
            self.rig_state._effects.append(effect)

            # Track named modifier
            if self._effect_name:
                # Remove any existing modifier with same name
                if self._effect_name in self.rig_state._named_modifiers:
                    old_effect = self.rig_state._named_modifiers[self._effect_name]
                    if old_effect in self.rig_state._effects:
                        self.rig_state._effects.remove(old_effect)
                self.rig_state._named_modifiers[self._effect_name] = effect
        else:
            # Immediate execution (no timing specified)
            if self.property_name == "speed":
                current = self.rig_state._speed
                target = self._calculate_target_value(current)
                self.rig_state._speed = max(0.0, target)
            elif self.property_name == "accel":
                current = self.rig_state._accel
                target = self._calculate_target_value(current)
                self.rig_state._accel = target

    def _calculate_target_value(self, current: float) -> float:
        """Calculate the target value based on operation

        Evaluates lambda functions at execution time with current state.
        """
        # Evaluate value if it's a callable (lambda)
        value = self.value
        if callable(value):
            # Pass StateAccessor to lambda for dynamic calculations
            if not hasattr(self.rig_state, '_state_accessor'):
                self.rig_state._state_accessor = StateAccessor(self.rig_state)
            value = value(self.rig_state._state_accessor)

        if self.operation == "to":
            return value
        elif self.operation == "by":
            return current + value
        elif self.operation == "mul":
            return current * value
        elif self.operation == "div":
            if abs(value) > 1e-10:
                return current / value
            return current
        return current

    def over(self, duration_ms: float, easing: str = "linear") -> 'PropertyEffectBuilder':
        """Apply change over duration - can be permanent or temporary based on .revert()/.hold()"""
        # Check if this is a temporary effect (has hold or revert)
        # We'll set _in_duration_ms which will be checked in _execute
        self._in_duration_ms = duration_ms
        self._in_easing = easing
        return self

    def hold(self, duration_ms: float) -> 'PropertyEffectBuilder':
        """Hold effect at full strength for duration"""
        self._hold_duration_ms = duration_ms
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'PropertyEffectBuilder':
        """Revert to original value - instant if duration=0, gradual otherwise"""
        self._out_duration_ms = duration_ms if duration_ms > 0 else 0
        self._out_easing = easing
        return self

    def rate(self, value: float = None) -> Union['PropertyEffectBuilder', 'PropertyRateNamespace']:
        """Change at specified rate or access rate namespace

        If value provided: context-aware rate (speed->speed/sec, accel->accel/sec²)
        If no value: returns namespace for .rate.speed(), .rate.accel()

        Examples:
            rig.speed.to(50).rate(10)         # Increase speed at 10/sec
            rig.speed.to(50).rate.accel(10)   # Accelerate at 10/sec² until reaching 50
        """
        if value is None:
            # Return namespace for .rate.speed(), .rate.accel()
            return PropertyRateNamespace(self)

        # Context-aware rate
        current = None
        target = None

        if self.property_name == "speed":
            current = self.rig_state._speed
            target = self._calculate_target_value(current)
        elif self.property_name == "accel":
            current = self.rig_state._accel
            target = self._calculate_target_value(current)
        else:
            raise ValueError(f".rate() not valid for {self.property_name}")

        delta = abs(target - current)
        if delta < 0.01:
            duration_ms = 1
        else:
            duration_sec = delta / value
            duration_ms = duration_sec * 1000

        self._in_duration_ms = duration_ms
        self._in_easing = "linear"  # Rate-based uses linear
        return self

    def __getattr__(self, name: str):
        """Provide helpful error messages for invalid chaining attempts"""
        # Common rig properties that can't be chained
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Don't allow chaining properties from effect builders
            raise AttributeError(_error_cannot_chain_property(f'{self.property_name} effect', name))
        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after {self.property_name} effect.\n\n"
                "Instead, use separate statements."
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute(
            f'{self.property_name.capitalize()}EffectBuilder',
            name,
            'over, hold, revert, rate'
        ))


class PropertyRateNamespace:
    """Namespace for rate-based timing on properties"""
    def __init__(self, builder: 'PropertyEffectBuilder'):
        self._builder = builder

    def speed(self, value: float) -> 'PropertyEffectBuilder':
        """Change at specified speed rate (units/sec)

        Only valid for position changes.
        """
        if self._builder.property_name == "position":
            # Calculate duration based on distance / speed
            # TODO: Implement position rate logic
            pass
        else:
            raise ValueError(f".rate.speed() only valid for position, not {self._builder.property_name}")
        return self._builder

    def accel(self, value: float) -> 'PropertyEffectBuilder':
        """Change via acceleration rate (units/sec²)

        For speed: accelerate/decelerate at specified rate until reaching target
        For accel: change acceleration at specified rate (jerk)
        """
        if self._builder.property_name == "speed":
            # v = at, so t = v/a
            current = self._builder.rig_state._speed
            target = self._builder._calculate_target_value(current)
            delta = abs(target - current)

            if delta < 0.01:
                duration_ms = 1  # Minimal duration
            else:
                duration_sec = delta / value
                duration_ms = duration_sec * 1000

            self._builder._in_duration_ms = duration_ms
            self._builder._in_easing = "linear"  # Rate-based uses linear

        elif self._builder.property_name == "accel":
            # Jerk (rate of acceleration change)
            current = self._builder.rig_state._accel
            target = self._builder._calculate_target_value(current)
            delta = abs(target - current)

            if delta < 0.01:
                duration_ms = 1
            else:
                duration_sec = delta / value
                duration_ms = duration_sec * 1000

            self._builder._in_duration_ms = duration_ms
            self._builder._in_easing = "linear"
        else:
            raise ValueError(f".rate.accel() not valid for {self._builder.property_name}")

        return self._builder


class DirectionBuilder:
    """Builder for direction operations with .over() support"""
    def __init__(self, rig_state: 'RigState', target_direction: Vec2, instant: bool = False):
        self.rig_state = rig_state
        self.target_direction = target_direction.normalized()
        self._easing = "linear"
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._duration_ms: Optional[float] = None
        self._use_rate: bool = False
        self._rate_degrees_per_second: Optional[float] = None
        self._wait_duration_ms: Optional[float] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Ignore errors during cleanup

    def _execute(self):
        """Execute the configured operation"""
        if self._duration_ms is not None or self._use_rate:
            # Calculate duration from rate if needed
            duration_ms = self._duration_ms
            if self._use_rate and self._rate_degrees_per_second is not None:
                current_dir = self.rig_state._direction
                dot = current_dir.dot(self.target_direction)
                dot = clamp(dot, -1.0, 1.0)
                angle_rad = math.acos(dot)
                angle_deg = math.degrees(angle_rad)

                if angle_deg < 0.1:
                    duration_ms = 1  # Minimal duration for near-zero turns
                else:
                    duration_sec = angle_deg / self._rate_degrees_per_second
                    duration_ms = duration_sec * 1000

            # Create transition with all configured options
            transition = DirectionTransition(
                self.rig_state._direction,
                self.target_direction,
                duration_ms,
                self._easing
            )
            self.rig_state.start()  # Ensure ticking is active
            self.rig_state._direction_transition = transition

            # Register callback with transition if set
            if self._then_callback:
                transition.on_complete = self._then_callback
        elif self._should_execute_instant:
            # Instant execution
            self.rig_state._direction = self.target_direction
            self.rig_state._direction_transition = None

            # Execute callback immediately or after wait duration
            if self._wait_duration_ms is not None and self._then_callback:
                # Wait for duration, then execute callback
                job = cron.after(f"{self._wait_duration_ms}ms", self._then_callback)
                self.rig_state._pending_wait_jobs.append(job)
            elif self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float, easing: str = "linear") -> 'DirectionBuilder':
        """Rotate to target direction over time

        Args:
            duration_ms: Duration in milliseconds
            easing: Easing function ('linear', 'ease_in', 'ease_out', 'ease_in_out', 'smoothstep')
        """
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant direction change with delay: rig.direction(1, 0).wait(500).then(callback)\n"
                "  - For smooth rotation over time: rig.direction(1, 0).over(500).then(callback)"
            )
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        self._easing = easing
        return self

    def rate(self, degrees_per_second: float) -> 'DirectionBuilder':
        """Rotate to target direction at specified rate (degrees/second)

        Duration is calculated based on angular distance: duration = angle / rate

        Examples:
            rig.direction((0, 1)).rate(90)   # Turn at 90°/s
            rig.direction((-1, 0)).rate(180) # Turn at 180°/s (half revolution per second)
        """
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .rate() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant direction change with delay: rig.direction(1, 0).wait(500).then(callback)\n"
                "  - For smooth rotation at rate: rig.direction(1, 0).rate(180).then(callback)"
            )
        self._should_execute_instant = False
        self._use_rate = True
        self._rate_degrees_per_second = degrees_per_second
        return self

    def wait(self, duration_ms: float) -> 'DirectionBuilder':
        """Set direction immediately and wait for duration before executing .then() callback"""
        if self._duration_ms is not None or self._use_rate:
            raise ValueError(
                "Cannot use .wait() after .over() or .rate() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant direction change with delay: rig.direction(1, 0).wait(500).then(callback)\n"
                "  - For smooth rotation over time: rig.direction(1, 0).over(500).then(callback)\n"
                "  - For smooth rotation at rate: rig.direction(1, 0).rate(180).then(callback)"
            )
        self._wait_duration_ms = duration_ms
        return self

    def then(self, callback: Callable) -> 'DirectionBuilder':
        """Execute callback after direction change completes"""
        self._then_callback = callback
        return self

    def __getattr__(self, name: str):
        """Provide helpful error messages for invalid chaining attempts"""
        # Common rig properties that can't be chained
        if name in ['speed', 'accel', 'pos', 'direction']:
            raise AttributeError(_error_cannot_chain_property('direction', name))
        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after 'direction'.\n\n"
                "Instead, use separate statements:\n"
                "    rig.direction(1, 0)\n"
                "    rig.{name}(...)"
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute('DirectionBuilder', name, 'over, rate, wait, then'))


class DirectionByBuilder:
    """Builder for direction.by(degrees) - relative rotation"""
    def __init__(self, rig_state: 'RigState', degrees: float, instant: bool = False):
        self.rig_state = rig_state
        self.degrees = degrees
        self._easing = "linear"
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._duration_ms: Optional[float] = None
        self._use_rate: bool = False
        self._rate_degrees_per_second: Optional[float] = None
        self._wait_duration_ms: Optional[float] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Ignore errors during cleanup

    def _execute(self):
        """Execute the configured operation"""
        # Calculate target direction from current + degrees
        current_dir = self.rig_state._direction
        angle_rad = math.radians(self.degrees)

        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        new_x = current_dir.x * cos_a - current_dir.y * sin_a
        new_y = current_dir.x * sin_a + current_dir.y * cos_a

        target_direction = Vec2(new_x, new_y).normalized()

        if self._duration_ms is not None or self._use_rate:
            # Calculate duration from rate if needed
            duration_ms = self._duration_ms
            if self._use_rate and self._rate_degrees_per_second is not None:
                angle_deg = abs(self.degrees)
                if angle_deg < 0.1:
                    duration_ms = 1  # Minimal duration for near-zero turns
                else:
                    duration_sec = angle_deg / self._rate_degrees_per_second
                    duration_ms = duration_sec * 1000

            # Create transition
            transition = DirectionTransition(
                self.rig_state._direction,
                target_direction,
                duration_ms,
                self._easing
            )
            self.rig_state.start()
            self.rig_state._direction_transition = transition

            # Register callback
            if self._then_callback:
                transition.on_complete = self._then_callback
        elif self._should_execute_instant:
            # Instant execution
            self.rig_state._direction = target_direction
            self.rig_state._direction_transition = None

            # Execute callback immediately or after wait duration
            if self._wait_duration_ms is not None and self._then_callback:
                job = cron.after(f"{self._wait_duration_ms}ms", self._then_callback)
                self.rig_state._pending_wait_jobs.append(job)
            elif self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float, easing: str = "linear") -> 'DirectionByBuilder':
        """Rotate by degrees over time"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant rotation with delay: rig.direction.by(45).wait(500).then(callback)\n"
                "  - For smooth rotation over time: rig.direction.by(45).over(500).then(callback)"
            )
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        self._easing = easing
        return self

    def rate(self, degrees_per_second: float) -> 'DirectionByBuilder':
        """Rotate by degrees at specified rate"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .rate() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant rotation with delay: rig.direction.by(45).wait(500).then(callback)\n"
                "  - For smooth rotation at rate: rig.direction.by(45).rate(90).then(callback)"
            )
        self._should_execute_instant = False
        self._use_rate = True
        self._rate_degrees_per_second = degrees_per_second
        return self

    def wait(self, duration_ms: float) -> 'DirectionByBuilder':
        """Rotate immediately and wait for duration before executing .then() callback"""
        if self._duration_ms is not None or self._use_rate:
            raise ValueError(
                "Cannot use .wait() after .over() or .rate() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant rotation with delay: rig.direction.by(45).wait(500).then(callback)\n"
                "  - For smooth rotation over time: rig.direction.by(45).over(500).then(callback)\n"
                "  - For smooth rotation at rate: rig.direction.by(45).rate(90).then(callback)"
            )
        self._wait_duration_ms = duration_ms
        return self

    def then(self, callback: Callable) -> 'DirectionByBuilder':
        """Execute callback after rotation completes"""
        self._then_callback = callback
        return self

    def __getattr__(self, name: str):
        """Provide helpful error messages for invalid chaining attempts"""
        if name in ['speed', 'accel', 'pos', 'direction']:
            raise AttributeError(_error_cannot_chain_property('direction.by()', name))
        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after 'direction.by()'.\n\n"
                "Instead, use separate statements."
            )

        raise AttributeError(_error_unknown_builder_attribute('DirectionByBuilder', name, 'over, rate, wait, then'))


class DirectionController:
    """Controller for direction operations (accessed via rig.direction)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, x: float, y: float) -> DirectionBuilder:
        """Set direction instantly or return builder for .over() (legacy shorthand for .to())"""
        return DirectionBuilder(self.rig_state, Vec2(x, y), instant=True)

    def to(self, x: float, y: float) -> DirectionBuilder:
        """Set direction to absolute vector (can use with .over(), .rate(), .wait(), .then())"""
        return DirectionBuilder(self.rig_state, Vec2(x, y), instant=True)

    def by(self, degrees: float) -> DirectionByBuilder:
        """Rotate by relative angle in degrees (can use with .over(), .rate(), .wait(), .then())

        Positive = clockwise, Negative = counter-clockwise

        Examples:
            rig.direction.by(90)              # Rotate 90° clockwise instantly
            rig.direction.by(-45).over(500)   # Rotate 45° counter-clockwise over 500ms
            rig.direction.by(180).rate(90)    # Rotate 180° at 90°/sec
        """
        return DirectionByBuilder(self.rig_state, degrees, instant=True)


class PositionController:
    """Controller for position operations (accessed via rig.pos)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def to(self, x: float, y: float) -> 'PositionToBuilder':
        """Move to absolute position - instant by default, use .over(ms) for smooth glide"""
        return PositionToBuilder(self.rig_state, x, y, instant=True)

    def by(self, dx: float, dy: float) -> 'PositionByBuilder':
        """Move by relative offset - instant by default, use .over(ms) for smooth glide"""
        return PositionByBuilder(self.rig_state, dx, dy, instant=True)


class PositionToBuilder:
    """Builder for pos.to() operations"""
    def __init__(self, rig_state: 'RigState', x: float, y: float, instant: bool = False):
        self.rig_state = rig_state
        self.x = x
        self.y = y
        self._easing = "ease_in_out"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._wait_duration_ms: Optional[float] = None
        self._hold_duration_ms: Optional[float] = None
        self._revert_duration_ms: Optional[float] = None
        self._revert_easing: str = "linear"
        self._original_pos: Optional[Vec2] = None
        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def over(self, duration_ms: float, easing: str = None) -> 'PositionToBuilder':
        """Glide to position over time"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait()\n"
                ".wait() is for instant actions with a delay before the callback.\n"
                ".over() is for smooth transitions over time.\n\n"
                "Valid patterns:\n"
                "  - Instant move, wait, then callback: rig.pos.to(x, y).wait(500).then(callback)\n"
                "  - Glide over time, then callback:    rig.pos.to(x, y).over(2000).then(callback)\n\n"
                "Did you mean: rig.pos.to(x, y).over(duration)?"
            )
        # Disable instant execution since we're doing a transition
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        if easing is not None:
            self._easing = easing
        self._current_stage = "after_forward"
        return self

    def wait(self, duration_ms: float) -> 'PositionToBuilder':
        """Add delay before executing .then() callback

        - After instant move: snap to position, wait, then callback
        - After .over(): glide over time, then wait additional duration, then callback
        """
        self._wait_duration_ms = duration_ms
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'PositionToBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def hold(self, duration_ms: float) -> 'PositionToBuilder':
        """Hold at target position before reverting"""
        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'PositionToBuilder':
        """Move back to original position after hold (or immediately if no hold)"""
        self._revert_duration_ms = duration_ms
        self._revert_easing = easing
        self._current_stage = "after_revert"
        return self

    def then(self, callback: Callable) -> 'PositionToBuilder':
        """Execute callback at the current point in the chain

        Can be called multiple times at different stages:
        - After .over(): fires when forward movement completes
        - After .hold(): fires when hold period completes
        - After .revert(): fires when revert completes

        Examples:
            rig.pos.to(x, y).over(500).then(do_something)
            rig.pos.to(x, y).over(500).then(start_drag).revert(500).then(end_drag)
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        else:
            # Default: fire after forward movement
            self._after_forward_callback = callback
        return self

    def __del__(self):
        """Execute the position change based on how the builder was configured"""
        try:
            if self._duration_ms is not None or self._revert_duration_ms is not None:
                # Store original position for potential revert
                current_pos = Vec2(*ctrl.mouse_pos())
                self._original_pos = current_pos

                # Create forward transition (to target)
                target_pos = Vec2(self.x, self.y)
                offset = target_pos - current_pos

                if self._duration_ms is not None:
                    # Animate to target
                    transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)
                else:
                    # Instant move to target
                    ctrl.mouse_move(int(self.x), int(self.y))
                    transition = None

                # Build callback chain from the end backwards
                rig_state = self.rig_state
                hold_duration = self._hold_duration_ms or 0

                # Stage 3: After revert callback
                after_revert_cb = self._after_revert_callback

                # Stage 2: After hold + schedule revert + after_revert callback
                if self._revert_duration_ms is not None:
                    original_x, original_y = self._original_pos.x, self._original_pos.y
                    revert_duration = self._revert_duration_ms
                    revert_easing = self._revert_easing

                    def schedule_revert():
                        # Move back to original position
                        curr_pos = Vec2(*ctrl.mouse_pos())
                        back_offset = Vec2(original_x, original_y) - curr_pos

                        if revert_duration > 0:
                            # Animate back
                            revert_transition = PositionTransition(
                                curr_pos, back_offset, revert_duration, revert_easing
                            )
                            # Attach after-revert callback
                            if after_revert_cb:
                                revert_transition.on_complete = after_revert_cb
                            rig_state._position_transitions.append(revert_transition)
                        else:
                            # Instant revert
                            ctrl.mouse_move(int(original_x), int(original_y))
                            if after_revert_cb:
                                after_revert_cb()

                    # Combine after_hold callback with revert scheduling
                    def after_hold_combined():
                        if self._after_hold_callback:
                            self._after_hold_callback()
                        schedule_revert()

                    after_hold_cb = after_hold_combined
                else:
                    # No revert, just use the after_hold callback
                    after_hold_cb = self._after_hold_callback

                # Stage 1: After forward + hold + callbacks
                def after_forward_combined():
                    # Call after_forward callback
                    if self._after_forward_callback:
                        self._after_forward_callback()

                    # Schedule hold period if specified
                    if hold_duration > 0:
                        if after_hold_cb:
                            cron.after(f"{hold_duration}ms", after_hold_cb)
                    else:
                        # No hold, go straight to after_hold callback (which includes revert)
                        if after_hold_cb:
                            after_hold_cb()

                # Wire up the forward transition
                if transition is not None:
                    transition.on_complete = after_forward_combined
                    self.rig_state.start()  # Ensure ticking is active
                    self.rig_state._position_transitions.append(transition)
                else:
                    # Instant forward, call callback immediately
                    after_forward_combined()

            elif self._should_execute_instant:
                # Instant move
                ctrl.mouse_move(int(self.x), int(self.y))

                # Execute callback immediately or after wait duration
                if self._wait_duration_ms is not None and self._after_forward_callback:
                    # Wait for duration, then execute callback
                    job = cron.after(f"{self._wait_duration_ms}ms", self._after_forward_callback)
                    self.rig_state._pending_wait_jobs.append(job)
                elif self._after_forward_callback:
                    self._after_forward_callback()
        except:
            pass  # Ignore errors during cleanup

    def __getattr__(self, name: str):
        """Provide helpful error messages for invalid chaining attempts"""
        # Common rig properties that can't be chained
        if name in ['speed', 'accel', 'pos', 'direction']:
            raise AttributeError(_error_cannot_chain_property('pos.to()', name))
        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after pos.to().\n\n"
                "Instead, use separate statements."
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute(
            'PositionToBuilder',
            name,
            'over, wait, hold, revert, then'
        ))


class PositionByBuilder:
    """Builder for pos.by() operations"""
    def __init__(self, rig_state: 'RigState', dx: float, dy: float, instant: bool = False):
        self.rig_state = rig_state
        self.dx = dx
        self.dy = dy
        self._easing = "ease_in_out"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._wait_duration_ms: Optional[float] = None
        self._hold_duration_ms: Optional[float] = None
        self._revert_duration_ms: Optional[float] = None
        self._revert_easing: str = "linear"
        self._original_pos: Optional[Vec2] = None
        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def over(self, duration_ms: float, easing: str = None) -> 'PositionByBuilder':
        """Glide by offset over time"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait()\n"
                ".wait() is for instant actions with a delay before the callback.\n"
                ".over() is for smooth transitions over time.\n\n"
                "Valid patterns:\n"
                "  - Instant move, wait, then callback: rig.pos.by(dx, dy).wait(500).then(callback)\n"
                "  - Glide over time, then callback:    rig.pos.by(dx, dy).over(2000).then(callback)\n\n"
                "Did you mean: rig.pos.by(dx, dy).over(duration)?"
            )
        # Disable instant execution since we're doing a transition
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        if easing is not None:
            self._easing = easing
        self._current_stage = "after_forward"
        return self

    def wait(self, duration_ms: float) -> 'PositionByBuilder':
        """Add delay before executing .then() callback

        - After instant move: apply offset, wait, then callback
        - After .over(): glide over time, then wait additional duration, then callback
        """
        self._wait_duration_ms = duration_ms
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'PositionByBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def hold(self, duration_ms: float) -> 'PositionByBuilder':
        """Hold at target position before reverting"""
        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'PositionByBuilder':
        """Move back to original position after hold (or immediately if no hold)"""
        self._revert_duration_ms = duration_ms
        self._revert_easing = easing
        self._current_stage = "after_revert"
        return self

    def then(self, callback: Callable) -> 'PositionByBuilder':
        """Execute callback at the current point in the chain

        Can be called multiple times at different stages:
        - After .over(): fires when forward movement completes
        - After .hold(): fires when hold period completes
        - After .revert(): fires when revert completes

        Examples:
            rig.pos.by(dx, dy).over(500).then(do_something)
            rig.pos.by(dx, dy).over(500).then(start_drag).revert(500).then(end_drag)
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        else:
            # Default: fire after forward movement
            self._after_forward_callback = callback
        return self

    def __del__(self):
        """Execute the position change based on how the builder was configured"""
        try:
            if self._duration_ms is not None or self._revert_duration_ms is not None:
                # Store original position for potential revert
                current_pos = Vec2(*ctrl.mouse_pos())
                self._original_pos = current_pos

                # Create forward transition (by offset)
                offset = Vec2(self.dx, self.dy)

                if self._duration_ms is not None:
                    # Animate by offset
                    transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)
                else:
                    # Instant move by offset
                    ctrl.mouse_move(int(current_pos.x + self.dx), int(current_pos.y + self.dy))
                    transition = None

                # Build callback chain from the end backwards
                rig_state = self.rig_state
                hold_duration = self._hold_duration_ms or 0

                # Stage 3: After revert callback
                after_revert_cb = self._after_revert_callback

                # Stage 2: After hold + schedule revert + after_revert callback
                if self._revert_duration_ms is not None:
                    revert_duration = self._revert_duration_ms
                    revert_easing = self._revert_easing
                    # Use inverse offset for precise return
                    inverse_offset = Vec2(-self.dx, -self.dy)

                    def schedule_revert():
                        # Move back by exact inverse offset
                        curr_pos = Vec2(*ctrl.mouse_pos())

                        if revert_duration > 0:
                            # Animate back using inverse offset
                            revert_transition = PositionTransition(
                                curr_pos, inverse_offset, revert_duration, revert_easing
                            )
                            # Attach after-revert callback
                            if after_revert_cb:
                                revert_transition.on_complete = after_revert_cb
                            rig_state._position_transitions.append(revert_transition)
                        else:
                            # Instant revert using inverse offset
                            ctrl.mouse_move(int(curr_pos.x - self.dx), int(curr_pos.y - self.dy))
                            if after_revert_cb:
                                after_revert_cb()

                    # Combine after_hold callback with revert scheduling
                    def after_hold_combined():
                        if self._after_hold_callback:
                            self._after_hold_callback()
                        schedule_revert()

                    after_hold_cb = after_hold_combined
                else:
                    # No revert, just use the after_hold callback
                    after_hold_cb = self._after_hold_callback

                # Stage 1: After forward + hold + callbacks
                def after_forward_combined():
                    # Call after_forward callback
                    if self._after_forward_callback:
                        self._after_forward_callback()

                    # Schedule hold period if specified
                    if hold_duration > 0:
                        if after_hold_cb:
                            cron.after(f"{hold_duration}ms", after_hold_cb)
                    else:
                        # No hold, go straight to after_hold callback (which includes revert)
                        if after_hold_cb:
                            after_hold_cb()

                # Wire up the forward transition
                if transition is not None:
                    transition.on_complete = after_forward_combined
                    self.rig_state.start()  # Ensure ticking is active
                    self.rig_state._position_transitions.append(transition)
                else:
                    # Instant forward, call callback immediately
                    after_forward_combined()

            elif self._should_execute_instant:
                # Instant move
                current_x, current_y = ctrl.mouse_pos()
                ctrl.mouse_move(int(current_x + self.dx), int(current_y + self.dy))

                # Execute callback immediately or after wait duration
                if self._wait_duration_ms is not None and self._after_forward_callback:
                    # Wait for duration, then execute callback
                    job = cron.after(f"{self._wait_duration_ms}ms", self._after_forward_callback)
                    self.rig_state._pending_wait_jobs.append(job)
                elif self._after_forward_callback:
                    self._after_forward_callback()
        except:
            pass  # Ignore errors during cleanup

    def __getattr__(self, name: str):
        """Provide helpful error messages for invalid chaining attempts"""
        # Common rig properties that can't be chained
        if name in ['speed', 'accel', 'pos', 'direction']:
            raise AttributeError(_error_cannot_chain_property('pos.by()', name))
        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after pos.by().\n\n"
                "Instead, use separate statements."
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute(
            'PositionByBuilder',
            name,
            'over, wait, hold, revert, then'
        ))


class NamedModifierBuilder:
    """Builder for named modifiers that can be stopped early"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name
        self._speed_controller = None
        self._accel_controller = None

    @property
    def speed(self) -> 'NamedSpeedController':
        """Access speed property for this named modifier"""
        if self._speed_controller is None:
            self._speed_controller = NamedSpeedController(self.rig_state, self.name)
        return self._speed_controller

    @property
    def accel(self) -> 'NamedAccelController':
        """Access accel property for this named modifier"""
        if self._accel_controller is None:
            self._accel_controller = NamedAccelController(self.rig_state, self.name)
        return self._accel_controller

    def stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop the named modifier

        Args:
            duration_ms: Optional duration to fade out. If None, stops immediately.
            easing: Easing function for gradual stop

        Examples:
            rig("boost").stop()  # Immediate stop
            rig("boost").stop(500, "ease_out")  # Fade out over 500ms
        """
        if self.name in self.rig_state._named_modifiers:
            effect = self.rig_state._named_modifiers[self.name]
            effect.request_stop(duration_ms, easing)


class NamedSpeedController:
    """Speed controller for named modifiers - only allows relative modifiers"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def to(self, value: float) -> 'PropertyEffectBuilder':
        """ERROR: Modifiers cannot use .to() - use rig.force() for absolute values"""
        raise ValueError(
            f"Modifiers can only use relative operations (.mul, .by, .div). "
            f"Use rig.force('{self.name}') for absolute values (.to)."
        )

    def by(self, delta: float) -> 'PropertyEffectBuilder':
        """Add delta to speed"""
        builder = PropertyEffectBuilder(self.rig_state, "speed", "by", delta)
        builder._effect_name = self.name
        return builder

    def mul(self, factor: float) -> 'PropertyEffectBuilder':
        """Multiply speed by factor"""
        builder = PropertyEffectBuilder(self.rig_state, "speed", "mul", factor)
        builder._effect_name = self.name
        return builder

    def div(self, divisor: float) -> 'PropertyEffectBuilder':
        """Divide speed by divisor"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide speed by zero")
        builder = PropertyEffectBuilder(self.rig_state, "speed", "div", divisor)
        builder._effect_name = self.name
        return builder


class NamedAccelController:
    """Accel controller for named modifiers - only allows relative modifiers"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def to(self, value: float) -> 'PropertyEffectBuilder':
        """ERROR: Modifiers cannot use .to() - use rig.force() for absolute values"""
        raise ValueError(
            f"Modifiers can only use relative operations (.mul, .by, .div). "
            f"Use rig.force('{self.name}') for absolute values (.to)."
        )

    def by(self, delta: float) -> 'PropertyEffectBuilder':
        """Add delta to accel"""
        builder = PropertyEffectBuilder(self.rig_state, "accel", "by", delta)
        builder._effect_name = self.name
        return builder

    def mul(self, factor: float) -> 'PropertyEffectBuilder':
        """Multiply accel by factor"""
        builder = PropertyEffectBuilder(self.rig_state, "accel", "mul", factor)
        builder._effect_name = self.name
        return builder

    def div(self, divisor: float) -> 'PropertyEffectBuilder':
        """Divide accel by divisor"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide accel by zero")
        builder = PropertyEffectBuilder(self.rig_state, "accel", "div", divisor)
        builder._effect_name = self.name
        return builder


class NamedForceBuilder:
    """Builder for named forces - independent entities with their own speed/direction/accel"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name
        self._ensure_force_exists()

    def _ensure_force_exists(self):
        """Ensure a Force object exists for this name"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)

    def _get_force(self) -> Force:
        """Get the Force object for this name"""
        self._ensure_force_exists()
        return self.rig_state._named_forces[self.name]

    @property
    def speed(self) -> 'NamedForceSpeedController':
        """Access speed property for this named force"""
        return NamedForceSpeedController(self.rig_state, self.name)

    @property
    def accel(self) -> 'NamedForceAccelController':
        """Access accel property for this named force"""
        return NamedForceAccelController(self.rig_state, self.name)

    def direction(self, x: float, y: float) -> 'NamedForceDirectionBuilder':
        """Set direction for this named force"""
        return NamedForceDirectionBuilder(self.rig_state, self.name, x, y)

    def stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop the named force

        Args:
            duration_ms: Optional duration to fade out. If None, stops immediately.
            easing: Easing function for gradual stop

        Examples:
            rig.force("wind").stop()  # Immediate stop
            rig.force("wind").stop(500, "ease_out")  # Fade out over 500ms
        """
        if self.name in self.rig_state._named_forces:
            force = self.rig_state._named_forces[self.name]
            force.request_stop(duration_ms, easing)


class NamedForceSpeedController:
    """Speed controller for named forces - only allows absolute setters"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def _get_force(self) -> Force:
        """Get or create the Force object"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        return self.rig_state._named_forces[self.name]

    def __call__(self, value: float) -> 'NamedForceSpeedController':
        """Set speed directly (absolute)"""
        return self.to(value)

    def to(self, value: float) -> 'NamedForceSpeedController':
        """Set speed to absolute value"""
        force = self._get_force()
        force._speed = value
        self.rig_state.start()  # Ensure ticking is active
        return self

    def by(self, delta: float) -> 'NamedForceSpeedController':
        """ERROR: Forces cannot use .by() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.by)."
        )

    def mul(self, factor: float) -> 'NamedForceSpeedController':
        """ERROR: Forces cannot use .mul() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.mul)."
        )

    def div(self, divisor: float) -> 'NamedForceSpeedController':
        """ERROR: Forces cannot use .div() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.div)."
        )


class NamedForceAccelController:
    """Accel controller for named forces - only allows absolute setters"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def _get_force(self) -> Force:
        """Get or create the Force object"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        return self.rig_state._named_forces[self.name]

    def __call__(self, value: float) -> 'NamedForceAccelController':
        """Set accel directly (absolute)"""
        return self.to(value)

    def to(self, value: float) -> 'NamedForceAccelController':
        """Set accel to absolute value"""
        force = self._get_force()
        force._accel = value
        self.rig_state.start()  # Ensure ticking is active
        return self

    def by(self, delta: float) -> 'NamedForceAccelController':
        """ERROR: Forces cannot use .by() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.by)."
        )

    def mul(self, factor: float) -> 'NamedForceAccelController':
        """ERROR: Forces cannot use .mul() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.mul)."
        )

    def div(self, divisor: float) -> 'NamedForceAccelController':
        """ERROR: Forces cannot use .div() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.div)."
        )


class NamedForceDirectionBuilder:
    """Direction builder for named forces"""
    def __init__(self, rig_state: 'RigState', name: str, x: float, y: float):
        self.rig_state = rig_state
        self.name = name
        self.x = x
        self.y = y

    def __del__(self):
        """Execute when builder goes out of scope"""
        try:
            # Set direction on the Force object
            if self.name not in self.rig_state._named_forces:
                self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)

            force = self.rig_state._named_forces[self.name]
            force._direction = Vec2(self.x, self.y).normalized()
            self.rig_state.start()  # Ensure ticking is active
        except:
            pass

class NamedModifierNamespace:
    """Namespace for rig.modifier operations"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, name: str) -> NamedModifierBuilder:
        """Create or access a named modifier"""
        return NamedModifierBuilder(self.rig_state, name)

    def stop_all(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop all named modifiers"""
        for effect in list(self.rig_state._named_modifiers.values()):
            effect.request_stop(duration_ms, easing)


class NamedForceNamespace:
    """Namespace for rig.force operations"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, name: str) -> NamedForceBuilder:
        """Create or access a named force"""
        return NamedForceBuilder(self.rig_state, name)

    def stop_all(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop all named forces"""
        for force in list(self.rig_state._named_forces.values()):
            force.request_stop(duration_ms, easing)

        # Clean up force metadata
        if hasattr(self.rig_state, '_named_forces'):
            self.rig_state._named_forces.clear()


# ============================================================================
# STATE ACCESSORS
# ============================================================================

class StateAccessor:
    """Accessor for computed state (base + modifiers + forces)"""
    def __init__(self, rig_state: 'RigState'):
        self._rig = rig_state

    @property
    def speed(self) -> float:
        """Get computed speed (base with modifiers applied, excluding accel velocity)"""
        return self._rig._get_effective_speed()

    @property
    def accel(self) -> float:
        """Get computed acceleration (base with modifiers applied)"""
        return self._rig._get_effective_accel()

    @property
    def direction(self) -> Tuple[float, float]:
        """Get current direction vector"""
        return (self._rig._direction.x, self._rig._direction.y)

    @property
    def pos(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return ctrl.mouse_pos()

    @property
    def velocity(self) -> Tuple[float, float]:
        """Get total velocity vector (speed + accel contributions)"""
        effective_speed = self._rig._get_effective_speed()
        accel_velocity = self._rig._get_accel_velocity_contribution()
        total_speed = effective_speed + accel_velocity
        velocity_vec = self._rig._direction * total_speed
        return (velocity_vec.x, velocity_vec.y)


class BaseAccessor:
    """Accessor for base values only (without modifiers/forces)"""
    def __init__(self, rig_state: 'RigState'):
        self._rig = rig_state

    @property
    def speed(self) -> float:
        """Get base speed (without modifiers)"""
        return self._rig._speed

    @property
    def accel(self) -> float:
        """Get base acceleration (without modifiers)"""
        return self._rig._accel

    @property
    def direction(self) -> Tuple[float, float]:
        """Get base direction vector"""
        return (self._rig._direction.x, self._rig._direction.y)

    @property
    def pos(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return ctrl.mouse_pos()


# ============================================================================
# RIG STATE (main state container)
# ============================================================================

class RigState:
    """Core state for the mouse rig"""
    def __init__(self):
        # Persistent state
        self._direction = Vec2(1, 0)  # unit vector
        self._speed = 0.0  # base speed magnitude
        self._accel = 0.0  # base acceleration magnitude
        self.limits_max_speed = settings.get("user.mouse_rig_max_speed")

        # Transitions (permanent)
        self._speed_transition: Optional[SpeedTransition] = None
        self._direction_transition: Optional[DirectionTransition] = None
        self._position_transitions: list[PositionTransition] = []

        # Effects (temporary property modifications)
        self._effects: list[Effect] = []
        self._named_modifiers: dict[str, Effect] = {}
        self._named_forces: dict[str, Force] = {}  # Force entities

        # Acceleration effects tracking (separate from cruise speed)
        # Maps effect instances to their accumulated velocity contribution
        self._accel_velocities: dict[Effect, float] = {}

        # Controllers (fluent API)
        self.speed = SpeedController(self)
        self.accel = AccelController(self)
        self.direction = DirectionController(self)
        self.pos = PositionController(self)

        # Named modifier/force namespaces
        self._modifier_namespace = NamedModifierNamespace(self)
        self._force_namespace = NamedForceNamespace(self)

        # Sequence state
        self._sequence_queue: list[Callable] = []
        self._sequence_running: bool = False

        # Pending wait/then callbacks
        self._pending_wait_jobs: list = []

        # Frame loop
        self._cron_job = None
        self._last_frame_time = None

        # Subpixel accuracy
        self._subpixel_adjuster = SubpixelAdjuster()

    def __call__(self, name: str) -> 'NamedModifierBuilder':
        """Create or access a named modifier (DEPRECATED - use .modifier() or .force())

        Named modifiers can be stopped early via rig('name').stop()

        Examples:
            rig("boost").speed.mul(2).hold(1000)
            rig("boost").stop()  # Stop immediately
            rig("boost").stop(500)  # Fade out over 500ms
        """
        return NamedModifierBuilder(self, name)

    @property
    def modifier(self) -> NamedModifierNamespace:
        """Access named modifiers (relative changes to base properties)

        Modifiers use relative operations (.mul, .by, .div) and recalculate when base changes.

        Examples:
            rig.modifier("boost").speed.mul(2)
            rig.modifier("boost").stop()
            rig.modifier.stop_all()
        """
        return self._modifier_namespace

    @property
    def force(self) -> NamedForceNamespace:
        """Access named forces (independent entities)

        Forces use absolute values (.to, direct setters) and remain constant.

        Examples:
            rig.force("wind").speed(5).direction(0, 1)
            rig.force("wind").stop()
            rig.force.stop_all()
        """
        return self._force_namespace

    @property
    def state(self) -> StateAccessor:
        """Access computed state (base + modifiers + forces)

        Examples:
            rig.state.speed      # Computed speed
            rig.state.accel      # Computed acceleration
            rig.state.direction  # Current direction
            rig.state.pos        # Current position
            rig.state.velocity   # Total velocity vector
        """
        if not hasattr(self, '_state_accessor'):
            self._state_accessor = StateAccessor(self)
        return self._state_accessor

    @property
    def base(self) -> BaseAccessor:
        """Access base values only (without modifiers/forces)

        Examples:
            rig.base.speed      # Base speed
            rig.base.accel      # Base acceleration
            rig.base.direction  # Base direction
        """
        if not hasattr(self, '_base_accessor'):
            self._base_accessor = BaseAccessor(self)
        return self._base_accessor

    @property
    def state_dict(self) -> dict:
        """Read-only state information as dictionary (deprecated - use .state properties)"""
        position = ctrl.mouse_pos()

        # Calculate effective speed and accel with effects applied
        effective_speed = self._get_effective_speed()
        effective_accel = self._get_effective_accel()
        accel_velocity = self._get_accel_velocity_contribution()

        # Total velocity includes cruise velocity + accel velocity contributions
        total_speed = effective_speed + accel_velocity
        total_velocity = self._direction * total_speed

        # Determine cardinal/intercardinal direction
        direction_cardinal = self._get_cardinal_direction(self._direction)

        return {
            "position": position,
            "direction": self._direction.to_tuple(),
            "direction_cardinal": direction_cardinal,
            "speed": self._speed,  # Base cruise speed
            "accel": self._accel,
            "effective_speed": effective_speed,  # Cruise speed with speed modifiers
            "effective_accel": effective_accel,  # Acceleration with accel modifiers
            "accel_velocity": accel_velocity,  # Integrated velocity from accel effects
            "total_speed": total_speed,  # Total effective speed (cruise + accel velocity)
            "velocity": total_velocity.to_tuple(),  # Total velocity vector
            "active_effects": len(self._effects),
            "named_modifiers": list(self._named_modifiers.keys()),
            "has_speed_transition": self._speed_transition is not None,
            "has_direction_transition": self._direction_transition is not None,
            "active_glides": len(self._position_transitions),
            "is_moving": self.is_moving,
            "is_ticking": self.is_ticking,
        }

    @property
    def is_ticking(self) -> bool:
        """Check if the frame loop is currently running"""
        return self._cron_job is not None

    @property
    def is_moving(self) -> bool:
        """Check if the rig is currently producing movement"""
        epsilon = settings.get("user.mouse_rig_epsilon")
        effective_speed = self._get_effective_speed()
        accel_velocity = self._get_accel_velocity_contribution()
        total_speed = effective_speed + accel_velocity
        effective_accel = self._get_effective_accel()
        return total_speed > epsilon or abs(effective_accel) > epsilon

    @property
    def settings(self) -> dict:
        """Get current rig settings"""
        return {
            "frame_interval": settings.get("user.mouse_rig_frame_interval"),
            "max_speed": self.limits_max_speed,
            "epsilon": settings.get("user.mouse_rig_epsilon"),
            "default_turn_rate": settings.get("user.mouse_rig_default_turn_rate"),
            "movement_type": settings.get("user.mouse_rig_movement_type"),
            "scale": settings.get("user.mouse_rig_scale"),
        }

    def _get_effective_speed(self) -> float:
        """Get speed with all effects applied"""
        base_speed = self._speed
        for effect in self._effects:
            if effect.property_name == "speed":
                base_speed = effect.update(base_speed)
        return max(0.0, base_speed)

    def _get_effective_accel(self) -> float:
        """Get acceleration with all effects applied

        Note: This returns the effective acceleration value but does NOT
        modify cruise speed. Acceleration effects track their own velocity
        contributions separately.
        """
        base_accel = self._accel
        for effect in self._effects:
            if effect.property_name == "accel":
                base_accel = effect.update(base_accel)
        return base_accel

    def _get_accel_velocity_contribution(self) -> float:
        """Get total velocity contribution from all acceleration effects

        This is the sum of all integrated velocities from accel effects,
        scaled by each effect's current multiplier (for fade-out support).
        """
        total = 0.0
        for effect, velocity in self._accel_velocities.items():
            # Scale velocity by effect's current multiplier
            # This makes velocity fade out when effect fades out
            total += velocity * effect.current_multiplier
        return total

    def reverse(self) -> DirectionByBuilder:
        """Reverse direction (180 degree turn)

        Can be instant or smooth:
            rig.reverse()              # Instant 180
            rig.reverse().over(500)    # Smooth 180 over 500ms
            rig.reverse().rate(180)    # Reverse at 180°/s
        """
        return DirectionByBuilder(self, 180, instant=True)

    def _get_cardinal_direction(self, direction: Vec2) -> str:
        """Get cardinal/intercardinal direction name from direction vector

        Returns one of: "right", "left", "up", "down",
                       "up_right", "up_left", "down_right", "down_left"
        """
        x, y = direction.x, direction.y

        # Threshold for considering a direction as "mostly" along an axis
        # 0.383 ≈ cos(67.5°), which is halfway between pure cardinal (0°) and pure diagonal (45°)
        threshold = 0.383

        # Pure cardinal directions (within 22.5° of axis)
        if abs(x) > abs(y) * 2.414:  # tan(67.5°) ≈ 2.414
            return "right" if x > 0 else "left"
        if abs(y) > abs(x) * 2.414:
            return "up" if y < 0 else "down"

        # Diagonal/intercardinal directions
        if x > 0 and y < 0:
            return "up_right"
        elif x < 0 and y < 0:
            return "up_left"
        elif x > 0 and y > 0:
            return "down_right"
        elif x < 0 and y > 0:
            return "down_left"

        # Fallback (shouldn't happen with normalized vectors)
        return "right"

    def bake(self) -> None:
        """Flatten computed state into base, clearing all effects and forces

        This takes the current computed values (base + effects + forces) and
        makes them the new base values, then clears all effects and forces.

        Examples:
            rig.speed(10)
            rig.modifier("boost").speed.mul(2)  # computed speed = 20
            rig.bake()                          # base speed now 20, modifier cleared
        """
        # Compute final values
        final_speed = self._get_effective_speed()
        final_accel = self._get_effective_accel()
        # Direction doesn't change with effects in current implementation
        final_direction = self._direction

        # Set as new base
        self._speed = final_speed
        self._accel = final_accel
        self._direction = final_direction

        # Clear all effects and forces
        self._effects.clear()
        self._named_modifiers.clear()
        self._named_forces.clear()
        self._accel_velocities.clear()

        # Note: We don't clear transitions as those are permanent changes in progress

    def _stop_immediate(self) -> None:
        """Internal: Immediate stop implementation"""
        # Stop movement
        self._speed = 0.0
        self._accel = 0.0
        self._speed_transition = None
        self._direction_transition = None
        self._position_transitions.clear()

        # Clear effects
        self._effects.clear()
        self._named_modifiers.clear()

        # Reset subpixel accumulator to prevent drift on restart
        self._subpixel_adjuster = SubpixelAdjuster()

        # Stop frame loop
        if self._cron_job is not None:
            cron.cancel(self._cron_job)
            self._cron_job = None

        # Cancel all pending wait/then callbacks
        for job in self._pending_wait_jobs:
            try:
                cron.cancel(job)
            except:
                pass  # Ignore errors if job already completed
        self._pending_wait_jobs.clear()

    def stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop everything: bake state, clear effects/forces, decelerate to 0

        Args:
            duration_ms: Optional duration to decelerate over. If None, stops immediately.
            easing: Easing function name for gradual deceleration

        Examples:
            rig.stop()                  # Instant: bake, clear, speed=0
            rig.stop(500)               # Bake, clear, then decelerate over 500ms
            rig.stop(1000, "ease_out")  # Bake, clear, decelerate with easing
        """
        # 1. Bake current state (flatten effects/forces into base)
        self.bake()

        # 2. Effects and forces already cleared by bake()

        # 3. Decelerate speed to 0
        if duration_ms is None or duration_ms == 0:
            # Immediate stop
            self._speed = 0.0
            self._accel = 0.0
            self._speed_transition = None
            self._direction_transition = None
            self._position_transitions.clear()

            # Reset subpixel accumulator
            self._subpixel_adjuster = SubpixelAdjuster()

            # Stop frame loop
            if self._cron_job is not None:
                cron.cancel(self._cron_job)
                self._cron_job = None

            # Cancel pending callbacks
            for job in self._pending_wait_jobs:
                try:
                    cron.cancel(job)
                except:
                    pass
            self._pending_wait_jobs.clear()
        else:
            # Gradual deceleration: fade speed to 0 over duration
            transition = SpeedTransition(
                self._speed,
                0.0,
                duration_ms,
                easing
            )
            self.start()
            self._speed_transition = transition

    def sequence(self, steps: list[Callable]) -> None:
        """Execute a sequence of operations in order

        Each step should be a callable (lambda or function) that performs one operation.
        The sequence waits for each step to complete before moving to the next.

        Args:
            steps: List of callables to execute in sequence

        Examples:
            # Click multiple points in order
            rig.sequence([
                lambda: rig.pos.to(100, 200).over(350),
                lambda: actions.mouse_click(0),
                lambda: rig.pos.to(300, 400).over(350),
                lambda: actions.mouse_click(0),
            ])

            # Drag operation
            rig.sequence([
                lambda: rig.pos.to(x1, y1).over(500),
                lambda: actions.mouse_click(0, hold=True),
                lambda: rig.pos.to(x2, y2).over(500),
                lambda: actions.mouse_click(0, hold=False),
            ])
        """
        if not steps:
            return

        self._sequence_queue = list(steps)
        self._sequence_running = True
        self._run_next_in_sequence()

    def _run_next_in_sequence(self) -> None:
        """Internal: Run the next step in the sequence"""
        if not self._sequence_running or not self._sequence_queue:
            self._sequence_running = False
            return

        # Get next step
        step = self._sequence_queue.pop(0)

        # Execute the step
        try:
            step()
        except Exception as e:
            print(f"Error in sequence step: {e}")
            self._sequence_running = False
            return

        # If there are more steps, we need to wait for this step to complete
        # For now, we'll use a simple approach: check if idle after a short delay
        if self._sequence_queue:
            # Schedule the next step to run after current operations complete
            self._schedule_next_sequence_step()
        else:
            self._sequence_running = False

    def _schedule_next_sequence_step(self) -> None:
        """Internal: Schedule the next sequence step after current operation completes"""
        # We need to poll until the rig becomes idle (all transitions complete)
        def check_and_continue():
            # Check if all async operations are done
            if (self._speed_transition is None and
                self._direction_transition is None and
                len(self._position_transitions) == 0):
                # Idle - run next step
                self._run_next_in_sequence()
            else:
                # Still busy - check again soon
                cron.after("16ms", check_and_continue)

        # Start checking after a frame
        cron.after("16ms", check_and_continue)

    def start(self) -> None:
        """Start the frame loop"""
        if self._cron_job is not None:
            return  # Already running

        self._last_frame_time = time.perf_counter()
        interval_ms = settings.get("user.mouse_rig_frame_interval")
        self._cron_job = cron.interval(f"{interval_ms}ms", self._update_frame)



    def _is_idle(self) -> bool:
        """Check if rig is completely idle (no movement or transitions)"""
        epsilon = settings.get("user.mouse_rig_epsilon")

        # Check if speed and accel are effectively zero
        if abs(self._speed) > epsilon or abs(self._accel) > epsilon:
            return False

        # Check for active transitions
        if self._speed_transition is not None:
            return False
        if self._direction_transition is not None:
            return False

        # Check for active effects
        if len(self._effects) > 0:
            return False

        # Check for active forces
        if len(self._named_forces) > 0:
            return False

        # Check for position transitions
        if len(self._position_transitions) > 0:
            return False

        # Check for pending wait/then callbacks - don't stop if we have scheduled callbacks
        if len(self._pending_wait_jobs) > 0:
            return False

        return True

    def _update_frame(self) -> None:
        """Frame update callback"""
        # Calculate delta time
        current_time = time.perf_counter()
        dt = current_time - self._last_frame_time if self._last_frame_time else 0.016
        self._last_frame_time = current_time

        # Update permanent transitions
        if self._speed_transition:
            self._speed_transition.update(self)
            if self._speed_transition.complete:
                self._speed_transition = None

        if self._direction_transition:
            self._direction_transition.update(self)
            if self._direction_transition.complete:
                self._direction_transition = None

        # Update effects (temporary property modifications)
        for effect in self._effects[:]:
            # Start effect if not started
            if effect.phase == "not_started":
                if effect.property_name == "speed":
                    effect.start(self._speed)
                elif effect.property_name == "accel":
                    effect.start(self._accel)
                    # Initialize velocity tracking for accel effects
                    self._accel_velocities[effect] = 0.0

            # Update effect lifecycle for accel effects (they integrate velocity separately)
            if effect.property_name == "accel":
                # Accel effects: get the current acceleration value but don't modify cruise speed
                current_accel = effect.update(self._accel)
                # Integrate the acceleration into this effect's velocity contribution
                if effect in self._accel_velocities:
                    self._accel_velocities[effect] += current_accel * dt

            # Remove completed effects
            if effect.complete:
                self._effects.remove(effect)
                # Remove from named modifiers if it has a name
                if effect.name and effect.name in self._named_modifiers:
                    del self._named_modifiers[effect.name]
                # Remove velocity tracking for accel effects
                if effect.property_name == "accel" and effect in self._accel_velocities:
                    del self._accel_velocities[effect]

        # Handle base acceleration (permanent accel changes)
        # Base accel DOES modify cruise speed permanently
        base_accel = self._accel
        if abs(base_accel) > 1e-6:
            self._speed += base_accel * dt
            self._speed = max(0.0, self._speed)
            if self.limits_max_speed is not None:
                self._speed = min(self._speed, self.limits_max_speed)

        # Calculate velocity from effective speed and direction
        effective_speed = self._get_effective_speed()

        # Add velocity contributions from acceleration effects
        accel_velocity_contribution = self._get_accel_velocity_contribution()
        total_speed = effective_speed + accel_velocity_contribution

        # Clamp total speed
        if self.limits_max_speed is not None:
            total_speed = min(total_speed, self.limits_max_speed)
        total_speed = max(0.0, total_speed)

        # Base velocity vector
        velocity = self._direction * total_speed

        # Add force contributions via vector addition
        # Forces return velocity in pixels/frame (same units as base velocity)
        for force_name, force in list(self._named_forces.items()):
            force_velocity = force.update(dt)
            velocity = velocity + force_velocity

            # Remove completed forces
            if force.complete:
                del self._named_forces[force_name]

        # Apply scale
        scale = settings.get("user.mouse_rig_scale")
        velocity = velocity * scale

        # Update position from velocity
        position_delta = velocity

        # Apply position transitions (glides)
        for pos_transition in self._position_transitions[:]:
            glide_delta = pos_transition.update(self)
            position_delta = position_delta + glide_delta
            if pos_transition.complete:
                self._position_transitions.remove(pos_transition)

        # Apply subpixel adjustment to prevent rounding drift
        dx_int, dy_int = self._subpixel_adjuster.adjust(position_delta.x, position_delta.y)

        # Move the cursor only if we have integer pixels to move
        if dx_int != 0 or dy_int != 0:
            current_x, current_y = ctrl.mouse_pos()
            new_x = current_x + dx_int
            new_y = current_y + dy_int
            _mouse_move(new_x, new_y)

        # Auto-stop if completely idle
        if self._is_idle():
            self.stop()


# ============================================================================
# GLOBAL RIG INSTANCE
# ============================================================================

_rig_instance: Optional[RigState] = None


def get_rig() -> RigState:
    """Get or create the global rig instance"""
    global _rig_instance
    if _rig_instance is None:
        _rig_instance = RigState()
        # Don't auto-start - will start on first command
    return _rig_instance


# ============================================================================
# TALON ACTIONS
# ============================================================================

@mod.action_class
class Actions:
    def mouse_rig() -> RigState:
        """Get the mouse rig instance

        Example:
            rig = actions.user.mouse_rig()
            rig.direction((1, 0))
            rig.speed(5)
        """
        return get_rig()

    def mouse_rig_state() -> dict:
        """Get the current state of the mouse rig

        Returns a dictionary with current rig state including:
        - position: Current mouse position (x, y)
        - direction: Direction vector (x, y)
        - direction_cardinal: Cardinal direction name ("right", "left", "up", "down", etc.)
        - speed: Current cruise speed
        - cruise_velocity: Cruise velocity (x, y)
        - total_velocity: Total velocity including overlays (x, y)
        - Active overlays/transitions counts
        - is_ticking: Whether the rig is actively running

        Example:
            state = actions.user.mouse_rig_state()
            print(f"Speed: {state['speed']}")
            print(f"Direction: {state['direction_cardinal']}")
        """
        rig = get_rig()
        return rig.state_dict

    def mouse_rig_stop() -> None:
        """Stop the mouse rig frame loop"""
        global _rig_instance
        if _rig_instance:
            _rig_instance.stop()
            _rig_instance = None

    def mouse_rig_set_type_talon() -> None:
        """Set mouse movement type to Talon (default, works for most apps)"""
        settings.set("user.mouse_rig_movement_type", "talon")

    def mouse_rig_set_type_windows_raw() -> None:
        """Set mouse movement type to Windows raw input (for some games)"""
        if not _windows_raw_available:
            print("Warning: Windows raw input not available (pywin32 not installed)")
            return
        settings.set("user.mouse_rig_movement_type", "windows_raw")

    def mouse_rig_set_scale(scale: float) -> None:
        """Set movement scale multiplier

        Args:
            scale: Scale factor (1.0 = normal, 2.0 = double, 0.5 = half)
        """
        settings.set("user.mouse_rig_scale", scale)
