"""Speed builder for base rig - speed control"""

from typing import Optional, Callable, TYPE_CHECKING
from ...core import DEFAULT_EASING, SpeedTransition
from .shared import PropertyEffectBuilder

if TYPE_CHECKING:
    from ...state import RigState


class SpeedBuilder:
    """Builder for speed operations with .over() support"""
    def __init__(self, rig_state: 'RigState', target_speed: float, instant: bool = False):
        self.rig_state = rig_state
        self.target_speed = target_speed
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
            self.rig_state.start()  # Ensure ticking is active

            # Execute callback immediately
            if self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float) -> 'SpeedBuilder':
        """Ramp to target speed over time"""
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'SpeedBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def then(self, callback: Callable) -> 'SpeedBuilder':
        """Execute callback after speed change completes"""
        self._then_callback = callback
        return self


class SpeedController:
    """Controller for speed operations (accessed via rig.speed)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, value: float) -> SpeedBuilder:
        """Set speed instantly or return builder for .over()"""
        return SpeedBuilder(self.rig_state, value, instant=True)

    def add(self, delta: float) -> PropertyEffectBuilder:
        """Add delta to current speed"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", delta)

    def subtract(self, delta: float) -> PropertyEffectBuilder:
        """Subtract from current speed"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", -delta)

    def sub(self, delta: float) -> PropertyEffectBuilder:
        """Subtract from current speed (shorthand for subtract)"""
        return self.subtract(delta)

    def mul(self, factor: float) -> PropertyEffectBuilder:
        """Multiply speed by factor"""
        return PropertyEffectBuilder(self.rig_state, "speed", "mul", factor)

    def div(self, divisor: float) -> PropertyEffectBuilder:
        """Divide speed by divisor"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide speed by zero")
        return PropertyEffectBuilder(self.rig_state, "speed", "div", divisor)

    def to(self, value: float) -> PropertyEffectBuilder:
        """Set speed to absolute value (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "to", value)

    def by(self, delta: float) -> PropertyEffectBuilder:
        """Add delta to speed (alias for .add())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", delta)
