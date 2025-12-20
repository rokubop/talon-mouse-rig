"""Talon settings for mouse rig"""

from talon import Module

mod = Module()

mod.setting("mouse_rig_frame_interval",
    type=int,
    default=16,
    desc="Frame interval in milliseconds (default 16ms = ~60fps)"
)

mod.setting(
    "mouse_rig_api_absolute",
    type=str,
    default="talon",
    desc="""API for absolute positioning (pos.to).

    Options:
    - talon: Talon ctrl.mouse_move (cross-platform, default)
    - platform: Auto-detect best platform-specific API
    - windows_mouse_event: Windows win32api.mouse_event (legacy, requires pywin32)
    - windows_send_input: Windows SendInput (modern, recommended for Windows)
    - macos_warp: macOS CGWarpMouseCursorPosition (requires pyobjc-framework-Quartz)
    - linux_x11: Linux X11 XWarpPointer (requires python-xlib)
    """
)

mod.setting(
    "mouse_rig_api_relative",
    type=str,
    default="platform",
    desc="""API for relative movement (pos.by, speed.to, speed.by, vector.to, etc.).

    Options:
    - platform: Auto-detect best platform-specific API (recommended)
    - talon: Talon actions.mouse_nudge (cross-platform)
    - windows_mouse_event: Windows win32api.mouse_event (legacy, requires pywin32)
    - windows_send_input: Windows SendInput (modern, recommended for Windows)
    - macos_warp: macOS CGWarpMouseCursorPosition (requires pyobjc-framework-Quartz)
    - linux_x11: Linux X11 XWarpPointer (requires python-xlib)
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
