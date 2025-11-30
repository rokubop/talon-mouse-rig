from talon import settings, actions
from typing import Any
from .settings import mod
from .src import rig as get_rig, reload_rig
from .src.mouse_api import MOUSE_APIS

@mod.action_class
class Actions:
    def mouse_rig() -> Any:
        """
        Get mouse rig for advanced fluent API syntax.
        All talon actions use this under the hood.
        ```python
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.direction.to(1, 0)
        rig.direction.by(90).over(100)
        rig.speed(5)
        rig.speed.to(5)
        rig.speed.add(2)
        rig.pos.to(500, 300).over(200, easing="ease_in_out")
        rig.layer("my_layer").speed.offset(10).over(500)
        rig.layer("my_layer").revert()
        rig.stop()
        rig.stop(1000)
        rig...over(ms).then(...).hold(ms).then(...).revert(ms).then(...)
        ```
        """
        return get_rig()

    def mouse_rig_go_left(initial_speed: int = 3) -> None:
        """Move continuously left at current speed or initial speed."""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        if not rig.state.speed:
            rig.speed(initial_speed)

    def mouse_rig_go_right(initial_speed: int = 3) -> None:
        """Move continuously right at current speed or initial speed."""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        if not rig.state.speed:
            rig.speed(initial_speed)

    def mouse_rig_go_up(initial_speed: int = 3) -> None:
        """Move continuously up at current speed or initial speed."""
        rig = actions.user.mouse_rig()
        rig.direction(0, -1)
        if not rig.state.speed:
            rig.speed(initial_speed)

    def mouse_rig_go_down(initial_speed: int = 3) -> None:
        """Move continuously down at current speed or initial speed."""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)
        if not rig.state.speed:
            rig.speed(initial_speed)

    def mouse_rig_pos_to(
            x: float,
            y: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Move mouse to absolute position, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.pos.to(x, y)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_pos_by(
            dx: float,
            dy: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Move mouse by relative offset, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.pos.by(dx, dy)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_speed_to(
            speed: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Set speed to absolute value, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.speed.to(speed)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_speed_add(
            delta: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None,
        ) -> None:
        """Add to current speed, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.speed.add(delta)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_speed_mul(
            multiplier: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Multiply current speed, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.speed.mul(multiplier)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_direction_to(
            direction_x: float,
            direction_y: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Set direction to absolute vector, curve if time provided.

        Args:
            direction_x: X direction component (-1.0 to 1.0, where -1=left, 1=right)
            direction_y: Y direction component (-1.0 to 1.0, where -1=up, 1=down)
            to_ms: Time in milliseconds to curve to the new direction
            to_easing: Easing function - "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.direction.to(direction_x, direction_y)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_direction_by(
            degrees: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Rotate direction by degrees, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.direction.by(degrees)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_layer_speed_offset_add(
            layer_name: str,
            delta: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Add speed offset for a named layer, stackable and revertible"""
        rig = actions.user.mouse_rig()
        builder = rig.layer(layer_name).speed.offset.add(delta)
        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_layer_speed_offset_to(
            layer_name: str,
            speed: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Sets the layer's speed offset to an exact value (rather than adding to it).

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.layer(layer_name).speed.offset.to(speed)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_layer_speed_override_to(
            layer_name: str,
            speed: float,
            to_ms: int = None,
            to_easing: str = None,
            to_callback: callable = None,
            hold_ms: int = None,
            hold_easing: str = None,
            hold_callback: callable = None,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Set speed override for a layer, replacing base speed entirely.

        Unlike offset which adds to the base speed, override ignores the base
        speed and all other layers, setting an absolute speed value.

        Can be reverted with user.mouse_rig_layer_revert(layer_name).

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        builder = rig.layer(layer_name).speed.override.to(speed)

        if to_ms is not None:
            builder = builder.over(to_ms, to_easing)
        if to_callback is not None:
            builder = builder.then(to_callback)
        if hold_ms is not None:
            builder = builder.hold(hold_ms, hold_easing)
        if hold_callback is not None:
            builder = builder.then(hold_callback)
        if revert_ms is not None:
            builder = builder.revert(revert_ms, revert_easing)
        if revert_callback is not None:
            builder = builder.then(revert_callback)

    def mouse_rig_layer_revert(
            layer_name: str,
            revert_ms: int = None,
            revert_easing: str = None,
            revert_callback: callable = None
        ) -> None:
        """Revert a specific layer, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if rig.state.layer(layer_name):
            builder = rig.layer(layer_name)
            if revert_ms is not None:
                builder = builder.revert(revert_ms, revert_easing)
            else:
                builder = builder.revert()
            if revert_callback is not None:
                builder.then(revert_callback)

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

    def mouse_rig_stop(over_ms: float = None, easing: str = None, callback: callable = None) -> None:
        """Stop the mouse rig and remove all layers, optionally over time.

        Args:
            over_ms: Time in milliseconds to decelerate to stop
            easing: Easing function - "linear", "ease_in_out", etc.
            callback: Function to call when system fully stops
        """
        rig = actions.user.mouse_rig()
        if easing is not None:
            handle = rig.stop(over_ms, easing)
        else:
            handle = rig.stop(over_ms)

        if callback is not None:
            handle.then(callback)

    def mouse_rig_set_api(api: str) -> None:
        """Set mouse movement API

        Args:
            api: API type - 'talon', 'windows_raw', 'windows_sendinput', 'macos', 'linux_x11'
        """
        if api not in MOUSE_APIS:
            available = ', '.join(f"'{k}'" for k in MOUSE_APIS.keys())
            print(f"Invalid mouse API: '{api}'")
            print(f"Available: {available}")
            return
        settings.set("user.mouse_rig_api", api)
        print(f"Mouse API set to: {api}")
        # Reload to pick up the new API immediately
        reload_rig()

    def mouse_rig_set_scale(scale: float) -> None:
        """Set movement scale multiplier

        Args:
            scale: Scale factor (1.0 = normal, 2.0 = double, 0.5 = half)
        """
        settings.set("user.mouse_rig_scale", scale)

    def mouse_rig_reload() -> None:
        """Reload/reset rig. Useful for development"""
        reload_rig()

    def mouse_rig_test_toggle_ui():
        """Show the QA test UI with buttons"""
        from .qa.main import toggle_test_ui
        toggle_test_ui()
