"""Universal RigBuilder - the single builder type for all operations

All fluent API calls return RigBuilder. Execution happens on __del__.
"""

import math
import time
from talon import ctrl
from typing import Optional, Callable, Any, TYPE_CHECKING
from .core import Vec2, EPSILON, mouse_move, mouse_move_relative
from .contracts import (
    BuilderConfig,
    LifecyclePhase,
    LayerType,
    validate_timing,
    validate_has_operation,
    validate_api_has_operation,
    ConfigError,
    RigAttributeError,
    find_closest_match,
    VALID_BUILDER_METHODS,
    VALID_OPERATORS,
)
from .lifecycle import Lifecycle, PropertyAnimator
from . import rate_utils
from . import mode_operations

if TYPE_CHECKING:
    from .state import RigState
    from .layer_group import LayerGroup


class BehaviorProxy:
    """Proxy that allows both .queue and .queue() syntax"""

    def __init__(self, builder: 'RigBuilder', behavior_name: str, has_args: bool = False):
        self.builder = builder
        self.behavior_name = behavior_name
        self.has_args = has_args

    def __call__(self, *args, **kwargs):
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        return method(*args, **kwargs)

    def __getattr__(self, name):
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        method()
        return getattr(self.builder, name)


class ModeProxy:
    """Proxy for mode-based property access (.offset, .override, .scale)"""

    def __init__(self, builder: 'RigBuilder', mode: str):
        self.builder = builder
        self.mode = mode

    def _set_implicit_layer(self, property_name: str) -> None:
        """Convert from base layer to auto-named modifier if no explicit layer name was given"""
        if not self.builder.config.is_user_named:
            implicit_name = f"{property_name}.{self.mode}"
            self.builder.config.layer_name = implicit_name
            self.builder.config.layer_type = LayerType.AUTO_NAMED_MODIFIER

    @property
    def pos(self) -> 'PropertyBuilder':
        self.builder.config.mode = self.mode
        self._set_implicit_layer("pos")
        return PropertyBuilder(self.builder, "pos")

    @property
    def speed(self) -> 'PropertyBuilder':
        self.builder.config.mode = self.mode
        self._set_implicit_layer("speed")
        return PropertyBuilder(self.builder, "speed")

    @property
    def direction(self) -> 'PropertyBuilder':
        self.builder.config.mode = self.mode
        self._set_implicit_layer("direction")
        return PropertyBuilder(self.builder, "direction")

    @property
    def vector(self) -> 'PropertyBuilder':
        self.builder.config.mode = self.mode
        self._set_implicit_layer("vector")
        return PropertyBuilder(self.builder, "vector")


class RigBuilder:
    """Universal builder for all mouse rig operations

    This is the ONLY builder type. All methods return self for chaining.
    Execution happens when the Python object is garbage collected (__del__).
    """

    def __init__(self, rig_state: 'RigState', layer: Optional[str] = None, order: Optional[int] = None):
        self.rig_state = rig_state
        self.config = BuilderConfig()
        self._is_valid = True
        self._executed = False
        self._lifecycle_stage = None

        if layer is None:
            self.config.layer_name = "__base_pending__"
            self.config.layer_type = LayerType.BASE
            self.config.is_user_named = False
        else:
            if not layer or not layer.strip():
                self._mark_invalid()
                raise ValueError("Empty layer name not allowed. Layer names must be non-empty strings.")
            # User-provided layer name - type will be set when mode is determined
            self.config.layer_name = layer
            self.config.layer_type = None  # Set later when mode is known
            self.config.is_user_named = True

        if order is not None:
            self.config.order = order

    def _mark_invalid(self):
        """Mark this builder as invalid so it won't execute on __del__"""
        self._is_valid = False

    @property
    def is_base_layer(self) -> bool:
        """Check if this is a base layer builder (transient, auto-bakes)"""
        return self.config.is_base_layer()

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
        if self.config.operator is not None and any(name in ops for ops in VALID_OPERATORS.values()):
            self._mark_invalid()
            raise ConfigError(
                f"Cannot call .{name}() after .{self.config.operator}() - duplicate operators not allowed.\n\n"
                f"Each command can only have one operator.\n\n"
                f"Either use one operator or use separate commands."
            )

        valid_properties = ['pos', 'speed', 'direction', 'vector']
        all_valid = valid_properties + VALID_BUILDER_METHODS

        suggestion = find_closest_match(name, all_valid)

        msg = f"RigBuilder has no attribute '{name}'"
        if suggestion:
            msg += f"\n\nDid you mean: '{suggestion}'?"
        else:
            msg += f"\n\nAvailable properties: {', '.join(valid_properties)}"
            msg += f"\nAvailable methods: {', '.join(VALID_BUILDER_METHODS)}"

        self._mark_invalid()
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
        all_kwargs = {'easing': easing, 'interpolation': interpolation, **kwargs}
        self.config.validate_method_kwargs('over', self._mark_invalid, **all_kwargs)

        validate_has_operation(self.config, 'over', self._mark_invalid)

        if rate is not None:
            self.config.over_rate = validate_timing(rate, 'rate', method='over', mark_invalid=self._mark_invalid)
            self.config.over_easing = easing
        else:
            self.config.over_ms = validate_timing(ms, 'ms', method='over', mark_invalid=self._mark_invalid) if ms is not None else 0
            self.config.over_easing = easing

        self.config.over_interpolation = interpolation

        self.config.is_synchronous = False

        self._lifecycle_stage = LifecyclePhase.OVER
        return self

    def hold(self, ms: float) -> 'RigBuilder':
        validate_has_operation(self.config, 'hold', self._mark_invalid)

        self.config.hold_ms = validate_timing(ms, 'ms', method='hold', mark_invalid=self._mark_invalid)
        if self.config.revert_ms is None:
            self.config.revert_ms = 0
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
        all_kwargs = {'easing': easing, 'interpolation': interpolation, **kwargs}
        self.config.validate_method_kwargs('revert', self._mark_invalid, **all_kwargs)

        if rate is not None:
            self.config.revert_rate = validate_timing(rate, 'rate', method='revert', mark_invalid=self._mark_invalid)
            self.config.revert_easing = easing
        else:
            self.config.revert_ms = validate_timing(ms, 'ms', method='revert', mark_invalid=self._mark_invalid) if ms is not None else 0
            self.config.revert_easing = easing

        self.config.revert_interpolation = interpolation

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

    def _set_stack(self, max: Optional[int] = None) -> 'RigBuilder':
        self.config.behavior = "stack"
        self.config.behavior_args = (max,) if max is not None else ()
        return self

    @property
    def replace(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'replace')

    def _set_replace(self) -> 'RigBuilder':
        self.config.behavior = "replace"
        return self

    @property
    def queue(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'queue', has_args=True)

    def _set_queue(self, max: Optional[int] = None) -> 'RigBuilder':
        self.config.behavior = "queue"
        self.config.behavior_args = (max,) if max is not None else ()
        return self

    @property
    def throttle(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'throttle', has_args=True)

    def _set_throttle(self, ms: Optional[float] = None) -> 'RigBuilder':
        """Internal: Set throttle behavior

        If ms is None, ignores while any builder active on layer (throttle with no args)
        If ms is provided, ignores if builder was active within last X ms (throttle with time limit)
        """
        self.config.behavior = "throttle"
        if ms is not None:
            self.config.behavior_args = (ms,)
        return self

    @property
    def debounce(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'debounce', has_args=True)

    def _set_debounce(self, ms: float) -> 'RigBuilder':
        """Internal: Set debounce behavior

        Delays execution by ms. If called again during delay, cancels previous and starts new delay.
        """
        self.config.behavior = "debounce"
        self.config.behavior_args = (ms,)
        return self

    # ========================================================================
    # BAKE CONTROL
    # ========================================================================

    def bake(self, value: bool = True) -> 'RigBuilder':
        self.config.bake_value = value
        return self

    # ========================================================================
    # API OVERRIDE
    # ========================================================================

    def api(self, api: str) -> 'RigBuilder':
        """Override mouse API for this operation

        Can be chained anywhere in the builder chain. The API will be used for
        whatever movement type this builder performs (absolute or relative).

        Examples:
            rig.pos.by(100, 0).api("talon")
            rig.pos.to(500, 300).api("talon")
            rig.layer("test").speed.to(50).api("windows_send_input")
            rig.speed.to(50).api("talon").over(1000)

        Args:
            api: Mouse API to use ('talon', 'platform', 'windows_send_input', etc.)

        Returns:
            self for chaining
        """
        # Validate API name
        from .mouse_api import MOUSE_APIS
        if api not in MOUSE_APIS:
            available = ', '.join(f"'{k}'" for k in MOUSE_APIS.keys())
            self._mark_invalid()
            raise ConfigError(
                f"Invalid API: '{api}'\n\n"
                f"Available APIs: {available}"
            )

        # Set API override
        self.config.api_override = api
        return self

    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================

    def __repr__(self) -> str:
        """Provide informative representation of the builder"""
        if not self.is_base_layer:
            return f"RigBuilder(layer='{self.config.layer_name}')"
        return f"RigBuilder()"

    def __str__(self) -> str:
        """Provide user-friendly string representation"""
        msg = "<RigBuilder - use for chaining operations"
        if not self.is_base_layer:
            msg += f" on layer '{self.config.layer_name}'"
        msg += ">\n\n"
        msg += "Available operations:\n"
        msg += "  .speed.to(value) / .speed.add(value)\n"
        msg += "  .direction.to(x, y) / .direction.by(degrees)\n"
        msg += "  .vector.to(x, y)\n"
        msg += "  .pos.to(x, y) / .pos.by(x, y)\n"
        msg += "  .over(ms) / .hold(ms) / .revert(ms)\n\n"
        msg += "To read current state: use rig.state"
        return msg

    # ========================================================================
    # EXECUTION (on __del__)
    # ========================================================================

    def __del__(self):
        if self._is_valid and not self._executed:
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

            validate_api_has_operation(self.config, self._mark_invalid)
            return

        # self._detect_and_apply_special_cases()

        self.config.validate_mode(self._mark_invalid)

        self._calculate_rate_durations()

        # Queue behavior is now handled by RigState.add_builder() and LayerGroup
        # Just create the ActiveBuilder and add it - the queue logic is in state.py
        active = ActiveBuilder(self.config, self.rig_state, self.is_base_layer)
        self.rig_state.add_builder(active)

    def _calculate_rate_durations(self):
        """Calculate durations from rate parameters"""
        if self.config.property is None or self.config.operator is None:
            return

        current_value = self._get_base_value()
        target_value = self._calculate_target_value(current_value)

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

        if self.rig_builder.config.property is not None and self.rig_builder.config.property != property_name:
            self.rig_builder._mark_invalid()
            raise ConfigError(
                f"Cannot combine multiple properties in one command.\n\n"
                f"Attempting to set both '{self.rig_builder.config.property}' and '{property_name}'.\n\n"
                f"Use separate commands instead:\n\n"
                f"  rig.{self.rig_builder.config.property}(...)\n"
                f"  rig.{property_name}(...)"
            )

        self.rig_builder.config.property = property_name

        # Set base layer name if this is a base operation (layer is still pending)
        if self.rig_builder.config.layer_name == "__base_pending__":
            self.rig_builder.config.layer_name = f"base.{property_name}"
            self.rig_builder.config.layer_type = LayerType.BASE

    def _set_implicit_layer_if_needed(self, mode: str) -> None:
        """Convert from base layer to auto-named modifier if mode is added without explicit layer name"""
        if not self.rig_builder.config.is_user_named:
            implicit_name = f"{self.property_name}.{mode}"
            self.rig_builder.config.layer_name = implicit_name
            self.rig_builder.config.layer_type = LayerType.AUTO_NAMED_MODIFIER
        else:
            # User provided layer name, now we know it's a modifier
            self.rig_builder.config.layer_type = LayerType.USER_NAMED_MODIFIER

    @property
    def offset(self) -> 'PropertyBuilder':
        self._check_duplicate_mode("offset")
        self.rig_builder.config.mode = "offset"
        self._set_implicit_layer_if_needed("offset")
        return self

    @property
    def override(self) -> 'PropertyBuilder':
        self._check_duplicate_mode("override")
        self.rig_builder.config.mode = "override"
        self._set_implicit_layer_if_needed("override")
        return self

    @property
    def scale(self) -> 'PropertyBuilder':
        self._check_duplicate_mode("scale")
        self.rig_builder.config.mode = "scale"
        self._set_implicit_layer_if_needed("scale")
        return self

    @property
    def absolute(self) -> 'PropertyBuilder':
        """Explicitly use absolute positioning (screen coordinates) for this operation."""
        self.rig_builder.config.movement_type = "absolute"
        self.rig_builder.config._movement_type_explicit = True
        return self

    @property
    def relative(self) -> 'PropertyBuilder':
        """Explicitly use relative positioning (deltas) for this operation."""
        self.rig_builder.config.movement_type = "relative"
        self.rig_builder.config._movement_type_explicit = True
        return self

    def api(self, api: str) -> 'PropertyBuilder':
        """Override mouse API for this property operation

        Allows .api() to be called after a property name, preserving the property context.

        Examples:
            rig.pos.api("talon").offset.by(100, 0)
            rig.layer("test").speed.api("talon").offset.to(50)

        Args:
            api: Mouse API to use ('talon', 'platform', etc.)

        Returns:
            self for continued chaining
        """
        # Delegate to RigBuilder's api method, but return PropertyBuilder to maintain chain
        self.rig_builder.api(api)
        return self

    def _check_duplicate_mode(self, new_mode: str) -> None:
        if self.rig_builder.config.mode is not None:
            self.rig_builder._mark_invalid()
            existing_mode = self.rig_builder.config.mode
            raise ConfigError(
                f"Cannot call .{new_mode} after .{existing_mode} - only one mode allowed.\n\n"
                f"Each operation can only have one mode (offset/override/scale).\n\n"
                f"Current chain: {self.property_name}.{existing_mode}.{new_mode}\n\n"
                f"Use one mode:\n"
                f"  rig.{self.property_name}.{new_mode}.to(...)\n\n"
                f"Modes:\n"
                f"  .offset   - Add to base value\n"
                f"  .override - Replace base value\n"
                f"  .scale    - Multiply base value"
            )

    def _check_duplicate_operator(self, new_operator: str) -> None:
        """Check if an operator is already set and raise error if so

        Args:
            new_operator: The operator being set

        Raises:
            ConfigError: If an operator is already set
        """
        if self.rig_builder.config.operator is not None:
            self.rig_builder._mark_invalid()
            existing_op = self.rig_builder.config.operator
            raise ConfigError(
                f"Cannot call .{new_operator}() after .{existing_op}() - duplicate operators not allowed.\n\n"
                f"Each command can only have one operator.\n\n"
                f"Current chain: {self.property_name}.{existing_op}(...).{new_operator}(...)\n\n"
                f"Either use one operator:\n"
                f"  rig.{self.property_name}.{new_operator}(...)\n\n"
                f"Or use separate commands:\n"
                f"  rig.{self.property_name}.{existing_op}(...)\n"
                f"  rig.{self.property_name}.{new_operator}(...)"
            )

    def to(self, *args) -> RigBuilder:
        self._check_duplicate_operator("to")
        self.rig_builder.config.operator = "to"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        self.rig_builder.config.validate_property_operator(self.rig_builder._mark_invalid)

        if self.rig_builder.config.property == "pos":
            self.rig_builder.config.is_synchronous = True
            # Set absolute for pos unless user explicitly set via .absolute/.relative
            if not self.rig_builder.config._movement_type_explicit:
                self.rig_builder.config.movement_type = "absolute"

        return self.rig_builder

    def add(self, *args) -> RigBuilder:
        self._check_duplicate_operator("add")
        self.rig_builder.config.operator = "add"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        self.rig_builder.config.validate_property_operator(self.rig_builder._mark_invalid)

        if self.rig_builder.config.property == "pos":
            self.rig_builder.config.is_synchronous = True
            # pos.by() defaults to absolute (pixels) unless explicitly set via .absolute/.relative
        self.rig_builder.config.movement_type = "relative"
        #     if not self.rig_builder.config._movement_type_explicit:
        #         self.rig_builder.config.movement_type = "absolute"
        # else:
        #     # Other properties default to relative
        #     if not self.rig_builder.config._movement_type_explicit:
        #         self.rig_builder.config.movement_type = "relative"

        return self.rig_builder

    def by(self, *args) -> RigBuilder:
        return self.add(*args)

    def sub(self, *args) -> RigBuilder:
        self._check_duplicate_operator("sub")
        self.rig_builder.config.operator = "sub"
        self.rig_builder.config.value = args[0] if len(args) == 1 else args
        self.rig_builder.config.validate_property_operator(self.rig_builder._mark_invalid)
        return self.rig_builder

    def mul(self, value: float) -> RigBuilder:
        self._check_duplicate_operator("mul")
        self.rig_builder.config.operator = "mul"
        self.rig_builder.config.value = value
        self.rig_builder.config.validate_property_operator(self.rig_builder._mark_invalid)
        return self.rig_builder

    def div(self, value: float) -> RigBuilder:
        self._check_duplicate_operator("div")
        self.rig_builder.config.operator = "div"
        self.rig_builder.config.value = value
        self.rig_builder.config.validate_property_operator(self.rig_builder._mark_invalid)
        return self.rig_builder

    def bake(self) -> RigBuilder:
        """Bake current computed value into base state

        Examples:
            rig.direction.bake()  # Bakes current direction to base
            rig.layer("boost").speed.bake()  # Bakes boost's speed to base
        """
        self.rig_builder.config.operator = "bake"
        self.rig_builder.config.value = None
        self.rig_builder.config.validate_property_operator(self.rig_builder._mark_invalid)
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

    def __call__(self, *args) -> RigBuilder:
        """Shorthand: rig.speed(5) -> rig.speed.to(5)

        Only works for anonymous builders.
        """
        return self.to(*args)

    def __getattr__(self, name: str):
        """Provide helpful errors for common mistakes"""
        if name in ('max', 'min'):
            raise ConfigError(
                f"Cannot call .{name}() before an operation.\n\n"
                f"Constraints must be applied after an operation:\n\n"
                f"  ✗ rig.{self.property_name}.{name}(value).add(10)\n"
                f"  ✓ rig.{self.property_name}.add(10).{name}(value)\n\n"
                f"Constraints are applied to the operation result."
            )
        # Fall through to default AttributeError
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def _value_error(self):
        """Provide helpful error when PropertyBuilder is used as a value"""
        raise ConfigError(
            f"Cannot use rig.{self.property_name} to read values.\n\n"
            f"rig.{self.property_name} is for setting/building operations:\n"
            f"  rig.{self.property_name}.to(value)\n"
            f"  rig.{self.property_name}.add(value)\n\n"
            f"To read current values, use rig.state:\n"
            f"  rig.state.{self.property_name}  # Current computed value\n"
            f"  rig.base.{self.property_name}   # Base (baked) value"
        )

    def __repr__(self):
        """Provide helpful error when PropertyBuilder is printed or converted to string"""
        self._value_error()

    def __str__(self):
        """Provide helpful error when PropertyBuilder is printed or converted to string"""
        self._value_error()

    def __abs__(self):
        """Provide helpful error when PropertyBuilder is used with abs()"""
        self._value_error()

    def __float__(self):
        """Provide helpful error when PropertyBuilder is converted to float"""
        self._value_error()

    def __int__(self):
        """Provide helpful error when PropertyBuilder is converted to int"""
        self._value_error()

    def __add__(self, other):
        """Provide helpful error when PropertyBuilder is used in addition"""
        self._value_error()

    def __radd__(self, other):
        """Provide helpful error when PropertyBuilder is used in addition (reversed)"""
        self._value_error()

    def __sub__(self, other):
        """Provide helpful error when PropertyBuilder is used in subtraction"""
        self._value_error()

    def __rsub__(self, other):
        """Provide helpful error when PropertyBuilder is used in subtraction (reversed)"""
        self._value_error()

    def __mul__(self, other):
        """Provide helpful error when PropertyBuilder is used in multiplication"""
        self._value_error()

    def __rmul__(self, other):
        """Provide helpful error when PropertyBuilder is used in multiplication (reversed)"""
        self._value_error()

    def __truediv__(self, other):
        """Provide helpful error when PropertyBuilder is used in division"""
        self._value_error()

    def __rtruediv__(self, other):
        """Provide helpful error when PropertyBuilder is used in division (reversed)"""
        self._value_error()

    def __floordiv__(self, other):
        """Provide helpful error when PropertyBuilder is used in floor division"""
        self._value_error()

    def __rfloordiv__(self, other):
        """Provide helpful error when PropertyBuilder is used in floor division (reversed)"""
        self._value_error()

    def __mod__(self, other):
        """Provide helpful error when PropertyBuilder is used in modulo"""
        self._value_error()

    def __rmod__(self, other):
        """Provide helpful error when PropertyBuilder is used in modulo (reversed)"""
        self._value_error()

    def __pow__(self, other):
        """Provide helpful error when PropertyBuilder is used in power"""
        self._value_error()

    def __rpow__(self, other):
        """Provide helpful error when PropertyBuilder is used in power (reversed)"""
        self._value_error()

    def __lt__(self, other):
        """Provide helpful error when PropertyBuilder is used in comparison"""
        self._value_error()

    def __le__(self, other):
        """Provide helpful error when PropertyBuilder is used in comparison"""
        self._value_error()

    def __gt__(self, other):
        """Provide helpful error when PropertyBuilder is used in comparison"""
        self._value_error()

    def __ge__(self, other):
        """Provide helpful error when PropertyBuilder is used in comparison"""
        self._value_error()

    def __eq__(self, other):
        """Provide helpful error when PropertyBuilder is used in comparison"""
        self._value_error()

    def __ne__(self, other):
        """Provide helpful error when PropertyBuilder is used in comparison"""
        self._value_error()

    def __neg__(self):
        """Provide helpful error when PropertyBuilder is negated"""
        self._value_error()

    def __pos__(self):
        """Provide helpful error when PropertyBuilder is used with unary +"""
        self._value_error()


class ActiveBuilder:
    """An active builder being executed in the state manager

    Builders are now managed by LayerGroups - they are siblings within a group,
    not parent/child relationships.
    """

    def __init__(self, config: BuilderConfig, rig_state: 'RigState', is_base_layer: bool):
        import time

        self.config = config
        self.rig_state = rig_state
        self.is_base_layer = is_base_layer
        self.layer = config.layer_name
        self.creation_time = time.perf_counter()

        # Back-reference to containing group (set by LayerGroup.add_builder)
        self.group: Optional['LayerGroup'] = None

        # For base layers, always use override mode to store absolute result values
        # Modes (offset/scale) are only meaningful for modifier layers
        if config.mode is None and is_base_layer:
            config.mode = "override"

        self.group_lifecycle: Optional[Lifecycle] = None
        self.group_base_value: Optional[Any] = None
        self.group_target_value: Optional[Any] = None

        self._marked_for_removal: bool = False

        self.lifecycle = Lifecycle(is_modifier_layer=not is_base_layer)
        self.lifecycle.over_ms = config.over_ms
        self.lifecycle.over_easing = config.over_easing
        self.lifecycle.hold_ms = config.hold_ms
        self.lifecycle.revert_ms = config.revert_ms
        self.lifecycle.revert_easing = config.revert_easing

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
                prop_state = getattr(rig_state, config.property)
                # SmartPropertyState wrapper - extract the actual value
                self.base_value = prop_state.value if hasattr(prop_state, 'value') else prop_state
        elif config.operator in ("by", "add"):
            # For relative operations
            if config.property == "pos" and config.movement_type == "relative":
                # pos.by() - always start at zero for offset mode
                # Queue accumulated state is tracked separately by the queue system
                self.base_value = Vec2(0, 0)
            elif is_base_layer:
                # For base layer operations, use computed value (includes pending builders)
                prop_state = getattr(rig_state, config.property)
                self.base_value = prop_state.value if hasattr(prop_state, 'value') else prop_state
            else:
                # For modifier layers: speed.by(), direction.by() - use base state
                self.base_value = self._get_base_value()
        else:
            # For all other operations (sub, mul, div)
            if is_base_layer:
                # For base layer operations, use computed value (includes pending builders)
                prop_state = getattr(rig_state, config.property)
                self.base_value = prop_state.value if hasattr(prop_state, 'value') else prop_state
            else:
                # For modifier layers, use base state
                self.base_value = self._get_base_value()

        self.target_value = self._calculate_target_value()

        # Revert target for offset mode with replace (set by state manager)
        # When set, this overrides the normal revert behavior to cancel accumulated value
        self.revert_target: Optional[Any] = None

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

                # Use API override if specified
                if self.config.api_override is not None:
                    from .mouse_api import get_mouse_move_functions
                    move_absolute, _ = get_mouse_move_functions(self.config.api_override, None)
                    move_absolute(int(self.rig_state._internal_pos.x), int(self.rig_state._internal_pos.y))
                else:
                    mouse_move(int(self.rig_state._internal_pos.x), int(self.rig_state._internal_pos.y))
            else:
                # Relative movement
                delta = self.target_value

                # Use API override if specified
                if self.config.api_override is not None:
                    from .mouse_api import get_mouse_move_functions
                    _, move_relative = get_mouse_move_functions(None, self.config.api_override)
                    move_relative(int(delta.x), int(delta.y))
                else:
                    mouse_move_relative(int(delta.x), int(delta.y))

        # Add other property types here as needed (speed, direction, etc.)

    def _trigger_queue_completion(self):
        """Notify group that this builder has completed"""
        if self.config.behavior == "queue" and self.group:
            # Let the group handle queue progression
            pass  # Group will handle this in on_builder_complete

    def advance(self, current_time: float) -> tuple[str, list]:
        """Advance this builder forward in time.

        Args:
            current_time: Current timestamp from perf_counter() (captured once per frame)

        Returns:
            (completed_phase, phase_transitions) where:
            - completed_phase: Phase that just completed (or None)
            - phase_transitions: List of (builder, completed_phase) for callbacks
        """
        phase_transitions = []

        if self.group_lifecycle:
            self.group_lifecycle.advance(current_time)
            if self.group_lifecycle.is_complete():
                if self.group_lifecycle.has_reverted():
                    self._marked_for_removal = True
                self.group_lifecycle = None
                return (None, [])

        # Track phase before advance
        old_phase = self.lifecycle.phase

        # Update lifecycle
        self.lifecycle.advance(current_time)

        # Track phase transition
        new_phase = self.lifecycle.phase
        if old_phase != new_phase and old_phase is not None:
            phase_transitions.append((self, old_phase))

        return (old_phase if old_phase != new_phase else None, phase_transitions)

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

        if self.config.property == "pos" and phase is None and self.lifecycle.has_reverted():
            print(f"[DEBUG _get_own_value] REVERT COMPLETE: base_value={self.base_value}, target_value={self.target_value}, has_reverted={self.lifecycle.has_reverted()}")

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
                        # If revert_target is set (from replace), use it instead of neutral
                        return self.revert_target if self.revert_target is not None else neutral
                    return self.target_value
                elif phase == LifecyclePhase.OVER:
                    return self.target_value * progress
                elif phase == LifecyclePhase.HOLD:
                    return self.target_value
                elif phase == LifecyclePhase.REVERT:
                    # If revert_target is set (from replace), animate to it instead of neutral
                    revert_to = self.revert_target if self.revert_target is not None else neutral
                    return self.target_value + (revert_to - self.target_value) * progress
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
        """Get current interpolated value for this builder

        No children - just return own value. Group handles aggregation.
        """
        # Handle group lifecycle if active
        if self.group_lifecycle and not self.group_lifecycle.is_complete():
            current_time = time.perf_counter()
            phase, progress = self.group_lifecycle.advance(current_time)

            property_type = self.config.property
            interpolation = self.config.revert_interpolation

            return PropertyAnimator.interpolate(
                property_type,
                self.group_base_value,
                self.group_target_value,
                phase,
                progress,
                self.group_lifecycle.has_reverted(),
                interpolation
            )

        # Return own value
        return self._get_own_value()
