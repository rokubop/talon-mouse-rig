"""Universal RigBuilder - the single builder type for all operations

All fluent API calls return RigBuilder. Execution happens on __del__.
"""

import math
import time
from talon import ctrl
from typing import Optional, Callable, Any, TYPE_CHECKING
from .core import Vec2, EPSILON
from .contracts import BuilderConfig, LifecyclePhase, validate_timing, validate_has_operation
from .lifecycle import Lifecycle, PropertyAnimator
from . import rate_utils
from . import mode_operations

if TYPE_CHECKING:
    from .state import RigState


class BehaviorProxy:
    """Proxy that allows both .queue and .queue() syntax"""

    def __init__(self, builder: 'RigBuilder', behavior_name: str, has_args: bool = False):
        self.builder = builder
        self.behavior_name = behavior_name
        self.has_args = has_args

    def __call__(self, *args):
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        return method(*args)

    def __getattr__(self, name):
        # Auto-apply the behavior first
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        method()
        return getattr(self.builder, name)


class ModeProxy:
    """Proxy for mode-based property access (.offset, .override, .scale)"""

    def __init__(self, builder: 'RigBuilder', mode: str):
        self.builder = builder
        self.mode = mode

    @property
    def pos(self) -> 'PropertyBuilder':
        self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "pos")

    @property
    def speed(self) -> 'PropertyBuilder':
        self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "speed")

    @property
    def direction(self) -> 'PropertyBuilder':
        self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "direction")

    @property
    def vector(self) -> 'PropertyBuilder':
        self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "vector")


class RigBuilder:
    """Universal builder for all mouse rig operations

    This is the ONLY builder type. All methods return self for chaining.
    Execution happens when the Python object is garbage collected (__del__).
    """

    def __init__(self, rig_state: 'RigState', layer: Optional[str] = None, order: Optional[int] = None):
        self.rig_state = rig_state
        self.config = BuilderConfig()

        # Auto-generate layer if anonymous (base layer)
        if layer is None:
            self.config.layer_name = rig_state._generate_base_layer_name()
        else:
            self.config.layer_name = layer

        # Set order if provided
        if order is not None:
            self.config.order = order

        self._executed = False
        self._lifecycle_stage = None  # Track which stage we're adding callbacks to

    @property
    def is_anonymous(self) -> bool:
        """Check if this is an anonymous builder (base layer without user-defined name)"""
        return self.config.layer_name == "__base__"

    # ========================================================================
    # MODE ACCESSORS
    # ========================================================================

    @property
    def offset(self) -> 'ModeProxy':
        return ModeProxy(self, "offset")

    @property
    def override(self) -> 'ModeProxy':
        return ModeProxy(self, "override")

    @property
    def scale(self) -> 'ModeProxy':
        return ModeProxy(self, "scale")

    # ========================================================================
    # PROPERTY ACCESSORS (return PropertyBuilder helper)
    # ========================================================================

    @property
    def pos(self) -> 'PropertyBuilder':
        return PropertyBuilder(self, "pos")

    @property
    def speed(self) -> 'PropertyBuilder':
        return PropertyBuilder(self, "speed")

    @property
    def direction(self) -> 'PropertyBuilder':
        return PropertyBuilder(self, "direction")

    @property
    def vector(self) -> 'PropertyBuilder':
        return PropertyBuilder(self, "vector")

    def __getattr__(self, name: str):
        """Handle unknown attributes with helpful error messages"""
        from .contracts import RigAttributeError, find_closest_match, VALID_BUILDER_METHODS

        # Valid properties are handled above
        valid_properties = ['pos', 'speed', 'direction', 'vector']
        all_valid = valid_properties + VALID_BUILDER_METHODS

        # Find closest match
        suggestion = find_closest_match(name, all_valid)

        msg = f"RigBuilder has no attribute '{name}'"
        if suggestion:
            msg += f"\n\nDid you mean: '{suggestion}'?"
        else:
            msg += f"\n\nAvailable properties: {', '.join(valid_properties)}"
            msg += f"\nAvailable methods: {', '.join(VALID_BUILDER_METHODS)}"

        raise RigAttributeError(msg)

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    def over(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp",
        **kwargs
    ) -> 'RigBuilder':
        """Set transition duration or rate

        Args:
            ms: Duration in milliseconds
            easing: Easing function ("linear", "ease_in", "ease_out", "ease_in_out")
            rate: Rate-based duration (units/sec, degrees/sec, pixels/sec)
            interpolation: Interpolation method - "lerp" (default) or "slerp" (for direction)
        """
        # Validate using contract
        all_kwargs = {'easing': easing, 'interpolation': interpolation, **kwargs}
        self.config.validate_method_kwargs('over', **all_kwargs)

        # Validate that there's an operation to transition over
        validate_has_operation(self.config, 'over')

        if rate is not None:
            # Rate-based, duration will be calculated later
            self.config.over_rate = validate_timing(rate, 'rate', method='over')
            self.config.over_easing = easing
        else:
            self.config.over_ms = validate_timing(ms, 'ms', method='over') if ms is not None else 0
            self.config.over_easing = easing

        self.config.over_interpolation = interpolation

        # When .over() is called, this becomes asynchronous (frame loop execution)
        self.config.is_synchronous = False

        self._lifecycle_stage = LifecyclePhase.OVER
        return self

    def hold(self, ms: float) -> 'RigBuilder':
        # Validate that there's an operation to hold
        validate_has_operation(self.config, 'hold')

        self.config.hold_ms = validate_timing(ms, 'ms', method='hold')
        self._lifecycle_stage = LifecyclePhase.HOLD
        return self

    def revert(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp",
        **kwargs
    ) -> 'RigBuilder':
        """Set revert duration or rate

        Args:
            ms: Duration in milliseconds
            easing: Easing function ("linear", "ease_in", "ease_out", "ease_in_out")
            rate: Rate-based duration (units/sec, degrees/sec, pixels/sec)
            interpolation: Interpolation method - "lerp" (default) or "slerp" (for direction)
        """
        # Validate using contract
        all_kwargs = {'easing': easing, 'interpolation': interpolation, **kwargs}
        self.config.validate_method_kwargs('revert', **all_kwargs)

        if rate is not None:
            self.config.revert_rate = validate_timing(rate, 'rate', method='revert')
            self.config.revert_easing = easing
        else:
            self.config.revert_ms = validate_timing(ms, 'ms', method='revert') if ms is not None else 0
            self.config.revert_easing = easing

        self.config.revert_interpolation = interpolation

        # When .revert() is called, this becomes asynchronous (frame loop execution)
        self.config.is_synchronous = False

        self._lifecycle_stage = LifecyclePhase.REVERT
        return self

    def then(self, callback: Callable) -> 'RigBuilder':
        stage = self._lifecycle_stage or LifecyclePhase.OVER
        self.config.then_callbacks.append((stage, callback))
        return self

    # ========================================================================
    # BEHAVIOR METHODS
    # ========================================================================

    @property
    def stack(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'stack', has_args=True)

    def _set_stack(self, max_count: Optional[int] = None) -> 'RigBuilder':
        self.config.behavior = "stack"
        self.config.behavior_args = (max_count,) if max_count is not None else ()
        return self

    @property
    def reset(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'reset')

    def _set_reset(self) -> 'RigBuilder':
        self.config.behavior = "reset"
        return self

    @property
    def queue(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'queue')

    def _set_queue(self) -> 'RigBuilder':
        self.config.behavior = "queue"
        return self

    @property
    def extend(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'extend')

    def _set_extend(self) -> 'RigBuilder':
        self.config.behavior = "extend"
        return self

    @property
    def throttle(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'throttle', has_args=False)

    def _set_throttle(self, ms: Optional[float] = None) -> 'RigBuilder':
        """Internal: Set throttle behavior

        If ms is None, sets behavior to 'ignore' (ignore while active)
        If ms is provided, sets behavior to 'throttle' with rate limiting
        """
        if ms is None:
            self.config.behavior = "ignore"
        else:
            self.config.behavior = "throttle"
            self.config.behavior_args = (ms,)
        return self

    # ========================================================================
    # BAKE CONTROL
    # ========================================================================

    def bake(self, value: bool = True) -> 'RigBuilder':
        self.config.bake_value = value
        return self

    # ========================================================================
    # EXECUTION (on __del__)
    # ========================================================================

    def __del__(self):
        if not self._executed:
            self._execute()

    def _execute(self):
        """Validate and execute the builder"""
        self._executed = True

        # Special case: revert-only call (no property/operator set)
        if self.config.property is None and self.config.operator is None:
            if self.config.revert_ms is not None:
                # This is a revert() call on an existing is_named_layer builder
                self.rig_state.trigger_revert(self.config.layer_name, self.config.revert_ms, self.config.revert_easing)
                return

            # Incomplete builder, ignore
            return

        # self._detect_and_apply_special_cases()

        self.config.validate_mode()
        self.config.validate_hold()

        self._calculate_rate_durations()

        active = ActiveBuilder(self.config, self.rig_state, self.is_anonymous)
        self.rig_state.add_builder(active)

    def _detect_and_apply_special_cases(self):
        """Detect and apply any necessary config transformations

        Checks for special cases that need to be rewritten before execution.
        """
        # Transform 180° direction reversals to vector operations for smooth zero transitions
        if (self.is_anonymous and
            self.config.property == "direction" and
            (self.config.operator == "to" or self.config.operator == "mul")):

            # Check if this is actually a 180° reversal before transforming
            current_dir = self.rig_state.base.direction

            # Calculate target direction based on operator
            if self.config.operator == "to":
                target_dir = Vec2.from_tuple(self.config.value).normalized()
            else:  # mul
                scalar = self.config.value
                target_dir = Vec2(current_dir.x * scalar, current_dir.y * scalar).normalized()

            # Only transform if approximately 180° (dot product ≈ -1)
            dot_product = current_dir.dot(target_dir)
            if dot_product < -0.99:
                # Commenting out vector conversion - using new linear interpolation approach instead
                # self._convert_direction_reversal_to_vector()
                pass

    def _convert_direction_reversal_to_vector(self):
        """Convert 180° direction reversals to vector operations

        This allows smooth velocity transitions through zero when reversing direction.
        Transforms the config in-place from direction to vector property.
        Only called after 180° reversal is already detected.

        NOTE: Currently disabled in favor of linear interpolation approach in ActiveBuilder.__init__
        """
        # Convert to vector reversal which supports smooth zero transitions
        current_velocity = self.rig_state.base.direction * self.rig_state.base.speed
        reversed_velocity = current_velocity * -1

        # Transform config to vector operation (preserves all lifecycle settings)
        self.config.property = "vector"
        self.config.operator = "to"
        self.config.value = (reversed_velocity.x, reversed_velocity.y)
        self.config.mode = "override"

    def _calculate_rate_durations(self):
        """Calculate durations from rate parameters"""
        if self.config.property is None or self.config.operator is None:
            return

        # Get current and target values
        current_value = self._get_base_value()
        target_value = self._calculate_target_value(current_value)

        # Calculate over duration from rate
        if self.config.over_rate is not None:
            if self.config.property == "speed":
                self.config.over_ms = rate_utils.calculate_speed_duration(
                    current_value, target_value, self.config.over_rate
                )
            elif self.config.property == "direction":
                if self.config.operator == "to":
                    current_dir = self.rig_state.base.direction
                    target_dir = Vec2.from_tuple(self.config.value).normalized()
                    self.config.over_ms = rate_utils.calculate_direction_duration(
                        current_dir, target_dir, self.config.over_rate
                    )
                elif self.config.operator in ("by", "add"):
                    angle_delta = self.config.value[0] if isinstance(self.config.value, tuple) else self.config.value
                    self.config.over_ms = rate_utils.calculate_direction_by_duration(
                        angle_delta, self.config.over_rate
                    )
            elif self.config.property == "pos":
                if self.config.operator == "to":
                    current_pos = self.rig_state.base.pos
                    target_pos = Vec2.from_tuple(self.config.value)
                    self.config.over_ms = rate_utils.calculate_position_duration(
                        current_pos, target_pos, self.config.over_rate
                    )
                elif self.config.operator in ("by", "add"):
                    offset = Vec2.from_tuple(self.config.value)
                    self.config.over_ms = rate_utils.calculate_position_by_duration(
                        offset, self.config.over_rate
                    )
            elif self.config.property == "vector":
                # For vector, use default rate as speed rate, or require explicit rate parameter
                current_vec = self.rig_state.base.direction * self.rig_state.base.speed
                target_vec = Vec2.from_tuple(self.config.value) if self.config.operator == "to" else current_vec + Vec2.from_tuple(self.config.value)
                # Use rate as speed rate (could be extended to support separate speed/direction rates)
                self.config.over_ms = rate_utils.calculate_vector_duration(
                    current_vec, target_vec, self.config.over_rate, self.config.over_rate
                )

        # Calculate revert duration from rate
        if self.config.revert_rate is not None:
            if self.config.property == "speed":
                self.config.revert_ms = rate_utils.calculate_speed_duration(
                    target_value, current_value, self.config.revert_rate
                )
            elif self.config.property == "direction":
                if self.config.operator == "to":
                    current_dir = self.rig_state.base.direction
                    target_dir = Vec2.from_tuple(self.config.value).normalized()
                    self.config.revert_ms = rate_utils.calculate_direction_duration(
                        target_dir, current_dir, self.config.revert_rate
                    )
                elif self.config.operator in ("by", "add"):
                    angle_delta = self.config.value[0] if isinstance(self.config.value, tuple) else self.config.value
                    self.config.revert_ms = rate_utils.calculate_direction_by_duration(
                        angle_delta, self.config.revert_rate
                    )
            elif self.config.property == "pos":
                if self.config.operator == "to":
                    current_pos = self.rig_state.base.pos
                    target_pos = Vec2.from_tuple(self.config.value)
                    self.config.revert_ms = rate_utils.calculate_position_duration(
                        target_pos, current_pos, self.config.revert_rate
                    )
                elif self.config.operator in ("by", "add"):
                    offset = Vec2.from_tuple(self.config.value)
                    self.config.revert_ms = rate_utils.calculate_position_by_duration(
                        offset, self.config.revert_rate
                    )
            elif self.config.property == "vector":
                # For vector revert, calculate from target back to current
                current_vec = self.rig_state.base.direction * self.rig_state.base.speed
                target_vec = Vec2.from_tuple(self.config.value) if self.config.operator == "to" else current_vec + Vec2.from_tuple(self.config.value)
                self.config.revert_ms = rate_utils.calculate_vector_duration(
                    target_vec, current_vec, self.config.revert_rate, self.config.revert_rate
                )

    def _get_base_value(self) -> Any:
        """Get current base value for this property"""
        if self.config.property == "speed":
            return self.rig_state.base.speed
        elif self.config.property == "direction":
            return self.rig_state.base.direction
        elif self.config.property == "pos":
            return self.rig_state.base.pos
        elif self.config.property == "vector":
            # Return velocity vector (direction * speed)
            return self.rig_state.base.direction * self.rig_state.base.speed
        return 0

    def _calculate_target_value(self, current: Any) -> Any:
        """Calculate target value after operator is applied"""
        operator = self.config.operator
        value = self.config.value

        if self.config.property == "speed":
            if operator == "to":
                return value
            elif operator in ("by", "add"):
                return current + value
            elif operator == "sub":
                return current - value
            elif operator == "mul":
                return current * value
            elif operator == "div":
                return current / value if value != 0 else current

        elif self.config.property == "direction":
            if operator == "to":
                return Vec2.from_tuple(value).normalized()
            elif operator in ("by", "add"):
                # Rotation by degrees
                angle_deg = value[0] if isinstance(value, tuple) else value
                angle_rad = math.radians(angle_deg)
                cos_a = math.cos(angle_rad)
                sin_a = math.sin(angle_rad)
                new_x = current.x * cos_a - current.y * sin_a
                new_y = current.x * sin_a + current.y * cos_a
                return Vec2(new_x, new_y).normalized()

        elif self.config.property == "pos":
            if operator == "to":
                return Vec2.from_tuple(value)
            elif operator in ("by", "add"):
                return current + Vec2.from_tuple(value)

        return current


class PropertyBuilder:
    """Helper for property operations - thin wrapper that configures RigBuilder"""

    def __init__(self, rig_builder: RigBuilder, property_name: str):
        from .contracts import ConfigError

        self.rig_builder = rig_builder
        self.property_name = property_name

        # Check if a property is already set - can't chain multiple properties
        if self.rig_builder.config.property is not None and self.rig_builder.config.property != property_name:
            self.rig_builder._executed = True
            raise ConfigError(
                f"Cannot combine multiple properties in one command.\n\n"
                f"Attempting to set both '{self.rig_builder.config.property}' and '{property_name}'.\n\n"
                f"Use separate commands instead:\n\n"
                f"  rig.{self.rig_builder.config.property}(...)\n"
                f"  rig.{property_name}(...)"
            )

        # Set property on builder
        self.rig_builder.config.property = property_name

    # Mode accessors for property.mode.operation() syntax
    @property
    def offset(self) -> 'PropertyBuilder':
        self.rig_builder.config.mode = "offset"
        return self

    @property
    def override(self) -> 'PropertyBuilder':
        self.rig_builder.config.mode = "override"
        return self

    @property
    def scale(self) -> 'PropertyBuilder':
        self.rig_builder.config.mode = "scale"
        return self

    def to(self, *args) -> RigBuilder:
        self.rig_builder.config.operator = "to"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        self.rig_builder.config.validate_property_operator()

        # Position operations are synchronous by default (instant execution)
        if self.rig_builder.config.property == "pos":
            self.rig_builder.config.is_synchronous = True
            # pos.to() needs absolute positioning (reads ctrl.mouse_pos())
            self.rig_builder.config.movement_type = "absolute"
        # else: keep default "relative" for speed.to(), direction.to()

        return self.rig_builder

    def add(self, *args) -> RigBuilder:
        self.rig_builder.config.operator = "add"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        self.rig_builder.config.validate_property_operator()

        # Position operations are synchronous by default (instant execution)
        if self.rig_builder.config.property == "pos":
            self.rig_builder.config.is_synchronous = True

        # All add/by operations use relative movement (pure deltas)
        self.rig_builder.config.movement_type = "relative"

        return self.rig_builder

    def by(self, *args) -> RigBuilder:
        return self.add(*args)

    def sub(self, *args) -> RigBuilder:
        self.rig_builder.config.operator = "sub"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        self.rig_builder.config.validate_property_operator()
        return self.rig_builder

    def mul(self, value: float) -> RigBuilder:
        self.rig_builder.config.operator = "mul"
        self.rig_builder.config.value = value
        self.rig_builder.config.validate_property_operator()
        return self.rig_builder

    def div(self, value: float) -> RigBuilder:
        self.rig_builder.config.operator = "div"
        self.rig_builder.config.value = value
        self.rig_builder.config.validate_property_operator()
        return self.rig_builder

    def bake(self) -> RigBuilder:
        """Bake current computed value into base state

        Examples:
            rig.direction.bake()  # Bakes current direction to base
            rig.layer("boost").speed.bake()  # Bakes boost's speed to base
        """
        self.rig_builder.config.operator = "bake"
        self.rig_builder.config.value = None
        self.rig_builder.config.validate_property_operator()
        return self.rig_builder

    def scale(self, value: float) -> RigBuilder:
        """Scale accumulated operations retroactively

        Scale is a retroactive multiplier applied to accumulated values within a layer.
        Last scale wins per layer.

        Examples:
            rig.layer("boost").speed.add(5).scale(2)  # Add 10 instead of 5
            rig.final.speed.scale(2)  # Scale final layer's accumulated value
        """
        self.rig_builder.config.operator = "scale"
        self.rig_builder.config.value = value
        self.rig_builder.config.validate_property_operator()
        return self.rig_builder

    def revert(self, ms: Optional[float] = None, easing: str = "linear", **kwargs) -> RigBuilder:
        """Revert this property/layer

        For anonymous builders, reverts all anonymous builders affecting this property.
        For is_named_layer builders, reverts the entire layer (same as layer.revert()).

        Examples:
            rig.speed.revert(500)  # Revert all anonymous speed changes
            layer("boost").speed.revert(500)  # Revert boost layer
        """
        return self.rig_builder.revert(ms, easing, **kwargs)

    # Shorthand for anonymous only
    def __call__(self, *args) -> RigBuilder:
        """Shorthand: rig.speed(5) -> rig.speed.to(5)

        Only works for anonymous builders.
        """
        return self.to(*args)


class ActiveBuilder:
    """An active builder being executed in the state manager

    Every builder has a children list that starts with [self].
    This provides uniform handling for single builders and groups.
    """

    def __init__(self, config: BuilderConfig, rig_state: 'RigState', is_anonymous: bool):
        import time

        self.config = config
        self.rig_state = rig_state
        self.is_anonymous = is_anonymous
        self.layer = config.layer_name
        self.creation_time = time.perf_counter()

        # For anonymous layers, set mode based on operator semantics
        if config.mode is None and is_anonymous:
            if config.operator == "to":
                config.mode = "override"  # Absolute value
            elif config.operator in ("mul", "div"):
                config.mode = "scale"  # Multiplicative
            else:
                config.mode = "offset"  # Additive contribution

        # Children list - starts empty, only actual children added
        self.children: list['ActiveBuilder'] = []

        # Group lifecycle for coordinated operations (like revert)
        self.group_lifecycle: Optional[Lifecycle] = None
        self.group_base_value: Optional[Any] = None
        self.group_target_value: Optional[Any] = None

        # Flag to mark builder for removal (set when group_lifecycle completes)
        self._marked_for_removal: bool = False

        # Create lifecycle
        self.lifecycle = Lifecycle(is_user_layer=not is_anonymous)
        self.lifecycle.over_ms = config.over_ms
        self.lifecycle.over_easing = config.over_easing
        self.lifecycle.hold_ms = config.hold_ms
        self.lifecycle.revert_ms = config.revert_ms
        self.lifecycle.revert_easing = config.revert_easing

        # Add callbacks
        for stage, callback in config.then_callbacks:
            self.lifecycle.add_callback(stage, callback)

        # Calculate values - branch on movement_type for position operations
        if config.operator == "to":
            # For 'to' operations, we need the current computed value
            # This "bakes" the current state before transitioning to new target
            if config.property == "pos":
                if config.movement_type == "absolute":
                    # pos.to() - read absolute position from screen
                    self.base_value = Vec2(*ctrl.mouse_pos())
                else:
                    # Shouldn't happen (pos.to is always absolute), but handle gracefully
                    self.base_value = Vec2(0, 0)
            else:
                # speed.to(), direction.to() - use computed state (relative)
                self.base_value = getattr(rig_state, config.property)
        elif config.operator in ("by", "add"):
            # For relative operations
            if config.property == "pos" and config.movement_type == "relative":
                # pos.by() - pure delta, start at zero
                self.base_value = Vec2(0, 0)
            else:
                # speed.by(), direction.by() - use base state
                self.base_value = self._get_base_value()
        else:
            # For all other operations (sub, mul, div), use base state
            self.base_value = self._get_base_value()

        self.target_value = self._calculate_target_value()

        # Auto-detect same-axis direction reversal for smooth zero-crossing
        if (config.property == "direction" and
            config.operator == "to" and
            config.over_ms is not None and
            config.over_ms > 0):
            if self._is_same_axis_reversal(self.base_value, self.target_value):
                config.over_interpolation = 'linear'
                config.revert_interpolation = 'linear'

    def _is_same_axis_reversal(self, base_dir: Vec2, target_dir: Vec2) -> bool:
        base_x_zero = abs(base_dir.x) < 0.01
        base_y_zero = abs(base_dir.y) < 0.01
        target_x_zero = abs(target_dir.x) < 0.01
        target_y_zero = abs(target_dir.y) < 0.01

        opposite_direction = base_dir.dot(target_dir) < -0.9

        return ((base_x_zero and target_x_zero) or (base_y_zero and target_y_zero)) and opposite_direction

    def __repr__(self) -> str:
        phase = self.lifecycle.phase if self.lifecycle and self.lifecycle.phase else "instant"
        return f"<ActiveBuilder '{self.layer}' {self.config.property}.{self.config.operator}({self.target_value}) mode={self.config.mode} phase={phase}>"

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def time_alive(self) -> float:
        """Get time in seconds since this builder was created"""
        import time
        return time.perf_counter() - self.creation_time

    def _get_base_value(self) -> Any:
        """Get current base value for this property"""
        if self.config.property == "speed":
            return self.rig_state.base.speed
        elif self.config.property == "direction":
            return self.rig_state.base.direction
        elif self.config.property == "pos":
            return self.rig_state.base.pos
        elif self.config.property == "vector":
            # Return velocity vector (direction * speed)
            return self.rig_state.base.direction * self.rig_state.base.speed
        return 0

    def _calculate_target_value(self) -> Any:
        """Calculate target value after operator is applied

        The stored value depends on the mode:
        - offset mode: stores the CONTRIBUTION value (what gets added)
        - override mode: stores the ABSOLUTE target value
        - scale mode: stores the MULTIPLIER
        """
        operator = self.config.operator
        value = self.config.value
        current = self.base_value
        mode = self.config.mode

        # Bake operation: immediately set base to current computed value
        if operator == "bake":
            # Return None - bake is handled immediately in state manager
            return None

        if self.config.property == "speed":
            return mode_operations.calculate_scalar_target(operator, value, current, mode)

        elif self.config.property == "direction":
            return mode_operations.calculate_direction_target(operator, value, current, mode)

        elif self.config.property == "pos":
            return mode_operations.calculate_position_target(operator, value, current, mode)

        elif self.config.property == "vector":
            # For vector, current is velocity (direction * speed)
            current_speed = self.rig_state.base.speed
            current_direction = self.rig_state.base.direction
            return mode_operations.calculate_vector_target(operator, value, current_speed, current_direction, mode)

        return current

    def execute_synchronous(self):
        """Execute this builder synchronously (instant, no animation)

        Applies the operation immediately and updates internal state.
        Only called for synchronous operations (no .over() or .revert()).

        Mode-aware execution:
        - offset: target_value is offset to add
        - override: target_value is absolute position
        - scale: target_value is multiplier
        """
        if self.config.property == "pos":
            if self.config.movement_type == "absolute":
                # Absolute positioning (pos.to)
                mode = self.config.mode
                current_value = self.target_value

                # Sync to actual current mouse position (in case user manually moved it)
                current_mouse_pos = ctrl.mouse_pos()
                self.rig_state._internal_pos = Vec2(current_mouse_pos[0], current_mouse_pos[1])
                self.rig_state._base_pos = Vec2(current_mouse_pos[0], current_mouse_pos[1])

                # Apply mode to current internal position
                new_pos = mode_operations.apply_position_mode(mode, current_value, self.rig_state._internal_pos)
                self.rig_state._internal_pos = new_pos
                self.rig_state._base_pos = Vec2(new_pos.x, new_pos.y)

                # Move mouse immediately
                from .core import mouse_move
                mouse_move(int(self.rig_state._internal_pos.x), int(self.rig_state._internal_pos.y))
            else:
                # Relative positioning (pos.by) - just emit the delta
                delta = self.target_value  # This is the delta (dx, dy)
                from .core import mouse_move_relative
                mouse_move_relative(int(delta.x), int(delta.y))

        # Add other property types here as needed (speed, direction, etc.)

    def add_child(self, child: 'ActiveBuilder'):
        """Add a child builder to this parent

        The child is appended to the children list for aggregation.
        Different behavior modes are handled by the caller (state.py).
        """
        self.children.append(child)

    def advance(self, current_time: float) -> bool:
        """Advance this builder and all children forward in time.

        Args:
            current_time: Current timestamp from perf_counter() (captured once per frame)

        Returns:
            True if still active, False if should be removed and garbage collected
        """
        # Update group lifecycle if active (for coordinated revert)
        group_reverted = False
        if self.group_lifecycle:
            self.group_lifecycle.advance(current_time)
            if self.group_lifecycle.is_complete():
                # Check if it completed via revert
                if self.group_lifecycle.has_reverted():
                    group_reverted = True
                self.group_lifecycle = None
                self._marked_for_removal = True  # Mark for removal
                return False  # Signal removal

        # Update own lifecycle (only if no group lifecycle is active)
        self.lifecycle.advance(current_time)

        # Update children, remove completed ones
        active_children = []
        for child in self.children:
            child.lifecycle.advance(current_time)
            if not child.lifecycle.should_be_garbage_collected():
                active_children.append(child)

        self.children = active_children

        # Should be removed if own lifecycle says garbage collect AND no children
        should_gc = self.lifecycle.should_be_garbage_collected()
        own_active = not should_gc
        has_children = len(self.children) > 0

        return own_active or has_children

    def _get_own_value(self) -> Any:
        """Get just this builder's own value (not including children)

        Used for aggregation where each child contributes its own value.
        The returned value depends on mode:
        - offset: returns contribution value to add
        - override: returns absolute value to use
        - scale: returns multiplier to apply
        """
        current_time = time.perf_counter()
        phase, progress = self.lifecycle.advance(current_time)
        mode = self.config.mode

        if self.config.property == "speed":
            # Get neutral value based on mode
            if mode == "scale":
                neutral = 1.0  # Scale neutral is 1.0 (no scaling)
            elif mode == "offset":
                neutral = 0.0  # Offset neutral is 0.0 (no contribution)
            else:  # override
                neutral = self.base_value  # Override neutral is base value

            return PropertyAnimator.animate_scalar(
                neutral,
                self.target_value,
                phase,
                progress,
                self.lifecycle.has_reverted()
            )
        elif self.config.property == "direction":
            # Determine which interpolation to use (over or revert)
            interpolation = self.config.over_interpolation
            if phase == LifecyclePhase.REVERT:
                interpolation = self.config.revert_interpolation

            # For direction, neutral depends on mode
            if mode == "offset":
                # For offset mode with angle rotation, animate the angle
                if isinstance(self.target_value, (int, float)):
                    # Animate angle from 0 to target angle
                    neutral_angle = 0.0
                    return PropertyAnimator.animate_scalar(
                        neutral_angle,
                        self.target_value,
                        phase,
                        progress,
                        self.lifecycle.has_reverted()
                    )
                else:
                    # Animate direction vector - use base as neutral for offset
                    return PropertyAnimator.animate_direction(
                        self.base_value,
                        self.target_value,
                        phase,
                        progress,
                        self.lifecycle.has_reverted(),
                        interpolation
                    )
            elif mode == "scale":
                # Scale mode: animate the multiplier from 1.0
                return PropertyAnimator.animate_scalar(
                    1.0,
                    self.target_value,
                    phase,
                    progress,
                    self.lifecycle.has_reverted()
                )
            else:  # override
                # Override: animate from base to absolute target
                return PropertyAnimator.animate_direction(
                    self.base_value,
                    self.target_value,
                    phase,
                    progress,
                    self.lifecycle.has_reverted(),
                    interpolation
                )
        elif self.config.property == "pos":
            # For position, neutral depends on mode
            if mode == "scale":
                # Scale mode: animate multiplier from 1.0
                return PropertyAnimator.animate_scalar(
                    1.0,
                    self.target_value,
                    phase,
                    progress,
                    self.lifecycle.has_reverted()
                )
            elif mode == "offset":
                # Offset mode: animate offset from zero
                neutral = Vec2(0, 0)
                if phase is None:
                    if self.lifecycle.has_reverted():
                        return neutral
                    return self.target_value
                elif phase == LifecyclePhase.OVER:
                    return self.target_value * progress
                elif phase == LifecyclePhase.HOLD:
                    return self.target_value
                elif phase == LifecyclePhase.REVERT:
                    return self.target_value * (1.0 - progress)
            else:  # override
                # Override mode: animate absolute position from base
                if phase is None:
                    if self.lifecycle.has_reverted():
                        return self.base_value
                    return self.target_value
                elif phase == LifecyclePhase.OVER:
                    return Vec2(
                        self.base_value.x + (self.target_value.x - self.base_value.x) * progress,
                        self.base_value.y + (self.target_value.y - self.base_value.y) * progress
                    )
                elif phase == LifecyclePhase.HOLD:
                    return self.target_value
                elif phase == LifecyclePhase.REVERT:
                    return Vec2(
                        self.target_value.x + (self.base_value.x - self.target_value.x) * progress,
                        self.target_value.y + (self.base_value.y - self.target_value.y) * progress
                    )
        elif self.config.property == "vector":
            # For vector, neutral depends on mode
            if mode == "scale":
                # Scale mode: animate multiplier from 1.0 (stored in x component)
                return PropertyAnimator.animate_scalar(
                    1.0,
                    self.target_value.x,
                    phase,
                    progress,
                    self.lifecycle.has_reverted()
                )
            elif mode == "offset":
                # Offset mode: animate velocity vector from zero
                neutral = Vec2(0, 0)
                interpolation = self.config.over_interpolation
                return PropertyAnimator.animate_vector(
                    neutral,
                    self.target_value,
                    phase,
                    progress,
                    self.lifecycle.has_reverted(),
                    interpolation
                )
            else:  # override
                # Override: animate from base velocity to target velocity
                interpolation = self.config.over_interpolation
                return PropertyAnimator.animate_vector(
                    self.base_value,
                    self.target_value,
                    phase,
                    progress,
                    self.lifecycle.has_reverted(),
                    interpolation
                )

        return self.target_value

    def get_interpolated_value(self) -> Any:
        """Get aggregated interpolated value from all children

        If group lifecycle is active (coordinated revert), use that.
        Otherwise aggregate all children's individual values.
        """
        current_time = time.perf_counter()
        # Use group lifecycle if active (coordinated revert)
        if self.group_lifecycle and not self.group_lifecycle.is_complete():
            phase, progress = self.group_lifecycle.advance(current_time)

            # Use builder's own property type (not children, which are cleared during revert)
            property_type = self.config.property

            # Animate from target back to base during revert
            if property_type == "speed":
                return PropertyAnimator.animate_scalar(
                    self.group_base_value,
                    self.group_target_value,
                    phase,
                    progress,
                    self.group_lifecycle.has_reverted()
                )
            elif property_type == "direction":
                # Group revert uses revert interpolation setting
                interpolation = self.config.revert_interpolation
                return PropertyAnimator.animate_direction(
                    self.group_base_value,
                    self.group_target_value,
                    phase,
                    progress,
                    self.group_lifecycle.has_reverted(),
                    interpolation
                )
            elif property_type == "pos":
                return PropertyAnimator.animate_position(
                    self.group_base_value,
                    self.group_target_value,
                    phase,
                    progress,
                    self.group_lifecycle.has_reverted()
                )
            elif property_type == "vector":
                interpolation = self.config.revert_interpolation
                return PropertyAnimator.animate_vector(
                    self.group_base_value,
                    self.group_target_value,
                    phase,
                    progress,
                    self.group_lifecycle.has_reverted(),
                    interpolation
                )

        # Aggregate own value plus all children values
        property_type = self.config.property

        if property_type == "speed":
            # Start with own value, then add children
            total = self._get_own_value()
            for child in self.children:
                if child.config.property == property_type:
                    total += child._get_own_value()
            return total

        elif property_type == "direction":
            # Compose rotations: apply own rotation, then each child's rotation
            current = self._get_own_value()

            # Each child rotation is relative to the result so far
            for child in self.children:
                if child.config.property == "direction":
                    # Get child's CURRENT animated rotation (not target)
                    child_current = child._get_own_value()

                    # For 'add/by' operations, we need to compose the rotations
                    # Extract the rotation from base to current animated position
                    if child.config.operator in ("add", "by"):
                        # Calculate the rotation angle from child's base to current animated value
                        import math
                        child_base = child.base_value

                        # Get angle between base and current animated rotation
                        dot = child_base.x * child_current.x + child_base.y * child_current.y
                        cross = child_base.x * child_current.y - child_base.y * child_current.x
                        angle = math.atan2(cross, dot)

                        # Apply this rotation to current direction
                        cos_a = math.cos(angle)
                        sin_a = math.sin(angle)
                        new_x = current.x * cos_a - current.y * sin_a
                        new_y = current.x * sin_a + current.y * cos_a
                        current = Vec2(new_x, new_y).normalized()
                    else:
                        # For 'to' operations, just use the current value directly
                        current = child_current

            return current

        elif property_type == "pos":
            # Start with own offset, then add children
            total_offset = self._get_own_value()
            for child in self.children:
                if child.config.property == "pos":
                    total_offset = total_offset + child._get_own_value()
            return total_offset

        elif property_type == "vector":
            # For vector, aggregate velocity contributions
            # In scale mode, multiply scalars. In offset/override, add vectors
            mode = self.config.mode

            if mode == "scale":
                # Scale mode: multiply all scale factors
                total_scale = self._get_own_value()
                for child in self.children:
                    if child.config.property == "vector":
                        total_scale *= child._get_own_value()
                return total_scale
            else:
                # Offset/override mode: add velocity vectors
                total_vector = self._get_own_value()
                for child in self.children:
                    if child.config.property == "vector":
                        child_vec = child._get_own_value()
                        if isinstance(child_vec, Vec2):
                            total_vector = total_vector + child_vec
                return total_vector

        # Fallback
        return self._get_own_value()
