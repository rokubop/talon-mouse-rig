from talon import actions, settings, Module
from typing import Any
from .src import rig as get_rig, reload_rig
from .src.sequence import run_sequence, WaitHandle

mod = Module()

BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}

DIRECTION_MAP = {
    "left":       (-1,  0),
    "right":      ( 1,  0),
    "up":         ( 0, -1),
    "down":       ( 0,  1),
    "up_left":    (-1, -1),
    "up_right":   ( 1, -1),
    "down_left":  (-1,  1),
    "down_right": ( 1,  1),
}

def _parse_direction(direction: str) -> tuple:
    key = direction.replace(" ", "_").replace("-", "_").lower()
    return DIRECTION_MAP[key]

@mod.action_class
class Actions:
    def mouse_rig() -> Any:
        """
        Get rig directly for advanced usage.

        ```python
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.direction.to(1, 0)
        rig.direction.by(90).over(100)
        rig.speed(5)
        rig.speed.to(5)
        rig.speed.add(2)
        rig.pos.to(500, 300).over(200, easing="ease_in_out")
        rig.scroll.speed.to(5)
        rig.scroll.direction.to(0, 1)
        rig.scroll.vector.to(0, 10).over(1000)
        rig.scroll.speed.offset.add(5).over(500)
        rig.scroll.speed.by_lines  # default
        rig.scroll.speed.by_pixels
        rig.layer("my_layer").speed.offset.by(10).over(500)
        rig.layer("my_layer").speed.override.to(10).over(500)
        rig.layer("my_layer").revert()
        rig.layer("my_layer").revert(1000, "ease_in_out")
        rig.stop()
        rig.stop(1000)
        rig...over(ms).then(...).hold(ms).then(...).revert(ms).then(...)
        ```
        """
        return get_rig()

    def mouse_rig_state() -> Any:
        """Get rig state for reading computed values.

        ```python
        state = actions.user.mouse_rig_state()
        state.pos            # Vec2 - current screen position
        state.speed          # float - computed speed (base + layers)
        state.direction      # Vec2 - computed direction
        state.vector         # Vec2 - speed * direction
        state.scroll_speed
        state.scroll_direction
        state.scroll_vector
        state.base.speed     # base value only (no layers)
        state.layers         # dict of active layer states
        ```
        """
        return get_rig().state

    def mouse_rig_pos_to(
            x: float,
            y: float,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """Move mouse to absolute position, optionally over time. Uses Talon mouse API.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.pos.to(x, y).over(over_ms, easing).then(callback)
        ```

        Args:
            x: Target x coordinate
            y: Target y coordinate
            over_ms: Duration in ms (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
            callback: Function to call when movement completes (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.pos.to(x, y)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        if callback is not None:
            builder = builder.then(callback)
        return builder

    def mouse_rig_pos_to_natural(
            x: float,
            y: float,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """Move mouse to absolute position with smooth easing.
        Defaults from mouse_rig_natural_pos_ms and mouse_rig_natural_pos_easing settings.

        Args:
            x: Target x coordinate
            y: Target y coordinate
            over_ms: Duration in ms (default: from settings)
            easing: Easing function (default: from settings)
            callback: Function to call when movement completes (optional)
        """
        if over_ms is None:
            over_ms = settings.get("user.mouse_rig_natural_pos_ms")
        if easing is None:
            easing = settings.get("user.mouse_rig_natural_pos_easing")
        rig = actions.user.mouse_rig()
        builder = rig.pos.to(x, y).over(over_ms, easing)

        if callback is not None:
            builder = builder.then(callback)
        return builder

    def mouse_rig_move(
            direction: str,
            amount: float = 1,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None,
            api: str = None
        ) -> None:
        """Move mouse in a direction by amount.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            amount: Distance in pixels (default: 1)
            over_ms: Duration in ms (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
            callback: Function to call when movement completes (optional)
            api: Mouse API to use, e.g. "talon" or "platform" (optional)
        """
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        builder = rig.pos.by(x * amount, y * amount)

        if api is not None:
            builder = builder.api(api)
        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        if callback is not None:
            builder = builder.then(callback)
        return builder

    def mouse_rig_move_natural(
            direction: str,
            amount: float = 1,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None,
            api: str = None
        ) -> None:
        """Move mouse in a direction with smooth easing.
        Defaults from mouse_rig_natural_move_ms and mouse_rig_natural_move_easing settings.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            amount: Distance in pixels (default: 1)
            over_ms: Duration in ms (default: from settings)
            easing: Easing function (default: from settings)
            callback: Function to call when movement completes (optional)
            api: Mouse API to use, e.g. "talon" or "platform" (optional)
        """
        if over_ms is None:
            over_ms = settings.get("user.mouse_rig_natural_move_ms")
        if easing is None:
            easing = settings.get("user.mouse_rig_natural_move_easing")
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        builder = rig.pos.by(x * amount, y * amount).over(over_ms, easing)

        if api is not None:
            builder = builder.api(api)
        if callback is not None:
            builder = builder.then(callback)
        return builder

    def mouse_rig_move_value(
            value: int | float,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None,
            api: str = None
        ) -> None:
        """Move mouse by value in current direction, optionally over time.

        Args:
            value: Distance to move in pixels along current direction
            over_ms: Duration in ms (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
            callback: Function to call when movement completes (optional)
            api: Mouse API to use, e.g. "talon" or "platform" (optional)
        """
        rig = actions.user.mouse_rig()
        dx = rig.state.direction.x * value
        dy = rig.state.direction.y * value
        builder = rig.pos.by(dx, dy)

        if api is not None:
            builder = builder.api(api)
        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        if callback is not None:
            builder = builder.then(callback)
        return builder

    def mouse_rig_speed_to(
            value: float | int,
            over_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Set speed to absolute value, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.speed.to(value).over(over_ms).hold(hold_ms).revert(revert_ms)
        ```

        Examples:
        ```python
        mouse_rig_speed_to(10) # instant set
        mouse_rig_speed_to(10, 1000) # speed to 10 over 1s and stay
        mouse_rig_speed_to(10, 1000, 0, 1000) # speed to 10 over 1s and revert over 1s
        mouse_rig_speed_to(10, 0, 1000, 0) # speed set instantly, hold for 1s and revert instantly
        mouse_rig_speed_to(10, 0, 0, 1000) # speed to 10 instantly, then revert over 1s
        ```
        """
        rig = actions.user.mouse_rig()
        builder = rig.speed.to(value)

        if over_ms:
            builder = builder.over(over_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)
        return builder

    def mouse_rig_speed_add(
            value: float | int,
            over_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Add to current speed, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.speed.add(value).over(over_ms).hold(hold_ms).revert(revert_ms)
        ```

        Examples:
        ```python
        mouse_rig_speed_add(10) # instant add
        mouse_rig_speed_add(10, 1000) # add 10 over 1s and stay
        mouse_rig_speed_add(10, 1000, 0, 1000) # add 10 over 1s and revert over 1s
        mouse_rig_speed_add(10, 0, 1000, 0) # add instantly, hold for 1s and revert instantly
        mouse_rig_speed_add(10, 0, 0, 1000) # add instantly, then revert over 1s
        ```
        """
        rig = actions.user.mouse_rig()
        builder = rig.speed.add(value)

        if over_ms:
            builder = builder.over(over_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)
        return builder

    def mouse_rig_speed_mul(
            value: float | int,
            over_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Multiply current speed, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.speed.mul(value).over(over_ms).hold(hold_ms).revert(revert_ms)
        ```

        Examples:
        ```python
        mouse_rig_speed_mul(2) # instant multiply
        mouse_rig_speed_mul(2, 1000) # multiply over 1s and stay
        mouse_rig_speed_mul(2, 1000, 0, 1000) # multiply over 1s and revert over 1s
        mouse_rig_speed_mul(2, 0, 1000, 0) # multiply instantly, hold for 1s and revert instantly
        mouse_rig_speed_mul(2, 0, 0, 1000) # multiply instantly, then revert over 1s
        ```
        """
        rig = actions.user.mouse_rig()
        builder = rig.speed.mul(value)

        if over_ms:
            builder = builder.over(over_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)
        return builder

    def mouse_rig_direction(
            direction: str,
            over_ms: int = None,
            easing: str = None
        ) -> None:
        """Set direction to a cardinal direction, optionally curve over time.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        builder = rig.direction.to(x, y)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        return builder

    def mouse_rig_rotate(
            degrees: int | float,
            over_ms: int = None,
            easing: str = None
        ) -> None:
        """Rotate direction by degrees, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.by(degrees).over(over_ms, easing)
        ```

        Args:
            degrees: Degrees to rotate (positive = clockwise)
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.direction.queue.by(degrees)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        return builder

    def mouse_rig_reverse(reverse_ms: int = None) -> None:
        """Reverse the current direction, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.reverse(reverse_ms)
        ```

        Args:
            reverse_ms: Time in ms to curve to the reversed direction (optional)
        """
        rig = actions.user.mouse_rig()
        if reverse_ms is not None:
            return rig.reverse(reverse_ms)
        else:
            return rig.reverse()

    def mouse_rig_go(direction: str, speed: float = 5, force: bool = False) -> None:
        """Set direction and start moving. Keeps current speed unless force=True.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            speed: Speed value. Only applied if stopped (or force=True).
            force: If True, always set speed. If False, only set speed when starting from stopped.
        """
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        rig.direction(x, y)
        if force or not rig.state.speed:
            rig.speed(speed)

    def mouse_rig_go_natural(direction: str, speed: float = 5, force: bool = False, scale: float = 1.0) -> None:
        """Like go() but with smooth turns and gradual speed changes.
        Turn timing scales with current speed (faster = smoother turns).
        Easing controlled by settings, timing scaled by `scale`.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            speed: Speed value. Only applied if stopped (or force=True).
            force: If True, always set speed. If False, only set speed when starting from stopped.
            scale: Multiplier for all natural timing (0.5 = snappier, 2.0 = smoother).
        """
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        base_turn_ms = settings.get("user.mouse_rig_natural_turn_ms")
        turn_easing = settings.get("user.mouse_rig_natural_turn_easing")
        speed_ms = int(settings.get("user.mouse_rig_natural_speed_ms") * scale)
        speed_easing = settings.get("user.mouse_rig_natural_speed_easing")

        if not rig.state.speed:
            # From stopped: snap direction, then ramp speed
            rig.direction(x, y)
            rig.speed.to(speed).over(speed_ms, speed_easing)
        else:
            # Already moving: smooth turn
            speed_factor = max(1.0, rig.state.speed / 3.0)
            turn_ms = int(base_turn_ms * scale * speed_factor)
            rig.direction.to(x, y).over(turn_ms, turn_easing)
            if force:
                rig.speed.to(speed).over(speed_ms, speed_easing)

    def mouse_rig_boost(amount: float, over_ms: int = 500, hold_ms: int = 0, release_ms: int = 500, stacks: int = 0) -> None:
        """One-shot speed boost: ramp up, hold, release.
        Uses the implicit speed.offset layer.

        Args:
            amount: Speed to add.
            over_ms: Time to ramp up to full amount.
            hold_ms: Time to hold at full amount before releasing.
            release_ms: Time to decay back to 0.
            stacks: Max concurrent boosts. 0 = unlimited.
        """
        rig = actions.user.mouse_rig()
        return rig.speed.offset.add(amount).over(over_ms).hold(hold_ms).revert(release_ms).stack(stacks)

    def mouse_rig_boost_start(amount: float, over_ms: int = 500) -> None:
        """Start a sustained boost. Ramps up and holds until boost_stop is called.
        Safe for held-input patterns (noise/pedal) — repeated calls are no-ops (.stack(1)).

        Args:
            amount: Speed to add.
            over_ms: Time to ramp up to full amount.
        """
        rig = actions.user.mouse_rig()
        return rig.speed.offset.add(amount).over(over_ms).stack(1)

    def mouse_rig_boost_stop(release_ms: int = 500) -> None:
        """Stop a sustained boost. Reverts the speed.offset layer back to 0.

        Args:
            release_ms: Time to decay back to 0.
        """
        rig = actions.user.mouse_rig()
        return rig.speed.offset.revert(release_ms)

    def mouse_rig_state_speed() -> float:
        """Get current speed from rig state"""
        rig = actions.user.mouse_rig()
        return rig.state.speed

    def mouse_rig_state_direction() -> tuple:
        """Get current direction (x, y) from rig state"""
        rig = actions.user.mouse_rig()
        return (rig.state.direction.x, rig.state.direction.y)

    def mouse_rig_state_direction_x() -> float:
        """Get current direction x component from rig state"""
        rig = actions.user.mouse_rig()
        return rig.state.direction.x

    def mouse_rig_state_direction_y() -> float:
        """Get current direction y component from rig state"""
        rig = actions.user.mouse_rig()
        return rig.state.direction.y

    def mouse_rig_state_is_moving() -> bool:
        """Check if mouse is currently moving (speed > 0)"""
        rig = actions.user.mouse_rig()
        return rig.state.speed > 0

    def mouse_rig_state_is_scrolling() -> bool:
        """Check if mouse is currently scrolling (scroll speed > 0)"""
        rig = actions.user.mouse_rig()
        return rig.state.scroll_speed > 0

    def mouse_rig_state_direction_cardinal() -> str:
        """Get current direction as cardinal string.

        Returns: "right", "left", "up", "down", "up_right", "up_left",
                 "down_right", "down_left", or None if no direction
        """
        rig = actions.user.mouse_rig()
        cardinal = rig.state.direction_cardinal
        return str(cardinal) if cardinal.current else None

    def mouse_rig_stop(stop_ms: float = None, easing: str = None, callback: callable = None) -> None:
        """Stop the mouse rig and remove all layers, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.stop(ms, easing).then(callback)
        ```

        Args:
            ms: Time in ms to decelerate to stop
            easing: Easing function - "linear", "ease_in_out", etc.
            callback: Function to call when system fully stops
        """
        rig = actions.user.mouse_rig()
        if easing is not None:
            handle = rig.stop(stop_ms, easing)
        else:
            handle = rig.stop(stop_ms)

        if callback is not None:
            handle.then(callback)
        return handle

    def mouse_rig_reload() -> None:
        """Reload/reset rig. Useful for development"""
        reload_rig()

    def mouse_rig_reset() -> None:
        """Reset rig to default state (speed=0, direction=right, clear all layers)"""
        rig = actions.user.mouse_rig()
        rig.reset()

    def mouse_rig_button_prime(button: str) -> None:
        """Prime a mouse button to press on next rig action and release on stop.

        The button is held down when the next builder starts and released when
        the frame loop stops (movement completes or stop() is called).

        Args:
            button: "left", "right", or "middle"
        """
        rig = actions.user.mouse_rig()
        rig.state.button_prime(BUTTON_MAP[button])

    def mouse_rig_sequence(steps: list) -> None:
        """Run a sequence of steps, waiting for rig animations between steps.

        Each step is a callable (lambda/function). If a step returns a RigBuilder
        with an async lifecycle (.over/.hold/.revert), the sequence waits for its
        animation to complete before running the next step. Otherwise continues
        immediately.

        Example:
        ```python
        actions.user.mouse_rig_sequence([
            lambda: ctrl.mouse_click(0, down=True),
            lambda: actions.user.mouse_rig_pos_to(500, 300, 500),
            lambda: ctrl.mouse_click(0, up=True),
        ])
        ```
        """
        run_sequence(steps)

    def mouse_rig_wait(ms: float) -> Any:
        """For use with `user.mouse_rig_sequence`

        Example:
        ```python
        actions.user.mouse_rig_sequence([
            lambda: actions.user.mouse_rig_go("right", 3),
            lambda: actions.user.mouse_rig_wait(1000),
            lambda: actions.user.mouse_rig_stop(),
        ])
        ```

        Args:
            ms: Duration to wait in milliseconds
        """
        return WaitHandle(ms)

    def mouse_rig_test_toggle_ui():
        """Show the QA UI for mouse rig development"""
        from .tests.main import toggle_test_ui
        toggle_test_ui()

    # Scroll actions
    def mouse_rig_scroll_stop(stop_ms: float = None, easing: str = None, callback: callable = None) -> None:
        """Stop scrolling, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.stop(stop_ms, easing).then(callback)
        ```

        Args:
            stop_ms: Time in ms to decelerate to stop
            easing: Easing function - "linear", "ease_in_out", etc.
            callback: Function to call when scroll fully stops
        """
        rig = actions.user.mouse_rig()
        handle = rig.scroll.stop(stop_ms, easing)

        if callback is not None:
            handle.then(callback)
        return handle

    def mouse_rig_scroll(
            direction: str,
            amount: float = 1,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """One-time scroll in a direction (like scroll wheel ticks).
        Uses native platform API. 1 amount = 1 physical scroll tick.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            amount: Number of scroll ticks (default: 1)
            over_ms: Duration in ms to spread scroll over (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
            callback: Function to call when complete (optional)
        """
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        builder = rig.scroll.by(x * amount, y * amount)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        if callback is not None:
            builder = builder.then(callback)
        return builder

    def mouse_rig_scroll_natural(
            direction: str,
            amount: float = 1,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """One-time smooth scroll in a direction using native platform API.
        Defaults from mouse_rig_natural_scroll_ms and mouse_rig_natural_scroll_easing settings.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            amount: Number of scroll ticks (default: 1)
            over_ms: Duration in ms (default: from settings)
            easing: Easing function (default: from settings)
            callback: Function to call when complete (optional)
        """
        if over_ms is None:
            over_ms = settings.get("user.mouse_rig_natural_scroll_ms")
        if easing is None:
            easing = settings.get("user.mouse_rig_natural_scroll_easing")
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        builder = rig.scroll.by_pixels.by(x * amount, y * amount).over(over_ms, easing)

        if callback is not None:
            builder = builder.then(callback)
        return builder

    def mouse_rig_scroll_speed_to(
            value: float | int,
            over_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Set scroll speed to absolute value, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.speed.to(value).over(over_ms).hold(hold_ms).revert(revert_ms)
        ```

        Args:
            value: Target scroll speed
            over_ms: Duration to reach target speed (optional)
            hold_ms: Duration to hold at target speed (optional)
            revert_ms: Duration to revert to previous speed (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.scroll.speed.to(value)

        if over_ms:
            builder = builder.over(over_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)
        return builder

    def mouse_rig_scroll_speed_add(
            value: float | int,
            over_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Add to current scroll speed, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.speed.add(value).over(over_ms).hold(hold_ms).revert(revert_ms)
        ```

        Args:
            value: Amount to add to scroll speed
            over_ms: Duration to add speed (optional)
            hold_ms: Duration to hold at new speed (optional)
            revert_ms: Duration to revert to previous speed (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.scroll.speed.add(value)

        if over_ms:
            builder = builder.over(over_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)
        return builder

    def mouse_rig_scroll_speed_mul(
            value: float | int,
            over_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Multiply current scroll speed, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.speed.mul(value).over(over_ms).hold(hold_ms).revert(revert_ms)
        ```

        Args:
            value: Multiplier for scroll speed
            over_ms: Duration to multiply speed (optional)
            hold_ms: Duration to hold at new speed (optional)
            revert_ms: Duration to revert to previous speed (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.scroll.speed.mul(value)

        if over_ms:
            builder = builder.over(over_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)
        return builder

    def mouse_rig_scroll_direction(
            direction: str,
            over_ms: int = None,
            easing: str = None
        ) -> None:
        """Set scroll direction to a cardinal direction, optionally curve over time.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        builder = rig.scroll.direction.to(x, y)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        return builder

    def mouse_rig_scroll_direction_by(
            degrees: int | float,
            over_ms: int = None,
            easing: str = None
        ) -> None:
        """Rotate scroll direction by degrees, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.direction.by(degrees).over(over_ms, easing)
        ```

        Args:
            degrees: Degrees to rotate (positive = clockwise)
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.scroll.direction.by(degrees)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        return builder

    def mouse_rig_scroll_go(direction: str, speed: float = 5, force: bool = False) -> None:
        """Set scroll direction and start scrolling. Same semantics as mouse_rig_go.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            speed: Speed value. Only applied if stopped (or force=True).
            force: If True, always set speed. If False, only set speed when starting from stopped.
        """
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        rig.scroll.direction(x, y)
        if force or not rig.state.scroll_speed:
            rig.scroll.speed(speed)

    def mouse_rig_scroll_go_natural(direction: str, speed: float = 5, force: bool = False, scale: float = 1.0) -> None:
        """Like scroll_go() but with smooth transitions. Same semantics as mouse_rig_go_natural.

        Args:
            direction: "left", "right", "up", "down", "up_left", "up_right", "down_left", "down_right"
            speed: Speed value. Only applied if stopped (or force=True).
            force: If True, always set speed. If False, only set speed when starting from stopped.
            scale: Multiplier for all natural timing (0.5 = snappier, 2.0 = smoother).
        """
        rig = actions.user.mouse_rig()
        x, y = _parse_direction(direction)
        base_turn_ms = settings.get("user.mouse_rig_natural_turn_ms")
        turn_easing = settings.get("user.mouse_rig_natural_turn_easing")
        speed_ms = int(settings.get("user.mouse_rig_natural_speed_ms") * scale)
        speed_easing = settings.get("user.mouse_rig_natural_speed_easing")

        if not rig.state.scroll_speed:
            # From stopped: snap direction, then ramp speed
            rig.scroll.direction(x, y)
            rig.scroll.speed.to(speed).over(speed_ms, speed_easing)
        else:
            # Already scrolling: smooth turn
            speed_factor = max(1.0, rig.state.scroll_speed / 3.0)
            turn_ms = int(base_turn_ms * scale * speed_factor)
            rig.scroll.direction.to(x, y).over(turn_ms, turn_easing)
            if force:
                rig.scroll.speed.to(speed).over(speed_ms, speed_easing)

    def mouse_rig_scroll_boost(amount: float, over_ms: int = 500, hold_ms: int = 0, release_ms: int = 500, stacks: int = 0) -> None:
        """One-shot scroll speed boost: ramp up, hold, release.
        Uses the implicit scroll speed.offset layer.

        Args:
            amount: Scroll speed to add.
            over_ms: Time to ramp up to full amount.
            hold_ms: Time to hold at full amount before releasing.
            release_ms: Time to decay back to 0.
            stacks: Max concurrent boosts. 0 = unlimited.
        """
        rig = actions.user.mouse_rig()
        return rig.scroll.speed.offset.add(amount).over(over_ms).hold(hold_ms).revert(release_ms).stack(stacks)

    def mouse_rig_scroll_boost_start(amount: float, over_ms: int = 500) -> None:
        """Start a sustained scroll boost. Ramps up and holds until scroll_boost_stop is called.
        Safe for held-input patterns (noise/pedal) — repeated calls are no-ops (.stack(1)).

        Args:
            amount: Scroll speed to add.
            over_ms: Time to ramp up to full amount.
        """
        rig = actions.user.mouse_rig()
        return rig.scroll.speed.offset.add(amount).over(over_ms).stack(1)

    def mouse_rig_scroll_boost_stop(release_ms: int = 500) -> None:
        """Stop a sustained scroll boost. Reverts the scroll speed.offset layer back to 0.

        Args:
            release_ms: Time to decay back to 0.
        """
        rig = actions.user.mouse_rig()
        return rig.scroll.speed.offset.revert(release_ms)
