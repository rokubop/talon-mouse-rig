"""Base builders for mouse rig - property effects and direct property control"""

import time
import math
from typing import Optional, Callable, Union, TYPE_CHECKING
from talon import ctrl, cron

from ..core import (
    Vec2, EASING_FUNCTIONS, ease_linear, lerp, clamp, DEFAULT_EASING,
    SpeedTransition, DirectionTransition, PositionTransition,
    _error_cannot_chain_property, _error_unknown_builder_attribute
)
from ..effects import Effect, DirectionEffect

if TYPE_CHECKING:
    from ..state import RigState, StateAccessor

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
        self._wait_duration_ms: Optional[float] = None
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
                from .base import StateAccessor
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
                return SpeedController(self._rig)
            elif name == 'accel':
                return AccelController(self._rig)
            elif name == 'pos':
                return PositionController(self._rig)
            elif name == 'direction':
                return DirectionController(self._rig)

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
            self.rig_state.start()  # Ensure ticking is active

            # Execute callback immediately
            if self._then_callback:
                self._then_callback()

    def over(self, duration_ms: float, easing: str = "linear") -> 'DirectionBuilder':
        """Rotate to target direction over time

        Args:
            duration_ms: Duration in milliseconds
            easing: Easing function ('linear', 'ease_in', 'ease_out', 'ease_in_out', 'smoothstep')
        """
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
        self._should_execute_instant = False
        self._use_rate = True
        self._rate_degrees_per_second = degrees_per_second
        return self

    def then(self, callback: Callable) -> 'DirectionBuilder':
        """Execute callback after direction change completes"""
        self._then_callback = callback
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
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
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

        # Temporary effect support
        self._hold_duration_ms: Optional[float] = None
        self._out_duration_ms: Optional[float] = None
        self._out_easing: str = "linear"

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Ignore errors during cleanup

    def _execute(self):
        """Execute the configured operation"""
        # Check if this is a temporary effect (has .revert() or .hold())
        is_temporary = self._hold_duration_ms is not None or self._out_duration_ms is not None

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

            self.rig_state.start()
            self.rig_state._direction_effects.append(dir_effect)

            # TODO: Handle callback when effect completes
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
            self.rig_state.start()  # Ensure ticking is active

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

    def hold(self, duration_ms: float) -> 'DirectionByBuilder':
        """Hold rotation at full strength for duration"""
        self._hold_duration_ms = duration_ms
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'DirectionByBuilder':
        """Revert to original direction - instant if duration=0, gradual otherwise"""
        self._out_duration_ms = duration_ms if duration_ms > 0 else 0
        self._out_easing = easing
        return self

    def then(self, callback: Callable) -> 'DirectionByBuilder':
        """Execute callback after rotation completes"""
        self._then_callback = callback
        return self

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._use_rate or
                self._wait_duration_ms is not None or
                self._hold_duration_ms is not None or
                self._out_duration_ms is not None
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .rate, .wait, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.direction.by(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current direction change immediately
            self._execute()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
                return PositionController(self.rig_state)
            elif name == 'direction':
                return DirectionController(self.rig_state)

        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after 'direction.by()'.\n\n"
                "Instead, use separate statements."
            )

        raise AttributeError(_error_unknown_builder_attribute('DirectionByBuilder', name, 'over, rate, wait, hold, revert, then'))



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
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._wait_duration_ms is not None or
                self._hold_duration_ms is not None or
                self._revert_duration_ms is not None
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .wait, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.pos.to(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current position change immediately
            self._should_execute_instant = True

            # Trigger execution via __del__
            self.__del__()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
                return PositionController(self.rig_state)
            elif name == 'direction':
                return DirectionController(self.rig_state)

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
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._wait_duration_ms is not None or
                self._hold_duration_ms is not None or
                self._revert_duration_ms is not None
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .wait, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.pos.by(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current position change immediately
            self._should_execute_instant = True

            # Trigger execution via __del__
            self.__del__()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
                return PositionController(self.rig_state)
            elif name == 'direction':
                return DirectionController(self.rig_state)

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


# ============================================================================
# ENTITY BUILDER (PRD 8 - Named Effects)
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
            self.rig_state.start()  # Ensure ticking is active

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
