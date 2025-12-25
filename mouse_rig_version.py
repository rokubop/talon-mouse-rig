"""Auto-generated version action for mouse_rig"""
import json
import os
from talon import Module

mod = Module()

def get_version():
    """Returns (major, minor, patch) from manifest.json"""
    manifest_path = os.path.join(os.path.dirname(__file__), 'manifest.json')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        version_str = json.load(f)['version']
    return tuple(map(int, version_str.split('.')))

@mod.action_class
class Actions:
    def mouse_rig_version() -> tuple[int, int, int]:
        """Returns the package version as (major, minor, patch)"""
        return get_version()
