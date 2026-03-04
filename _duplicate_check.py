"""Detects if this package is loaded from multiple locations."""
from talon import actions

_duplicate = False
try:
    actions.user.mouse_rig_version()
    _duplicate = True
except Exception:
    pass

if _duplicate:
    print("============================================================")
    print("DUPLICATE PACKAGE: talon-mouse-rig (user.mouse_rig)")
    print("")
    print("  talon-mouse-rig is already loaded from another location.")
    print("  If using talon-gamekit, remove your standalone talon-mouse-rig clone.")
    print("  Only one copy of talon-mouse-rig can exist in talon/user.")
    print("============================================================")
    raise RuntimeError(
        "Duplicate package: talon-mouse-rig (user.mouse_rig) is already loaded."
    )
