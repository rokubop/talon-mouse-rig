"""Talon settings for mouse rig"""

from talon import Module

mod = Module()

# Settings
mod.setting(
    "mouse_rig_frame_interval",
    type=int,
    default=16,
    desc="Frame interval in milliseconds (default 16ms = ~60fps)"
)
mod.setting(
    "mouse_rig_max_speed",
    type=float,
    default=15.0,
    desc="Default maximum speed limit (pixels per frame)"
)
mod.setting(
    "mouse_rig_epsilon",
    type=float,
    default=0.01,
    desc="Epsilon for floating point comparisons"
)
mod.setting(
    "mouse_rig_default_turn_rate",
    type=float,
    default=180.0,
    desc="Default turn rate in degrees per second (used with .rate() without args)"
)
mod.setting(
    "mouse_rig_movement_type",
    type=str,
    default="talon",
    desc="Mouse movement type: 'talon' (ctrl.mouse_move) or 'windows_raw' (win32api.mouse_event)"
)
mod.setting(
    "mouse_rig_scale",
    type=float,
    default=1.0,
    desc="Movement scale multiplier (1.0 = normal, 2.0 = double speed/distance, 0.5 = half speed/distance)"
)
