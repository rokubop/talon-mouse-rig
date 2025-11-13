"""Shared builders for base properties - common classes for speed and acceleration"""

from typing import Optional, Callable, Union, TYPE_CHECKING
from ..contracts import TimingMethodsContract

if TYPE_CHECKING:
    from ...state import RigState


class PropertyEffectBuilder(TimingMethodsContract['PropertyEffectBuilder']):
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
                from ...state import StateAccessor
                self.rig_state._state_accessor = StateAccessor(self.rig_state)
            value = value(self.rig_state._state_accessor)

        # Determine if this is a temporary effect (has .hold() or .revert())
        is_temporary = (self._hold_duration_ms is not None or self._out_duration_ms is not None)

        if is_temporary:
            # Create temporary property effect
            from ...effects import PropertyEffect
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
                from ...core import SpeedTransition
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

    def over(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> 'PropertyEffectBuilder':
        """Apply change over duration or at rate - can be permanent or temporary based on .revert()/.hold()

        Args:
            duration_ms: Duration in milliseconds (time-based)
            easing: Easing function
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
        """
        # Validate inputs
        rate_provided = rate_speed is not None or rate_accel is not None
        if duration_ms is not None and rate_provided:
            raise ValueError("Cannot specify both duration_ms and rate parameters")

        # Calculate duration from rate if provided
        if rate_provided:
            rate_value = rate_speed if rate_speed is not None else rate_accel
            rate_property = "speed" if rate_speed is not None else "accel"

            if rate_property != self.property_name:
                raise ValueError(f"Rate parameter mismatch: trying to use rate_{rate_property} on {self.property_name} property")

            # Get current and target values
            current = getattr(self.rig_state, f"_{self.property_name}")
            value = self.value
            if callable(value):
                if not hasattr(self.rig_state, '_state_accessor'):
                    from ...state import StateAccessor
                    self.rig_state._state_accessor = StateAccessor(self.rig_state)
                value = value(self.rig_state._state_accessor)

            target = self._calculate_target_value(current, value)
            delta = abs(target - current)

            if delta < 0.01:
                duration_ms = 1
            else:
                duration_sec = delta / rate_value
                duration_ms = duration_sec * 1000

        self._in_duration_ms = duration_ms
        self._in_easing = easing
        return self

    def hold(self, duration_ms: float) -> 'PropertyEffectBuilder':
        """Hold effect at full strength for duration"""
        self._hold_duration_ms = duration_ms
        return self

    def revert(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> 'PropertyEffectBuilder':
        """Revert to original value - instant if duration=0, gradual otherwise

        Args:
            duration_ms: Duration in milliseconds (time-based), 0 for instant
            easing: Easing function
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
        """
        # For revert, rate-based doesn't make as much sense since we're going back to original
        # But we'll support it for consistency
        rate_provided = rate_speed is not None or rate_accel is not None
        if duration_ms is not None and rate_provided:
            raise ValueError("Cannot specify both duration_ms and rate parameters")

        if rate_provided:
            # Just use a default duration for now - proper implementation would calculate based on current delta
            duration_ms = 500  # TODO: Calculate based on current value vs original

        self._out_duration_ms = duration_ms if duration_ms is not None and duration_ms > 0 else 0
        self._out_easing = easing
        return self

    def then(self, callback: Callable) -> 'PropertyEffectBuilder':
        """Execute callback after property change completes"""
        self._then_callback = callback
        return self

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        from ...core import _error_unknown_builder_attribute

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
                from .speed import SpeedController
                return SpeedController(self.rig_state)
            elif name == 'accel':
                from .accel import AccelController
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
            'over, hold, revert, then'
        ))
