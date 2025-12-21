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
    default="platform",
    desc="""API for all relative movement (except pos.to which always uses Talon's ctrl.mouse_move)
    Options:
    - platform: Auto-detect best platform-specific API (windows_send_input, macos_warp, or linux_x11)
    - talon: Talon actions.mouse_nudge (cross-platform)
    - windows_send_input: Windows SendInput (modern, recommended for Windows)
    - windows_mouse_event: Windows win32api.mouse_event (legacy, requires pywin32)
    - macos_warp: macOS CGWarpMouseCursorPosition (requires pyobjc-framework-Quartz)
    - linux_x11: Linux X11 XWarpPointer (requires python-xlib)

    To override this, chain .api("name") to force a specific API for an individual action.
    """
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

mod.setting(
    "mouse_rig_relative_scale",
    type=float,
    default=1.0,
    desc="Scale multiplier for all relative mouse movement. Adjust for gaming sensitivity or desktop precision."
)
