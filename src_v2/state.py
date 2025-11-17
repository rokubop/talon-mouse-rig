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

    def add_builder(self, builder: 'ActiveBuilder'):
        """Add an active builder to state"""
        tag = builder.tag

        # Handle behavior modes
        behavior = builder.config.get_effective_behavior()

        if behavior == "replace":
            # Cancel existing builder with same tag
            self.remove_builder(tag)

        elif behavior == "queue":
            # Check if there's already an active builder with this tag
            if tag in self._active_builders:
                # Queue this builder for later
                def execute_later():
                    self.add_builder(builder)
                self._queue_manager.enqueue(tag, execute_later)
                return

        elif behavior == "extend":
            # Extend hold duration of existing builder
            if tag in self._active_builders:
                existing = self._active_builders[tag]
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

        elif behavior == "ignore":
            # Ignore if already active
            if tag in self._active_builders:
                return

        elif behavior == "stack":
            # Check stack limit
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
            # Instant completion - bake immediately if anonymous
            self.remove_builder(tag)
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

            # Notify queue system
            self._queue_manager.on_builder_complete(tag)

        # Stop frame loop if no active builders AND no movement
        if len(self._active_builders) == 0 and not self._has_movement():
            self._stop_frame_loop()

    def _bake_builder(self, builder: 'ActiveBuilder'):
        """Merge builder's final value into base state"""
        prop = builder.config.property
        operator = builder.config.operator
        value = builder.config.value

        if prop == "speed":
            self._base_speed = builder.get_current_value()
        elif prop == "accel":
            self._base_accel = builder.get_current_value()
        elif prop == "direction":
            self._base_direction = builder.get_current_value()
        elif prop == "pos":
            # Position is more complex - update base position
            offset = builder.get_current_value()
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
                direction = current_value
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
        completed = []
        for tag, builder in self._active_builders.items():
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

    def stop(self, transition_ms: Optional[float] = None):
        """Stop movement (speed to 0)"""
        # This will be implemented via builder in builder.py
        pass

    def reverse(self, transition_ms: Optional[float] = None):
        """Reverse direction (180° turn)"""
        # This will be implemented via builder in builder.py
        pass

    def bake_all(self):
        """Bake all active builders immediately"""
        for tag in list(self._active_builders.keys()):
            self.remove_builder(tag)
