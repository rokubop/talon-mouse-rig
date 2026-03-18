"""Mouse RigState - extends BaseRigState with mouse-specific behavior

Mouse adds: absolute/relative positioning, velocity computation, scroll support,
subpixel adjustment, manual movement detection, primed button, emit layers.

All shared behavior (throttle, debounce, queue, stack, replace, builder lifecycle)
is inherited from BaseRigState in rig-core.
"""

import time
import math
from typing import Optional, TYPE_CHECKING, Union, Any
from talon import cron, ctrl, settings
from .core import SubpixelAdjuster, mouse_move, mouse_move_relative, mouse_scroll_native, mouse_scroll_end, SCROLL_EMIT_THRESHOLD
from .mouse_api import get_mouse_move_functions

if TYPE_CHECKING:
    from .builder import ActiveBuilder

# Set by _build_classes
RigState = None


def _build_classes(core):
    global RigState

    Vec2 = core.Vec2
    is_vec2 = core.is_vec2
    EPSILON = core.EPSILON
    LifecyclePhase = core.LifecyclePhase

    from .layer_group import LayerGroup
    from .contracts import BuilderConfig, ConfigError, validate_timing, VALID_LAYER_STATE_ATTRS
    from . import mode_operations

    class _MouseRigState(core.BaseRigState):
        """Mouse-specific state manager extending BaseRigState"""

        def __init__(self):
            super().__init__()

            # Mouse-specific base state
            self._absolute_base_pos: Optional[Vec2] = None
            self._base_speed: float = 0.0
            self._base_direction: Vec2 = Vec2(1, 0)
            self._base_scroll_speed: float = 0.0
            self._base_scroll_direction: Vec2 = Vec2(0, 1)

            # Mouse-specific tracking
            self._subpixel_adjuster = SubpixelAdjuster()
            self._absolute_current_pos: Optional[Vec2] = None

            # Mouse-specific stop callbacks
            self._scroll_stop_callbacks: list = []
            self._move_stop_callbacks: list = []

            # Primed button
            self._primed_button: Optional[int] = None

        # ====================================================================
        # CONFIG FACTORY OVERRIDE
        # ====================================================================

        def _create_config(self) -> BuilderConfig:
            """Return mouse-specific BuilderConfig"""
            return BuilderConfig()

        # ====================================================================
        # CRON OVERRIDES (mouse uses settings for frame interval)
        # ====================================================================

        def _get_frame_interval_str(self) -> str:
            frame_interval = settings.get("user.mouse_rig_frame_interval", 16)
            return f"{frame_interval}ms"

        # ====================================================================
        # __repr__ / __str__
        # ====================================================================

        def __repr__(self) -> str:
            pos = self.pos
            speed = self.speed
            direction = self.direction
            vector = self.vector
            scroll = self.scroll
            layers = self.layers
            try:
                cardinal = self.direction_cardinal
            except Exception:
                cardinal = None

            try:
                scroll_cardinal = scroll.direction_cardinal
            except Exception:
                scroll_cardinal = None

            lines = [
                "RigState:",
                f"  pos = ({pos.x:.1f}, {pos.y:.1f})",
                f"  pos.current = ({pos.current.x:.1f}, {pos.current.y:.1f}), pos.target = {pos.target}",
                f"  pos.x = {pos.x:.1f}, pos.y = {pos.y:.1f}",
                f"  speed = {speed.current:.1f}",
                f"  speed.current = {speed.current:.1f}, speed.target = {speed.target}",
                f"  direction = ({direction.x:.2f}, {direction.y:.2f})",
                f"  direction.current = ({direction.current.x:.2f}, {direction.current.y:.2f}), direction.target = {direction.target}",
            ]

            if cardinal:
                lines.extend([
                    f"  direction_cardinal = {cardinal.current or 'None'}",
                    f"  direction_cardinal.current = {cardinal.current or 'None'}, direction_cardinal.target = {cardinal.target or 'None'}",
                ])
            else:
                lines.extend([
                    f"  direction_cardinal = None",
                    f"  direction_cardinal.current = None, direction_cardinal.target = None",
                ])

            lines.extend([
                f"  vector = ({vector.x:.2f}, {vector.y:.2f})",
                f"  vector.current = ({vector.current.x:.2f}, {vector.current.y:.2f}), vector.target = {vector.target}",
                f"  scroll = ({scroll.x:.2f}, {scroll.y:.2f})",
                f"  scroll.current = ({scroll.current.x:.2f}, {scroll.current.y:.2f}), scroll.target = {scroll.target}",
                f"  scroll.x = {scroll.x:.2f}, scroll.y = {scroll.y:.2f}",
                f"  scroll.speed = {scroll.speed.current:.2f}",
                f"  scroll.speed.current = {scroll.speed.current:.2f}, scroll.speed.target = {scroll.speed.target}",
                f"  scroll.direction = ({scroll.direction.x:.2f}, {scroll.direction.y:.2f})",
                f"  scroll.direction.current = ({scroll.direction.current.x:.2f}, {scroll.direction.current.y:.2f}), scroll.direction.target = {scroll.direction.target}",
            ])

            if scroll_cardinal:
                lines.extend([
                    f"  scroll.direction_cardinal = {scroll_cardinal.current or 'None'}",
                    f"  scroll.direction_cardinal.current = {scroll_cardinal.current or 'None'}, scroll.direction_cardinal.target = {scroll_cardinal.target or 'None'}",
                ])
            else:
                lines.extend([
                    f"  scroll.direction_cardinal = None",
                    f"  scroll.direction_cardinal.current = None, scroll.direction_cardinal.target = None",
                ])

            lines.extend([
                f"  scroll.vector = ({scroll.vector.x:.2f}, {scroll.vector.y:.2f})",
                f"  scroll.vector.current = ({scroll.vector.current.x:.2f}, {scroll.vector.current.y:.2f}), scroll.vector.target = {scroll.vector.target}",
                *[f'  layers["{name}"] = <LayerState>' for name in layers],
                f"  base = <BaseState>",
                f"  frame_loop_active = {self._frame_loop_job is not None}",
            ])
            return "\n".join(lines)

        def __str__(self) -> str:
            return self.__repr__()

        # ====================================================================
        # MOUSE-SPECIFIC HELPERS
        # ====================================================================

        def time_alive(self, layer: str) -> Optional[float]:
            """Get time in seconds since builder was created. Returns None if layer doesn't exist."""
            if layer in self._layer_groups:
                group = self._layer_groups[layer]
                if group.builders:
                    return group.builders[0].time_alive
            return None

        def _recalculate_rate_duration(self, builder: 'ActiveBuilder'):
            """Recalculate rate-based duration after base_value changed"""
            rate_utils = core.rate_utils

            if builder.config.over_rate is None:
                return

            if builder.config.property == "speed":
                builder.config.over_ms = rate_utils.calculate_speed_duration(
                    builder.base_value, builder.target_value, builder.config.over_rate
                )
            elif builder.config.property == "direction":
                if builder.config.operator == "to":
                    target_dir = Vec2.from_tuple(builder.config.value).normalized()
                    builder.config.over_ms = rate_utils.calculate_direction_duration(
                        builder.base_value, target_dir, builder.config.over_rate
                    )
                elif builder.config.operator in ("by", "add"):
                    angle_delta = builder.config.value[0] if isinstance(builder.config.value, tuple) else builder.config.value
                    builder.config.over_ms = rate_utils.calculate_direction_by_duration(
                        angle_delta, builder.config.over_rate
                    )
            elif builder.config.property == "pos":
                if builder.config.operator == "to":
                    target_pos = Vec2.from_tuple(builder.config.value)
                    builder.config.over_ms = rate_utils.calculate_position_duration(
                        builder.base_value, target_pos, builder.config.over_rate
                    )
                elif builder.config.operator in ("by", "add"):
                    offset = Vec2.from_tuple(builder.config.value)
                    builder.config.over_ms = rate_utils.calculate_position_by_duration(
                        offset, builder.config.over_rate
                    )
            elif builder.config.property == "vector":
                target_vec = Vec2.from_tuple(builder.config.value) if builder.config.operator == "to" else builder.base_value + Vec2.from_tuple(builder.config.value)
                builder.config.over_ms = rate_utils.calculate_vector_duration(
                    builder.base_value, target_vec, builder.config.over_rate, builder.config.over_rate
                )

        # ====================================================================
        # OVERRIDES: add_builder (primed button), _finalize_builder_completion,
        #            _apply_replace_behavior, _should_frame_loop_be_active,
        #            _ensure_frame_loop_running, _stop_frame_loop,
        #            _check_and_update_rate_cache
        # ====================================================================

        def _check_and_update_rate_cache(self, builder, layer: str) -> bool:
            """Override to add _recalculate_rate_duration call"""
            rate_cache_key = self._get_rate_cache_key(layer, builder.config)
            if rate_cache_key is None:
                return False

            if rate_cache_key in self._rate_builder_cache:
                cached_builder, cached_target = self._rate_builder_cache[rate_cache_key]
                targets_match = self._targets_match(builder.target_value, cached_target)

                if targets_match and layer in self._layer_groups:
                    return True
                else:
                    if layer in self._layer_groups:
                        group = self._layer_groups[layer]
                        old_current_value = group.get_current_value()

                        if is_vec2(old_current_value):
                            builder.base_value = Vec2(old_current_value.x, old_current_value.y)
                        else:
                            builder.base_value = old_current_value
                        builder.target_value = builder._calculate_target_value()

                        # Mouse-specific: recalculate rate duration
                        self._recalculate_rate_duration(builder)

            self._rate_builder_cache[rate_cache_key] = (builder, builder.target_value)
            return False

        def add_builder(self, builder: 'ActiveBuilder'):
            """Override to add primed button logic"""
            layer = builder.config.layer_name

            if builder.config.operator == "bake":
                self._bake_property(builder.config.property, layer if not builder.config.is_base_layer() else None, getattr(builder.config, 'input_type', 'move'))
                return

            if builder.config.behavior == "debounce":
                self._apply_debounce_behavior(builder, layer)
                return

            should_skip_cached = self._check_and_update_rate_cache(builder, layer)
            if should_skip_cached:
                return

            group = self._get_or_create_group(builder)

            if builder.config.max_value is not None:
                group.max_value = builder.config.max_value
            if builder.config.min_value is not None:
                group.min_value = builder.config.min_value

            behavior = builder.config.get_effective_behavior()

            if behavior == "throttle":
                is_throttled = self._apply_throttle_behavior(builder, layer)
                if is_throttled:
                    return

            if behavior == "replace":
                self._apply_replace_behavior(builder, group)
            elif behavior == "stack":
                is_at_stack_limit = self._apply_stack_behavior(builder, group)
                if is_at_stack_limit:
                    return
            elif behavior == "queue":
                was_enqueued = self._apply_queue_behavior(builder, group)
                if was_enqueued:
                    return

            # Mouse-specific: primed button
            if self._primed_button is not None:
                btn = self._primed_button
                self._primed_button = None
                ctrl.mouse_click(button=btn, down=True)
                self.add_stop_callback(lambda: ctrl.mouse_click(button=btn, up=True))

            group.add_builder(builder)

            if not builder.lifecycle.is_complete():
                self._ensure_frame_loop_running()
            else:
                self._finalize_builder_completion(builder, group)

        def _finalize_builder_completion(self, builder, group):
            """Override for synchronous execution and velocity property frame loop"""
            layer = builder.config.layer_name

            if builder.config.is_synchronous:
                builder.execute_synchronous()
                bake_result = group.on_builder_complete(builder)
                if bake_result == "bake_to_base":
                    self._bake_group_to_base(group)

                group.remove_builder(builder)

                if group.is_base and not group.should_persist():
                    velocity_properties = {"speed", "direction", "vector"}
                    if builder.config.property in velocity_properties:
                        self._ensure_frame_loop_running()

                    if layer in self._layer_groups:
                        del self._layer_groups[layer]
            else:
                bake_result = group.on_builder_complete(builder)
                if bake_result == "bake_to_base":
                    self._bake_group_to_base(group)

                group.remove_builder(builder)

                if builder.config.property in {"speed", "direction", "vector"}:
                    self._ensure_frame_loop_running()

                if not group.should_persist():
                    if layer in self._layer_groups:
                        del self._layer_groups[layer]
                    if layer in self._layer_orders:
                        del self._layer_orders[layer]

        def _apply_replace_behavior(self, builder, group):
            """Override for pos.offset committed_value architecture"""
            current_value = group.get_current_value()
            group.clear_builders()

            # POS.OFFSET: Use committed_value architecture
            if builder.config.property == "pos" and builder.config.mode == "offset":
                if is_vec2(current_value):
                    if group.committed_value is None:
                        group.committed_value = Vec2(0, 0)

                    group.committed_value = Vec2(
                        group.committed_value.x + current_value.x,
                        group.committed_value.y + current_value.y
                    )
                    group.accumulated_value = Vec2(0, 0)

                if isinstance(builder.config.value, tuple):
                    group.replace_target = Vec2.from_tuple(builder.config.value)
                else:
                    group.replace_target = builder.config.value

                builder.base_value = Vec2(0, 0)
                builder.target_value = group.replace_target

                if builder.lifecycle.revert_ms:
                    if is_vec2(group.replace_target):
                        builder.revert_target = Vec2(0, 0)
                    else:
                        builder.revert_target = 0.0

            # OTHER PROPERTIES: Simple snapshot and reset
            else:
                if not group.is_base:
                    group.accumulated_value = current_value

                if builder.config.property == "pos" and builder.config.mode == "override" and group.is_base:
                    mouse_x, mouse_y = ctrl.mouse_pos()
                    builder.base_value = Vec2(mouse_x, mouse_y)
                elif builder.config.property in ("direction", "pos", "vector") and not is_vec2(current_value):
                    builder.base_value = Vec2(0, 0)
                else:
                    builder.base_value = current_value

                if builder.config.mode == "offset":
                    if isinstance(builder.config.value, tuple):
                        builder.target_value = Vec2.from_tuple(builder.config.value)
                    else:
                        builder.target_value = builder.config.value
                else:
                    builder.target_value = builder._calculate_target_value()

                if not group.is_base and builder.config.mode == "offset" and builder.lifecycle.revert_ms:
                    accumulated = group.accumulated_value
                    if is_vec2(accumulated):
                        builder.revert_target = Vec2(-accumulated.x, -accumulated.y)
                    elif isinstance(accumulated, (int, float)):
                        builder.revert_target = -accumulated
                    else:
                        builder.revert_target = None

        def _should_frame_loop_be_active(self) -> bool:
            """Override to check velocity movement"""
            has_movement = self._has_movement()
            if has_movement:
                return True

            for group in self._layer_groups.values():
                for builder in group.builders:
                    if not builder.lifecycle.is_complete():
                        return True

            return False

        def _ensure_frame_loop_running(self):
            """Override to sync absolute position on start"""
            if self._frame_loop_job is None:
                self._last_frame_time = time.perf_counter()
                self._frame_loop_job = self._schedule_cron_interval(
                    self._get_frame_interval_str(),
                    self._tick_frame
                )
                # Sync to actual mouse position only if we have absolute position builders
                has_absolute_builder = any(
                    group.property == "pos" and any(
                        builder.config.movement_type == "absolute"
                        for builder in group.builders
                    )
                    for group in self._layer_groups.values()
                )
                if has_absolute_builder:
                    current_mouse = Vec2(*ctrl.mouse_pos())
                    self._absolute_current_pos = current_mouse
                    self._absolute_base_pos = current_mouse

        def _stop_frame_loop(self):
            """Override to handle subpixel reset, position sync, and mouse-specific stop callbacks"""
            if self._frame_loop_job is not None:
                self._cancel_cron(self._frame_loop_job)
                self._frame_loop_job = None
                self._last_frame_time = None
                self._subpixel_adjuster.reset()

                if self._absolute_current_pos is not None:
                    current_mouse = Vec2(*ctrl.mouse_pos())
                    self._absolute_current_pos = current_mouse
                    if self._absolute_base_pos is not None:
                        diff = abs(current_mouse.x - self._absolute_base_pos.x) + abs(current_mouse.y - self._absolute_base_pos.y)
                        if diff > 2:
                            self._absolute_base_pos = current_mouse

                for callback in self._stop_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        pass
                self._stop_callbacks.clear()

        # ====================================================================
        # ABSTRACT METHOD IMPLEMENTATIONS (8)
        # ====================================================================

        def _create_active_builder(self, config, is_base):
            """Factory for mouse ActiveBuilder"""
            from .builder import ActiveBuilder
            return ActiveBuilder(config, self, is_base)

        def _get_or_create_group(self, builder) -> 'LayerGroup':
            """Get existing group or create new one for this builder"""
            layer = builder.config.layer_name

            if layer in self._layer_groups:
                group = self._layer_groups[layer]
                group.input_type = builder.config.input_type
                return group

            # Map mouse property names to PropertyKind
            PropertyKind = core.PropertyKind
            _PROPERTY_KIND_MAP = {
                "speed": PropertyKind.SCALAR,
                "pos": PropertyKind.POSITION,
                "direction": PropertyKind.DIRECTION,
                "vector": PropertyKind.VECTOR,
                "scroll_pos": PropertyKind.POSITION,
            }
            prop_kind = _PROPERTY_KIND_MAP.get(builder.config.property, PropertyKind.SCALAR)

            group = LayerGroup(
                layer_name=layer,
                property=builder.config.property,
                property_kind=prop_kind,
                mode=builder.config.mode,
                layer_type=builder.config.layer_type,
                order=builder.config.order,
                input_type=builder.config.input_type
            )

            if group.is_base:
                input_type = group.input_type

                if input_type == "scroll":
                    if builder.config.property == "speed":
                        group.accumulated_value = self._base_scroll_speed
                    elif builder.config.property == "direction":
                        group.accumulated_value = self._base_scroll_direction.copy()
                else:
                    if builder.config.property == "speed":
                        group.accumulated_value = self._base_speed
                    elif builder.config.property == "direction":
                        group.accumulated_value = self._base_direction.copy()
                    elif builder.config.property == "pos":
                        pass  # Position uses absolute coordinates, keep at (0,0)
            elif builder.config.mode == "override":
                if builder.config.property == "speed":
                    group.accumulated_value = self._compute_velocity()[0]
                elif builder.config.property == "direction":
                    group.accumulated_value = self._compute_velocity()[1]
                elif builder.config.property == "vector":
                    speed, direction = self._compute_velocity()
                    group.accumulated_value = direction * speed
                elif builder.config.property == "pos":
                    pos, _, _, _, _, _ = self._compute_current_state()
                    group.accumulated_value = pos

            if builder.config.order is not None:
                self._layer_orders[layer] = builder.config.order
            elif not builder.config.is_base_layer():
                if layer not in self._layer_orders:
                    self._layer_orders[layer] = self._next_auto_order
                    self._next_auto_order += 1
                    group.order = self._layer_orders[layer]

            self._layer_groups[layer] = group
            return group

        def _compute_current_state(self) -> tuple:
            """Compute (position, speed, direction, scroll_speed, scroll_direction, pos_is_override)"""
            pos = Vec2(self._absolute_base_pos.x, self._absolute_base_pos.y) if self._absolute_base_pos else Vec2(0, 0)
            speed = self._base_speed
            direction = Vec2(self._base_direction.x, self._base_direction.y)
            scroll_speed = self._base_scroll_speed
            scroll_direction = Vec2(self._base_scroll_direction.x, self._base_scroll_direction.y)
            pos_is_override = False

            base_groups = []
            user_groups = []

            for layer_name, group in self._layer_groups.items():
                if group.is_base:
                    base_groups.append(group)
                else:
                    user_groups.append(group)

            def get_layer_order(group) -> int:
                return group.order if group.order is not None else 999999

            user_groups = sorted(user_groups, key=get_layer_order)

            for group in base_groups:
                pos, speed, direction, scroll_speed, scroll_direction, override = self._apply_group(group, pos, speed, direction, scroll_speed, scroll_direction)
                pos_is_override = pos_is_override or override

            for group in user_groups:
                pos, speed, direction, scroll_speed, scroll_direction, override = self._apply_group(group, pos, speed, direction, scroll_speed, scroll_direction)
                pos_is_override = pos_is_override or override

            return (pos, speed, direction, scroll_speed, scroll_direction, pos_is_override)

        def _apply_group(self, group, *accumulated):
            """Apply a layer group's aggregated value"""
            pos, speed, direction, scroll_speed, scroll_direction = accumulated
            prop = group.property
            mode = group.mode
            current_value = group.get_current_value()
            pos_is_override = False

            input_type = group.input_type

            if input_type == "scroll":
                if prop == "speed":
                    scroll_speed = mode_operations.apply_scalar_mode(mode, current_value, scroll_speed)
                elif prop == "direction":
                    scroll_direction = mode_operations.apply_direction_mode(mode, current_value, scroll_direction)
                elif prop == "vector":
                    scroll_speed, scroll_direction = mode_operations.apply_vector_mode(mode, current_value, scroll_speed, scroll_direction)
            else:
                if prop == "speed":
                    speed = mode_operations.apply_scalar_mode(mode, current_value, speed)
                elif prop == "direction":
                    direction = mode_operations.apply_direction_mode(mode, current_value, direction)
                elif prop == "vector":
                    speed, direction = mode_operations.apply_vector_mode(mode, current_value, speed, direction)

            if prop == "pos":
                pos = mode_operations.apply_position_mode(mode, current_value, pos)
                pos_is_override = (mode == "override")

            return pos, speed, direction, scroll_speed, scroll_direction, pos_is_override

        def _tick_frame(self):
            """Main frame loop tick"""
            current_time, dt = self._calculate_delta_time()
            if dt is None:
                return

            self._check_debounce_pending(current_time)

            phase_transitions = self._advance_all_builders(current_time)

            frame_delta = Vec2(0, 0)
            frame_delta += self._compute_velocity_delta()

            has_absolute_position, absolute_target, relative_delta, relative_position_updates = self._process_position_builders()
            frame_delta += relative_delta

            self._emit_mouse_movement(has_absolute_position, absolute_target, frame_delta)

            scroll_pos_delta, scroll_position_updates = self._process_scroll_position_builders()
            self._emit_scroll(scroll_pos_delta if scroll_pos_delta.magnitude() > 0.001 else None)

            for group in self._layer_groups.values():
                if group.property == "pos" and group.replace_target is not None:
                    if group.builders and group.builders[0].config.movement_type == "relative":
                        group.committed_value += relative_delta

            for builder, new_value, new_int_value in relative_position_updates:
                builder._last_emitted_relative_pos = new_value
                builder._total_emitted_int = new_int_value

            for builder, new_value, _ in scroll_position_updates:
                builder._last_emitted_scroll_pos = new_value

            completed_layers = self._remove_completed_builders(current_time)
            self._execute_phase_callbacks(phase_transitions)
            self._stop_frame_loop_if_done()

        def _calculate_delta_time(self) -> tuple:
            """Calculate time since last frame. Returns (current_time, dt) where dt is None on first frame."""
            now = time.perf_counter()
            if self._last_frame_time is None:
                self._last_frame_time = now
                return (now, None)

            dt = now - self._last_frame_time
            self._last_frame_time = now
            return (now, dt)

        def _advance_all_builders(self, current_time: float) -> list:
            """Advance all groups and track phase transitions."""
            phase_transitions = []

            for layer, group in list(self._layer_groups.items()):
                group_transitions, builders_to_remove = group.advance(current_time)
                phase_transitions.extend(group_transitions)

                if not hasattr(group, '_pending_bake_results'):
                    group._pending_bake_results = []
                group._pending_bake_results.extend(builders_to_remove)

            return phase_transitions

        def _remove_completed_builders(self, current_time: float) -> set:
            """Remove completed builders from groups"""
            completed_layers = set()

            for layer, group in list(self._layer_groups.items()):
                builders_to_remove = []

                for builder in group.builders:
                    if builder._marked_for_removal:
                        builders_to_remove.append(builder)
                        continue

                    completed_phase, _ = builder.advance(current_time)

                    if completed_phase is not None:
                        if (builder.config.property == "pos" and
                            builder.config.movement_type == "relative" and
                            hasattr(builder, '_total_emitted_int')):

                            final_value = builder.get_interpolated_value()
                            final_target_int = Vec2(round(final_value.x), round(final_value.y))
                            final_delta_int = final_target_int - builder._total_emitted_int

                            if final_delta_int.x != 0 or final_delta_int.y != 0:
                                _, move_relative_override = self._get_override_functions()
                                if move_relative_override is not None:
                                    move_relative_override(int(final_delta_int.x), int(final_delta_int.y))
                                else:
                                    mouse_move_relative(int(final_delta_int.x), int(final_delta_int.y))

                        builders_to_remove.append(builder)
                    elif builder.lifecycle.should_be_garbage_collected():
                        builders_to_remove.append(builder)

                if hasattr(group, '_pending_bake_results'):
                    for builder, bake_result in group._pending_bake_results:
                        if builder in group.builders:
                            if bake_result == "bake_to_base":
                                self._bake_group_to_base(group)
                    group._pending_bake_results = []

                for builder in builders_to_remove:
                    group.remove_builder(builder)

                if not group.should_persist():
                    if layer in self._layer_groups:
                        del self._layer_groups[layer]
                    if layer in self._layer_orders:
                        del self._layer_orders[layer]
                    completed_layers.add(layer)

            return completed_layers

        def _execute_phase_callbacks(self, phase_transitions: list):
            """Execute callbacks for completed phases"""
            for builder, completed_phase in phase_transitions:
                builder.lifecycle.execute_callbacks(completed_phase)

        def _bake_group_to_base(self, group):
            """Bake base layer group's value into base state"""
            if not group.is_base:
                return

            current_value = group.get_current_value()
            prop = group.property
            input_type = group.input_type

            if input_type == "scroll":
                if prop == "speed":
                    self._base_scroll_speed = float(current_value)
                elif prop == "direction":
                    if isinstance(current_value, tuple):
                        self._base_scroll_direction = Vec2.from_tuple(current_value).normalized()
                    else:
                        self._base_scroll_direction = current_value.normalized() if hasattr(current_value, 'normalized') else current_value
                elif prop == "vector":
                    if isinstance(current_value, tuple):
                        self._base_scroll_direction = Vec2.from_tuple(current_value).normalized()
                        self._base_scroll_speed = Vec2.from_tuple(current_value).magnitude()
                    else:
                        self._base_scroll_direction = current_value.normalized()
                        self._base_scroll_speed = current_value.magnitude()
            else:
                if prop == "pos":
                    if isinstance(current_value, tuple):
                        self._absolute_base_pos = Vec2.from_tuple(current_value)
                    else:
                        self._absolute_base_pos = current_value
                elif prop == "speed":
                    self._base_speed = float(current_value)
                elif prop == "direction":
                    if isinstance(current_value, tuple):
                        self._base_direction = Vec2.from_tuple(current_value).normalized()
                    else:
                        self._base_direction = current_value.normalized() if hasattr(current_value, 'normalized') else current_value
                elif prop == "vector":
                    if isinstance(current_value, tuple):
                        self._base_direction = Vec2.from_tuple(current_value).normalized()
                        self._base_speed = Vec2.from_tuple(current_value).magnitude()
                    else:
                        self._base_direction = current_value.normalized()
                        self._base_speed = current_value.magnitude()
                else:
                    self._base_direction = current_value.normalized()
                    self._base_speed = current_value.magnitude()

        def _bake_property(self, property_name: str, layer: Optional[str] = None, input_type: str = "move"):
            """Bake current computed value of a property into base state"""
            is_scroll = input_type == "scroll"

            if is_scroll:
                attr_prefix = "scroll_"
            else:
                attr_prefix = ""
            current_value = getattr(self, f"{attr_prefix}{property_name}")

            if property_name == "vector":
                mag = current_value.magnitude()
                norm = current_value.normalized() if mag > EPSILON else Vec2(1, 0)
                if is_scroll:
                    self._base_scroll_speed = mag
                    self._base_scroll_direction = norm
                else:
                    self._base_speed = mag
                    self._base_direction = norm
            elif property_name == "speed":
                if is_scroll:
                    self._base_scroll_speed = float(current_value)
                else:
                    self._base_speed = float(current_value)
            elif property_name == "direction":
                if is_scroll:
                    self._base_scroll_direction = Vec2(current_value.x, current_value.y)
                else:
                    self._base_direction = Vec2(current_value.x, current_value.y)
            elif property_name == "pos":
                self._absolute_base_pos = Vec2(current_value.x, current_value.y) if hasattr(current_value, 'x') else current_value

            if layer:
                if layer in self._layer_groups:
                    del self._layer_groups[layer]
                if layer in self._layer_orders:
                    del self._layer_orders[layer]
            else:
                layers_to_remove = [
                    l for l, g in self._layer_groups.items()
                    if g.property == property_name and getattr(g, 'input_type', 'move') == input_type
                ]
                for l in layers_to_remove:
                    if l in self._layer_groups:
                        del self._layer_groups[l]
                    if l in self._layer_orders:
                        del self._layer_orders[l]

        def stop(self, transition_ms: Optional[float] = None, easing: str = "linear", **kwargs):
            """Stop everything"""
            transition_ms = validate_timing(transition_ms, 'transition_ms', method='stop')

            config = BuilderConfig()
            all_kwargs = {'easing': easing, **kwargs}
            config.validate_method_kwargs('stop', **all_kwargs)

            for layer in list(self._layer_groups.keys()):
                group = self._layer_groups[layer]
                if group.is_base:
                    self._bake_group_to_base(group)

            self._layer_groups.clear()
            self._layer_orders.clear()
            self._throttle_times.clear()
            self._rate_builder_cache.clear()
            self._debounce_pending.clear()
            self._primed_button = None

            if transition_ms is None or transition_ms == 0:
                self._base_speed = 0.0
                self._base_scroll_speed = 0.0
                if len(self._layer_groups) == 0:
                    self._stop_frame_loop()
            else:
                from .builder import ActiveBuilder

                if self._base_speed != 0:
                    config = BuilderConfig()
                    config.property = "speed"
                    config.layer_name = f"base.{config.property}"
                    config.operator = "to"
                    config.value = 0
                    config.over_ms = transition_ms
                    config.over_easing = easing
                    builder = ActiveBuilder(config, self, is_base_layer=True)
                    self.add_builder(builder)

                if self._base_scroll_speed != 0:
                    scroll_config = BuilderConfig()
                    scroll_config.property = "speed"
                    scroll_config.input_type = "scroll"
                    scroll_config.layer_name = f"scroll:base.{scroll_config.property}"
                    scroll_config.operator = "to"
                    scroll_config.value = 0
                    scroll_config.over_ms = transition_ms
                    scroll_config.over_easing = easing
                    scroll_builder = ActiveBuilder(scroll_config, self, is_base_layer=True)
                    self.add_builder(scroll_builder)

        # ====================================================================
        # MOUSE-SPECIFIC METHODS (velocity, scroll, position, emit, etc.)
        # ====================================================================


        def _bake_builder(self, builder, removing_layer: Optional[str] = None):
            """Merge builder's final aggregated value into base state"""
            if builder.lifecycle.has_reverted():
                return

            current_value = builder.get_interpolated_value()
            if current_value is None:
                return

            prop = builder.config.property
            mode = builder.config.mode
            input_type = getattr(builder.config, 'input_type', 'move')

            if input_type == "scroll":
                if prop == "vector":
                    self._base_scroll_speed, self._base_scroll_direction = mode_operations.apply_vector_mode(
                        mode, current_value, self._base_scroll_speed, self._base_scroll_direction
                    )
                elif prop == "speed":
                    self._base_scroll_speed = mode_operations.apply_scalar_mode(mode, current_value, self._base_scroll_speed)
                elif prop == "direction":
                    self._base_scroll_direction = mode_operations.apply_direction_mode(mode, current_value, self._base_scroll_direction)
            else:
                if prop == "vector":
                    self._base_speed, self._base_direction = mode_operations.apply_vector_mode(
                        mode, current_value, self._base_speed, self._base_direction
                    )
                elif prop == "speed":
                    self._base_speed = mode_operations.apply_scalar_mode(mode, current_value, self._base_speed)
                elif prop == "direction":
                    self._base_direction = mode_operations.apply_direction_mode(mode, current_value, self._base_direction)

            if prop == "pos":
                if mode == "offset":
                    if self._absolute_current_pos is not None and self._absolute_base_pos is not None:
                        if builder.lifecycle.over_ms is not None and builder.lifecycle.over_ms > 0:
                            self._absolute_base_pos = Vec2(self._absolute_current_pos.x, self._absolute_current_pos.y)
                        else:
                            self._absolute_base_pos = Vec2(self._absolute_base_pos.x + current_value.x, self._absolute_base_pos.y + current_value.y)
                            self._absolute_current_pos = Vec2(self._absolute_base_pos.x, self._absolute_base_pos.y)
                elif mode == "override":
                    if self._absolute_base_pos is None or self._absolute_current_pos is None:
                        current_screen_pos = Vec2(*ctrl.mouse_pos())
                        self._absolute_base_pos = current_screen_pos
                        self._absolute_current_pos = current_screen_pos

                    if self._base_speed == 0:
                        self._absolute_base_pos = Vec2(current_value.x, current_value.y)
                        self._absolute_current_pos = Vec2(current_value.x, current_value.y)
                    else:
                        self._absolute_base_pos = Vec2(self._absolute_current_pos.x, self._absolute_current_pos.y)
                elif mode == "scale":
                    if self._absolute_base_pos is not None and self._absolute_current_pos is not None:
                        self._absolute_base_pos = Vec2(self._absolute_base_pos.x * current_value, self._absolute_base_pos.y * current_value)
                        self._absolute_current_pos = Vec2(self._absolute_base_pos.x, self._absolute_base_pos.y)

                active_count = len(self._layer_groups)
                if removing_layer and removing_layer in self._layer_groups:
                    active_count -= 1

                will_be_active = self._has_movement() or active_count > 0
                is_relative = builder.config.movement_type == "relative"
                if not will_be_active and not is_relative and self._absolute_base_pos is not None:
                    move_absolute_override, _ = self._get_override_functions()
                    if move_absolute_override is not None:
                        move_absolute_override(int(self._absolute_base_pos.x), int(self._absolute_base_pos.y))
                    else:
                        mouse_move(int(self._absolute_base_pos.x), int(self._absolute_base_pos.y))

            if self._should_frame_loop_be_active():
                self._ensure_frame_loop_running()

        def _compute_velocity(self) -> tuple:
            """Compute (speed, direction) for mouse movement"""
            speed = self._base_speed
            direction = Vec2(self._base_direction.x, self._base_direction.y)

            base_groups = []
            user_groups = []
            emit_groups = []

            for layer_name, group in self._layer_groups.items():
                if group.property in ("speed", "direction", "vector"):
                    if group.input_type != 'move':
                        continue

                    if group.is_emit_layer:
                        emit_groups.append(group)
                    elif group.is_base:
                        base_groups.append(group)
                    else:
                        user_groups.append(group)

            def get_layer_order(group) -> int:
                return group.order if group.order is not None else 999999

            user_groups = sorted(user_groups, key=get_layer_order)

            for group in base_groups + user_groups:
                prop = group.property
                mode = group.mode
                current_value = group.get_current_value()

                if prop == "speed":
                    speed = mode_operations.apply_scalar_mode(mode, current_value, speed)
                elif prop == "direction":
                    direction = mode_operations.apply_direction_mode(mode, current_value, direction)
                elif prop == "vector":
                    speed, direction = mode_operations.apply_vector_mode(mode, current_value, speed, direction)

            if emit_groups:
                base_velocity = direction * speed
                for group in emit_groups:
                    if group.property == "vector" and group.mode == "offset":
                        emit_offset = group.get_current_value()
                        base_velocity = base_velocity + emit_offset

                speed = base_velocity.magnitude()
                if speed > EPSILON:
                    direction = base_velocity.normalized()

            return speed, direction

        def _compute_scroll_velocity(self) -> tuple:
            """Compute (scroll_speed, scroll_direction) for scroll"""
            scroll_speed = self._base_scroll_speed
            scroll_direction = Vec2(self._base_scroll_direction.x, self._base_scroll_direction.y)

            base_groups = []
            user_groups = []
            emit_groups = []

            for layer_name, group in self._layer_groups.items():
                if group.property in ("speed", "direction", "vector"):
                    if getattr(group, 'input_type', 'move') != 'scroll':
                        continue

                    if group.is_emit_layer:
                        emit_groups.append(group)
                    elif group.is_base:
                        base_groups.append(group)
                    else:
                        user_groups.append(group)

            def get_layer_order(group) -> int:
                return group.order if group.order is not None else 999999

            user_groups = sorted(user_groups, key=get_layer_order)

            for group in base_groups + user_groups:
                prop = group.property
                mode = group.mode
                current_value = group.get_current_value()

                if prop == "speed":
                    scroll_speed = mode_operations.apply_scalar_mode(mode, current_value, scroll_speed)
                elif prop == "direction":
                    scroll_direction = mode_operations.apply_direction_mode(mode, current_value, scroll_direction)
                elif prop == "vector":
                    scroll_speed, scroll_direction = mode_operations.apply_vector_mode(mode, current_value, scroll_speed, scroll_direction)

            if emit_groups:
                base_velocity = scroll_direction * scroll_speed
                for group in emit_groups:
                    if group.property == "vector" and group.mode == "offset":
                        emit_offset = group.get_current_value()
                        base_velocity = base_velocity + emit_offset

                scroll_speed = base_velocity.magnitude()
                if scroll_speed > EPSILON:
                    scroll_direction = base_velocity.normalized()

            return scroll_speed, scroll_direction

        def _apply_velocity_movement(self, speed: float, direction):
            """Apply velocity-based movement to absolute position"""
            if speed == 0:
                return
            if self._absolute_current_pos is None:
                return

            velocity = direction * speed
            dx_int, dy_int = self._subpixel_adjuster.adjust(velocity.x, velocity.y)
            self._absolute_current_pos = Vec2(self._absolute_current_pos.x + dx_int, self._absolute_current_pos.y + dy_int)

        def _compute_velocity_delta(self):
            """Compute velocity contribution as delta"""
            speed, direction = self._compute_velocity()
            if speed == 0:
                return Vec2(0, 0)

            velocity = direction * speed
            dx, dy = self._subpixel_adjuster.adjust(velocity.x, velocity.y)
            return Vec2(dx, dy)

        def _process_position_builders(self) -> tuple:
            """Process all position builders and gather their contributions"""
            has_absolute_position = False
            absolute_target = None
            relative_delta = Vec2(0, 0)
            relative_position_updates = []

            for layer_name, group in self._layer_groups.items():
                if group.property != "pos":
                    continue
                if not group.builders:
                    continue

                first_builder = group.builders[0]

                if first_builder.config.movement_type == "absolute":
                    has_absolute_position = True
                    absolute_target = group.get_current_value()
                else:
                    for builder in group.builders:
                        current_interpolated = builder.get_interpolated_value()

                        if not hasattr(builder, '_last_emitted_relative_pos'):
                            builder._last_emitted_relative_pos = Vec2(0, 0)
                        if not hasattr(builder, '_total_emitted_int'):
                            builder._total_emitted_int = Vec2(0, 0)

                        target_total_int = Vec2(round(current_interpolated.x), round(current_interpolated.y))
                        actual_delta_int = target_total_int - builder._total_emitted_int

                        relative_delta += Vec2(actual_delta_int.x, actual_delta_int.y)

                        new_total_emitted = builder._total_emitted_int + actual_delta_int
                        relative_position_updates.append((builder, current_interpolated, new_total_emitted))

            for layer_name, group in self._layer_groups.items():
                if group.property != "pos":
                    continue
                if not group.builders:
                    continue
                first_builder = group.builders[0]
                if first_builder.config.movement_type == "relative" and group.replace_target is not None:
                    projected_total = group.committed_value + relative_delta
                    clamped_total = Vec2(
                        max(-abs(group.replace_target.x), min(abs(group.replace_target.x), projected_total.x)),
                        max(-abs(group.replace_target.y), min(abs(group.replace_target.y), projected_total.y))
                    )
                    clamped_delta = clamped_total - group.committed_value
                    relative_delta = clamped_delta
                    break

            return has_absolute_position, absolute_target, relative_delta, relative_position_updates

        def _process_scroll_position_builders(self) -> tuple:
            """Process all scroll_pos builders"""
            scroll_delta = Vec2(0, 0)
            scroll_position_updates = []

            for layer_name, group in self._layer_groups.items():
                if group.property != "scroll_pos":
                    continue
                if not group.builders:
                    continue

                for builder in group.builders:
                    current_interpolated = builder.get_interpolated_value()

                    if not hasattr(builder, '_last_emitted_scroll_pos'):
                        builder._last_emitted_scroll_pos = Vec2(0, 0)
                    if not hasattr(builder, '_total_emitted_scroll_int'):
                        builder._total_emitted_scroll_int = Vec2(0, 0)

                    target_total = current_interpolated
                    actual_delta = target_total - builder._last_emitted_scroll_pos

                    scroll_delta += actual_delta
                    scroll_position_updates.append((builder, current_interpolated, current_interpolated))

            return scroll_delta, scroll_position_updates

        def _has_api_overrides(self) -> bool:
            """Check if any active group has API overrides"""
            for group in self._layer_groups.values():
                for builder in group.builders:
                    if builder.config.api_override is not None:
                        return True
            return False

        def _get_override_functions(self):
            """Get override functions if any builder has overrides"""
            if not self._has_api_overrides():
                return None, None

            api_override = None
            for group in self._layer_groups.values():
                for builder in group.builders:
                    if builder.config.api_override is not None:
                        api_override = builder.config.api_override

            return get_mouse_move_functions(api_override, api_override)

        def _emit_mouse_movement(self, has_absolute_position: bool, absolute_target, frame_delta):
            """Emit mouse movement based on accumulated deltas"""
            move_absolute_override, move_relative_override = self._get_override_functions()

            if has_absolute_position:
                final_pos = absolute_target + frame_delta
                self._absolute_current_pos = final_pos
                new_x = int(round(final_pos.x))
                new_y = int(round(final_pos.y))
                current_x, current_y = ctrl.mouse_pos()
                if new_x != current_x or new_y != current_y:
                    if move_absolute_override is not None:
                        move_absolute_override(new_x, new_y)
                    else:
                        mouse_move(new_x, new_y)
            else:
                if frame_delta.x != 0 or frame_delta.y != 0:
                    dx = round(frame_delta.x)
                    dy = round(frame_delta.y)
                    if move_relative_override is not None:
                        move_relative_override(dx, dy)
                    else:
                        mouse_move_relative(dx, dy)

        def _emit_scroll(self, scroll_pos_delta=None):
            """Emit scroll events"""
            scroll_speed = self.scroll_speed.current
            scroll_direction = self.scroll_direction.current

            scroll_velocity = scroll_direction * scroll_speed

            if scroll_pos_delta is not None:
                scroll_velocity = scroll_velocity + scroll_pos_delta

            if abs(scroll_velocity.x) < SCROLL_EMIT_THRESHOLD and abs(scroll_velocity.y) < SCROLL_EMIT_THRESHOLD:
                return

            mouse_scroll_native(scroll_velocity.x, scroll_velocity.y)

        def _update_relative_position_tracking(self, relative_position_updates: list, completed_layers: set):
            """Update tracking for relative position builders after removal"""
            for builder, new_value, new_int_value in relative_position_updates:
                if builder.config.layer_name not in completed_layers:
                    builder._last_emitted_relative_pos = new_value
                    builder._total_emitted_int = new_int_value

        def _has_movement(self) -> bool:
            """Check if there's any movement happening"""
            if self._base_speed != 0:
                return True
            if self._base_scroll_speed != 0:
                return True

            for group in self._layer_groups.values():
                prop = group.property
                if prop in ("speed", "direction", "vector"):
                    if prop in ("speed", "vector"):
                        return True

            return False

        def _get_cardinal_direction(self, direction) -> Optional[str]:
            """Get cardinal/intercardinal direction name from direction vector"""
            x, y = direction.x, direction.y

            if x == 0 and y == 0:
                return None

            threshold = 2.414

            if abs(x) > abs(y) * threshold:
                return "right" if x > 0 else "left"
            if abs(y) > abs(x) * threshold:
                return "up" if y < 0 else "down"

            if x > 0 and y < 0:
                return "up_right"
            elif x < 0 and y < 0:
                return "up_left"
            elif x > 0 and y > 0:
                return "down_right"
            elif x < 0 and y > 0:
                return "down_left"

            return "right"

        # ====================================================================
        # PUBLIC STATE ACCESSORS (inner classes)
        # ====================================================================

        class CardinalPropertyState:
            """Smart accessor for direction_cardinal with .current and .target"""
            def __init__(self, rig_state, current_cardinal: Optional[str]):
                self._rig_state = rig_state
                self._current_cardinal = current_cardinal

            @property
            def current(self) -> Optional[str]:
                return self._current_cardinal

            @property
            def target(self) -> Optional[str]:
                layer_name = "base.direction"
                if layer_name in self._rig_state._layer_groups:
                    group = self._rig_state._layer_groups[layer_name]
                    if len(group.builders) > 0:
                        for builder in group.builders:
                            if not builder.lifecycle.is_complete():
                                target_dir = builder.target_value
                                if is_vec2(target_dir):
                                    return self._rig_state._get_cardinal_direction(target_dir)
                return None

            def __repr__(self):
                return f"CardinalPropertyState(current={self._current_cardinal}, target={self.target})"

            def __str__(self):
                return str(self._current_cardinal)

            def __eq__(self, other):
                if isinstance(other, _MouseRigState.CardinalPropertyState):
                    return self._current_cardinal == other._current_cardinal
                return self._current_cardinal == other

            def __ne__(self, other):
                return not self.__eq__(other)

            def __bool__(self):
                return self._current_cardinal is not None

        @property
        def direction_cardinal(self):
            """Current direction as cardinal/intercardinal string"""
            direction_vec = self._compute_current_state()[2]
            cardinal = self._get_cardinal_direction(direction_vec)
            return _MouseRigState.CardinalPropertyState(self, cardinal)

        class LayersView:
            """Dict-like read-only view of active layers."""
            __slots__ = ('_groups',)

            def __init__(self, groups):
                self._groups = groups

            def __getitem__(self, name: str):
                group = self._groups.get(name)
                return _MouseRigState.LayerState(group) if group is not None else None

            def get(self, name: str, default=None):
                group = self._groups.get(name)
                return _MouseRigState.LayerState(group) if group is not None else default

            def keys(self):
                return self._groups.keys()

            def values(self):
                return [_MouseRigState.LayerState(g) for g in self._groups.values()]

            def items(self):
                return [(k, _MouseRigState.LayerState(g)) for k, g in self._groups.items()]

            def __contains__(self, name: str) -> bool:
                return name in self._groups

            def __len__(self) -> int:
                return len(self._groups)

            def __iter__(self):
                return iter(self._groups)

            def __bool__(self) -> bool:
                return bool(self._groups)

            def __repr__(self) -> str:
                return repr(dict(self.items()))

        @property
        def layers(self):
            """Dict-like view of active layers"""
            return _MouseRigState.LayersView(self._layer_groups)

        class LayerState:
            """State information for a specific layer"""
            def __init__(self, group):
                self._group = group

            def __repr__(self) -> str:
                def format_value(val):
                    if is_vec2(val):
                        return f"({val.x:.1f}, {val.y:.1f})"
                    elif isinstance(val, float):
                        return f"{val:.1f}"
                    elif val is None:
                        return "None"
                    else:
                        return str(val)

                current_value = self._group.get_current_value()
                target_value = self._group.target

                lines = [
                    f"LayerState('{self._group.layer_name}'):",
                    f"  property = {self._group.property}",
                    f"  mode = {self._group.mode}",
                    f"  layer_type = {self._group.layer_type}",
                    f"  order = {self._group.order}",
                    f"  is_emit_layer = {self._group.is_emit_layer}",
                    f"  source_layer = {self._group.source_layer}",
                    f"  value = {format_value(current_value)}",
                    f"  target = {format_value(target_value)}",
                    f"  accumulated = {format_value(self._group.accumulated_value)}",
                    f"  active_builders = {len(self._group.builders)}",
                ]

                if self._group.builders:
                    builder = self._group.builders[0]
                    lifecycle = builder.lifecycle
                    lines.append(f"  time_alive = {builder.time_alive:.2f}s")
                    lines.append(f"  operator = {builder.config.operator}")

                    if lifecycle.over_ms:
                        lines.append(f"  over_ms = {lifecycle.over_ms}")
                    if lifecycle.hold_ms:
                        lines.append(f"  hold_ms = {lifecycle.hold_ms}")
                    if lifecycle.revert_ms:
                        lines.append(f"  revert_ms = {lifecycle.revert_ms}")

                return "\n".join(lines)

            def __str__(self) -> str:
                return self.__repr__()

            @property
            def prop(self) -> str:
                return self._group.property

            @property
            def mode(self) -> str:
                return self._group.mode

            @property
            def operator(self) -> str:
                if self._group.builders:
                    return self._group.builders[0].config.operator
                return "accumulated"

            @property
            def current(self):
                return self._group.get_current_value()

            @property
            def target(self):
                return self._group.target

            @property
            def time_alive(self) -> float:
                return time.perf_counter() - self._group.creation_time

            @property
            def time_left(self) -> float:
                if not self._group.builders:
                    return 0

                builder = self._group.builders[0]
                lifecycle = builder.lifecycle
                total_duration = 0

                if lifecycle.over_ms:
                    total_duration += lifecycle.over_ms
                if lifecycle.hold_ms:
                    total_duration += lifecycle.hold_ms
                if lifecycle.revert_ms:
                    total_duration += lifecycle.revert_ms

                if total_duration == 0:
                    return 0

                elapsed_ms = builder.time_alive * 1000
                remaining_ms = max(0, total_duration - elapsed_ms)
                return remaining_ms / 1000

            def __getattr__(self, name: str):
                raise AttributeError(
                    f"LayerState has no attribute '{name}'. "
                    f"Available attributes: {', '.join(VALID_LAYER_STATE_ATTRS)}"
                )

        class BasePropertyState:
            """Smart accessor for base state properties with .current and .target"""
            def __init__(self, rig_state, property_name: str, base_value):
                self._rig_state = rig_state
                self._property_name = property_name
                self._base_value = base_value

            @property
            def current(self):
                return self._base_value

            @property
            def target(self):
                layer_name = f"base.{self._property_name}"
                if layer_name in self._rig_state._layer_groups:
                    group = self._rig_state._layer_groups[layer_name]
                    if len(group.builders) > 0:
                        for builder in group.builders:
                            if not builder.lifecycle.is_complete():
                                return builder.target_value
                return None

            def __repr__(self):
                return f"BasePropertyState('{self._property_name}', value={self._base_value}, target={self.target})"

            def __str__(self):
                return str(self._base_value)

            def __add__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value + other_val

            def __radd__(self, other):
                return other + self._base_value

            def __sub__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value - other_val

            def __rsub__(self, other):
                return other - self._base_value

            def __mul__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value * other_val

            def __rmul__(self, other):
                return other * self._base_value

            def __truediv__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value / other_val

            def __rtruediv__(self, other):
                return other / self._base_value

            def __eq__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value == other_val

            def __ne__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value != other_val

            def __lt__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value < other_val

            def __le__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value <= other_val

            def __gt__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value > other_val

            def __ge__(self, other):
                other_val = other.current if isinstance(other, (_MouseRigState.BasePropertyState, _MouseRigState.SmartPropertyState)) else other
                return self._base_value >= other_val

            def __float__(self):
                return float(self._base_value)

            def __int__(self):
                return int(self._base_value)

            def __bool__(self):
                return bool(self._base_value)

            def __getattr__(self, name):
                return getattr(self._base_value, name)

        class BaseState:
            def __init__(self, rig_state):
                self._rig_state = rig_state

            def __repr__(self) -> str:
                pos = self.pos
                speed = self.speed
                direction = self.direction
                vector = self.vector
                cardinal = self.direction_cardinal
                scroll = self.scroll
                scroll_cardinal = scroll.direction_cardinal

                lines = [
                    "BaseState:",
                    f"  pos = ({pos.current.x:.1f}, {pos.current.y:.1f})",
                    f"  pos.current = ({pos.current.x:.1f}, {pos.current.y:.1f}), pos.target = {pos.target}",
                    f"  pos.x = {pos.x:.1f}, pos.y = {pos.y:.1f}",
                    f"  speed = {speed.current:.1f}",
                    f"  speed.current = {speed.current:.1f}, speed.target = {speed.target}",
                    f"  direction = ({direction.current.x:.2f}, {direction.current.y:.2f})",
                    f"  direction.current = ({direction.current.x:.2f}, {direction.current.y:.2f}), direction.target = {direction.target}",
                    f"  direction_cardinal = {cardinal.current or 'None'}",
                    f"  direction_cardinal.current = {cardinal.current or 'None'}, direction_cardinal.target = {cardinal.target or 'None'}",
                    f"  vector = ({vector.current.x:.2f}, {vector.current.y:.2f})",
                    f"  vector.current = ({vector.current.x:.2f}, {vector.current.y:.2f}), vector.target = {vector.target}",
                    f"  scroll = ({scroll.current.x:.2f}, {scroll.current.y:.2f})",
                    f"  scroll.current = ({scroll.current.x:.2f}, {scroll.current.y:.2f}), scroll.target = {scroll.target}",
                    f"  scroll.x = {scroll.x:.2f}, scroll.y = {scroll.y:.2f}",
                    f"  scroll.speed = {scroll.speed.current:.2f}",
                    f"  scroll.speed.current = {scroll.speed.current:.2f}, scroll.speed.target = {scroll.speed.target}",
                    f"  scroll.direction = ({scroll.direction.current.x:.2f}, {scroll.direction.current.y:.2f})",
                    f"  scroll.direction.current = ({scroll.direction.current.x:.2f}, {scroll.direction.current.y:.2f}), scroll.direction.target = {scroll.direction.target}",
                    f"  scroll.direction_cardinal = {scroll_cardinal.current or 'None'}",
                    f"  scroll.direction_cardinal.current = {scroll_cardinal.current or 'None'}, scroll.direction_cardinal.target = {scroll_cardinal.target or 'None'}",
                    f"  scroll.vector = ({scroll.vector.current.x:.2f}, {scroll.vector.current.y:.2f})",
                    f"  scroll.vector.current = ({scroll.vector.current.x:.2f}, {scroll.vector.current.y:.2f}), scroll.vector.target = {scroll.vector.target}",
                ]
                return "\n".join(lines)

            def __str__(self) -> str:
                return self.__repr__()

            @property
            def pos(self):
                base_pos = self._rig_state._absolute_base_pos if self._rig_state._absolute_base_pos else Vec2(0, 0)
                return _MouseRigState.BasePropertyState(self._rig_state, "pos", base_pos)

            @property
            def speed(self):
                return _MouseRigState.BasePropertyState(self._rig_state, "speed", self._rig_state._base_speed)

            @property
            def direction(self):
                return _MouseRigState.BasePropertyState(self._rig_state, "direction", self._rig_state._base_direction)

            @property
            def direction_cardinal(self):
                cardinal = self._rig_state._get_cardinal_direction(self._rig_state._base_direction)
                return _MouseRigState.CardinalPropertyState(self._rig_state, cardinal)

            @property
            def vector(self):
                base_vector = self._rig_state._base_direction * self._rig_state._base_speed
                return _MouseRigState.BasePropertyState(self._rig_state, "vector", base_vector)

            @property
            def scroll(self):
                return _MouseRigState.BaseScrollPropertyContainer(self._rig_state)

        class BaseScrollPropertyContainer:
            """Container for base scroll properties"""
            def __init__(self, rig_state):
                self._rig_state = rig_state

            @property
            def pos(self):
                base_scroll_amount = self._rig_state._base_scroll_direction * self._rig_state._base_scroll_speed
                return _MouseRigState.BasePropertyState(self._rig_state, "scroll", base_scroll_amount)

            @property
            def speed(self):
                return _MouseRigState.BasePropertyState(self._rig_state, "scroll_speed", self._rig_state._base_scroll_speed)

            @property
            def direction(self):
                return _MouseRigState.BasePropertyState(self._rig_state, "scroll_direction", self._rig_state._base_scroll_direction)

            @property
            def direction_cardinal(self):
                cardinal = self._rig_state._get_cardinal_direction(self._rig_state._base_scroll_direction)
                return _MouseRigState.CardinalPropertyState(self._rig_state, cardinal)

            @property
            def vector(self):
                base_scroll_vector = self._rig_state._base_scroll_direction * self._rig_state._base_scroll_speed
                return _MouseRigState.BasePropertyState(self._rig_state, "scroll_vector", base_scroll_vector)

            @property
            def current(self):
                return self._rig_state._base_scroll_direction * self._rig_state._base_scroll_speed

            @property
            def target(self):
                for layer_name, group in self._rig_state._layer_groups.items():
                    if (group.is_base and
                        group.property in ("scroll", "scroll_vector") and
                        len(group.builders) > 0):
                        for builder in group.builders:
                            if not builder.lifecycle.is_complete():
                                return builder.target_value
                return None

            @property
            def x(self):
                return self.current.x

            @property
            def y(self):
                return self.current.y

            def __repr__(self):
                return f"({self.current.x:.2f}, {self.current.y:.2f})"

            def __str__(self):
                return self.__repr__()

        @property
        def base(self):
            """Access to base (baked) state only"""
            return _MouseRigState.BaseState(self)

        class ScrollPropertyContainer:
            """Container for scroll properties with nested access"""
            def __init__(self, rig_state):
                self._rig_state = rig_state

            @property
            def pos(self):
                scroll_speed = self._rig_state._compute_current_state()[3]
                scroll_direction = self._rig_state._compute_current_state()[4]
                return _MouseRigState.SmartPropertyState(self._rig_state, "scroll", scroll_direction * scroll_speed)

            @property
            def speed(self):
                scroll_speed_val = self._rig_state._compute_current_state()[3]
                return _MouseRigState.SmartPropertyState(self._rig_state, "scroll_speed", scroll_speed_val)

            @property
            def direction(self):
                scroll_direction_vec = self._rig_state._compute_current_state()[4]
                return _MouseRigState.SmartPropertyState(self._rig_state, "scroll_direction", scroll_direction_vec)

            @property
            def direction_cardinal(self):
                scroll_direction_vec = self._rig_state._compute_current_state()[4]
                cardinal = self._rig_state._get_cardinal_direction(scroll_direction_vec)
                return _MouseRigState.CardinalPropertyState(self._rig_state, cardinal)

            @property
            def vector(self):
                scroll_speed = self._rig_state._compute_current_state()[3]
                scroll_direction = self._rig_state._compute_current_state()[4]
                return _MouseRigState.SmartPropertyState(self._rig_state, "scroll_vector", scroll_direction * scroll_speed)

            @property
            def current(self):
                scroll_speed = self._rig_state._compute_current_state()[3]
                scroll_direction = self._rig_state._compute_current_state()[4]
                return scroll_direction * scroll_speed

            @property
            def target(self):
                for layer_name, group in self._rig_state._layer_groups.items():
                    if (group.is_base and
                        group.property in ("scroll", "scroll_vector") and
                        len(group.builders) > 0):
                        for builder in group.builders:
                            if not builder.lifecycle.is_complete():
                                return builder.target_value
                return None

            @property
            def x(self):
                return self.current.x

            @property
            def y(self):
                return self.current.y

            def __repr__(self):
                return f"({self.current.x:.2f}, {self.current.y:.2f})"

            def __str__(self):
                return self.__repr__()

        class SmartPropertyState:
            """Smart accessor that provides both computed value and layer mode states"""
            def __init__(self, rig_state, property_name: str, computed_value):
                self._rig_state = rig_state
                self._property_name = property_name
                self._computed_current = computed_value

            @property
            def current(self):
                return self._computed_current

            @property
            def target(self):
                for layer_name, group in self._rig_state._layer_groups.items():
                    if (group.is_base and
                        group.property == self._property_name and
                        len(group.builders) > 0):
                        for builder in group.builders:
                            if not builder.lifecycle.is_complete():
                                return builder.target_value
                return None

            @property
            def x(self):
                if not hasattr(self._computed_current, 'x'):
                    raise AttributeError(f"Property '{self._property_name}' is a scalar and doesn't have .x component. Only Vec2 properties (pos, direction, vector) support .x/.y shortcuts.")
                return self._computed_current.x

            @property
            def y(self):
                if not hasattr(self._computed_current, 'y'):
                    raise AttributeError(f"Property '{self._property_name}' is a scalar and doesn't have .y component. Only Vec2 properties (pos, direction, vector) support .x/.y shortcuts.")
                return self._computed_current.y

            @property
            def offset(self):
                layer_name = f"{self._property_name}.offset"
                return self._rig_state.layers[layer_name]

            @property
            def override(self):
                layer_name = f"{self._property_name}.override"
                return self._rig_state.layers[layer_name]

            @property
            def scale(self):
                layer_name = f"{self._property_name}.scale"
                return self._rig_state.layers[layer_name]

            def __repr__(self):
                prop_type = "Vec2" if hasattr(self._computed_current, 'x') else "scalar"

                parts = [
                    f"SmartPropertyState('{self._property_name}')",
                    f"  .current - Current computed {self._property_name}",
                    f"  .target - Target from base animation (or None)",
                ]

                if prop_type == "Vec2":
                    parts.extend([
                        f"  .x - Shortcut to .current.x",
                        f"  .y - Shortcut to .current.y",
                    ])

                parts.extend([
                    f"  .offset - LayerState for implicit '{self._property_name}.offset' layer (or None)",
                    f"  .override - LayerState for implicit '{self._property_name}.override' layer (or None)",
                    f"  .scale - LayerState for implicit '{self._property_name}.scale' layer (or None)",
                ])

                return "\n".join(parts)

            def __str__(self):
                return str(self._computed_current)

            def __add__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current + other_val

            def __radd__(self, other):
                return other + self._computed_current

            def __sub__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current - other_val

            def __rsub__(self, other):
                return other - self._computed_current

            def __mul__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current * other_val

            def __rmul__(self, other):
                return other * self._computed_current

            def __truediv__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current / other_val

            def __rtruediv__(self, other):
                return other / self._computed_current

            def __floordiv__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current // other_val

            def __rfloordiv__(self, other):
                return other // self._computed_current

            def __mod__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current % other_val

            def __rmod__(self, other):
                return other % self._computed_current

            def __pow__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current ** other_val

            def __rpow__(self, other):
                return other ** self._computed_current

            def __neg__(self):
                return -self._computed_current

            def __pos__(self):
                return +self._computed_current

            def __abs__(self):
                return abs(self._computed_current)

            def __eq__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current == other_val

            def __ne__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current != other_val

            def __lt__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current < other_val

            def __le__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current <= other_val

            def __gt__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current > other_val

            def __ge__(self, other):
                other_val = other.current if isinstance(other, self.__class__) else other
                return self._computed_current >= other_val

            def __float__(self):
                return float(self._computed_current)

            def __int__(self):
                return int(self._computed_current)

            def __bool__(self):
                return bool(self._computed_current)

            def __getattr__(self, name):
                return getattr(self._computed_current, name)

        # Override property getters to return smart accessors
        @property
        def pos(self):
            pos_vec = self._compute_current_state()[0]
            return _MouseRigState.SmartPropertyState(self, "pos", pos_vec)

        @property
        def speed(self):
            speed_val = self._compute_current_state()[1]
            return _MouseRigState.SmartPropertyState(self, "speed", speed_val)

        @property
        def direction(self):
            direction_vec = self._compute_current_state()[2]
            return _MouseRigState.SmartPropertyState(self, "direction", direction_vec)

        @property
        def vector(self):
            speed = self._compute_current_state()[1]
            direction = self._compute_current_state()[2]
            return _MouseRigState.SmartPropertyState(self, "vector", direction * speed)

        @property
        def scroll_speed(self):
            scroll_speed_val = self._compute_current_state()[3]
            return _MouseRigState.SmartPropertyState(self, "speed", scroll_speed_val)

        @property
        def scroll_direction(self):
            scroll_direction_vec = self._compute_current_state()[4]
            return _MouseRigState.SmartPropertyState(self, "direction", scroll_direction_vec)

        @property
        def scroll_vector(self):
            scroll_speed = self._compute_current_state()[3]
            scroll_direction = self._compute_current_state()[4]
            return _MouseRigState.SmartPropertyState(self, "vector", scroll_direction * scroll_speed)

        @property
        def scroll(self):
            return _MouseRigState.ScrollPropertyContainer(self)

        def button_prime(self, button: int):
            """Prime a mouse button to press on next movement and release on stop."""
            self._primed_button = button

        def add_stop_callback(self, callback):
            """Add a callback to fire when the frame loop stops"""
            self._stop_callbacks.append(callback)

        def add_scroll_stop_callback(self, callback):
            """Add a callback to fire when scroll stops"""
            self._scroll_stop_callbacks.append(callback)

        def add_move_stop_callback(self, callback):
            """Add a callback to fire when movement stops"""
            self._move_stop_callbacks.append(callback)

        def _fire_move_stop_callbacks(self):
            """Fire and clear movement stop callbacks"""
            for callback in self._move_stop_callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in move stop callback: {e}")
            self._move_stop_callbacks.clear()

        def scroll_stop(self, transition_ms: Optional[float] = None, easing: str = "linear", **kwargs):
            """Stop scrolling only"""
            transition_ms = validate_timing(transition_ms, 'transition_ms', method='scroll_stop')

            config = BuilderConfig()
            all_kwargs = {'easing': easing, **kwargs}
            config.validate_method_kwargs('stop', **all_kwargs)

            scroll_layers = [
                layer for layer, group in self._layer_groups.items()
                if group.input_type == "scroll"
            ]
            for layer in scroll_layers:
                group = self._layer_groups[layer]
                if group.is_base:
                    self._bake_group_to_base(group)

            self._clear_layer_tracking(scroll_layers)
            for layer in scroll_layers:
                del self._layer_groups[layer]
                if layer in self._layer_orders:
                    del self._layer_orders[layer]

            if transition_ms is None or transition_ms == 0:
                self._base_scroll_speed = 0.0
                mouse_scroll_end()
                for callback in self._scroll_stop_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        print(f"Error in scroll stop callback: {e}")
                self._scroll_stop_callbacks.clear()
                if len(self._layer_groups) == 0 and self._base_speed == 0:
                    self._stop_frame_loop()
            else:
                from .builder import ActiveBuilder

                if self._base_scroll_speed != 0:
                    scroll_config = BuilderConfig()
                    scroll_config.property = "speed"
                    scroll_config.input_type = "scroll"
                    scroll_config.layer_name = f"scroll:base.{scroll_config.property}"
                    scroll_config.operator = "to"
                    scroll_config.value = 0
                    scroll_config.over_ms = transition_ms
                    scroll_config.over_easing = easing
                    scroll_builder = ActiveBuilder(scroll_config, self, is_base_layer=True)
                    self.add_builder(scroll_builder)

        def move_stop(self, transition_ms: Optional[float] = None, easing: str = "linear", **kwargs):
            """Stop movement only"""
            transition_ms = validate_timing(transition_ms, 'transition_ms', method='move_stop')

            config = BuilderConfig()
            all_kwargs = {'easing': easing, **kwargs}
            config.validate_method_kwargs('stop', **all_kwargs)

            move_layers = [
                layer for layer, group in self._layer_groups.items()
                if group.input_type != "scroll"
            ]
            for layer in move_layers:
                group = self._layer_groups[layer]
                if group.is_base:
                    self._bake_group_to_base(group)

            self._clear_layer_tracking(move_layers)
            for layer in move_layers:
                del self._layer_groups[layer]
                if layer in self._layer_orders:
                    del self._layer_orders[layer]

            self._primed_button = None

            if transition_ms is None or transition_ms == 0:
                self._base_speed = 0.0
                if len(self._layer_groups) == 0 and self._base_scroll_speed == 0:
                    self._stop_frame_loop()
                cron.after("1ms", self._fire_move_stop_callbacks)
            else:
                from .builder import ActiveBuilder

                if self._base_speed != 0:
                    move_config = BuilderConfig()
                    move_config.property = "speed"
                    move_config.layer_name = f"base.{move_config.property}"
                    move_config.operator = "to"
                    move_config.value = 0
                    move_config.over_ms = transition_ms
                    move_config.over_easing = easing
                    move_builder = ActiveBuilder(move_config, self, is_base_layer=True)
                    self.add_builder(move_builder)

        def bake_all(self):
            """Bake all active mouse movement builders immediately (not scroll)"""
            properties_to_bake = set()
            for group in self._layer_groups.values():
                if getattr(group, 'input_type', 'move') == 'move':
                    properties_to_bake.add(group.property)

            for prop in properties_to_bake:
                if prop == "pos":
                    current_pos = self.pos
                    self._absolute_base_pos = Vec2(current_pos.x, current_pos.y) if hasattr(current_pos, 'x') else current_pos
                    if self._absolute_current_pos is not None:
                        self._absolute_current_pos = Vec2(self._absolute_base_pos.x, self._absolute_base_pos.y)
                elif prop == "speed":
                    current_speed = self.speed
                    self._base_speed = float(current_speed)
                elif prop == "direction":
                    current_direction = self.direction
                    self._base_direction = Vec2(current_direction.x, current_direction.y)
                elif prop == "vector":
                    current_vector = self.vector
                    self._base_speed = current_vector.magnitude()
                    self._base_direction = current_vector.normalized() if self._base_speed > EPSILON else Vec2(1, 0)

            for layer in list(self._layer_groups.keys()):
                group = self._layer_groups.get(layer)
                if group and getattr(group, 'input_type', 'move') == 'move':
                    self.remove_layer(layer, bake=False)

        def bake_scroll_all(self):
            """Bake all active scroll builders immediately (not mouse movement)"""
            properties_to_bake = set()
            for group in self._layer_groups.values():
                if getattr(group, 'input_type', 'move') == 'scroll':
                    properties_to_bake.add(group.property)

            for prop in properties_to_bake:
                if prop == "speed":
                    self._base_scroll_speed = float(self.scroll_speed)
                elif prop == "direction":
                    current_dir = self.scroll_direction
                    self._base_scroll_direction = Vec2(current_dir.x, current_dir.y)
                elif prop == "vector":
                    current_vector = self.scroll_vector
                    mag = current_vector.magnitude()
                    self._base_scroll_speed = mag
                    self._base_scroll_direction = current_vector.normalized() if mag > EPSILON else Vec2(0, 1)

            for layer in list(self._layer_groups.keys()):
                group = self._layer_groups.get(layer)
                if group and getattr(group, 'input_type', 'move') == 'scroll':
                    self.remove_layer(layer, bake=False)

        def reset(self):
            """Reset everything to default state"""
            self._stop_frame_loop()

            self._layer_groups.clear()
            self._layer_orders.clear()
            self._throttle_times.clear()
            self._rate_builder_cache.clear()
            self._debounce_pending.clear()

            self._base_speed = 0.0
            self._base_direction = Vec2(1, 0)
            self._base_scroll_speed = 0.0
            self._base_scroll_direction = Vec2(0, 1)
            self._absolute_base_pos = None
            self._absolute_current_pos = None

            self._subpixel_adjuster.reset()
            self._next_auto_order = 0

            self._stop_callbacks.clear()
            self._scroll_stop_callbacks.clear()
            self._move_stop_callbacks.clear()
            self._primed_button = None

        def trigger_revert(self, layer: str, revert_ms: Optional[float] = None, easing: str = "linear", current_time: Optional[float] = None):
            """Trigger revert on a layer group"""
            if layer in self._layer_groups:
                group = self._layer_groups[layer]

                if current_time is None:
                    current_time = time.perf_counter()

                if group.builders:
                    for builder in group.builders:
                        builder.lifecycle.trigger_revert(current_time, revert_ms, easing)
                else:
                    if not group.is_base and not group._is_reverted_to_zero():
                        from .builder import ActiveBuilder

                        config = BuilderConfig()
                        config.layer_name = layer
                        config.layer_type = group.layer_type
                        config.property = group.property
                        config.mode = group.mode
                        config.input_type = group.input_type
                        config.operator = "to"

                        if is_vec2(group.accumulated_value):
                            config.value = (group.accumulated_value.x, group.accumulated_value.y)
                        else:
                            config.value = group.accumulated_value

                        config.over_ms = 0
                        config.revert_ms = revert_ms if revert_ms is not None else 0
                        config.revert_easing = easing
                        config.is_synchronous = False

                        if is_vec2(group.accumulated_value):
                            group.accumulated_value = Vec2(0, 0)
                        else:
                            group.accumulated_value = 0.0

                        builder = ActiveBuilder(config, self, is_base_layer=False)
                        builder.lifecycle.start(current_time)
                        builder.lifecycle.phase = LifecyclePhase.REVERT
                        builder.lifecycle.phase_start_time = current_time

                        self.add_builder(builder)

                self._ensure_frame_loop_running()

    RigState = _MouseRigState
