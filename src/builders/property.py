"""Property builders for base rig - speed and acceleration control"""

import time
from typing import Optional, Callable, Union, TYPE_CHECKING
from talon import ctrl, cron

from ..core import (
    Vec2, DEFAULT_EASING, SpeedTransition,
    _error_unknown_builder_attribute
)

if TYPE_CHECKING:
    from ..state import RigState


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

        # Callback support
        self._then_callback: Optional[Callable] = None

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

        # Evaluate value if it's a callable (lambda)
        value = self.value
        if callable(value):
            if not hasattr(self.rig_state, '_state_accessor'):
                from ..state import StateAccessor
                self.rig_state._state_accessor = StateAccessor(self.rig_state)
            value = value(self.rig_state._state_accessor)

        # Determine if this is a temporary effect (has .hold() or .revert())
        is_temporary = (self._hold_duration_ms is not None or self._out_duration_ms is not None)

        if is_temporary:
            # Create temporary property effect
            from ..effects import PropertyEffect
            effect = PropertyEffect(self.property_name, self.operation, value, self._effect_name)
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
            self.rig_state._property_effects.append(effect)
            return

        # Permanent changes (no .hold() or .revert())
        if self._in_duration_ms is not None:
            # Transition over time
            if self.property_name == "speed":
                current = self.rig_state._speed
                target = self._calculate_target_value(current, value)
                transition = SpeedTransition(current, target, self._in_duration_ms, self._in_easing)

                # Register callback with transition if set
                if self._then_callback:
                    transition.on_complete = self._then_callback

                self.rig_state.start()
                self.rig_state._speed_transition = transition
            elif self.property_name == "accel":
                # TODO: Add accel transition support if needed
                current = self.rig_state._accel
                target = self._calculate_target_value(current, value)
                self.rig_state._accel = target

                if self._then_callback:
                    self._then_callback()
        else:
            # Immediate execution (no .over() timing specified)
            if self.property_name == "speed":
                current = self.rig_state._speed
                target = self._calculate_target_value(current, value)
                target = max(0.0, target)

                # Apply speed limit if set
                max_speed = self.rig_state.limits_max_speed
                if max_speed is not None:
                    target = min(target, max_speed)

                self.rig_state._speed = target
                self.rig_state.start()  # Ensure ticking is active

                if self._then_callback:
                    self._then_callback()
            elif self.property_name == "accel":
                current = self.rig_state._accel
                target = self._calculate_target_value(current, value)
                self.rig_state._accel = target

                if self._then_callback:
                    self._then_callback()

    def _calculate_target_value(self, current: float, value: float) -> float:
        """Calculate the target value based on operation (value already evaluated)"""
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
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._hold_duration_ms is not None or
                self._out_duration_ms is not None or
                self._in_duration_ms is not None or
                self._in_easing != "linear"
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .in_out, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.{self.property_name}(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current property change immediately
            self._execute()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
                from .position import PositionController
                return PositionController(self.rig_state)
            elif name == 'direction':
                from .direction import DirectionController
                return DirectionController(self.rig_state)

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
            target = self._builder._calculate_target_value(current, self._builder.value)
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
            target = self._builder._calculate_target_value(current, self._builder.value)
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

    def add(self, delta: float) -> 'PropertyEffectBuilder':
        """Add to current speed (alias for .by())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", delta)

    def subtract(self, delta: float) -> 'PropertyEffectBuilder':
        """Subtract from current speed"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", -delta)

    def sub(self, delta: float) -> 'PropertyEffectBuilder':
        """Subtract from current speed (shorthand for subtract)"""
        return self.subtract(delta)

    def multiply(self, factor: float) -> 'PropertyEffectBuilder':
        """Multiply current speed by factor (alias for .mul())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "mul", factor)

    def mul(self, factor: float) -> 'PropertyEffectBuilder':
        """Multiply speed by factor (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "mul", factor)

    def divide(self, divisor: float) -> 'PropertyEffectBuilder':
        """Divide current speed by divisor (alias for .div())"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide speed by zero")
        return PropertyEffectBuilder(self.rig_state, "speed", "div", divisor)

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
