"""Shared builders for base properties - common classes for speed and acceleration"""

from typing import Optional, Callable, Union, TYPE_CHECKING
from ..contracts import TimingMethodsContract, TransitionBasedBuilder, PropertyChainingContract

if TYPE_CHECKING:
    from ...state import RigState


class PropertyEffectBuilder(TimingMethodsContract['PropertyEffectBuilder'], TransitionBasedBuilder, PropertyChainingContract):
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

        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

        # Named modifier
        self._effect_name: Optional[str] = None

    def _has_transition(self) -> bool:
        """Check if this builder should create a transition or effect"""
        if self._instant_done:
            return False
        # Has transition if has timing OR is temporary (hold/revert)
        return (self._in_duration_ms is not None or
                self._hold_duration_ms is not None or
                self._out_duration_ms is not None)

    def _has_instant(self) -> bool:
        """Check if this builder should execute instantly"""
        # Execute instantly if not already done and no timing
        return not self._instant_done and not self._has_transition()

    def _execute_transition(self):
        """Execute with transition or effect"""
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

            # Attach stage-specific callbacks
            effect.after_forward_callback = self._after_forward_callback
            effect.after_hold_callback = self._after_hold_callback
            effect.after_revert_callback = self._after_revert_callback

            self.rig_state.start()
            self.rig_state._property_effects.append(effect)
            return

        # Permanent changes with transition (has .over())
        if self.property_name == "speed":
            from ...core import SpeedTransition
            current = self.rig_state._speed
            target = self._calculate_target_value(current, value)
            transition = SpeedTransition(current, target, self._in_duration_ms, self._in_easing)

            # Register callback with transition if set
            if self._after_forward_callback:
                transition.on_complete = self._after_forward_callback

            self.rig_state.start()
            self.rig_state._speed_transition = transition
        elif self.property_name == "accel":
            # TODO: Add accel transition support if needed
            current = self.rig_state._accel
            target = self._calculate_target_value(current, value)
            self.rig_state._accel = target

            if self._after_forward_callback:
                self._after_forward_callback()

    def _execute_instant(self):
        """Execute instantly without transition"""
        # Evaluate value if it's a callable (lambda)
        value = self.value
        if callable(value):
            if not hasattr(self.rig_state, '_state_accessor'):
                from ...state import StateAccessor
                self.rig_state._state_accessor = StateAccessor(self.rig_state)
            value = value(self.rig_state._state_accessor)

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

            if self._after_forward_callback:
                self._after_forward_callback()
        elif self.property_name == "accel":
            current = self.rig_state._accel
            target = self._calculate_target_value(current, value)
            self.rig_state._accel = target

            if self._after_forward_callback:
                self._after_forward_callback()

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

    # ===== Hooks for TimingMethodsContract =====

    def _calculate_over_duration_from_rate(
        self,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> float:
        """Calculate duration from rate based on delta between current and target"""
        rate_provided = rate_speed is not None or rate_accel is not None
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
                return 1.0
            else:
                duration_sec = delta / rate_value
                return duration_sec * 1000
        return 500.0

    def _calculate_revert_duration_from_rate(self, rate_speed: Optional[float],
                                            rate_accel: Optional[float],
                                            rate_rotation: Optional[float]) -> Optional[float]:
        """Calculate revert duration from rate parameters"""
        rate_provided = rate_speed is not None or rate_accel is not None
        if rate_provided:
            # Just use a default duration for now - proper implementation would calculate based on current delta
            return 500.0  # TODO: Calculate based on current value vs original
        return None

    # ===== PropertyChainingContract hooks =====

    def _has_timing_configured(self) -> bool:
        """Check if any timing has been configured"""
        return (
            self._hold_duration_ms is not None or
            self._out_duration_ms is not None or
            self._in_duration_ms is not None or
            self._in_easing != "linear"
        )

    def _execute_for_chaining(self) -> None:
        """Execute immediately for property chaining"""
        self._execute()
