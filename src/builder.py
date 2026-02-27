"""Mouse RigBuilder - fluent API + MouseActiveBuilder subclass

The fluent API (RigBuilder, PropertyBuilder, etc.) is entirely mouse-specific.
ActiveBuilder extends BaseActiveBuilder with mouse-specific value resolution.
"""

import math
import time
from talon import ctrl
from typing import Optional, Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .state import RigState
    from .layer_group import LayerGroup

# Module-level references set by _build_classes
Vec2 = None
is_vec2 = None
BuilderConfig = None
LifecyclePhase = None
LayerType = None
validate_timing = None
validate_has_operation = None
validate_api_has_operation = None
ConfigError = None
RigAttributeError = None
find_closest_match = None
VALID_BUILDER_METHODS = None
VALID_OPERATORS = None
Lifecycle = None
PropertyAnimator = None
PropertyKind = None
ActiveBuilder = None
rate_utils = None

# Module-level imports that don't need rig-core
from .core import mouse_move, mouse_move_relative, mouse_scroll_native
from .mouse_api import MOUSE_APIS, get_mouse_move_functions


def _build_classes(core):
    global Vec2, is_vec2, BuilderConfig, LifecyclePhase, LayerType
    global validate_timing, validate_has_operation, validate_api_has_operation
    global ConfigError, RigAttributeError, find_closest_match
    global VALID_BUILDER_METHODS, VALID_OPERATORS
    global Lifecycle, PropertyAnimator, PropertyKind
    global ActiveBuilder
    global rate_utils

    Vec2 = core.Vec2
    is_vec2 = core.is_vec2
    LifecyclePhase = core.LifecyclePhase
    LayerType = core.LayerType
    validate_timing = core.validate_timing
    validate_has_operation = core.validate_has_operation
    ConfigError = core.ConfigError
    RigAttributeError = core.RigAttributeError
    find_closest_match = core.find_closest_match
    Lifecycle = core.Lifecycle
    PropertyAnimator = core.PropertyAnimator
    PropertyKind = core.PropertyKind

    from .contracts import (
        BuilderConfig as _BuilderConfig,
        validate_api_has_operation as _validate_api_has_operation,
        VALID_BUILDER_METHODS as _VALID_BUILDER_METHODS,
        VALID_OPERATORS as _VALID_OPERATORS,
    )
    BuilderConfig = _BuilderConfig
    validate_api_has_operation = _validate_api_has_operation
    VALID_BUILDER_METHODS = _VALID_BUILDER_METHODS
    VALID_OPERATORS = _VALID_OPERATORS

    from . import mode_operations
    rate_utils = core.rate_utils

    # ========================================================================
    # MouseActiveBuilder — extends BaseActiveBuilder
    # ========================================================================

    class _MouseActiveBuilder(core.BaseActiveBuilder):
        """Mouse-specific ActiveBuilder with pos/scroll handling"""

        def __init__(self, config, rig_state, is_base_layer: bool):
            # Mouse-specific init: handle pos movement_type, scroll, same-axis reversal
            # We need to set up some things before super().__init__ calls _resolve_base_value

            # Store for use in _resolve_base_value override
            self._mouse_config = config
            self._mouse_rig_state = rig_state

            # Call super which will call our abstract methods
            super().__init__(config, rig_state, is_base_layer)

            # Auto-detect scroll direction to use linear interpolation
            input_type = getattr(config, 'input_type', 'move')
            if (input_type == "scroll" and
                config.property == "direction" and
                config.operator == "to" and
                config.over_ms is not None and
                config.over_ms > 0):
                if config.over_interpolation == "lerp":
                    config.over_interpolation = 'linear'
                if config.revert_interpolation == "lerp":
                    config.revert_interpolation = 'linear'

            # Auto-detect same-axis direction reversal for smooth zero-crossing
            if (config.property == "direction" and
                config.operator == "to" and
                config.over_ms is not None and
                config.over_ms > 0):
                if self._is_same_axis_reversal(self.base_value, self.target_value):
                    config.over_interpolation = 'linear'
                    config.revert_interpolation = 'linear'

        def _resolve_base_value(self) -> Any:
            """Override to handle pos movement_type and scroll_pos"""
            config = self.config

            if config.operator == "to":
                if config.property == "pos":
                    if config.movement_type == "absolute":
                        return Vec2(*ctrl.mouse_pos())
                    else:
                        return Vec2(0, 0)
                else:
                    return self._get_current_or_base_value()
            elif config.operator in ("by", "add"):
                if config.property == "pos" and config.movement_type == "relative":
                    return Vec2(0, 0)
                elif self.is_base_layer:
                    return self._get_current_or_base_value()
                else:
                    return self._get_base_value()
            else:
                if self.is_base_layer:
                    return self._get_current_or_base_value()
                else:
                    return self._get_base_value()

        def _is_same_axis_reversal(self, base_dir, target_dir) -> bool:
            base_x_zero = abs(base_dir.x) < 0.01
            base_y_zero = abs(base_dir.y) < 0.01
            target_x_zero = abs(target_dir.x) < 0.01
            target_y_zero = abs(target_dir.y) < 0.01

            opposite_direction = base_dir.dot(target_dir) < -0.9

            return ((base_x_zero and target_x_zero) or (base_y_zero and target_y_zero)) and opposite_direction

        # ====================================================================
        # ABSTRACT METHOD IMPLEMENTATIONS (3)
        # ====================================================================

        def _get_base_value(self) -> Any:
            """Read raw base value from mouse state"""
            input_type = getattr(self.config, 'input_type', 'move')

            if input_type == "scroll":
                if self.config.property == "speed":
                    return self.rig_state._base_scroll_speed
                elif self.config.property == "direction":
                    return Vec2(self.rig_state._base_scroll_direction.x, self.rig_state._base_scroll_direction.y)
                elif self.config.property == "vector":
                    return self.rig_state._base_scroll_direction * self.rig_state._base_scroll_speed
                else:
                    return 0
            else:
                if self.config.property == "speed":
                    return self.rig_state.base.speed
                elif self.config.property == "direction":
                    return Vec2(self.rig_state.base.direction.x, self.rig_state.base.direction.y)
                elif self.config.property == "pos":
                    return Vec2(self.rig_state.base.pos.x, self.rig_state.base.pos.y)
                elif self.config.property == "vector":
                    return self.rig_state.base.direction * self.rig_state.base.speed
                return 0

        def _calculate_target_value(self) -> Any:
            """Compute target value via mode_operations"""
            operator = self.config.operator
            value = self.config.value
            current = self.base_value
            mode = self.config.mode

            if operator == "bake":
                return None

            if self.config.property == "speed":
                return mode_operations.calculate_scalar_target(operator, value, current, mode)

            elif self.config.property == "direction":
                return mode_operations.calculate_direction_target(operator, value, current, mode)

            elif self.config.property == "pos":
                return mode_operations.calculate_position_target(operator, value, current, mode)

            elif self.config.property == "vector":
                current_speed = self.rig_state.base.speed
                current_direction = self.rig_state.base.direction
                return mode_operations.calculate_vector_target(operator, value, current_speed, current_direction, mode)

            elif self.config.property == "scroll_pos":
                return Vec2.from_tuple(value) if isinstance(value, tuple) else value

            return current

        def _get_property_kind(self) -> PropertyKind:
            """Return PropertyKind for animation routing"""
            _PROPERTY_KIND_MAP = {
                "speed": PropertyKind.SCALAR,
                "pos": PropertyKind.POSITION,
                "direction": PropertyKind.DIRECTION,
                "vector": PropertyKind.VECTOR,
                "scroll_pos": PropertyKind.POSITION,
            }
            return _PROPERTY_KIND_MAP.get(self.config.property, PropertyKind.SCALAR)

        # ====================================================================
        # MOUSE-SPECIFIC: _get_own_value override for scroll_pos
        # ====================================================================

        def _get_own_value(self) -> Any:
            """Override to add scroll_pos handling"""
            if self.config.property == "scroll_pos":
                current_time = time.perf_counter()
                phase, progress = self.lifecycle.advance(current_time)

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
                    return self.target_value + (neutral - self.target_value) * progress

            return super()._get_own_value()

        def get_interpolated_value(self) -> Any:
            """Override to use PropertyAnimator.interpolate for group lifecycle"""
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

            return self._get_own_value()

        # ====================================================================
        # MOUSE-SPECIFIC: execute_synchronous
        # ====================================================================

        def execute_synchronous(self):
            """Execute this builder synchronously (instant, no animation)"""
            if self.config.property == "pos":
                if self.config.movement_type == "absolute":
                    mode = self.config.mode
                    current_value = self.target_value

                    current_mouse_pos = ctrl.mouse_pos()
                    self.rig_state._internal_pos = Vec2(current_mouse_pos[0], current_mouse_pos[1])
                    self.rig_state._base_pos = Vec2(current_mouse_pos[0], current_mouse_pos[1])

                    new_pos = mode_operations.apply_position_mode(mode, current_value, self.rig_state._internal_pos)
                    self.rig_state._internal_pos = new_pos
                    self.rig_state._base_pos = Vec2(new_pos.x, new_pos.y)

                    if self.config.api_override is not None:
                        move_absolute, _ = get_mouse_move_functions(self.config.api_override, None)
                        move_absolute(int(self.rig_state._internal_pos.x), int(self.rig_state._internal_pos.y))
                    else:
                        mouse_move(int(self.rig_state._internal_pos.x), int(self.rig_state._internal_pos.y))
                else:
                    delta = self.target_value

                    if self.config.api_override is not None:
                        _, move_relative = get_mouse_move_functions(None, self.config.api_override)
                        move_relative(int(delta.x), int(delta.y))
                    else:
                        mouse_move_relative(int(delta.x), int(delta.y))

            elif self.config.property == "scroll_pos":
                delta = self.target_value
                if abs(delta.x) > 0.01 or abs(delta.y) > 0.01:
                    mouse_scroll_native(delta.x, delta.y)

    ActiveBuilder = _MouseActiveBuilder


# ============================================================================
# FLUENT API CLASSES (entirely mouse-specific, stay as module-level)
# These use module-level globals set by _build_classes
# ============================================================================

class BehaviorProxy:
    """Proxy that allows both .queue and .queue() syntax"""

    def __init__(self, builder: 'RigBuilder', behavior_name: str, has_args: bool = False):
        self.builder = builder
        self.behavior_name = behavior_name
        self.has_args = has_args
        self._property_builder = None

    def __call__(self, *args, **kwargs):
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        method(*args, **kwargs)
        return self._property_builder if self._property_builder else self.builder

    def __getattr__(self, name):
        method = getattr(self.builder, f'_set_{self.behavior_name}')
        method()
        if self._property_builder:
            return getattr(self._property_builder, name)
        return getattr(self.builder, name)


class ModeProxy:
    """Proxy for mode-based property access (.offset, .override, .scale)"""

    def __init__(self, builder: 'RigBuilder', mode: str):
        self.builder = builder
        self.mode = mode

    def _set_implicit_layer(self, property_name: str) -> None:
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

    @property
    def scroll(self) -> 'ScrollPropertyProxy':
        return ScrollPropertyProxy(self.builder, self.mode)


class ScrollPropertyProxy:
    """Proxy for scroll input_type"""

    def __init__(self, builder: 'RigBuilder', mode: str = None):
        self.builder = builder
        self.mode = mode
        self.builder.config.input_type = "scroll"

    @property
    def speed(self) -> 'PropertyBuilder':
        if self.mode:
            self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "speed")

    @property
    def direction(self) -> 'PropertyBuilder':
        if self.mode:
            self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "direction")

    @property
    def vector(self) -> 'PropertyBuilder':
        if self.mode:
            self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "vector")

    @property
    def offset(self) -> 'ScrollPropertyProxy':
        self.mode = "offset"
        return self

    @property
    def override(self) -> 'ScrollPropertyProxy':
        self.mode = "override"
        return self

    @property
    def scale(self) -> 'ScrollPropertyProxy':
        self.mode = "scale"
        return self

    @property
    def by_lines(self) -> 'ScrollPropertyProxy':
        self.builder.config.by_lines = True
        return self

    @property
    def by_pixels(self) -> 'ScrollPropertyProxy':
        self.builder.config.by_lines = False
        return self

    @property
    def pos(self) -> 'PropertyBuilder':
        if self.mode:
            self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "pos")

    def to(self, *args) -> 'RigBuilder':
        return self.by(*args)

    def by(self, *args) -> 'RigBuilder':
        if self.mode:
            self.builder.config.mode = self.mode
        return PropertyBuilder(self.builder, "scroll_pos").by(*args)

    def bake(self):
        self.builder.rig_state.bake_scroll_all()

    def emit(self, ms: float = 1000, easing: str = "linear") -> 'RigBuilder':
        """Convert current total scroll velocity to autonomous decaying offset"""
        scroll_speed, scroll_direction = self.builder.rig_state._compute_scroll_velocity()
        current_velocity = scroll_direction * scroll_speed

        self.builder.rig_state.bake_scroll_all()
        self.builder.rig_state._base_scroll_speed = 0.0

        layer_name = f"emit.scroll.{int(time.perf_counter() * 1000000)}"
        self.builder._mark_invalid()
        return RigBuilder(self.builder.rig_state, layer=layer_name).scroll.vector.offset.to(current_velocity.x, current_velocity.y).revert(ms, easing)

    def stop(self, ms=None, easing: str = "linear"):
        ms = validate_timing(ms, 'ms', method='stop')
        self.builder.rig_state.scroll_stop(ms, easing)
        self.builder._mark_invalid()


class RigBuilder:
    """Universal builder for all mouse rig operations"""

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
            self.config.layer_name = layer
            self.config.layer_type = None
            self.config.is_user_named = True

        if order is not None:
            self.config.order = order

    def _mark_invalid(self):
        self._is_valid = False

    @property
    def is_base_layer(self) -> bool:
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
    # PROPERTY ACCESSORS
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

    @property
    def scroll(self) -> 'ScrollPropertyProxy':
        return ScrollPropertyProxy(self)

    def __getattr__(self, name: str):
        if self.config.operator is not None and any(name in ops for ops in VALID_OPERATORS.values()):
            self._mark_invalid()
            raise ConfigError(
                f"Cannot call .{name}() after .{self.config.operator}() - duplicate operators not allowed.\n\n"
                f"Each command can only have one operator.\n\n"
                f"Either use one operator or use separate commands."
            )

        valid_properties = ['pos', 'speed', 'direction', 'vector', 'scroll']
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

    def reverse(self, ms: Optional[float] = None, easing: str = "linear") -> 'RigBuilder':
        ms = validate_timing(ms, 'ms', method='reverse', mark_invalid=self._mark_invalid) if ms is not None else None

        layer_name = self.config.layer_name

        if not self.config.is_user_named:
            self._mark_invalid()
            raise ValueError(
                f"reverse() can only be used on user-named layers.\n"
                f"Use rig.layer('name') to create a named layer before reversing."
            )

        if layer_name not in self.rig_state._layer_groups:
            self._mark_invalid()
            raise ValueError(
                f"Cannot reverse layer '{layer_name}' - layer does not exist.\n"
                f"Hint: Create the layer first before reversing it."
            )

        group = self.rig_state._layer_groups[layer_name]

        if ms is not None:
            try:
                self.copy().emit(ms, easing)
                self.copy().emit(ms, easing)
            except:
                pass

        if group.property in ("direction", "vector") and group.accumulated_value is not None:
            group.accumulated_value = group.accumulated_value * -1

        for builder in group.builders:
            if builder.config.property in ("direction", "vector") and builder.target_value is not None:
                builder.target_value = builder.target_value * -1
                if builder.base_value is not None:
                    builder.base_value = builder.base_value * -1

        self._mark_invalid()
        return RigBuilder(self.rig_state, layer=layer_name)

    def copy(self, name: Optional[str] = None) -> 'RigBuilder':
        layer_name = self.config.layer_name

        if not self.config.is_user_named:
            self._mark_invalid()
            raise ValueError(
                f"copy() can only be used on user-named layers.\n"
                f"Use rig.layer('name') to create a named layer before copying."
            )

        if layer_name not in self.rig_state._layer_groups:
            self._mark_invalid()
            raise ValueError(
                f"Cannot copy layer '{layer_name}' - layer does not exist.\n"
                f"Hint: Create the layer first before copying it."
            )

        if name is None:
            copy_name = f"copy.{layer_name}.{int(time.perf_counter() * 1000000)}"
        else:
            copy_name = name

        original_group = self.rig_state._layer_groups[layer_name]
        copy_group = original_group.copy(copy_name)
        self.rig_state._layer_groups[copy_name] = copy_group

        self._mark_invalid()
        return RigBuilder(self.rig_state, layer=copy_name)

    def emit(self, ms: float = 1000, easing: str = "linear") -> 'RigBuilder':
        if not self._executed and self._is_valid and self.config.property is not None:
            self._execute()

        self.config.validate_easing(easing, context='emit', mark_invalid=self._mark_invalid)

        layer_name = self.config.layer_name

        if layer_name not in self.rig_state._layer_groups:
            self._mark_invalid()
            return self

        group = self.rig_state._layer_groups[layer_name]

        if group.property == "vector" and group.mode in ("offset", "override"):
            pass
        elif group.property == "speed" and group.mode == "offset":
            pass
        else:
            if group.property == "direction":
                raise ValueError(
                    f"emit() cannot be used on direction layers.\n"
                    f"Direction (angular) changes don't have momentum semantics.\n"
                    f"Layer: '{layer_name}' ({group.property}.{group.mode})"
                )
            elif group.property == "pos":
                raise ValueError(
                    f"emit() cannot be used on position layers.\n"
                    f"Position offsets don't have momentum semantics.\n"
                    f"Layer: '{layer_name}' ({group.property}.{group.mode})"
                )
            elif group.property == "speed" and group.mode != "offset":
                raise ValueError(
                    f"emit() can only be used on speed.offset layers.\n"
                    f"speed.override/scale don't have momentum semantics.\n"
                    f"Layer: '{layer_name}' ({group.property}.{group.mode})\n"
                    f"Hint: Use speed.offset for additive speed contributions."
                )
            elif group.property == "vector" and group.mode not in ("offset", "override"):
                raise ValueError(
                    f"emit() can only be used on vector.offset or vector.override layers.\n"
                    f"Layer: '{layer_name}' ({group.property}.{group.mode})"
                )
            else:
                raise ValueError(
                    f"emit() cannot be used on '{layer_name}' ({group.property}.{group.mode}).\n"
                    f"emit() only works for: vector.offset, vector.override, speed.offset"
                )

        if group.property == "vector":
            current_value = group.get_current_value()
            velocity = current_value if is_vec2(current_value) else Vec2(0, 0)
        elif group.property == "speed" and group.mode == "offset":
            if group.input_type == "scroll":
                current_direction = self.rig_state.scroll_direction
            else:
                current_direction = self.rig_state.direction
            speed_contrib = group.get_current_value()
            velocity = current_direction * speed_contrib
        else:
            self._mark_invalid()
            return self

        self.rig_state.remove_layer(layer_name, bake=False)

        emit_layer = f"emit.{layer_name}.{int(time.perf_counter() * 1000000)}"
        self._mark_invalid()

        if group.input_type == "scroll":
            builder = RigBuilder(self.rig_state, layer=emit_layer).scroll.vector.offset.to(velocity.x, velocity.y).revert(ms, easing)
        else:
            builder = RigBuilder(self.rig_state, layer=emit_layer).vector.offset.to(velocity.x, velocity.y).revert(ms, easing)

        if emit_layer in self.rig_state._layer_groups:
            self.rig_state._layer_groups[emit_layer].is_emit_layer = True

        return builder

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
        self.config.behavior = "throttle"
        if ms is not None:
            self.config.behavior_args = (ms,)
        return self

    @property
    def debounce(self) -> BehaviorProxy:
        return BehaviorProxy(self, 'debounce', has_args=True)

    def _set_debounce(self, ms: float) -> 'RigBuilder':
        self.config.behavior = "debounce"
        self.config.behavior_args = (ms,)
        return self

    # ========================================================================
    # BAKE CONTROL
    # ========================================================================

    def max(self, value: float) -> 'RigBuilder':
        self.config.max_value = value
        return self

    def min(self, value: float) -> 'RigBuilder':
        self.config.min_value = value
        return self

    def bake(self, value: bool = True) -> 'RigBuilder':
        self.config.bake_value = value
        return self

    # ========================================================================
    # API OVERRIDE
    # ========================================================================

    def api(self, api: str) -> 'RigBuilder':
        if api not in MOUSE_APIS:
            available = ', '.join(f"'{k}'" for k in MOUSE_APIS.keys())
            self._mark_invalid()
            raise ConfigError(
                f"Invalid API: '{api}'\n\n"
                f"Available APIs: {available}"
            )

        self.config.api_override = api
        return self

    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================

    def __repr__(self) -> str:
        if not self.is_base_layer:
            return f"RigBuilder(layer='{self.config.layer_name}')"
        return f"RigBuilder()"

    def __str__(self) -> str:
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

    def run(self) -> 'RigBuilder':
        if self._is_valid and not self._executed:
            self._execute()
        return self

    def __del__(self):
        if self._is_valid and not self._executed:
            self._execute()

    def _execute(self):
        self._executed = True

        if self.config.operator is None:
            if self.config.revert_ms is not None:
                self.rig_state.trigger_revert(self.config.layer_name, self.config.revert_ms, self.config.revert_easing)
                return

            validate_api_has_operation(self.config, self._mark_invalid)
            return

        self.config.validate_mode(self._mark_invalid)
        self._calculate_rate_durations()

        active = ActiveBuilder(self.config, self.rig_state, self.is_base_layer)
        self.rig_state.add_builder(active)

    def _calculate_rate_durations(self):
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
                current_vec = self.rig_state.base.direction * self.rig_state.base.speed
                target_vec = Vec2.from_tuple(self.config.value) if self.config.operator == "to" else current_vec + Vec2.from_tuple(self.config.value)
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
                current_vec = self.rig_state.base.direction * self.rig_state.base.speed
                target_vec = Vec2.from_tuple(self.config.value) if self.config.operator == "to" else current_vec + Vec2.from_tuple(self.config.value)
                self.config.revert_ms = rate_utils.calculate_vector_duration(
                    target_vec, current_vec, self.config.revert_rate, self.config.revert_rate
                )

    def _get_base_value(self) -> Any:
        input_type = getattr(self.config, 'input_type', 'move')

        if input_type == "scroll":
            if self.config.property == "speed":
                result = self.rig_state._base_scroll_speed
            elif self.config.property == "direction":
                result = Vec2(self.rig_state._base_scroll_direction.x, self.rig_state._base_scroll_direction.y)
            elif self.config.property == "pos":
                result = self.rig_state._base_scroll_direction * self.rig_state._base_scroll_speed
            elif self.config.property == "vector":
                result = self.rig_state._base_scroll_direction * self.rig_state._base_scroll_speed
            else:
                result = 0
        else:
            if self.config.property == "speed":
                result = self.rig_state.base.speed
            elif self.config.property == "direction":
                result = Vec2(self.rig_state.base.direction.x, self.rig_state.base.direction.y)
            elif self.config.property == "pos":
                result = Vec2(self.rig_state.base.pos.x, self.rig_state.base.pos.y)
            elif self.config.property == "vector":
                result = self.rig_state.base.direction * self.rig_state.base.speed
            else:
                result = 0
        return result

    def _calculate_target_value(self, current: Any = None) -> Any:
        from . import mode_operations

        if current is None:
            current = self.base_value

        operator = self.config.operator
        value = self.config.value

        if self.config.property == "speed":
            if operator == "to":
                return value
            elif operator in ("by", "add"):
                return current + value
            elif operator == "mul":
                return current * value

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

        if self.rig_builder.config.layer_name == "__base_pending__":
            input_type = self.rig_builder.config.input_type
            if input_type == "move":
                self.rig_builder.config.layer_name = f"base.{property_name}"
            else:
                self.rig_builder.config.layer_name = f"{input_type}:base.{property_name}"
            self.rig_builder.config.layer_type = LayerType.BASE

    def _set_implicit_layer_if_needed(self, mode: str) -> None:
        if not self.rig_builder.config.is_user_named:
            input_type = self.rig_builder.config.input_type
            if input_type == "move":
                implicit_name = f"{self.property_name}.{mode}"
            else:
                implicit_name = f"{input_type}:{self.property_name}.{mode}"
            self.rig_builder.config.layer_name = implicit_name
            self.rig_builder.config.layer_type = LayerType.AUTO_NAMED_MODIFIER
        else:
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
        self.rig_builder.config.movement_type = "absolute"
        self.rig_builder.config._movement_type_explicit = True
        return self

    @property
    def relative(self) -> 'PropertyBuilder':
        self.rig_builder.config.movement_type = "relative"
        self.rig_builder.config._movement_type_explicit = True
        return self

    @property
    def by_lines(self) -> 'PropertyBuilder':
        self.rig_builder.config.by_lines = True
        return self

    @property
    def by_pixels(self) -> 'PropertyBuilder':
        self.rig_builder.config.by_lines = False
        return self

    def api(self, api: str) -> 'PropertyBuilder':
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
            self.rig_builder.config.movement_type = "relative"
        elif self.rig_builder.config.property == "scroll_pos":
            self.rig_builder.config.is_synchronous = True
            self.rig_builder.config.movement_type = "relative"

        return self.rig_builder

    def by(self, *args) -> RigBuilder:
        return self.add(*args)

    def mul(self, value: float) -> RigBuilder:
        self._check_duplicate_operator("mul")
        self.rig_builder.config.operator = "mul"
        self.rig_builder.config.value = value
        self.rig_builder.config.validate_property_operator(self.rig_builder._mark_invalid)
        return self.rig_builder

    def bake(self) -> RigBuilder:
        self.rig_builder.config.operator = "bake"
        self.rig_builder.config.value = None
        self.rig_builder.config.validate_property_operator(self.rig_builder._mark_invalid)
        return self.rig_builder

    def revert(self, ms: Optional[float] = None, easing: str = "linear", **kwargs) -> RigBuilder:
        return self.rig_builder.revert(ms, easing, **kwargs)

    def __call__(self, *args) -> RigBuilder:
        return self.to(*args)

    def __getattr__(self, name: str):
        if name in ('queue', 'stack', 'replace', 'throttle', 'debounce'):
            result = getattr(self.rig_builder, name)
            if isinstance(result, BehaviorProxy):
                result._property_builder = self
            return result

        if name in ('max', 'min'):
            raise ConfigError(
                f"Cannot call .{name}() before an operation.\n\n"
                f"Constraints must be applied after an operation:\n\n"
                f"  ✗ rig.{self.property_name}.{name}(value).add(10)\n"
                f"  ✓ rig.{self.property_name}.add(10).{name}(value)\n\n"
                f"Constraints are applied to the operation result."
            )
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def _value_error(self):
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
        self._value_error()

    def __str__(self):
        self._value_error()

    def __abs__(self):
        self._value_error()

    def __float__(self):
        self._value_error()

    def __int__(self):
        self._value_error()

    def __add__(self, other):
        self._value_error()

    def __radd__(self, other):
        self._value_error()

    def __sub__(self, other):
        self._value_error()

    def __rsub__(self, other):
        self._value_error()

    def __mul__(self, other):
        self._value_error()

    def __rmul__(self, other):
        self._value_error()

    def __truediv__(self, other):
        self._value_error()

    def __rtruediv__(self, other):
        self._value_error()

    def __floordiv__(self, other):
        self._value_error()

    def __rfloordiv__(self, other):
        self._value_error()

    def __mod__(self, other):
        self._value_error()

    def __rmod__(self, other):
        self._value_error()

    def __pow__(self, other):
        self._value_error()

    def __rpow__(self, other):
        self._value_error()

    def __lt__(self, other):
        self._value_error()

    def __le__(self, other):
        self._value_error()

    def __gt__(self, other):
        self._value_error()

    def __ge__(self, other):
        self._value_error()

    def __eq__(self, other):
        self._value_error()

    def __ne__(self, other):
        self._value_error()

    def __neg__(self):
        self._value_error()

    def __pos__(self):
        self._value_error()
