"""Talon settings for mouse rig"""

from talon import Module

mod = Module()

mod.setting("mouse_rig_frame_interval",
    type=int,
    default=16,
    desc="Frame interval in milliseconds (default 16ms = ~60fps)"
)

mod.setting(
    "mouse_rig_api",
    type=str,
    default="talon",
    desc="Options: 'talon', 'windows_raw', 'windows_sendinput', 'macos', 'linux_x11'"
)

mod.setting(
    "mouse_rig_pause_on_manual_movement",
    type=bool,
    default=True,
    desc="Whether manual mouse movement should pause the rig temporarily"
)

mod.setting(
    "mouse_rig_manual_movement_timeout_ms",
    type=int,
    default=300,
    desc="Timeout in milliseconds after manual mouse movement before rig resumes control"
)
