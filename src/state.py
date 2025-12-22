"""State management for mouse rig V2

Unified state manager with:
- Base state (baked values)
- Layer groups (containers for builders)
- Queue system (integrated into groups)
- Frame loop
"""

import time
import math
from typing import Optional, TYPE_CHECKING, Union, Any
from talon import cron, ctrl, settings
from .core import Vec2, SubpixelAdjuster, mouse_move, mouse_move_relative
from .layer_group import LayerGroup
from .lifecycle import Lifecycle, LifecyclePhase, PropertyAnimator
from . import mode_operations, rate_utils
from .contracts import BuilderConfig

if TYPE_CHECKING:
    from .builder import ActiveBuilder


class RigState:
    """Core state manager for the mouse rig"""

    def __init__(self):
        # Base state (baked values)
        self._absolute_base_pos: Optional[Vec2] = None  # Baked screen position (lazy init - only for pos.to)
        self._base_speed: float = 0.0
        self._base_direction: Vec2 = Vec2(1, 0)

        # Layer groups (layer_name -> LayerGroup)
        # Each group contains multiple builders and manages their lifecycle
        self._layer_groups: dict[str, LayerGroup] = {}

        # Layer order tracking (layer_name -> order)
        self._layer_orders: dict[str, int] = {}

        # Frame loop
        self._frame_loop_job: Optional[cron.CronJob] = None
        self._last_frame_time: Optional[float] = None
        self._subpixel_adjuster = SubpixelAdjuster()
        # Track current screen position with subpixel precision (lazy init - only for pos.to)
        self._absolute_current_pos: Optional[Vec2] = None

        # Throttle tracking (global - spans group recreation)
        self._throttle_times: dict[str, float] = {}

        # Auto-order counter for layers without explicit order
        self._next_auto_order: int = 0

        # Rate-based builder cache (cache_key -> (builder, target_value))
        # Cache key: (layer, property, operator, normalized_target)
        self._rate_builder_cache: dict[tuple, tuple['ActiveBuilder', Any]] = {}

        # Debounce pending builders (debounce_key -> (target_time, config, is_base_layer, cron_job))
        self._debounce_pending: dict[str, tuple[float, 'BuilderConfig', bool, Optional[cron.CronJob]]] = {}

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

    def _get_queue_key(self, layer: str, builder: 'ActiveBuilder') -> str:
        """Get the queue key for a builder

        Single source of truth for queue key generation.

        Uses (layer, property, operator) to allow independent queues for different operations,
        even on base layer.

        Args:
            layer: The layer name
            builder: The builder to generate a key for

        Returns:
            Queue key string for use with QueueManager
        """
        # Use property + operator for specific queue tracking
        # This allows: rig.pos.by().queue and rig.speed.to().queue to be independent
        return f"{layer}_{builder.config.property}_{builder.config.operator}"

    def _get_throttle_key(self, layer: str, builder_or_config: Union['ActiveBuilder', 'BuilderConfig']) -> str:
        """Get throttle key for a builder

        Uses (layer, property, operator) to allow independent throttling per operation type.

        Args:
            layer: The layer name
            builder_or_config: The builder or config to generate a key for

        Returns:
            Throttle key string
        """
        config = builder_or_config if isinstance(builder_or_config, BuilderConfig) else builder_or_config.config
        return f"{layer}_{config.property}_{config.operator}"

    def _get_rate_cache_key(self, layer: str, config: 'BuilderConfig') -> Optional[tuple]:
        """Get rate cache key for a builder using rate-based timing

        Cache key is (layer, property, operator, mode, normalized_target_value).
        Returns None if not a rate-based operation.

        Args:
            layer: The layer name
            config: The builder config

        Returns:
            Cache key tuple or None
        """
        if config.over_rate is None and config.revert_rate is None:
            return None  # Not a rate-based operation

        # Normalize target value for comparison
        target = config.value
        if isinstance(target, tuple):
            # For tuples (pos, direction), round to reasonable precision
            normalized = tuple(round(v, 3) for v in target)
        elif isinstance(target, (int, float)):
            normalized = round(target, 3)
        else:
            normalized = target

        return (layer, config.property, config.operator, config.mode, normalized)

    def _get_debounce_key(self, layer: str, config: 'BuilderConfig') -> str:
        """Get debounce key for a builder

        Uses (layer, property, operator) for targeted debounce tracking.

        Args:
            layer: The layer name
            config: The builder config

        Returns:
            Debounce key string
        """
        return f"{layer}_{config.property}_{config.operator}"

    def time_alive(self, layer: str) -> Optional[float]:
        """Get time in seconds since builder was created

        Returns None if layer doesn't exist
        """
        if layer in self._layer_groups:
            group = self._layer_groups[layer]
            if group.builders:
                # Return time of first builder
                return group.builders[0].time_alive
        return None

    def _check_throttle(self, builder: 'ActiveBuilder', layer: str) -> bool:
        """Check if builder should be throttled

        Returns:
            True if throttled (should skip), False if allowed to proceed
        """
        throttle_key = self._get_throttle_key(layer, builder)
        throttle_ms = builder.config.behavior_args[0] if builder.config.behavior_args else 0

        if throttle_key in self._throttle_times:
            elapsed = (time.perf_counter() - self._throttle_times[throttle_key]) * 1000
            if elapsed < throttle_ms:
                return True  # Throttled

        self._throttle_times[throttle_key] = time.perf_counter()
        return False  # Not throttled

    def add_builder(self, builder: 'ActiveBuilder'):
        """Add a builder to its layer group

        Creates group if needed, handles behaviors, manages queue.
        """
        layer = builder.config.layer_name

        # Handle special operators
        if builder.config.operator == "bake":
            self._bake_property(builder.config.property, layer if not builder.config.is_base_layer() else None)
            return

        # Handle debounce behavior
        if builder.config.behavior == "debounce":
            if not builder.config.behavior_args:
                from .contracts import ConfigError
                raise ConfigError("debounce() requires a delay in milliseconds")

            delay_ms = builder.config.behavior_args[0]
            debounce_key = self._get_debounce_key(layer, builder.config)

            # Cancel existing debounce
            if debounce_key in self._debounce_pending:
                _, _, _, old_cron_job = self._debounce_pending[debounce_key]
                if old_cron_job is not None:
                    cron.cancel(old_cron_job)

            # Store pending
            target_time = time.perf_counter() + (delay_ms / 1000.0)

            cron_job = None
            if self._frame_loop_job is None:
                def execute_debounced():
                    if debounce_key in self._debounce_pending:
                        _, config, is_base, _ = self._debounce_pending[debounce_key]
                        del self._debounce_pending[debounce_key]
                        config.behavior = None
                        config.behavior_args = ()
                        from .builder import ActiveBuilder
                        actual_builder = ActiveBuilder(config, self, is_base)
                        self.add_builder(actual_builder)

                cron_job = cron.after(f"{delay_ms}ms", execute_debounced)

            self._debounce_pending[debounce_key] = (target_time, builder.config, builder.config.is_base_layer(), cron_job)
            return

        # Handle rate-based caching
        rate_cache_key = self._get_rate_cache_key(layer, builder.config)
        if rate_cache_key is not None:
            if rate_cache_key in self._rate_builder_cache:
                cached_builder, cached_target = self._rate_builder_cache[rate_cache_key]

                # Check if targets match
                targets_match = self._targets_match(builder.target_value, cached_target)

                if targets_match and layer in self._layer_groups:
                    # Same target in progress - ignore
                    return
                else:
                    # Different target - replace
                    if layer in self._layer_groups:
                        group = self._layer_groups[layer]
                        old_current_value = group.get_current_value()

                        # Update builder to start from current
                        builder.base_value = old_current_value
                        builder.target_value = builder._calculate_target_value()

                        # Recalculate rate duration
                        self._recalculate_rate_duration(builder)

            # Cache this builder
            self._rate_builder_cache[rate_cache_key] = (builder, builder.target_value)

        # Get or create group
        group = self._get_or_create_group(builder)

        # Handle behaviors
        behavior = builder.config.get_effective_behavior()

        if behavior == "throttle":
            if self._check_throttle(builder, layer):
                return  # Throttled, skip

        if behavior == "replace":
            # Get current accumulated value
            current_value = group.get_current_value()
            builder.base_value = current_value
            builder.target_value = builder._calculate_target_value()

            # Clear existing builders
            group.clear_builders()

        elif behavior == "stack":
            # Check max
            if builder.config.behavior_args:
                max_count = builder.config.behavior_args[0]
                if len(group.builders) >= max_count:
                    return  # At max, skip

        elif behavior == "queue":
            # Check max
            if builder.config.behavior_args:
                max_count = builder.config.behavior_args[0]
                total = len(group.builders) + len(group.pending_queue)
                if group.is_queue_active:
                    total += 1  # Count currently executing
                if total >= max_count:
                    return  # At max, skip

            # If queue is active or has pending, enqueue
            if group.is_queue_active or len(group.pending_queue) > 0:
                def execute_callback():
                    group.add_builder(builder)
                    if not builder.lifecycle.is_complete():
                        self._ensure_frame_loop_running()

                group.enqueue_builder(execute_callback)
                return
            else:
                # First in queue - execute immediately
                group.is_queue_active = True

        # Add builder to group
        group.add_builder(builder)

        # Start frame loop if needed
        if not builder.lifecycle.is_complete():
            self._ensure_frame_loop_running()
        elif builder.config.is_synchronous:
            # Handle instant completion
            print(f"[DEBUG add_builder] Synchronous execution for {builder.config.property}.{builder.config.operator}()")
            builder.execute_synchronous()
            bake_result = group.on_builder_complete(builder)
            print(f"[DEBUG add_builder] Bake result: {bake_result}")
            if bake_result == "bake_to_base":
                self._bake_group_to_base(group)
            
            # Remove the builder immediately for synchronous operations
            print(f"[DEBUG add_builder] Removing builder from group, group had {len(group.builders)} builders")
            group.remove_builder(builder)
            print(f"[DEBUG add_builder] After removal, group has {len(group.builders)} builders")

            # Clean up empty base groups
            if group.is_base and not group.should_persist():
                # Velocity properties need frame loop even after sync completion
                velocity_properties = {"speed", "direction", "vector"}
                if builder.config.property in velocity_properties:
                    # Start frame loop for velocity-based movement
                    print(f"[DEBUG add_builder] Starting frame loop for velocity property {builder.config.property}")
                    self._ensure_frame_loop_running()
                
                # Clean up the empty group
                print(f"[DEBUG add_builder] Deleting empty group {layer}")
                del self._layer_groups[layer]
                if layer in self._layer_orders:
                    del self._layer_orders[layer]
        else:
            # Builder is complete but not synchronous (e.g., speed.to(), direction.to())
            # These need frame loop to clean up and apply velocity
            print(f"[DEBUG add_builder] Non-synchronous complete builder for {builder.config.property}, starting frame loop")
            self._ensure_frame_loop_running()

    def _get_or_create_group(self, builder: 'ActiveBuilder') -> 'LayerGroup':
        """Get existing group or create new one for this builder"""
        layer = builder.config.layer_name

        if layer in self._layer_groups:
            return self._layer_groups[layer]

        # Create new group
        from .layer_group import LayerGroup

        group = LayerGroup(
            layer_name=layer,
            property=builder.config.property,
            mode=builder.config.mode,
            is_base=builder.config.is_base_layer(),
            order=builder.config.order
        )

        # Track order
        if builder.config.order is not None:
            self._layer_orders[layer] = builder.config.order
        elif not builder.config.is_base_layer():
            if layer not in self._layer_orders:
                self._layer_orders[layer] = self._next_auto_order
                self._next_auto_order += 1
                group.order = self._layer_orders[layer]

        self._layer_groups[layer] = group
        return group

    def _targets_match(self, target1: Any, target2: Any) -> bool:
        """Check if two target values match (with epsilon for floats)"""
        from .core import EPSILON

        if isinstance(target1, (int, float)) and isinstance(target2, (int, float)):
            return abs(target1 - target2) < EPSILON
        elif isinstance(target1, tuple) and isinstance(target2, tuple):
            return all(abs(a - b) < EPSILON for a, b in zip(target1, target2))
        elif isinstance(target1, Vec2) and isinstance(target2, Vec2):
            return abs(target1.x - target2.x) < EPSILON and abs(target1.y - target2.y) < EPSILON
        else:
            return target1 == target2

    def _recalculate_rate_duration(self, builder: 'ActiveBuilder'):
        """Recalculate rate-based duration after base_value changed"""
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

    def _bake_group_to_base(self, group: 'LayerGroup'):
        """Bake base layer group's value into base state"""
        if not group.is_base:
            return

        current_value = group.get_current_value()
        prop = group.property

        # Apply to base state
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


    def remove_builder(self, layer: str, bake: bool = False):
        """Remove a layer group"""
        if layer not in self._layer_groups:
            return

        group = self._layer_groups[layer]

        # If bake=true, bake current value into base
        if bake:
            if group.is_base:
                self._bake_group_to_base(group)
            else:
                # Modifier - keep accumulated value
                pass

        # Clean up rate builder cache for all builders in group
        for builder in group.builders:
            rate_cache_key = self._get_rate_cache_key(layer, builder.config)
            if rate_cache_key is not None and rate_cache_key in self._rate_builder_cache:
                del self._rate_builder_cache[rate_cache_key]

            # Clean up throttle tracking
            throttle_key = self._get_throttle_key(layer, builder)
            if throttle_key in self._throttle_times:
                del self._throttle_times[throttle_key]

        # Remove group
        del self._layer_groups[layer]

        # Remove order tracking
        if layer in self._layer_orders:
            del self._layer_orders[layer]

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

        if current_value is None:
            return

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

    def _bake_property(self, property_name: str, layer: Optional[str] = None):
        """Bake current computed value of a property into base state

        Args:
            property_name: The property to bake ("speed", "direction", "pos")
            layer: Optional layer to bake from a specific builder. If None, bakes computed state.
        """
        if layer:
            # Bake from a specific layer - remove it and bake its value
            if layer in self._layer_groups:
                group = self._layer_groups[layer]
                if group.property == property_name:
                    # Bake the group's current value
                    if group.is_base:
                        self._bake_group_to_base(group)
                    # Remove the group
                    del self._layer_groups[layer]
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

            # Remove all base layer groups affecting this property
            layers_to_remove = [
                l for l, g in self._layer_groups.items()
                if g.is_base and g.property == property_name
            ]
            for l in layers_to_remove:
                if l in self._layer_groups:
                    del self._layer_groups[l]

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

        # Separate groups by layer type
        base_groups = []   # Base layer groups
        user_groups = []   # User layer groups

        for layer_name, group in self._layer_groups.items():
            if group.is_base:
                base_groups.append(group)
            else:
                user_groups.append(group)

        # Sort user layers by order
        def get_layer_order(group: 'LayerGroup') -> int:
            return group.order if group.order is not None else 999999

        user_groups = sorted(user_groups, key=get_layer_order)

        # Process in layer order: base → user layers
        for group in base_groups:
            pos, speed, direction, override = self._apply_group(group, pos, speed, direction)
            pos_is_override = pos_is_override or override

        for group in user_groups:
            pos, speed, direction, override = self._apply_group(group, pos, speed, direction)
            pos_is_override = pos_is_override or override

        return (pos, speed, direction, pos_is_override)

    def _apply_group(
        self,
        group: 'LayerGroup',
        pos: Vec2,
        speed: float,
        direction: Vec2
    ) -> tuple[Vec2, float, Vec2, bool]:
        """Apply a layer group's aggregated value

        Args:
            group: The layer group to apply
            pos, speed, direction: Current accumulated state values

        Returns:
            Updated (pos, speed, direction, pos_is_override)
            pos_is_override is True if this layer used override mode for position

        Mode behavior:
        - offset: current_value is a CONTRIBUTION (added to accumulated)
        - override: current_value is ABSOLUTE (replaces accumulated)
        - scale: current_value is a MULTIPLIER (multiplies accumulated)
        """
        prop = group.property
        mode = group.mode
        current_value = group.get_current_value()
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

        # Separate groups by layer type
        base_groups = []
        user_groups = []

        for layer_name, group in self._layer_groups.items():
            if group.property in ("speed", "direction", "vector"):
                if group.is_base:
                    base_groups.append(group)
                else:
                    user_groups.append(group)

        # Sort user layers by order
        def get_layer_order(group: 'LayerGroup') -> int:
            return group.order if group.order is not None else 999999

        user_groups = sorted(user_groups, key=get_layer_order)

        # Apply all velocity groups
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
            - has_absolute_position: True if any pos.to() builders exist
            - absolute_target: Target position for absolute builders (last one wins)
            - relative_delta: Accumulated delta from all pos.by() builders
            - relative_position_updates: List of (builder, new_value, new_int_value) for tracking updates
        """
        has_absolute_position = False
        absolute_target = None
        relative_delta = Vec2(0, 0)
        relative_position_updates = []

        for layer_name, group in self._layer_groups.items():
            if group.property != "pos":
                continue

            # Check movement type from first builder (all should match in a group)
            if not group.builders:
                continue

            first_builder = group.builders[0]

            if first_builder.config.movement_type == "absolute":
                # pos.to() - absolute positioning
                # Use group's aggregated value (handles mode correctly)
                has_absolute_position = True
                absolute_target = group.get_current_value()
                print(f"[DEBUG _process_position_builders] Layer '{layer_name}': absolute_target={absolute_target}, mode={group.mode}, builders={len(group.builders)}")
            else:
                # pos.by() - pure relative delta
                for builder in group.builders:
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

    def _has_api_overrides(self) -> bool:
        """Check if any active group has API overrides"""
        for group in self._layer_groups.values():
            for builder in group.builders:
                if builder.config.api_override is not None:
                    return True
        return False

    def _get_override_functions(self):
        """Get override functions if any builder has overrides, otherwise None

        Returns (move_absolute, move_relative) or (None, None)
        """
        if not self._has_api_overrides():
            return None, None

        # Find override (last one wins if multiple)
        api_override = None
        for group in self._layer_groups.values():
            for builder in group.builders:
                if builder.config.api_override is not None:
                    api_override = builder.config.api_override

        from .mouse_api import get_mouse_move_functions
        return get_mouse_move_functions(api_override, api_override)

    def _emit_mouse_movement(self, has_absolute_position: bool, absolute_target: Optional[Vec2], frame_delta: Vec2):
        """Emit mouse movement based on accumulated deltas

        Args:
            has_absolute_position: True if using absolute positioning (pos.to)
            absolute_target: Target position for absolute mode
            frame_delta: Accumulated delta from velocity and relative position builders
        """
        # Get override functions if any builder has them
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
                self._expected_mouse_pos = (new_x, new_y)
        else:
            if frame_delta.x != 0 or frame_delta.y != 0:
                if move_relative_override is not None:
                    move_relative_override(round(frame_delta.x), round(frame_delta.y))
                else:
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

    def _check_debounce_pending(self, current_time: float):
        """Check and execute any debounce builders that are ready

        Args:
            current_time: Current timestamp from perf_counter()
        """
        ready_keys = []

        for debounce_key, (target_time, config, is_anon, cron_job) in list(self._debounce_pending.items()):
            if current_time >= target_time:
                ready_keys.append(debounce_key)

        # Execute ready builders
        for debounce_key in ready_keys:
            target_time, config, is_base, cron_job = self._debounce_pending[debounce_key]
            del self._debounce_pending[debounce_key]

            # Cancel cron if it exists (shouldn't fire since we're executing now)
            if cron_job is not None:
                cron.cancel(cron_job)

            # Clear debounce behavior so builder executes normally
            config.behavior = None
            config.behavior_args = ()

            # Create and add the actual builder
            from .builder import ActiveBuilder
            actual_builder = ActiveBuilder(config, self, is_base)
            self.add_builder(actual_builder)

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
        print(f"[DEBUG _tick_frame] START - active groups: {len(self._layer_groups)}")
        current_time, dt = self._calculate_delta_time()
        if dt is None:
            return

        # Process pending debounce builders
        self._check_debounce_pending(current_time)

        # Check for manual movement (only works in absolute mode)
        manual_movement_detected = self._sync_to_manual_mouse_movement()
        phase_transitions = self._advance_all_builders(current_time)

        if manual_movement_detected:
            print(f"[DEBUG _tick_frame] Manual movement detected, early exit")
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
        print(f"[DEBUG _tick_frame] About to execute {len(phase_transitions)} phase callbacks")
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
        """Advance all groups and track phase transitions.

        Args:
            current_time: Current timestamp from perf_counter() (captured once per frame)

        Returns:
            List of (builder, completed_phase) tuples for callbacks
        """
        phase_transitions = []

        for layer, group in list(self._layer_groups.items()):
            # Advance the group (which advances all builders)
            group_transitions = group.advance(current_time)
            phase_transitions.extend(group_transitions)

        return phase_transitions

    def _remove_completed_builders(self, current_time: float) -> set[str]:
        """Remove completed builders from groups

        Args:
            current_time: Current timestamp from perf_counter() (captured once per frame)

        Returns:
            Set of layer names that were completed and removed
        """
        completed_layers = set()

        for layer, group in list(self._layer_groups.items()):
            builders_to_remove = []

            for builder in group.builders:
                # Check if marked for removal
                if builder._marked_for_removal:
                    builders_to_remove.append(builder)
                    continue

                # Final advance to ensure target achieved
                completed_phase, _ = builder.advance(current_time)

                if completed_phase is not None:
                    print(f"[DEBUG _remove_completed_builders] Builder completing phase '{completed_phase}'")
                    # For relative position builders, emit any remaining delta
                    if (builder.config.property == "pos" and
                        builder.config.movement_type == "relative" and
                        hasattr(builder, '_total_emitted_int')):

                        final_value = builder.get_interpolated_value()
                        final_target_int = Vec2(round(final_value.x), round(final_value.y))
                        final_delta_int = final_target_int - builder._total_emitted_int

                        print(f"[DEBUG _remove_completed_builders] Relative position: final_value={final_value}, final_target_int={final_target_int}, total_emitted={builder._total_emitted_int}, final_delta_int={final_delta_int}")

                        if final_delta_int.x != 0 or final_delta_int.y != 0:
                            print(f"[DEBUG _remove_completed_builders] Emitting final delta: ({int(final_delta_int.x)}, {int(final_delta_int.y)})")
                            _, move_relative_override = self._get_override_functions()
                            if move_relative_override is not None:
                                move_relative_override(int(final_delta_int.x), int(final_delta_int.y))
                            else:
                                mouse_move_relative(int(final_delta_int.x), int(final_delta_int.y))

                    builders_to_remove.append(builder)

            # Remove completed builders from group
            for builder in builders_to_remove:
                bake_result = group.on_builder_complete(builder)
                if bake_result == "bake_to_base":
                    self._bake_group_to_base(group)

            # Check if group should be removed
            if not group.should_persist():
                del self._layer_groups[layer]
                if layer in self._layer_orders:
                    del self._layer_orders[layer]
                completed_layers.add(layer)

        return completed_layers

    def _execute_phase_callbacks(self, phase_transitions: list[tuple['ActiveBuilder', str]]):
        """Execute callbacks for completed phases"""
        for builder, completed_phase in phase_transitions:
            builder.lifecycle.execute_callbacks(completed_phase)

    def _stop_frame_loop_if_done(self):
        """Stop frame loop if no longer needed"""
        should_be_active = self._should_frame_loop_be_active()
        print(f"[DEBUG _stop_frame_loop_if_done] should_be_active={should_be_active}")
        if not should_be_active:
            print(f"[DEBUG _stop_frame_loop_if_done] STOPPING frame loop")
            self._stop_frame_loop()


    def _ensure_frame_loop_running(self):
        """Start frame loop if not already running"""
        print(f"[DEBUG _ensure_frame_loop_running] Called, job exists: {self._frame_loop_job is not None}")
        if self._frame_loop_job is None:
            frame_interval = settings.get("user.mouse_rig_frame_interval", 16)
            self._frame_loop_job = cron.interval(f"{frame_interval}ms", self._tick_frame)
            self._last_frame_time = None
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
                    pass
            self._stop_callbacks.clear()

    def _has_movement(self) -> bool:
        """Check if there's any movement happening (base speed or velocity layers)"""
        # Fast path: base speed is non-zero
        if self._base_speed != 0:
            return True

        # Check if any velocity-affecting groups exist
        # If they do, they could create movement even with base speed 0
        for group in self._layer_groups.values():
            prop = group.property
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
        has_movement = self._has_movement()
        print(f"[DEBUG _should_frame_loop_be_active] has_movement={has_movement}, groups={len(self._layer_groups)}")
        if has_movement:
            return True

        # Check if any builder has an incomplete lifecycle
        for group in self._layer_groups.values():
            print(f"[DEBUG _should_frame_loop_be_active] Checking group '{group.layer_name}': {len(group.builders)} builders")
            for builder in group.builders:
                is_complete = builder.lifecycle.is_complete()
                print(f"[DEBUG _should_frame_loop_be_active]   Builder {builder.config.property}.{builder.config.operator}(): complete={is_complete}, phase={builder.lifecycle.phase}")
                if not is_complete:
                    return True

        print(f"[DEBUG _should_frame_loop_be_active] No active work, returning False")
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
    def direction_cardinal(self) -> Optional[str]:
        """Current direction as cardinal/intercardinal string

        Returns one of: "right", "left", "up", "down",
                       "up_right", "up_left", "down_right", "down_left"
        or None if direction is zero vector.
        """
        direction_vec = self._compute_current_state()[2]
        return self._get_cardinal_direction(direction_vec)

    @property
    def layers(self) -> list[str]:
        """List of active user layers (excludes anonymous)

        Returns a list of layer names for currently active user layers.
        Anonymous (base) layers are excluded.

        Example:
            rig.state.layers  # ["sprint", "drift"]
        """
        return [layer for layer, group in self._layer_groups.items()
                if not group.is_base]

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
                f"operator={builder.config.operator}",
                f"value={format_value(builder.get_interpolated_value())}",
                f"target={format_value(builder.target_value)}",
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
        def operator(self) -> str:
            """Operator type: 'to', 'by', 'add', 'mult'"""
            return self._builder.config.operator

        @property
        def value(self):
            """Current aggregated value (includes children) - always fresh"""
            return self._builder.get_interpolated_value()

        @property
        def target(self):
            """Target value this layer is moving toward"""
            return self._builder.target_value

        @property
        def time_alive(self) -> float:
            """Time in seconds since this builder was created"""
            return self._builder.time_alive

        @property
        def time_left(self) -> float:
            """Time in seconds until this layer completes (0 if infinite or no timing)"""
            lifecycle = self._builder.lifecycle
            total_duration = 0

            if lifecycle.over_ms:
                total_duration += lifecycle.over_ms
            if lifecycle.hold_ms:
                total_duration += lifecycle.hold_ms
            if lifecycle.revert_ms:
                total_duration += lifecycle.revert_ms

            if total_duration == 0:
                return 0  # Infinite/no timing

            elapsed_ms = self._builder.time_alive * 1000
            remaining_ms = max(0, total_duration - elapsed_ms)
            return remaining_ms / 1000

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
        if layer_name not in self._layer_groups:
            return None

        group = self._layer_groups[layer_name]
        # Return state based on first builder in group
        if not group.builders:
            return None
        return RigState.LayerState(group.builders[0])

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

    # Smart property accessors for computed values with layer mode access
    class SmartPropertyState:
        """Smart accessor that provides both computed value and layer mode states"""
        def __init__(self, rig_state: 'RigState', property_name: str, computed_value):
            self._rig_state = rig_state
            self._property_name = property_name
            self._computed_value = computed_value

        @property
        def value(self):
            """Current computed value (includes all layers)"""
            return self._computed_value

        @property
        def target(self):
            """Target value from base layer animation (None if no base animation)"""
            # Find base groups for this property
            for layer_name, group in self._rig_state._layer_groups.items():
                if (group.is_base and
                    group.property == self._property_name and
                    len(group.builders) > 0):
                    # Return target of first active builder
                    for builder in group.builders:
                        if not builder.lifecycle.is_complete():
                            return builder.target_value
            return None

        # Shortcuts for Vec2 properties (pos, direction, vector)
        @property
        def x(self):
            """X component of the computed value (shortcut to .value.x)"""
            if not hasattr(self._computed_value, 'x'):
                raise AttributeError(f"Property '{self._property_name}' is a scalar and doesn't have .x component. Only Vec2 properties (pos, direction, vector) support .x/.y shortcuts.")
            return self._computed_value.x

        @property
        def y(self):
            """Y component of the computed value (shortcut to .value.y)"""
            if not hasattr(self._computed_value, 'y'):
                raise AttributeError(f"Property '{self._property_name}' is a scalar and doesn't have .y component. Only Vec2 properties (pos, direction, vector) support .x/.y shortcuts.")
            return self._computed_value.y

        # Layer mode accessors
        @property
        def offset(self) -> Optional['RigState.LayerState']:
            """Get implicit layer state for .offset mode"""
            layer_name = f"{self._property_name}.offset"
            return self._rig_state.layer(layer_name) if layer_name in self._rig_state._layer_groups else None

        @property
        def override(self) -> Optional['RigState.LayerState']:
            """Get implicit layer state for .override mode"""
            layer_name = f"{self._property_name}.override"
            return self._rig_state.layer(layer_name) if layer_name in self._rig_state._layer_groups else None

        @property
        def scale(self) -> Optional['RigState.LayerState']:
            """Get implicit layer state for .scale mode"""
            layer_name = f"{self._property_name}.scale"
            return self._rig_state.layer(layer_name) if layer_name in self._rig_state._layer_groups else None

        def __repr__(self):
            # Show available properties/methods, not the computed value
            prop_type = "Vec2" if hasattr(self._computed_value, 'x') else "scalar"

            parts = [
                f"SmartPropertyState('{self._property_name}')",
                f"  .value - Current computed {self._property_name}",
                f"  .target - Target from base animation (or None)",
            ]

            if prop_type == "Vec2":
                parts.extend([
                    f"  .x - Shortcut to .value.x",
                    f"  .y - Shortcut to .value.y",
                ])

            parts.extend([
                f"  .offset - LayerState for implicit '{self._property_name}.offset' layer (or None)",
                f"  .override - LayerState for implicit '{self._property_name}.override' layer (or None)",
                f"  .scale - LayerState for implicit '{self._property_name}.scale' layer (or None)",
            ])

            return "\n".join(parts)

        def __str__(self):
            return str(self._computed_value)

        # Magic methods to make SmartPropertyState behave like the underlying value
        # in mathematical operations (auto-delegates to .value)
        def __add__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value + other_val

        def __radd__(self, other):
            return other + self._computed_value

        def __sub__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value - other_val

        def __rsub__(self, other):
            return other - self._computed_value

        def __mul__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value * other_val

        def __rmul__(self, other):
            return other * self._computed_value

        def __truediv__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value / other_val

        def __rtruediv__(self, other):
            return other / self._computed_value

        def __floordiv__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value // other_val

        def __rfloordiv__(self, other):
            return other // self._computed_value

        def __mod__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value % other_val

        def __rmod__(self, other):
            return other % self._computed_value

        def __pow__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value ** other_val

        def __rpow__(self, other):
            return other ** self._computed_value

        def __neg__(self):
            return -self._computed_value

        def __pos__(self):
            return +self._computed_value

        def __abs__(self):
            return abs(self._computed_value)

        # Comparison operators
        def __eq__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value == other_val

        def __ne__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value != other_val

        def __lt__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value < other_val

        def __le__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value <= other_val

        def __gt__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value > other_val

        def __ge__(self, other):
            other_val = other.value if isinstance(other, self.__class__) else other
            return self._computed_value >= other_val

        # Numeric conversion
        def __float__(self):
            return float(self._computed_value)

        def __int__(self):
            return int(self._computed_value)

        def __bool__(self):
            return bool(self._computed_value)

    # Override property getters to return smart accessors
    @property
    def pos(self) -> 'RigState.SmartPropertyState':
        """Current computed position (with .offset, .override, .scale layer access)"""
        pos_vec = self._compute_current_state()[0]
        return RigState.SmartPropertyState(self, "pos", pos_vec)

    @property
    def speed(self) -> 'RigState.SmartPropertyState':
        """Current computed speed (with .offset, .override, .scale layer access)"""
        speed_val = self._compute_current_state()[1]
        return RigState.SmartPropertyState(self, "speed", speed_val)

    @property
    def direction(self) -> 'RigState.SmartPropertyState':
        """Current computed direction (with .offset, .override, .scale layer access)"""
        direction_vec = self._compute_current_state()[2]
        return RigState.SmartPropertyState(self, "direction", direction_vec)

    @property
    def vector(self) -> 'RigState.SmartPropertyState':
        """Current computed velocity vector (with .offset, .override, .scale layer access)"""
        speed = self._compute_current_state()[1]
        direction = self._compute_current_state()[2]
        return RigState.SmartPropertyState(self, "vector", direction * speed)

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
        transition_ms = validate_timing(transition_ms, 'transition_ms', method='stop')

        config = BuilderConfig()
        all_kwargs = {'easing': easing, **kwargs}
        config.validate_method_kwargs('stop', **all_kwargs)

        # 1. Bake all active groups into base
        for layer in list(self._layer_groups.keys()):
            group = self._layer_groups[layer]
            if group.is_base:
                self._bake_group_to_base(group)

        # 2. Clear all active groups and layer tracking
        self._layer_groups.clear()
        self._layer_orders.clear()
        self._throttle_times.clear()
        self._rate_builder_cache.clear()
        self._debounce_pending.clear()

        # 3. Decelerate speed to 0
        if transition_ms is None or transition_ms == 0:
            # Immediate stop
            self._base_speed = 0.0
            # Stop frame loop if no active groups
            if len(self._layer_groups) == 0:
                self._stop_frame_loop()
        else:
            # Smooth deceleration - create base layer builder
            from .builder import ActiveBuilder
            from .contracts import BuilderConfig

            config = BuilderConfig()
            config.property = "speed"
            config.layer_name = f"base.{config.property}"
            config.operator = "to"
            config.value = 0
            config.over_ms = transition_ms
            config.over_easing = easing

            builder = ActiveBuilder(config, self, is_base_layer=True)
            self.add_builder(builder)

    def reverse(self, transition_ms: Optional[float] = None):
        """Reverse direction (180 degrees turn)"""
        # This will be implemented via builder in builder.py
        pass

    def bake_all(self):
        """Bake all active builders immediately"""
        for layer in list(self._layer_groups.keys()):
            self.remove_builder(layer, bake=True)

    def reset(self):
        """Reset everything to default state

        Clears all layers, resets base speed to 0, base direction to (1, 0),
        position tracking to None, and stops the frame loop.

        This is useful when direction or other properties persist from previous
        operations and you want a clean slate.
        """
        # Stop frame loop
        self._stop_frame_loop()

        # Clear all active groups and tracking
        self._layer_groups.clear()
        self._layer_orders.clear()
        self._throttle_times.clear()
        self._rate_builder_cache.clear()
        self._debounce_pending.clear()

        # Reset base state to defaults
        self._base_speed = 0.0
        self._base_direction = Vec2(1, 0)
        self._absolute_base_pos = None
        self._absolute_current_pos = None

        # Reset subpixel tracking
        self._subpixel_adjuster.reset()

        # Reset manual movement tracking
        self._last_manual_movement_time = None
        self._expected_mouse_pos = None

        # Reset auto-order counter
        self._next_auto_order = 0

        # Clear stop callbacks
        self._stop_callbacks.clear()

    def trigger_revert(self, layer: str, revert_ms: Optional[float] = None, easing: str = "linear", current_time: Optional[float] = None):
        """Trigger revert on a layer group

        Args:
            layer: Layer name to revert
            revert_ms: Duration in milliseconds for the revert
            easing: Easing function for the revert
            current_time: Current timestamp from perf_counter() (if called from frame loop)
        """
        if layer in self._layer_groups:
            group = self._layer_groups[layer]

            # Trigger revert on all builders in the group
            if current_time is None:
                current_time = time.perf_counter()

            for builder in group.builders:
                builder.lifecycle.trigger_revert(current_time, revert_ms, easing)

            self._ensure_frame_loop_running()
