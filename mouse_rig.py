from talon import settings, actions, ctrl, actions, cron
from typing import Any
from .settings import mod
from .src import rig as get_rig, reload_rig
from .src.mouse_api import MOUSE_APIS

@mod.action_class
class Actions:
    def mouse_rig() -> Any:
        """
        Get mouse rig directly for advanced usage.

        ```python
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.direction.to(1, 0)
        rig.direction.by(90).over(100)
        rig.speed(5)
        rig.speed.to(5)
        rig.speed.add(2)
        rig.pos.to(500, 300).over(200, easing="ease_in_out")
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
            ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """Move mouse to absolute position, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.pos.to(x, y).over(ms, easing).then(callback)
        ```

        Args:
            x: Target x coordinate
            y: Target y coordinate
            ms: Duration in ms (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
            callback: Function to call when movement completes (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.pos.to(x, y)

        if ms is not None:
            builder = builder.over(ms, easing)
        if callback is not None:
            builder = builder.then(callback)

    def mouse_rig_pos_by(
            dx: float,
            dy: float,
            ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """Move mouse by relative offset, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.pos.by(dx, dy).over(ms, easing).then(callback)
        ```

        Args:
            dx: Relative x offset
            dy: Relative y offset
            ms: Duration in ms (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
            callback: Function to call when movement completes (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.pos.by(dx, dy)

        if ms is not None:
            builder = builder.over(ms, easing)
        if callback is not None:
            builder = builder.then(callback)

    def mouse_rig_speed_to(
            speed: float | int,
            to_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Set speed to absolute value, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.speed.to(speed).over(to_ms).hold(hold_ms).revert(revert_ms)
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
        builder = rig.speed.to(speed)

        if to_ms:
            builder = builder.over(to_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)

    def mouse_rig_speed_add(
            delta: float | int,
            to_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Add to current speed, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.speed.add(delta).over(to_ms).hold(hold_ms).revert(revert_ms)
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
        builder = rig.speed.add(delta)

        if to_ms:
            builder = builder.over(to_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)

    def mouse_rig_speed_mul(
            multiplier: float | int,
            to_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Multiply current speed, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.speed.mul(multiplier).over(to_ms).hold(hold_ms).revert(revert_ms)
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
        builder = rig.speed.mul(multiplier)

        if to_ms:
            builder = builder.over(to_ms)
        if hold_ms:
            builder = builder.hold(hold_ms)
        if revert_ms:
            builder = builder.revert(revert_ms)

    def mouse_rig_direction_to(
            direction_x: float,
            direction_y: float,
            ms: int = None,
            easing: str = None
        ) -> None:
        """Set direction to absolute vector, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(direction_x, direction_y).over(ms, easing)
        ```

        Args:
            direction_x: X direction component (-1.0 to 1.0, where -1=left, 1=right)
            direction_y: Y direction component (-1.0 to 1.0, where -1=up, 1=down)
            ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        rig = actions.user.mouse_rig()
        builder = rig.direction.to(direction_x, direction_y)

        if ms is not None:
            builder = builder.over(ms, easing)

    def mouse_rig_direction_by(
            degrees: float,
            ms: int = None,
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

        if ms is not None:
            builder = builder.over(ms, easing)

    def mouse_rig_direction_left(ms: int = None, easing: str = None) -> None:
        """Set direction to left, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(-1, 0).over(ms, easing)
        ```

        Args:
            ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_direction_to(-1, 0, ms, easing)

    def mouse_rig_direction_right(ms: int = None, easing: str = None) -> None:
        """Set direction to right, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(1, 0).over(ms, easing)
        ```

        Args:
            ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_direction_to(1, 0, ms, easing)

    def mouse_rig_direction_up(ms: int = None, easing: str = None) -> None:
        """Set direction to up, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(0, -1).over(ms, easing)
        ```

        Args:
            ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_direction_to(0, -1, ms, easing)

    def mouse_rig_direction_down(ms: int = None, easing: str = None) -> None:
        """Set direction to down, optionally curve over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction.to(0, 1).over(ms, easing)
        ```

        Args:
            ms: Time in ms to curve to the new direction (optional)
            easing: Easing function like "linear", "ease_in_out" (optional)
        """
        actions.user.mouse_rig_direction_to(0, 1, ms, easing)

    def mouse_rig_go_direction(
            x: float,
            y: float,
            initial_speed: int = 3,
            target_speed: int = None,
            ms: int = None,
            easing: str = None
        ) -> None:
        """Set direction and speed to move in specified direction.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction(x, y)
        if not rig.state.speed:
            rig.speed(initial_speed)
        if target_speed is not None:
            rig.speed.to(target_speed).over(ms, easing)
        ```

        Args:
            x: Horizontal direction (-1 for left, 1 for right)
            y: Vertical direction (-1 for up, 1 for down)
            initial_speed: Speed to use if mouse isn't already moving
            target_speed: Target speed to transition to
            ms: Duration in ms for speed transition
            easing: "linear", "ease_in", "ease_out", "ease_in_out", or add number at end for power curve e.g. "ease_in_out2"
        """
        rig = actions.user.mouse_rig()
        rig.direction(x, y)

        if not rig.state.speed:
            rig.speed(initial_speed)
        if target_speed is not None and ms is not None and rig.state.speed != target_speed:
            rig.speed.to(target_speed).over(ms, easing)

    def mouse_rig_go_left(initial_speed: int = 3, target_speed: int = None, ms: int = None, easing: str = None) -> None:
        """Set direction and speed to move left.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        if not rig.state.speed:
            rig.speed(initial_speed)
        if target_speed is not None:
            rig.speed.to(target_speed).over(ms, easing)
        ```

        Args:
            initial_speed: Speed to use if mouse isn't already moving
            target_speed: Target speed to transition to
            ms: Duration in ms for speed transition
            easing: "linear", "ease_in", "ease_out", "ease_in_out", or add number at end for power curve e.g. "ease_in_out2"
        """
        actions.user.mouse_rig_go_direction(-1, 0, initial_speed, target_speed, ms, easing)

    def mouse_rig_go_right(initial_speed: int = 3, target_speed: int = None, ms: int = None, easing: str = None) -> None:
        """Set direction and speed to move right.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        if not rig.state.speed:
            rig.speed(initial_speed)
        if target_speed is not None:
            rig.speed.to(target_speed).over(ms, easing)
        ```

        Args:
            initial_speed: Speed to use if mouse isn't already moving
            target_speed: Target speed to transition to
            ms: Duration in ms for speed transition
            easing: "linear", "ease_in", "ease_out", "ease_in_out", or add number at end for power curve e.g. "ease_in_out2"
        """
        actions.user.mouse_rig_go_direction(1, 0, initial_speed, target_speed, ms, easing)

    def mouse_rig_go_up(initial_speed: int = 3, target_speed: int = None, ms: int = None, easing: str = None) -> None:
        """Set direction and speed to move up.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction(0, -1)
        if not rig.state.speed:
            rig.speed(initial_speed)
        if target_speed is not None:
            rig.speed.to(target_speed).over(ms, easing)
        ```

        Args:
            initial_speed: Speed to use if mouse isn't already moving
            target_speed: Target speed to transition to
            ms: Duration in ms for speed transition
            easing: "linear", "ease_in", "ease_out", "ease_in_out", or add number at end for power curve e.g. "ease_in_out2"
        """
        actions.user.mouse_rig_go_direction(0, -1, initial_speed, target_speed, ms, easing)

    def mouse_rig_go_down(initial_speed: int = 3, target_speed: int = None, ms: int = None, easing: str = None) -> None:
        """Set direction and speed to move down.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)
        if not rig.state.speed:
            rig.speed(initial_speed)
        if target_speed is not None:
            rig.speed.to(target_speed).over(ms, easing)
        ```

        Args:
            initial_speed: Speed to use if mouse isn't already moving
            target_speed: Target speed to transition to
            ms: Duration in ms for speed transition
            easing: "linear", "ease_in", "ease_out", "ease_in_out", or add number at end for power curve e.g. "ease_in_out2"
        """
        actions.user.mouse_rig_go_direction(0, 1, initial_speed, target_speed, ms, easing)

    def mouse_rig_layer_speed_offset_by(
            layer_name: str,
            delta: float | int,
            to_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Create a named speed layer that offsets the base speed.
        Multiple invocations stack and the layer can be reverted by name.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.layer(layer_name).speed.offset.by(delta).over(to_ms).hold(hold_ms).revert(revert_ms)
        ```

        Examples:
        ```python
        mouse_rig_layer_speed_offset_by("boost", 5)                 # instant add
        mouse_rig_layer_speed_offset_by("boost", 5, 1000)           # add over 1s, stay
        mouse_rig_layer_speed_offset_by("boost", 5, 1000, 0, 1000)  # add 1s, revert 1s
        mouse_rig_layer_speed_offset_by("boost", 5, 0, 500, 0)      # instant, hold 500ms, revert
        ```
        """
        rig = actions.user.mouse_rig()
        builder = rig.layer(layer_name).speed.offset.by(delta)
        if to_ms is not None:
            builder = builder.over(to_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder = builder.revert(revert_ms)

    def mouse_rig_layer_speed_offset_to(
            layer_name: str,
            offset: float | int,
            to_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Create a named speed layer that offsets the base speed to an exact value.
        Multiple layers combine and the layer can be reverted by name.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.layer(layer_name).speed.offset.to(offset).over(to_ms).hold(hold_ms).revert(revert_ms)
        ```

        Examples:
        ```python
        mouse_rig_layer_speed_offset_to("boost", 5)                 # instant set
        mouse_rig_layer_speed_offset_to("boost", 5, 1000)           # set over 1s, stay
        mouse_rig_layer_speed_offset_to("boost", 5, 1000, 0, 1000)  # set 1s, revert 1s
        mouse_rig_layer_speed_offset_to("boost", 5, 0, 500, 0)      # instant, hold 500ms, revert
        ```
        """
        rig = actions.user.mouse_rig()
        builder = rig.layer(layer_name).speed.offset.to(offset)
        if to_ms is not None:
            builder = builder.over(to_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder = builder.revert(revert_ms)

    def mouse_rig_layer_speed_override_to(
            layer_name: str,
            speed: float | int,
            to_ms: int = None,
            hold_ms: int = None,
            revert_ms: int = None
        ) -> None:
        """Create a named speed layer that overrides the current speed to an exact value.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.layer(layer_name).speed.override.to(speed).over(to_ms).hold(hold_ms).revert(revert_ms)
        ```

        Examples:
        ```python
        mouse_rig_layer_speed_override_to("precision", 2)                 # instant override
        mouse_rig_layer_speed_override_to("precision", 2, 1000)           # override over 1s, stay
        mouse_rig_layer_speed_override_to("precision", 2, 1000, 0, 1000)  # override 1s, revert 1s
        mouse_rig_layer_speed_override_to("precision", 2, 0, 500, 0)      # instant, hold 500ms, revert
        ```
        """
        rig = actions.user.mouse_rig()
        builder = rig.layer(layer_name).speed.override.to(speed)
        if to_ms is not None:
            builder = builder.over(to_ms)
        if hold_ms is not None:
            builder = builder.hold(hold_ms)
        if revert_ms is not None:
            builder = builder.revert(revert_ms)

    def mouse_rig_layer_pos_override_to(
            layer_name: str,
            x: float,
            y: float,
            ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """Create a named position layer that overrides the mouse position.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.layer(layer_name).pos.override.to(x, y).over(ms, easing).then(callback)
        ```

        Examples:
        ```python
        mouse_rig_layer_pos_override_to("center", 960, 540)              # instant override
        mouse_rig_layer_pos_override_to("center", 960, 540, 500)         # override over 500ms
        mouse_rig_layer_pos_override_to("center", 960, 540, 500, "ease") # override with easing
        ```
        """
        rig = actions.user.mouse_rig()
        builder = rig.layer(layer_name).pos.override.to(x, y)
        if ms is not None:
            builder = builder.over(ms, easing)
        if callback is not None:
            builder.then(callback)

    def mouse_rig_layer_pos_offset_by(
            layer_name: str,
            dx: float,
            dy: float,
            ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """Create a named position layer that offsets the mouse position.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.layer(layer_name).pos.offset.by(dx, dy).over(ms, easing).then(callback)
        ```

        Examples:
        ```python
        mouse_rig_layer_pos_offset_by("shake", 10, 5)              # instant offset
        mouse_rig_layer_pos_offset_by("shake", 10, 5, 100)         # offset over 100ms
        mouse_rig_layer_pos_offset_by("shake", 10, 5, 100, "ease") # offset with easing
        ```
        """
        rig = actions.user.mouse_rig()
        builder = rig.layer(layer_name).pos.offset.by(dx, dy)
        if ms is not None:
            builder = builder.over(ms, easing)
        if callback is not None:
            builder.then(callback)

    def mouse_rig_layer_revert(
            layer_name: str,
            ms: int = None,
            easing: str = None,
            callback: callable = None
        ) -> None:
        """Revert a layer by name, optionally over time.

        Equivalent to:
        ```
        rig = actions.user.mouse_rig()
        rig.layer(layer_name).revert(ms, easing).then(callback)
        ```

        Examples:
        ```python
        mouse_rig_layer_revert("boost")                    # instant revert
        mouse_rig_layer_revert("boost", 500)               # revert over 500ms
        mouse_rig_layer_revert("boost", 500, "ease_out")   # revert with easing
        ```
        """
        rig = actions.user.mouse_rig()
        if rig.state.layer(layer_name):
            if ms is not None:
                handle = rig.layer(layer_name).revert(ms, easing)
            else:
                handle = rig.layer(layer_name).revert()

            if callback is not None:
                handle.then(callback)

    def mouse_rig_state_speed() -> float:
        """Get current speed from rig state"""
        rig = actions.user.mouse_rig()
        return rig.state.speed

    def mouse_rig_state_direction() -> tuple:
        """Get current direction (x, y) from rig state"""
        rig = actions.user.mouse_rig()
        return (rig.state.direction.x, rig.state.direction.y)

    def mouse_rig_state_pos() -> tuple:
        """Get current position (x, y) from rig state"""
        rig = actions.user.mouse_rig()
        return (rig.state.pos.x, rig.state.pos.y)

    def mouse_rig_state_layer(layer_name: str) -> bool:
        """Check if a layer exists in rig state"""
        rig = actions.user.mouse_rig()
        return rig.state.layer(layer_name)

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
        return rig.state.direction_cardinal

    def mouse_rig_state_layers() -> list:
        """Get list of active layer names.

        Returns list of user-defined layer names (excludes anonymous base layers).
        """
        rig = actions.user.mouse_rig()
        return rig.state.layers

    def mouse_rig_stop(ms: float = None, easing: str = None, callback: callable = None) -> None:
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
            handle = rig.stop(ms, easing)
        else:
            handle = rig.stop(ms)

        if callback is not None:
            handle.then(callback)

    def mouse_rig_set_api(api: str) -> None:
        """Set mouse movement API

        Args:
            api: API type - 'talon', 'windows_raw', 'windows_sendinput', 'macos', 'linux_x11'
        """
        if api not in MOUSE_APIS:
            available = ', '.join(f"'{k}'" for k in MOUSE_APIS.keys())
            return
        settings.set("user.mouse_rig_api", api)
        # Reload to pick up the new API immediately
        reload_rig()

    def mouse_rig_reload() -> None:
        """Reload/reset rig. Useful for development"""
        reload_rig()

    def mouse_rig_test_toggle_ui():
        """Show the QA UI for mouse rig development"""
        from .tests.main import toggle_test_ui
        toggle_test_ui()

    def mouse_rig_test_one():
        """Run test one from mouse rig tests"""
        # print("x", actions.mouse_x())
        # print("y", actions.mouse_y())
        # print(ctrl.mouse_pos())
        actions.user.mouse_rig_go_right(5, 10, 1000, "linear")