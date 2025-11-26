from talon import settings
from .settings import mod
from .src import rig as get_rig, reload_rig
from .src.mouse_api import MOUSE_APIS

@mod.action_class
class Actions:
    def mouse_rig():
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
        rig.stop()
        ```
        """
        return get_rig()

    def mouse_rig_stop(ms: float = None, easing: str = None) -> None:
        """Alias for `rig.stop(ms, easing)`

        `rig.stop()` - Stop the mouse rig and remove all layers

        `rig.stop(1000)` - Flatten all layers, and then stop over 1000ms

        Easing values - `"ease_in_out"`, `"linear"`, `"ease_out"`, `"ease_in"`
        Also can numbers 2, 3, 4 at the end of the easing to increase power e.g. `"ease_in_out2"`
        """
        rig = get_rig()
        rig.stop(ms, easing)

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
