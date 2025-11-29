from talon import settings, actions
from typing import Any
from .settings import mod
from .src import rig as get_rig, reload_rig
from .src.mouse_api import MOUSE_APIS

@mod.action_class
class Actions:
    def mouse_rig() -> Any:
        """Get the mouse rig instance
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

    def mouse_rig_stop(over_ms: float = None, easing: str = None) -> None:
        """Stop the mouse rig and remove all layers, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if easing is not None:
            rig.stop(over_ms, easing)
        else:
            rig.stop(over_ms)

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

    def mouse_rig_go_left(initial_speed: int = 3) -> None:
        """Move continuously left at specified speed.

        Maintains current speed if already moving, otherwise uses initial_speed.
        """
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        rig.speed(rig.state.speed or initial_speed)

    def mouse_rig_go_right(initial_speed: int = 3) -> None:
        """Move continuously right at specified speed.

        Maintains current speed if already moving, otherwise uses initial_speed.
        """
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(rig.state.speed or initial_speed)

    def mouse_rig_go_up(initial_speed: int = 3) -> None:
        """Move continuously up at specified speed.

        Maintains current speed if already moving, otherwise uses initial_speed.
        """
        rig = actions.user.mouse_rig()
        rig.direction(0, -1)
        rig.speed(rig.state.speed or initial_speed)

    def mouse_rig_go_down(initial_speed: int = 3) -> None:
        """Move continuously down at specified speed.

        Maintains current speed if already moving, otherwise uses initial_speed.
        """
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)
        rig.speed(rig.state.speed or initial_speed)

    def mouse_rig_speed_to(speed: float, over_ms: int = None, easing: str = None) -> None:
        """Set speed to absolute value, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if over_ms is not None:
            rig.speed.to(speed).over(over_ms, easing)
        else:
            rig.speed.to(speed)

    def mouse_rig_speed_add(delta: float, over_ms: int = None, easing: str = None) -> None:
        """Add to current speed, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if over_ms is not None:
            rig.speed.add(delta).over(over_ms, easing)
        else:
            rig.speed.add(delta)

    def mouse_rig_speed_mul(multiplier: float, over_ms: int = None, easing: str = None) -> None:
        """Multiply current speed, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if over_ms is not None:
            rig.speed.mul(multiplier).over(over_ms, easing)
        else:
            rig.speed.mul(multiplier)

    def mouse_rig_pos_to(x: float, y: float, over_ms: int = None, easing: str = None) -> None:
        """Move mouse to absolute position, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if over_ms is not None:
            rig.pos.to(x, y).over(over_ms, easing)
        else:
            rig.pos.to(x, y)

    def mouse_rig_pos_by(dx: float, dy: float, over_ms: int = None, easing: str = None) -> None:
        """Move mouse by relative offset, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if over_ms is not None:
            rig.pos.by(dx, dy).over(over_ms, easing)
        else:
            rig.pos.by(dx, dy)

    def mouse_rig_direction_to(x: float, y: float, over_ms: int = None, easing: str = None) -> None:
        """Set direction to absolute vector or angle, optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if over_ms is not None:
            rig.direction.to(x, y).over(over_ms, easing)
        else:
            rig.direction.to(x, y)

    def mouse_rig_direction_by(angle: float, over_ms: int = None, easing: str = None) -> None:
        """Rotate direction by angle (degrees), optionally over time.

        easing: "linear", "ease_in_out", etc.
        """
        rig = actions.user.mouse_rig()
        if over_ms is not None:
            rig.direction.by(angle).over(over_ms, easing)
        else:
            rig.direction.by(angle)

    def mouse_rig_boost(speed_increase: float, over_ms: int = None, revert_ms: int = None) -> None:
        """Temporarily boost speed"""
        rig = actions.user.mouse_rig()
        rig.speed.add(speed_increase).over(over_ms).revert(revert_ms)
