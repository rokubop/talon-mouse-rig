"""Direction builders for base rig - direction and rotation control"""

import math
from typing import Optional, Callable, TYPE_CHECKING
from ...core import Vec2, clamp, DirectionTransition
from ...effects import DirectionEffect
from ..contracts import TimingMethodsContract, TransitionBasedBuilder, PropertyChainingContract

if TYPE_CHECKING:
    from ...state import RigState


class DirectionBuilder(TimingMethodsContract['DirectionBuilder'], TransitionBasedBuilder, PropertyChainingContract):
    """Builder for direction operations with .over() support"""
    def __init__(self, rig_state: 'RigState', target_direction: Vec2, instant: bool = False):
        self.rig_state = rig_state
        self.target_direction = target_direction.normalized()
        self._easing = "linear"
        self._interpolation = "slerp"
        self._should_execute_instant = instant
        self._duration_ms: Optional[float] = None
        self._rate_rotation: Optional[float] = None

        # Temporary effect support
        self._hold_duration_ms: Optional[float] = None
        self._out_duration_ms: Optional[float] = None
        self._out_easing: str = "linear"

        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def _has_transition(self) -> bool:
        """Check if this builder should create a transition or effect"""
        return (self._duration_ms is not None or
                self._rate_rotation is not None or
                self._hold_duration_ms is not None or
                self._out_duration_ms is not None)

    def _has_instant(self) -> bool:
        """Check if this builder should execute instantly"""
        return self._should_execute_instant

    def _execute_transition(self):
        if self._duration_ms is not None or self._rate_rotation is not None:
            # Calculate duration from rate if needed
            duration_ms = self._duration_ms
            if self._rate_rotation is not None:
                current_dir = self.rig_state._direction
                dot = current_dir.dot(self.target_direction)
                dot = clamp(dot, -1.0, 1.0)
                angle_rad = math.acos(dot)
                angle_deg = math.degrees(angle_rad)

                if angle_deg < 0.1:
                    duration_ms = 1
                else:
                    duration_sec = angle_deg / self._rate_rotation
                    duration_ms = duration_sec * 1000

            transition = DirectionTransition(
                self.rig_state._direction,
                self.target_direction,
                duration_ms,
                self._easing,
                self._interpolation
            )
            self.rig_state.start()
            self.rig_state._direction_transition = transition

            if self._then_callback:
                transition.on_complete = self._then_callback

    def _execute_instant(self):
        self.rig_state._direction = self.target_direction
        self.rig_state._direction_transition = None
        self.rig_state.start()

        if self._then_callback:
            self._then_callback()

    # ===== Hooks for TimingMethodsContract =====

    def _before_over(
        self,
        duration_ms: Optional[float],
        easing: str,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> None:
        """Validate that either duration_ms or rate_rotation is provided"""
        if duration_ms is None and rate_rotation is None:
            raise ValueError("Must specify either duration_ms or rate_rotation")

    def _calculate_over_duration_from_rate(
        self,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> float:
        """Calculate duration from rotation rate based on angle to target"""
        if rate_rotation is not None:
            self._rate_rotation = rate_rotation
            return None
        return 500.0

    def _store_over_config(self, duration_ms: Optional[float], easing: str, interpolation: str = "slerp") -> None:
        """Store in _duration_ms (not _in_duration_ms) and disable instant execution"""
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        self._easing = easing
        self._interpolation = interpolation

    # No custom behavior needed for hold/revert - using base implementation

    def _calculate_revert_duration_from_rate(self, rate_speed: Optional[float],
                                            rate_accel: Optional[float],
                                            rate_rotation: Optional[float]) -> Optional[float]:
        """Calculate revert duration from rotation rate"""
        if rate_rotation is not None:
            return 500.0
        return None

    # ===== PropertyChainingContract hooks =====

    def _has_timing_configured(self) -> bool:
        """Check if any timing has been configured"""
        return self._duration_ms is not None or self._use_rate

    def _execute_for_chaining(self) -> None:
        """Execute immediately for property chaining"""
        self._execute()


class DirectionByBuilder(TimingMethodsContract['DirectionByBuilder'], TransitionBasedBuilder, PropertyChainingContract):
    """Builder for direction.by(degrees) - relative rotation"""
    def __init__(self, rig_state: 'RigState', degrees: float, instant: bool = False):
        self.rig_state = rig_state
        self.degrees = degrees
        self._easing = "linear"
        self._interpolation = "slerp"
        self._should_execute_instant = instant
        self._duration_ms: Optional[float] = None
        self._rate_rotation: Optional[float] = None

        # Temporary effect support
        self._hold_duration_ms: Optional[float] = None
        self._out_duration_ms: Optional[float] = None
        self._out_easing: str = "linear"
        self._out_rate_rotation: Optional[float] = None

        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def _has_transition(self) -> bool:
        """Check if this builder should create a transition"""
        # DirectionByBuilder uses effect system for temporary changes
        return (self._hold_duration_ms is not None or self._out_duration_ms is not None or
                self._duration_ms is not None or self._rate_rotation is not None)

    def _has_instant(self) -> bool:
        """Check if this builder should execute instantly"""
        return self._should_execute_instant

    def _execute_transition(self):
        """Execute with transition or effect"""
        # Check if this is a temporary effect
        is_temporary = (self._hold_duration_ms is not None or self._out_duration_ms is not None)

        if is_temporary:
            dir_effect = DirectionEffect(self.degrees)

            dir_effect.configure_lifecycle(
                in_duration_ms=self._duration_ms,
                in_easing=self._easing,
                hold_duration_ms=self._hold_duration_ms,
                out_duration_ms=0 if (self._hold_duration_ms is not None and self._out_duration_ms is None) else self._out_duration_ms,
                out_easing=self._out_easing,
                after_forward_callback=self._after_forward_callback,
                after_hold_callback=self._after_hold_callback,
                after_revert_callback=self._after_revert_callback
            )

            self.rig_state.start()
            self.rig_state._direction_effects.append(dir_effect)
            return

        # Non-temporary: permanent rotation
        # Calculate target direction from current + degrees
        current_dir = self.rig_state._direction
        angle_rad = math.radians(self.degrees)

        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        new_x = current_dir.x * cos_a - current_dir.y * sin_a
        new_y = current_dir.x * sin_a + current_dir.y * cos_a

        target_direction = Vec2(new_x, new_y).normalized()

        if self._duration_ms is not None or self._rate_rotation is not None:
            # Calculate duration from rate if needed
            duration_ms = self._duration_ms
            if self._rate_rotation is not None:
                angle_deg = abs(self.degrees)
                if angle_deg < 0.1:
                    duration_ms = 1  # Minimal duration for near-zero turns
                else:
                    duration_sec = angle_deg / self._rate_rotation
                    duration_ms = duration_sec * 1000

            # Create transition
            transition = DirectionTransition(
                self.rig_state._direction,
                target_direction,
                duration_ms,
                self._easing,
                self._interpolation
            )
            self.rig_state.start()
            self.rig_state._direction_transition = transition

            # Register callback
            if self._after_forward_callback:
                transition.on_complete = self._after_forward_callback

    def _execute_instant(self):
        """Execute instantly without transition"""
        # Instant rotation
        current_dir = self.rig_state._direction
        angle_rad = math.radians(self.degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        new_x = current_dir.x * cos_a - current_dir.y * sin_a
        new_y = current_dir.x * sin_a + current_dir.y * cos_a
        self.rig_state._direction = Vec2(new_x, new_y).normalized()
        self.rig_state._direction_transition = None
        self.rig_state.start()  # Ensure ticking is active

        if self._after_forward_callback:
            self._after_forward_callback()

    # ===== Hooks for TimingMethodsContract =====

    def _calculate_over_duration_from_rate(
        self,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> float:
        """Calculate duration from rotation rate based on angle"""
        if rate_rotation is not None:
            # Store rate for later use
            self._rate_rotation = rate_rotation
            # Return None to calculate later during execution
            return None
        return 500.0

    def _store_over_config(self, duration_ms: Optional[float], easing: str, interpolation: str = "slerp") -> None:
        """Store in _duration_ms and disable instant execution"""
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        self._easing = easing
        self._interpolation = interpolation

    def _calculate_revert_duration_from_rate(self, rate_speed: Optional[float],
                                            rate_accel: Optional[float],
                                            rate_rotation: Optional[float]) -> Optional[float]:
        """Calculate revert duration from rotation rate"""
        if rate_rotation is not None:
            return 500.0  # TODO: Calculate based on angle difference
        return None

    # ===== PropertyChainingContract hooks =====

    def _has_timing_configured(self) -> bool:
        """Check if any timing has been configured"""
        return (
            self._duration_ms is not None or
            self._rate_rotation is not None or
            self._hold_duration_ms is not None or
            self._out_duration_ms is not None
        )

    def _execute_for_chaining(self) -> None:
        """Execute immediately for property chaining"""
        self._execute()


class DirectionController:
    """Controller for direction operations (accessed via rig.direction)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, x: float, y: float) -> DirectionBuilder:
        """Set direction instantly or return builder for .over() (legacy shorthand for .to())"""
        return DirectionBuilder(self.rig_state, Vec2(x, y), instant=True)

    def to(self, x: float, y: float) -> DirectionBuilder:
        """Set direction to absolute vector (can use with .over(), .rate(), .then())"""
        return DirectionBuilder(self.rig_state, Vec2(x, y), instant=True)

    def by(self, degrees: float) -> DirectionByBuilder:
        """Rotate by relative angle in degrees (alias for .add())

        Positive = clockwise, Negative = counter-clockwise

        Examples:
            rig.direction.by(90)              # Rotate 90° clockwise instantly
            rig.direction.by(-45).over(500)   # Rotate 45° counter-clockwise over 500ms
            rig.direction.by(180).rate(90)    # Rotate 180° at 90°/sec
        """
        return DirectionByBuilder(self.rig_state, degrees, instant=True)

    def add(self, degrees: float) -> DirectionByBuilder:
        """Add angle in degrees - clockwise rotation

        Examples:
            rig.direction.add(90)             # Rotate 90° clockwise
            rig.direction.add(45).over(500)   # Rotate 45° clockwise over 500ms
        """
        return DirectionByBuilder(self.rig_state, degrees, instant=True)

    def sub(self, degrees: float) -> DirectionByBuilder:
        """Subtract angle in degrees - counter-clockwise rotation

        Examples:
            rig.direction.sub(90)             # Rotate 90° counter-clockwise
            rig.direction.sub(45).over(500)   # Rotate 45° counter-clockwise over 500ms
        """
        return DirectionByBuilder(self.rig_state, -degrees, instant=True)
