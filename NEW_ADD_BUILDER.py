"""New add_builder implementation for LayerGroup architecture

This is the new add_builder method to replace the existing one in state.py
"""

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
        builder.execute_synchronous()
        bake_result = group.on_builder_complete(builder)
        if bake_result == "bake_to_base":
            self._bake_group_to_base(group)
        
        # Clean up empty base groups
        if group.is_base and not group.should_persist():
            del self._layer_groups[layer]


def _get_or_create_group(self, builder: 'ActiveBuilder') -> LayerGroup:
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


def _bake_group_to_base(self, group: LayerGroup):
    """Bake group's accumulated value to base state"""
    value = group.accumulated_value
    prop = group.property
    mode = group.mode
    
    if prop == "speed":
        if mode == "offset":
            self._base_speed += value
        elif mode == "override":
            self._base_speed = value
        elif mode == "scale":
            self._base_speed *= value
    
    elif prop == "direction":
        if mode == "offset":
            # Apply rotation
            import math
            if isinstance(value, (int, float)):
                angle_rad = math.radians(value)
            else:
                # Already a direction vector
                angle_rad = math.atan2(value.y, value.x) - math.atan2(self._base_direction.y, self._base_direction.x)
            
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            new_x = self._base_direction.x * cos_a - self._base_direction.y * sin_a
            new_y = self._base_direction.x * sin_a + self._base_direction.y * cos_a
            self._base_direction = Vec2(new_x, new_y).normalized()
        elif mode == "override":
            self._base_direction = value if isinstance(value, Vec2) else Vec2.from_tuple(value).normalized()
    
    elif prop == "pos":
        if mode == "offset":
            # This is tricky - pos offset in base doesn't make sense
            # We'd need to track absolute position
            pass
        elif mode == "override":
            self._absolute_base_pos = value if isinstance(value, Vec2) else Vec2.from_tuple(value)
