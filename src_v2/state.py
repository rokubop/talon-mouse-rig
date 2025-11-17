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
            # For tagged builders with delta operators (add/by/mul/div), accumulate instead
            if (not builder.is_anonymous and
                tag in self._active_builders and
                builder.config.operator in ("add", "by", "mul", "div", "sub")):
                # Accumulate the delta into the existing builder
                existing = self._active_builders[tag]
                self._accumulate_delta(existing, builder)
                return
            else:
                # Cancel existing builder with same tag
                self.remove_builder(tag)

        elif behavior == "queue":
            # For anonymous builders, queue by property/operator (e.g., all direction.by() calls queue together)
            # For tagged builders, queue by tag
            queue_key = tag
            if builder.is_anonymous:
                queue_key = f"__queue_{builder.config.property}_{builder.config.operator}"

            # Check if there's already an active builder for this queue
            is_queue_busy = False
            if builder.is_anonymous:
                # Check if any builder with same property/operator is active and animating
                for active_builder in self._active_builders.values():
                    if (active_builder.config.property == builder.config.property and
                        active_builder.config.operator == builder.config.operator and
                        active_builder.is_anonymous and
                        not active_builder.lifecycle.is_complete()):
                        is_queue_busy = True
                        break
            else:
                # Tagged builders queue by tag - check if tag exists AND lifecycle is still active
                if tag in self._active_builders:
                    existing = self._active_builders[tag]
                    # Queue is busy if the existing builder's lifecycle hasn't completed
                    is_queue_busy = not existing.lifecycle.is_complete()

            if is_queue_busy:
                # Queue this builder for later
                def execute_later():
                    self.add_builder(builder)
                self._queue_manager.enqueue(queue_key, execute_later)
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
            # Instant completion - bake immediately if anonymous, remove if tagged
            if builder.is_anonymous:
                self.remove_builder(tag)
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

    def _accumulate_delta(self, existing: 'ActiveBuilder', new: 'ActiveBuilder'):
        """Accumulate a new delta into an existing tagged builder

        For tagged builders called multiple times with delta operators (add/by/mul/div),
        this accumulates the effect instead of replacing it.
        """
        prop = existing.config.property
        operator = existing.config.operator

        if prop == "direction" and operator in ("add", "by"):
            # For direction rotation, accumulate the angle
            existing_angle = existing.config.value if isinstance(existing.config.value, (int, float)) else existing.config.value[0]
            new_angle = new.config.value if isinstance(new.config.value, (int, float)) else new.config.value[0]
            accumulated_angle = existing_angle + new_angle

            # Update config and recalculate target
            existing.config.value = accumulated_angle
            import math
            from .core import Vec2
            angle_rad = math.radians(accumulated_angle)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            base = existing.base_value  # Keep original base
            new_x = base.x * cos_a - base.y * sin_a
            new_y = base.x * sin_a + base.y * cos_a
            existing.target_value = Vec2(new_x, new_y).normalized()

        elif prop in ("speed", "accel"):
            if operator in ("add", "by"):
                # Accumulate additive delta
                existing.config.value += new.config.value
                existing.target_value = existing.config.value
            elif operator == "mul":
                # Accumulate multiplicative delta
                existing.config.value *= new.config.value
                existing.target_value = existing.config.value
            elif operator == "div":
                # Accumulate divisive delta
                if new.config.value != 0:
                    existing.config.value /= new.config.value
                    existing.target_value = existing.config.value
            elif operator == "sub":
                # Accumulate subtractive delta
                existing.config.value -= new.config.value
                existing.target_value = existing.config.value

        # Restart lifecycle animation to show the new accumulated value
        existing.lifecycle.started = False
        existing.lifecycle.phase = None
        existing.lifecycle.elapsed = 0
        existing.lifecycle.phase_start_time = None

    def _bake_builder(self, builder: 'ActiveBuilder'):
        """Merge builder's final value into base state"""
        # If builder has reverted, don't bake (it's already back to base)
        if builder.lifecycle.has_reverted():
            return

        prop = builder.config.property
        operator = builder.config.operator
        current_value = builder.get_current_value()

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
                # Direction always uses absolute values (animate_direction handles rotation)
                # Even for add/by operators, the builder has already calculated the rotated target
                # and animate_direction returns the interpolated absolute direction
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
        """Trigger early revert on an existing active builder"""
        if tag in self._active_builders:
            builder = self._active_builders[tag]
            # Set the builder to start reverting
            builder.lifecycle.revert_ms = revert_ms if revert_ms is not None else 0
            builder.lifecycle.revert_easing = easing
            # Force transition to revert phase
            builder.lifecycle.phase = LifecyclePhase.REVERT
            builder.lifecycle.phase_start_time = time.perf_counter()
        else:
            print(f"  Builder {tag} not found")
