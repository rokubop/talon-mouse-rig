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
from talon import cron, ctrl
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
        self._base_pos: Vec2 = Vec2(*ctrl.mouse_pos())
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
        self._last_position_offset: Vec2 = Vec2(0, 0)
        # Track our internal position with subpixel precision
        self._internal_pos: Vec2 = Vec2(*ctrl.mouse_pos())

        # Throttle tracking (layer -> last execution time)
        self._throttle_times: dict[str, float] = {}

        # Auto-order counter for layers without explicit order
        self._next_auto_order: int = 0

        # Manual mouse movement timeout
        self._last_manual_movement_time: Optional[float] = None
        self._manual_movement_timeout_ms: float = 200  # Default 200ms delay
    def _generate_base_layer_name(self) -> str:
        """Return base layer name"""
        return "__base__"

    def _generate_final_layer_name(self) -> str:
        """Return final layer name"""
        return "__final__"

    def time_alive(self, layer: str) -> Optional[float]:
        """Get time in seconds since builder was created

        Returns None if layer doesn't exist
        """
        if layer in self._active_builders:
            return self._active_builders[layer].time_alive()
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
        """Handle behavior for base/final layer operations"""
        layer = builder.config.layer_name

        if behavior == "reset" and layer in ("__base__", "__final__"):
            # For .to() operator, cancel all base/final builders with same property
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
        For base/final layers, operations execute with their configured lifecycle.
        """
        layer = builder.config.layer_name

        # Handle bake operation immediately
        if builder.config.operator == "bake":
            self._bake_property(builder.config.property, layer if not builder.config.is_anonymous() and layer != "__final__" else None)
            return

        # Validate mode consistency for user layers
        if not builder.config.is_anonymous() and layer != "__final__" and layer in self._active_builders:
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

        if not builder.config.is_anonymous() and layer != "__final__" and layer in self._active_builders:
            if self._handle_user_layer_behavior(builder, self._active_builders[layer], behavior):
                return

        self._handle_base_layer_behavior(builder, behavior)

        self._active_builders[layer] = builder

        # Track layer order
        if builder.config.order is not None:
            self._layer_orders[layer] = builder.config.order
        elif layer not in ("__base__", "__final__"):
            if layer not in self._layer_orders:
                self._layer_orders[layer] = self._next_auto_order
                self._next_auto_order += 1

        # Start frame loop if builder has lifecycle
        if not builder.lifecycle.is_complete():
            self._ensure_frame_loop_running()
            return

        # Handle instant completion
        self._handle_instant_completion(builder, layer)

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
            if layer in ("__base__", "__final__"):
                queue_key = f"__queue_{builder.config.property}_{builder.config.operator}"
            self._queue_manager.on_builder_complete(queue_key)

        # Frame loop will be stopped by _update_frame after final mouse movement

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
        current_value = builder.get_current_value()

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
                # Offset mode: current_value is an offset vector, add to base position
                # Check if animated or instant
                if builder.lifecycle.over_ms is not None and builder.lifecycle.over_ms > 0:
                    # Was animated - position tracking already moved, just sync base
                    self._base_pos = Vec2(self._internal_pos.x, self._internal_pos.y)
                else:
                    # Instant operation - apply offset
                    self._base_pos = Vec2(self._base_pos.x + current_value.x, self._base_pos.y + current_value.y)
                    self._internal_pos = Vec2(self._base_pos.x, self._base_pos.y)
            elif mode == "override":
                # Override mode: current_value is absolute position, set base to it
                if self._base_speed == 0:
                    # No velocity - snap to exact position
                    self._base_pos = Vec2(current_value.x, current_value.y)
                    self._internal_pos = Vec2(current_value.x, current_value.y)
                else:
                    # Velocity active - use current internal position to avoid jump
                    self._base_pos = Vec2(self._internal_pos.x, self._internal_pos.y)
            elif mode == "scale":
                # Scale mode: current_value is multiplier, scale base position
                self._base_pos = Vec2(self._base_pos.x * current_value, self._base_pos.y * current_value)
                self._internal_pos = Vec2(self._base_pos.x, self._base_pos.y)

            # Reset position offset tracking
            self._last_position_offset = Vec2(0, 0)

            # For instant position changes, apply manually only if frame loop won't handle it
            # Exclude the builder being removed from the active count
            active_count = len(self._active_builders)
            if removing_layer and removing_layer in self._active_builders:
                active_count -= 1

            will_be_active = self._has_movement() or active_count > 0
            if not will_be_active:
                mouse_move(int(self._base_pos.x), int(self._base_pos.y))

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
                self._base_pos = current_value

            # Remove all anonymous layer builders affecting this property
            layers_to_remove = [
                l for l, b in self._active_builders.items()
                if b.config.is_anonymous() and b.config.property == property_name
            ]
            for l in layers_to_remove:
                if l in self._active_builders:
                    del self._active_builders[l]

    def _compute_current_state(self) -> tuple[Vec2, float, Vec2]:
        """Compute current state by applying all active layers to base.

        Computation order:
        1. Start with base values
        2. Process base layer operations
        3. Process user layers (in order)
        4. Process final layer operations

        Returns:
            (position, speed, direction)
        """
        # Start with base
        pos = Vec2(self._base_pos.x, self._base_pos.y)
        speed = self._base_speed
        direction = Vec2(self._base_direction.x, self._base_direction.y)

        # Separate builders by layer type
        base_builders = []   # Anonymous layers (base operations)
        user_builders = []   # User layers
        final_builders = []  # __final__ layer

        for layer_name, builder in self._active_builders.items():
            if layer_name == "__base__":
                base_builders.append(builder)
            elif layer_name == "__final__":
                final_builders.append(builder)
            else:
                user_builders.append(builder)

        # Sort user layers by order
        def get_layer_order(builder: 'ActiveBuilder') -> int:
            layer_name = builder.config.layer_name
            return self._layer_orders.get(layer_name, 999999)  # Unordered layers go last

        user_builders = sorted(user_builders, key=get_layer_order)

        # Process in layer order: base → user layers → final
        for builder in base_builders:
            pos, speed, direction = self._apply_layer(builder, pos, speed, direction)

        for builder in user_builders:
            pos, speed, direction = self._apply_layer(builder, pos, speed, direction)

        for builder in final_builders:
            pos, speed, direction = self._apply_layer(builder, pos, speed, direction)


        return (pos, speed, direction)

    def _apply_layer(
        self,
        builder: 'ActiveBuilder',
        pos: Vec2,
        speed: float,
        direction: Vec2
    ) -> tuple[Vec2, float, Vec2]:
        """Apply a layer's operations

        Args:
            builder: The builder to apply
            pos, speed, direction: Current accumulated state values

        Returns:
            Updated (pos, speed, direction)

        Mode behavior:
        - offset: current_value is a CONTRIBUTION (added to accumulated)
        - override: current_value is ABSOLUTE (replaces accumulated)
        - scale: current_value is a MULTIPLIER (multiplies accumulated)
        """
        prop = builder.config.property
        mode = builder.config.mode
        current_value = builder.get_current_value()

        if prop == "speed":
            speed = mode_operations.apply_scalar_mode(mode, current_value, speed)

        elif prop == "direction":
            direction = mode_operations.apply_direction_mode(mode, current_value, direction)

        elif prop == "vector":
            speed, direction = mode_operations.apply_vector_mode(mode, current_value, speed, direction)

        elif prop == "pos":
            pos = mode_operations.apply_position_mode(mode, current_value, pos)

        return pos, speed, direction

    def _apply_velocity_movement(self, speed: float, direction: Vec2):
        """Apply velocity-based movement to internal position"""
        if speed == 0:
            return

        velocity = direction * speed
        dx_int, dy_int = self._subpixel_adjuster.adjust(velocity.x, velocity.y)
        self._internal_pos = Vec2(self._internal_pos.x + dx_int, self._internal_pos.y + dy_int)

    def _apply_position_offset(self, pos: Vec2):
        """Apply position offset to internal position"""
        position_offset = pos - self._base_pos
        offset_delta = position_offset - self._last_position_offset

        if offset_delta.x != 0 or offset_delta.y != 0:
            # Apply position offset directly without subpixel adjuster
            # Position changes are absolute targets, not velocity-based movement
            self._internal_pos = Vec2(
                self._internal_pos.x + offset_delta.x,
                self._internal_pos.y + offset_delta.y
            )

        self._last_position_offset = position_offset

    def _sync_to_manual_mouse_movement(self) -> bool:
        """Detect and sync to manual mouse movements by the user

        If the actual mouse position differs from our expected internal position,
        the user has manually moved the mouse.

        Returns:
            True if we should skip rig movement (manual movement detected or in timeout), False otherwise
        """
        current_x, current_y = ctrl.mouse_pos()
        expected_x = int(round(self._internal_pos.x))
        expected_y = int(round(self._internal_pos.y))

        # If mouse position differs from our internal position, user moved it manually
        if current_x != expected_x or current_y != expected_y:
            manual_move = Vec2(current_x, current_y)

            # Update internal position to match manual movement
            self._internal_pos = manual_move
            # Update base position to match (this effectively "bakes" the manual movement)
            self._base_pos = manual_move
            # Reset position offset tracking
            self._last_position_offset = Vec2(0, 0)

            # Record time of manual movement
            self._last_manual_movement_time = time.perf_counter()

            return True

        # Check if we're still in timeout period after manual movement
        if self._last_manual_movement_time is not None:
            elapsed_ms = (time.perf_counter() - self._last_manual_movement_time) * 1000
            if elapsed_ms < self._manual_movement_timeout_ms:
                return True  # Still in timeout, skip rig movement
            else:
                # Timeout expired, allow rig to take control again
                self._last_manual_movement_time = None

        return False

    def _update_frame(self):
        """Update all active builders and move mouse"""
        now = time.perf_counter()
        if self._last_frame_time is None:
            self._last_frame_time = now
            return

        dt = now - self._last_frame_time
        self._last_frame_time = now

        # Sync to any manual mouse movements by the user
        manual_movement_detected = self._sync_to_manual_mouse_movement()

        # Update all builders, remove completed ones
        # Use list() to create a snapshot and avoid "dictionary changed size during iteration"
        completed = []
        for layer, builder in list(self._active_builders.items()):
            still_active = builder.update(dt)
            if not still_active:
                completed.append(layer)
            else:
                # Debug: why is it still active?
                phase, progress = builder.lifecycle.update(0)

        for layer in completed:
            self.remove_builder(layer)

        # If user manually moved mouse, skip applying rig movement this frame
        # But we still updated the builders above so time progresses
        if manual_movement_detected:
            return

        pos, speed, direction = self._compute_current_state()

        self._apply_velocity_movement(speed, direction)
        self._apply_position_offset(pos)

        # Update _base_pos to track accumulated position from velocity movement
        # This ensures position offsets are calculated from the current actual position
        # Otherwise position builders can "snap" at the end when they don't account for velocity
        self._base_pos = Vec2(self._internal_pos.x, self._internal_pos.y)

        new_x = int(round(self._internal_pos.x))
        new_y = int(round(self._internal_pos.y))

        current_x, current_y = ctrl.mouse_pos()
        if new_x != current_x or new_y != current_y:
            mouse_move(new_x, new_y)

        # Stop frame loop AFTER mouse movement if no longer needed
        # This ensures final position is applied before stopping
        if not self._should_frame_loop_be_active():
            self._stop_frame_loop()


    def _ensure_frame_loop_running(self):
        """Start frame loop if not already running"""
        if self._frame_loop_job is None:
            # 60 FPS = ~16.67ms per frame
            self._frame_loop_job = cron.interval("16ms", self._update_frame)
            self._last_frame_time = None
            # Sync to actual mouse position when starting (handles manual movements)
            current_mouse = Vec2(*ctrl.mouse_pos())
            self._internal_pos = current_mouse
            self._base_pos = current_mouse
            self._last_position_offset = Vec2(0, 0)

    def _stop_frame_loop(self):
        """Stop the frame loop"""
        if self._frame_loop_job is not None:
            cron.cancel(self._frame_loop_job)
            self._frame_loop_job = None
            self._last_frame_time = None
            self._subpixel_adjuster.reset()
            # Sync internal position to actual mouse position when stopping
            # But keep _base_pos as-is (it was set by the last bake)
            current_mouse = Vec2(*ctrl.mouse_pos())
            self._internal_pos = current_mouse
            # Only update _base_pos if it's significantly different from current mouse
            # This handles manual mouse movements while preserving exact baked positions
            diff = abs(current_mouse.x - self._base_pos.x) + abs(current_mouse.y - self._base_pos.y)
            if diff > 2:  # More than 2 pixels difference suggests manual movement
                self._base_pos = current_mouse
            self._last_position_offset = Vec2(0, 0)

    def _has_movement(self) -> bool:
        """Check if there's any movement happening (base speed non-zero)"""
        return self._base_speed != 0

    def _should_frame_loop_be_active(self) -> bool:
        """Check if frame loop should be running (movement or active builders)"""
        return self._has_movement() or len(self._active_builders) > 0

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
        # tan(67.5°) ≈ 2.414, which is halfway between pure cardinal (90°) and diagonal (45°)
        # This means directions within ±22.5° of an axis are considered pure cardinal
        threshold = 2.414

        # Pure cardinal directions (within 22.5° of axis)
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
        """List of active user layers (excludes anonymous and final)

        Returns a list of layer names for currently active user layers.
        Anonymous (base) and final layers are excluded.

        Example:
            rig.state.layers  # ["sprint", "drift"]
        """
        return [layer for layer, builder in self._active_builders.items()
                if not builder.config.is_anonymous() and layer != "__final__"]

    # Layer state access
    class LayerState:
        """State information for a specific layer"""
        def __init__(self, builder: 'ActiveBuilder'):
            self._builder = builder

        @property
        def prop(self) -> str:
            """What property this layer is affecting: 'speed', 'direction', 'pos'"""
            return self._builder.config.property

        @property
        def operator(self) -> str:
            """Operation type: 'to', 'add', 'by', 'mul', 'div', 'sub'"""
            return self._builder.config.operator

        @property
        def value(self):
            """Current aggregated value (includes children)"""
            return self._builder.get_current_value()

        @property
        def phase(self) -> Optional[str]:
            """Current lifecycle phase: 'over', 'hold', 'revert', or None"""
            return self._builder.lifecycle.phase.value if self._builder.lifecycle else None

        @property
        def speed(self) -> Optional[float]:
            """Speed value if this layer affects speed, else None"""
            return self.value if self.prop == 'speed' else None

        @property
        def direction(self) -> Optional[Vec2]:
            """Direction value if this layer affects direction, else None"""
            return self.value if self.prop == 'direction' else None

        @property
        def pos(self) -> Optional[Vec2]:
            """Position offset if this layer affects position, else None"""
            return self.value if self.prop == 'pos' else None

        def time_alive(self) -> float:
            """Get time in seconds since this builder was created"""
            return self._builder.time_alive()

        def revert(self, ms: Optional[float] = None, easing: str = "linear"):
            """Trigger a revert on this layer

            Args:
                ms: Duration in milliseconds for the revert
                easing: Easing function for the revert
            """
            from .builder import RigBuilder
            # Create a revert-only builder that will trigger the revert
            builder = RigBuilder(self._builder.rig_state, self._builder.config.layer_name)
            builder.revert(ms, easing)
            # Force immediate execution (since it won't have __del__ called naturally)
            builder._execute()

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

        @property
        def pos(self) -> Vec2:
            return self._rig_state._base_pos

        @property
        def speed(self) -> float:
            return self._rig_state._base_speed

        @property
        def direction(self) -> Vec2:
            return self._rig_state._base_direction

    @property
    def base(self) -> 'RigState.BaseState':
        """Access to base (baked) state only"""
        return RigState.BaseState(self)

    def stop(self, transition_ms: Optional[float] = None, easing: str = "linear", **kwargs):
        """Stop everything: bake state, clear effects, decelerate to 0

        This matches v1 behavior:
        1. Bake current computed state into base
        2. Clear all active builders (effects)
        3. Set speed to 0 (with optional smooth deceleration)
        """
        # Validate arguments
        from .contracts import BuilderConfig, ConfigError
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
        """Reverse direction (180° turn)"""
        # This will be implemented via builder in builder.py
        pass

    def bake_all(self):
        """Bake all active builders immediately"""
        for layer in list(self._active_builders.keys()):
            self.remove_builder(layer, bake=True)

    def trigger_revert(self, layer: str, revert_ms: Optional[float] = None, easing: str = "linear"):
        """Trigger revert on builder tree

        Strategy:
        1. Capture current aggregated value from all children
        2. Clear all children (bake the aggregate)
        3. Create group lifecycle that reverses from aggregate to neutral
        """
        if layer in self._active_builders:
            builder = self._active_builders[layer]

            # Capture current aggregated value
            current_value = builder.get_current_value()

            # Get base value (neutral/zero for the property type)
            # Use builder's own config since children might be empty after first revert
            if builder.config.property == "speed":
                base_value = 0
            elif builder.config.property == "direction":
                base_value = builder.base_value  # Original direction
            elif builder.config.property == "pos":
                base_value = Vec2(0, 0)  # Zero offset
            else:
                base_value = 0

            # Create group lifecycle for coordinated revert
            builder.group_lifecycle = Lifecycle(is_user_layer=not builder.is_anonymous)
            builder.group_lifecycle.over_ms = 0  # Skip over phase
            builder.group_lifecycle.hold_ms = 0  # Skip hold phase
            builder.group_lifecycle.revert_ms = revert_ms if revert_ms is not None else 0
            builder.group_lifecycle.revert_easing = easing
            builder.group_lifecycle.phase = LifecyclePhase.REVERT
            builder.group_lifecycle.phase_start_time = time.perf_counter()

            # Store aggregate values for animation
            builder.group_base_value = base_value
            builder.group_target_value = current_value

            # Clear all children - we'll revert as a single coordinated unit
            builder.children = []
