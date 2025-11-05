"""
Talon Mouse Rig - Continuous motion-based mouse control system

A fluent, stateful mouse control API supporting:
- Continuous movement with direction + speed
- Smooth transitions and easing
- Temporary overlays (thrust, resist, boost)
- Permanent rate-based changes (accelerate, decelerate)
- Position control (glides)

Usage:
    rig = actions.user.mouse_rig()
    rig.direction((1, 0))       # right
    rig.speed(5)                # set cruise speed
    rig.speed(10).over(300)     # ramp to 10 over 300ms

    # Temporary overlays
    rig.thrust(5).over(1000)    # temporary acceleration
    rig.resist(3).over(500)     # temporary deceleration

    # Permanent rate-based
    rig.accelerate(2)           # cruise speed increases continuously
    rig.decelerate(2)           # cruise speed decreases continuously
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


class AccelerateTransition:
    """Permanent acceleration transition (rate-based speed increase)"""
    def __init__(self, accel_rate: float):
        self.accel_rate = accel_rate  # speed units to gain per second
        self.complete = False

    def update(self, rig_state: 'RigState', dt: float) -> None:
        # Apply acceleration (speed units per second)
        delta_v = self.accel_rate * dt
        rig_state._speed += delta_v

        # Clamp to max speed limit if set
        if rig_state.limits_max_speed is not None:
            rig_state._speed = min(rig_state._speed, rig_state.limits_max_speed)


class DecelerateTransition:
    """Permanent deceleration transition (rate-based speed decrease)"""
    def __init__(self, decel_rate: float):
        self.decel_rate = decel_rate  # speed units to lose per second
        self.complete = False

    def update(self, rig_state: 'RigState', dt: float) -> None:
        epsilon = settings.get("user.mouse_rig_epsilon")

        # Apply deceleration (speed units per second)
        delta_v = self.decel_rate * dt
        rig_state._speed = max(0.0, rig_state._speed - delta_v)

        # Complete when we reach zero
        if rig_state._speed < epsilon:
            rig_state._speed = 0.0
            self.complete = True


# ============================================================================
# THRUST, RESIST & BOOST OVERLAYS
# ============================================================================

class ThrustOverlay:
    """Temporary acceleration overlay that integrates to velocity, then decays"""
    def __init__(self, acceleration: float, direction: Optional[Vec2] = None,
                 duration_ms: Optional[float] = None, easing: str = "linear"):
        self.acceleration = acceleration
        self.direction = direction  # None means use rig's current direction
        self.duration_ms = duration_ms
        self.decay_duration_ms = duration_ms if duration_ms else 0  # Same duration for decay
        self.start_time = time.perf_counter() if duration_ms else None
        self.easing_fn = EASING_FUNCTIONS.get(easing, ease_linear)
        self.phase = "accel"  # "accel" or "decay"
        self.accumulated_velocity = Vec2(0, 0)
        self.peak_velocity = Vec2(0, 0)
        self.decay_start_time = None
        self.complete = False

    def update(self, rig_direction: Vec2, dt: float) -> Vec2:
        """Update and return velocity contribution for this frame"""
        if self.complete:
            return Vec2(0, 0)

        # Determine direction
        thrust_dir = self.direction if self.direction else rig_direction

        if self.phase == "accel":
            # Acceleration phase - integrate to build velocity
            if self.duration_ms and self.start_time:
                elapsed = (time.perf_counter() - self.start_time) * 1000
                if elapsed >= self.duration_ms:
                    # Transition to decay phase
                    self.phase = "decay"
                    self.peak_velocity = self.accumulated_velocity
                    self.decay_start_time = time.perf_counter()
                else:
                    # Apply acceleration with easing envelope
                    t = elapsed / self.duration_ms
                    magnitude = self.acceleration * self.easing_fn(t)
                    accel_vec = thrust_dir * magnitude
                    self.accumulated_velocity = self.accumulated_velocity + (accel_vec * dt)

        if self.phase == "decay":
            # Decay phase - linearly reduce accumulated velocity back to 0
            elapsed = (time.perf_counter() - self.decay_start_time) * 1000
            if elapsed >= self.decay_duration_ms:
                self.complete = True
                return Vec2(0, 0)

            # Linear decay from peak to 0
            t = 1.0 - (elapsed / self.decay_duration_ms)
            self.accumulated_velocity = self.peak_velocity * t

        return self.accumulated_velocity


class ResistOverlay:
    """Temporary deceleration overlay - applies velocity that opposes motion"""
    def __init__(self, deceleration: float, direction: Optional[Vec2] = None,
                 duration_ms: Optional[float] = None, easing: str = "ease_out"):
        self.deceleration = deceleration
        self.direction = direction  # None means opposite of rig's current direction
        self.duration_ms = duration_ms
        self.start_time = time.perf_counter() if duration_ms else None
        self.easing_fn = EASING_FUNCTIONS.get(easing, ease_linear)
        self.complete = False

    def get_velocity(self, rig_direction: Vec2) -> Vec2:
        """Get velocity offset for this frame (opposes motion)"""
        if self.complete:
            return Vec2(0, 0)

        # Determine direction (default is opposite of current motion)
        resist_dir = self.direction if self.direction else (rig_direction * -1)

        # Calculate magnitude based on time envelope
        magnitude = self.deceleration
        if self.duration_ms and self.start_time:
            elapsed = (time.perf_counter() - self.start_time) * 1000
            if elapsed >= self.duration_ms:
                self.complete = True
                return Vec2(0, 0)
            t = elapsed / self.duration_ms
            magnitude *= self.easing_fn(t)

        return resist_dir * magnitude


class BoostOverlay:
    """Instant velocity offset that decays over time"""
    def __init__(self, force: float, direction: Vec2, duration_ms: float):
        self.initial_velocity = direction.normalized() * force
        self.duration_ms = duration_ms
        self.start_time = time.perf_counter()
        self.complete = False

    def get_velocity(self) -> Vec2:
        """Get velocity contribution for this frame (decays linearly)"""
        elapsed = (time.perf_counter() - self.start_time) * 1000
        if elapsed >= self.duration_ms:
            self.complete = True
            return Vec2(0, 0)

        # Linear decay
        t = 1.0 - (elapsed / self.duration_ms)
        return self.initial_velocity * t


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
        """Add to current speed"""
        return SpeedAdjustBuilder(self.rig_state, delta, instant=True)

    def subtract(self, delta: float) -> SpeedAdjustBuilder:
        """Subtract from current speed"""
        return self.add(-delta)

    def sub(self, delta: float) -> SpeedAdjustBuilder:
        """Subtract from current speed (shorthand for subtract)"""
        return self.subtract(delta)

    def multiply(self, factor: float) -> SpeedMultiplyBuilder:
        """Multiply current speed by factor"""
        return SpeedMultiplyBuilder(self.rig_state, factor, instant=True)

    def mul(self, factor: float) -> SpeedMultiplyBuilder:
        """Multiply current speed by factor (shorthand for multiply)"""
        return self.multiply(factor)

    def divide(self, divisor: float) -> SpeedDivideBuilder:
        """Divide current speed by divisor"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide speed by zero")

        return SpeedDivideBuilder(self.rig_state, divisor, instant=True)

    def div(self, divisor: float) -> SpeedDivideBuilder:
        """Divide current speed by divisor (shorthand for divide)"""
        return self.divide(divisor)


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

    def over(self, duration_ms: float) -> 'DirectionBuilder':
        """Rotate to target direction over time"""
        if self._wait_duration_ms is not None:
            raise ValueError(
                "Cannot use .over() after .wait() - these are mutually exclusive execution modes.\n"
                "Choose one:\n"
                "  - For instant direction change with delay: rig.direction(1, 0).wait(500).then(callback)\n"
                "  - For smooth rotation over time: rig.direction(1, 0).over(500).then(callback)"
            )
        self._should_execute_instant = False
        self._duration_ms = duration_ms
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

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'DirectionBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def then(self, callback: Callable) -> 'DirectionBuilder':
        """Execute callback after direction change completes"""
        self._then_callback = callback
        return self


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
        self._easing = "linear"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._wait_duration_ms: Optional[float] = None

    def over(self, duration_ms: float) -> 'PositionToBuilder':
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

    def then(self, callback: Callable) -> 'PositionToBuilder':
        """Execute callback after position change completes"""
        self._then_callback = callback
        return self

    def __del__(self):
        """Execute the position change based on how the builder was configured"""
        try:
            if self._duration_ms is not None:
                # Create and apply transition with the configured easing
                current_pos = Vec2(*ctrl.mouse_pos())
                target_pos = Vec2(self.x, self.y)
                offset = target_pos - current_pos
                transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)

                # Register callback with transition if set
                if self._then_callback:
                    # If wait is specified, add additional delay after transition
                    if self._wait_duration_ms is not None:
                        # Capture variables in closure
                        wait_ms = self._wait_duration_ms
                        callback = self._then_callback
                        rig_state = self.rig_state
                        print(f"DEBUG: Setting up delayed callback with wait_ms={wait_ms}")
                        def delayed_callback():
                            print(f"DEBUG: Transition complete, scheduling callback after {wait_ms}ms")
                            def execute_callback():
                                print(f"DEBUG: About to execute callback")
                                try:
                                    callback()
                                    print(f"DEBUG: Callback executed")
                                finally:
                                    # Remove this job from pending list after execution
                                    if job in rig_state._pending_wait_jobs:
                                        rig_state._pending_wait_jobs.remove(job)
                                    print(f"DEBUG: Job removed from pending list")
                            job = cron.after(f"{wait_ms}ms", execute_callback)
                            rig_state._pending_wait_jobs.append(job)
                            print(f"DEBUG: Callback scheduled, job={job}")
                        transition.on_complete = delayed_callback
                    else:
                        transition.on_complete = self._then_callback

                self.rig_state.start()  # Ensure ticking is active
                self.rig_state._position_transitions.append(transition)
            elif self._should_execute_instant:
                # Instant move
                ctrl.mouse_move(int(self.x), int(self.y))

                # Execute callback immediately or after wait duration
                if self._wait_duration_ms is not None and self._then_callback:
                    # Wait for duration, then execute callback
                    job = cron.after(f"{self._wait_duration_ms}ms", self._then_callback)
                    self.rig_state._pending_wait_jobs.append(job)
                    self.rig_state._pending_wait_jobs.append(job)
                elif self._then_callback:
                    self._then_callback()
        except:
            pass  # Ignore errors during cleanup


class PositionByBuilder:
    """Builder for pos.by() operations"""
    def __init__(self, rig_state: 'RigState', dx: float, dy: float, instant: bool = False):
        self.rig_state = rig_state
        self.dx = dx
        self.dy = dy
        self._easing = "linear"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._wait_duration_ms: Optional[float] = None

    def over(self, duration_ms: float) -> 'PositionByBuilder':
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

    def then(self, callback: Callable) -> 'PositionByBuilder':
        """Execute callback after position change completes"""
        self._then_callback = callback
        return self

    def __del__(self):
        """Execute the position change based on how the builder was configured"""
        try:
            if self._duration_ms is not None:
                # Create and apply transition with the configured easing
                current_pos = Vec2(*ctrl.mouse_pos())
                offset = Vec2(self.dx, self.dy)
                transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)

                # Register callback with transition if set
                if self._then_callback:
                    # If wait is specified, add additional delay after transition
                    if self._wait_duration_ms is not None:
                        # Capture variables in closure
                        wait_ms = self._wait_duration_ms
                        callback = self._then_callback
                        rig_state = self.rig_state
                        def delayed_callback():
                            job = cron.after(f"{wait_ms}ms", callback)
                            rig_state._pending_wait_jobs.append(job)
                        transition.on_complete = delayed_callback
                    else:
                        transition.on_complete = self._then_callback

                self.rig_state.start()  # Ensure ticking is active
                self.rig_state._position_transitions.append(transition)
            elif self._should_execute_instant:
                # Instant move
                current_x, current_y = ctrl.mouse_pos()
                ctrl.mouse_move(int(current_x + self.dx), int(current_y + self.dy))

                # Execute callback immediately or after wait duration
                if self._wait_duration_ms is not None and self._then_callback:
                    # Wait for duration, then execute callback
                    job = cron.after(f"{self._wait_duration_ms}ms", self._then_callback)
                    self.rig_state._pending_wait_jobs.append(job)
                elif self._then_callback:
                    self._then_callback()
        except:
            pass  # Ignore errors during cleanup


class ThrustBuilder:
    """Builder for thrust operations"""
    def __init__(self, rig_state: 'RigState', acceleration: float):
        self.rig_state = rig_state
        self.acceleration = acceleration
        self._direction = None
        self._easing = "linear"

    def dir(self, x: float, y: float) -> 'ThrustBuilder':
        """Set explicit thrust direction

        Args:
            x: X component of direction vector
            y: Y component of direction vector
        """
        self._direction = Vec2(x, y).normalized()
        return self

    def over(self, duration_ms: float) -> 'ThrustBuilder':
        """Apply thrust over time"""
        overlay = ThrustOverlay(
            self.acceleration,
            self._direction,
            duration_ms,
            self._easing
        )
        self.rig_state.start()  # Ensure ticking is active
        self.rig_state._thrust_overlays.append(overlay)
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'ThrustBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self


class ResistBuilder:
    """Builder for resist (temporary deceleration) operations"""
    def __init__(self, rig_state: 'RigState', deceleration: float):
        self.rig_state = rig_state
        self.deceleration = deceleration
        self._direction = None
        self._easing = "linear"

    def dir(self, x: float, y: float) -> 'ResistBuilder':
        """Set explicit resist direction

        Args:
            x: X component of direction vector
            y: Y component of direction vector
        """
        self._direction = Vec2(x, y).normalized()
        return self

    def over(self, duration_ms: float) -> 'ResistBuilder':
        """Apply resist over time"""
        overlay = ResistOverlay(
            self.deceleration,
            self._direction,
            duration_ms,
            self._easing
        )
        self.rig_state.start()  # Ensure ticking is active
        self.rig_state._resist_overlays.append(overlay)
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'ResistBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self


class BoostBuilder:
    """Builder for boost operations"""
    def __init__(self, rig_state: 'RigState', force: float):
        self.rig_state = rig_state
        self.force = force
        self._direction = None

    def dir(self, x: float, y: float) -> 'BoostBuilder':
        """Set explicit boost direction

        Args:
            x: X component of direction vector
            y: Y component of direction vector
        """
        self._direction = Vec2(x, y).normalized()
        return self

    def over(self, duration_ms: float) -> 'BoostBuilder':
        """Apply boost with decay over time"""
        direction = self._direction if self._direction else self.rig_state._direction
        overlay = BoostOverlay(self.force, direction, duration_ms)
        self.rig_state.start()  # Ensure ticking is active
        self.rig_state._boost_overlays.append(overlay)
        return self


class StopBuilder:
    """Builder for stop operations with .over() support"""
    def __init__(self, rig_state: 'RigState', instant: bool = False):
        self.rig_state = rig_state
        self._easing = "linear"
        self._should_execute_instant = instant
        self._then_callback: Optional[Callable] = None
        self._duration_ms: Optional[float] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Ignore errors during cleanup

    def _execute(self):
        """Execute the configured operation"""
        if self._duration_ms is not None:
            # Bake current velocity, clear everything, then decelerate
            self.rig_state.bake()

            # Create transition from current (baked) speed to 0
            current_speed = self.rig_state._speed
            transition = SpeedTransition(
                current_speed,
                0.0,
                self._duration_ms,
                self._easing
            )
            self.rig_state.start()  # Ensure ticking is active
            self.rig_state._speed_transition = transition

            # Register callback with transition if set
            if self._then_callback:
                transition.on_complete = self._then_callback
        elif self._should_execute_instant:
            # Instant stop (original behavior)
            self.rig_state._stop_immediate()

            # Execute callback immediately if set
            if self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float) -> 'StopBuilder':
        """Decelerate to stop over time

        Bakes current velocity (including all overlays) into cruise speed,
        clears all overlays/transitions, then smoothly decelerates to zero.

        Examples:
            rig.stop().over(500)                    # Smooth stop over 500ms
            rig.stop().over(500).ease("ease_out")   # Smooth stop with easing
        """
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'StopBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def then(self, callback: Callable) -> 'StopBuilder':
        """Execute callback after stop completes"""
        self._then_callback = callback
        return self


# ============================================================================
# RIG STATE (main state container)
# ============================================================================

class RigState:
    """Core state for the mouse rig"""
    def __init__(self):
        # Persistent state
        self._direction = Vec2(1, 0)  # unit vector
        self._speed = 0.0  # cruise speed magnitude
        self.limits_max_speed = settings.get("user.mouse_rig_max_speed")

        # Transitions
        self._speed_transition: Optional[SpeedTransition] = None
        self._direction_transition: Optional[DirectionTransition] = None
        self._accelerate_transition: Optional[AccelerateTransition] = None
        self._decelerate_transition: Optional[DecelerateTransition] = None
        self._position_transitions: list[PositionTransition] = []

        # Overlays
        self._thrust_overlays: list[ThrustOverlay] = []
        self._resist_overlays: list[ResistOverlay] = []
        self._boost_overlays: list[BoostOverlay] = []

        # Controllers (fluent API)
        self.speed = SpeedController(self)
        self.pos = PositionController(self)

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

    @property
    def state(self) -> dict:
        """Read-only state information"""
        position = ctrl.mouse_pos()
        cruise_velocity = self._direction * self._speed

        # Calculate overlay contributions
        thrust_velocity = Vec2(0, 0)
        for thrust in self._thrust_overlays:
            accel_vec = thrust.get_acceleration(self._direction)
            # Approximate velocity contribution (using frame interval)
            dt = settings.get("user.mouse_rig_frame_interval") / 1000.0
            thrust_velocity = thrust_velocity + (accel_vec * dt)

        resist_velocity = Vec2(0, 0)
        for resist in self._resist_overlays:
            resist_vec = resist.get_velocity(self._direction)
            resist_velocity = resist_velocity + resist_vec

        boost_velocity = Vec2(0, 0)
        for boost in self._boost_overlays:
            boost_velocity = boost_velocity + boost.get_velocity()

        total_velocity = cruise_velocity + thrust_velocity + resist_velocity + boost_velocity

        return {
            "position": position,
            "direction": self._direction.to_tuple(),
            "speed": self._speed,
            "cruise_velocity": cruise_velocity.to_tuple(),
            "total_velocity": total_velocity.to_tuple(),
            "active_thrusts": len(self._thrust_overlays),
            "active_resists": len(self._resist_overlays),
            "active_boosts": len(self._boost_overlays),
            "has_speed_transition": self._speed_transition is not None,
            "has_direction_transition": self._direction_transition is not None,
            "has_accelerate": self._accelerate_transition is not None,
            "has_decelerate": self._decelerate_transition is not None,
            "active_glides": len(self._position_transitions),
            "is_ticking": self.is_ticking,
        }

    @property
    def is_ticking(self) -> bool:
        """Check if the frame loop is currently running"""
        return self._cron_job is not None

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

    def direction(self, x: float, y: float) -> DirectionBuilder:
        """Set direction instantly or return builder for .over()

        Args:
            x: X component of direction vector
            y: Y component of direction vector

        Examples:
            rig.direction(1, 0)   # Right
            rig.direction(0, 1)   # Down
            rig.direction(-1, -1) # Up-left diagonal
        """
        self.start()  # Ensure ticking is active
        vec2 = Vec2(x, y)
        normalized = vec2.normalized()

        # Return builder - it will handle instant vs transition
        return DirectionBuilder(self, normalized, instant=True)

    def dir(self, x: float, y: float) -> DirectionBuilder:
        """Alias for direction()"""
        return self.direction(x, y)

    def reverse(self) -> DirectionBuilder:
        """Reverse direction (180 degree turn)

        Can be instant or smooth:
            rig.reverse()              # Instant 180
            rig.reverse().over(500)    # Smooth 180 over 500ms
            rig.reverse().rate(180)    # Reverse at 180°/s
        """
        reversed_dir = self._direction * -1
        return DirectionBuilder(self, reversed_dir, instant=True)

    def _calculate_total_velocity(self) -> Vec2:
        """Calculate current total velocity including all overlays

        Returns the combined velocity from:
        - Cruise velocity (direction * speed)
        - Thrust overlays
        - Resist overlays
        - Boost overlays
        """
        # Calculate cruise velocity
        cruise_velocity = self._direction * self._speed

        # Get frame interval for overlay calculations
        dt = settings.get("user.mouse_rig_frame_interval") / 1000.0

        # Calculate thrust velocity
        thrust_velocity = Vec2(0, 0)
        for thrust in self._thrust_overlays:
            accel_vec = thrust.get_acceleration(self._direction)
            thrust_velocity = thrust_velocity + (accel_vec * dt)

        # Calculate resist velocity
        resist_velocity = Vec2(0, 0)
        for resist in self._resist_overlays:
            resist_vec = resist.get_velocity(self._direction)
            resist_velocity = resist_velocity + resist_vec

        # Calculate boost velocity
        boost_velocity = Vec2(0, 0)
        for boost in self._boost_overlays:
            boost_velocity = boost_velocity + boost.get_velocity()

        # Combine all velocities
        total_velocity = cruise_velocity + thrust_velocity + resist_velocity + boost_velocity
        return total_velocity

    def bake(self) -> None:
        """Collapse all overlays into cruise velocity

        Takes the current total velocity (including thrust/resist/boost overlays)
        and bakes it into the cruise speed and direction, then clears all overlays.

        Useful for:
        - Converting temporary overlays into permanent cruise velocity
        - Simplifying state before making other changes
        - Preparing for a smooth stop

        Examples:
            rig.thrust(5).over(2000)  # Active thrust overlay
            rig.bake()                # Fold into cruise speed, clear overlay
        """
        total_vel = self._calculate_total_velocity()

        # Bake into cruise velocity
        magnitude = total_vel.magnitude()
        if magnitude > 1e-6:
            self._speed = magnitude
            self._direction = total_vel.normalized()
        else:
            self._speed = 0.0
            # Keep direction as-is when speed is zero

        # Clear all overlays
        self._thrust_overlays.clear()
        self._resist_overlays.clear()
        self._boost_overlays.clear()

    def _stop_immediate(self) -> None:
        """Internal: Immediate stop implementation"""
        # Stop movement
        self._speed = 0.0
        self._speed_transition = None
        self._accelerate_transition = None
        self._decelerate_transition = None
        self._direction_transition = None
        self._position_transitions.clear()

        # Clear overlays
        self._thrust_overlays.clear()
        self._resist_overlays.clear()
        self._boost_overlays.clear()

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

    def stop(self) -> StopBuilder:
        """Stop the rig

        By default stops immediately. Use .over() for smooth deceleration.

        Examples:
            rig.stop()                              # Instant stop
            rig.stop().over(500)                    # Smooth stop over 500ms
            rig.stop().over(500).ease("ease_out")   # Smooth stop with easing
            rig.stop().over(500).then(callback)     # Stop then callback
        """
        return StopBuilder(self, instant=True)

    def thrust(self, acceleration: float) -> ThrustBuilder:
        """Add temporary acceleration overlay

        Args:
            acceleration: Acceleration rate (speed units per second)

        Examples:
            rig.thrust(5).over(1000)              # Accelerate at 5 units/sec for 1 second
            rig.thrust(3).dir(1, 0).over(500)     # Thrust right for 0.5 seconds
        """
        return ThrustBuilder(self, acceleration)

    def resist(self, deceleration: float) -> ResistBuilder:
        """Add temporary deceleration overlay

        Args:
            deceleration: Deceleration rate (speed units per second)

        Examples:
            rig.resist(5).over(1000)              # Decelerate at 5 units/sec for 1 second
            rig.resist(3).dir(-1, 0).over(500)    # Resist in specific direction
        """
        return ResistBuilder(self, deceleration)

    def accelerate(self, rate: float) -> None:
        """Permanently increase cruise speed at rate (speed units per second)

        Args:
            rate: Speed increase rate per second

        Examples:
            rig.accelerate(5)     # Cruise speed increases by 5 units/sec continuously
        """
        self.start()  # Ensure ticking is active
        self._accelerate_transition = AccelerateTransition(rate)
        self._decelerate_transition = None  # Cancel any active deceleration

    def accel(self, rate: float) -> None:
        """Alias for accelerate()"""
        self.accelerate(rate)

    def decelerate(self, rate: float) -> None:
        """Permanently decrease cruise speed at rate (speed units per second)

        Args:
            rate: Speed decrease rate per second

        Examples:
            rig.decelerate(5)     # Cruise speed decreases by 5 units/sec until 0
        """
        self.start()  # Ensure ticking is active
        self._decelerate_transition = DecelerateTransition(rate)
        self._accelerate_transition = None  # Cancel any active acceleration

    def decel(self, rate: float) -> None:
        """Alias for decelerate()"""
        self.decelerate(rate)

    def boost(self, force: float) -> BoostBuilder:
        """Add instant velocity offset with decay

        Args:
            force: Initial velocity magnitude

        Examples:
            rig.boost(10).over(500)           # Burst of speed that decays over 0.5 sec
        """
        return BoostBuilder(self, force)

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

        # Check if speed is effectively zero
        if abs(self._speed) > epsilon:
            return False

        # Check for active transitions
        if self._speed_transition is not None:
            return False
        if self._direction_transition is not None:
            return False
        if self._accelerate_transition is not None:
            return False
        if self._decelerate_transition is not None:
            return False

        # Check for active overlays
        if len(self._thrust_overlays) > 0:
            return False
        if len(self._resist_overlays) > 0:
            return False
        if len(self._boost_overlays) > 0:
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

        # Update transitions (in precedence order: accelerate/decelerate > speed)
        if self._accelerate_transition:
            self._accelerate_transition.update(self, dt)
            # Accelerate never completes on its own (runs until cancelled)

        if self._decelerate_transition:
            self._decelerate_transition.update(self, dt)
            if self._decelerate_transition.complete:
                self._decelerate_transition = None

        if self._speed_transition:
            self._speed_transition.update(self)
            if self._speed_transition.complete:
                self._speed_transition = None

        if self._direction_transition:
            self._direction_transition.update(self)
            if self._direction_transition.complete:
                self._direction_transition = None

        # Calculate cruise velocity
        cruise_velocity = self._direction * self._speed

        # Apply thrust overlays (acceleration → velocity, then decay)
        thrust_velocity = Vec2(0, 0)
        for thrust in self._thrust_overlays[:]:
            thrust_velocity = thrust_velocity + thrust.update(self._direction, dt)
            if thrust.complete:
                self._thrust_overlays.remove(thrust)

        # Apply resist overlays (velocity offset)
        resist_velocity = Vec2(0, 0)
        for resist in self._resist_overlays[:]:
            resist_vec = resist.get_velocity(self._direction)
            resist_velocity = resist_velocity + resist_vec
            if resist.complete:
                self._resist_overlays.remove(resist)

        # Apply boost overlays (velocity)
        boost_velocity = Vec2(0, 0)
        for boost in self._boost_overlays[:]:
            boost_velocity = boost_velocity + boost.get_velocity()
            if boost.complete:
                self._boost_overlays.remove(boost)

        # Combine velocities
        total_velocity = cruise_velocity + thrust_velocity + resist_velocity + boost_velocity

        # Apply scale
        scale = settings.get("user.mouse_rig_scale")
        total_velocity = total_velocity * scale

        # Update position from velocity
        position_delta = total_velocity

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
