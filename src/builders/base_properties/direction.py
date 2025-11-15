"""Direction builders for base rig - direction and rotation control"""

import math
from typing import Optional, Callable, TYPE_CHECKING
from ...core import (
    Vec2, clamp, DirectionTransition,
    _error_unknown_builder_attribute
)
from ...effects import DirectionEffect
from ..contracts import TimingMethodsContract, TransitionBasedBuilder

if TYPE_CHECKING:
    from ...state import RigState


class DirectionBuilder(TimingMethodsContract['DirectionBuilder'], TransitionBasedBuilder):
    """Builder for direction operations with .over() support"""
    def __init__(self, rig_state: 'RigState', target_direction: Vec2, instant: bool = False):
        self.rig_state = rig_state
        self.target_direction = target_direction.normalized()
        self._easing = "linear"
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
        """Execute with transition"""
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
                    duration_ms = 1  # Minimal duration for near-zero turns
                else:
                    duration_sec = angle_deg / self._rate_rotation
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

    def _execute_instant(self):
        """Execute instantly without transition"""
        self.rig_state._direction = self.target_direction
        self.rig_state._direction_transition = None
        self.rig_state.start()  # Ensure ticking is active

        # Execute callback immediately
        if self._then_callback:
            self._then_callback()

    def over(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> 'DirectionBuilder':
        """Rotate to target direction over time or at rate

        Args:
            duration_ms: Duration in milliseconds (time-based)
            easing: Easing function ('linear', 'ease_in', 'ease_out', 'ease_in_out', 'smoothstep')
            rate_rotation: Rotation rate in degrees/second (rate-based)

        Examples:
            rig.direction(0, 1).over(500)  # Rotate over 500ms
            rig.direction(0, 1).over(500, "ease_out")  # With easing
            rig.direction(0, 1).over(rate_rotation=90)  # At 90°/s
        """
        if duration_ms is not None and rate_rotation is not None:
            raise ValueError("Cannot specify both duration_ms and rate_rotation")
        if duration_ms is None and rate_rotation is None:
            raise ValueError("Must specify either duration_ms or rate_rotation")

        self._should_execute_instant = False
        self._duration_ms = duration_ms
        self._rate_rotation = rate_rotation
        self._easing = easing
        return self

    def hold(self, duration_ms: float) -> 'DirectionBuilder':
        """Hold at target direction for duration before reverting"""
        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"
        return self

    def revert(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> 'DirectionBuilder':
        """Revert to original direction after hold
        
        Args:
            duration_ms: Duration in milliseconds (time-based), 0 for instant
            easing: Easing function
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
        rate_provided = rate_rotation is not None
        if duration_ms is not None and rate_provided:
            raise ValueError("Cannot specify both duration_ms and rate_rotation")
        
        if rate_provided:
            # Calculate based on angle difference - for now use default
            duration_ms = 500  # TODO: Calculate based on current angle vs original
        
        self._out_duration_ms = duration_ms if duration_ms is not None and duration_ms > 0 else 0
        self._out_easing = easing
        self._current_stage = "after_revert"
        return self

    def then(self, callback: Callable) -> 'DirectionBuilder':
        """Execute callback at current point in lifecycle chain
        
        Can be called multiple times at different stages:
        - After .over(): fires when forward rotation completes
        - After .hold(): fires when hold period completes
        - After .revert(): fires when revert completes
        
        Examples:
            rig.direction.to(0, 1).over(500).then(cb1)
            rig.direction.to(0, 1).over(400).then(cb1).hold(100).then(cb2).revert(400).then(cb3)
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        return self

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._use_rate
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .rate).\n\n"
                    "Use separate statements:\n"
                    f"  rig.direction(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current direction change immediately
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
                return DirectionController(self.rig_state)

        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after 'direction'.\n\n"
                "Instead, use separate statements:\n"
                "    rig.direction(1, 0)\n"
                "    rig.{name}(...)"
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute('DirectionBuilder', name, 'over, then'))


class DirectionByBuilder(TimingMethodsContract['DirectionByBuilder'], TransitionBasedBuilder):
    """Builder for direction.by(degrees) - relative rotation"""
    def __init__(self, rig_state: 'RigState', degrees: float, instant: bool = False):
        self.rig_state = rig_state
        self.degrees = degrees
        self._easing = "linear"
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
            # Create and register temporary direction effect
            dir_effect = DirectionEffect(self.degrees)
            dir_effect.in_duration_ms = self._duration_ms  # Can be None for instant application
            dir_effect.in_easing = self._easing
            dir_effect.hold_duration_ms = self._hold_duration_ms

            # PRD5: .hold() alone implies instant revert after hold period
            if self._hold_duration_ms is not None and self._out_duration_ms is None:
                dir_effect.out_duration_ms = 0
            else:
                dir_effect.out_duration_ms = self._out_duration_ms
            dir_effect.out_easing = self._out_easing

            # Attach stage-specific callbacks
            dir_effect.after_forward_callback = self._after_forward_callback
            dir_effect.after_hold_callback = self._after_hold_callback
            dir_effect.after_revert_callback = self._after_revert_callback

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
                self._easing
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

    def over(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> 'DirectionByBuilder':
        """Rotate by degrees over time or at rate

        Args:
            duration_ms: Duration in milliseconds (time-based)
            easing: Easing function
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
        if duration_ms is not None and rate_rotation is not None:
            raise ValueError("Cannot specify both duration_ms and rate_rotation")

        self._should_execute_instant = False
        self._duration_ms = duration_ms
        self._rate_rotation = rate_rotation
        self._easing = easing
        return self

    def hold(self, duration_ms: float) -> 'DirectionByBuilder':
        """Hold rotation at full strength for duration"""
        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"
        return self

    def revert(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> 'DirectionByBuilder':
        """Revert to original direction - instant if duration=0, gradual otherwise

        Args:
            duration_ms: Duration in milliseconds (time-based), 0 for instant
            easing: Easing function
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
        if duration_ms is not None and rate_rotation is not None:
            raise ValueError("Cannot specify both duration_ms and rate_rotation")

        self._out_duration_ms = duration_ms if duration_ms is not None and duration_ms > 0 else 0
        self._out_rate_rotation = rate_rotation
        self._out_easing = easing
        self._current_stage = "after_revert"
        return self

    def then(self, callback: Callable) -> 'DirectionByBuilder':
        """Execute callback at current point in lifecycle chain
        
        Can be called multiple times at different stages:
        - After .over(): fires when forward rotation completes
        - After .hold(): fires when hold period completes
        - After .revert(): fires when revert completes
        
        Examples:
            rig.direction.by(90).over(500).then(cb1)
            rig.direction.by(90).over(400).then(cb1).hold(100).then(cb2).revert(400).then(cb3)
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        return self

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._rate_rotation is not None or
                self._hold_duration_ms is not None or
                self._out_duration_ms is not None
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.direction.by(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current direction change immediately
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
                return DirectionController(self.rig_state)

        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after 'direction.by()'.\n\n"
                "Instead, use separate statements."
            )

        raise AttributeError(_error_unknown_builder_attribute('DirectionByBuilder', name, 'over, hold, revert, then'))


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
