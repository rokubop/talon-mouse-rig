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
        rate: Optional[float] = None
    ) -> 'RigBuilder':
        """Set transition duration or rate"""
        if rate is not None:
            # Rate-based, duration will be calculated later
            self.config.over_rate = rate
            self.config.over_easing = easing
        else:
            self.config.over_ms = ms if ms is not None else 0
            self.config.over_easing = easing
        
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
        rate: Optional[float] = None
    ) -> 'RigBuilder':
        """Set revert duration or rate"""
        if rate is not None:
            self.config.revert_rate = rate
            self.config.revert_easing = easing
        else:
            self.config.revert_ms = ms if ms is not None else 0
            self.config.revert_easing = easing
        
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

    def stack(self, max_count: Optional[int] = None) -> 'RigBuilder':
        """Stack behavior (unlimited or max)"""
        self.config.behavior = "stack"
        self.config.behavior_args = (max_count,) if max_count is not None else ()
        return self

    def replace(self) -> 'RigBuilder':
        """Replace behavior (cancel previous)"""
        self.config.behavior = "replace"
        return self

    def queue(self) -> 'RigBuilder':
        """Queue behavior (wait for current)"""
        self.config.behavior = "queue"
        return self

    def extend(self) -> 'RigBuilder':
        """Extend hold duration"""
        self.config.behavior = "extend"
        return self

    def throttle(self, ms: float) -> 'RigBuilder':
        """Throttle behavior (rate limit)"""
        self.config.behavior = "throttle"
        self.config.behavior_args = (ms,)
        return self

    def ignore(self) -> 'RigBuilder':
        """Ignore while active"""
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

        # Validation
        if self.config.property is None or self.config.operator is None:
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
    """An active builder being executed in the state manager"""

    def __init__(self, config: BuilderConfig, rig_state: 'RigState', is_anonymous: bool):
        self.config = config
        self.rig_state = rig_state
        self.is_anonymous = is_anonymous
        self.tag = config.tag_name

        # Create lifecycle
        self.lifecycle = Lifecycle()
        self.lifecycle.over_ms = config.over_ms
        self.lifecycle.over_easing = config.over_easing
        self.lifecycle.hold_ms = config.hold_ms
        self.lifecycle.revert_ms = config.revert_ms
        self.lifecycle.revert_easing = config.revert_easing

        # Add callbacks
        for stage, callback in config.then_callbacks:
            self.lifecycle.add_callback(stage, callback)

        # Calculate values - use computed current state for 'to' operator
        if config.operator == "to" and config.property in ("speed", "accel"):
            # For 'to' operations, we need the current computed value
            self.base_value = getattr(rig_state, config.property)
        else:
            # For other operations, use base state
            self.base_value = self._get_base_value()
        
        self.target_value = self._calculate_target_value()

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
                # Return offset from current position
                target_pos = Vec2.from_tuple(value)
                return target_pos - current
            elif operator in ("by", "add"):
                return Vec2.from_tuple(value)

        return current

    def update(self, dt: float) -> bool:
        """Update this builder.

        Returns:
            True if still active, False if complete
        """
        phase, progress = self.lifecycle.update(dt)

        if self.lifecycle.is_complete():
            return False

        return True

    def get_current_value(self) -> Any:
        """Get current animated value"""
        phase, progress = self.lifecycle.update(0)

        if self.config.property in ("speed", "accel"):
            return PropertyAnimator.animate_scalar(
                self.base_value,
                self.target_value,
                phase,
                progress,
                self.config.operator
            )
        elif self.config.property == "direction":
            return PropertyAnimator.animate_direction(
                self.base_value,
                self.target_value,
                phase,
                progress
            )
        elif self.config.property == "pos":
            return PropertyAnimator.animate_position(
                self.base_value,
                self.target_value,
                phase,
                progress
            )

        return self.target_value
