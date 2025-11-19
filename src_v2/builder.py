"""Universal RigBuilder - the single builder type for all operations

All fluent API calls return RigBuilder. Execution happens on __del__.
"""

import math
from typing import Optional, Callable, Any, TYPE_CHECKING
from .core import Vec2, EPSILON
from .contracts import BuilderConfig, LifecyclePhase
from .lifecycle import Lifecycle, PropertyAnimator
from . import rate_utils

if TYPE_CHECKING:
    from .state import RigState


class BehaviorProxy:
    """Proxy that allows both .queue and .queue() syntax"""

    def __init__(self, builder: 'RigBuilder', behavior_name: str, has_args: bool = False):
        self.builder = builder
        self.behavior_name = behavior_name
        self.has_args = has_args

    def __call__(self, *args):
        """Handle .queue() syntax"""
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        return method(*args)

    def __getattr__(self, name):
        """Handle .queue.direction syntax (property chaining)"""
        # Auto-apply the behavior first
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        method()  # Call with no args for property-style access
        # Then forward to the builder
        return getattr(self.builder, name)


class RigBuilder:
    """Universal builder for all mouse rig operations

    This is the ONLY builder type. All methods return self for chaining.
    Execution happens when the Python object is garbage collected (__del__).
    """

    def __init__(self, rig_state: 'RigState', tag: Optional[str] = None):
        self.rig_state = rig_state
        self.config = BuilderConfig()

        # Auto-generate tag if anonymous
        if tag is None:
            self.config.tag_name = rig_state.generate_anonymous_tag()
        else:
            self.config.tag_name = tag

        self._executed = False
        self._lifecycle_stage = None  # Track which stage we're adding callbacks to

    @property
    def is_anonymous(self) -> bool:
        """Check if this is an anonymous builder"""
        return self.config.tag_name.startswith("__anon_")

    # ========================================================================
    # PROPERTY ACCESSORS (return PropertyBuilder helper)
    # ========================================================================

    @property
    def pos(self) -> 'PropertyBuilder':
        """Position property accessor"""
        return PropertyBuilder(self, "pos")

    @property
    def speed(self) -> 'PropertyBuilder':
        """Speed property accessor"""
        return PropertyBuilder(self, "speed")

    @property
    def direction(self) -> 'PropertyBuilder':
        """Direction property accessor"""
        return PropertyBuilder(self, "direction")

    @property
    def accel(self) -> 'PropertyBuilder':
        """Acceleration property accessor"""
        return PropertyBuilder(self, "accel")

    # ========================================================================
    # LIFECYCLE METHODS
    # ========================================================================

    def over(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp"
    ) -> 'RigBuilder':
        """Set transition duration or rate

        Args:
            ms: Duration in milliseconds
            easing: Easing function ("linear", "ease_in", "ease_out", "ease_in_out")
            rate: Rate-based duration (units/sec, degrees/sec, pixels/sec)
            interpolation: Interpolation method - "lerp" (default) or "slerp" (for direction)
        """
        if rate is not None:
            # Rate-based, duration will be calculated later
            self.config.over_rate = rate
            self.config.over_easing = easing
        else:
            self.config.over_ms = ms if ms is not None else 0
            self.config.over_easing = easing

        self.config.over_interpolation = interpolation
        self._lifecycle_stage = LifecyclePhase.OVER
        return self

    def hold(self, ms: float) -> 'RigBuilder':
        """Set hold duration"""
        self.config.hold_ms = ms
        self._lifecycle_stage = LifecyclePhase.HOLD
        return self

    def revert(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp"
    ) -> 'RigBuilder':
        """Set revert duration or rate

        Args:
            ms: Duration in milliseconds
            easing: Easing function ("linear", "ease_in", "ease_out", "ease_in_out")
            rate: Rate-based duration (units/sec, degrees/sec, pixels/sec)
            interpolation: Interpolation method - "lerp" (default) or "slerp" (for direction)
        """
        if rate is not None:
            self.config.revert_rate = rate
            self.config.revert_easing = easing
        else:
            self.config.revert_ms = ms if ms is not None else 0
            self.config.revert_easing = easing

        self.config.revert_interpolation = interpolation

        self._lifecycle_stage = LifecyclePhase.REVERT
        return self

    def then(self, callback: Callable) -> 'RigBuilder':
        """Add callback after current lifecycle stage"""
        stage = self._lifecycle_stage or LifecyclePhase.OVER
        self.config.then_callbacks.append((stage, callback))
        return self

    # ========================================================================
    # BEHAVIOR METHODS
    # ========================================================================

    @property
    def stack(self) -> BehaviorProxy:
        """Stack behavior (unlimited or max) - use .stack or .stack(max)"""
        return BehaviorProxy(self, 'stack', has_args=True)

    def _set_stack(self, max_count: Optional[int] = None) -> 'RigBuilder':
        """Internal: Set stack behavior"""
        self.config.behavior = "stack"
        self.config.behavior_args = (max_count,) if max_count is not None else ()
        return self

    @property
    def replace(self) -> BehaviorProxy:
        """Replace behavior (cancel previous) - use .replace or .replace()"""
        return BehaviorProxy(self, 'replace')

    def _set_replace(self) -> 'RigBuilder':
        """Internal: Set replace behavior"""
        self.config.behavior = "replace"
        return self

    @property
    def queue(self) -> BehaviorProxy:
        """Queue behavior (wait for current) - use .queue or .queue()"""
        return BehaviorProxy(self, 'queue')

    def _set_queue(self) -> 'RigBuilder':
        """Internal: Set queue behavior"""
        self.config.behavior = "queue"
        return self

    @property
    def extend(self) -> BehaviorProxy:
        """Extend hold duration - use .extend or .extend()"""
        return BehaviorProxy(self, 'extend')

    def _set_extend(self) -> 'RigBuilder':
        """Internal: Set extend behavior"""
        self.config.behavior = "extend"
        return self

    @property
    def throttle(self) -> BehaviorProxy:
        """Throttle behavior (rate limit) - use .throttle(ms)"""
        return BehaviorProxy(self, 'throttle', has_args=True)

    def _set_throttle(self, ms: float) -> 'RigBuilder':
        """Internal: Set throttle behavior"""
        self.config.behavior = "throttle"
        self.config.behavior_args = (ms,)
        return self

    @property
    def ignore(self) -> BehaviorProxy:
        """Ignore while active - use .ignore or .ignore()"""
        return BehaviorProxy(self, 'ignore')

    def _set_ignore(self) -> 'RigBuilder':
        """Internal: Set ignore behavior"""
        self.config.behavior = "ignore"
        return self

    # ========================================================================
    # BAKE CONTROL
    # ========================================================================

    def bake(self, value: bool = True) -> 'RigBuilder':
        """Control whether changes persist to base"""
        self.config.bake_value = value
        return self

    # ========================================================================
    # EXECUTION (on __del__)
    # ========================================================================

    def __del__(self):
        """Execute builder when garbage collected"""
        if not self._executed:
            self._execute()

    def _execute(self):
        """Validate and execute the builder"""
        self._executed = True


        # Special case: revert-only call (no property/operator set)
        if self.config.property is None and self.config.operator is None:
            if self.config.revert_ms is not None:
                # This is a revert() call on an existing tagged builder
                self.rig_state.trigger_revert(self.config.tag_name, self.config.revert_ms, self.config.revert_easing)
                return

            # Incomplete builder, ignore
            return

        # Calculate rate-based durations
        self._calculate_rate_durations()

        # Create ActiveBuilder and add to state
        active = ActiveBuilder(self.config, self.rig_state, self.is_anonymous)
        self.rig_state.add_builder(active)

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
            elif self.config.property == "accel":
                self.config.over_ms = rate_utils.calculate_accel_duration(
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

        # Calculate revert duration from rate
        if self.config.revert_rate is not None:
            if self.config.property == "speed":
                self.config.revert_ms = rate_utils.calculate_speed_duration(
                    target_value, current_value, self.config.revert_rate
                )
            elif self.config.property == "accel":
                self.config.revert_ms = rate_utils.calculate_accel_duration(
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

    def _get_base_value(self) -> Any:
        """Get current base value for this property"""
        if self.config.property == "speed":
            return self.rig_state.base.speed
        elif self.config.property == "accel":
            return self.rig_state.base.accel
        elif self.config.property == "direction":
            return self.rig_state.base.direction
        elif self.config.property == "pos":
            return self.rig_state.base.pos
        return 0

    def _calculate_target_value(self, current: Any) -> Any:
        """Calculate target value after operator is applied"""
        operator = self.config.operator
        value = self.config.value

        if self.config.property in ("speed", "accel"):
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
        self.rig_builder = rig_builder
        self.property_name = property_name

        # Set property on builder
        self.rig_builder.config.property = property_name

    def to(self, *args) -> RigBuilder:
        """Set absolute value"""
        self.rig_builder.config.operator = "to"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        return self.rig_builder

    def add(self, *args) -> RigBuilder:
        """Add delta"""
        self.rig_builder.config.operator = "add"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        return self.rig_builder

    def by(self, *args) -> RigBuilder:
        """Add delta (alias for add)"""
        return self.add(*args)

    def sub(self, *args) -> RigBuilder:
        """Subtract delta"""
        self.rig_builder.config.operator = "sub"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        return self.rig_builder

    def mul(self, value: float) -> RigBuilder:
        """Multiply"""
        self.rig_builder.config.operator = "mul"
        self.rig_builder.config.value = value
        return self.rig_builder

    def div(self, value: float) -> RigBuilder:
        """Divide"""
        self.rig_builder.config.operator = "div"
        self.rig_builder.config.value = value
        return self.rig_builder

    # Shorthand for anonymous only
    def __call__(self, *args) -> RigBuilder:
        """Shorthand: rig.speed(5) -> rig.speed.to(5)"""
        if not self.rig_builder.is_anonymous:
            raise ValueError("Shorthand syntax only allowed for anonymous builders")
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
        self.tag = config.tag_name
        self.creation_time = time.perf_counter()

        # Children list - starts empty, only actual children added
        self.children: list['ActiveBuilder'] = []

        # Group lifecycle for coordinated operations (like revert)
        self.group_lifecycle: Optional[Lifecycle] = None
        self.group_base_value: Optional[Any] = None
        self.group_target_value: Optional[Any] = None

        # Create lifecycle
        self.lifecycle = Lifecycle(is_tagged=not is_anonymous)
        self.lifecycle.over_ms = config.over_ms
        self.lifecycle.over_easing = config.over_easing
        self.lifecycle.hold_ms = config.hold_ms
        self.lifecycle.revert_ms = config.revert_ms
        self.lifecycle.revert_easing = config.revert_easing

        # Add callbacks
        for stage, callback in config.then_callbacks:
            self.lifecycle.add_callback(stage, callback)

        # Calculate values - use computed current state for certain operations
        if config.operator == "to" and config.property in ("speed", "accel"):
            # For 'to' operations, we need the current computed value
            self.base_value = getattr(rig_state, config.property)
        else:
            # For all other operations (including direction.add), use base state
            # This ensures stacked rotations all rotate from the same base
            self.base_value = self._get_base_value()

        self.target_value = self._calculate_target_value()

    def time_alive(self) -> float:
        """Get time in seconds since this builder was created"""
        import time
        return time.perf_counter() - self.creation_time

    def _get_base_value(self) -> Any:
        """Get current base value for this property"""
        if self.config.property == "speed":
            return self.rig_state.base.speed
        elif self.config.property == "accel":
            return self.rig_state.base.accel
        elif self.config.property == "direction":
            return self.rig_state.base.direction
        elif self.config.property == "pos":
            return self.rig_state.base.pos
        return 0

    def _calculate_target_value(self) -> Any:
        """Calculate target value after operator is applied"""
        operator = self.config.operator
        value = self.config.value
        current = self.base_value

        if self.config.property in ("speed", "accel"):
            if operator == "to":
                return value
            elif operator in ("by", "add"):
                return value  # Return the delta, not absolute
            elif operator == "sub":
                return value  # Return the delta, not absolute
            elif operator == "mul":
                return value  # Return the multiplier
            elif operator == "div":
                return value  # Return the divisor

        elif self.config.property == "direction":
            if operator == "to":
                return Vec2.from_tuple(value).normalized()
            elif operator in ("by", "add"):
                # Support both rotation by degrees and vector addition
                if isinstance(value, tuple) and len(value) == 2:
                    # Vector addition: add delta vector to current direction
                    delta = Vec2.from_tuple(value)
                    return (current + delta).normalized()
                else:
                    # Rotation by degrees (single value)
                    angle_deg = value[0] if isinstance(value, tuple) else value
                    angle_rad = math.radians(angle_deg)
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)
                    new_x = current.x * cos_a - current.y * sin_a
                    new_y = current.x * sin_a + current.y * cos_a
                    return Vec2(new_x, new_y).normalized()
            elif operator == "sub":
                # Vector subtraction: subtract delta vector from current direction
                if isinstance(value, tuple) and len(value) == 2:
                    delta = Vec2.from_tuple(value)
                    return (current - delta).normalized()
                else:
                    # Rotation by negative degrees (single value)
                    angle_deg = value[0] if isinstance(value, tuple) else value
                    angle_rad = math.radians(-angle_deg)  # Negative for subtraction
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)
                    new_x = current.x * cos_a - current.y * sin_a
                    new_y = current.x * sin_a + current.y * cos_a
                    return Vec2(new_x, new_y).normalized()

        elif self.config.property == "pos":
            if operator == "to":
                # Return offset from current position
                target_pos = Vec2.from_tuple(value)
                return target_pos - current
            elif operator in ("by", "add"):
                return Vec2.from_tuple(value)

        return current

    def add_child(self, child: 'ActiveBuilder'):
        """Add a child builder to this parent

        The child is appended to the children list for aggregation.
        Different behavior modes are handled by the caller (state.py).
        """
        self.children.append(child)

    def update(self, dt: float) -> bool:
        """Update this builder and all children.

        Returns:
            True if still active, False if should be removed and garbage collected
        """
        # Update group lifecycle if active (for coordinated revert)
        group_reverted = False
        if self.group_lifecycle:
            self.group_lifecycle.update(dt)
            if self.group_lifecycle.is_complete():
                # Check if it completed via revert
                if self.group_lifecycle.has_reverted():
                    group_reverted = True
                self.group_lifecycle = None
                return False  # Remove immediately when group revert completes

        # Update own lifecycle (only if no group lifecycle is active)
        self.lifecycle.update(dt)

        # Update children, remove completed ones
        active_children = []
        for child in self.children:
            child.lifecycle.update(dt)
            if not child.lifecycle.should_be_garbage_collected():
                active_children.append(child)

        self.children = active_children

        # Should be removed if own lifecycle says garbage collect AND no children
        own_active = not self.lifecycle.should_be_garbage_collected()
        return own_active or len(self.children) > 0

    def _get_own_value(self) -> Any:
        """Get just this builder's own value (not including children)

        Used for aggregation where each child contributes its own value.
        """
        phase, progress = self.lifecycle.update(0)

        if self.config.property in ("speed", "accel"):
            return PropertyAnimator.animate_scalar(
                self.base_value,
                self.target_value,
                phase,
                progress,
                self.config.operator,
                self.lifecycle.has_reverted()
            )
        elif self.config.property == "direction":
            # Determine which interpolation to use (over or revert)
            interpolation = self.config.over_interpolation
            if phase == LifecyclePhase.REVERT:
                interpolation = self.config.revert_interpolation

            return PropertyAnimator.animate_direction(
                self.base_value,
                self.target_value,
                phase,
                progress,
                self.lifecycle.has_reverted(),
                interpolation
            )
        elif self.config.property == "pos":
            return PropertyAnimator.animate_position(
                self.base_value,
                self.target_value,
                phase,
                progress,
                self.lifecycle.has_reverted()
            )

        return self.target_value

    def get_current_value(self) -> Any:
        """Get aggregated current value from all children

        If group lifecycle is active (coordinated revert), use that.
        Otherwise aggregate all children's individual values.
        """
        # Use group lifecycle if active (coordinated revert)
        if self.group_lifecycle and not self.group_lifecycle.is_complete():
            phase, progress = self.group_lifecycle.update(0)

            # Use builder's own property type (not children, which are cleared during revert)
            property_type = self.config.property

            # Animate from target back to base during revert
            if property_type in ("speed", "accel"):
                return PropertyAnimator.animate_scalar(
                    self.group_base_value,
                    self.group_target_value,
                    phase,
                    progress,
                    "to",  # Group revert is always absolute
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

        # Aggregate own value plus all children values
        property_type = self.config.property

        if property_type in ("speed", "accel"):
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

        # Fallback
        return self._get_own_value()
