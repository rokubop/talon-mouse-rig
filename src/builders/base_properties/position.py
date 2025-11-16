"""Position builders for base rig - position and glide control"""

from typing import Optional, Callable, TYPE_CHECKING, Literal
from talon import ctrl

from ...core import Vec2, DEFAULT_EASING, PositionTransition
from ..contracts import TimingMethodsContract, TransitionBasedBuilder, PropertyChainingContract, MultiSegmentMixin

if TYPE_CHECKING:
    from ...state import RigState


class PositionController:
    """Controller for position operations (accessed via rig.pos)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def to(self, x: float, y: float) -> 'PositionBuilder':
        """Move to absolute position - instant by default, use .over(ms) for smooth glide"""
        return PositionBuilder(self.rig_state, x, y, mode="absolute", instant=True)

    def by(self, dx: float, dy: float) -> 'PositionBuilder':
        """Move by relative offset - instant by default, use .over(ms) for smooth glide"""
        return PositionBuilder(self.rig_state, dx, dy, mode="relative", instant=True)


class PositionBuilder(MultiSegmentMixin['PositionBuilder'], TimingMethodsContract['PositionBuilder'], TransitionBasedBuilder, PropertyChainingContract):
    """
    Unified builder for position operations - handles both absolute (.to()) and relative (.by()).

    Supports:
    - Instant movement or smooth glides with .over()
    - Hold at position with .hold()
    - Revert to original position with .revert()
    - Stage-specific callbacks with .then()
    """
    def __init__(
        self,
        rig_state: 'RigState',
        x_or_dx: float,
        y_or_dy: float,
        mode: Literal["absolute", "relative"] = "absolute",
        instant: bool = False
    ):
        self.rig_state = rig_state
        self.x_or_dx = x_or_dx
        self.y_or_dy = y_or_dy
        self.mode = mode  # "absolute" for .to(), "relative" for .by()
        self._easing = "ease_in_out"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._hold_duration_ms: Optional[float] = None
        self._out_duration_ms: Optional[float] = None
        self._out_easing: str = "linear"

        # Stage-specific callbacks - support multiple then() calls
        self._after_forward_callbacks: list[Callable] = []
        self._after_hold_callbacks: list[Callable] = []
        self._after_revert_callbacks: list[Callable] = []
        self._current_stage: str = "initial"  # Track what stage we're configuring

        # Multi-segment support (reactive tag assignment)
        self.name: str = ""  # Auto-assigned when chaining begins
        self._is_chaining: bool = False  # Set to True by timing methods
        self._property_name: str = "pos"  # For error messages

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'PositionBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    # ===== MultiSegmentMixin hooks =====

    def _get_queue_builder(self, queue_namespace):
        """Return position builder from queue namespace"""
        return queue_namespace.pos

    # ===== Hooks for TimingMethodsContract =====

    def _calculate_over_duration_from_rate(
        self,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> float:
        """Calculate duration from rate based on distance to target"""
        if rate_speed is not None:
            current_pos = self.rig_state._position
            if self.mode == "absolute":
                target_pos = Vec2(self.x_or_dx, self.y_or_dy)
            else:  # relative
                target_pos = current_pos + Vec2(self.x_or_dx, self.y_or_dy)

            distance = (target_pos - current_pos).magnitude()
            if distance < 0.01:
                return 1.0
            else:
                duration_sec = distance / rate_speed
                return duration_sec * 1000
        return 500.0

    def _store_over_config(self, duration_ms: Optional[float], easing: str, interpolation: str = "lerp") -> None:
        """Store in _duration_ms and optionally override easing, disable instant execution"""
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        if easing is not None:
            self._easing = easing

    def _after_over_configured(self) -> None:
        """Hook called after over() has configured timing"""
        self._current_stage = "over"

    def _after_hold_configured(self) -> None:
        """Hook called after hold() has configured hold duration"""
        self._current_stage = "hold"

    def _after_revert_configured(self) -> None:
        """Hook called after revert() has configured revert duration"""
        self._current_stage = "revert"

    def _calculate_revert_duration_from_rate(self, rate_speed: Optional[float],
                                            rate_accel: Optional[float],
                                            rate_rotation: Optional[float]) -> Optional[float]:
        """Calculate revert duration from movement rate"""
        if rate_speed is not None:
            return 500.0
        return None

    def _has_transition(self) -> bool:
        """Check if this builder should create a transition"""
        return self._duration_ms is not None or self._out_duration_ms is not None

    def _has_instant(self) -> bool:
        """Check if this builder should execute instantly"""
        return self._should_execute_instant

    def _execute_transition(self):
        self._execute_with_timing()

    def _execute(self):
        """Execute the position change based on how the builder was configured"""
        if self._duration_ms is not None or self._out_duration_ms is not None:
            self._execute_with_timing()
        elif self._should_execute_instant:
            self._execute_instant()

    def _execute_with_timing(self):
        """Execute position change with timing (transitions, holds, reverts)"""
        current_pos = Vec2(*ctrl.mouse_pos())

        # Calculate offset based on mode
        if self.mode == "absolute":
            offset = Vec2(self.x_or_dx, self.y_or_dy) - current_pos
            target_pos = Vec2(self.x_or_dx, self.y_or_dy)
        else:  # relative
            offset = Vec2(self.x_or_dx, self.y_or_dy)
            target_pos = current_pos + offset

        # Determine if this is a temporary effect (has .hold() or .revert())
        is_temporary = (self._hold_duration_ms is not None or self._out_duration_ms is not None)

        if is_temporary:
            # UNIFIED: Use PositionEffect with lifecycle support
            from ...effects import PositionEffect

            pos_effect = PositionEffect(
                offset=target_pos if self.mode == "absolute" else offset,
                mode=self.mode
            )

            # UNIFIED: Configure lifecycle using single source of truth
            pos_effect.configure_lifecycle(
                in_duration_ms=self._duration_ms,
                in_easing=self._easing,
                hold_duration_ms=self._hold_duration_ms,
                out_duration_ms=self._out_duration_ms,
                out_easing=self._out_easing,
                after_forward_callbacks=self._after_forward_callbacks if self._after_forward_callbacks else None,
                after_hold_callbacks=self._after_hold_callbacks if self._after_hold_callbacks else None,
                after_revert_callbacks=self._after_revert_callbacks if self._after_revert_callbacks else None
            )

            pos_effect.start(current_pos)
            self.rig_state.start()
            self.rig_state._position_effects.append(pos_effect)
            return

        # Permanent changes with transition (has .over() only, no hold/revert)
        if self._duration_ms is not None and self._duration_ms > 0:
            transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)

            if self._after_forward_callbacks:
                def chain_callbacks():
                    for cb in self._after_forward_callbacks:
                        cb()
                transition.on_complete = chain_callbacks

            self.rig_state.start()
            self.rig_state._position_transitions.append(transition)
        else:
            # Instant movement
            if self.mode == "absolute":
                ctrl.mouse_move(int(self.x_or_dx), int(self.y_or_dy))
            else:
                ctrl.mouse_move(int(current_pos.x + self.x_or_dx), int(current_pos.y + self.y_or_dy))

            if self._after_forward_callbacks:
                for cb in self._after_forward_callbacks:
                    cb()

    def _execute_instant(self):
        if self.mode == "absolute":
            ctrl.mouse_move(int(self.x_or_dx), int(self.y_or_dy))
        else:
            current_x, current_y = ctrl.mouse_pos()
            ctrl.mouse_move(int(current_x + self.x_or_dx), int(current_y + self.y_or_dy))

        # Execute callback immediately
        if self._after_forward_callbacks:
            for cb in self._after_forward_callbacks:
                cb()

    # ===== PropertyChainingContract hooks =====

    def _has_timing_configured(self) -> bool:
        """Check if any timing has been configured"""
        return (
            self._duration_ms is not None or
            self._hold_duration_ms is not None or
            self._out_duration_ms is not None
        )

    def _execute_for_chaining(self) -> None:
        """Execute immediately for property chaining"""
        self._should_execute_instant = True
        self._execute()
