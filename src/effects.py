"""Effect system for mouse rig - temporary property modifications"""

import time
import math
from typing import Optional, Union, Literal, Callable, TYPE_CHECKING
from dataclasses import dataclass, field

from .core import Vec2, EASING_FUNCTIONS, ease_linear, lerp

if TYPE_CHECKING:
    from .state import RigState


# ============================================================================
# EFFECT STACK (tracks operation stacking for effects)
# ============================================================================

@dataclass
class EffectStack:
    """
    Tracks stacking behavior for effect operations.

    Default on-repeat strategy = unlimited stacking
    - .to(value): Set absolute value (stacking has no effect - always sets to same value)
    - .mul(value): Multiply (stacks by default - unlimited)
    - .div(value): Divide (stacks by default - unlimited)
    - .add(value): Add (stacks by default - unlimited)
    - .sub(value): Subtract (stacks by default - unlimited)

    On-Repeat Strategies:
    - Default: max_stack_count = None (unlimited stacking)
    - .on_repeat("stack", n): max_stack_count = n (max n stacks)
    - .on_repeat("replace"): max_stack_count = 1 (calling same operation replaces previous)

    For effects:
    - Multiplicative ops (.mul/.div) are summed: base * (1.0 + sum of multipliers)
    - Additive ops (.add/.sub) are summed: base + sum of additions
    - Absolute ops (.to) set value directly

    For vectors (direction, position), stores Vec2 objects.
    """
    name: str  # Entity name
    property: str  # "speed", "accel", "direction", "pos"
    operation_type: str  # "mul", "div", "add", "sub", "to"

    # Values (scalar or vector) - stacking controlled by max_stack_count
    values: list[Union[float, 'Vec2']] = field(default_factory=list)

    # Constraints
    max_value: Optional[float] = None  # Maximum computed value
    max_stack_count: Optional[int] = None  # Default: None (unlimited stacking)

    def add_operation(self, value: Union[float, 'Vec2']) -> None:
        """Add a new operation (stacks with existing)"""
        self.values.append(value)

        # Enforce max stack count
        if self.max_stack_count is not None and len(self.values) > self.max_stack_count:
            # Keep only the most recent values up to max
            self.values = self.values[-self.max_stack_count:]

    def get_total(self) -> Union[float, 'Vec2']:
        """Get total computed value for this operation type"""
        if not self.values:
            return self._get_zero_value()

        # For mul/div, multiply all values together (multiplicative stacking)
        if self.operation_type in ["mul", "div"]:
            if isinstance(self.values[0], Vec2):
                # Not typical, but if needed, sum for vectors
                value = Vec2(0, 0)
                for v in self.values:
                    value = value + v
            else:
                # Multiply scalars: [2, 1.5] → 2 * 1.5 = 3.0
                value = 1.0
                for v in self.values:
                    value *= v
        else:
            # For add/sub, sum all values (additive stacking)
            if isinstance(self.values[0], Vec2):
                value = Vec2(0, 0)
                for v in self.values:
                    value = value + v
            else:
                value = sum(self.values)

        # Apply max constraint (scalars only)
        if self.max_value is not None and isinstance(value, float):
            value = min(value, self.max_value)

        return value

    def _get_zero_value(self) -> Union[float, 'Vec2']:
        """Get zero value appropriate for property type"""
        if self.property in ["direction", "pos"]:
            return Vec2(0, 0)
        return 0.0

    def apply_to_base(self, base_value: Union[float, 'Vec2']) -> Union[float, 'Vec2']:
        """Apply this effect to a base value"""
        total = self.get_total()

        if self.operation_type in ["mul", "div"]:
            # Multiplicative: base * total
            # For .mul(2), total = 2, so base * 2 (double)
            # For .div(2), stores 1/2 = 0.5, so base * 0.5 (half)
            # Multiple .mul() calls stack multiplicatively via product
            if isinstance(base_value, Vec2):
                # For vectors, scale the magnitude
                multiplier = total if isinstance(total, float) else 1.0
                result = base_value * multiplier
            else:
                result = base_value * total
        elif self.operation_type in ["add", "sub"]:
            # Additive: base + total
            if isinstance(base_value, Vec2) and isinstance(total, Vec2):
                result = base_value + total
            else:
                result = base_value + total
        else:
            result = base_value

        # Apply max value constraint for final result (scalars only)
        if self.max_value is not None and isinstance(result, float):
            result = min(result, self.max_value)

        return result


class EffectLifecycle:
    """
    Wrapper for EffectStack with lifecycle support.
    Now uses the unified Effect class internally.
    """
    def __init__(self, stack: EffectStack, rig_state: 'RigState'):
        self.stack = stack
        self.rig_state = rig_state
        # Create unified Effect for stack-based lifecycle
        self._effect = Effect(stack=stack)

        # Repeat strategy configuration
        self.repeat_strategy: str = "stack"  # Default: unlimited stacking
        self.throttle_ms: Optional[float] = None  # For throttle strategy
        self.last_activation_time: Optional[float] = None  # Track last activation

    # Delegate lifecycle configuration to unified Effect
    @property
    def in_duration_ms(self):
        return self._effect.in_duration_ms

    @in_duration_ms.setter
    def in_duration_ms(self, value):
        self._effect.in_duration_ms = value

    @property
    def in_easing(self):
        return self._effect.in_easing

    @in_easing.setter
    def in_easing(self, value):
        self._effect.in_easing = value

    @property
    def hold_duration_ms(self):
        return self._effect.hold_duration_ms

    @hold_duration_ms.setter
    def hold_duration_ms(self, value):
        self._effect.hold_duration_ms = value

    @property
    def out_duration_ms(self):
        return self._effect.out_duration_ms

    @out_duration_ms.setter
    def out_duration_ms(self, value):
        self._effect.out_duration_ms = value

    @property
    def out_easing(self):
        return self._effect.out_easing

    @out_easing.setter
    def out_easing(self, value):
        self._effect.out_easing = value

    @property
    def phase(self):
        return self._effect.phase

    @property
    def complete(self):
        return self._effect.complete

    @property
    def current_multiplier(self):
        return self._effect.current_multiplier

    @property
    def after_forward_callbacks(self):
        return self._effect.after_forward_callbacks

    @property
    def after_hold_callbacks(self):
        return self._effect.after_hold_callbacks

    @property
    def after_revert_callbacks(self):
        return self._effect.after_revert_callbacks

    def configure_lifecycle(
        self,
        in_duration_ms: Optional[float] = None,
        in_easing: str = "linear",
        hold_duration_ms: Optional[float] = None,
        out_duration_ms: Optional[float] = None,
        out_easing: str = "linear",
        after_forward_callbacks: Optional[list[Callable]] = None,
        after_hold_callbacks: Optional[list[Callable]] = None,
        after_revert_callbacks: Optional[list[Callable]] = None
    ) -> None:
        """Configure lifecycle - delegates to unified Effect"""
        self._effect.configure_lifecycle(
            in_duration_ms=in_duration_ms,
            in_easing=in_easing,
            hold_duration_ms=hold_duration_ms,
            out_duration_ms=out_duration_ms,
            out_easing=out_easing,
            after_forward_callbacks=after_forward_callbacks,
            after_hold_callbacks=after_hold_callbacks,
            after_revert_callbacks=after_revert_callbacks
        )

    def start(self) -> None:
        """Start the effect lifecycle"""
        self._effect.start()

    def update(self) -> float:
        """Update lifecycle and return current multiplier

        Queue strategy now uses RigState._segment_queues for unified queuing.
        """
        multiplier = self._effect.update()
        return multiplier

    def request_stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Request the effect to stop"""
        self._effect.request_stop(duration_ms, easing)

    def apply_to_base(self, base_value: float) -> float:
        """Apply effect with current multiplier"""
        if self._effect.current_multiplier == 0.0:
            return base_value

        # Get the full effect value
        full_effect = self.stack.apply_to_base(base_value)

        # Interpolate between base and full effect based on multiplier
        return lerp(base_value, full_effect, self._effect.current_multiplier)

    def should_accept_new_operation(self) -> bool:
        """Check if a new operation should be accepted based on repeat strategy

        Returns:
            True if operation should be processed, False if it should be rejected
        """
        current_time = time.perf_counter()

        # Stack/replace: always accept (handled by max_stack_count)
        if self.repeat_strategy in ("stack", "replace"):
            self.last_activation_time = current_time
            return True

        # Ignore: reject if effect is currently active
        if self.repeat_strategy == "ignore":
            if self._effect.phase not in ("not_started", "complete"):
                return False  # Effect is active, ignore
            self.last_activation_time = current_time
            return True

        # Throttle: reject if called too soon after last activation
        if self.repeat_strategy == "throttle":
            if self.throttle_ms is None:
                raise ValueError("Throttle strategy requires throttle_ms to be set")
            if self.last_activation_time is not None:
                elapsed_ms = (current_time - self.last_activation_time) * 1000
                if elapsed_ms < self.throttle_ms:
                    return False  # Too soon, throttle
            self.last_activation_time = current_time
            return True

        # Extend/queue: always accept (special handling in apply_operation_with_strategy)
        if self.repeat_strategy in ("extend", "queue"):
            self.last_activation_time = current_time
            return True

        # Unknown strategy
        return True

    def apply_operation_with_strategy(self, value: Union[float, Vec2]) -> None:
        """Apply operation according to repeat strategy

        Handles the actual operation based on the configured strategy.
        Called after should_accept_new_operation returns True.
        """
        # For stack/replace/ignore/throttle: just add the operation normally
        if self.repeat_strategy in ("stack", "replace", "ignore", "throttle"):
            self.stack.add_operation(value)
            return

        # Extend: add operation and extend the hold duration
        if self.repeat_strategy == "extend":
            self.stack.add_operation(value)
            if self._effect.phase == "hold" and self.hold_duration_ms is not None:
                # Extend hold by resetting the phase start time
                self._effect.phase_start_time = time.perf_counter()
            elif self._effect.phase == "out":
                # Cancel revert, go back to hold
                if self.hold_duration_ms is not None:
                    self._effect.phase = "hold"
                    self._effect.phase_start_time = time.perf_counter()
                    self._effect.current_multiplier = 1.0
            return

        # Queue: use unified RigState queue system
        if self.repeat_strategy == "queue":
            if self._effect.phase in ("not_started", "complete"):
                # No active effect, apply immediately
                self.stack.add_operation(value)
            else:
                # Effect is active, queue callback to RigState
                tag_name = self.stack.name
                def apply_queued_value():
                    self.stack.add_operation(value)
                    # Restart the lifecycle for the queued operation
                    self._effect.complete = False
                    self._effect.phase = "not_started"
                    self._effect.start()
                self.rig_state._queue_segment(tag_name, apply_queued_value)
            return


# ============================================================================
# UNIFIED EFFECT SYSTEM
# ============================================================================

class Effect:
    """
    Unified effect system supporting both:
    - Scalar property effects (speed, accel) with operations (to/by/mul/div)
    - Effect stack lifecycle (for named effects with on-repeat strategies)

    Provides lifecycle support: in → hold → out → complete
    """
    def __init__(
        self,
        property_name: Optional[str] = None,
        operation: Optional[str] = None,
        value: Optional[float] = None,
        stack: Optional['EffectStack'] = None,
        name: Optional[str] = None
    ):
        # Effect type determination
        self.is_property_effect = property_name is not None
        self.is_stack_effect = stack is not None

        # Property effect fields
        self.property_name = property_name  # "speed", "accel", etc.
        self.operation = operation  # "to", "by", "mul", "div"
        self.value = value
        self.base_value: Optional[float] = None  # For property effects

        # Stack effect fields
        self.stack = stack  # For named effects with stacks

        # Common
        self.name = name  # Optional name for stopping early

        # Lifecycle configuration
        self.in_duration_ms: Optional[float] = None
        self.in_easing: str = "linear"
        self.hold_duration_ms: Optional[float] = None
        self.out_duration_ms: Optional[float] = None
        self.out_easing: str = "linear"

        # Stage-specific callbacks (for property effects) - now supports multiple
        self.after_forward_callbacks: list[Callable] = []
        self.after_hold_callbacks: list[Callable] = []
        self.after_revert_callbacks: list[Callable] = []

        # Runtime state
        self.phase: str = "not_started"  # "in", "hold", "out", "complete"
        self.phase_start_time: Optional[float] = None
        self.current_multiplier: float = 0.0  # 0 to 1, how much of the effect is active
        self.complete = False

        # For stopping
        self.stop_requested = False
        self.stop_duration_ms: Optional[float] = None
        self.stop_easing: str = "linear"
        self.stop_start_time: Optional[float] = None

    def configure_lifecycle(
        self,
        in_duration_ms: Optional[float] = None,
        in_easing: str = "linear",
        hold_duration_ms: Optional[float] = None,
        out_duration_ms: Optional[float] = None,
        out_easing: str = "linear",
        after_forward_callbacks: Optional[list[Callable]] = None,
        after_hold_callbacks: Optional[list[Callable]] = None,
        after_revert_callbacks: Optional[list[Callable]] = None
    ) -> 'Effect':
        """
        UNIFIED configuration method for all Effect lifecycle settings.

        Single source of truth for configuring Effect objects from both
        SpeedAccelBuilder and EffectBuilderBase.

        Returns self for chaining.
        """
        self.in_duration_ms = in_duration_ms
        self.in_easing = in_easing
        self.hold_duration_ms = hold_duration_ms

        # .hold() alone implies instant revert after hold period
        if hold_duration_ms is not None and out_duration_ms is None:
            self.out_duration_ms = 0
        else:
            self.out_duration_ms = out_duration_ms
        self.out_easing = out_easing

        # Callbacks - append to existing lists (supports multiple then() calls)
        if after_forward_callbacks:
            self.after_forward_callbacks.extend(after_forward_callbacks)
        if after_hold_callbacks:
            self.after_hold_callbacks.extend(after_hold_callbacks)
        if after_revert_callbacks:
            self.after_revert_callbacks.extend(after_revert_callbacks)

        return self

    def start(self, current_value: Optional[float] = None) -> None:
        """Start the effect lifecycle

        Args:
            current_value: Required for property effects, not used for stack effects
        """
        if self.is_property_effect:
            self.base_value = current_value

        if self.in_duration_ms is not None:
            self.phase = "in"
            self.phase_start_time = time.perf_counter()
            self.current_multiplier = 0.0 if self.is_property_effect else 0.0
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
            if self.name or self.is_stack_effect:
                # Named effects or stack effects persist indefinitely at full strength
                self.phase = "hold"
                self.current_multiplier = 1.0
            else:
                # Unnamed property effects without lifecycle complete immediately
                self.phase = "complete"
                self.complete = True

    def update(self, current_base_value: Optional[float] = None) -> Union[float, None]:
        """
        Update effect and return the modified value or multiplier.

        Args:
            current_base_value: Required for property effects, not used for stack effects

        Returns:
            For property effects: modified value
            For stack effects: current multiplier (0.0 to 1.0)
        """
        if self.complete:
            return current_base_value if self.is_property_effect else 0.0

        # Handle stop request
        if self.stop_requested:
            return self._update_stop(current_base_value)

        # Auto-start for stack effects
        if self.phase == "not_started" and self.is_stack_effect:
            self.start()

        # Normal lifecycle progression
        current_time = time.perf_counter()
        elapsed_ms = (current_time - self.phase_start_time) * 1000 if self.phase_start_time else 0

        if self.phase == "in":
            if elapsed_ms >= self.in_duration_ms:
                # Move to next phase
                self.current_multiplier = 1.0

                # Fire all after-forward callbacks (property effects only)
                for callback in self.after_forward_callbacks:
                    callback()

                if self.hold_duration_ms is not None:
                    self.phase = "hold"
                    self.phase_start_time = current_time
                elif self.out_duration_ms is not None:
                    self.phase = "out"
                    self.phase_start_time = current_time
                else:
                    # No hold or revert specified - persist at full strength
                    self.phase = "hold"
                    if self.is_property_effect:
                        self.hold_duration_ms = None  # Persist indefinitely
            else:
                # Update multiplier with easing
                t = elapsed_ms / self.in_duration_ms
                easing_fn = EASING_FUNCTIONS.get(self.in_easing, ease_linear)
                self.current_multiplier = easing_fn(t)

        elif self.phase == "hold":
            # Check if we have a duration specified
            if self.hold_duration_ms is not None:
                if elapsed_ms >= self.hold_duration_ms:
                    # Fire all after-hold callbacks (property effects only)
                    for callback in self.after_hold_callbacks:
                        callback()

                    # Move to next phase
                    if self.out_duration_ms is not None:
                        self.phase = "out"
                        self.phase_start_time = current_time
                    else:
                        self.phase = "complete"
                        self.complete = True
                        return current_base_value if self.is_property_effect else 0.0
            # else: persist indefinitely at full strength
            # Multiplier stays at 1.0 during hold

        elif self.phase == "out":
            if elapsed_ms >= self.out_duration_ms:
                # Fire all after-revert callbacks (property effects only)
                for callback in self.after_revert_callbacks:
                    callback()

                self.phase = "complete"
                self.complete = True
                return current_base_value if self.is_property_effect else 0.0
            else:
                # Fade out
                t = elapsed_ms / self.out_duration_ms
                easing_fn = EASING_FUNCTIONS.get(self.out_easing, ease_linear)
                self.current_multiplier = 1.0 - easing_fn(t)

        # Return based on effect type
        if self.is_property_effect:
            return self._apply_operation(current_base_value)
        else:
            return self.current_multiplier

    def _apply_operation(self, base_value: float) -> float:
        """Apply the operation to the base value based on multiplier"""
        if self.current_multiplier == 0.0:
            return base_value

        if self.operation == "to":
            # Interpolate from base to target
            return lerp(base_value, self.value, self.current_multiplier)
        elif self.operation == "by":
            # Add scaled delta
            return base_value + (self.value * self.current_multiplier)
        elif self.operation == "mul":
            # Multiply: base * (1 + (multiplier - 1) * current_multiplier)
            # At multiplier=0: base * 1 = base
            # At multiplier=1: base * value
            return base_value * (1.0 + (self.value - 1.0) * self.current_multiplier)
        elif self.operation == "div":
            # Divide: similar to multiply
            if abs(self.value) < 1e-6:
                return base_value
            divisor = 1.0 + (self.value - 1.0) * self.current_multiplier
            if abs(divisor) < 1e-6:
                return base_value
            return base_value / divisor
        return base_value

    def _update_stop(self, current_base_value: float) -> float:
        """Handle stop request by fading out"""
        current_time = time.perf_counter()

        if self.stop_start_time is None:
            self.stop_start_time = current_time

        if self.stop_duration_ms == 0:
            # Instant stop
            self.complete = True
            return current_base_value

        elapsed_ms = (current_time - self.stop_start_time) * 1000

        if elapsed_ms >= self.stop_duration_ms:
            self.complete = True
            return current_base_value

        # Fade out from current multiplier to 0
        t = elapsed_ms / self.stop_duration_ms
        easing_fn = EASING_FUNCTIONS.get(self.stop_easing, ease_linear)
        # Store the multiplier we had when stop was requested
        if not hasattr(self, '_stop_start_multiplier'):
            self._stop_start_multiplier = self.current_multiplier
        self.current_multiplier = self._stop_start_multiplier * (1.0 - easing_fn(t))

        if self.is_property_effect:
            return self._apply_operation(current_base_value)
        else:
            return self.current_multiplier

    def request_stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Request the effect to stop"""
        self.stop_requested = True
        self.stop_duration_ms = duration_ms if duration_ms is not None else 0
        self.stop_easing = easing


# Backwards compatibility aliases
PropertyEffect = Effect  # For property effects


# ============================================================================
# DIRECTION EFFECT
# ============================================================================

class DirectionEffect:
    """
    Represents a temporary direction rotation with lifecycle phases.

    Uses the unified Effect class for lifecycle management, with direction-specific
    application logic for rotating Vec2 values.
    """
    def __init__(self, degrees: float, name: Optional[str] = None):
        self.degrees = degrees  # Rotation amount in degrees
        self.name = name  # Optional name for stopping early

        # Create unified Effect for lifecycle management (direction is just a scalar degree value)
        self._effect = Effect(value=degrees, operation="add", name=name)

    # Delegate all lifecycle properties to unified Effect
    @property
    def in_duration_ms(self):
        return self._effect.in_duration_ms

    @in_duration_ms.setter
    def in_duration_ms(self, value):
        self._effect.in_duration_ms = value

    @property
    def in_easing(self):
        return self._effect.in_easing

    @in_easing.setter
    def in_easing(self, value):
        self._effect.in_easing = value

    @property
    def hold_duration_ms(self):
        return self._effect.hold_duration_ms

    @hold_duration_ms.setter
    def hold_duration_ms(self, value):
        self._effect.hold_duration_ms = value

    @property
    def out_duration_ms(self):
        return self._effect.out_duration_ms

    @out_duration_ms.setter
    def out_duration_ms(self, value):
        self._effect.out_duration_ms = value

    @property
    def out_easing(self):
        return self._effect.out_easing

    @out_easing.setter
    def out_easing(self, value):
        self._effect.out_easing = value

    @property
    def after_forward_callbacks(self):
        return self._effect.after_forward_callbacks

    @property
    def after_hold_callbacks(self):
        return self._effect.after_hold_callbacks

    @property
    def after_revert_callbacks(self):
        return self._effect.after_revert_callbacks

    @property
    def phase(self):
        return self._effect.phase

    @property
    def complete(self):
        return self._effect.complete

    @property
    def current_multiplier(self):
        return self._effect.current_multiplier

    def configure_lifecycle(
        self,
        in_duration_ms: Optional[float] = None,
        in_easing: str = "linear",
        hold_duration_ms: Optional[float] = None,
        out_duration_ms: Optional[float] = None,
        out_easing: str = "linear",
        after_forward_callbacks: Optional[list[Callable]] = None,
        after_hold_callbacks: Optional[list[Callable]] = None,
        after_revert_callbacks: Optional[list[Callable]] = None
    ) -> None:
        """Configure lifecycle - delegates to unified Effect"""
        self._effect.configure_lifecycle(
            in_duration_ms=in_duration_ms,
            in_easing=in_easing,
            hold_duration_ms=hold_duration_ms,
            out_duration_ms=out_duration_ms,
            out_easing=out_easing,
            after_forward_callbacks=after_forward_callbacks,
            after_hold_callbacks=after_hold_callbacks,
            after_revert_callbacks=after_revert_callbacks
        )

    def start(self, current_direction: Vec2 = None) -> None:
        """Start the effect lifecycle"""
        # Direction effects don't need base value for lifecycle
        self._effect.start()

    def update(self, current_base_direction: Vec2) -> Vec2:
        """
        Update effect and return the modified direction.

        Args:
            current_base_direction: The current base direction (without this effect)

        Returns:
            The modified direction with this effect applied
        """
        # Update the unified effect lifecycle
        self._effect.update()

        if self._effect.complete:
            return current_base_direction

        # Apply rotation based on current multiplier from unified effect
        return self._apply_rotation(current_base_direction)

    def _apply_rotation(self, base_direction: Vec2) -> Vec2:
        """Apply the rotation to the base direction based on multiplier"""
        if self._effect.current_multiplier == 0.0:
            return base_direction

        # Calculate the rotation amount scaled by multiplier
        angle_rad = math.radians(self.degrees * self._effect.current_multiplier)

        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        new_x = base_direction.x * cos_a - base_direction.y * sin_a
        new_y = base_direction.x * sin_a + base_direction.y * cos_a

        return Vec2(new_x, new_y).normalized()

    def request_stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Request the effect to stop"""
        self._effect.request_stop(duration_ms, easing)


class ReverseEffect:
    """
    Temporary reverse effect with lifecycle phases.

    Unlike DirectionEffect which rotates, ReverseEffect flips direction 180°
    and manipulates speed to create a backing-up motion effect.

    Lifecycle:
    - Forward: Flip direction, fade speed from -start to +start
    - Hold: Stay reversed with normal speed
    - Revert: Flip back, fade speed from -start to +start again
    """
    def __init__(self, name: Optional[str] = None):
        self.name = name
        self.phase = "initial"
        self.complete = False

        # Lifecycle timing
        self.in_duration_ms: Optional[float] = None
        self.in_easing: str = "linear"
        self.hold_duration_ms: Optional[float] = None
        self.out_duration_ms: Optional[float] = None
        self.out_easing: str = "linear"

        # Callbacks
        self.after_forward_callbacks: list[Callable] = []
        self.after_hold_callbacks: list[Callable] = []
        self.after_revert_callbacks: list[Callable] = []

        # State
        self.phase_start_time: Optional[float] = None
        self.start_speed: float = 0.0
        self.direction_flipped: bool = False
        self.original_direction: Optional[Vec2] = None

    def configure_lifecycle(
        self,
        in_duration_ms: Optional[float] = None,
        in_easing: str = "linear",
        hold_duration_ms: Optional[float] = None,
        out_duration_ms: Optional[float] = None,
        out_easing: str = "linear",
        after_forward_callbacks: Optional[list[Callable]] = None,
        after_hold_callbacks: Optional[list[Callable]] = None,
        after_revert_callbacks: Optional[list[Callable]] = None
    ) -> None:
        """Configure lifecycle phases"""
        self.in_duration_ms = in_duration_ms
        self.in_easing = in_easing
        self.hold_duration_ms = hold_duration_ms
        self.out_duration_ms = out_duration_ms
        self.out_easing = out_easing
        if after_forward_callbacks:
            self.after_forward_callbacks.extend(after_forward_callbacks)
        if after_hold_callbacks:
            self.after_hold_callbacks.extend(after_hold_callbacks)
        if after_revert_callbacks:
            self.after_revert_callbacks.extend(after_revert_callbacks)

    def start(self, start_speed: float, current_direction: Vec2) -> None:
        """Start the reverse effect"""
        self.start_speed = abs(start_speed)
        self.original_direction = current_direction
        self.phase_start_time = time.perf_counter()
        self.phase = "forward"
        self.direction_flipped = False

    def update(self, rig_state: 'RigState') -> None:
        """Update the reverse effect - modifies rig_state direction and speed directly"""
        if self.complete or self.phase == "initial":
            return

        current_time = time.perf_counter()
        elapsed_ms = (current_time - self.phase_start_time) * 1000

        if self.phase == "forward":
            # Flip direction on first update
            if not self.direction_flipped:
                rig_state._direction = Vec2(-rig_state._direction.x, -rig_state._direction.y)
                self.direction_flipped = True

            # Fade speed from -start_speed to +start_speed
            if self.in_duration_ms is not None and self.in_duration_ms > 0:
                progress = min(elapsed_ms / self.in_duration_ms, 1.0)
                easing_fn = EASING_FUNCTIONS.get(self.in_easing, ease_linear)
                eased = easing_fn(progress)
                rig_state._speed = lerp(-self.start_speed, self.start_speed, eased)

                if progress >= 1.0:
                    self._transition_to_hold()
            else:
                # Instant forward
                rig_state._speed = self.start_speed
                self._transition_to_hold()

        elif self.phase == "hold":
            # Just wait
            if self.hold_duration_ms is not None:
                if elapsed_ms >= self.hold_duration_ms:
                    self._transition_to_out()
            else:
                # No hold phase, go straight to out if configured
                if self.out_duration_ms is not None:
                    self._transition_to_out()
                else:
                    self.complete = True

        elif self.phase == "out":
            # Flip direction back
            if self.direction_flipped:
                rig_state._direction = Vec2(-rig_state._direction.x, -rig_state._direction.y)
                self.direction_flipped = False

            # Fade speed from -start_speed to +start_speed again
            if self.out_duration_ms is not None and self.out_duration_ms > 0:
                progress = min(elapsed_ms / self.out_duration_ms, 1.0)
                easing_fn = EASING_FUNCTIONS.get(self.out_easing, ease_linear)
                eased = easing_fn(progress)
                rig_state._speed = lerp(-self.start_speed, self.start_speed, eased)

                if progress >= 1.0:
                    for callback in self.after_revert_callbacks:
                        callback()
                    self.complete = True
            else:
                # Instant revert
                rig_state._speed = self.start_speed
                for callback in self.after_revert_callbacks:
                    callback()
                self.complete = True

    def _transition_to_hold(self) -> None:
        """Transition from forward to hold phase"""
        for callback in self.after_forward_callbacks:
            callback()

        self.phase_start_time = time.perf_counter()
        if self.hold_duration_ms is not None:
            self.phase = "hold"
        elif self.out_duration_ms is not None:
            self.phase = "out"
            self.direction_flipped = True  # Mark as flipped so out phase can flip back
        else:
            self.complete = True

    def _transition_to_out(self) -> None:
        """Transition from hold to out phase"""
        for callback in self.after_hold_callbacks:
            callback()

        self.phase_start_time = time.perf_counter()
        self.phase = "out"

    def request_stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Request early stop"""
        self.out_duration_ms = duration_ms if duration_ms is not None else 0
        self.out_easing = easing
        self.phase_start_time = time.perf_counter()
        self.phase = "out"


class PositionEffect:
    """
    Represents a temporary position offset with lifecycle phases.

    Uses the unified Effect class for lifecycle management, with position-specific
    application logic for Vec2 offset values. Supports both absolute and relative modes.
    """
    def __init__(self, offset: Vec2, mode: str = "relative", name: Optional[str] = None):
        """
        Args:
            offset: Position offset (relative) or target position (absolute)
            mode: "relative" or "absolute"
            name: Optional name for stopping early
        """
        self.offset = offset  # Vec2 offset or target position
        self.mode = mode  # "relative" or "absolute"
        self.name = name  # Optional name for stopping early
        self.original_pos: Optional[Vec2] = None  # Captured at start

        # Create unified Effect for lifecycle management
        self._effect = Effect(value=0.0, operation="add", name=name)

    # Delegate all lifecycle properties to unified Effect
    @property
    def in_duration_ms(self):
        return self._effect.in_duration_ms

    @in_duration_ms.setter
    def in_duration_ms(self, value):
        self._effect.in_duration_ms = value

    @property
    def in_easing(self):
        return self._effect.in_easing

    @in_easing.setter
    def in_easing(self, value):
        self._effect.in_easing = value

    @property
    def hold_duration_ms(self):
        return self._effect.hold_duration_ms

    @hold_duration_ms.setter
    def hold_duration_ms(self, value):
        self._effect.hold_duration_ms = value

    @property
    def out_duration_ms(self):
        return self._effect.out_duration_ms

    @out_duration_ms.setter
    def out_duration_ms(self, value):
        self._effect.out_duration_ms = value

    @property
    def out_easing(self):
        return self._effect.out_easing

    @out_easing.setter
    def out_easing(self, value):
        self._effect.out_easing = value

    @property
    def after_forward_callbacks(self):
        return self._effect.after_forward_callbacks

    @property
    def after_hold_callbacks(self):
        return self._effect.after_hold_callbacks

    @property
    def after_revert_callbacks(self):
        return self._effect.after_revert_callbacks

    @property
    def phase(self):
        return self._effect.phase

    @property
    def complete(self):
        return self._effect.complete

    @property
    def current_multiplier(self):
        return self._effect.current_multiplier

    def configure_lifecycle(
        self,
        in_duration_ms: Optional[float] = None,
        in_easing: str = "linear",
        hold_duration_ms: Optional[float] = None,
        out_duration_ms: Optional[float] = None,
        out_easing: str = "linear",
        after_forward_callbacks: Optional[list[Callable]] = None,
        after_hold_callbacks: Optional[list[Callable]] = None,
        after_revert_callbacks: Optional[list[Callable]] = None
    ) -> None:
        """Configure lifecycle - delegates to unified Effect"""
        self._effect.configure_lifecycle(
            in_duration_ms=in_duration_ms,
            in_easing=in_easing,
            hold_duration_ms=hold_duration_ms,
            out_duration_ms=out_duration_ms,
            out_easing=out_easing,
            after_forward_callbacks=after_forward_callbacks,
            after_hold_callbacks=after_hold_callbacks,
            after_revert_callbacks=after_revert_callbacks
        )

    def start(self, current_pos: Vec2) -> None:
        """Start the effect lifecycle"""
        from talon import ctrl
        # Capture current actual mouse position for revert
        self.original_pos = Vec2(*ctrl.mouse_pos())
        self._effect.start()

    def update(self) -> Optional[Vec2]:
        """
        Update effect and return the target position to move to, or None if complete.

        Returns:
            Target position to move to, or None if effect is complete
        """
        from talon import ctrl

        # Update the unified effect lifecycle
        self._effect.update()

        if self._effect.complete:
            return None

        # Get current mouse position
        current_pos = Vec2(*ctrl.mouse_pos())

        # Calculate target position based on phase and multiplier
        if self._effect.phase in ("in", "hold"):
            # Moving forward to target
            if self.mode == "absolute":
                # Interpolate from original to target
                target = Vec2(
                    lerp(self.original_pos.x, self.offset.x, self._effect.current_multiplier),
                    lerp(self.original_pos.y, self.offset.y, self._effect.current_multiplier)
                )
            else:  # relative
                # Apply scaled offset from original position
                target = Vec2(
                    self.original_pos.x + (self.offset.x * self._effect.current_multiplier),
                    self.original_pos.y + (self.offset.y * self._effect.current_multiplier)
                )
            return target

        elif self._effect.phase == "out":
            # Reverting back to original position
            # Get current position (which may have been modified by forward phase)
            forward_pos = current_pos
            if self._effect.current_multiplier > 0:
                # Still has some effect, interpolate back
                target = Vec2(
                    lerp(forward_pos.x, self.original_pos.x, 1.0 - self._effect.current_multiplier),
                    lerp(forward_pos.y, self.original_pos.y, 1.0 - self._effect.current_multiplier)
                )
            else:
                # Fully reverted
                target = self.original_pos
            return target

        return None

    def request_stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Request the effect to stop"""
        self._effect.request_stop(duration_ms, easing)


# ============================================================================
# FORCE SYSTEM (independent entities with vector addition)
# ============================================================================

class Force:
    """
    Independent entity with its own speed, acceleration, and direction.
    Forces combine with base rig via vector addition.

    Supports lifecycle: in (fade in) → hold → out (fade out/revert)
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

        # Lifecycle state (similar to EffectLifecycle)
        self.phase: Literal["not_started", "in", "hold", "out", "complete"] = "not_started"
        self.start_time: Optional[float] = None
        self.phase_start_time: Optional[float] = None

        # Lifecycle timing
        self.in_duration_ms: Optional[float] = None
        self.in_easing: str = "linear"
        self.hold_duration_ms: Optional[float] = None
        self.out_duration_ms: Optional[float] = None
        self.out_easing: str = "linear"

        # Initial values for lifecycle
        self.initial_speed = 0.0
        self.initial_accel = 0.0
        self.initial_velocity = 0.0

        # Current lifecycle multiplier (0.0 to 1.0)
        self.multiplier = 1.0

        self.complete = False

    def start(self) -> None:
        """Start the force lifecycle"""
        if self.phase == "not_started":
            self.start_time = time.perf_counter()
            self.phase_start_time = self.start_time

            # Store initial values
            self.initial_speed = self._speed
            self.initial_accel = self._accel
            self.initial_velocity = self._velocity

            # Determine starting phase
            if self.in_duration_ms is not None and self.in_duration_ms > 0:
                self.phase = "in"
                self.multiplier = 0.0  # Start from 0 and fade in
            else:
                # No fade-in, go straight to hold (indefinite by default)
                self.phase = "hold"
                self.multiplier = 1.0

    def update(self, dt: float) -> Vec2:
        """
        Update force lifecycle and return its velocity vector contribution.

        Args:
            dt: Delta time in seconds

        Returns:
            Velocity vector from this force
        """
        if self.complete:
            return Vec2(0, 0)

        if self.phase == "not_started":
            self.start()

        # Update lifecycle phase
        self._update_lifecycle()

        # Integrate acceleration into velocity
        if abs(self._accel) > 1e-6:
            self._velocity += self._accel * dt

        # Apply lifecycle multiplier to speed and velocity
        effective_speed = self._speed * self.multiplier
        effective_velocity = self._velocity * self.multiplier
        total_speed = effective_speed + effective_velocity

        # Return velocity vector
        return self._direction * total_speed

    def _update_lifecycle(self) -> None:
        """Update lifecycle phase and multiplier"""
        if self.phase == "complete":
            self.complete = True
            return

        current_time = time.perf_counter()
        elapsed_ms = (current_time - self.phase_start_time) * 1000

        if self.phase == "in":
            if self.in_duration_ms is None or self.in_duration_ms == 0:
                # Instant in
                self.multiplier = 1.0
                self._transition_to_hold()
            else:
                # Fade in
                t = min(1.0, elapsed_ms / self.in_duration_ms)
                easing_fn = EASING_FUNCTIONS.get(self.in_easing, ease_linear)
                self.multiplier = easing_fn(t)

                if t >= 1.0:
                    self.multiplier = 1.0
                    self._transition_to_hold()

        elif self.phase == "hold":
            if self.hold_duration_ms is None:
                # Hold indefinitely
                self.multiplier = 1.0
            else:
                # Hold for duration
                if elapsed_ms >= self.hold_duration_ms:
                    self._transition_to_out()

        elif self.phase == "out":
            if self.out_duration_ms is None or self.out_duration_ms == 0:
                # Instant out
                self.multiplier = 0.0
                self.phase = "complete"
            else:
                # Fade out
                t = min(1.0, elapsed_ms / self.out_duration_ms)
                easing_fn = EASING_FUNCTIONS.get(self.out_easing, ease_linear)
                self.multiplier = 1.0 - easing_fn(t)

                if t >= 1.0:
                    self.multiplier = 0.0
                    self.phase = "complete"

    def _transition_to_hold(self) -> None:
        """Transition from 'in' to 'hold' phase"""
        self.phase_start_time = time.perf_counter()
        if self.hold_duration_ms is not None or self.out_duration_ms is not None:
            self.phase = "hold"
        else:
            # No hold or out, we're done
            self.phase = "complete"

    def _transition_to_out(self) -> None:
        """Transition from 'hold' to 'out' phase"""
        self.phase_start_time = time.perf_counter()
        if self.out_duration_ms is not None:
            self.phase = "out"
        else:
            # No out phase, we're done
            self.phase = "complete"

    def request_stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Request the force to stop, optionally over a duration"""
        # Transition to out phase
        self.out_duration_ms = duration_ms if duration_ms is not None else 0
        self.out_easing = easing
        self.phase_start_time = time.perf_counter()
        self.phase = "out"
