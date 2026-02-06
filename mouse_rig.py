from talon import actions, Module
from typing import Any
from .src import rig as get_rig, reload_rig

mod = Module()

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

    def mouse_rig_pos_by(
            dx: float,
            dy: float,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None,
            api: str = None
        ) -> None:
        """Move mouse by relative offset, optionally over time. Uses platform api by default.
        If you need screen coordinates precision, use "talon" api instead.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.pos.by(dx, dy).api(api).over(over_ms, easing).then(callback)
        ```

        Args:
            dx: Relative x offset
            dy: Relative y offset
            over_ms: Duration in ms (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
            callback: Function to call when movement completes (optional)
            api: Mouse API to use, e.g. "talon" or "platform" (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.pos.by(dx, dy)

        if api is not None:
            builder = builder.api(api)
        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        if callback is not None:
            builder = builder.then(callback)

    def mouse_rig_pos_by_value(
            value: int | float,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None,
            api: str = None
        ) -> None:
        """Move mouse by value in current direction, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        dx = rig.state.direction.x * value
        dy = rig.state.direction.y * value
        rig.pos.by(dx, dy).api(api).over(over_ms, easing).then(callback)
        ```

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

    def mouse_rig_direction_to(
            x: int | float,
            y: int | float,
            over_ms: int = None,
            easing: str = None
        ) -> None:
        """Set direction to absolute vector, optionally curve over time.

        mouse_rig_direction_to(1, 0)  # right
        mouse_rig_direction_to(-1, 0) # left
        mouse_rig_direction_to(0, -1) # up
        mouse_rig_direction_to(0, 1)  # down

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(x, y).over(ms, easing)
        ```

        Args:
            x: X direction component (-1.0 to 1.0, where -1=left, 1=right)
            y: Y direction component (-1.0 to 1.0, where -1=up, 1=down)
            ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.direction.to(x, y)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)

    def mouse_rig_direction_by(
            degrees: int | float,
            over_ms: int = None,
            easing: str = None
        ) -> None:
        """Rotate direction by degrees, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.by(degrees).over(ms, easing)
        ```

        Args:
            degrees: Degrees to rotate (positive = clockwise)
            ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.direction.by(degrees)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)

    def mouse_rig_direction_left(over_ms: int = None, easing: str = None) -> None:
        """Set direction to left, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(-1, 0).over(over_ms, easing)
        ```

        Args:
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_direction_to(-1, 0, over_ms, easing)

    def mouse_rig_direction_right(over_ms: int = None, easing: str = None) -> None:
        """Set direction to right, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(1, 0).over(over_ms, easing)
        ```

        Args:
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_direction_to(1, 0, over_ms, easing)

    def mouse_rig_direction_up(over_ms: int = None, easing: str = None) -> None:
        """Set direction to up, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(0, -1).over(over_ms, easing)
        ```

        Args:
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_direction_to(0, -1, over_ms, easing)

    def mouse_rig_direction_down(over_ms: int = None, easing: str = None) -> None:
        """Set direction to down, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(0, 1).over(over_ms, easing)
        ```

        Args:
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_direction_to(0, 1, over_ms, easing)

    def mouse_rig_reverse(reverse_ms: int = None) -> None:
        """Reverse the current direction, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.reverse(reverse_ms)
        ```

        Args:
            over_ms: Time in ms to curve to the reversed direction (optional)
        """
        rig = actions.user.mouse_rig()
        if reverse_ms is not None:
            rig.reverse(reverse_ms)
        else:
            rig.reverse()

    def mouse_rig_go_direction(
            x: float,
            y: float,
            initial_speed: int | float = 5,
            initial_ms: int = None,
            initial_easing: str = None
        ) -> None:
        """Set direction and start moving if stopped. Respects current speed if already moving.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction(x, y)
        if not rig.state.speed:
            rig.speed.to(initial_speed).over(initial_ms, initial_easing)
        ```

        Args:
            x: Horizontal direction (-1 for left, 1 for right)
            y: Vertical direction (-1 for up, 1 for down)
            initial_speed: Speed to use if mouse isn't already moving
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        rig = actions.user.mouse_rig()
        rig.direction(x, y)

        if not rig.state.speed:
            if initial_ms is not None:
                rig.speed.to(initial_speed).over(initial_ms, initial_easing)
            else:
                rig.speed(initial_speed)

    def mouse_rig_go_left(initial_speed: int | float = 5, initial_ms: int = None, initial_easing: str = None) -> None:
        """Move left, setting direction and starting speed if stopped.

        Args:
            initial_speed: Speed to use if mouse isn't already moving
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        actions.user.mouse_rig_go_direction(-1, 0, initial_speed, initial_ms, initial_easing)

    def mouse_rig_go_right(initial_speed: int | float = 5, initial_ms: int = None, initial_easing: str = None) -> None:
        """Move right, setting direction and starting speed if stopped.

        Args:
            initial_speed: Speed to use if mouse isn't already moving
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        actions.user.mouse_rig_go_direction(1, 0, initial_speed, initial_ms, initial_easing)

    def mouse_rig_go_up(initial_speed: int | float = 5, initial_ms: int = None, initial_easing: str = None) -> None:
        """Move up, setting direction and starting speed if stopped.

        Args:
            initial_speed: Speed to use if mouse isn't already moving
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        actions.user.mouse_rig_go_direction(0, -1, initial_speed, initial_ms, initial_easing)

    def mouse_rig_go_down(initial_speed: int | float = 5, initial_ms: int = None, initial_easing: str = None) -> None:
        """Move down, setting direction and starting speed if stopped.

        Args:
            initial_speed: Speed to use if mouse isn't already moving
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        actions.user.mouse_rig_go_direction(0, 1, initial_speed, initial_ms, initial_easing)

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

    def mouse_rig_state_pos() -> tuple:
        """Get current position (x, y) from rig state - may be incorrect due to platform based movement"""
        rig = actions.user.mouse_rig()
        return (rig.state.pos.x, rig.state.pos.y)

    def mouse_rig_state_is_moving() -> bool:
        """Check if mouse is currently moving (speed > 0)"""
        rig = actions.user.mouse_rig()
        return rig.state.speed > 0

    def mouse_rig_state_direction_cardinal() -> str:
        """Get current direction as cardinal string.

        Returns: "right", "left", "up", "down", "up_right", "up_left",
                 "down_right", "down_left", or None if no direction
        """
        rig = actions.user.mouse_rig()
        cardinal = rig.state.direction_cardinal
        # Auto-converts to string via __str__, or returns the .current directly
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

    def mouse_rig_reload() -> None:
        """Reload/reset rig. Useful for development"""
        reload_rig()

    def mouse_rig_reset() -> None:
        """Reset rig to default state (speed=0, direction=right, clear all layers)"""
        rig = actions.user.mouse_rig()
        rig.reset()

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

    def mouse_rig_scroll_by(
            dx: float,
            dy: float,
            over_ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """One-time scroll by delta amount (like scroll wheel).

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.by(dx, dy).over(over_ms, easing).then(callback)
        ```

        Args:
            dx: Horizontal scroll amount (positive = right, negative = left)
            dy: Vertical scroll amount (positive = down, negative = up)
            over_ms: Duration in ms to spread scroll over (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
            callback: Function to call when complete (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.scroll.by(dx, dy)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)
        if callback is not None:
            builder = builder.then(callback)

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

    def mouse_rig_scroll_direction_to(
            x: int | float,
            y: int | float,
            over_ms: int = None,
            easing: str = None
        ) -> None:
        """Set scroll direction to absolute vector, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.direction.to(x, y).over(over_ms, easing)
        ```

        Args:
            x: X direction component (-1.0 to 1.0)
            y: Y direction component (-1.0 to 1.0)
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.scroll.direction.to(x, y)

        if over_ms is not None:
            builder = builder.over(over_ms, easing)

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

    def mouse_rig_scroll_direction_left(over_ms: int = None, easing: str = None) -> None:
        """Set scroll direction to left, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.direction.to(-1, 0).over(over_ms, easing)
        ```

        Args:
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_scroll_direction_to(-1, 0, over_ms, easing)

    def mouse_rig_scroll_direction_right(over_ms: int = None, easing: str = None) -> None:
        """Set scroll direction to right, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.direction.to(1, 0).over(over_ms, easing)
        ```

        Args:
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_scroll_direction_to(1, 0, over_ms, easing)

    def mouse_rig_scroll_direction_up(over_ms: int = None, easing: str = None) -> None:
        """Set scroll direction to up, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.direction.to(0, -1).over(over_ms, easing)
        ```

        Args:
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_scroll_direction_to(0, -1, over_ms, easing)

    def mouse_rig_scroll_direction_down(over_ms: int = None, easing: str = None) -> None:
        """Set scroll direction to down, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.direction.to(0, 1).over(over_ms, easing)
        ```

        Args:
            over_ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_scroll_direction_to(0, 1, over_ms, easing)

    def mouse_rig_scroll_go_direction(
            x: float,
            y: float,
            initial_speed: int | float = 5,
            initial_ms: int = None,
            initial_easing: str = None
        ) -> None:
        """Set scroll direction and start scrolling if stopped. Respects current speed if already scrolling.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.scroll.direction(x, y)
        if not rig.state.scroll_speed:
            rig.scroll.speed.to(initial_speed).over(initial_ms, initial_easing)
        ```

        Args:
            x: Horizontal direction (-1 for left, 1 for right)
            y: Vertical direction (-1 for up, 1 for down)
            initial_speed: Speed to use if not already scrolling
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        rig = actions.user.mouse_rig()
        rig.scroll.direction(x, y)

        if not rig.state.scroll_speed:
            if initial_ms is not None:
                rig.scroll.speed.to(initial_speed).over(initial_ms, initial_easing)
            else:
                rig.scroll.speed(initial_speed)

    def mouse_rig_scroll_go_left(initial_speed: int | float = 5, initial_ms: int = None, initial_easing: str = None) -> None:
        """Scroll left, setting direction and starting speed if not scrolling.

        Args:
            initial_speed: Speed to use if not already scrolling
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        actions.user.mouse_rig_scroll_go_direction(-1, 0, initial_speed, initial_ms, initial_easing)

    def mouse_rig_scroll_go_right(initial_speed: int | float = 5, initial_ms: int = None, initial_easing: str = None) -> None:
        """Scroll right, setting direction and starting speed if not scrolling.

        Args:
            initial_speed: Speed to use if not already scrolling
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        actions.user.mouse_rig_scroll_go_direction(1, 0, initial_speed, initial_ms, initial_easing)

    def mouse_rig_scroll_go_up(initial_speed: int | float = 5, initial_ms: int = None, initial_easing: str = None) -> None:
        """Scroll up, setting direction and starting speed if not scrolling.

        Args:
            initial_speed: Speed to use if not already scrolling
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        actions.user.mouse_rig_scroll_go_direction(0, -1, initial_speed, initial_ms, initial_easing)

    def mouse_rig_scroll_go_down(initial_speed: int | float = 5, initial_ms: int = None, initial_easing: str = None) -> None:
        """Scroll down, setting direction and starting speed if not scrolling.

        Args:
            initial_speed: Speed to use if not already scrolling
            initial_ms: Duration to ramp up to initial_speed (optional)
            initial_easing: Easing function for ramp up (optional)
        """
        actions.user.mouse_rig_scroll_go_direction(0, 1, initial_speed, initial_ms, initial_easing)