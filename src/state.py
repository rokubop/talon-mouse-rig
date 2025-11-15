"""Main state management for mouse rig"""

import time
import math
from typing import Optional, Callable, Tuple
from .builders.rate_utils import calculate_revert_duration_for_property
from talon import cron, settings, ctrl

from . import core
from .core import (
    Vec2, SubpixelAdjuster,
    SpeedTransition, DirectionTransition, PositionTransition, ReverseTransition
)
from .effects import EffectStack, EffectLifecycle, Force, Effect, DirectionEffect
from .builders.base import (
    AccelController,
    DirectionController,
    DirectionByBuilder,
    DirectionReverseBuilder,
    PositionController,
    SpeedController
)
from .builders.effect import EffectBuilder
from .builders.force import NamedForceNamespace, NamedForceBuilder

class RigState:
    """Core state for the mouse rig"""
    def __init__(self):
        # Persistent state
        self._direction = Vec2(1, 0)  # unit vector
        self._speed = 0.0  # base speed magnitude
        self._accel = 0.0  # base acceleration magnitude
        self.limits_max_speed = settings.get("user.mouse_rig_max_speed")

        # Transitions (permanent)
        self._speed_transition: Optional[SpeedTransition] = None
        self._direction_transition: Optional[DirectionTransition] = None
        self._position_transitions: list[PositionTransition] = []

        # UNIFIED EFFECT SYSTEM
        # All effects (property and stack-based) managed in single list
        self._effects: list[Effect] = []  # Unified: property effects (speed/accel) and stack effects
        self._direction_effects: list[DirectionEffect] = []  # direction temporary effects

        # Named forces (for backward compatibility with force API)
        self._named_forces: dict[str, Force] = {}

        # PRD 8: Effect stacks (operations with stacking control)
        self._effect_stacks: dict[str, EffectStack] = {}  # key: "entity_name:property:op_type"
        self._effect_order: list[str] = []  # Track creation order for composition

        # PRD 8: Effect lifecycles (lifecycle-aware wrappers for effect stacks)
        # Maps stack key to its EffectLifecycle wrapper (which wraps unified Effect)
        self._effect_lifecycles: dict[str, EffectLifecycle] = {}  # key: same as _effect_stacks

        # Controllers (fluent API)
        self.speed = SpeedController(self)
        self.accel = AccelController(self)
        self.direction = DirectionController(self)
        self.pos = PositionController(self)

        # Named force namespace
        self._force_namespace = NamedForceNamespace(self)

        # Sequence state
        self._sequence_queue: list[Callable] = []
        self._sequence_running: bool = False

        # Pending wait/then callbacks
        self._pending_wait_jobs: list = []

        # Frame loop
        self._cron_job = None
        self._last_frame_time = None

        # Subpixel accuracy
        self._subpixel_adjuster = SubpixelAdjuster()

        # Position offset tracking (for effects)
        self._last_position_offset = Vec2(0, 0)

    def effect(self, name: str) -> EffectBuilder:
        """Create or access a named effect entity (PRD 8)

        Effects modify base properties using explicit operations:
        - .to(value): Set absolute value
        - .add(value) / .by(value): Add delta (aliases)
        - .sub(value): Subtract
        - .mul(value): Multiply
        - .div(value): Divide

        Effects use strict syntax - explicit operations are required.

        Examples:
            rig.effect("sprint").speed.mul(2)       # Double speed
            rig.effect("boost").speed.add(10)       # Add 10 to speed
            rig.effect("drift").direction.add(15)   # Rotate 15 degrees
        """
        return EffectBuilder(self, name, strict_mode=True)

    def force(self, name: str) -> 'NamedForceBuilder':
        """Create or access a named force entity (PRD 8)

        Forces are independent entities with their own speed, direction, and acceleration.
        They combine with the base rig via vector addition.

        Examples:
            rig.force("gravity").direction(0, 1).accel(9.8)
            rig.force("wind").velocity(5, 0)
            rig.force("wind").stop(500)
        """
        return NamedForceBuilder(self, name)

    @property
    def force_namespace(self) -> NamedForceNamespace:
        """Access named forces (independent entities)

        Forces use absolute values (.to, direct setters) and remain constant.

        Examples:
            rig.force("wind").speed(5).direction(0, 1)
            rig.force("wind").stop()
            rig.force.stop_all()
        """
        return self._force_namespace

    @property
    def state(self) -> 'StateAccessor':
        """Access computed state (base + modifiers + forces)

        Examples:
            rig.state.speed      # Computed speed
            rig.state.accel      # Computed acceleration
            rig.state.direction  # Current direction
            rig.state.pos        # Current position
            rig.state.velocity   # Total velocity vector
        """
        if not hasattr(self, '_state_accessor'):
            self._state_accessor = StateAccessor(self)
        return self._state_accessor

    @property
    def base(self) -> 'BaseAccessor':
        """Access base values only (without modifiers/forces)

        Examples:
            rig.base.speed      # Base speed
            rig.base.accel      # Base acceleration
            rig.base.direction  # Base direction
        """
        if not hasattr(self, '_base_accessor'):
            self._base_accessor = BaseAccessor(self)
        return self._base_accessor

    @property
    def state_dict(self) -> dict:
        """Read-only state information as dictionary (deprecated - use .state properties)"""
        position = ctrl.mouse_pos()

        # Calculate effective speed and accel with effects applied
        effective_speed = self._get_effective_speed()
        effective_accel = self._get_effective_accel()
        effective_direction = self._get_effective_direction()
        accel_velocity = self._get_accel_velocity_contribution()

        # Total velocity includes cruise velocity + accel velocity contributions
        total_speed = effective_speed + accel_velocity
        total_velocity = effective_direction * total_speed

        # Determine cardinal/intercardinal direction
        direction_cardinal = self._get_cardinal_direction(effective_direction)

        return {
            "position": position,
            "direction": effective_direction.to_tuple(),
            "direction_cardinal": direction_cardinal,
            "speed": self._speed,  # Base cruise speed
            "accel": self._accel,
            "effective_speed": effective_speed,  # Cruise speed with speed modifiers
            "effective_accel": effective_accel,  # Acceleration with accel modifiers
            "accel_velocity": accel_velocity,  # Integrated velocity from accel effects
            "total_speed": total_speed,  # Total effective speed (cruise + accel velocity)
            "velocity": total_velocity.to_tuple(),  # Total velocity vector
            "active_effects": len(self._effects),
            "active_effect_stacks": len(self._effect_stacks),
            "active_effect_lifecycles": len(self._effect_lifecycles),
            "has_speed_transition": self._speed_transition is not None,
            "has_direction_transition": self._direction_transition is not None,
            "active_glides": len(self._position_transitions),
            "is_moving": self.is_moving,
            "is_ticking": self.is_ticking,
        }

    @property
    def is_ticking(self) -> bool:
        """Check if the frame loop is currently running"""
        return self._cron_job is not None

    @property
    def is_moving(self) -> bool:
        """Check if the rig is currently producing movement"""
        epsilon = settings.get("user.mouse_rig_epsilon")
        effective_speed = self._get_effective_speed()
        accel_velocity = self._get_accel_velocity_contribution()
        total_speed = effective_speed + accel_velocity
        effective_accel = self._get_effective_accel()
        return total_speed > epsilon or abs(effective_accel) > epsilon

    @property
    def settings(self) -> dict:
        """Get current rig settings"""
        return {
            "frame_interval": settings.get("user.mouse_rig_frame_interval"),
            "max_speed": self.limits_max_speed,
            "epsilon": settings.get("user.mouse_rig_epsilon"),
            "default_turn_rate": settings.get("user.mouse_rig_default_turn_rate"),
            "movement_type": settings.get("user.mouse_rig_movement_type"),
            "scale": settings.get("user.mouse_rig_scale"),
        }

    def _get_effective_speed(self) -> float:
        """Get speed with all effects applied"""
        base_speed = self._speed

        # Apply temporary property effects first (base rig temporary modifications)
        for effect in self._effects:
            if effect.is_property_effect and effect.property_name == "speed":
                base_speed = effect.update(base_speed)

        # Apply effect stacks (PRD 8 - named effects)
        # Pipeline: base → all mul/div effects → all add/sub effects (in entity creation order)
        # This ensures multiplicative operations apply before additive

        # Group by entity name to track first occurrence order
        entity_order = []
        entities_seen = set()
        for key in self._effect_order:
            stack = self._effect_stacks[key]
            if stack.property == "speed" and stack.name not in entities_seen:
                entity_order.append(stack.name)
                entities_seen.add(stack.name)

        # Apply mul/div effects first (in entity creation order)
        for entity_name in entity_order:
            for op_type in ["mul", "div"]:
                effect_key = f"{entity_name}:speed:{op_type}"
                if effect_key in self._effect_stacks:
                    stack = self._effect_stacks[effect_key]
                    # Check if there's a lifecycle effect wrapper
                    if effect_key in self._effect_lifecycles:
                        effect = self._effect_lifecycles[effect_key]
                        base_speed = effect.apply_to_base(base_speed)
                    else:
                        base_speed = stack.apply_to_base(base_speed)

        # Then apply add/sub transforms (in entity creation order)
        for entity_name in entity_order:
            for op_type in ["add", "sub"]:
                effect_key = f"{entity_name}:speed:{op_type}"
                if effect_key in self._effect_stacks:
                    stack = self._effect_stacks[effect_key]
                    # Check if there's a lifecycle effect wrapper
                    if effect_key in self._effect_lifecycles:
                        effect = self._effect_lifecycles[effect_key]
                        base_speed = effect.apply_to_base(base_speed)
                    else:
                        base_speed = stack.apply_to_base(base_speed)

        # Allow negative speed during ReverseTransition
        if isinstance(self._direction_transition, ReverseTransition):
            return base_speed
        return max(0.0, base_speed)

    def _get_effective_accel(self) -> float:
        """Get acceleration with all effects applied

        Note: This returns the effective acceleration value but does NOT
        modify cruise speed. Acceleration effects track their own velocity
        contributions separately.
        """
        base_accel = self._accel

        # Apply temporary property effects first (base rig temporary modifications)
        for effect in self._effects:
            if effect.is_property_effect and effect.property_name == "accel":
                base_accel = effect.update(base_accel)

        # Apply effect stacks (PRD 8 - named effects)
        # Pipeline: base → all mul/div effects → all add/sub effects (in entity creation order)

        # Group by entity name to track first occurrence order
        entity_order = []
        entities_seen = set()
        for key in self._effect_order:
            stack = self._effect_stacks[key]
            if stack.property == "accel" and stack.name not in entities_seen:
                entity_order.append(stack.name)
                entities_seen.add(stack.name)

        # Apply mul/div effects first (in entity creation order)
        for entity_name in entity_order:
            for op_type in ["mul", "div"]:
                effect_key = f"{entity_name}:accel:{op_type}"
                if effect_key in self._effect_stacks:
                    stack = self._effect_stacks[effect_key]
                    # Check if there's a lifecycle effect wrapper
                    if effect_key in self._effect_lifecycles:
                        effect = self._effect_lifecycles[effect_key]
                        base_accel = effect.apply_to_base(base_accel)
                    else:
                        base_accel = stack.apply_to_base(base_accel)

        # Then apply add/sub transforms (in entity creation order)
        for entity_name in entity_order:
            for op_type in ["add", "sub"]:
                effect_key = f"{entity_name}:accel:{op_type}"
                if effect_key in self._effect_stacks:
                    stack = self._effect_stacks[effect_key]
                    # Check if there's a lifecycle effect wrapper
                    if effect_key in self._effect_lifecycles:
                        effect = self._effect_lifecycles[effect_key]
                        base_accel = effect.apply_to_base(base_accel)
                    else:
                        base_accel = stack.apply_to_base(base_accel)

        return base_accel

    def _get_effective_direction(self) -> Vec2:
        """Get direction with all rotation effects and transforms applied"""
        base_direction = self._direction

        # Apply temporary direction effects first (base rig temporary rotations)
        for effect in self._direction_effects:
            base_direction = effect.update(base_direction)

        # Apply effect stacks (PRD 8 - named effects) - direction rotations
        # Direction uses add/sub for rotation by degrees, and to() for absolute
        # Group by entity name to track first occurrence order
        entity_order = []
        entities_seen = set()
        for key in self._effect_order:
            if key not in self._effect_stacks:
                continue
            stack = self._effect_stacks[key]
            if stack.property == "direction" and stack.name not in entities_seen:
                entity_order.append(stack.name)
                entities_seen.add(stack.name)

        # Apply add/sub effects (rotation in degrees, in entity creation order)
        for entity_name in entity_order:
            for op_type in ["add", "sub"]:
                effect_key = f"{entity_name}:direction:{op_type}"
                if effect_key in self._effect_stacks:
                    stack = self._effect_stacks[effect_key]
                    # Get total rotation in degrees
                    total_degrees = stack.get_total()

                    # Check if there's a lifecycle effect wrapper
                    if effect_key in self._effect_lifecycles:
                        effect = self._effect_lifecycles[effect_key]
                        multiplier = effect.current_multiplier
                        total_degrees = total_degrees * multiplier

                    # Apply rotation
                    if abs(total_degrees) > 1e-6:
                        angle_rad = math.radians(total_degrees)
                        cos_a = math.cos(angle_rad)
                        sin_a = math.sin(angle_rad)
                        new_x = base_direction.x * cos_a - base_direction.y * sin_a
                        new_y = base_direction.x * sin_a + base_direction.y * cos_a
                        base_direction = Vec2(new_x, new_y).normalized()

        return base_direction

    def _get_position_offset(self) -> Vec2:
        """Get total position offset from all position effects"""
        offset = Vec2(0, 0)

        # Apply position effect stacks (PRD 8)
        # Position uses add/sub for offsets, to() for absolute
        # Group by entity name to track first occurrence order
        entity_order = []
        entities_seen = set()
        for key in self._effect_order:
            if key not in self._effect_stacks:
                continue
            stack = self._effect_stacks[key]
            if stack.property == "pos" and stack.name not in entities_seen:
                entity_order.append(stack.name)
                entities_seen.add(stack.name)

        # Apply add/sub effects (position offsets, in entity creation order)
        for entity_name in entity_order:
            for op_type in ["add", "sub"]:
                effect_key = f"{entity_name}:pos:{op_type}"
                if effect_key in self._effect_stacks:
                    stack = self._effect_stacks[effect_key]
                    # Get total position offset vector
                    total_offset = stack.get_total()

                    # Check if there's a lifecycle effect wrapper
                    if effect_key in self._effect_lifecycles:
                        effect = self._effect_lifecycles[effect_key]
                        multiplier = effect.current_multiplier
                        # Lerp from zero to full offset based on multiplier
                        total_offset = total_offset * multiplier

                    # Add to cumulative offset
                    if isinstance(total_offset, Vec2):
                        offset = offset + total_offset

        return offset

    def _get_accel_velocity_contribution(self) -> float:
        """Get total velocity contribution from all acceleration effects

        PRD 8: Currently returns 0 - accel velocity tracking removed with old effect system.
        Accel effects now directly modify the accel property through effect stacks.
        """
        return 0.0

    def reverse(self) -> DirectionReverseBuilder:
        """Reverse direction (180 degree turn with speed fade)

        Can be instant or smooth:
            rig.reverse()                     # Instant 180° flip
            rig.reverse().over(500)           # Fade to reverse over 500ms
            rig.reverse().revert(1000)        # Instant flip, fade back over 1000ms
            rig.reverse().over(500).revert(500)  # Fade both ways
        """
        return DirectionReverseBuilder(self, instant=True)

    def _get_cardinal_direction(self, direction: Vec2) -> str:
        """Get cardinal/intercardinal direction name from direction vector

        Returns one of: "right", "left", "up", "down",
                       "up_right", "up_left", "down_right", "down_left"
        """
        x, y = direction.x, direction.y

        # Threshold for considering a direction as "mostly" along an axis
        # 0.383 ≈ cos(67.5°), which is halfway between pure cardinal (0°) and pure diagonal (45°)
        threshold = 0.383

        # Pure cardinal directions (within 22.5° of axis)
        if abs(x) > abs(y) * 2.414:  # tan(67.5°) ≈ 2.414
            return "right" if x > 0 else "left"
        if abs(y) > abs(x) * 2.414:
            return "up" if y < 0 else "down"

        # Diagonal/intercardinal directions
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

    def bake(self) -> None:
        """Flatten computed state into base, clearing all effects and forces

        This takes the current computed values (base + effects + forces) and
        makes them the new base values, then clears all effects and forces.

        For position transforms: The offset has already been applied to the cursor
        via delta tracking in _update_frame(), so we just clear the transforms
        and reset tracking.

        Examples:
            rig.speed(10)
            rig.modifier("boost").speed.mul(2)  # computed speed = 20
            rig.bake()                          # base speed now 20, modifier cleared
        """
        # Compute final values for speed/accel/direction
        final_speed = self._get_effective_speed()
        final_accel = self._get_effective_accel()
        final_direction = self._get_effective_direction()

        # Set as new base
        self._speed = final_speed
        self._accel = final_accel
        self._direction = final_direction

        # Reset position offset tracking
        # (The cursor is already at the offset position from delta tracking,
        #  so we just reset to prepare for future transforms)
        self._last_position_offset = Vec2(0, 0)

        # Clear all effects and forces
        self._named_forces.clear()
        self._effects.clear()
        self._direction_effects.clear()

        # Clear effect system (PRD 8)
        self._effect_stacks.clear()
        self._effect_lifecycles.clear()
        self._effect_order.clear()

        # Note: We don't clear transitions as those are permanent changes in progress

    def _stop_immediate(self) -> None:
        """Internal: Immediate stop implementation"""
        # Stop movement
        self._speed = 0.0
        self._accel = 0.0
        self._speed_transition = None
        self._direction_transition = None
        self._position_transitions.clear()

        # Clear effects
        self._named_forces.clear()
        self._effects.clear()
        self._effect_stacks.clear()
        self._effect_lifecycles.clear()
        self._effect_order.clear()

        # Reset subpixel accumulator to prevent drift on restart
        self._subpixel_adjuster = SubpixelAdjuster()

        # Stop frame loop
        if self._cron_job is not None:
            cron.cancel(self._cron_job)
            self._cron_job = None

        # Cancel all pending wait/then callbacks
        for job in self._pending_wait_jobs:
            try:
                cron.cancel(job)
            except:
                pass  # Ignore errors if job already completed
        self._pending_wait_jobs.clear()

    def stop(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None,
        interpolation: str = "lerp"
    ) -> None:
        """Stop everything: bake state, clear effects/forces, decelerate to 0

        Args:
            duration_ms: Optional duration to decelerate over. If None, stops immediately.
            easing: Easing function name for gradual deceleration
            rate_speed: Speed deceleration rate in units/second (rate-based)
            interpolation: Interpolation method - "lerp" (linear, default) or "slerp" (rotation)

        Examples:
            rig.stop()                  # Instant: bake, clear, speed=0
            rig.stop(500)               # Bake, clear, then decelerate over 500ms
            rig.stop(1000, "ease_out")  # Bake, clear, decelerate with easing
            rig.stop(rate_speed=50)     # Decelerate at 50 units/s
        """
        # Calculate duration from rate if provided
        if rate_speed is not None:
            duration_ms = calculate_revert_duration_for_property(
                "speed", self._speed,
                rate_speed, rate_accel, rate_rotation
            )

        # 1. Bake current state (flatten effects/forces into base)
        self.bake()

        # 2. Effects and forces already cleared by bake()

        # 3. Decelerate speed to 0
        if duration_ms is None or duration_ms == 0:
            # Immediate stop
            self._speed = 0.0
            self._accel = 0.0
            self._speed_transition = None
            self._direction_transition = None
            self._position_transitions.clear()

            # Reset subpixel accumulator
            self._subpixel_adjuster = SubpixelAdjuster()

            # Stop frame loop
            if self._cron_job is not None:
                cron.cancel(self._cron_job)
                self._cron_job = None

            # Cancel pending callbacks
            for job in self._pending_wait_jobs:
                try:
                    cron.cancel(job)
                except:
                    pass
            self._pending_wait_jobs.clear()
        else:
            # Gradual deceleration: fade speed to 0 over duration
            transition = SpeedTransition(
                self._speed,
                0.0,
                duration_ms,
                easing
            )
            self.start()
            self._speed_transition = transition

    def sequence(self, steps: list[Callable]) -> None:
        """Execute a sequence of operations in order

        Each step should be a callable (lambda or function) that performs one operation.
        The sequence waits for each step to complete before moving to the next.

        Args:
            steps: List of callables to execute in sequence

        Examples:
            # Click multiple points in order
            rig.sequence([
                lambda: rig.pos.to(100, 200).over(350),
                lambda: actions.mouse_click(0),
                lambda: rig.pos.to(300, 400).over(350),
                lambda: actions.mouse_click(0),
            ])

            # Drag operation
            rig.sequence([
                lambda: rig.pos.to(x1, y1).over(500),
                lambda: actions.mouse_click(0, hold=True),
                lambda: rig.pos.to(x2, y2).over(500),
                lambda: actions.mouse_click(0, hold=False),
            ])
        """
        if not steps:
            return

        self._sequence_queue = list(steps)
        self._sequence_running = True
        self._run_next_in_sequence()

    def _run_next_in_sequence(self) -> None:
        """Internal: Run the next step in the sequence"""
        if not self._sequence_running or not self._sequence_queue:
            self._sequence_running = False
            return

        # Get next step
        step = self._sequence_queue.pop(0)

        # Execute the step
        try:
            step()
        except Exception as e:
            print(f"Error in sequence step: {e}")
            self._sequence_running = False
            return

        # If there are more steps, we need to wait for this step to complete
        # For now, we'll use a simple approach: check if idle after a short delay
        if self._sequence_queue:
            # Schedule the next step to run after current operations complete
            self._schedule_next_sequence_step()
        else:
            self._sequence_running = False

    def _schedule_next_sequence_step(self) -> None:
        """Internal: Schedule the next sequence step after current operation completes"""
        # We need to poll until the rig becomes idle (all transitions complete)
        def check_and_continue():
            # Check if all async operations are done
            if (self._speed_transition is None and
                self._direction_transition is None and
                len(self._position_transitions) == 0):
                # Idle - run next step
                self._run_next_in_sequence()
            else:
                # Still busy - check again soon
                cron.after("16ms", check_and_continue)

        # Start checking after a frame
        cron.after("16ms", check_and_continue)

    def start(self) -> None:
        """Start the frame loop"""
        if self._cron_job is not None:
            return  # Already running

        self._last_frame_time = time.perf_counter()
        interval_ms = settings.get("user.mouse_rig_frame_interval")
        self._cron_job = cron.interval(f"{interval_ms}ms", self._update_frame)



    def _is_idle(self) -> bool:
        """Check if rig is completely idle (no movement or transitions)"""
        epsilon = settings.get("user.mouse_rig_epsilon")

        # Check if speed and accel are effectively zero
        if abs(self._speed) > epsilon or abs(self._accel) > epsilon:
            return False

        # Check for active transitions
        if self._speed_transition is not None:
            return False
        if self._direction_transition is not None:
            return False

        # Check for active forces
        if len(self._named_forces) > 0:
            return False

        # Check for position transitions
        if len(self._position_transitions) > 0:
            return False

        # Check for pending wait/then callbacks - don't stop if we have scheduled callbacks
        if len(self._pending_wait_jobs) > 0:
            return False

        # Check for active effects (PRD 8)
        if len(self._effect_stacks) > 0:
            return False

        # Check for active effect lifecycles (lifecycle wrappers)
        if len(self._effect_lifecycles) > 0:
            return False

        # Check for active effects (unified property and stack effects)
        if len(self._effects) > 0:
            return False

        # Check for active direction effects
        if len(self._direction_effects) > 0:
            return False

        return True

    def _update_frame(self) -> None:
        """Frame update callback"""
        # Calculate delta time
        current_time = time.perf_counter()
        dt = current_time - self._last_frame_time if self._last_frame_time else 0.016
        self._last_frame_time = current_time

        # Update permanent transitions
        if self._speed_transition:
            self._speed_transition.update(self)
            if self._speed_transition.complete:
                self._speed_transition = None

        if self._direction_transition:
            self._direction_transition.update(self)
            if self._direction_transition.complete:
                self._direction_transition = None

        # Start any property effects that haven't been started yet
        for effect in self._effects:
            if effect.is_property_effect and effect.phase == "not_started":
                current_value = self._speed if effect.property_name == "speed" else self._accel
                effect.start(current_value)

        # Update and cleanup all effects (property and stack-based)
        self._effects = [
            effect for effect in self._effects
            if not effect.complete
        ]

        # Start any direction effects that haven't been started yet
        for effect in self._direction_effects:
            if effect.phase == "not_started":
                effect.start(self._direction)

        # Update and cleanup temporary direction effects
        self._direction_effects = [
            effect for effect in self._direction_effects
            if not effect.complete
        ]

        # Update effect lifecycles (lifecycle wrappers for effect stacks - named effects)
        for key, effect_lifecycle in list(self._effect_lifecycles.items()):
            # Start effect if not started
            if effect_lifecycle.phase == "not_started":
                effect_lifecycle.start()

            # Update lifecycle state (uses perf_counter internally, no dt needed)
            effect_lifecycle.update()

            # Remove completed effects and their underlying stacks
            if effect_lifecycle.complete:
                del self._effect_lifecycles[key]
                # Also remove the effect stack so it stops being applied
                if key in self._effect_stacks:
                    del self._effect_stacks[key]
                if key in self._effect_order:
                    self._effect_order.remove(key)

        # Handle base acceleration (permanent accel changes)
        # Base accel DOES modify cruise speed permanently
        # Use effective accel to include temporary accel effects
        effective_accel = self._get_effective_accel()
        if abs(effective_accel) > 1e-6:
            self._speed += effective_accel * dt
            # Allow negative speed only during ReverseTransition
            if not isinstance(self._direction_transition, ReverseTransition):
                self._speed = max(0.0, self._speed)
            if self.limits_max_speed is not None:
                self._speed = min(self._speed, self.limits_max_speed)

        # Calculate velocity from effective speed and direction
        effective_speed = self._get_effective_speed()

        # Add velocity contributions from acceleration effects
        accel_velocity_contribution = self._get_accel_velocity_contribution()
        total_speed = effective_speed + accel_velocity_contribution

        # Clamp total speed (allow negative during ReverseTransition)
        if self.limits_max_speed is not None:
            total_speed = min(total_speed, self.limits_max_speed)
        if not isinstance(self._direction_transition, ReverseTransition):
            total_speed = max(0.0, total_speed)

        # Get effective direction (with rotation effects applied)
        effective_direction = self._get_effective_direction()

        # Base velocity vector
        velocity = effective_direction * total_speed

        # Add force contributions via vector addition
        # Forces return velocity in pixels/frame (same units as base velocity)
        for force_name, force in list(self._named_forces.items()):
            force_velocity = force.update(dt)
            velocity = velocity + force_velocity

            # Remove completed forces
            if force.complete:
                del self._named_forces[force_name]

        # Apply scale
        scale = settings.get("user.mouse_rig_scale")
        velocity = velocity * scale

        # Update position from velocity
        position_delta = velocity

        # Apply position transitions (glides)
        for pos_transition in self._position_transitions[:]:
            glide_delta = pos_transition.update(self)
            position_delta = position_delta + glide_delta
            if pos_transition.complete:
                self._position_transitions.remove(pos_transition)

        # Apply subpixel adjustment to prevent rounding drift
        dx_int, dy_int = self._subpixel_adjuster.adjust(position_delta.x, position_delta.y)

        # Get current position
        current_x, current_y = ctrl.mouse_pos()

        # Calculate new position from velocity
        new_x = current_x + dx_int
        new_y = current_y + dy_int

        # Apply position transforms (static offsets)
        # Only apply the CHANGE in offset since last frame
        position_offset = self._get_position_offset()
        offset_delta = position_offset - self._last_position_offset
        new_x += int(offset_delta.x)
        new_y += int(offset_delta.y)
        self._last_position_offset = position_offset

        # Move the cursor if position changed (either from velocity or offset)
        if new_x != current_x or new_y != current_y:
            core._mouse_move(new_x, new_y)

        # Auto-stop if completely idle
        if self._is_idle():
            self.stop()


# ============================================================================
# GLOBAL RIG INSTANCE
# ============================================================================

_rig_instance: Optional[RigState] = None


def get_rig() -> RigState:
    """Get or create the global rig instance"""
    global _rig_instance
    if _rig_instance is None:
        _rig_instance = RigState()
        # Don't auto-start - will start on first command
    return _rig_instance


# ============================================================================
# STATE ACCESSORS
# ============================================================================

class StateAccessor:
    """Accessor for computed state (base + modifiers + forces)"""
    def __init__(self, rig_state: 'RigState'):
        self._rig = rig_state

    @property
    def speed(self) -> float:
        """Get computed speed (base with modifiers applied, excluding accel velocity)"""
        return self._rig._get_effective_speed()

    @property
    def accel(self) -> float:
        """Get computed acceleration (base with modifiers applied)"""
        return self._rig._get_effective_accel()

    @property
    def direction(self) -> Tuple[float, float]:
        """Get current direction vector (with effects applied)"""
        dir_vec = self._rig._get_effective_direction()
        return (dir_vec.x, dir_vec.y)

    @property
    def pos(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return ctrl.mouse_pos()

    @property
    def velocity(self) -> Tuple[float, float]:
        """Get total velocity vector (base + transforms + forces)

        Pipeline: base → transforms (scale then shift) → forces (vector addition)
        """
        # Get transformed speed
        effective_speed = self._rig._get_effective_speed()
        accel_velocity = self._rig._get_effective_accel_velocity_contribution()
        total_speed = effective_speed + accel_velocity

        # Get transformed direction
        effective_direction = self._rig._get_effective_direction()

        # Base velocity (after effects)
        velocity_vec = effective_direction * total_speed

        # Add force contributions (independent velocity vectors)
        for force in self._rig._named_forces.values():
            # Forces contribute independent velocity vectors
            force_dir = force._direction
            force_speed = force._speed + force._velocity
            force_vec = force_dir * force_speed
            velocity_vec = velocity_vec + force_vec

        return (velocity_vec.x, velocity_vec.y)



class BaseAccessor:
    """Accessor for base values only (without modifiers/forces)"""
    def __init__(self, rig_state: 'RigState'):
        self._rig = rig_state

    @property
    def speed(self) -> float:
        """Get base speed (without modifiers)"""
        return self._rig._speed

    @property
    def accel(self) -> float:
        """Get base acceleration (without modifiers)"""
        return self._rig._accel

    @property
    def direction(self) -> Tuple[float, float]:
        """Get base direction vector"""
        return (self._rig._direction.x, self._rig._direction.y)

    @property
    def pos(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return ctrl.mouse_pos()