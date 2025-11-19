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
        # Base state (baked values)
        self._base_pos: Vec2 = Vec2(*ctrl.mouse_pos())
        self._base_speed: float = 0.0
        self._base_direction: Vec2 = Vec2(1, 0)
        self._base_accel: float = 0.0

        # Active builders (tag -> ActiveBuilder)
        # Anonymous builders get unique generated tags
        self._active_builders: dict[str, 'ActiveBuilder'] = {}

        # Execution order tracking (for anonymous before tagged)
        self._anonymous_tags: list[str] = []  # Ordered list of anonymous builder tags
        self._tagged_tags: list[str] = []     # Ordered list of named builder tags

        # Queue system
        self._queue_manager = QueueManager()

        # Frame loop
        self._cron_job: Optional[cron.CronJob] = None
        self._last_frame_time: Optional[float] = None
        self._subpixel_adjuster = SubpixelAdjuster()

        # Tag counter for anonymous builders
        self._tag_counter = 0

        # Throttle tracking (tag -> last execution time)
        self._throttle_times: dict[str, float] = {}

    def generate_anonymous_tag(self) -> str:
        """Generate a unique tag for anonymous builders"""
        self._tag_counter += 1
        return f"__anon_{self._tag_counter}"

    def time_alive(self, tag: str) -> Optional[float]:
        """Get time in seconds since builder was created

        Returns None if tag doesn't exist
        """
        if tag in self._active_builders:
            return self._active_builders[tag].time_alive()
        return None

    def add_builder(self, builder: 'ActiveBuilder'):
        """Add an active builder to state

        For tagged builders, if tag exists, add as child to existing builder.
        For anonymous builders, behavior modes control the relationship.
        """
        tag = builder.tag

        # Handle behavior modes
        behavior = builder.config.get_effective_behavior()

        # Tagged builders: add as child to existing parent
        if not builder.is_anonymous and tag in self._active_builders:
            existing = self._active_builders[tag]

            if behavior == "replace":
                # Replace entire builder
                self.remove_builder(tag)
            elif behavior == "extend":
                # Extend hold duration of parent
                if existing.lifecycle.hold_ms is not None:
                    existing.lifecycle.hold_ms += builder.config.hold_ms or 0
                return
            elif behavior == "throttle":
                # Check throttle timing
                throttle_ms = builder.config.behavior_args[0] if builder.config.behavior_args else 0
                if tag in self._throttle_times:
                    elapsed = (time.perf_counter() - self._throttle_times[tag]) * 1000
                    if elapsed < throttle_ms:
                        return  # Ignore this call
                # Add as child
                existing.add_child(builder)
                return
            elif behavior == "ignore":
                # Ignore if already active
                return
            else:
                # Stack/queue: add as child
                # If this child has operator='to', remove existing children with same property
                if builder.config.operator == "to" and builder.config.property:
                    existing.children = [
                        child for child in existing.children
                        if child.config.property != builder.config.property
                    ]
                existing.add_child(builder)
                return

        # Anonymous builders: behavior modes control creation
        if behavior == "replace":
            # For .to() operator, cancel all anonymous builders with same property
            if builder.config.operator == "to" and builder.config.property:
                tags_to_remove = [
                    t for t, b in self._active_builders.items()
                    if b.is_anonymous and b.config.property == builder.config.property
                ]
                for t in tags_to_remove:
                    self.remove_builder(t)
            else:
                # For other operators with explicit .replace(), remove by tag
                self.remove_builder(tag)

        elif behavior == "queue":
            # For anonymous builders, queue by property/operator
            queue_key = f"__queue_{builder.config.property}_{builder.config.operator}"

            # Check if any builder with same property/operator is active and animating
            is_queue_busy = False
            for active_builder in self._active_builders.values():
                if (active_builder.config.property == builder.config.property and
                    active_builder.config.operator == builder.config.operator and
                    active_builder.is_anonymous and
                    not active_builder.lifecycle.is_complete()):
                    is_queue_busy = True
                    break

            if is_queue_busy:
                # Queue this builder for later
                def execute_later():
                    self.add_builder(builder)
                self._queue_manager.enqueue(queue_key, execute_later)
                return

        elif behavior == "throttle":
            # Check throttle timing for anonymous (uses generated tag)
            throttle_ms = builder.config.behavior_args[0] if builder.config.behavior_args else 0
            if tag in self._throttle_times:
                elapsed = (time.perf_counter() - self._throttle_times[tag]) * 1000
                if elapsed < throttle_ms:
                    return  # Ignore this call

        elif behavior == "stack":
            # Check stack limit for anonymous builders
            max_count = builder.config.behavior_args[0] if builder.config.behavior_args else None
            if max_count is not None:
                # Count existing stacks with same property/operator
                stack_key = f"{builder.config.property}_{builder.config.operator}"
                count = sum(1 for b in self._active_builders.values()
                           if f"{b.config.property}_{b.config.operator}" == stack_key)
                if count >= max_count:
                    # Remove oldest stack
                    for old_tag, old_builder in list(self._active_builders.items()):
                        if f"{old_builder.config.property}_{old_builder.config.operator}" == stack_key:
                            self.remove_builder(old_tag)
                            break

        # Add builder to active set
        self._active_builders[tag] = builder

        # Track execution order
        if builder.is_anonymous:
            self._anonymous_tags.append(tag)
        else:
            self._tagged_tags.append(tag)

        # Update throttle time
        self._throttle_times[tag] = time.perf_counter()

        # Check if this builder completes instantly (no lifecycle)
        if builder.lifecycle.is_complete():
            # Instant completion - bake immediately if anonymous, remove if tagged
            if builder.is_anonymous:
                # Bake BEFORE removing, since frame loop might clear children
                if builder.config.get_effective_bake():
                    self._bake_builder(builder)
                # Remove from active set (don't call remove_builder to avoid double-bake)
                del self._active_builders[tag]
                self._anonymous_tags.remove(tag)
            else:
                # Tagged builders without lifecycle should stay active indefinitely
                # (they can be manually reverted later)
                pass
            return

        # Start frame loop if not running
        self._ensure_frame_loop_running()

    def remove_builder(self, tag: str):
        """Remove an active builder"""
        if tag in self._active_builders:
            builder = self._active_builders[tag]

            # If bake=true, merge values into base
            if builder.config.get_effective_bake():
                self._bake_builder(builder)

            del self._active_builders[tag]

            # Remove from order tracking
            if tag in self._anonymous_tags:
                self._anonymous_tags.remove(tag)
            if tag in self._tagged_tags:
                self._tagged_tags.remove(tag)

            # Notify queue system (using same queue key logic as add_builder)
            queue_key = tag
            if builder.is_anonymous:
                queue_key = f"__queue_{builder.config.property}_{builder.config.operator}"
            self._queue_manager.on_builder_complete(queue_key)

        # Stop frame loop if no active builders AND no movement
        if len(self._active_builders) == 0 and not self._has_movement():
            self._stop_frame_loop()

    def _bake_builder(self, builder: 'ActiveBuilder'):
        """Merge builder's final aggregated value into base state"""
        # If builder has reverted, don't bake (it's already back to base)
        if builder.lifecycle.has_reverted():
            return

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
        elif prop == "accel":
            if operator == "to":
                self._base_accel = current_value
            elif operator in ("add", "by"):
                self._base_accel += current_value
            elif operator == "sub":
                self._base_accel -= current_value
            elif operator == "mul":
                self._base_accel *= current_value
            elif operator == "div":
                self._base_accel /= current_value if current_value != 0 else 1
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

    def _compute_current_state(self) -> tuple[Vec2, float, Vec2, float]:
        """Compute current state by applying all active builders to base.

        Returns:
            (position, speed, direction, accel)
        """
        # Start with base
        pos = Vec2(self._base_pos.x, self._base_pos.y)
        speed = self._base_speed
        direction = Vec2(self._base_direction.x, self._base_direction.y)
        accel = self._base_accel

        # Apply builders in order: anonymous first, then tagged
        ordered_tags = self._anonymous_tags + self._tagged_tags

        for tag in ordered_tags:
            if tag not in self._active_builders:
                continue

            builder = self._active_builders[tag]
            prop = builder.config.property
            operator = builder.config.operator
            current_value = builder.get_current_value()

            if prop == "speed":
                if operator == "to":
                    speed = current_value
                elif operator in ("add", "by"):
                    speed += current_value
                elif operator == "sub":
                    speed -= current_value
                elif operator == "mul":
                    speed *= current_value
                elif operator == "div":
                    speed /= current_value if current_value != 0 else 1
            elif prop == "accel":
                if operator == "to":
                    accel = current_value
                elif operator in ("add", "by"):
                    accel += current_value
                elif operator == "sub":
                    accel -= current_value
                elif operator == "mul":
                    accel *= current_value
                elif operator == "div":
                    accel /= current_value if current_value != 0 else 1
            elif prop == "direction":
                if operator == "to":
                    # Direction 'to' replaces current value
                    direction = current_value
                elif operator in ("add", "by"):
                    # Direction add/by contributes to current value
                    direction = (direction + current_value).normalized()
                elif operator == "sub":
                    # Direction sub subtracts from current value
                    direction = (direction - current_value).normalized()
            elif prop == "pos":
                # Position builders return offsets
                pos = pos + current_value

        return (pos, speed, direction, accel)

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
        for tag, builder in list(self._active_builders.items()):
            if not builder.update(dt):
                completed.append(tag)

        for tag in completed:
            self.remove_builder(tag)

        # Compute current state
        pos, speed, direction, accel = self._compute_current_state()

        # Apply acceleration to speed (accel is per frame)
        if accel != 0:
            speed += accel

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
        """Check if there's any movement happening (base speed or accel non-zero)"""
        return self._base_speed != 0 or self._base_accel != 0

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
    def accel(self) -> float:
        """Current computed acceleration"""
        return self._compute_current_state()[3]

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
    def tags(self) -> list[str]:
        """List of active named tags (excludes anonymous builders)

        Returns a list of tag names for currently active builders.
        Anonymous builders (internal temporary effects) are excluded.

        Example:
            rig.state.tags  # ["sprint", "drift"]
        """
        return [tag for tag in self._tagged_tags if tag in self._active_builders]

    # Tag state access
    class TagState:
        """State information for a specific tag"""
        def __init__(self, builder: 'ActiveBuilder'):
            self._builder = builder

        @property
        def prop(self) -> str:
            """What property this tag is affecting: 'speed', 'direction', 'pos', 'accel'"""
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
            """Speed value if this tag affects speed, else None"""
            return self.value if self.prop == 'speed' else None

        @property
        def direction(self) -> Optional[Vec2]:
            """Direction value if this tag affects direction, else None"""
            return self.value if self.prop == 'direction' else None

        @property
        def pos(self) -> Optional[Vec2]:
            """Position offset if this tag affects position, else None"""
            return self.value if self.prop == 'pos' else None

        @property
        def accel(self) -> Optional[float]:
            """Acceleration value if this tag affects accel, else None"""
            return self.value if self.prop == 'accel' else None

        def time_alive(self) -> float:
            """Get time in seconds since this builder was created"""
            return self._builder.time_alive()

        def revert(self, ms: Optional[float] = None, easing: str = "linear"):
            """Trigger a revert on this tagged builder

            Args:
                ms: Duration in milliseconds for the revert
                easing: Easing function for the revert
            """
            from .builder import RigBuilder
            # Create a revert-only builder that will trigger the revert
            builder = RigBuilder(self._builder.rig_state, self._builder.config.tag_name)
            builder.revert(ms, easing)
            # Force immediate execution (since it won't have __del__ called naturally)
            builder._execute()

    def tag(self, tag: str) -> Optional['RigState.TagState']:
        """Get state information for a specific tag

        Returns a TagState object with the tag's current state, or None if not active.

        Example:
            sprint = rig.state.tag("sprint")
            if sprint:
                print(f"Sprint speed: {sprint.speed}")
                print(f"Phase: {sprint.phase}")
        """
        if tag not in self._active_builders:
            return None

        builder = self._active_builders[tag]
        return RigState.TagState(builder)

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
        def accel(self) -> float:
            return self._rig_state._base_accel

    @property
    def base(self) -> 'RigState.BaseState':
        """Access to base (baked) state only"""
        return RigState.BaseState(self)

    def stop(self, transition_ms: Optional[float] = None, easing: str = "linear"):
        """Stop everything: bake state, clear effects, decelerate to 0

        This matches v1 behavior:
        1. Bake current computed state into base
        2. Clear all active builders (effects)
        3. Set speed to 0 (with optional smooth deceleration)
        """
        # 1. Bake all active builders into base
        for tag in list(self._active_builders.keys()):
            builder = self._active_builders[tag]
            if not builder.lifecycle.has_reverted():
                self._bake_builder(builder)

        # 2. Clear all active builders
        self._active_builders.clear()
        self._anonymous_tags.clear()
        self._tagged_tags.clear()

        # 3. Decelerate speed to 0
        if transition_ms is None or transition_ms == 0:
            # Immediate stop
            self._base_speed = 0.0
            self._base_accel = 0.0
        else:
            # Smooth deceleration - create anonymous builder
            from .builder import RigBuilder, ActiveBuilder
            from .contracts import BuilderConfig

            config = BuilderConfig()
            config.tag_name = self.generate_anonymous_tag()
            config.property = "speed"
            config.operator = "to"
            config.value = 0
            config.over_ms = transition_ms
            config.over_easing = easing

            builder = ActiveBuilder(config, self, is_anonymous=True)
            self._active_builders[config.tag_name] = builder
            self._anonymous_tags.append(config.tag_name)
            self._ensure_frame_loop_running()

    def reverse(self, transition_ms: Optional[float] = None):
        """Reverse direction (180° turn)"""
        # This will be implemented via builder in builder.py
        pass

    def bake_all(self):
        """Bake all active builders immediately"""
        for tag in list(self._active_builders.keys()):
            self.remove_builder(tag)

    def trigger_revert(self, tag: str, revert_ms: Optional[float] = None, easing: str = "linear"):
        """Trigger revert on builder tree

        Strategy:
        1. Capture current aggregated value from all children
        2. Clear all children (bake the aggregate)
        3. Create group lifecycle that reverses from aggregate to neutral
        """
        if tag in self._active_builders:
            builder = self._active_builders[tag]

            # Capture current aggregated value
            current_value = builder.get_current_value()

            # Get base value (neutral/zero for the property type)
            # Use builder's own config since children might be empty after first revert
            if builder.config.property in ("speed", "accel"):
                base_value = 0
            elif builder.config.property == "direction":
                base_value = builder.base_value  # Original direction
            elif builder.config.property == "pos":
                base_value = Vec2(0, 0)  # Zero offset
            else:
                base_value = 0

            # Create group lifecycle for coordinated revert
            builder.group_lifecycle = Lifecycle(is_tagged=not builder.is_anonymous)
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
