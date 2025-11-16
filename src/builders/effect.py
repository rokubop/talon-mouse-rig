"""Effect builders for named effects"""

from typing import Optional, TYPE_CHECKING, Union, TypeVar, Generic, Callable
from ..core import Vec2
from ..effects import EffectStack, EffectLifecycle
from .contracts import PropertyOperationsContract, MultiSegmentMixin
from .rate_utils import (
    validate_rate_params,
    calculate_duration_from_rate,
    calculate_over_duration_for_property,
    calculate_revert_duration_for_property
)

if TYPE_CHECKING:
    from ..state import RigState

# Type variable for self-return types in base class
T = TypeVar('T', bound='EffectBuilderBase')


class EffectBuilderBase(MultiSegmentMixin[T], PropertyOperationsContract[T]):
    """
    Base class for all effect property builders.
    Consolidates shared implementation for operations and timing methods.
    Subclasses only need to specify property name and override type hints.

    Uses MultiSegmentMixin for unified operation chaining behavior.
    """
    # Override in subclasses
    _property_name: str = None

    def __init__(self, rig_state: 'RigState', name: str, strict_mode: bool = False):
        self.rig_state = rig_state
        self.name = name
        self.strict_mode = strict_mode
        self._last_op_type: Optional[str] = None
        self._started = False

        # Stage-specific callbacks - support multiple then() calls
        self._after_forward_callbacks: list[Callable] = []
        self._after_hold_callbacks: list[Callable] = []
        self._after_revert_callbacks: list[Callable] = []
        self._current_stage: str = "initial"

        # Timing configuration
        self._hold_duration_ms: Optional[float] = None
        self._out_duration_ms: Optional[float] = None
        self._out_easing: str = "linear"

        # Multi-segment chaining flag (for MultiSegmentMixin)
        self._is_chaining: bool = False  # Set to True by timing methods

        # Pre-configured repeat strategy (from sugar syntax)
        self._pending_repeat_strategy: Optional[str] = None
        self._pending_repeat_args: tuple = ()

    def __del__(self):
        try:
            if not self._started and self._last_op_type is not None:
                self.rig_state.start()
        except:
            pass

    def __call__(self, value: Union[float, Vec2]) -> T:
        """Shorthand for add/to operation - strict mode disallows this"""
        if self.strict_mode:
            raise ValueError(
                f"Strict syntax required for effects. "
                f"Use .to({value}) for absolute value or .add({value}) for delta. "
                f"Shorthand syntax like .{self._property_name}({value}) is not allowed for effects."
            )
        return self.to(value)

    def _get_or_create_stack(self, op_type: str) -> EffectStack:
        """Get or create the effect stack for this operation type"""
        key = f"{self.name}:{self._property_name}:{op_type}"
        if key not in self.rig_state._effect_stacks:
            stack = EffectStack(
                name=self.name,
                property=self._property_name,
                operation_type=op_type
            )
            self.rig_state._effect_stacks[key] = stack
            if key not in self.rig_state._effect_order:
                self.rig_state._effect_order.append(key)
        return self.rig_state._effect_stacks[key]

    def _get_or_create_effect(self, op_type: str) -> EffectLifecycle:
        """Get or create the effect lifecycle wrapper"""
        key = f"{self.name}:{self._property_name}:{op_type}"
        if key not in self.rig_state._effect_lifecycles:
            stack = self._get_or_create_stack(op_type)
            self.rig_state._effect_lifecycles[key] = EffectLifecycle(stack, self.rig_state)
        return self.rig_state._effect_lifecycles[key]

    def _apply_operation(self, op_type: str, value: Union[float, Vec2]) -> bool:
        """Apply operation respecting repeat strategy

        Returns:
            True if operation was applied, False if rejected by strategy
        """
        key = f"{self.name}:{self._property_name}:{op_type}"

        # Apply pending repeat strategy if set (from sugar syntax)
        if self._pending_repeat_strategy and key not in self.rig_state._effect_lifecycles:
            self.on_repeat(self._pending_repeat_strategy, *self._pending_repeat_args)
            self._pending_repeat_strategy = None  # Clear after applying

        # Check if there's a lifecycle managing this operation
        if key in self.rig_state._effect_lifecycles:
            lifecycle = self.rig_state._effect_lifecycles[key]
            if not lifecycle.should_accept_new_operation():
                return False  # Rejected by strategy (ignore/throttle)
            lifecycle.apply_operation_with_strategy(value)
        else:
            # No lifecycle yet, just add to stack normally
            stack = self._get_or_create_stack(op_type)
            stack.add_operation(value)

        return True

    # Override MultiSegmentMixin operations to apply effect-specific logic before chaining
    def to(self, value: Union[float, Vec2]) -> T:
        """Set absolute value"""
        # Check if in chaining mode (uses MultiSegmentMixin logic)
        if self._is_chaining:
            return self._queue_next_segment("to", (value,))

        stack = self._get_or_create_stack("to")
        stack.add_operation(value)
        self._last_op_type = "to"
        return self

    def add(self, value: Union[float, Vec2]) -> T:
        """Add delta (stacks by default - unlimited)"""
        # Check if in chaining mode (uses MultiSegmentMixin logic)
        if self._is_chaining:
            return self._queue_next_segment("add", (value,))

        self._apply_operation("add", value)
        self._last_op_type = "add"
        return self

    # by() inherited from MultiSegmentMixin - calls add()

    def sub(self, value: Union[float, Vec2]) -> T:
        """Subtract (stacks by default - unlimited)"""
        negated = -value if isinstance(value, (int, float)) else Vec2(-value.x, -value.y)

        # Check if in chaining mode (uses MultiSegmentMixin logic)
        if self._is_chaining:
            return self._queue_next_segment("sub", (negated,))

        self._apply_operation("sub", negated)
        self._last_op_type = "sub"
        return self

    def mul(self, value: float) -> T:
        """Multiply (stacks by default - unlimited)"""
        # Check if in chaining mode (uses MultiSegmentMixin logic)
        if self._is_chaining:
            return self._queue_next_segment("mul", (value,))

        self._apply_operation("mul", value)
        self._last_op_type = "mul"
        return self

    def div(self, value: float) -> T:
        """Divide (stacks by default - unlimited)"""
        if abs(value) < 1e-6:
            raise ValueError("Cannot divide by zero or near-zero value")

        # Check if in chaining mode (uses MultiSegmentMixin logic)
        if self._is_chaining:
            return self._queue_next_segment("div", (1.0 / value,))

        self._apply_operation("div", 1.0 / value)
        self._last_op_type = "div"
        return self

    def _get_queue_builder(self, queue_namespace):
        """Get the builder for this operation type from queue namespace (MultiSegmentMixin hook)"""
        # Return the appropriate property builder from EffectBuilder.queue namespace
        if self._property_name == "speed":
            return queue_namespace.speed
        elif self._property_name == "accel":
            return queue_namespace.accel
        elif self._property_name == "direction":
            return queue_namespace.direction
        elif self._property_name == "pos":
            return queue_namespace.pos
        else:
            raise ValueError(f"Unknown property: {self._property_name}")

    def on_repeat(self, strategy: str = "stack", *args) -> T:
        """Configure behavior when effect is called multiple times

        Strategies:
            "stack" (default): Stack effects (unlimited or with max count)
            "replace": New call replaces existing effect, resets duration
            "extend": Extend duration from current phase, cancel pending revert
            "queue": Queue effects to run sequentially
            "ignore": Ignore new calls while effect is active
            "throttle" [ms]: Rate limit calls (minimum time between calls)

        Examples:
            .add(10)                             # Unlimited stacking (default)
            .add(10).on_repeat("stack", 3)       # Max 3 stacks
            .add(10).on_repeat("replace")        # Replace instead of stack
            .add(10).on_repeat("extend")         # Extend duration
            .add(10).on_repeat("throttle", 500)  # Max 1 call per 500ms
        """
        if self._last_op_type is None:
            raise ValueError("No operation to apply .on_repeat() to - call .to()/.mul()/.div()/.add()/.sub() first")

        key = f"{self.name}:{self._property_name}:{self._last_op_type}"

        if strategy == "stack":
            max_count = args[0] if args else None
            if key in self.rig_state._effect_stacks:
                self.rig_state._effect_stacks[key].max_stack_count = max_count
        elif strategy == "replace":
            if key in self.rig_state._effect_stacks:
                self.rig_state._effect_stacks[key].max_stack_count = 1
        elif strategy in ("extend", "queue", "ignore", "throttle"):
            # Ensure lifecycle exists for these strategies
            lifecycle = self._get_or_create_effect(self._last_op_type)
            lifecycle.repeat_strategy = strategy
            if strategy == "throttle" and args:
                lifecycle.throttle_ms = args[0]
        else:
            raise ValueError(f"Unknown repeat strategy: {strategy}. Use: replace, stack, extend, queue, ignore, throttle")

        return self

    # ===== Hooks to customize base TimingMethodsContract behavior =====

    def _before_over(
        self,
        duration_ms: Optional[float],
        easing: str,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> None:
        """Validate that an operation was called first"""
        if self._last_op_type is None:
            raise ValueError("No operation to apply .over() to - call .mul()/.div()/.add()/.sub() first")

        # Validate: cannot call over() twice on same segment
        if self._is_chaining and self._current_stage == "after_forward":
            raise ValueError("Cannot call .over() multiple times on the same segment. Use separate operations for chaining.")

    def _calculate_over_duration_from_rate(
        self,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> float:
        """Calculate duration from rate based on effect value"""
        # For effects, calculate based on the operation value
        effect = self._get_or_create_effect(self._last_op_type)
        # This is simplified - proper implementation would calculate based on actual delta
        value = abs(effect.value) if hasattr(effect, 'value') else 10

        # Use unified rate calculation (handles validation internally)
        return calculate_over_duration_for_property(
            self._property_name, 0.0, value,
            rate_speed, rate_accel, rate_rotation
        )

    def _store_over_config(self, duration_ms: Optional[float], easing: str, interpolation: str = "lerp") -> None:
        """UNIFIED: Store configuration using Effect.configure_lifecycle"""
        effect = self._get_or_create_effect(self._last_op_type)
        effect.configure_lifecycle(
            in_duration_ms=duration_ms,
            in_easing=easing,
            hold_duration_ms=effect.hold_duration_ms,  # Preserve existing
            out_duration_ms=effect.out_duration_ms,    # Preserve existing
            out_easing=effect.out_easing,             # Preserve existing
            after_forward_callbacks=self._after_forward_callbacks if self._after_forward_callbacks else None,
            after_hold_callbacks=None,  # Preserve existing
            after_revert_callbacks=None  # Preserve existing
        )

    def _after_over_configured(self, duration_ms: Optional[float], easing: str) -> None:
        """Start rig if not started and set up queue execution"""
        # Add callback to execute next queued segment if no hold/revert will be called
        # (If hold/revert are called, they will add their own callbacks)
        if self._after_forward_callbacks is None:
            self._after_forward_callbacks = []

        tag_name = self.name
        rig_state = self.rig_state
        def execute_next_queued_segment():
            rig_state._execute_next_segment(tag_name)

        self._after_forward_callbacks.append(execute_next_queued_segment)

        if not self._started:
            self.rig_state.start()
            self._started = True

    def _before_hold(self, duration_ms: float) -> None:
        """Validate that an operation was called first"""
        if self._last_op_type is None:
            raise ValueError("No operation to apply .hold() to - call .mul()/.div()/.add()/.sub() first")

        # Validate: cannot call hold() if segment already has hold
        if self._is_chaining and self._current_stage == "after_hold":
            raise ValueError("Cannot call .hold() multiple times on the same segment.")

    def _after_hold_configured(self, duration_ms: float) -> None:
        """UNIFIED: Apply hold using Effect.configure_lifecycle"""
        effect = self._get_or_create_effect(self._last_op_type)

        # Add callback to execute next queued segment if no revert will be called
        if self._after_hold_callbacks is None:
            self._after_hold_callbacks = []

        tag_name = self.name
        rig_state = self.rig_state
        def execute_next_queued_segment():
            rig_state._execute_next_segment(tag_name)

        self._after_hold_callbacks.append(execute_next_queued_segment)

        effect.configure_lifecycle(
            in_duration_ms=effect.in_duration_ms,    # Preserve existing
            in_easing=effect.in_easing,              # Preserve existing
            hold_duration_ms=duration_ms,
            out_duration_ms=effect.out_duration_ms,  # Preserve existing
            out_easing=effect.out_easing,            # Preserve existing
            after_forward_callbacks=None,  # Preserve existing
            after_hold_callbacks=self._after_hold_callbacks if self._after_hold_callbacks else None,
            after_revert_callbacks=None  # Preserve existing
        )

        if not self._started:
            self.rig_state.start()
            self._started = True

    def _before_revert(self, duration_ms: Optional[float], easing: str,
                      rate_speed: Optional[float], rate_accel: Optional[float],
                      rate_rotation: Optional[float]) -> None:
        """Validate revert rules"""
        if self._last_op_type is None:
            raise ValueError("No operation to apply .revert() to - call .mul()/.div()/.add()/.sub() first")

        # Validate: cannot call revert() twice on same segment
        if self._is_chaining and self._current_stage == "after_revert":
            raise ValueError("Cannot call .revert() multiple times on the same segment.")

    def _calculate_revert_duration_from_rate(self, rate_speed: Optional[float],
                                            rate_accel: Optional[float],
                                            rate_rotation: Optional[float]) -> Optional[float]:
        """Calculate revert duration from rate parameters"""
        # For now, use a default value - proper implementation would calculate based on effect strength
        # Using value of 10 as a placeholder for effect strength
        return calculate_revert_duration_for_property(
            self._property_name, 10.0,
            rate_speed, rate_accel, rate_rotation
        )

    def _after_revert_configured(self, duration_ms: float, easing: str) -> None:
        """UNIFIED: Apply revert using Effect.configure_lifecycle"""
        effect = self._get_or_create_effect(self._last_op_type)

        # If no hold duration is set and we have fade-in, add instant hold
        hold_ms = effect.hold_duration_ms
        if effect.in_duration_ms is not None and hold_ms is None:
            hold_ms = 0

        # Add callback to execute next queued segment when this one completes
        if self._after_revert_callbacks is None:
            self._after_revert_callbacks = []

        # Create callback to execute next segment from queue
        tag_name = self.name
        rig_state = self.rig_state
        def execute_next_queued_segment():
            rig_state._execute_next_segment(tag_name)

        self._after_revert_callbacks.append(execute_next_queued_segment)

        effect.configure_lifecycle(
            in_duration_ms=effect.in_duration_ms,    # Preserve existing
            in_easing=effect.in_easing,              # Preserve existing
            hold_duration_ms=hold_ms,
            out_duration_ms=duration_ms,
            out_easing=easing,
            after_forward_callbacks=None,  # Preserve existing
            after_hold_callbacks=None,  # Preserve existing
            after_revert_callbacks=self._after_revert_callbacks if self._after_revert_callbacks else None
        )

        if not self._started:
            self.rig_state.start()
            self._started = True

    def _after_then_configured(self, callback: 'Callable') -> None:
        """Update the effect lifecycle with the newly set callback"""
        if self._last_op_type is None:
            return  # No effect to update yet

        effect = self._get_or_create_effect(self._last_op_type)
        effect.configure_lifecycle(
            in_duration_ms=effect.in_duration_ms,
            in_easing=effect.in_easing,
            hold_duration_ms=effect.hold_duration_ms,
            out_duration_ms=effect.out_duration_ms,
            out_easing=effect.out_easing,
            after_forward_callbacks=self._after_forward_callbacks if self._after_forward_callbacks else None,
            after_hold_callbacks=self._after_hold_callbacks if self._after_hold_callbacks else None,
            after_revert_callbacks=self._after_revert_callbacks if self._after_revert_callbacks else None
        )

class EffectBuilder:
    """
    Builder for named effect entities (tags).

    Effects modify base properties using direct operations:
    - .to(value): Set absolute value
    - .add(value) / .by(value): Add delta (aliases)
    - .sub(value): Subtract
    - .mul(value): Multiply
    - .div(value): Divide

    Effects use strict syntax - shorthand like speed(10) is not allowed.
    Use explicit operations like speed.to(10) or speed.add(10).

    Sugar syntax for repeat strategies (only for tags):
        rig.tag("x").stack.pos.to(...)         # Unlimited stacking
        rig.tag("x").stack(3).pos.to(...)      # Max 3 stacks
        rig.tag("x").replace.pos.to(...)       # Replace on repeat
        rig.tag("x").queue.pos.to(...)         # Queue segments
        rig.tag("x").throttle(300).pos.to(...) # Throttle 300ms
        rig.tag("x").ignore.pos.to(...)        # Ignore repeats

    Examples:
        rig.tag("sprint").speed.mul(2)       # Double speed
        rig.tag("boost").speed.add(10)       # Add 10 to speed
        rig.tag("drift").direction.add(15)   # Rotate 15 degrees
    """
    def __init__(self, rig_state: 'RigState', name: str, strict_mode: bool = True, repeat_strategy: Optional[str] = None, repeat_args: Optional[tuple] = None):
        self.rig_state = rig_state
        self.name = name
        self.strict_mode = strict_mode
        self._speed_builder = None
        self._accel_builder = None
        self._direction_builder = None
        self._pos_builder = None
        self._repeat_strategy = repeat_strategy
        self._repeat_args = repeat_args or ()

    @property
    def speed(self) -> 'EffectSpeedBuilder':
        """Access speed effect operations"""
        if self._speed_builder is None:
            self._speed_builder = EffectSpeedBuilder(self.rig_state, self.name, self.strict_mode)
            # Apply pre-configured repeat strategy if set
            if self._repeat_strategy:
                self._speed_builder._pending_repeat_strategy = self._repeat_strategy
                self._speed_builder._pending_repeat_args = self._repeat_args
        return self._speed_builder

    @property
    def accel(self) -> 'EffectAccelBuilder':
        """Access accel effect operations"""
        if self._accel_builder is None:
            self._accel_builder = EffectAccelBuilder(self.rig_state, self.name, self.strict_mode)
            # Apply pre-configured repeat strategy if set
            if self._repeat_strategy:
                self._accel_builder._pending_repeat_strategy = self._repeat_strategy
                self._accel_builder._pending_repeat_args = self._repeat_args
        return self._accel_builder

    @property
    def direction(self) -> 'EffectDirectionBuilder':
        """Access direction effect operations (rotation)"""
        if self._direction_builder is None:
            self._direction_builder = EffectDirectionBuilder(self.rig_state, self.name, self.strict_mode)
            # Apply pre-configured repeat strategy if set
            if self._repeat_strategy:
                self._direction_builder._pending_repeat_strategy = self._repeat_strategy
                self._direction_builder._pending_repeat_args = self._repeat_args
        return self._direction_builder

    @property
    def pos(self) -> 'EffectPosBuilder':
        """Access position effect operations (offsets)"""
        if self._pos_builder is None:
            self._pos_builder = EffectPosBuilder(self.rig_state, self.name, self.strict_mode)
            # Apply pre-configured repeat strategy if set
            if self._repeat_strategy:
                self._pos_builder._pending_repeat_strategy = self._repeat_strategy
                self._pos_builder._pending_repeat_args = self._repeat_args
        return self._pos_builder

    # Sugar syntax for repeat strategies
    @property
    def stack(self) -> 'EffectBuilder':
        """Set repeat strategy to stack (unlimited or with max count)

        Usage:
            rig.tag("x").stack.pos.to(...)      # Unlimited stacking
            rig.tag("x").stack(3).pos.to(...)   # Max 3 stacks
        """
        return EffectBuilder(self.rig_state, self.name, self.strict_mode, "stack", ())

    def __call__(self, *args) -> 'EffectBuilder':
        """Allow stack(n) syntax for max stack count"""
        if self._repeat_strategy == "stack" and len(args) == 1:
            return EffectBuilder(self.rig_state, self.name, self.strict_mode, "stack", (args[0],))
        elif self._repeat_strategy == "throttle" and len(args) == 1:
            return EffectBuilder(self.rig_state, self.name, self.strict_mode, "throttle", (args[0],))
        else:
            raise ValueError(f"Invalid call on EffectBuilder. Use stack(n) or throttle(ms) only.")

    @property
    def replace(self) -> 'EffectBuilder':
        """Set repeat strategy to replace

        Usage:
            rig.tag("x").replace.pos.to(...)
        """
        return EffectBuilder(self.rig_state, self.name, self.strict_mode, "replace", ())

    @property
    def queue(self) -> 'EffectBuilder':
        """Set repeat strategy to queue

        Usage:
            rig.tag("x").queue.pos.to(...)
        """
        return EffectBuilder(self.rig_state, self.name, self.strict_mode, "queue", ())

    @property
    def ignore(self) -> 'EffectBuilder':
        """Set repeat strategy to ignore

        Usage:
            rig.tag("x").ignore.pos.to(...)
        """
        return EffectBuilder(self.rig_state, self.name, self.strict_mode, "ignore", ())

    @property
    def throttle(self) -> 'EffectBuilder':
        """Set repeat strategy to throttle (requires duration via call)

        Usage:
            rig.tag("x").throttle(300).pos.to(...)
        """
        return EffectBuilder(self.rig_state, self.name, self.strict_mode, "throttle", ())

    def revert(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> 'EffectBuilder':
        """Revert this effect (removes all operations)

        Args:
            duration_ms: Duration in milliseconds (time-based), 0 for instant
            easing: Easing function name
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
        # Validate and check if rate parameters are provided
        rate_provided = validate_rate_params(duration_ms, rate_speed, rate_accel, rate_rotation)

        # Calculate duration from rate if provided
        if rate_provided:
            # Get all effect stacks to calculate total effect strength
            keys = [key for key in self.rig_state._effect_stacks
                   if key.startswith(f"{self.name}:")]

            if keys:
                # Use the first stack to determine property type and calculate fade duration
                key = keys[0]
                stack = self.rig_state._effect_stacks[key]
                total = abs(stack.get_total())

                if rate_speed is not None and stack.property == "speed":
                    duration_ms = calculate_duration_from_rate(total, rate_speed)
                elif rate_accel is not None and stack.property == "accel":
                    duration_ms = calculate_duration_from_rate(total, rate_accel)
                elif rate_rotation is not None and stack.property == "direction":
                    duration_ms = calculate_duration_from_rate(total, rate_rotation)
                else:
                    # Default fallback if rate doesn't match property
                    duration_ms = 500.0
            else:
                # No stacks to revert
                return self

        # Revert all effect stacks for this entity
        keys_to_revert = [key for key in self.rig_state._effect_stacks
                         if key.startswith(f"{self.name}:")]

        for key in keys_to_revert:
            if key in self.rig_state._effect_lifecycles:
                # Effect has lifecycle - request stop
                effect = self.rig_state._effect_lifecycles[key]
                effect.request_stop(duration_ms, easing)
            elif duration_ms is not None and duration_ms > 0:
                # Effect has no lifecycle but user wants gradual revert - create lifecycle for fadeout
                stack = self.rig_state._effect_stacks[key]
                lifecycle = EffectLifecycle(stack, self.rig_state)
                # Configure to start at full strength and fade out
                lifecycle.configure_lifecycle(
                    in_duration_ms=None,  # No fade in
                    hold_duration_ms=None,  # No hold
                    out_duration_ms=duration_ms,
                    out_easing=easing
                )
                # Start at full strength (already applied)
                lifecycle.start()
                # Immediately request stop so it fades out
                lifecycle.request_stop(duration_ms, easing)
                # Store the lifecycle so it gets updated
                self.rig_state._effect_lifecycles[key] = lifecycle
            else:
                # Immediate removal if no lifecycle and no duration
                del self.rig_state._effect_stacks[key]
                if key in self.rig_state._effect_order:
                    self.rig_state._effect_order.remove(key)

        # Start the update loop to apply the revert (especially important when stopped)
        self.rig_state.start()

        return self




class EffectSpeedBuilder(EffectBuilderBase['EffectSpeedBuilder']):
    """Builder for effect speed operations (to/mul/div/add/sub)"""
    _property_name = "speed"

    @property
    def max(self) -> 'MaxBuilder':
        """Access max constraints"""
        return MaxBuilder(self.rig_state, self.name, "speed", None)



class EffectAccelBuilder(EffectBuilderBase['EffectAccelBuilder']):
    """Builder for effect accel operations (to/mul/div/add/sub)"""
    _property_name = "accel"



class EffectDirectionBuilder(EffectBuilderBase['EffectDirectionBuilder']):
    """Builder for effect direction operations (rotation in degrees)"""
    _property_name = "direction"

    def to(self, *args) -> 'EffectDirectionBuilder':
        """Set direction to specific angle (degrees) or vector (x, y)"""
        stack = self._get_or_create_stack("to")
        if len(args) == 1:
            # Angle in degrees
            stack.values = [args[0]]
        elif len(args) == 2:
            # Vector (x, y)
            stack.values = [Vec2(args[0], args[1])]
        else:
            raise ValueError("direction.to() requires 1 arg (degrees) or 2 args (x, y)")
        self._last_op_type = "to"
        return self



class EffectPosBuilder(EffectBuilderBase['EffectPosBuilder']):
    """Builder for effect position operations (offsets)"""
    _property_name = "pos"

    def to(self, x: float, y: float) -> 'EffectPosBuilder':
        """Set offset to specific position"""
        stack = self._get_or_create_stack("to")
        stack.values = [Vec2(x, y)]
        self._last_op_type = "to"
        return self

    def add(self, x: float, y: float) -> 'EffectPosBuilder':
        """Add position offset (stacks by default - unlimited)"""
        self._apply_operation("add", Vec2(x, y))
        self._last_op_type = "add"
        return self

    def by(self, x: float, y: float) -> 'EffectPosBuilder':
        """Alias for add (offset by vector)"""
        return self.add(x, y)

    def sub(self, x: float, y: float) -> 'EffectPosBuilder':
        """Subtract position offset (stacks by default - unlimited)"""
        self._apply_operation("sub", Vec2(-x, -y))
        self._last_op_type = "sub"
        return self



class MaxBuilder:
    """Builder for max constraints on effect operations"""
    def __init__(self, rig_state: 'RigState', name: str, property: str, operation_type: str):
        self.rig_state = rig_state
        self.name = name
        self.property = property
        self.operation_type = operation_type

    def __call__(self, value: Union[float, int]) -> 'MaxBuilder':
        """Set max constraint on current property (context-aware shorthand)

        Examples:
            rig("boost").shift.speed.by(10).max(50)         # max speed value
            rig("drift").shift.direction.by(45).max(90)     # max rotation degrees
            rig("boost").shift.speed.by(10).max.stack(3)    # max stack count
        """
        if self.property == "speed":
            return self.speed(value)
        elif self.property == "accel":
            return self.accel(value)
        elif self.property == "direction":
            return self.direction(value)
        elif self.property == "pos":
            return self.pos(value)
        return self

    def speed(self, value: float) -> 'MaxBuilder':
        """Set maximum speed constraint"""
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_value = value
        return self

    def accel(self, value: float) -> 'MaxBuilder':
        """Set maximum accel constraint"""
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_value = value
        return self

    def direction(self, value: float) -> 'MaxBuilder':
        """Set maximum direction rotation constraint (in degrees)

        Example:
            rig("drift").shift.direction.by(45).max.direction(90)  # Cap at 90° total
        """
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_value = value
        return self

    def pos(self, value: float) -> 'MaxBuilder':
        """Set maximum position offset magnitude constraint

        Example:
            rig("shake").shift.pos.by(10, 10).max.pos(50)  # Cap total offset magnitude
        """
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_value = value
        return self

    def stack(self, count: int) -> 'MaxBuilder':
        """Set maximum stack count"""
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_stack_count = count
        return self
