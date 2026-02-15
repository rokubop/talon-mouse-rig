"""Talon settings for mouse rig"""

from talon import Module

mod = Module()

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
    desc="""API for all mouse rig movement, except `pos.to` which uses ctrl.mouse_move)
    Options:
    - "platform": Auto-detect best platform-specific API (windows_send_input, macos_warp, or linux_x11)
    - "talon": Talon actions.mouse_nudge for relative movement and ctrl.mouse_move for absolute movement
    - "windows_send_input": Windows SendInput (modern, recommended for Windows)
    - "windows_mouse_event": Windows win32api.mouse_event (legacy, requires pywin32)
    - "macos_warp": macOS CGWarpMouseCursorPosition (requires pyobjc-framework-Quartz)
    - "linux_x11": Linux X11 XWarpPointer (requires python-xlib)

    To override this, chain .api("name") to force a specific API for an individual action.
    """
)

mod.setting(
    "mouse_rig_scroll_api",
    type=str,
    default="default",
    desc="""API for scroll operations. Uses native platform APIs for sub-line precision.
    Options:
    - "default": Use the same API as mouse_rig_api
    - "platform": Auto-detect best platform-specific API
    - "talon": Talon actions.mouse_scroll (cross-platform, but quantizes small values)
    - "windows_send_input": Windows SendInput MOUSEEVENTF_WHEEL/HWHEEL
    - "windows_mouse_event": Windows win32api.mouse_event (legacy, requires pywin32)
    - "macos_warp": macOS CGEventCreateScrollWheelEvent (requires pyobjc-framework-Quartz)
    - "linux_x11": Linux X11 XTest fake button events (requires python-xlib)
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
    "mouse_rig_scale",
    type=float,
    default=1.0,
    desc="""Scale multiplier for all mouse rig movement, except `pos.to`.
    You may want to adjust this based on your mouse DPI settings or based on the application/game.
    """
)

mod.setting(
    "mouse_rig_natural_turn_ms",
    type=int,
    default=500,
    desc="Base duration in ms for direction changes in go_natural. Scales with speed (faster = smoother turns)."
)

mod.setting(
    "mouse_rig_natural_turn_easing",
    type=str,
    default="ease_out2",
    desc="Easing function for direction changes in go_natural"
)

mod.setting(
    "mouse_rig_natural_speed_ms",
    type=int,
    default=200,
    desc="Duration in ms for speed changes in go_natural"
)

mod.setting(
    "mouse_rig_natural_speed_easing",
    type=str,
    default="ease_in_out",
    desc="Easing function for speed changes in go_natural"
)

mod.setting(
    "mouse_rig_natural_move_ms",
    type=int,
    default=250,
    desc="Duration in ms for move_natural one-shot movements"
)

mod.setting(
    "mouse_rig_natural_move_easing",
    type=str,
    default="ease_out2",
    desc="Easing function for move_natural one-shot movements"
)

mod.setting(
    "mouse_rig_natural_scroll_ms",
    type=int,
    default=400,
    desc="Duration in ms for scroll_natural one-shot scrolls"
)

mod.setting(
    "mouse_rig_natural_scroll_easing",
    type=str,
    default="ease_out2",
    desc="Easing function for scroll_natural one-shot scrolls"
)

mod.setting(
    "mouse_rig_natural_pos_ms",
    type=int,
    default=300,
    desc="Duration in ms for pos_to_natural position moves"
)

mod.setting(
    "mouse_rig_natural_pos_easing",
    type=str,
    default="ease_in_out",
    desc="Easing function for pos_to_natural position moves"
)
