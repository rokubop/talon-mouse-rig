"""State management for mouse rig V2

Unified state manager with:
- Base state (baked values)
- Active builders (temporary modifications)
- Queue system
- Frame loop
"""

import time
from typing import Optional, TYPE_CHECKING
from talon import cron, ctrl
from .core import Vec2, SubpixelAdjuster, mouse_move
from .queue import QueueManager
from .lifecycle import Lifecycle, LifecyclePhase, PropertyAnimator

if TYPE_CHECKING:
    from .builder import ActiveBuilder


class RigState:
    """Core state manager for the mouse rig"""

    def __init__(self):
        print(f"DEBUG: Creating NEW RigState instance")
        # Base state (baked values)
        self._base_pos: Vec2 = Vec2(*ctrl.mouse_pos())
        self._base_speed: float = 0.0
        self._base_direction: Vec2 = Vec2(1, 0)

        # Active builders (layer_name -> ActiveBuilder)
        self._active_builders: dict[str, 'ActiveBuilder'] = {}

        # Layer order tracking (layer_name -> order)
        self._layer_orders: dict[str, int] = {}

        # Track operations per layer per property for processing
        # (layer_name, property, phase) -> list of operations
        # phase is one of: "incoming", "default", "outgoing"
        self._layer_operations: dict[tuple[str, str, str], list] = {}

        # Queue system
        self._queue_manager = QueueManager()

        # Frame loop
        self._cron_job: Optional[cron.CronJob] = None
        self._last_frame_time: Optional[float] = None
        self._subpixel_adjuster = SubpixelAdjuster()

        # Throttle tracking (layer -> last execution time)
        self._throttle_times: dict[str, float] = {}

        # Base layer counter for unique base layer names
        self._base_counter: int = 0
        self._final_counter: int = 0

    def _generate_base_layer_name(self) -> str:
        """Generate unique base layer name for base operations"""
        self._base_counter += 1
        return f"__base_{self._base_counter}"

    def _generate_final_layer_name(self) -> str:
        """Generate unique final layer name for final operations"""
        self._final_counter += 1
        return f"__final_{self._final_counter}"

    def time_alive(self, layer: str) -> Optional[float]:
        """Get time in seconds since builder was created

        Returns None if layer doesn't exist
        """
        if layer in self._active_builders:
            return self._active_builders[layer].time_alive()
        return None

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

        # Handle behavior modes
        behavior = builder.config.get_effective_behavior()

        # User layers: add as child to existing parent
        if not builder.config.is_anonymous() and layer != "__final__" and layer in self._active_builders:
            existing = self._active_builders[layer]

            if behavior == "replace":
                # Replace entire builder
                self.remove_builder(layer)
            elif behavior == "extend":
                # Extend hold duration of parent
                if existing.lifecycle.hold_ms is not None:
                    existing.lifecycle.hold_ms += builder.config.hold_ms or 0
                return
            elif behavior == "throttle":
                # Check throttle timing
                throttle_ms = builder.config.behavior_args[0] if builder.config.behavior_args else 0
                if layer in self._throttle_times:
                    elapsed = (time.perf_counter() - self._throttle_times[layer]) * 1000
                    if elapsed < throttle_ms:
                        return  # Ignore this call
                # Add as child
                existing.add_child(builder)
                return
            elif behavior == "ignore":
                # Ignore if already active
                return
            else:
                # Stack or queue - add as child
                existing.add_child(builder)
                return

        # Base/final layer operations
        if behavior == "replace" and layer in ("__base__", "__final__"):
            # For .to() operator, cancel all base/final builders with same property
            if builder.config.property:
                layers_to_remove = [
                    l for l, b in self._active_builders.items()
                    if l == layer and b.config.property == builder.config.property
                ]
                for l in layers_to_remove:
                    self.remove_builder(l)

        elif behavior == "throttle":
            # Check throttle timing
            throttle_ms = builder.config.behavior_args[0] if builder.config.behavior_args else 0
            if layer in self._throttle_times:
                elapsed = (time.perf_counter() - self._throttle_times[layer]) * 1000
                if elapsed < throttle_ms:
                    return  # Ignore this call

        # Add builder to active set
        self._active_builders[layer] = builder

        # Track order if provided
        if builder.config.order is not None:
            self._layer_orders[layer] = builder.config.order

        # Update throttle time
        self._throttle_times[layer] = time.perf_counter()

        # Check if this builder completes instantly (no lifecycle)
        if builder.lifecycle.is_complete():
            print(f"DEBUG: Builder {layer} completes instantly, anonymous={builder.config.is_anonymous()}")
            # Instant completion - bake immediately for anonymous layers
            if builder.config.is_anonymous():
                if builder.config.get_effective_bake():
                    print(f"DEBUG: Baking {layer} immediately")
                    self._bake_builder(builder)
                # Remove from active set (it was added on line 134)
                del self._active_builders[layer]
            else:
                # User/final layers without lifecycle should stay active
                pass
            return

        # Start frame loop if not running
        print(f"DEBUG: Builder {layer} has lifecycle, starting frame loop. over_ms={builder.config.over_ms}, revert_ms={builder.config.revert_ms}")
        self._ensure_frame_loop_running()

    def remove_builder(self, layer: str):
        """Remove an active builder"""
        if layer in self._active_builders:
            builder = self._active_builders[layer]

            print(f"DEBUG: Removing builder {layer}, has_reverted={builder.lifecycle.has_reverted()}, will_bake={builder.config.get_effective_bake()}")

            # If bake=true, merge values into base
            if builder.config.get_effective_bake():
                self._bake_builder(builder)

            del self._active_builders[layer]

            # Remove order tracking
            if layer in self._layer_orders:
                del self._layer_orders[layer]

            # Notify queue system
            queue_key = layer
            if layer in ("__base__", "__final__"):
                queue_key = f"__queue_{builder.config.property}_{builder.config.operator}"
            self._queue_manager.on_builder_complete(queue_key)

        # Stop frame loop if no active builders AND no movement
        if len(self._active_builders) == 0 and not self._has_movement():
            self._stop_frame_loop()

    def _bake_builder(self, builder: 'ActiveBuilder'):
        """Merge builder's final aggregated value into base state"""
        # If builder has reverted, don't bake (it's already back to base)
        if builder.lifecycle.has_reverted():
            print(f"DEBUG: Builder has reverted, NOT baking")
            return

        print(f"DEBUG: Baking builder - property={builder.config.property}, operator={builder.config.operator}")

        # Get aggregated value (includes own value + children)
        current_value = builder.get_current_value()

        # Get property and operator from builder config (not children)
        prop = builder.config.property
        operator = builder.config.operator

        if prop == "speed":
            if operator == "to":
                self._base_speed = current_value
            elif operator in ("add", "by"):
                self._base_speed += current_value
            elif operator == "sub":
                self._base_speed -= current_value
            elif operator == "mul":
                self._base_speed *= current_value
            elif operator == "div":
                self._base_speed /= current_value if current_value != 0 else 1
        elif prop == "direction":
            # current_value is already the final direction (operation already applied in target_value)
            self._base_direction = current_value
        elif prop == "pos":
            # Position is more complex - update base position
            offset = current_value
            self._base_pos = self._base_pos + offset

        # Ensure frame loop is running if there's movement
        if self._has_movement():
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

            if property_name == "speed":
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

        Computation order (per PRD13):
        1. Start with base values
        2. Process base layer: incoming (no-op) → operations → outgoing (no-op)
        3. Process user layers (in order): incoming → operations → outgoing
        4. Process final layer: incoming (no-op) → operations → outgoing (no-op)

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
            if builder.config.is_anonymous():
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
        """Apply a layer: incoming → operations → outgoing

        Args:
            builder: The builder to apply
            pos, speed, direction: Current accumulated state values

        Returns:
            Updated (pos, speed, direction)
        """
        prop = builder.config.property
        operator = builder.config.operator
        phase = builder.config.phase
        scope = builder.config.scope
        current_value = builder.get_current_value()

        # Check for override scope - ignore accumulated value
        if scope == "override":
            if prop == "speed":
                if operator == "to":
                    speed = current_value
            elif prop == "direction":
                if operator == "to":
                    direction = current_value
            elif prop == "pos":
                if operator == "to":
                    pos = current_value if isinstance(current_value, Vec2) else Vec2.from_tuple(current_value)
            return (pos, speed, direction)

        # Apply operation based on property and phase
        if prop == "speed":
            if phase == "incoming":
                # Multiply input before layer's operations
                speed *= current_value
            elif phase == "outgoing":
                # Multiply output after layer's operations
                speed *= current_value
            elif operator == "to":
                speed = current_value
            elif operator in ("add", "by"):
                speed += current_value
            elif operator == "sub":
                speed -= current_value
            elif operator == "mul":
                # mul on non-has_incoming_outgoing layers (base/final) is ordered operation
                speed *= current_value
            elif operator == "div":
                speed /= current_value if current_value != 0 else 1
            elif operator == "scale":
                # Scale is a retroactive multiplier
                speed *= current_value

        elif prop == "direction":
            if phase == "incoming":
                # Multiply direction components
                direction = Vec2(direction.x * current_value.x, direction.y * current_value.y).normalized()
            elif phase == "outgoing":
                # Multiply direction components
                direction = Vec2(direction.x * current_value.x, direction.y * current_value.y).normalized()
            elif operator == "to":
                direction = current_value
            elif operator in ("add", "by"):
                # Apply rotation
                direction = current_value  # Already computed as rotated direction
            elif operator == "mul":
                # mul on non-has_incoming_outgoing layers (base/final) is ordered operation
                direction = Vec2(direction.x * current_value, direction.y * current_value).normalized()
            elif operator == "scale":
                direction = Vec2(direction.x * current_value, direction.y * current_value).normalized()

        elif prop == "pos":
            if operator in ("add", "by"):
                pos = pos + current_value
            elif operator == "to":
                pos = current_value if isinstance(current_value, Vec2) else Vec2.from_tuple(current_value)

        return (pos, speed, direction)

    def _update_frame(self):
        """Update all active builders and move mouse"""
        now = time.perf_counter()
        if self._last_frame_time is None:
            self._last_frame_time = now
            return

        dt = now - self._last_frame_time
        self._last_frame_time = now

        # Update all builders, remove completed ones
        # Use list() to create a snapshot and avoid "dictionary changed size during iteration"
        completed = []
        for layer, builder in list(self._active_builders.items()):
            if not builder.update(dt):
                completed.append(layer)

        for layer in completed:
            self.remove_builder(layer)

        # Compute current state
        pos, speed, direction = self._compute_current_state()

        # Calculate movement (speed is pixels per frame, not per second)
        if speed != 0:
            velocity = direction * speed
            dx = velocity.x
            dy = velocity.y

            # Apply subpixel adjustment
            dx_int, dy_int = self._subpixel_adjuster.adjust(dx, dy)

            if dx_int != 0 or dy_int != 0:
                current_x, current_y = ctrl.mouse_pos()
                new_x = current_x + dx_int
                new_y = current_y + dy_int
                mouse_move(new_x, new_y)

    def _ensure_frame_loop_running(self):
        """Start frame loop if not already running"""
        if self._cron_job is None:
            # 60 FPS = ~16.67ms per frame
            self._cron_job = cron.interval("16ms", self._update_frame)
            self._last_frame_time = None

    def _stop_frame_loop(self):
        """Stop the frame loop"""
        if self._cron_job is not None:
            cron.cancel(self._cron_job)
            self._cron_job = None
            self._last_frame_time = None
            self._subpixel_adjuster.reset()

    def _has_movement(self) -> bool:
        """Check if there's any movement happening (base speed non-zero)"""
        return self._base_speed != 0

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
        """Get state information for a specific layer

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
        self._layer_operations.clear()
        self._throttle_times.clear()

        # 3. Decelerate speed to 0
        if transition_ms is None or transition_ms == 0:
            # Immediate stop
            self._base_speed = 0.0
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
            self.remove_builder(layer)

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
