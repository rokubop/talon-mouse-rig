"""Position builders for base rig - position and glide control"""

import time
from typing import Optional, Callable, TYPE_CHECKING
from talon import ctrl, cron

from ..core import (
    Vec2, DEFAULT_EASING, PositionTransition,
    _error_unknown_builder_attribute
)

if TYPE_CHECKING:
    from ..state import RigState

class PositionController:
    """Controller for position operations (accessed via rig.pos)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def to(self, x: float, y: float) -> 'PositionToBuilder':
        """Move to absolute position - instant by default, use .over(ms) for smooth glide"""
        return PositionToBuilder(self.rig_state, x, y, instant=True)

    def by(self, dx: float, dy: float) -> 'PositionByBuilder':
        """Move by relative offset - instant by default, use .over(ms) for smooth glide"""
        return PositionByBuilder(self.rig_state, dx, dy, instant=True)



class PositionToBuilder:
    """Builder for pos.to() operations"""
    def __init__(self, rig_state: 'RigState', x: float, y: float, instant: bool = False):
        self.rig_state = rig_state
        self.x = x
        self.y = y
        self._easing = "ease_in_out"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._hold_duration_ms: Optional[float] = None
        self._revert_duration_ms: Optional[float] = None
        self._revert_easing: str = "linear"
        self._original_pos: Optional[Vec2] = None
        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def over(self, duration_ms: float, easing: str = None) -> 'PositionToBuilder':
        """Glide to position over time"""
        # Disable instant execution since we're doing a transition
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        if easing is not None:
            self._easing = easing
        self._current_stage = "after_forward"
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'PositionToBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def hold(self, duration_ms: float) -> 'PositionToBuilder':
        """Hold at target position before reverting"""
        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'PositionToBuilder':
        """Move back to original position after hold (or immediately if no hold)"""
        self._revert_duration_ms = duration_ms
        self._revert_easing = easing
        self._current_stage = "after_revert"
        return self

    def then(self, callback: Callable) -> 'PositionToBuilder':
        """Execute callback at the current point in the chain

        Can be called multiple times at different stages:
        - After .over(): fires when forward movement completes
        - After .hold(): fires when hold period completes
        - After .revert(): fires when revert completes

        Examples:
            rig.pos.to(x, y).over(500).then(do_something)
            rig.pos.to(x, y).over(500).then(start_drag).revert(500).then(end_drag)
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        else:
            # Default: fire after forward movement
            self._after_forward_callback = callback
        return self

    def __del__(self):
        """Execute the position change based on how the builder was configured"""
        try:
            if self._duration_ms is not None or self._revert_duration_ms is not None:
                # Store original position for potential revert
                current_pos = Vec2(*ctrl.mouse_pos())
                self._original_pos = current_pos

                # Create forward transition (to target)
                target_pos = Vec2(self.x, self.y)
                offset = target_pos - current_pos

                if self._duration_ms is not None:
                    # Animate to target
                    transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)
                else:
                    # Instant move to target
                    ctrl.mouse_move(int(self.x), int(self.y))
                    transition = None

                # Build callback chain from the end backwards
                rig_state = self.rig_state
                hold_duration = self._hold_duration_ms or 0

                # Stage 3: After revert callback
                after_revert_cb = self._after_revert_callback

                # Stage 2: After hold + schedule revert + after_revert callback
                if self._revert_duration_ms is not None:
                    original_x, original_y = self._original_pos.x, self._original_pos.y
                    revert_duration = self._revert_duration_ms
                    revert_easing = self._revert_easing

                    def schedule_revert():
                        # Move back to original position
                        curr_pos = Vec2(*ctrl.mouse_pos())
                        back_offset = Vec2(original_x, original_y) - curr_pos

                        if revert_duration > 0:
                            # Animate back
                            revert_transition = PositionTransition(
                                curr_pos, back_offset, revert_duration, revert_easing
                            )
                            # Attach after-revert callback
                            if after_revert_cb:
                                revert_transition.on_complete = after_revert_cb
                            rig_state._position_transitions.append(revert_transition)
                        else:
                            # Instant revert
                            ctrl.mouse_move(int(original_x), int(original_y))
                            if after_revert_cb:
                                after_revert_cb()

                    # Combine after_hold callback with revert scheduling
                    def after_hold_combined():
                        if self._after_hold_callback:
                            self._after_hold_callback()
                        schedule_revert()

                    after_hold_cb = after_hold_combined
                else:
                    # No revert, just use the after_hold callback
                    after_hold_cb = self._after_hold_callback

                # Stage 1: After forward + hold + callbacks
                def after_forward_combined():
                    # Call after_forward callback
                    if self._after_forward_callback:
                        self._after_forward_callback()

                    # Schedule hold period if specified
                    if hold_duration > 0:
                        if after_hold_cb:
                            cron.after(f"{hold_duration}ms", after_hold_cb)
                    else:
                        # No hold, go straight to after_hold callback (which includes revert)
                        if after_hold_cb:
                            after_hold_cb()

                # Wire up the forward transition
                if transition is not None:
                    transition.on_complete = after_forward_combined
                    self.rig_state.start()  # Ensure ticking is active
                    self.rig_state._position_transitions.append(transition)
                else:
                    # Instant forward, call callback immediately
                    after_forward_combined()

            elif self._should_execute_instant:
                # Instant move
                ctrl.mouse_move(int(self.x), int(self.y))

                # Execute callback immediately
                if self._after_forward_callback:
                    self._after_forward_callback()
        except:
            pass  # Ignore errors during cleanup

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._hold_duration_ms is not None or
                self._revert_duration_ms is not None
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .wait, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.pos.to(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current position change immediately
            self._should_execute_instant = True

            # Trigger execution via __del__
            self.__del__()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
                return PositionController(self.rig_state)
            elif name == 'direction':
                return DirectionController(self.rig_state)

        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after pos.to().\n\n"
                "Instead, use separate statements."
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute(
            'PositionToBuilder',
            name,
            'over, hold, revert, then'
        ))



class PositionByBuilder:
    """Builder for pos.by() operations"""
    def __init__(self, rig_state: 'RigState', dx: float, dy: float, instant: bool = False):
        self.rig_state = rig_state
        self.dx = dx
        self.dy = dy
        self._easing = "ease_in_out"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._hold_duration_ms: Optional[float] = None
        self._revert_duration_ms: Optional[float] = None
        self._revert_easing: str = "linear"
        self._original_pos: Optional[Vec2] = None
        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def over(self, duration_ms: float, easing: str = None) -> 'PositionByBuilder':
        """Glide by offset over time"""
        # Disable instant execution since we're doing a transition
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        if easing is not None:
            self._easing = easing
        self._current_stage = "after_forward"
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'PositionByBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def hold(self, duration_ms: float) -> 'PositionByBuilder':
        """Hold at target position before reverting"""
        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'PositionByBuilder':
        """Move back to original position after hold (or immediately if no hold)"""
        self._revert_duration_ms = duration_ms
        self._revert_easing = easing
        self._current_stage = "after_revert"
        return self

    def then(self, callback: Callable) -> 'PositionByBuilder':
        """Execute callback at the current point in the chain

        Can be called multiple times at different stages:
        - After .over(): fires when forward movement completes
        - After .hold(): fires when hold period completes
        - After .revert(): fires when revert completes

        Examples:
            rig.pos.by(dx, dy).over(500).then(do_something)
            rig.pos.by(dx, dy).over(500).then(start_drag).revert(500).then(end_drag)
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        else:
            # Default: fire after forward movement
            self._after_forward_callback = callback
        return self

    def __del__(self):
        """Execute the position change based on how the builder was configured"""
        try:
            if self._duration_ms is not None or self._revert_duration_ms is not None:
                # Store original position for potential revert
                current_pos = Vec2(*ctrl.mouse_pos())
                self._original_pos = current_pos

                # Create forward transition (by offset)
                offset = Vec2(self.dx, self.dy)

                if self._duration_ms is not None:
                    # Animate by offset
                    transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)
                else:
                    # Instant move by offset
                    ctrl.mouse_move(int(current_pos.x + self.dx), int(current_pos.y + self.dy))
                    transition = None

                # Build callback chain from the end backwards
                rig_state = self.rig_state
                hold_duration = self._hold_duration_ms or 0

                # Stage 3: After revert callback
                after_revert_cb = self._after_revert_callback

                # Stage 2: After hold + schedule revert + after_revert callback
                if self._revert_duration_ms is not None:
                    revert_duration = self._revert_duration_ms
                    revert_easing = self._revert_easing
                    # Use inverse offset for precise return
                    inverse_offset = Vec2(-self.dx, -self.dy)

                    def schedule_revert():
                        # Move back by exact inverse offset
                        curr_pos = Vec2(*ctrl.mouse_pos())

                        if revert_duration > 0:
                            # Animate back using inverse offset
                            revert_transition = PositionTransition(
                                curr_pos, inverse_offset, revert_duration, revert_easing
                            )
                            # Attach after-revert callback
                            if after_revert_cb:
                                revert_transition.on_complete = after_revert_cb
                            rig_state._position_transitions.append(revert_transition)
                        else:
                            # Instant revert using inverse offset
                            ctrl.mouse_move(int(curr_pos.x - self.dx), int(curr_pos.y - self.dy))
                            if after_revert_cb:
                                after_revert_cb()

                    # Combine after_hold callback with revert scheduling
                    def after_hold_combined():
                        if self._after_hold_callback:
                            self._after_hold_callback()
                        schedule_revert()

                    after_hold_cb = after_hold_combined
                else:
                    # No revert, just use the after_hold callback
                    after_hold_cb = self._after_hold_callback

                # Stage 1: After forward + hold + callbacks
                def after_forward_combined():
                    # Call after_forward callback
                    if self._after_forward_callback:
                        self._after_forward_callback()

                    # Schedule hold period if specified
                    if hold_duration > 0:
                        if after_hold_cb:
                            cron.after(f"{hold_duration}ms", after_hold_cb)
                    else:
                        # No hold, go straight to after_hold callback (which includes revert)
                        if after_hold_cb:
                            after_hold_cb()

                # Wire up the forward transition
                if transition is not None:
                    transition.on_complete = after_forward_combined
                    self.rig_state.start()  # Ensure ticking is active
                    self.rig_state._position_transitions.append(transition)
                else:
                    # Instant forward, call callback immediately
                    after_forward_combined()

            elif self._should_execute_instant:
                # Instant move
                current_x, current_y = ctrl.mouse_pos()
                ctrl.mouse_move(int(current_x + self.dx), int(current_y + self.dy))

                # Execute callback immediately
                if self._after_forward_callback:
                    self._after_forward_callback()
        except:
            pass  # Ignore errors during cleanup

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._hold_duration_ms is not None or
                self._revert_duration_ms is not None
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.pos.by(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current position change immediately
            self._should_execute_instant = True

            # Trigger execution via __del__
            self.__del__()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
                return PositionController(self.rig_state)
            elif name == 'direction':
                return DirectionController(self.rig_state)

        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after pos.by().\n\n"
                "Instead, use separate statements."
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute(
            'PositionByBuilder',
            name,
            'over, hold, revert, then'
        ))


class PositionController:
    """Controller for position operations (accessed via rig.pos)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def to(self, x: float, y: float) -> 'PositionToBuilder':
        """Move to absolute position - instant by default, use .over(ms) for smooth glide"""
        return PositionToBuilder(self.rig_state, x, y, instant=True)

    def by(self, dx: float, dy: float) -> 'PositionByBuilder':
        """Move by relative offset - instant by default, use .over(ms) for smooth glide"""
        return PositionByBuilder(self.rig_state, dx, dy, instant=True)



class PositionToBuilder:
    """Builder for pos.to() operations"""
    def __init__(self, rig_state: 'RigState', x: float, y: float, instant: bool = False):
        self.rig_state = rig_state
        self.x = x
        self.y = y
        self._easing = "ease_in_out"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._hold_duration_ms: Optional[float] = None
        self._revert_duration_ms: Optional[float] = None
        self._revert_easing: str = "linear"
        self._original_pos: Optional[Vec2] = None
        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def over(self, duration_ms: float, easing: str = None) -> 'PositionToBuilder':
        """Glide to position over time"""
        # Disable instant execution since we're doing a transition
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        if easing is not None:
            self._easing = easing
        self._current_stage = "after_forward"
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'PositionToBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def hold(self, duration_ms: float) -> 'PositionToBuilder':
        """Hold at target position before reverting"""
        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'PositionToBuilder':
        """Move back to original position after hold (or immediately if no hold)"""
        self._revert_duration_ms = duration_ms
        self._revert_easing = easing
        self._current_stage = "after_revert"
        return self

    def then(self, callback: Callable) -> 'PositionToBuilder':
        """Execute callback at the current point in the chain

        Can be called multiple times at different stages:
        - After .over(): fires when forward movement completes
        - After .hold(): fires when hold period completes
        - After .revert(): fires when revert completes

        Examples:
            rig.pos.to(x, y).over(500).then(do_something)
            rig.pos.to(x, y).over(500).then(start_drag).revert(500).then(end_drag)
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        else:
            # Default: fire after forward movement
            self._after_forward_callback = callback
        return self

    def __del__(self):
        """Execute the position change based on how the builder was configured"""
        try:
            if self._duration_ms is not None or self._revert_duration_ms is not None:
                # Store original position for potential revert
                current_pos = Vec2(*ctrl.mouse_pos())
                self._original_pos = current_pos

                # Create forward transition (to target)
                target_pos = Vec2(self.x, self.y)
                offset = target_pos - current_pos

                if self._duration_ms is not None:
                    # Animate to target
                    transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)
                else:
                    # Instant move to target
                    ctrl.mouse_move(int(self.x), int(self.y))
                    transition = None

                # Build callback chain from the end backwards
                rig_state = self.rig_state
                hold_duration = self._hold_duration_ms or 0

                # Stage 3: After revert callback
                after_revert_cb = self._after_revert_callback

                # Stage 2: After hold + schedule revert + after_revert callback
                if self._revert_duration_ms is not None:
                    original_x, original_y = self._original_pos.x, self._original_pos.y
                    revert_duration = self._revert_duration_ms
                    revert_easing = self._revert_easing

                    def schedule_revert():
                        # Move back to original position
                        curr_pos = Vec2(*ctrl.mouse_pos())
                        back_offset = Vec2(original_x, original_y) - curr_pos

                        if revert_duration > 0:
                            # Animate back
                            revert_transition = PositionTransition(
                                curr_pos, back_offset, revert_duration, revert_easing
                            )
                            # Attach after-revert callback
                            if after_revert_cb:
                                revert_transition.on_complete = after_revert_cb
                            rig_state._position_transitions.append(revert_transition)
                        else:
                            # Instant revert
                            ctrl.mouse_move(int(original_x), int(original_y))
                            if after_revert_cb:
                                after_revert_cb()

                    # Combine after_hold callback with revert scheduling
                    def after_hold_combined():
                        if self._after_hold_callback:
                            self._after_hold_callback()
                        schedule_revert()

                    after_hold_cb = after_hold_combined
                else:
                    # No revert, just use the after_hold callback
                    after_hold_cb = self._after_hold_callback

                # Stage 1: After forward + hold + callbacks
                def after_forward_combined():
                    # Call after_forward callback
                    if self._after_forward_callback:
                        self._after_forward_callback()

                    # Schedule hold period if specified
                    if hold_duration > 0:
                        if after_hold_cb:
                            cron.after(f"{hold_duration}ms", after_hold_cb)
                    else:
                        # No hold, go straight to after_hold callback (which includes revert)
                        if after_hold_cb:
                            after_hold_cb()

                # Wire up the forward transition
                if transition is not None:
                    transition.on_complete = after_forward_combined
                    self.rig_state.start()  # Ensure ticking is active
                    self.rig_state._position_transitions.append(transition)
                else:
                    # Instant forward, call callback immediately
                    after_forward_combined()

            elif self._should_execute_instant:
                # Instant move
                ctrl.mouse_move(int(self.x), int(self.y))

                # Execute callback immediately
                if self._after_forward_callback:
                    self._after_forward_callback()
        except:
            pass  # Ignore errors during cleanup

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._hold_duration_ms is not None or
                self._revert_duration_ms is not None
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .wait, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.pos.to(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current position change immediately
            self._should_execute_instant = True

            # Trigger execution via __del__
            self.__del__()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
                return PositionController(self.rig_state)
            elif name == 'direction':
                return DirectionController(self.rig_state)

        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after pos.to().\n\n"
                "Instead, use separate statements."
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute(
            'PositionToBuilder',
            name,
            'over, hold, revert, then'
        ))



class PositionByBuilder:
    """Builder for pos.by() operations"""
    def __init__(self, rig_state: 'RigState', dx: float, dy: float, instant: bool = False):
        self.rig_state = rig_state
        self.dx = dx
        self.dy = dy
        self._easing = "ease_in_out"
        self._duration_ms = None
        self._should_execute_instant = instant
        self._hold_duration_ms: Optional[float] = None
        self._revert_duration_ms: Optional[float] = None
        self._revert_easing: str = "linear"
        self._original_pos: Optional[Vec2] = None
        # Stage-specific callbacks
        self._after_forward_callback: Optional[Callable] = None
        self._after_hold_callback: Optional[Callable] = None
        self._after_revert_callback: Optional[Callable] = None
        self._current_stage: str = "initial"  # Track what stage we're configuring

    def over(self, duration_ms: float, easing: str = None) -> 'PositionByBuilder':
        """Glide by offset over time"""
        # Disable instant execution since we're doing a transition
        self._should_execute_instant = False
        self._duration_ms = duration_ms
        if easing is not None:
            self._easing = easing
        self._current_stage = "after_forward"
        return self

    def ease(self, easing_type: str = DEFAULT_EASING) -> 'PositionByBuilder':
        """Set easing function (defaults to ease_out if not specified)"""
        self._easing = easing_type
        return self

    def hold(self, duration_ms: float) -> 'PositionByBuilder':
        """Hold at target position before reverting"""
        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'PositionByBuilder':
        """Move back to original position after hold (or immediately if no hold)"""
        self._revert_duration_ms = duration_ms
        self._revert_easing = easing
        self._current_stage = "after_revert"
        return self

    def then(self, callback: Callable) -> 'PositionByBuilder':
        """Execute callback at the current point in the chain

        Can be called multiple times at different stages:
        - After .over(): fires when forward movement completes
        - After .hold(): fires when hold period completes
        - After .revert(): fires when revert completes

        Examples:
            rig.pos.by(dx, dy).over(500).then(do_something)
            rig.pos.by(dx, dy).over(500).then(start_drag).revert(500).then(end_drag)
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        else:
            # Default: fire after forward movement
            self._after_forward_callback = callback
        return self

    def __del__(self):
        """Execute the position change based on how the builder was configured"""
        try:
            if self._duration_ms is not None or self._revert_duration_ms is not None:
                # Store original position for potential revert
                current_pos = Vec2(*ctrl.mouse_pos())
                self._original_pos = current_pos

                # Create forward transition (by offset)
                offset = Vec2(self.dx, self.dy)

                if self._duration_ms is not None:
                    # Animate by offset
                    transition = PositionTransition(current_pos, offset, self._duration_ms, self._easing)
                else:
                    # Instant move by offset
                    ctrl.mouse_move(int(current_pos.x + self.dx), int(current_pos.y + self.dy))
                    transition = None

                # Build callback chain from the end backwards
                rig_state = self.rig_state
                hold_duration = self._hold_duration_ms or 0

                # Stage 3: After revert callback
                after_revert_cb = self._after_revert_callback

                # Stage 2: After hold + schedule revert + after_revert callback
                if self._revert_duration_ms is not None:
                    revert_duration = self._revert_duration_ms
                    revert_easing = self._revert_easing
                    # Use inverse offset for precise return
                    inverse_offset = Vec2(-self.dx, -self.dy)

                    def schedule_revert():
                        # Move back by exact inverse offset
                        curr_pos = Vec2(*ctrl.mouse_pos())

                        if revert_duration > 0:
                            # Animate back using inverse offset
                            revert_transition = PositionTransition(
                                curr_pos, inverse_offset, revert_duration, revert_easing
                            )
                            # Attach after-revert callback
                            if after_revert_cb:
                                revert_transition.on_complete = after_revert_cb
                            rig_state._position_transitions.append(revert_transition)
                        else:
                            # Instant revert using inverse offset
                            ctrl.mouse_move(int(curr_pos.x - self.dx), int(curr_pos.y - self.dy))
                            if after_revert_cb:
                                after_revert_cb()

                    # Combine after_hold callback with revert scheduling
                    def after_hold_combined():
                        if self._after_hold_callback:
                            self._after_hold_callback()
                        schedule_revert()

                    after_hold_cb = after_hold_combined
                else:
                    # No revert, just use the after_hold callback
                    after_hold_cb = self._after_hold_callback

                # Stage 1: After forward + hold + callbacks
                def after_forward_combined():
                    # Call after_forward callback
                    if self._after_forward_callback:
                        self._after_forward_callback()

                    # Schedule hold period if specified
                    if hold_duration > 0:
                        if after_hold_cb:
                            cron.after(f"{hold_duration}ms", after_hold_cb)
                    else:
                        # No hold, go straight to after_hold callback (which includes revert)
                        if after_hold_cb:
                            after_hold_cb()

                # Wire up the forward transition
                if transition is not None:
                    transition.on_complete = after_forward_combined
                    self.rig_state.start()  # Ensure ticking is active
                    self.rig_state._position_transitions.append(transition)
                else:
                    # Instant forward, call callback immediately
                    after_forward_combined()

            elif self._should_execute_instant:
                # Instant move
                current_x, current_y = ctrl.mouse_pos()
                ctrl.mouse_move(int(current_x + self.dx), int(current_y + self.dy))

                # Execute callback immediately
                if self._after_forward_callback:
                    self._after_forward_callback()
        except:
            pass  # Ignore errors during cleanup

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            has_timing = (
                self._duration_ms is not None or
                self._hold_duration_ms is not None or
                self._revert_duration_ms is not None
            )

            if has_timing:
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .hold, .revert).\n\n"
                    "Use separate statements:\n"
                    f"  rig.pos.by(...).over(...)\n"
                    f"  rig.{name}(...)"
                )

            # Execute current position change immediately
            self._should_execute_instant = True

            # Trigger execution via __del__
            self.__del__()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                return SpeedController(self.rig_state)
            elif name == 'accel':
                return AccelController(self.rig_state)
            elif name == 'pos':
                return PositionController(self.rig_state)
            elif name == 'direction':
                return DirectionController(self.rig_state)

        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after pos.by().\n\n"
                "Instead, use separate statements."
            )

        # Unknown attribute
        raise AttributeError(_error_unknown_builder_attribute(
            'PositionByBuilder',
            name,
            'over, hold, revert, then'
        ))


