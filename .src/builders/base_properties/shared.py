"""Shared builders for base properties - common classes for speed and acceleration"""

from typing import Optional, Callable, Union, TYPE_CHECKING
from ..contracts import TimingMethodsContract, TransitionBasedBuilder, PropertyChainingContract, MultiSegmentMixin
from ..rate_utils import calculate_over_duration_for_property, calculate_revert_duration_for_property

if TYPE_CHECKING:
    from ...state import RigState


class SpeedAccelBuilder(MultiSegmentMixin['SpeedAccelBuilder'], TimingMethodsContract['SpeedAccelBuilder'], TransitionBasedBuilder, PropertyChainingContract):
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

        # Stage-specific callbacks - support multiple then() calls
        self._after_forward_callbacks: list[Callable] = []
        self._after_hold_callbacks: list[Callable] = []
        self._after_revert_callbacks: list[Callable] = []
        self._current_stage: str = "initial"  # Track what stage we're configuring

        # Named modifier
        self._effect_name: Optional[str] = None

        # Multi-segment support (reactive tag assignment)
        self.name: str = ""  # Auto-assigned when chaining begins
        self._is_chaining: bool = False  # Set to True by timing methods
        # Note: self.property_name already set above, used by mixin for error messages

    # ===== MultiSegmentMixin hooks =====

    def _get_queue_builder(self, queue_namespace):
        """Return property builder from queue namespace"""
        if self.property_name == "speed":
            return queue_namespace.speed
        elif self.property_name == "accel":
            return queue_namespace.accel
        else:
            raise ValueError(f"Unknown property: {self.property_name}")

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
            # Create temporary property effect using unified Effect
            from ...effects import Effect
            effect = Effect(
                property_name=self.property_name,
                operation=self.operation,
                value=value,
                name=self._effect_name
            )

            # UNIFIED: Configure lifecycle using single source of truth
            effect.configure_lifecycle(
                in_duration_ms=self._in_duration_ms,
                in_easing=self._in_easing,
                hold_duration_ms=self._hold_duration_ms,
                out_duration_ms=self._out_duration_ms,
                out_easing=self._out_easing,
                after_forward_callbacks=self._after_forward_callbacks if self._after_forward_callbacks else None,
                after_hold_callbacks=self._after_hold_callbacks if self._after_hold_callbacks else None,
                after_revert_callbacks=self._after_revert_callbacks if self._after_revert_callbacks else None
            )

            self.rig_state.start()
            self.rig_state._effects.append(effect)
            return

        # Permanent changes with transition (has .over())
        if self.property_name == "speed":
            from ...core import SpeedTransition
            current = self.rig_state._speed
            target = self._calculate_target_value(current, value)
            transition = SpeedTransition(current, target, self._in_duration_ms, self._in_easing)

            if self._after_forward_callbacks:
                def chain_callbacks():
                    for cb in self._after_forward_callbacks:
                        cb()
                transition.on_complete = chain_callbacks

            self.rig_state.start()
            self.rig_state._speed_transition = transition
        elif self.property_name == "accel":
            current = self.rig_state._accel
            target = self._calculate_target_value(current, value)
            self.rig_state._accel = target

            if self._after_forward_callbacks:
                for cb in self._after_forward_callbacks:
                    cb()

    def _execute_instant(self):
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

            max_speed = self.rig_state.limits_max_speed
            if max_speed is not None:
                target = min(target, max_speed)

            self.rig_state._speed = target
            self.rig_state.start()

            if self._after_forward_callbacks:
                for cb in self._after_forward_callbacks:
                    cb()
        elif self.property_name == "accel":
            current = self.rig_state._accel
            target = self._calculate_target_value(current, value)
            self.rig_state._accel = target

            if self._after_forward_callbacks:
                for cb in self._after_forward_callbacks:
                    cb()

    def _calculate_target_value(self, current: float, value: float) -> float:
        """Calculate the target value based on operation"""
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
        current = getattr(self.rig_state, f"_{self.property_name}")
        value = self.value
        if callable(value):
            if not hasattr(self.rig_state, '_state_accessor'):
                from ...state import StateAccessor
                self.rig_state._state_accessor = StateAccessor(self.rig_state)
            value = value(self.rig_state._state_accessor)

        target = self._calculate_target_value(current, value)

        return calculate_over_duration_for_property(
            self.property_name, current, target,
            rate_speed, rate_accel, rate_rotation
        )

    def _calculate_revert_duration_from_rate(self, rate_speed: Optional[float],
                                            rate_accel: Optional[float],
                                            rate_rotation: Optional[float]) -> Optional[float]:
        """Calculate revert duration from rate parameters"""
        current = getattr(self.rig_state, f"_{self.property_name}")
        return calculate_revert_duration_for_property(
            self.property_name, current,
            rate_speed, rate_accel, rate_rotation
        )

    def _after_over_configured(self, duration_ms: Optional[float], easing: str) -> None:
        """Hook called after over() - start rig execution"""
        # Don't execute immediately - let builder go out of scope and trigger __del__
        pass

    def _after_hold_configured(self, duration_ms: float) -> None:
        """Hook called after hold() - start rig execution"""
        # Don't execute immediately - let builder go out of scope and trigger __del__
        pass

    def _after_revert_configured(self, duration_ms: Optional[float], easing: str) -> None:
        """Hook called after revert() - start rig execution"""
        # Don't execute immediately - let builder go out of scope and trigger __del__
        pass

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
