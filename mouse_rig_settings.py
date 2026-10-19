"""Talon settings for mouse rig"""

from talon import Module

from .src.mouse_api import MOUSE_APIS, SCROLL_APIS

mod = Module()


def _options(apis: dict) -> str:
    return "\n".join(f'    - "{name}": {desc}' for name, desc in apis.items())

mod.setting(
    "mouse_rig_frame_interval",
    type=int,
    default=16,
    desc="""How often (in milliseconds) the mouse cursor position updates.
    Lower = smoother movement. Default: 16ms (60 updates per second)"""
)

mod.setting(
    "mouse_rig_api",
    type=str,
    default="platform",
    desc=f"""API for all mouse rig movement, except `pos.to` which uses ctrl.mouse_move)
    Options:
{_options(MOUSE_APIS)}

    To override this, chain .api("name") to force a specific API for an individual action.
    Type: mouse_rig.mouse_api
    """
)

mod.setting(
    "mouse_rig_scroll_api",
    type=str,
    default="default",
    desc=f"""API for scroll operations. Uses native platform APIs for sub-line precision.
    Options:
{_options(SCROLL_APIS)}
    Type: mouse_rig.scroll_api
    """
)



mod.setting(
    "mouse_rig_scale",
    type=float,
    default=1.0,
    desc="""Scale multiplier for all mouse rig movement, except `pos.to`.
    You may want to adjust this based on your mouse DPI settings or based on the application/game.
    """
)

mod.setting(
    "mouse_rig_smooth_turn_ms",
    type=int,
    default=500,
    desc="Base duration in ms for direction changes in move_continuous_smooth. Scales with speed (faster = smoother turns)."
)

mod.setting(
    "mouse_rig_smooth_turn_easing",
    type=str,
    default="ease_out2",
    desc="Easing function for direction changes in move_continuous_smooth. Type: rig_core.easing"
)

mod.setting(
    "mouse_rig_smooth_speed_ms",
    type=int,
    default=200,
    desc="Duration in ms for speed changes in move_continuous_smooth"
)

mod.setting(
    "mouse_rig_smooth_speed_easing",
    type=str,
    default="ease_in_out",
    desc="Easing function for speed changes in move_continuous_smooth. Type: rig_core.easing"
)

mod.setting(
    "mouse_rig_smooth_delta_ms",
    type=int,
    default=250,
    desc="Duration in ms for move_delta_smooth one-shot movements"
)

mod.setting(
    "mouse_rig_smooth_delta_easing",
    type=str,
    default="ease_out2",
    desc="Easing function for move_delta_smooth one-shot movements. Type: rig_core.easing"
)

mod.setting(
    "mouse_rig_smooth_scroll_ms",
    type=int,
    default=400,
    desc="Duration in ms for scroll_delta_smooth one-shot scrolls"
)

mod.setting(
    "mouse_rig_smooth_scroll_easing",
    type=str,
    default="ease_out2",
    desc="Easing function for scroll_delta_smooth one-shot scrolls. Type: rig_core.easing"
)

mod.setting(
    "mouse_rig_smooth_move_to_ms",
    type=int,
    default=300,
    desc="Duration in ms for move_to_smooth position moves"
)

mod.setting(
    "mouse_rig_smooth_move_to_easing",
    type=str,
    default="ease_in_out",
    desc="Easing function for move_to_smooth position moves. Type: rig_core.easing"
)
