"""Position builders for base rig - position and glide control"""

from typing import Optional, Callable, TYPE_CHECKING, Literal
from talon import ctrl, cron

from ...core import Vec2, DEFAULT_EASING, PositionTransition
from ..contracts import TimingMethodsContract, TransitionBasedBuilder, PropertyChainingContract

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


class PositionBuilder(TimingMethodsContract['PositionBuilder'], TransitionBasedBuilder, PropertyChainingContract):
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
        self._original_pos: Optional[Vec2] = None
        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'PositionBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

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

    def _store_over_config(self, duration_ms: Optional[float], easing: str) -> None:
        """Store in _duration_ms and optionally override easing, disable instant execution"""
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        if easing is not None:
            self._easing = easing

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
        self._original_pos = current_pos

        offset = self._calculate_forward_offset(current_pos)
        transition = self._create_forward_transition(current_pos, offset)

        callback_chain = self._build_callback_chain()
        self._start_transition(transition, callback_chain)

    def _calculate_forward_offset(self, current_pos: Vec2) -> Vec2:
        """Calculate the offset for forward movement based on mode"""
        if self.mode == "absolute":
            target_pos = Vec2(self.x_or_dx, self.y_or_dy)
            return target_pos - current_pos
        else:
            return Vec2(self.x_or_dx, self.y_or_dy)

    def _create_forward_transition(self, current_pos: Vec2, offset: Vec2) -> Optional[PositionTransition]:
        """Create transition for forward movement, or execute instant move"""
        if self._duration_ms is not None and self._duration_ms > 0:
            return PositionTransition(current_pos, offset, self._duration_ms, self._easing)
        else:
            if self.mode == "absolute":
                ctrl.mouse_move(int(self.x_or_dx), int(self.y_or_dy))
            else:
                ctrl.mouse_move(int(current_pos.x + self.x_or_dx), int(current_pos.y + self.y_or_dy))
            return None

    def _build_callback_chain(self) -> Callable:
        """Build the complete callback chain: forward → hold → revert"""
        hold_duration = self._hold_duration_ms or 0

        revert_callback = self._create_revert_callback() if self._out_duration_ms is not None else None
        hold_callback = self._create_hold_callback(revert_callback)
        return self._create_forward_callback(hold_duration, hold_callback)

    def _create_revert_callback(self) -> Callable:
        """Create callback that handles reverting to original position"""
        revert_duration = self._out_duration_ms
        revert_easing = self._out_easing
        after_revert_cb = self._after_revert_callback
        rig_state = self.rig_state

        if self.mode == "absolute":
            original_x, original_y = self._original_pos.x, self._original_pos.y

            def schedule_revert():
                curr_pos = Vec2(*ctrl.mouse_pos())
                back_offset = Vec2(original_x, original_y) - curr_pos

                if revert_duration > 0:
                    revert_transition = PositionTransition(
                        curr_pos, back_offset, revert_duration, revert_easing
                    )
                    if after_revert_cb:
                        revert_transition.on_complete = after_revert_cb
                    rig_state.start()
                    rig_state._position_transitions.append(revert_transition)
                else:
                    ctrl.mouse_move(int(original_x), int(original_y))
                    if after_revert_cb:
                        after_revert_cb()
        else:
            # Relative: revert using inverse offset
            inverse_offset = Vec2(-self.x_or_dx, -self.y_or_dy)

            def schedule_revert():
                curr_pos = Vec2(*ctrl.mouse_pos())

                if revert_duration > 0:
                    revert_transition = PositionTransition(
                        curr_pos, inverse_offset, revert_duration, revert_easing
                    )
                    if after_revert_cb:
                        revert_transition.on_complete = after_revert_cb
                    rig_state.start()
                    rig_state._position_transitions.append(revert_transition)
                else:
                    ctrl.mouse_move(int(curr_pos.x - self.x_or_dx), int(curr_pos.y - self.y_or_dy))
                    if after_revert_cb:
                        after_revert_cb()

        return schedule_revert

    def _create_hold_callback(self, revert_callback: Optional[Callable]) -> Optional[Callable]:
        """Create callback for hold stage, combining hold callback with revert"""
        if revert_callback is None:
            # No revert, just use the after_hold callback
            return self._after_hold_callback

        # Combine after_hold callback with revert scheduling
        def after_hold_combined():
            if self._after_hold_callback:
                self._after_hold_callback()
            revert_callback()

        return after_hold_combined

    def _create_forward_callback(self, hold_duration: float, hold_callback: Optional[Callable]) -> Callable:
        """Create callback for forward movement completion"""
        def after_forward_combined():
            # Call after_forward callback
            if self._after_forward_callback:
                self._after_forward_callback()

            # Schedule hold period if specified
            if hold_duration > 0:
                if hold_callback:
                    cron.after(f"{hold_duration}ms", hold_callback)
            else:
                # No hold, go straight to after_hold callback (which includes revert)
                if hold_callback:
                    hold_callback()

        return after_forward_combined

    def _start_transition(self, transition: Optional[PositionTransition], callback: Callable):
        """Start the transition or call callback immediately if instant"""
        if transition is not None:
            transition.on_complete = callback
            self.rig_state.start()
            self.rig_state._position_transitions.append(transition)
        else:
            # Instant forward, call callback immediately
            callback()

    def _execute_instant(self):
        if self.mode == "absolute":
            ctrl.mouse_move(int(self.x_or_dx), int(self.y_or_dy))
        else:
            current_x, current_y = ctrl.mouse_pos()
            ctrl.mouse_move(int(current_x + self.x_or_dx), int(current_y + self.y_or_dy))

        # Execute callback immediately
        if self._after_forward_callback:
            self._after_forward_callback()

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
