"""State management for mouse rig V2

Unified state manager with:
- Base state (baked values)
- Active builders (temporary modifications)
- Queue system
- Frame loop
"""

import time
import math
from typing import Optional, TYPE_CHECKING
from talon import cron, ctrl, settings
from .core import Vec2, SubpixelAdjuster, mouse_move
from .queue import QueueManager
from .lifecycle import Lifecycle, LifecyclePhase, PropertyAnimator
from . import mode_operations

if TYPE_CHECKING:
    from .builder import ActiveBuilder


class RigState:
    """Core state manager for the mouse rig"""

    def __init__(self):
        # Base state (baked values)
        self._absolute_base_pos: Optional[Vec2] = None  # Baked screen position (lazy init - only for pos.to)
        self._base_speed: float = 0.0
        self._base_direction: Vec2 = Vec2(1, 0)

        # Active builders (layer_name -> ActiveBuilder)
        self._active_builders: dict[str, 'ActiveBuilder'] = {}

        # Layer order tracking (layer_name -> order)
        self._layer_orders: dict[str, int] = {}

        # Queue system
        self._queue_manager = QueueManager()

        # Frame loop
        self._frame_loop_job: Optional[cron.CronJob] = None
        self._last_frame_time: Optional[float] = None
        self._subpixel_adjuster = SubpixelAdjuster()
        # Track current screen position with subpixel precision (lazy init - only for pos.to)
        self._absolute_current_pos: Optional[Vec2] = None

        # Throttle tracking (layer -> last execution time)
        self._throttle_times: dict[str, float] = {}

        # Auto-order counter for layers without explicit order
        self._next_auto_order: int = 0

        # Manual mouse movement detection (works in both absolute and relative modes)
        self._last_manual_movement_time: Optional[float] = None
        self._expected_mouse_pos: Optional[tuple[int, int]] = None  # Expected screen position after last rig movement

        # Stop callbacks (fired when frame loop stops)
        self._stop_callbacks: list = []

    def __repr__(self) -> str:
        pos = self.pos
        speed = self.speed
        direction = self.direction
        layers = self.layers

        lines = [
            "RigState:",
            f"  .pos = ({pos.x:.1f}, {pos.y:.1f})",
            f"  .speed = {speed:.1f}",
            f"  .direction = ({direction.x:.2f}, {direction.y:.2f})",
            f"  .direction_cardinal = {self.direction_cardinal or 'None'}",
            f"  .layers = {layers}",
            f"  .base = <BaseState>",
            f"  .layer(name) = <LayerState | None>",
            "",
            "Methods:",
            "  .time_alive(layer) -> float | None",
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.__repr__()

    def _generate_base_layer_name(self) -> str:
        return "__base__"

    def time_alive(self, layer: str) -> Optional[float]:
        """Get time in seconds since builder was created

        Returns None if layer doesn't exist
        """
        if layer in self._active_builders:
            return self._active_builders[layer].time_alive
        return None

    def _handle_user_layer_behavior(self, builder: 'ActiveBuilder', existing: 'ActiveBuilder', behavior: str) -> bool:
        """Handle behavior for existing user layer

        Returns True if handled (early return), False if should continue processing
        """
        layer = builder.config.layer_name

        if behavior == "reset":
            self.remove_builder(layer)
            return False  # Continue processing as new builder
        elif behavior == "extend":
            if existing.lifecycle.hold_ms is not None:
                existing.lifecycle.hold_ms += builder.config.hold_ms or 0
            return True  # Handled, early return
        elif behavior == "throttle":
            throttle_ms = builder.config.behavior_args[0] if builder.config.behavior_args else 0
            if layer in self._throttle_times:
                elapsed = (time.perf_counter() - self._throttle_times[layer]) * 1000
                if elapsed < throttle_ms:
                    return True  # Throttled, early return
            self._throttle_times[layer] = time.perf_counter()
            existing.add_child(builder)
            return True  # Handled, early return
        elif behavior == "ignore":
            return True  # Ignored, early return
        else:
            # Stack or queue - add as child
            existing.add_child(builder)
            return True  # Handled, early return

    def _handle_base_layer_behavior(self, builder: 'ActiveBuilder', behavior: str):
        """Handle behavior for base layer operations"""
        layer = builder.config.layer_name

        if behavior == "reset" and layer == "__base__":
            # For .to() operator, cancel all base builders with same property
            if builder.config.property:
                layers_to_remove = [
                    l for l, b in self._active_builders.items()
                    if l == layer and b.config.property == builder.config.property
                ]
                for l in layers_to_remove:
                    self.remove_builder(l)
        elif behavior == "throttle":
            throttle_ms = builder.config.behavior_args[0] if builder.config.behavior_args else 0
            if layer in self._throttle_times:
                elapsed = (time.perf_counter() - self._throttle_times[layer]) * 1000
                if elapsed < throttle_ms:
                    return  # Early return handled by caller
            self._throttle_times[layer] = time.perf_counter()

    def _handle_instant_completion(self, builder: 'ActiveBuilder', layer: str):
        """Handle builders that complete instantly (no lifecycle)"""
        # For synchronous operations, execute immediately if frame loop isn't running
        if builder.config.is_synchronous and self._frame_loop_job is None:
            builder.execute_synchronous()
            # Synchronous execution already updated state, just cleanup
            if builder.config.is_anonymous():
                del self._active_builders[layer]
                if layer in self._throttle_times:
                    del self._throttle_times[layer]
            return

        # Non-synchronous instant completion (bake the value)
        if builder.config.is_anonymous():
            if builder.config.get_effective_bake():
                self._bake_builder(builder, removing_layer=layer)
            del self._active_builders[layer]
            if layer in self._throttle_times:
                del self._throttle_times[layer]

    def add_builder(self, builder: 'ActiveBuilder'):
        """Add an active builder to state

        For user layers, if layer exists, add as child to existing builder.
        For base layers, operations execute with their configured lifecycle.
        """
        layer = builder.config.layer_name

        # Handle bake operation immediately
        if builder.config.operator == "bake":
            self._bake_property(builder.config.property, layer if not builder.config.is_anonymous() else None)
            return

        # Validate mode consistency for user layers
        if not builder.config.is_anonymous() and layer in self._active_builders:
            existing_builder = self._active_builders[layer]
            existing_mode = existing_builder.config.mode
            new_mode = builder.config.mode

            # Check for mode mixing
            if existing_mode is not None and new_mode is not None and existing_mode != new_mode:
                from .contracts import ConfigError
                raise ConfigError(
                    f"Cannot mix modes on layer '{layer}'.\n"
                    f"Existing mode: '{existing_mode}'\n"
                    f"Attempted mode: '{new_mode}'\n\n"
                    f"Each layer must use a single mode. Either use .reset or use separate layers for different modes:\n"
                    f"  rig.layer('boost').speed.offset.to(100)\n"
                    f"  rig.layer('cap').speed.override.to(200)  # Different layer"
                )

        behavior = builder.config.get_effective_behavior()

        if not builder.config.is_anonymous() and layer in self._active_builders:
            if self._handle_user_layer_behavior(builder, self._active_builders[layer], behavior):
                return

        self._handle_base_layer_behavior(builder, behavior)

        self._active_builders[layer] = builder

        # Track layer order
        if builder.config.order is not None:
            self._layer_orders[layer] = builder.config.order
        elif layer != "__base__":
            if layer not in self._layer_orders:
                self._layer_orders[layer] = self._next_auto_order
                self._next_auto_order += 1

        # Start frame loop if builder has lifecycle
        if not builder.lifecycle.is_complete():
            self._ensure_frame_loop_running()
            return

        # Handle instant completion
        self._handle_instant_completion(builder, layer)

        # After adding builder, check if frame loop should be running
        # (e.g., if layer creates velocity movement even with base speed 0)
        if self._should_frame_loop_be_active():
            self._ensure_frame_loop_running()

    def remove_builder(self, layer: str, bake: bool = False):
        """Remove an active builder"""
        if layer in self._active_builders:
            builder = self._active_builders[layer]

            # If bake=true, merge values into base
            if builder.config.get_effective_bake() or bake:
                self._bake_builder(builder, removing_layer=layer)

            del self._active_builders[layer]

            # Remove order tracking
            if layer in self._layer_orders:
                del self._layer_orders[layer]

            # Clean up throttle tracking
            if layer in self._throttle_times:
                del self._throttle_times[layer]

            # Notify queue system
            queue_key = layer
            if layer == "__base__":
                queue_key = f"__queue_{builder.config.property}_{builder.config.operator}"
            self._queue_manager.on_builder_complete(queue_key)

        # Frame loop will be stopped by _tick_frame after final mouse movement

    def _bake_builder(self, builder: 'ActiveBuilder', removing_layer: Optional[str] = None):
        """Merge builder's final aggregated value into base state

        Args:
            builder: The builder to bake
            removing_layer: Layer being removed (to exclude from active count check)

        Baking applies the layer's contribution to base state:
        - offset mode: add contribution to base
        - override mode: replace base with absolute value
        - scale mode: multiply base by factor
        """
        # If builder has reverted, don't bake (it's already back to base)
        if builder.lifecycle.has_reverted():
            return

        # Get aggregated value (includes own value + children)
        current_value = builder.get_interpolated_value()

        # Get property and mode from builder config
        prop = builder.config.property
        mode = builder.config.mode

        if prop == "vector":
            # Decompose vector into speed and direction
            self._base_speed, self._base_direction = mode_operations.apply_vector_mode(
                mode, current_value, self._base_speed, self._base_direction
            )

        elif prop == "speed":
            self._base_speed = mode_operations.apply_scalar_mode(mode, current_value, self._base_speed)

        elif prop == "direction":
            self._base_direction = mode_operations.apply_direction_mode(mode, current_value, self._base_direction)

        elif prop == "pos":
            if mode == "offset":
                # Offset mode: current_value is an offset vector
                # For relative movement (pos.by), we don't track absolute position
                # Only update if we're in absolute mode (mixed with pos.to)
                if self._absolute_current_pos is not None and self._absolute_base_pos is not None:
                    # Check if animated or instant
                    if builder.lifecycle.over_ms is not None and builder.lifecycle.over_ms > 0:
                        # Was animated - position tracking already moved, just sync base
                        self._absolute_base_pos = Vec2(self._absolute_current_pos.x, self._absolute_current_pos.y)
                    else:
                        # Instant operation - apply offset
                        self._absolute_base_pos = Vec2(self._absolute_base_pos.x + current_value.x, self._absolute_base_pos.y + current_value.y)
                        self._absolute_current_pos = Vec2(self._absolute_base_pos.x, self._absolute_base_pos.y)
            elif mode == "override":
                # Override mode: current_value is absolute position, set base to it
                # Initialize absolute tracking if this is first pos.to
                if self._absolute_base_pos is None or self._absolute_current_pos is None:
                    current_screen_pos = Vec2(*ctrl.mouse_pos())
                    self._absolute_base_pos = current_screen_pos
                    self._absolute_current_pos = current_screen_pos

                if self._base_speed == 0:
                    # No velocity - snap to exact position
                    self._absolute_base_pos = Vec2(current_value.x, current_value.y)
                    self._absolute_current_pos = Vec2(current_value.x, current_value.y)
                else:
                    # Velocity active - use current internal position to avoid jump
                    self._absolute_base_pos = Vec2(self._absolute_current_pos.x, self._absolute_current_pos.y)
            elif mode == "scale":
                # Scale mode: current_value is multiplier, scale base position
                # Only apply if tracking absolute position
                if self._absolute_base_pos is not None and self._absolute_current_pos is not None:
                    self._absolute_base_pos = Vec2(self._absolute_base_pos.x * current_value, self._absolute_base_pos.y * current_value)
                    self._absolute_current_pos = Vec2(self._absolute_base_pos.x, self._absolute_base_pos.y)

            # For instant position changes, apply manually only if frame loop won't handle it
            # Exclude the builder being removed from the active count
            active_count = len(self._active_builders)
            if removing_layer and removing_layer in self._active_builders:
                active_count -= 1

            will_be_active = self._has_movement() or active_count > 0
            is_relative = builder.config.movement_type == "relative"
            if not will_be_active and not is_relative and self._absolute_base_pos is not None:
                mouse_move(int(self._absolute_base_pos.x), int(self._absolute_base_pos.y))

        if self._should_frame_loop_be_active():
            self._ensure_frame_loop_running()

    def _bake_property(self, property_name: str, layer: Optional[str] = None):
        """Bake current computed value of a property into base state

        Args:
            property_name: The property to bake ("speed", "direction", "pos")
            layer: Optional layer to bake from a specific builder. If None, bakes computed state.
        """
        if layer:
            # Bake from a specific layer - remove it and bake its value
            if layer in self._active_builders:
                builder = self._active_builders[layer]
                if builder.config.property == property_name:
                    # Force bake this builder
                    self._bake_builder(builder)
                    # Remove the builder
                    del self._active_builders[layer]
        else:
            # Bake current computed value for this property
            current_value = getattr(self, property_name)

            if property_name == "vector":
                self._base_speed = current_value.magnitude()
                self._base_direction = current_value.normalized()
            elif property_name == "speed":
                self._base_speed = current_value
            elif property_name == "direction":
                self._base_direction = current_value
            elif property_name == "pos":
                self._absolute_base_pos = current_value

            # Remove all anonymous layer builders affecting this property
            layers_to_remove = [
                l for l, b in self._active_builders.items()
                if b.config.is_anonymous() and b.config.property == property_name
            ]
            for l in layers_to_remove:
                if l in self._active_builders:
                    del self._active_builders[l]

    def _compute_current_state(self) -> tuple[Vec2, float, Vec2, bool]:
        """Compute current state by applying all active layers to base.

        Computation order:
        1. Start with base values
        2. Process base layer operations
        3. Process user layers (in order)

        Returns:
            (position, speed, direction, pos_is_override)
            pos_is_override is True if any position builder used override mode
        """
        # Start with base
        pos = Vec2(self._absolute_base_pos.x, self._absolute_base_pos.y) if self._absolute_base_pos else Vec2(0, 0)
        speed = self._base_speed
        direction = Vec2(self._base_direction.x, self._base_direction.y)
        pos_is_override = False

        # Separate builders by layer type
        base_builders = []   # Anonymous layers (base operations)
        user_builders = []   # User layers

        for layer_name, builder in self._active_builders.items():
            if layer_name == "__base__":
                base_builders.append(builder)
            else:
                user_builders.append(builder)

        # Sort user layers by order
        def get_layer_order(builder: 'ActiveBuilder') -> int:
            layer_name = builder.config.layer_name
            return self._layer_orders.get(layer_name, 999999)  # Unordered layers go last

        user_builders = sorted(user_builders, key=get_layer_order)

        # Process in layer order: base → user layers
        for builder in base_builders:
            pos, speed, direction, override = self._apply_layer(builder, pos, speed, direction)
            pos_is_override = pos_is_override or override

        for builder in user_builders:
            pos, speed, direction, override = self._apply_layer(builder, pos, speed, direction)
            pos_is_override = pos_is_override or override

        return (pos, speed, direction, pos_is_override)

    def _apply_layer(
        self,
        builder: 'ActiveBuilder',
        pos: Vec2,
        speed: float,
        direction: Vec2
    ) -> tuple[Vec2, float, Vec2, bool]:
        """Apply a layer's operations

        Args:
            builder: The builder to apply
            pos, speed, direction: Current accumulated state values

        Returns:
            Updated (pos, speed, direction, pos_is_override)
            pos_is_override is True if this layer used override mode for position

        Mode behavior:
        - offset: current_value is a CONTRIBUTION (added to accumulated)
        - override: current_value is ABSOLUTE (replaces accumulated)
        - scale: current_value is a MULTIPLIER (multiplies accumulated)
        """
        prop = builder.config.property
        mode = builder.config.mode
        current_value = builder.get_interpolated_value()
        pos_is_override = False

        if prop == "speed":
            speed = mode_operations.apply_scalar_mode(mode, current_value, speed)

        elif prop == "direction":
            direction = mode_operations.apply_direction_mode(mode, current_value, direction)

        elif prop == "vector":
            speed, direction = mode_operations.apply_vector_mode(mode, current_value, speed, direction)

        elif prop == "pos":
            pos = mode_operations.apply_position_mode(mode, current_value, pos)
            pos_is_override = (mode == "override")

        return pos, speed, direction, pos_is_override

    def _compute_velocity(self) -> tuple[float, Vec2]:
        """Compute current velocity from speed and direction builders.

        Returns:
            (speed, direction) tuple
        """
        speed = self._base_speed
        direction = Vec2(self._base_direction.x, self._base_direction.y)

        # Separate builders by layer type
        base_builders = []
        user_builders = []

        for layer_name, builder in self._active_builders.items():
            if builder.config.property in ("speed", "direction", "vector"):
                if layer_name == "__base__":
                    base_builders.append(builder)
                else:
                    user_builders.append(builder)

        # Sort user layers by order
        def get_layer_order(builder: 'ActiveBuilder') -> int:
            layer_name = builder.config.layer_name
            return self._layer_orders.get(layer_name, 999999)

        user_builders = sorted(user_builders, key=get_layer_order)

        # Apply all velocity builders
        for builder in base_builders + user_builders:
            prop = builder.config.property
            mode = builder.config.mode
            current_value = builder.get_interpolated_value()

            if prop == "speed":
                speed = mode_operations.apply_scalar_mode(mode, current_value, speed)
            elif prop == "direction":
                direction = mode_operations.apply_direction_mode(mode, current_value, direction)
            elif prop == "vector":
                speed, direction = mode_operations.apply_vector_mode(mode, current_value, speed, direction)

        return speed, direction

    def _apply_velocity_movement(self, speed: float, direction: Vec2):
        """Apply velocity-based movement to absolute position (only used in absolute mode)"""
        if speed == 0:
            return

        if self._absolute_current_pos is None:
            return  # No absolute tracking, skip velocity updates

        velocity = direction * speed
        dx_int, dy_int = self._subpixel_adjuster.adjust(velocity.x, velocity.y)
        self._absolute_current_pos = Vec2(self._absolute_current_pos.x + dx_int, self._absolute_current_pos.y + dy_int)

    def _compute_velocity_delta(self) -> Vec2:
        """Compute velocity contribution as delta (speed + direction)

        Returns:
            Delta vector from velocity this frame
        """
        speed, direction = self._compute_velocity()
        if speed == 0:
            return Vec2(0, 0)

        velocity = direction * speed
        dx, dy = self._subpixel_adjuster.adjust(velocity.x, velocity.y)
        return Vec2(dx, dy)

    def _process_position_builders(self) -> tuple[bool, Optional[Vec2], Vec2, list]:
        """Process all position builders and gather their contributions

        Returns:
            (has_absolute_position, absolute_target, relative_delta, relative_position_updates)
            - has_absolute_position: True if any pos.to() builder exists
            - absolute_target: Target position from pos.to() (if exists)
            - relative_delta: Accumulated delta from all pos.by() builders
            - relative_position_updates: List of (builder, new_value, new_int_value) for tracking updates
        """
        has_absolute_position = False
        absolute_target = None
        relative_delta = Vec2(0, 0)
        relative_position_updates = []

        for layer_name, builder in self._active_builders.items():
            if builder.config.property != "pos":
                continue

            if builder.config.movement_type == "absolute":
                # pos.to() - absolute positioning
                has_absolute_position = True
                absolute_target = builder.get_interpolated_value()
                # Note: only one absolute position builder should be active at a time
                # If multiple exist, last one wins (matches current override behavior)
            else:
                # pos.by() - pure relative delta
                current_interpolated = builder.get_interpolated_value()

                # Initialize tracking attributes if needed
                if not hasattr(builder, '_last_emitted_relative_pos'):
                    builder._last_emitted_relative_pos = Vec2(0, 0)
                if not hasattr(builder, '_total_emitted_int'):
                    builder._total_emitted_int = Vec2(0, 0)

                # Compute integer delta accounting for accumulated error
                target_total_int = Vec2(round(current_interpolated.x), round(current_interpolated.y))
                actual_delta_int = target_total_int - builder._total_emitted_int

                relative_delta += Vec2(actual_delta_int.x, actual_delta_int.y)

                # The new total is what we've already emitted plus what we're about to emit
                new_total_emitted = builder._total_emitted_int + actual_delta_int

                # Store update to apply after builder removal check
                relative_position_updates.append((builder, current_interpolated, new_total_emitted))

        return has_absolute_position, absolute_target, relative_delta, relative_position_updates

    def _emit_mouse_movement(self, has_absolute_position: bool, absolute_target: Optional[Vec2], frame_delta: Vec2):
        """Emit mouse movement based on accumulated deltas

        Args:
            has_absolute_position: True if using absolute positioning (pos.to)
            absolute_target: Target position for absolute mode
            frame_delta: Accumulated delta from velocity and relative position builders
        """
        if has_absolute_position:
            final_pos = absolute_target + frame_delta
            self._absolute_current_pos = final_pos
            from .core import mouse_move
            new_x = int(round(final_pos.x))
            new_y = int(round(final_pos.y))
            current_x, current_y = ctrl.mouse_pos()
            if new_x != current_x or new_y != current_y:
                mouse_move(new_x, new_y)
                self._expected_mouse_pos = (new_x, new_y)
        else:
            if frame_delta.x != 0 or frame_delta.y != 0:
                from .core import mouse_move_relative
                mouse_move_relative(round(frame_delta.x), round(frame_delta.y))
                self._expected_mouse_pos = ctrl.mouse_pos()

    def _update_relative_position_tracking(self, relative_position_updates: list, completed_layers: set):
        """Update tracking for relative position builders after removal

        Args:
            relative_position_updates: List of (builder, new_value, new_int_value) to update
            completed_layers: Set of layer names that were completed and removed
        """
        for builder, new_value, new_int_value in relative_position_updates:
            # Only update builders that are still active (weren't completed)
            if builder.config.layer_name not in completed_layers:
                builder._last_emitted_relative_pos = new_value
                builder._total_emitted_int = new_int_value

    def _sync_to_manual_mouse_movement(self) -> bool:
        """Detect and sync to manual mouse movements by the user

        Works in both absolute and relative modes by tracking expected position
        after each rig movement and comparing it to actual position before next movement.

        Returns:
            True if we should skip rig movement (manual movement detected or in timeout), False otherwise
        """
        # Only perform manual movement detection if enabled
        if not settings.get("user.mouse_rig_pause_on_manual_movement", True):
            return False

        # Check if we're still in timeout period after manual movement
        if self._last_manual_movement_time is not None:
            timeout_ms = settings.get("user.mouse_rig_manual_movement_timeout_ms", 200)
            elapsed_ms = (time.perf_counter() - self._last_manual_movement_time) * 1000
            if elapsed_ms < timeout_ms:
                return True  # Still in timeout, skip rig movement
            else:
                # Timeout expired, allow rig to take control again
                self._last_manual_movement_time = None
                self._expected_mouse_pos = None  # Reset tracking

        # If we have an expected position from last movement, check if it matches actual
        if self._expected_mouse_pos is not None:
            current_x, current_y = ctrl.mouse_pos()
            expected_x, expected_y = self._expected_mouse_pos

            # If mouse position differs from expected, user moved it manually
            if current_x != expected_x or current_y != expected_y:
                # Sync internal tracking to manual position
                if self._absolute_current_pos is not None:
                    # In absolute mode, update tracked positions
                    manual_pos = Vec2(current_x, current_y)
                    self._absolute_current_pos = manual_pos
                    self._absolute_base_pos = manual_pos

                # Record time of manual movement
                self._last_manual_movement_time = time.perf_counter()
                self._expected_mouse_pos = None  # Reset until next rig movement

                return True

        return False

    def _tick_frame(self):
        """Main frame loop tick - processes all builders and emits mouse movement

        Flow:
        1. Check for manual mouse movement (absolute mode only)
        2. Advance all builder lifecycles
        3. Compute velocity delta (speed + direction)
        4. Process position builders (absolute vs relative)
        5. Emit mouse movement (absolute or relative)
        6. Remove completed builders
        7. Update tracking for remaining builders
        8. Execute callbacks and stop if done
        """
        current_time, dt = self._calculate_delta_time()
        if dt is None:
            return

        # Check for manual movement (only works in absolute mode)
        manual_movement_detected = self._sync_to_manual_mouse_movement()
        phase_transitions = self._advance_all_builders(current_time)

        if manual_movement_detected:
            self._remove_completed_builders(current_time)
            self._execute_phase_callbacks(phase_transitions)
            self._stop_frame_loop_if_done()
            return

        # Accumulate all movement contributions
        frame_delta = Vec2(0, 0)

        # 1. Add velocity contribution (always relative)
        frame_delta += self._compute_velocity_delta()

        # 2. Process position builders (absolute vs relative)
        has_absolute_position, absolute_target, relative_delta, relative_position_updates = self._process_position_builders()
        frame_delta += relative_delta

        # 3. Emit mouse movement (absolute or relative mode)
        self._emit_mouse_movement(has_absolute_position, absolute_target, frame_delta)

        # 4. Update tracking BEFORE checking for completion to avoid double-emission
        # We update unconditionally here since the deltas were already emitted
        for builder, new_value, new_int_value in relative_position_updates:
            builder._last_emitted_relative_pos = new_value
            builder._total_emitted_int = new_int_value

        # 5. Remove completed builders (may emit final deltas)
        completed_layers = self._remove_completed_builders(current_time)

        # 6. Execute callbacks and stop if done
        self._execute_phase_callbacks(phase_transitions)
        self._stop_frame_loop_if_done()

    def _calculate_delta_time(self) -> tuple[float, Optional[float]]:
        """Calculate time since last frame.

        Returns:
            (current_time, dt) where dt is None on first frame
        """
        now = time.perf_counter()
        if self._last_frame_time is None:
            self._last_frame_time = now
            return (now, None)

        dt = now - self._last_frame_time
        self._last_frame_time = now
        return (now, dt)

    def _advance_all_builders(self, current_time: float) -> list[tuple['ActiveBuilder', str]]:
        """Advance all builders and track phase transitions.

        Args:
            current_time: Current timestamp from perf_counter() (captured once per frame)

        Returns:
            List of (builder, completed_phase) tuples for callbacks
        """
        phase_transitions = []

        for layer, builder in list(self._active_builders.items()):
            old_phase = builder.lifecycle.phase
            builder.advance(current_time)
            new_phase = builder.lifecycle.phase

            if old_phase != new_phase and old_phase is not None:
                phase_transitions.append((builder, old_phase))

        return phase_transitions

    def _remove_completed_builders(self, current_time: float) -> set[str]:
        """Remove builders that are no longer active

        Args:
            current_time: Current timestamp from perf_counter() (captured once per frame)

        Returns:
            Set of layer names that were completed and removed
        """
        completed = []

        for layer, builder in list(self._active_builders.items()):
            # Check if already marked for removal (e.g., group_lifecycle completed)
            if builder._marked_for_removal:
                completed.append(layer)
                continue
            
            # Final advance to ensure target achieved
            still_active = builder.advance(current_time)

            if not still_active:
                # For relative position builders, emit any remaining delta after final advance
                if (builder.config.property == "pos" and
                    builder.config.movement_type == "relative" and
                    hasattr(builder, '_total_emitted_int')):

                    # Get final value after completion
                    final_value = builder.get_interpolated_value()
                    final_target_int = Vec2(round(final_value.x), round(final_value.y))

                    # Emit any remaining delta that wasn't captured in main tick
                    # Compare integer targets to avoid rounding errors
                    final_delta_int = final_target_int - builder._total_emitted_int

                    if final_delta_int.x != 0 or final_delta_int.y != 0:
                        from .core import mouse_move_relative
                        mouse_move_relative(int(final_delta_int.x), int(final_delta_int.y))

                completed.append(layer)

        for layer in completed:
            self.remove_builder(layer)

        return set(completed)

    def _execute_phase_callbacks(self, phase_transitions: list[tuple['ActiveBuilder', str]]):
        """Execute callbacks for completed phases"""
        for builder, completed_phase in phase_transitions:
            builder.lifecycle.execute_callbacks(completed_phase)

    def _stop_frame_loop_if_done(self):
        """Stop frame loop if no longer needed"""
        if not self._should_frame_loop_be_active():
            self._stop_frame_loop()


    def _ensure_frame_loop_running(self):
        """Start frame loop if not already running"""
        if self._frame_loop_job is None:
            frame_interval = settings.get("user.mouse_rig_frame_interval", 16)
            self._frame_loop_job = cron.interval(f"{frame_interval}ms", self._tick_frame)
            self._last_frame_time = None
            # Sync to actual mouse position only if we have absolute position builders
            has_absolute_builder = any(
                builder.config.property == "pos" and builder.config.movement_type == "absolute"
                for builder in self._active_builders.values()
            )
            if has_absolute_builder:
                current_mouse = Vec2(*ctrl.mouse_pos())
                self._absolute_current_pos = current_mouse
                self._absolute_base_pos = current_mouse

    def _stop_frame_loop(self):
        """Stop the frame loop"""
        if self._frame_loop_job is not None:
            cron.cancel(self._frame_loop_job)
            self._frame_loop_job = None
            self._last_frame_time = None
            self._subpixel_adjuster.reset()
            self._expected_mouse_pos = None  # Clear expected position tracking

            # Only sync position if we're tracking absolute coordinates
            if self._absolute_current_pos is not None:
                current_mouse = Vec2(*ctrl.mouse_pos())
                self._absolute_current_pos = current_mouse
                # Only update base if it's significantly different from current mouse
                # This handles manual mouse movements while preserving exact baked positions
                if self._absolute_base_pos is not None:
                    diff = abs(current_mouse.x - self._absolute_base_pos.x) + abs(current_mouse.y - self._absolute_base_pos.y)
                    if diff > 2:  # More than 2 pixels difference suggests manual movement
                        self._absolute_base_pos = current_mouse

            # Execute stop callbacks when frame loop actually stops
            for callback in self._stop_callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in stop callback: {e}")
            self._stop_callbacks.clear()

    def _has_movement(self) -> bool:
        """Check if there's any movement happening (base speed or velocity layers)"""
        # Fast path: base speed is non-zero
        if self._base_speed != 0:
            return True

        # Check if any velocity-affecting builders exist
        # If they do, they could create movement even with base speed 0
        for builder in self._active_builders.values():
            prop = builder.config.property
            if prop in ("speed", "direction", "vector"):
                # For speed/vector with offset mode, they add to velocity
                # For direction, it only matters if speed > 0
                if prop in ("speed", "vector"):
                    return True

        return False

    def _should_frame_loop_be_active(self) -> bool:
        """Check if frame loop should be running (movement or animating builders)

        Frame loop runs when:
        1. There's velocity movement (speed > 0), OR
        2. Any builder has an incomplete lifecycle (in OVER, HOLD, or REVERT phase)

        Frame loop stops when:
        - No velocity AND all builders have completed their lifecycle
        """
        if self._has_movement():
            return True

        # Check if any builder has an incomplete lifecycle
        for builder in self._active_builders.values():
            if not builder.lifecycle.is_complete():
                return True

        return False

    def _get_cardinal_direction(self, direction: Vec2) -> Optional[str]:
        """Get cardinal/intercardinal direction name from direction vector

        Returns one of: "right", "left", "up", "down",
                       "up_right", "up_left", "down_right", "down_left"
        or None if direction is zero vector.
        """
        x, y = direction.x, direction.y

        # Handle zero vector
        if x == 0 and y == 0:
            return None

        # Threshold for pure cardinal vs intercardinal
        # tan(67.5 degrees) ≈ 2.414, which is halfway between pure cardinal (90 degrees) and diagonal (45 degrees)
        # This means directions within ±22.5 degrees of an axis are considered pure cardinal
        threshold = 2.414

        # Pure cardinal directions (within 22.5 degrees of axis)
        if abs(x) > abs(y) * threshold:
            return "right" if x > 0 else "left"
        if abs(y) > abs(x) * threshold:
            return "up" if y < 0 else "down"

        # Intercardinal/diagonal directions
        if x > 0 and y < 0:
            return "up_right"
        elif x < 0 and y < 0:
            return "up_left"
        elif x > 0 and y > 0:
            return "down_right"
        elif x < 0 and y > 0:
            return "down_left"

        # Fallback (shouldn't happen with normalized vectors)
        return "right"

    # Public API for reading state
    @property
    def pos(self) -> Vec2:
        """Current computed position"""
        return self._compute_current_state()[0]

    @property
    def speed(self) -> float:
        """Current computed speed"""
        return self._compute_current_state()[1]

    @property
    def direction(self) -> Vec2:
        """Current computed direction"""
        return self._compute_current_state()[2]

    @property
    def vector(self) -> Vec2:
        """Current computed velocity vector (speed * direction)"""
        speed = self.speed
        direction = self.direction
        return direction * speed

    @property
    def direction_cardinal(self) -> Optional[str]:
        """Current direction as cardinal/intercardinal string

        Returns one of: "right", "left", "up", "down",
                       "up_right", "up_left", "down_right", "down_left"
        or None if direction is zero vector.
        """
        direction = self.direction
        return self._get_cardinal_direction(direction)

    @property
    def layers(self) -> list[str]:
        """List of active user layers (excludes anonymous)

        Returns a list of layer names for currently active user layers.
        Anonymous (base) layers are excluded.

        Example:
            rig.state.layers  # ["sprint", "drift"]
        """
        return [layer for layer, builder in self._active_builders.items()
                if not builder.config.is_anonymous()]

    # Layer state access
    class LayerState:
        """State information for a specific layer"""
        def __init__(self, builder: 'ActiveBuilder'):
            self._builder = builder

        def __repr__(self) -> str:
            builder = self._builder
            lifecycle = builder.lifecycle

            # Format values based on type
            def format_value(val):
                if isinstance(val, Vec2):
                    return f"Vec2({val.x:.1f}, {val.y:.1f})"
                elif isinstance(val, float):
                    return f"{val:.1f}"#
                else:
                    return str(val)

            # Build parts list
            parts = [
                f"prop={builder.config.property}",
                f"mode={builder.config.mode}",
                f"current_value={format_value(builder.get_interpolated_value())}",
                f"target_value={format_value(builder.target_value)}",
                f"time_alive={builder.time_alive:.2f}s",
            ]

            # Add timing info if present
            if lifecycle.over_ms:
                parts.append(f"over_ms={lifecycle.over_ms}")
            if lifecycle.hold_ms:
                parts.append(f"hold_ms={lifecycle.hold_ms}")
            if lifecycle.revert_ms:
                parts.append(f"revert_ms={lifecycle.revert_ms}")

            # Add children count if non-zero
            children_count = len(builder.children)
            if children_count > 0:
                parts.append(f"children={children_count}")

            return f"LayerState('{builder.config.layer_name}', {', '.join(parts)})"

        def __str__(self) -> str:
            return self.__repr__()

        @property
        def prop(self) -> str:
            """What property this layer is affecting: 'speed', 'direction', 'pos'"""
            return self._builder.config.property

        @property
        def mode(self) -> str:
            """Mode of this layer: 'offset', 'override', 'scale'"""
            return self._builder.config.mode

        @property
        def current_value(self):
            """Current aggregated value (includes children) - always fresh"""
            return self._builder.get_interpolated_value()

        @property
        def target_value(self):
            """Target value this layer is moving toward"""
            return self._builder.target_value

        @property
        def time_alive(self) -> float:
            """Time in seconds since this builder was created"""
            return self._builder.time_alive

        def __getattr__(self, name: str):
            """Provide helpful error messages for invalid attributes"""
            from .contracts import VALID_LAYER_STATE_ATTRS

            raise AttributeError(
                f"LayerState has no attribute '{name}'. "
                f"Available attributes: {', '.join(VALID_LAYER_STATE_ATTRS)}"
            )

    def layer(self, layer_name: str) -> Optional['RigState.LayerState']:
        """Get state information for a specific ---layer

        Returns a LayerState object with the layer's current state, or None if not active.

        Example:
            sprint = rig.state.layer("sprint")
            if sprint:
                print(f"Sprint speed: {sprint.speed}")
                print(f"Phase: {sprint.phase}")
        """
        if layer_name not in self._active_builders:
            return None

        builder = self._active_builders[layer_name]
        return RigState.LayerState(builder)

    # Base state access
    class BaseState:
        def __init__(self, rig_state: 'RigState'):
            self._rig_state = rig_state

        def __repr__(self) -> str:
            pos = self.pos
            speed = self.speed
            direction = self.direction

            lines = [
                "BaseState:",
                f"  .pos = ({pos.x:.1f}, {pos.y:.1f})",
                f"  .speed = {speed:.1f}",
                f"  .direction = ({direction.x:.2f}, {direction.y:.2f})",
            ]
            return "\n".join(lines)

        def __str__(self) -> str:
            return self.__repr__()

        @property
        def pos(self) -> Vec2:
            return self._rig_state._absolute_base_pos if self._rig_state._absolute_base_pos else Vec2(0, 0)

        @property
        def speed(self) -> float:
            return self._rig_state._base_speed

        @property
        def direction(self) -> Vec2:
            return self._rig_state._base_direction

        @property
        def vector(self) -> Vec2:
            """Base velocity vector (speed * direction)"""
            return self._rig_state._base_direction * self._rig_state._base_speed

    @property
    def base(self) -> 'RigState.BaseState':
        """Access to base (baked) state only"""
        return RigState.BaseState(self)

    def add_stop_callback(self, callback):
        """Add a callback to fire when the frame loop stops"""
        self._stop_callbacks.append(callback)

    def stop(self, transition_ms: Optional[float] = None, easing: str = "linear", **kwargs):
        """Stop everything: bake state, clear effects, decelerate to 0

        This matches v1 behavior:
        1. Bake current computed state into base
        2. Clear all active builders (effects)
        3. Set speed to 0 (with optional smooth deceleration)
        """
        # Validate arguments
        from .contracts import BuilderConfig, ConfigError, validate_timing
        transition_ms = validate_timing(transition_ms, 'transition_ms')

        config = BuilderConfig()
        all_kwargs = {'easing': easing, **kwargs}
        config.validate_method_kwargs('stop', **all_kwargs)

        # 1. Bake all active builders into base
        for layer in list(self._active_builders.keys()):
            builder = self._active_builders[layer]
            if not builder.lifecycle.has_reverted():
                self._bake_builder(builder)

        # 2. Clear all active builders and layer tracking
        self._active_builders.clear()
        self._layer_orders.clear()
        self._throttle_times.clear()

        # 3. Decelerate speed to 0
        if transition_ms is None or transition_ms == 0:
            # Immediate stop
            self._base_speed = 0.0
            # Stop frame loop if no active builders
            if len(self._active_builders) == 0:
                self._stop_frame_loop()
        else:
            # Smooth deceleration - create base layer builder
            from .builder import ActiveBuilder
            from .contracts import BuilderConfig

            config = BuilderConfig()
            config.layer_name = self._generate_base_layer_name()
            config.property = "speed"
            config.operator = "to"
            config.value = 0
            config.over_ms = transition_ms
            config.over_easing = easing

            builder = ActiveBuilder(config, self, is_anonymous=True)
            self._active_builders[config.layer_name] = builder
            self._ensure_frame_loop_running()

    def reverse(self, transition_ms: Optional[float] = None):
        """Reverse direction (180 degrees turn)"""
        # This will be implemented via builder in builder.py
        pass

    def bake_all(self):
        """Bake all active builders immediately"""
        for layer in list(self._active_builders.keys()):
            self.remove_builder(layer, bake=True)

    def trigger_revert(self, layer: str, revert_ms: Optional[float] = None, easing: str = "linear", current_time: Optional[float] = None):
        """Trigger revert on builder tree

        Strategy:
        1. Capture current aggregated value from all children
        2. Clear all children (bake the aggregate)
        3. Create group lifecycle that reverses from aggregate to neutral

        Args:
            layer: Layer name to revert
            revert_ms: Duration in milliseconds for the revert
            easing: Easing function for the revert
            current_time: Current timestamp from perf_counter() (if called from frame loop)
        """
        if layer in self._active_builders:
            builder = self._active_builders[layer]

            # Capture current aggregated value
            current_value = builder.get_interpolated_value()

            # Get base value (neutral/zero for the property type)
            # Use builder's own config since children might be empty after first revert
            if builder.config.property == "speed":
                base_value = 0
            elif builder.config.property == "direction":
                base_value = builder.base_value  # Original direction
            elif builder.config.property == "pos":
                base_value = Vec2(0, 0)  # Zero offset
            elif builder.config.property == "vector":
                base_value = Vec2(0, 0)  # Zero velocity
            else:
                base_value = 0

            # Create group lifecycle for coordinated revert
            builder.group_lifecycle = Lifecycle(is_user_layer=not builder.is_anonymous)
            builder.group_lifecycle.over_ms = 0  # Skip over phase
            builder.group_lifecycle.hold_ms = 0  # Skip hold phase
            builder.group_lifecycle.revert_ms = revert_ms if revert_ms is not None else 0
            builder.group_lifecycle.revert_easing = easing
            builder.group_lifecycle.phase = LifecyclePhase.REVERT
            builder.group_lifecycle.phase_start_time = current_time if current_time is not None else time.perf_counter()

            # Store aggregate values for animation
            builder.group_base_value = base_value
            builder.group_target_value = current_value

            # Clear all children - we'll revert as a single coordinated unit
            builder.children = []
