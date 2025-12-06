"""Lifecycle management for builder transitions (over/hold/revert phases)

Handles the temporal aspects of builders:
- Over: Transition from current to target value
- Hold: Sustain the target value
- Revert: Transition back to original value
"""

import time
from typing import Optional, Callable, Any
from .core import Vec2, lerp, get_easing_function, EPSILON
from .contracts import LifecyclePhase
import math


class Lifecycle:
    """Manages the over/hold/revert lifecycle for a builder"""

    def __init__(self, is_user_layer: bool = False):
        # Configuration
        self.over_ms: Optional[float] = None
        self.over_easing: str = "linear"
        self.hold_ms: Optional[float] = None
        self.revert_ms: Optional[float] = None
        self.revert_easing: str = "linear"

        # Whether this is for a is_named_layer builder (affects completion logic)
        self.is_user_layer = is_user_layer

        # Callbacks per phase (phase -> list of callbacks)
        self.callbacks: dict[str, list[Callable]] = {
            LifecyclePhase.OVER: [],
            LifecyclePhase.HOLD: [],
            LifecyclePhase.REVERT: [],
        }

        # Runtime state
        self.phase: Optional[str] = None
        self.phase_start_time: Optional[float] = None
        self.started = False

    def add_callback(self, phase: str, callback: Callable):
        if phase not in self.callbacks:
            self.callbacks[phase] = []
        self.callbacks[phase].append(callback)

    def start(self, current_time: float):
        """Start the lifecycle

        Args:
            current_time: Current timestamp from perf_counter()
        """
        self.started = True
        self.phase_start_time = current_time

        # Determine starting phase
        if self.over_ms is not None and self.over_ms > 0:
            self.phase = LifecyclePhase.OVER
        elif self.hold_ms is not None and self.hold_ms > 0:
            self.phase = LifecyclePhase.HOLD
        elif self.revert_ms is not None and self.revert_ms > 0:
            self.phase = LifecyclePhase.REVERT
        else:
            # Instant application, no lifecycle
            self.phase = LifecyclePhase.OVER

    def advance(self, current_time: float) -> tuple[Optional[str], float]:
        """Advance lifecycle state forward in time.

        Args:
            current_time: Current timestamp from perf_counter() (captured once per frame)

        Returns:
            (current_phase, progress) where progress is [0, 1] with easing applied
            Returns (None, 1.0) if lifecycle is complete
        """
        if not self.started:
            self.start(current_time)

        if self.phase is None:
            # No lifecycle, instant application
            return (None, 1.0)

        elapsed = (current_time - self.phase_start_time) * 1000

        # Calculate progress for current phase
        if self.phase == LifecyclePhase.OVER:
            if self.over_ms is None or self.over_ms == 0:
                progress = 1.0
            else:
                progress = min(1.0, elapsed / self.over_ms)
                # Apply easing
                easing_fn = get_easing_function(self.over_easing)
                progress = easing_fn(progress)

            if elapsed >= (self.over_ms or 0):
                # Over phase complete - advance to next phase
                # Callbacks will be executed by caller after state is applied
                self._advance_to_next_phase(current_time)
                return self.advance(current_time)  # Immediately check next phase

            return (LifecyclePhase.OVER, progress)

        elif self.phase == LifecyclePhase.HOLD:
            if self.hold_ms is None or self.hold_ms == 0:
                progress = 1.0
            else:
                progress = 1.0  # Hold is always at full value

            if elapsed >= (self.hold_ms or 0):
                # Hold phase complete - advance to next phase
                # Callbacks will be executed by caller after state is applied
                self._advance_to_next_phase(current_time)
                return self.advance(current_time)  # Immediately check next phase

            return (LifecyclePhase.HOLD, progress)

        elif self.phase == LifecyclePhase.REVERT:
            if self.revert_ms is None or self.revert_ms == 0:
                progress = 1.0
            else:
                progress = min(1.0, elapsed / self.revert_ms)
                # Apply easing
                easing_fn = get_easing_function(self.revert_easing)
                progress = easing_fn(progress)

            if elapsed >= (self.revert_ms or 0):
                # Revert phase complete
                # Callbacks will be executed by caller after state is applied
                self.phase = None  # Lifecycle complete
                return (None, 1.0)

            return (LifecyclePhase.REVERT, progress)

        return (None, 1.0)

    def _advance_to_next_phase(self, current_time: float):
        """Move to the next lifecycle phase

        Args:
            current_time: Current timestamp from perf_counter()
        """
        self.phase_start_time = current_time

        if self.phase == LifecyclePhase.OVER:
            if self.hold_ms is not None and self.hold_ms > 0:
                self.phase = LifecyclePhase.HOLD
            elif self.revert_ms is not None and self.revert_ms > 0:
                self.phase = LifecyclePhase.REVERT
            else:
                self.phase = None

        elif self.phase == LifecyclePhase.HOLD:
            if self.revert_ms is not None and self.revert_ms > 0:
                self.phase = LifecyclePhase.REVERT
            else:
                self.phase = None

        elif self.phase == LifecyclePhase.REVERT:
            self.phase = None

    def get_phase_callbacks(self, phase: str) -> list:
        return self.callbacks.get(phase, [])

    def execute_callbacks(self, phase: str):
        for callback in self.callbacks.get(phase, []):
            try:
                callback()
            except Exception as e:
                print(f"Error in lifecycle callback: {e}")

    def is_complete(self) -> bool:
        if not self.has_any_lifecycle():
            return True

        return self.started and self.phase is None

    def has_any_lifecycle(self) -> bool:
        return (
            (self.over_ms is not None and self.over_ms > 0) or
            (self.hold_ms is not None and self.hold_ms > 0) or
            (self.revert_ms is not None and self.revert_ms >= 0)
        )

    def is_reverting(self) -> bool:
        return self.phase == LifecyclePhase.REVERT

    def has_reverted(self) -> bool:
        """Check if this lifecycle completed with a revert phase

        Only returns True if revert_ms was explicitly set (meaning .revert() was called).
        Builders with only .over() or .hold() should still bake.
        """
        return (
            self.started and
            self.phase is None and
            self.revert_ms is not None and
            self.revert_ms >= 0
        )

    def is_animating(self) -> bool:
        """Check if lifecycle is currently in an active animation phase.

        Returns True if in OVER or REVERT phase (actively animating).
        Returns False if in HOLD phase (static) or complete (phase is None).
        """
        return self.phase in (LifecyclePhase.OVER, LifecyclePhase.REVERT)

    def should_be_garbage_collected(self) -> bool:
        """Check if builder should be removed from active builders.

        Garbage collection rules:
        - Anonymous builders: removed when lifecycle completes
        - Named builders: removed only when explicitly reverted
        - Any builder: removed if reverted (regardless of named/anonymous)

        This ensures:
        - Anonymous builders don't persist after completion
        - Named builders without lifecycle stay active indefinitely
        - Named builders with lifecycle (but no revert) stay active after completion
        - Any builder that reverts gets cleaned up
        """
        # Not complete yet - keep it
        if not self.is_complete():
            return False

        # Reverted - always remove (named or anonymous)
        if self.has_reverted():
            return True

        # Anonymous and complete (no revert) - remove it
        if not self.is_user_layer:
            return True

        # Named, complete, not reverted - keep it active
        return False


class PropertyAnimator:
    """Handles animation of property values during lifecycle phases"""

    @staticmethod
    def animate_scalar(
        base_value: float,
        target_value: float,
        phase: Optional[str],
        progress: float,
        has_reverted: bool = False
    ) -> float:
        """Animate a scalar property value.

        Args:
            base_value: The neutral/starting value (depends on mode: 0 for offset, 1 for scale, base for override)
            target_value: The target value to animate to
            phase: Current lifecycle phase
            progress: Progress [0, 1] within current phase
            has_reverted: Whether this lifecycle completed via revert

        Returns:
            Current animated value
        """
        if phase is None:
            # Lifecycle complete
            if has_reverted:
                return base_value  # Return to neutral
            return target_value

        # Animate from base to target
        if phase == LifecyclePhase.OVER:
            return lerp(base_value, target_value, progress)
        elif phase == LifecyclePhase.HOLD:
            return target_value
        elif phase == LifecyclePhase.REVERT:
            return lerp(target_value, base_value, progress)

        return target_value

    @staticmethod
    def animate_direction(
        base_dir: Vec2,
        target_dir: Vec2,
        phase: Optional[str],
        progress: float,
        has_reverted: bool = False,
        interpolation: str = "lerp"
    ) -> Vec2:
        """Animate a direction vector using lerp or slerp.

        Args:
            base_dir: The base direction vector (normalized)
            target_dir: The target direction vector (normalized)
            phase: Current lifecycle phase
            progress: Progress [0, 1] within current phase
            has_reverted: Whether this lifecycle completed via revert
            interpolation: "lerp" for linear interpolation or "slerp" for spherical

        Returns:
            Current animated direction vector
        """
        if phase is None:
            # Lifecycle complete
            if has_reverted:
                # Revert complete - return to base direction
                return base_dir
            return target_dir

        if phase == LifecyclePhase.OVER:
            if interpolation == "slerp":
                return _slerp(base_dir, target_dir, progress)
            else:
                return _lerp_direction(base_dir, target_dir, progress)
        elif phase == LifecyclePhase.HOLD:
            return target_dir
        elif phase == LifecyclePhase.REVERT:
            if interpolation == "slerp":
                return _slerp(target_dir, base_dir, progress)
            else:
                return _lerp_direction(target_dir, base_dir, progress)

        return target_dir

    @staticmethod
    def animate_position(
        base_pos: Vec2,
        target_offset: Vec2,
        phase: Optional[str],
        progress: float,
        has_reverted: bool = False
    ) -> Vec2:
        """Animate a position offset.

        Args:
            base_pos: The base position
            target_offset: The target offset from base
            phase: Current lifecycle phase
            progress: Progress [0, 1] within current phase
            has_reverted: Whether this lifecycle completed via revert

        Returns:
            Current offset to apply
        """
        if phase is None:
            # Lifecycle complete
            if has_reverted:
                # Revert complete - return zero offset (back to base)
                return Vec2(0, 0)
            return target_offset

        if phase == LifecyclePhase.OVER:
            return target_offset * progress
        elif phase == LifecyclePhase.HOLD:
            return target_offset
        elif phase == LifecyclePhase.REVERT:
            return target_offset * (1.0 - progress)

        return target_offset

    @staticmethod
    def animate_vector(
        base_vector: Vec2,
        target_vector: Vec2,
        phase: Optional[str],
        progress: float,
        has_reverted: bool = False,
        interpolation: str = 'lerp'
    ) -> Vec2:
        """Animate a velocity vector (speed + direction combined).

        Args:
            base_vector: The base velocity vector
            target_vector: The target velocity vector
            phase: Optional[str]
            progress: Progress [0, 1] within current phase
            has_reverted: Whether this lifecycle completed via revert
            interpolation: 'lerp' for magnitude/direction, 'linear' for component-wise

        Returns:
            Current animated velocity vector
        """
        if phase is None:
            # Lifecycle complete
            if has_reverted:
                return base_vector
            return target_vector

        if phase == LifecyclePhase.OVER:
            # If 'linear', lerp vector components directly (for smooth reversals through zero)
            if interpolation == 'linear':
                x = base_vector.x + (target_vector.x - base_vector.x) * progress
                y = base_vector.y + (target_vector.y - base_vector.y) * progress
                return Vec2(x, y)
            # Interpolate both magnitude and direction
            base_speed = base_vector.magnitude()
            target_speed = target_vector.magnitude()
            interpolated_speed = lerp(base_speed, target_speed, progress)

            # Handle zero vectors
            if base_speed < EPSILON and target_speed < EPSILON:
                return Vec2(0, 0)
            elif base_speed < EPSILON:
                return target_vector.normalized() * interpolated_speed
            elif target_speed < EPSILON:
                return base_vector.normalized() * (base_speed * (1.0 - progress))

            # Interpolate direction
            base_dir = base_vector.normalized()
            target_dir = target_vector.normalized()
            interpolated_dir = _lerp_direction(base_dir, target_dir, progress)

            return interpolated_dir * interpolated_speed

        elif phase == LifecyclePhase.HOLD:
            return target_vector

        elif phase == LifecyclePhase.REVERT:
            # If 'linear', lerp vector components directly
            if interpolation == 'linear':
                x = target_vector.x + (base_vector.x - target_vector.x) * progress
                y = target_vector.y + (base_vector.y - target_vector.y) * progress
                return Vec2(x, y)

            # Interpolate back from target to base
            base_speed = base_vector.magnitude()
            target_speed = target_vector.magnitude()
            interpolated_speed = lerp(target_speed, base_speed, progress)

            # Handle zero vectors
            if base_speed < EPSILON and target_speed < EPSILON:
                return Vec2(0, 0)
            elif base_speed < EPSILON:
                return target_vector.normalized() * (target_speed * (1.0 - progress))
            elif target_speed < EPSILON:
                return base_vector.normalized() * interpolated_speed

            # Interpolate direction
            base_dir = base_vector.normalized()
            target_dir = target_vector.normalized()
            interpolated_dir = _lerp_direction(target_dir, base_dir, progress)

            return interpolated_dir * interpolated_speed

        return target_vector


def _lerp_direction(v1: Vec2, v2: Vec2, t: float) -> Vec2:
    """Linear interpolation between two direction vectors

    Args:
        v1: Start direction vector
        v2: End direction vector
        t: Progress [0, 1]
    """
    x = v1.x + (v2.x - v1.x) * t
    y = v1.y + (v2.y - v1.y) * t
    return Vec2(x, y).normalized()
def _slerp(v1: Vec2, v2: Vec2, t: float) -> Vec2:
    """Spherical linear interpolation between two direction vectors"""
    # Calculate angle between vectors
    dot = v1.dot(v2)
    dot = max(-1.0, min(1.0, dot))  # Clamp to avoid math domain errors
    angle = math.acos(dot)

    if angle < EPSILON:
        # Vectors are nearly identical
        return v2

    # Calculate cross product to determine rotation direction
    cross = v1.x * v2.y - v1.y * v2.x
    direction = 1 if cross >= 0 else -1

    # Rotate v1 by (angle * t * direction)
    current_angle = angle * t * direction
    cos_a = math.cos(current_angle)
    sin_a = math.sin(current_angle)

    new_x = v1.x * cos_a - v1.y * sin_a
    new_y = v1.x * sin_a + v1.y * cos_a

    return Vec2(new_x, new_y).normalized()


def calculate_vector_transition(
    current: Vec2,
    target: Vec2,
    progress: float
) -> Vec2:
    """Calculate the interpolated vector value during a transition.

    Args:
        current: Current vector value
        target: Target vector value
        progress: Transition progress [0, 1]

    Returns:
        Interpolated vector value
    """
    interpolated_speed = lerp(current.magnitude(), target.magnitude(), progress)
    interpolated_direction = lerp(current.normalized(), target.normalized(), progress).normalized()

    return interpolated_direction * interpolated_speed
