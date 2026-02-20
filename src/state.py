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
from .core import Vec2, is_vec2, SubpixelAdjuster, mouse_move, mouse_move_relative, mouse_scroll_native, EPSILON
from .layer_group import LayerGroup
from .lifecycle import LifecyclePhase
from . import mode_operations, rate_utils
from .mouse_api import get_mouse_move_functions
from .contracts import (
    BuilderConfig,
    ConfigError,
    validate_timing,
    VALID_LAYER_STATE_ATTRS
)

if TYPE_CHECKING:
    from .builder import ActiveBuilder


class RigState:
    """Core state manager for the mouse rig"""

    def __init__(self):
        # Base state (baked values)
        self._absolute_base_pos: Optional[Vec2] = None  # Baked screen position (lazy init - only for pos.to)
        self._base_speed: float = 0.0
        self._base_direction: Vec2 = Vec2(1, 0)
        self._base_scroll_speed: float = 0.0  # Scroll speed (magnitude)
        self._base_scroll_direction: Vec2 = Vec2(0, 1)  # Scroll direction (default: down)

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

        # Manual mouse movement detection (works in both absolute and relative modes)
        self._last_manual_movement_time: Optional[float] = None
        self._expected_mouse_pos: Optional[tuple[int, int]] = None  # Expected screen position after last rig movement

        # Stop callbacks (fired when frame loop stops)
        self._stop_callbacks: list = []
        self._scroll_stop_callbacks: list = []

        # Primed button (pressed on next add_builder, released on stop)
        self._primed_button: Optional[int] = None

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

    def _apply_throttle_behavior(self, builder: 'ActiveBuilder', layer: str) -> bool:
        """Apply throttle behavior: check and record throttle time

        Two modes:
        1. throttle() without args: Ignore while any builder with throttle behavior is active on layer
        2. throttle(ms): Rate limit calls to once per ms (time-based)

        Side effect: Updates throttle timestamp when not throttled (time-based mode only)

        Returns:
            True if throttled (should skip), False if allowed to proceed
        """
        throttle_key = self._get_throttle_key(layer, builder)

        # Check if we have a time-based throttle or a "while active" throttle
        has_time_arg = bool(builder.config.behavior_args)

        if has_time_arg:
            # Time-based throttle: throttle(ms)
            throttle_ms = builder.config.behavior_args[0]
            if throttle_key in self._throttle_times:
                elapsed = (time.perf_counter() - self._throttle_times[throttle_key]) * 1000
                if elapsed < throttle_ms:
                    return True  # Throttled
            self._throttle_times[throttle_key] = time.perf_counter()
            return False  # Not throttled
        else:
            # "While active" throttle: throttle()
            # Check if there are any active builders with throttle behavior on this layer
            if layer in self._layer_groups:
                group = self._layer_groups[layer]
                active_throttled_count = sum(1 for b in group.builders if b.config.behavior == "throttle")
                if active_throttled_count > 0:
                    return True  # Found an active throttled builder - reject this one
            return False  # No active throttled builders - allow this one

    def _apply_debounce_behavior(self, builder: 'ActiveBuilder', layer: str):
        """Apply debounce behavior: schedule builder for delayed execution

        Cancels any existing debounced builder with the same key and schedules
        the new builder to execute after the specified delay.

        Args:
            builder: The builder to schedule
            layer: The layer name
        """
        if not builder.config.behavior_args:
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

    def _check_and_update_rate_cache(self, builder: 'ActiveBuilder', layer: str) -> bool:
        """Check rate-based cache and update builder/cache as needed

        Side effects: May modify builder.base_value, builder.target_value, and update cache

        For rate-based builders (using .over_rate or .revert_rate), checks if a
        matching builder is already in progress. If targets match, skips this builder.
        If targets differ, updates the new builder to start from current value.

        Args:
            builder: The builder to check and potentially update
            layer: The layer name

        Returns:
            True if builder should be skipped (matching target in progress)
            False if builder should proceed
        """
        rate_cache_key = self._get_rate_cache_key(layer, builder.config)
        if rate_cache_key is None:
            return False  # Not a rate-based operation

        if rate_cache_key in self._rate_builder_cache:
            cached_builder, cached_target = self._rate_builder_cache[rate_cache_key]

            # Check if targets match
            targets_match = self._targets_match(builder.target_value, cached_target)

            if targets_match and layer in self._layer_groups:
                # Same target in progress - skip
                return True
            else:
                # Different target - replace
                if layer in self._layer_groups:
                    group = self._layer_groups[layer]
                    old_current_value = group.get_current_value()

                    # Update builder to start from current (make copy if Vec2)
                    if is_vec2(old_current_value):
                        builder.base_value = Vec2(old_current_value.x, old_current_value.y)
                    else:
                        builder.base_value = old_current_value
                    builder.target_value = builder._calculate_target_value()

                    # Recalculate rate duration
                    self._recalculate_rate_duration(builder)

        # Cache this builder
        self._rate_builder_cache[rate_cache_key] = (builder, builder.target_value)
        return False

    def _apply_replace_behavior(self, builder: 'ActiveBuilder', group: 'LayerGroup'):
        """Apply replace behavior with new committed_value architecture

        For pos.offset:
        - Bakes current progress to committed_value
        - Sets replace_target for clamping
        - Builder animates its full target value
        - Output gets clamped by LayerGroup.get_current_value()

        For other properties:
        - Simple snapshot and reset behavior (no committed tracking)

        Args:
            builder: The new builder to add
            group: The layer group to apply replace behavior to
        """
        # Get current value (includes accumulated + active builders)
        current_value = group.get_current_value()

        # Clear existing builders first (they've been accounted for in current_value)
        group.clear_builders()

        # POS.OFFSET: Use committed_value architecture
        if builder.config.property == "pos" and builder.config.mode == "offset":
            # Bake current progress to committed_value
            if is_vec2(current_value):
                if group.committed_value is None:
                    group.committed_value = Vec2(0, 0)

                # Add current_value to committed (baking the progress from active builders)
                group.committed_value = Vec2(
                    group.committed_value.x + current_value.x,
                    group.committed_value.y + current_value.y
                )

                # Reset accumulated for new builder
                group.accumulated_value = Vec2(0, 0)

            # Set up replace_target (user's absolute target)
            if isinstance(builder.config.value, tuple):
                group.replace_target = Vec2.from_tuple(builder.config.value)
            else:
                group.replace_target = builder.config.value

            # Builder animates from 0 to full target value
            builder.base_value = Vec2(0, 0)
            builder.target_value = group.replace_target

            # Revert handling: revert back to zero (start position)
            if builder.lifecycle.revert_ms:
                # After forward animation, we'll have:
                # - committed = replace_target (from cleanup in on_builder_complete)
                # - accumulated = 0
                # Revert needs to go back to (0, 0) total, so revert to 0
                if is_vec2(group.replace_target):
                    builder.revert_target = Vec2(0, 0)
                else:
                    builder.revert_target = 0.0

        # OTHER PROPERTIES: Simple snapshot and reset
        else:
            # Snapshot current value to accumulated
            if not group.is_base:
                group.accumulated_value = current_value

            # Builder starts from current position
            # For pos.override on base layer, use actual mouse position, not group's current_value
            if builder.config.property == "pos" and builder.config.mode == "override" and group.is_base:
                mouse_x, mouse_y = ctrl.mouse_pos()
                builder.base_value = Vec2(mouse_x, mouse_y)
            elif builder.config.property in ("direction", "pos", "vector") and not is_vec2(current_value):
                builder.base_value = Vec2(0, 0)
            else:
                builder.base_value = current_value

            if builder.config.mode == "offset":
                # For offset mode, target is absolute offset value
                if isinstance(builder.config.value, tuple):
                    builder.target_value = Vec2.from_tuple(builder.config.value)
                else:
                    builder.target_value = builder.config.value
            else:
                # For override/scale mode, calculate normally
                builder.target_value = builder._calculate_target_value()

            # Revert for offset mode: negate the accumulated
            if not group.is_base and builder.config.mode == "offset" and builder.lifecycle.revert_ms:
                accumulated = group.accumulated_value
                if is_vec2(accumulated):
                    builder.revert_target = Vec2(-accumulated.x, -accumulated.y)
                elif isinstance(accumulated, (int, float)):
                    builder.revert_target = -accumulated
                else:
                    builder.revert_target = None

    def _apply_stack_behavior(self, builder: 'ActiveBuilder', group: 'LayerGroup') -> bool:
        """Apply stack behavior: check if limit is reached (pure check, no side effects)

        Args:
            builder: The builder to check
            group: The layer group to check

        Returns:
            True if at stack limit (should skip builder)
            False if under limit (should add builder)
        """
        if builder.config.behavior_args:
            max_count = builder.config.behavior_args[0]
            if max_count > 0 and len(group.builders) >= max_count:
                return True  # At max, skip
        return False

    def _apply_queue_behavior(self, builder: 'ActiveBuilder', group: 'LayerGroup') -> bool:
        """Apply queue behavior: enqueue or execute builder based on queue state

        If queue is active or has pending items, enqueues the builder.
        If queue is empty, marks it as active and returns False to execute immediately.

        Args:
            builder: The builder to enqueue or execute
            group: The layer group managing the queue

        Returns:
            True if builder was enqueued (caller should return early)
            False if builder should be executed immediately
        """
        # Check max
        if builder.config.behavior_args:
            max_count = builder.config.behavior_args[0]
            # Count active builders + pending queue items
            # Don't add 1 for is_queue_active - executing builder is already in group.builders
            total = len(group.builders) + len(group.pending_queue)
            if total >= max_count:
                return True  # At max, skip

        # If queue is active or has pending, enqueue
        if group.is_queue_active or len(group.pending_queue) > 0:
            def execute_callback():
                # Recalculate timing so animation starts fresh
                builder.creation_time = time.perf_counter()
                builder.lifecycle.started = False
                # For base layers, recalculate base from current animated value
                # so queued operations chain from where the previous one ended.
                # For modifier layers, keep original base_value (offsets accumulate independently).
                if group.is_base:
                    builder.base_value = builder._get_current_or_base_value()
                    builder.target_value = builder._calculate_target_value()
                group.add_builder(builder)
                if not builder.lifecycle.is_complete():
                    self._ensure_frame_loop_running()

            group.enqueue_builder(execute_callback)
            return True  # Enqueued, caller should return
        else:
            # First in queue - execute immediately
            group.is_queue_active = True
            return False  # Execute immediately

    def _finalize_builder_completion(self, builder: 'ActiveBuilder', group: 'LayerGroup'):
        """Handle builder completion and cleanup

        Handles both synchronous (pos.to, pos.by) and instant completion
        (speed.to, direction.to without .over) cases. Manages baking, builder
        removal, frame loop starting, and group cleanup.

        Args:
            builder: The completed builder
            group: The layer group containing the builder
        """
        layer = builder.config.layer_name

        if builder.config.is_synchronous:
            # Handle synchronous instant completion (pos.to, pos.by)
            builder.execute_synchronous()
            bake_result = group.on_builder_complete(builder)
            if bake_result == "bake_to_base":
                self._bake_group_to_base(group)

            # Remove the builder immediately for synchronous operations
            group.remove_builder(builder)

            # Clean up empty base groups
            if group.is_base and not group.should_persist():
                # Velocity properties need frame loop even after sync completion
                velocity_properties = {"speed", "direction", "vector"}
                if builder.config.property in velocity_properties:
                    # Start frame loop for velocity-based movement
                    self._ensure_frame_loop_running()

                # Clean up the empty group
                if layer in self._layer_groups:
                    del self._layer_groups[layer]
        else:
            # Handle non-synchronous instant completion (speed.to, direction.to without .over)
            bake_result = group.on_builder_complete(builder)
            if bake_result == "bake_to_base":
                self._bake_group_to_base(group)

            # Remove the builder
            group.remove_builder(builder)

            # For velocity properties, start frame loop for movement
            if builder.config.property in {"speed", "direction", "vector"}:
                self._ensure_frame_loop_running()

            # Clean up empty groups
            if not group.should_persist():
                if layer in self._layer_groups:
                    del self._layer_groups[layer]
                if layer in self._layer_orders:
                    del self._layer_orders[layer]

    def add_builder(self, builder: 'ActiveBuilder'):
        """Add a builder to its layer group

        Creates group if needed, handles behaviors, manages queue.
        """
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

    def _get_or_create_group(self, builder: 'ActiveBuilder') -> 'LayerGroup':
        """Get existing group or create new one for this builder"""
        layer = builder.config.layer_name

        if layer in self._layer_groups:
            group = self._layer_groups[layer]
            # Update input_type in case it changed (important for groups that exist across different contexts)
            group.input_type = builder.config.input_type
            return group

        # Create new group
        group = LayerGroup(
            layer_name=layer,
            property=builder.config.property,
            mode=builder.config.mode,
            layer_type=builder.config.layer_type,
            order=builder.config.order,
            input_type=builder.config.input_type
        )

        # Initialize base layer accumulated_value from actual base state
        # This ensures that when groups are recreated after deletion, they start with correct values
        if group.is_base:
            # Get input_type from group to determine which base state to use
            input_type = group.input_type

            if input_type == "scroll":
                # Scroll input_type - use scroll base state
                if builder.config.property == "speed":
                    group.accumulated_value = self._base_scroll_speed
                elif builder.config.property == "direction":
                    group.accumulated_value = self._base_scroll_direction.copy()
            else:
                # Mouse movement input_type (default)
                if builder.config.property == "speed":
                    group.accumulated_value = self._base_speed
                elif builder.config.property == "direction":
                    group.accumulated_value = self._base_direction.copy()
                elif builder.config.property == "pos":
                    # Position uses absolute coordinates, keep at (0,0) for accumulated
                    pass
        # Initialize override mode layers with current computed value
        # so interpolation starts from current state, not zero
        elif builder.config.mode == "override":
            if builder.config.property == "speed":
                # Get current computed speed (base + all modifier layers)
                group.accumulated_value = self._compute_velocity()[0]
            elif builder.config.property == "direction":
                # Get current computed direction (base + all modifier layers)
                group.accumulated_value = self._compute_velocity()[1]
            elif builder.config.property == "vector":
                # Get current computed velocity (direction * speed from all layers)
                speed, direction = self._compute_velocity()
                group.accumulated_value = direction * speed
            elif builder.config.property == "pos":
                # Get current computed position
                pos, _, _, _, _, _ = self._compute_current_state()
                group.accumulated_value = pos

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
        if isinstance(target1, (int, float)) and isinstance(target2, (int, float)):
            return abs(target1 - target2) < EPSILON
        elif isinstance(target1, tuple) and isinstance(target2, tuple):
            return all(abs(a - b) < EPSILON for a, b in zip(target1, target2))
        elif is_vec2(target1) and is_vec2(target2):
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

        # Get input_type from group
        input_type = group.input_type

        # Route to correct base state based on input_type
        if input_type == "scroll":
            # Apply to scroll base state
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
            # Apply to mouse movement base state (default input_type)
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
        if layer in self._layer_groups:
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
        input_type = getattr(builder.config, 'input_type', 'move')

        # Route to correct base state based on input_type
        if input_type == "scroll":
            # Bake to scroll base state
            if prop == "vector":
                self._base_scroll_speed, self._base_scroll_direction = mode_operations.apply_vector_mode(
                    mode, current_value, self._base_scroll_speed, self._base_scroll_direction
                )
            elif prop == "speed":
                self._base_scroll_speed = mode_operations.apply_scalar_mode(mode, current_value, self._base_scroll_speed)
            elif prop == "direction":
                self._base_scroll_direction = mode_operations.apply_direction_mode(mode, current_value, self._base_scroll_direction)
        else:
            # Bake to mouse movement base state (default input_type)
            if prop == "vector":
                # Decompose vector into speed and direction
                self._base_speed, self._base_direction = mode_operations.apply_vector_mode(
                    mode, current_value, self._base_speed, self._base_direction
                )

            elif prop == "speed":
                self._base_speed = mode_operations.apply_scalar_mode(mode, current_value, self._base_speed)

            elif prop == "direction":
                self._base_direction = mode_operations.apply_direction_mode(mode, current_value, self._base_direction)

        # Position is input_type-agnostic (only used for mouse currently)
        if prop == "pos":
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

    def _bake_property(self, property_name: str, layer: Optional[str] = None, input_type: str = "move"):
        """Bake current computed value of a property into base state

        Args:
            property_name: The property to bake ("speed", "direction", "pos")
            layer: Optional layer to bake. If specified, bakes computed state and removes that layer.
                   If None, bakes computed state and removes all layers for this property.
            input_type: "move" for mouse movement, "scroll" for scroll
        """
        is_scroll = input_type == "scroll"

        # Read from the correct computed state
        if is_scroll:
            attr_prefix = "scroll_"
        else:
            attr_prefix = ""
        current_value = getattr(self, f"{attr_prefix}{property_name}")

        # Write to the correct base state
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

        # Remove the specified layer or all layers for this property
        if layer:
            # Remove specific layer
            if layer in self._layer_groups:
                del self._layer_groups[layer]
            if layer in self._layer_orders:
                del self._layer_orders[layer]
        else:
            # Remove all layer groups affecting this property and input_type
            layers_to_remove = [
                l for l, g in self._layer_groups.items()
                if g.property == property_name and getattr(g, 'input_type', 'move') == input_type
            ]
            for l in layers_to_remove:
                if l in self._layer_groups:
                    del self._layer_groups[l]
                if l in self._layer_orders:
                    del self._layer_orders[l]

    def _compute_current_state(self) -> tuple[Vec2, float, Vec2, float, Vec2, bool]:
        """Compute current state by applying all active layers to base.

        Computation order:
        1. Start with base values
        2. Process base layer operations
        3. Process user layers (in order)

        Returns:
            (position, speed, direction, scroll_speed, scroll_direction, pos_is_override)
            pos_is_override is True if any position builder used override mode
        """
        # Start with base
        pos = Vec2(self._absolute_base_pos.x, self._absolute_base_pos.y) if self._absolute_base_pos else Vec2(0, 0)
        speed = self._base_speed
        direction = Vec2(self._base_direction.x, self._base_direction.y)
        scroll_speed = self._base_scroll_speed
        scroll_direction = Vec2(self._base_scroll_direction.x, self._base_scroll_direction.y)
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
            pos, speed, direction, scroll_speed, scroll_direction, override = self._apply_group(group, pos, speed, direction, scroll_speed, scroll_direction)
            pos_is_override = pos_is_override or override

        for group in user_groups:
            pos, speed, direction, scroll_speed, scroll_direction, override = self._apply_group(group, pos, speed, direction, scroll_speed, scroll_direction)
            pos_is_override = pos_is_override or override

        return (pos, speed, direction, scroll_speed, scroll_direction, pos_is_override)

    def _apply_group(
        self,
        group: 'LayerGroup',
        pos: Vec2,
        speed: float,
        direction: Vec2,
        scroll_speed: float,
        scroll_direction: Vec2
    ) -> tuple[Vec2, float, Vec2, float, Vec2, bool]:
        """Apply a layer group's aggregated value

        Args:
            group: The layer group to apply
            pos, speed, direction: Current accumulated state values
            scroll_speed, scroll_direction: Current scroll state values

        Returns:
            Updated (pos, speed, direction, scroll_speed, scroll_direction, pos_is_override)
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

        # Check input_type first to route properly
        input_type = group.input_type

        if input_type == "scroll":
            # Apply to scroll state only
            if prop == "speed":
                scroll_speed = mode_operations.apply_scalar_mode(mode, current_value, scroll_speed)
            elif prop == "direction":
                scroll_direction = mode_operations.apply_direction_mode(mode, current_value, scroll_direction)
            elif prop == "vector":
                scroll_speed, scroll_direction = mode_operations.apply_vector_mode(mode, current_value, scroll_speed, scroll_direction)
        else:
            # Apply to mouse movement state (default 'move' input_type)
            if prop == "speed":
                speed = mode_operations.apply_scalar_mode(mode, current_value, speed)
            elif prop == "direction":
                direction = mode_operations.apply_direction_mode(mode, current_value, direction)
            elif prop == "vector":
                speed, direction = mode_operations.apply_vector_mode(mode, current_value, speed, direction)

        # Position is input_type-agnostic (only used for mouse currently)
        if prop == "pos":
            pos = mode_operations.apply_position_mode(mode, current_value, pos)
            pos_is_override = (mode == "override")

        return pos, speed, direction, scroll_speed, scroll_direction, pos_is_override

    def _compute_velocity(self) -> tuple[float, Vec2]:
        """Compute current velocity from speed and direction builders.

        Returns:
            (speed, direction) tuple for mouse movement input_type only
        """
        speed = self._base_speed
        direction = Vec2(self._base_direction.x, self._base_direction.y)

        # Separate groups by layer type
        base_groups = []
        user_groups = []
        emit_groups = []

        for layer_name, group in self._layer_groups.items():
            # Only process velocity for 'move' input_type (mouse movement)
            if group.property in ("speed", "direction", "vector"):
                # Check input_type
                if group.input_type != 'move':
                    continue  # Skip scroll and other input_types

                if group.is_emit_layer:
                    # Emit layers are pure additive offsets processed separately
                    emit_groups.append(group)
                elif group.is_base:
                    base_groups.append(group)
                else:
                    user_groups.append(group)

        # Sort user layers by order
        def get_layer_order(group: 'LayerGroup') -> int:
            return group.order if group.order is not None else 999999

        user_groups = sorted(user_groups, key=get_layer_order)

        # Apply all velocity groups (excluding emit layers)
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

        # Add emit layer contributions as pure vector offsets (after base velocity computed)
        if emit_groups:
            base_velocity = direction * speed
            for group in emit_groups:
                if group.property == "vector" and group.mode == "offset":
                    emit_offset = group.get_current_value()
                    base_velocity = base_velocity + emit_offset

            # Recompute speed and direction from combined velocity
            speed = base_velocity.magnitude()
            if speed > EPSILON:
                direction = base_velocity.normalized()

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

        # Apply replace clamping if any pos.offset group has a replace_target
        for layer_name, group in self._layer_groups.items():
            if group.property != "pos":
                continue
            if not group.builders:
                continue
            first_builder = group.builders[0]
            if first_builder.config.movement_type == "relative" and group.replace_target is not None:
                # Clamp: committed + current should not exceed replace_target
                # For relative, we need to clamp the total accumulated movement

                # Current total that will be accumulated: committed + what we're about to add
                # We need to ensure that doesn't exceed replace_target
                projected_total = group.committed_value + relative_delta

                # Clamp to replace_target
                clamped_total = Vec2(
                    max(-abs(group.replace_target.x), min(abs(group.replace_target.x), projected_total.x)),
                    max(-abs(group.replace_target.y), min(abs(group.replace_target.y), projected_total.y))
                )

                # The delta we can actually apply is: clamped_total - committed
                clamped_delta = clamped_total - group.committed_value

                # Replace relative_delta with the clamped version
                relative_delta = clamped_delta
                break  # Only one pos.offset group should have replace_target

        return has_absolute_position, absolute_target, relative_delta, relative_position_updates

    def _process_scroll_position_builders(self) -> tuple[Vec2, list]:
        """Process all scroll_pos builders (one-time scroll) and gather their contributions

        Returns:
            - scroll_delta: Accumulated delta from all scroll.by() builders
            - scroll_position_updates: List of (builder, new_value, new_int_value) for tracking updates
        """
        scroll_delta = Vec2(0, 0)
        scroll_position_updates = []

        for layer_name, group in self._layer_groups.items():
            if group.property != "scroll_pos":
                continue

            if not group.builders:
                continue

            # scroll_pos only supports relative (by) operations
            for builder in group.builders:
                current_interpolated = builder.get_interpolated_value()

                # Initialize tracking attributes if needed
                if not hasattr(builder, '_last_emitted_scroll_pos'):
                    builder._last_emitted_scroll_pos = Vec2(0, 0)
                if not hasattr(builder, '_total_emitted_scroll_int'):
                    builder._total_emitted_scroll_int = Vec2(0, 0)

                # Compute delta accounting for accumulated error (subpixel accuracy)
                target_total = current_interpolated
                actual_delta = target_total - builder._last_emitted_scroll_pos

                scroll_delta += actual_delta

                # Store update to apply after builder removal check
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

    def _emit_scroll(self, scroll_pos_delta: Optional[Vec2] = None):
        """Emit scroll events based on velocity and/or one-time scroll delta

        Args:
            scroll_pos_delta: Additional scroll from scroll.by() builders
        """
        scroll_speed = self.scroll_speed.current
        scroll_direction = self.scroll_direction.current

        # Compute scroll velocity vector
        scroll_velocity = scroll_direction * scroll_speed

        # Add scroll position delta if provided
        if scroll_pos_delta is not None:
            scroll_velocity = scroll_velocity + scroll_pos_delta

        # Skip if no scroll
        if abs(scroll_velocity.x) < 0.01 and abs(scroll_velocity.y) < 0.01:
            return

        mouse_scroll_native(scroll_velocity.x, scroll_velocity.y)

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
        expected = self._expected_mouse_pos
        if expected is not None:
            current_x, current_y = ctrl.mouse_pos()
            expected_x, expected_y = expected

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

        # Process pending debounce builders
        self._check_debounce_pending(current_time)

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

        # 3.1. Process scroll position builders (one-time scroll)
        scroll_pos_delta, scroll_position_updates = self._process_scroll_position_builders()

        # 3.2. Emit scroll events (velocity + one-time delta)
        self._emit_scroll(scroll_pos_delta if scroll_pos_delta.magnitude() > 0.001 else None)

        # 3.5. Update committed_value for pos.offset groups with replace_target
        for group in self._layer_groups.values():
            if group.property == "pos" and group.replace_target is not None:
                if group.builders and group.builders[0].config.movement_type == "relative":
                    group.committed_value += relative_delta

        # 4. Update tracking BEFORE checking for completion to avoid double-emission
        # We update unconditionally here since the deltas were already emitted
        for builder, new_value, new_int_value in relative_position_updates:
            builder._last_emitted_relative_pos = new_value
            builder._total_emitted_int = new_int_value

        # 4.1. Update scroll position tracking
        for builder, new_value, _ in scroll_position_updates:
            builder._last_emitted_scroll_pos = new_value

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
        """Advance all groups and track phase transitions.

        Args:
            current_time: Current timestamp from perf_counter() (captured once per frame)

        Returns:
            List of (builder, completed_phase) tuples for callbacks
        """
        phase_transitions = []

        for layer, group in list(self._layer_groups.items()):
            # Advance the group (which advances all builders)
            group_transitions, builders_to_remove = group.advance(current_time)
            phase_transitions.extend(group_transitions)

            # Store bake results for _remove_completed_builders to use
            if not hasattr(group, '_pending_bake_results'):
                group._pending_bake_results = []
            group._pending_bake_results.extend(builders_to_remove)

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
                    # For relative position builders, emit any remaining delta
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
                    # Builder is complete/reverted but didn't have a phase transition this frame
                    # (revert completed in a previous frame, or instant completion)
                    builders_to_remove.append(builder)

            # Process pending bake results (from advance())
            if hasattr(group, '_pending_bake_results'):
                for builder, bake_result in group._pending_bake_results:
                    if builder in group.builders:  # Only process if still in group
                        if bake_result == "bake_to_base":
                            self._bake_group_to_base(group)
                group._pending_bake_results = []

            # Remove completed builders from group
            for builder in builders_to_remove:
                # Don't call on_builder_complete again - already called in advance()
                # Actually remove the builder from the group
                group.remove_builder(builder)

            # Check if group should be removed
            if not group.should_persist():
                if layer in self._layer_groups:
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
        if not should_be_active:
            self._stop_frame_loop()


    def _ensure_frame_loop_running(self):
        """Start frame loop if not already running"""
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
        # Fast path: mouse movement speed is non-zero
        if self._base_speed != 0:
            return True

        # Fast path: scroll speed is non-zero
        if self._base_scroll_speed != 0:
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
        if has_movement:
            return True

        # Check if any builder has an incomplete lifecycle
        for group in self._layer_groups.values():
            for builder in group.builders:
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
    class CardinalPropertyState:
        """Smart accessor for direction_cardinal with .current and .target"""
        def __init__(self, rig_state: 'RigState', current_cardinal: Optional[str]):
            self._rig_state = rig_state
            self._current_cardinal = current_cardinal

        @property
        def current(self) -> Optional[str]:
            """Current cardinal direction"""
            return self._current_cardinal

        @property
        def target(self) -> Optional[str]:
            """Target cardinal direction from base.direction animation"""
            # Find base.direction layer group
            layer_name = "base.direction"
            if layer_name in self._rig_state._layer_groups:
                group = self._rig_state._layer_groups[layer_name]
                if len(group.builders) > 0:
                    for builder in group.builders:
                        if not builder.lifecycle.is_complete():
                            # Get target direction and convert to cardinal
                            target_dir = builder.target_value
                            if is_vec2(target_dir):
                                return self._rig_state._get_cardinal_direction(target_dir)
            return None

        def __repr__(self):
            return f"CardinalPropertyState(current={self._current_cardinal}, target={self.target})"

        def __str__(self):
            return str(self._current_cardinal)

        def __eq__(self, other):
            if isinstance(other, RigState.CardinalPropertyState):
                return self._current_cardinal == other._current_cardinal
            return self._current_cardinal == other

        def __ne__(self, other):
            return not self.__eq__(other)

        def __bool__(self):
            return self._current_cardinal is not None

    @property
    def direction_cardinal(self) -> 'RigState.CardinalPropertyState':
        """Current direction as cardinal/intercardinal string

        Returns one of: "right", "left", "up", "down",
                       "up_right", "up_left", "down_right", "down_left"
        or None if direction is zero vector.
        """
        direction_vec = self._compute_current_state()[2]
        cardinal = self._get_cardinal_direction(direction_vec)
        # Use RigState prefix to access nested class
        return RigState.CardinalPropertyState(self, cardinal)

    class LayersView:
        """Dict-like read-only view of active layers.

        Returns None for missing keys instead of raising KeyError,
        since layers are transient and may not be active.
        """
        __slots__ = ('_groups',)

        def __init__(self, groups):
            self._groups = groups

        def __getitem__(self, name: str) -> Optional['RigState.LayerState']:
            group = self._groups.get(name)
            return RigState.LayerState(group) if group is not None else None

        def get(self, name: str, default=None) -> Optional['RigState.LayerState']:
            group = self._groups.get(name)
            return RigState.LayerState(group) if group is not None else default

        def keys(self):
            return self._groups.keys()

        def values(self):
            return [RigState.LayerState(g) for g in self._groups.values()]

        def items(self):
            return [(k, RigState.LayerState(g)) for k, g in self._groups.items()]

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
    def layers(self) -> 'RigState.LayersView':
        """Dict-like view of active layers (including base layers)

        Access by name to get LayerState or None:
            rig.state.layers["sprint"]  # LayerState or None

        Also supports iteration, len, and containment:
            "sprint" in rig.state.layers
            for name in rig.state.layers: ...
        """
        return RigState.LayersView(self._layer_groups)

    # Layer state access
    class LayerState:
        """State information for a specific layer (backed by LayerGroup)"""
        def __init__(self, group: 'LayerGroup'):
            self._group = group

        def __repr__(self) -> str:
            # Format values based on type
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

            # Add timing info from first builder if available
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
            """What property this layer is affecting: 'speed', 'direction', 'pos'"""
            return self._group.property

        @property
        def mode(self) -> str:
            """Mode of this layer: 'offset', 'override', 'scale'"""
            return self._group.mode

        @property
        def operator(self) -> str:
            """Operator type: 'to', 'by', 'add', 'mult' (from first builder if available)"""
            if self._group.builders:
                return self._group.builders[0].config.operator
            return "accumulated"

        @property
        def current(self):
            """Current value from LayerGroup (includes accumulated + all active builders)"""
            return self._group.get_current_value()

        @property
        def target(self):
            """Final target value after all builders complete (from LayerGroup)"""
            return self._group.target

        @property
        def time_alive(self) -> float:
            """Time in seconds since this layer was created"""
            return time.perf_counter() - self._group.creation_time

        @property
        def time_left(self) -> float:
            """Time in seconds until this layer completes (0 if infinite or no active builders)"""
            if not self._group.builders:
                return 0  # No active animation

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
                return 0  # Infinite/no timing

            elapsed_ms = builder.time_alive * 1000
            remaining_ms = max(0, total_duration - elapsed_ms)
            return remaining_ms / 1000

        def __getattr__(self, name: str):
            """Provide helpful error messages for invalid attributes"""
            raise AttributeError(
                f"LayerState has no attribute '{name}'. "
                f"Available attributes: {', '.join(VALID_LAYER_STATE_ATTRS)}"
            )

    # Base state access
    class BasePropertyState:
        """Smart accessor for base state properties with .current and .target"""
        def __init__(self, rig_state: 'RigState', property_name: str, base_value):
            self._rig_state = rig_state
            self._property_name = property_name
            self._base_value = base_value

        @property
        def current(self):
            """Current baked base value"""
            return self._base_value

        @property
        def target(self):
            """Target value from base layer animation (None if no base animation)"""
            # Find base.{property} layer group
            layer_name = f"base.{self._property_name}"
            if layer_name in self._rig_state._layer_groups:
                group = self._rig_state._layer_groups[layer_name]
                if len(group.builders) > 0:
                    # Return target of first active builder
                    for builder in group.builders:
                        if not builder.lifecycle.is_complete():
                            return builder.target_value
            return None

        def __repr__(self):
            return f"BasePropertyState('{self._property_name}', value={self._base_value}, target={self.target})"

        def __str__(self):
            return str(self._base_value)

        # Magic methods to make BasePropertyState behave like the underlying value
        def __add__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value + other_val

        def __radd__(self, other):
            return other + self._base_value

        def __sub__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value - other_val

        def __rsub__(self, other):
            return other - self._base_value

        def __mul__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value * other_val

        def __rmul__(self, other):
            return other * self._base_value

        def __truediv__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value / other_val

        def __rtruediv__(self, other):
            return other / self._base_value

        def __eq__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value == other_val

        def __ne__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value != other_val

        def __lt__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value < other_val

        def __le__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value <= other_val

        def __gt__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value > other_val

        def __ge__(self, other):
            other_val = other.current if isinstance(other, (RigState.BasePropertyState, RigState.SmartPropertyState)) else other
            return self._base_value >= other_val

        def __float__(self):
            return float(self._base_value)

        def __int__(self):
            return int(self._base_value)

        def __bool__(self):
            return bool(self._base_value)

        def __getattr__(self, name):
            """Delegate attribute/method access to the underlying value (e.g., Vec2 methods)"""
            return getattr(self._base_value, name)

    class BaseState:
        def __init__(self, rig_state: 'RigState'):
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
        def pos(self) -> 'RigState.BasePropertyState':
            base_pos = self._rig_state._absolute_base_pos if self._rig_state._absolute_base_pos else Vec2(0, 0)
            return RigState.BasePropertyState(self._rig_state, "pos", base_pos)

        @property
        def speed(self) -> 'RigState.BasePropertyState':
            return RigState.BasePropertyState(self._rig_state, "speed", self._rig_state._base_speed)

        @property
        def direction(self) -> 'RigState.BasePropertyState':
            return RigState.BasePropertyState(self._rig_state, "direction", self._rig_state._base_direction)

        @property
        def direction_cardinal(self) -> 'RigState.CardinalPropertyState':
            """Base direction as cardinal/intercardinal string"""
            cardinal = self._rig_state._get_cardinal_direction(self._rig_state._base_direction)
            return RigState.CardinalPropertyState(self._rig_state, cardinal)

        @property
        def vector(self) -> 'RigState.BasePropertyState':
            """Base velocity vector (speed * direction)"""
            base_vector = self._rig_state._base_direction * self._rig_state._base_speed
            return RigState.BasePropertyState(self._rig_state, "vector", base_vector)
            """Base velocity vector (speed * direction)"""
            base_vector = self._rig_state._base_direction * self._rig_state._base_speed
            return RigState.BasePropertyState(self._rig_state, "vector", base_vector)

        @property
        def scroll(self) -> 'RigState.BaseScrollPropertyContainer':
            """Base scroll property container"""
            return RigState.BaseScrollPropertyContainer(self._rig_state)

    class BaseScrollPropertyContainer:
        """Container for base scroll properties (pos, speed, direction, vector)"""
        def __init__(self, rig_state: 'RigState'):
            self._rig_state = rig_state

        @property
        def pos(self) -> 'RigState.BasePropertyState':
            """Base scroll amount (one-time scroll, like pos for movement)"""
            # Note: For now, scroll doesn't have a separate 'pos' base value like movement does
            # So we return the scroll_vector as the base scroll amount
            base_scroll_amount = self._rig_state._base_scroll_direction * self._rig_state._base_scroll_speed
            return RigState.BasePropertyState(self._rig_state, "scroll", base_scroll_amount)

        @property
        def speed(self) -> 'RigState.BasePropertyState':
            return RigState.BasePropertyState(self._rig_state, "scroll_speed", self._rig_state._base_scroll_speed)

        @property
        def direction(self) -> 'RigState.BasePropertyState':
            return RigState.BasePropertyState(self._rig_state, "scroll_direction", self._rig_state._base_scroll_direction)

        @property
        def direction_cardinal(self) -> 'RigState.CardinalPropertyState':
            """Base scroll direction as cardinal/intercardinal string"""
            cardinal = self._rig_state._get_cardinal_direction(self._rig_state._base_scroll_direction)
            return RigState.CardinalPropertyState(self._rig_state, cardinal)

        @property
        def vector(self) -> 'RigState.BasePropertyState':
            """Base scroll vector (scroll_speed * scroll_direction)"""
            base_scroll_vector = self._rig_state._base_scroll_direction * self._rig_state._base_scroll_speed
            return RigState.BasePropertyState(self._rig_state, "scroll_vector", base_scroll_vector)

        # Shortcuts to match scroll API
        @property
        def current(self):
            """Current base scroll vector value"""
            return self._rig_state._base_scroll_direction * self._rig_state._base_scroll_speed

        @property
        def target(self):
            """Target value from base scroll animation (None if no base animation)"""
            # Check for base.scroll layer
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
            """X component of the base scroll vector"""
            return self.current.x

        @property
        def y(self):
            """Y component of the base scroll vector"""
            return self.current.y

        def __repr__(self):
            return f"({self.current.x:.2f}, {self.current.y:.2f})"

        def __str__(self):
            return self.__repr__()

    @property
    def base(self) -> 'RigState.BaseState':
        """Access to base (baked) state only"""
        return RigState.BaseState(self)

    # Scroll property container for computed values
    class ScrollPropertyContainer:
        """Container for scroll properties with nested access to pos, speed, direction, vector"""
        def __init__(self, rig_state: 'RigState'):
            self._rig_state = rig_state

        @property
        def pos(self) -> 'RigState.SmartPropertyState':
            """Scroll amount (one-time scroll, like pos for movement) with layer access"""
            # Note: For now, scroll doesn't have a separate 'pos' computed value
            # So we return the computed scroll amount
            scroll_speed = self._rig_state._compute_current_state()[3]
            scroll_direction = self._rig_state._compute_current_state()[4]
            return RigState.SmartPropertyState(self._rig_state, "scroll", scroll_direction * scroll_speed)

        @property
        def speed(self) -> 'RigState.SmartPropertyState':
            """Current computed scroll speed (with .offset, .override, .scale layer access)"""
            scroll_speed_val = self._rig_state._compute_current_state()[3]
            return RigState.SmartPropertyState(self._rig_state, "scroll_speed", scroll_speed_val)

        @property
        def direction(self) -> 'RigState.SmartPropertyState':
            """Current computed scroll direction (with .offset, .override, .scale layer access)"""
            scroll_direction_vec = self._rig_state._compute_current_state()[4]
            return RigState.SmartPropertyState(self._rig_state, "scroll_direction", scroll_direction_vec)

        @property
        def direction_cardinal(self) -> 'RigState.CardinalPropertyState':
            """Computed scroll direction as cardinal/intercardinal string"""
            scroll_direction_vec = self._rig_state._compute_current_state()[4]
            cardinal = self._rig_state._get_cardinal_direction(scroll_direction_vec)
            return RigState.CardinalPropertyState(self._rig_state, cardinal)

        @property
        def vector(self) -> 'RigState.SmartPropertyState':
            """Current computed scroll vector (with .offset, .override, .scale layer access)"""
            scroll_speed = self._rig_state._compute_current_state()[3]
            scroll_direction = self._rig_state._compute_current_state()[4]
            return RigState.SmartPropertyState(self._rig_state, "scroll_vector", scroll_direction * scroll_speed)

        # Direct value access (matching scroll API)
        @property
        def current(self):
            """Current computed scroll vector value"""
            scroll_speed = self._rig_state._compute_current_state()[3]
            scroll_direction = self._rig_state._compute_current_state()[4]
            return scroll_direction * scroll_speed

        @property
        def target(self):
            """Target value from base scroll animation (None if no base animation)"""
            # Check for base.scroll or base.scroll_vector layer
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
            """X component of the computed scroll vector"""
            return self.current.x

        @property
        def y(self):
            """Y component of the computed scroll vector"""
            return self.current.y

        def __repr__(self):
            return f"({self.current.x:.2f}, {self.current.y:.2f})"

        def __str__(self):
            return self.__repr__()

    # Smart property accessors for computed values with layer mode access
    class SmartPropertyState:
        """Smart accessor that provides both computed value and layer mode states"""
        def __init__(self, rig_state: 'RigState', property_name: str, computed_value):
            self._rig_state = rig_state
            self._property_name = property_name
            self._computed_current = computed_value

        @property
        def current(self):
            """Current computed value (includes all layers)"""
            return self._computed_current

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
            """X component of the computed value (shortcut to .current.x)"""
            if not hasattr(self._computed_current, 'x'):
                raise AttributeError(f"Property '{self._property_name}' is a scalar and doesn't have .x component. Only Vec2 properties (pos, direction, vector) support .x/.y shortcuts.")
            return self._computed_current.x

        @property
        def y(self):
            """Y component of the computed value (shortcut to .current.y)"""
            if not hasattr(self._computed_current, 'y'):
                raise AttributeError(f"Property '{self._property_name}' is a scalar and doesn't have .y component. Only Vec2 properties (pos, direction, vector) support .x/.y shortcuts.")
            return self._computed_current.y

        # Layer mode accessors
        @property
        def offset(self) -> Optional['RigState.LayerState']:
            """Get implicit layer state for .offset mode"""
            layer_name = f"{self._property_name}.offset"
            return self._rig_state.layers[layer_name]

        @property
        def override(self) -> Optional['RigState.LayerState']:
            """Get implicit layer state for .override mode"""
            layer_name = f"{self._property_name}.override"
            return self._rig_state.layers[layer_name]

        @property
        def scale(self) -> Optional['RigState.LayerState']:
            """Get implicit layer state for .scale mode"""
            layer_name = f"{self._property_name}.scale"
            return self._rig_state.layers[layer_name]

        def __repr__(self):
            # Show available properties/methods, not the computed value
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

        # Magic methods to make SmartPropertyState behave like the underlying value
        # in mathematical operations (auto-delegates to .current)
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

        # Comparison operators
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

        # Numeric conversion
        def __float__(self):
            return float(self._computed_current)

        def __int__(self):
            return int(self._computed_current)

        def __bool__(self):
            return bool(self._computed_current)

        def __getattr__(self, name):
            """Delegate attribute/method access to the underlying computed value

            This allows Vec2 methods like .to_cardinal(), .normalized(), etc. to work
            on SmartPropertyState objects transparently.
            """
            return getattr(self._computed_current, name)

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

    @property
    def scroll_speed(self) -> 'RigState.SmartPropertyState':
        """Current computed scroll speed (with .offset, .override, .scale layer access)"""
        scroll_speed_val = self._compute_current_state()[3]
        return RigState.SmartPropertyState(self, "speed", scroll_speed_val)

    @property
    def scroll_direction(self) -> 'RigState.SmartPropertyState':
        """Current computed scroll direction (with .offset, .override, .scale layer access)"""
        scroll_direction_vec = self._compute_current_state()[4]
        return RigState.SmartPropertyState(self, "direction", scroll_direction_vec)

    @property
    def scroll_vector(self) -> 'RigState.SmartPropertyState':
        """Current computed scroll vector (with .offset, .override, .scale layer access)"""
        scroll_speed = self._compute_current_state()[3]
        scroll_direction = self._compute_current_state()[4]
        return RigState.SmartPropertyState(self, "vector", scroll_direction * scroll_speed)

    @property
    def scroll(self) -> 'RigState.ScrollPropertyContainer':
        """Scroll property container with nested access to pos, speed, direction, vector"""
        return RigState.ScrollPropertyContainer(self)

    def button_prime(self, button: int):
        """Prime a mouse button to press on next movement and release on stop.

        Args:
            button: Mouse button index (0=left, 1=right, 2=middle)
        """
        self._primed_button = button

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

        # Clear primed button if unused
        self._primed_button = None

        # 3. Decelerate speed to 0
        if transition_ms is None or transition_ms == 0:
            # Immediate stop
            self._base_speed = 0.0
            self._base_scroll_speed = 0.0
            # Stop frame loop if no active groups
            if len(self._layer_groups) == 0:
                self._stop_frame_loop()
        else:
            # Smooth deceleration - create base layer builders for both mouse and scroll
            from .builder import ActiveBuilder

            # Mouse speed deceleration
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

            # Scroll speed deceleration
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

    def add_scroll_stop_callback(self, callback):
        """Add a callback to fire when scroll stops"""
        self._scroll_stop_callbacks.append(callback)

    def scroll_stop(self, transition_ms: Optional[float] = None, easing: str = "linear", **kwargs):
        """Stop scrolling: bake scroll layers, clear scroll effects, decelerate scroll to 0

        Similar to stop() but only affects scroll-related state:
        1. Bake scroll layers into base
        2. Clear scroll-related layer groups
        3. Set scroll speed to 0 (with optional smooth deceleration)
        """
        # Validate arguments
        transition_ms = validate_timing(transition_ms, 'transition_ms', method='scroll_stop')

        config = BuilderConfig()
        all_kwargs = {'easing': easing, **kwargs}
        config.validate_method_kwargs('stop', **all_kwargs)

        # 1. Bake scroll-related layers into base
        scroll_layers = [
            layer for layer, group in self._layer_groups.items()
            if group.input_type == "scroll"
        ]
        for layer in scroll_layers:
            group = self._layer_groups[layer]
            if group.is_base:
                self._bake_group_to_base(group)

        # 2. Clear scroll-related layer groups
        for layer in scroll_layers:
            del self._layer_groups[layer]
            if layer in self._layer_orders:
                del self._layer_orders[layer]

        # 3. Decelerate scroll speed to 0
        if transition_ms is None or transition_ms == 0:
            # Immediate stop
            self._base_scroll_speed = 0.0
            # Fire scroll stop callbacks
            for callback in self._scroll_stop_callbacks:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in scroll stop callback: {e}")
            self._scroll_stop_callbacks.clear()
            # Stop frame loop if no active groups remain
            if len(self._layer_groups) == 0 and self._base_speed == 0:
                self._stop_frame_loop()
        else:
            # Smooth deceleration
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

    def reverse(self, transition_ms: Optional[float] = None):
        """Reverse direction (180 degrees turn)"""
        # This will be implemented via builder in builder.py
        pass

    def bake_all(self):
        """Bake all active mouse movement builders immediately (not scroll)"""
        # Compute final values for all mouse movement properties that have active layers
        properties_to_bake = set()
        for group in self._layer_groups.values():
            if getattr(group, 'input_type', 'move') == 'move':
                properties_to_bake.add(group.property)

        # Bake computed values into base state
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

        # Remove only mouse movement layers
        for layer in list(self._layer_groups.keys()):
            group = self._layer_groups.get(layer)
            if group and getattr(group, 'input_type', 'move') == 'move':
                self.remove_builder(layer, bake=False)

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

        # Remove only scroll layers
        for layer in list(self._layer_groups.keys()):
            group = self._layer_groups.get(layer)
            if group and getattr(group, 'input_type', 'move') == 'scroll':
                self.remove_builder(layer, bake=False)

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
        self._base_scroll_speed = 0.0
        self._base_scroll_direction = Vec2(0, 1)
        self._absolute_base_pos = None
        self._absolute_current_pos = None

        # Reset subpixel tracking
        self._subpixel_adjuster.reset()

        # Reset manual movement tracking
        self._last_manual_movement_time = None
        self._expected_mouse_pos = None

        # Reset auto-order counter
        self._next_auto_order = 0

        # Clear stop callbacks and primed button
        self._stop_callbacks.clear()
        self._scroll_stop_callbacks.clear()
        self._primed_button = None

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

            if current_time is None:
                current_time = time.perf_counter()

            if group.builders:
                # Trigger revert on all active builders in the group
                for builder in group.builders:
                    builder.lifecycle.trigger_revert(current_time, revert_ms, easing)
            else:
                # No active builders, but group has accumulated_value
                # Create a revert builder to transition accumulated_value to zero
                if not group.is_base and not group._is_reverted_to_zero():
                    from .builder import BuilderConfig, ActiveBuilder
                    from .contracts import LayerType

                    # Create a builder config that represents the current accumulated state
                    config = BuilderConfig()
                    config.layer_name = layer
                    config.layer_type = group.layer_type
                    config.property = group.property
                    config.mode = group.mode
                    config.input_type = group.input_type
                    config.operator = "to"

                    # Set target value to current accumulated value
                    if is_vec2(group.accumulated_value):
                        config.value = (group.accumulated_value.x, group.accumulated_value.y)
                    else:
                        config.value = group.accumulated_value

                    # No over phase, immediately start reverting
                    config.over_ms = 0
                    config.revert_ms = revert_ms if revert_ms is not None else 0
                    config.revert_easing = easing
                    config.is_synchronous = False

                    # Zero out accumulated value — the revert builder takes sole
                    # ownership of the value during its transition back to zero.
                    if is_vec2(group.accumulated_value):
                        group.accumulated_value = Vec2(0, 0)
                    else:
                        group.accumulated_value = 0.0

                    # Create the builder
                    builder = ActiveBuilder(config, self, is_base_layer=False)

                    # Configure lifecycle to start directly in REVERT phase
                    # Skip over phase by setting over_ms to 0, force revert phase
                    builder.lifecycle.start(current_time)
                    builder.lifecycle.phase = LifecyclePhase.REVERT
                    builder.lifecycle.phase_start_time = current_time

                    # Now add it to the group
                    self.add_builder(builder)

            self._ensure_frame_loop_running()
