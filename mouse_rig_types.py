"""Value sets for user.mouse_rig_types(), built from the tables the code runs on. Easings are rig_core's."""

from talon import Module

from .mouse_rig import BUTTONS, DIRECTIONS
from .src.mouse_api import MOUSE_APIS, SCROLL_APIS

mod = Module()


def _values(table: dict) -> list:
    return [
        {"id": name, "desc": v[1] if isinstance(v, tuple) else v}
        for name, v in table.items()
    ]


def types() -> dict:
    return {
        "direction": {
            "desc": "Which way to move or scroll. Spaces, hyphens and capitals are also taken: 'up left', 'Up-Left'.",
            "values": _values(DIRECTIONS),
        },
        "button": {
            "desc": "A mouse button.",
            "values": _values(BUTTONS),
        },
        "mouse_api": {
            "desc": "What moves the cursor. pos.to always uses ctrl.mouse_move.",
            "values": _values(MOUSE_APIS),
        },
        "scroll_api": {
            "desc": "What scrolls, for the mouse_rig_scroll_api setting. The native APIs scroll by less than a line.",
            "values": _values(SCROLL_APIS),
        },
    }


@mod.action_class
class Actions:
    def mouse_rig_types() -> dict:
        """Named sets of values the mouse rig takes:
        {name: {"desc": str, "values": [{"id": str, "desc": str}]}}"""
        return types()
