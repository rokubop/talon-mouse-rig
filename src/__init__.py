"""Mouse Rig V2 - Unified fluent API for mouse movement

This is the main entry point for the mouse rig system.

Example usage:
    from .src import rig

    def my_action():
        r = rig()
        r.speed.to(10)
        r.direction(1, 0)  # Start moving right

    def boost():
        r = rig()
        r.layer("boost").speed.add(10).hold(2000)

    def sprint():
        r = rig()
        r.layer("sprint").speed.mul(2).over(500).hold(3000).revert(500)
"""

from typing import Optional
import os
import time
from .state import RigState
from .builder import RigBuilder
from .contracts import (
    validate_timing,
    RigAttributeError,
    find_closest_match,
    VALID_RIG_METHODS,
    VALID_RIG_PROPERTIES
)
from .ui import show_reloading_notification

_global_state: Optional[RigState] = None


def _get_global_state() -> RigState:
    """Get or create the global rig state"""
    global _global_state
    if _global_state is None:
        _global_state = RigState()
    return _global_state


def reload_rig():
    """Clear the rig state and touch all Python files to force Talon reload

    Manually triggers reload by:
    1. Stopping active movements and clearing state
    2. Touching all Python files in src/ and tests/ to trigger Talon's file watcher

    Call this manually when you want to reload code changes.
    """
    global _global_state

    if _global_state is not None:
        # Stop any active movements
        try:
            # Stop movement first (sets base speed to 0)
            _global_state.stop(transition_ms=0)
            # Then stop the frame loop
            _global_state._stop_frame_loop()
        except Exception as e:
            pass
        _global_state = None

    # Show brief notification before reload
    show_reloading_notification()
    # Small delay to ensure notification is visible before reload
    time.sleep(0.1)

    # Touch all Python files in src/ and tests/ to trigger Talon's file watcher
    # Touch src/__init__.py FIRST so module reinitializes properly
    src_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(src_dir)

    touched_count = 0

    # Touch src/__init__.py first (order matters for Talon's reload)
    init_file = os.path.join(src_dir, '__init__.py')
    if os.path.exists(init_file):
        try:
            os.utime(init_file, None)
            touched_count += 1
        except Exception as e:
            pass

    # Then touch other src/ files (skip ui.py so notification cron job can execute)
    for filename in os.listdir(src_dir):
        if filename.endswith('.py') and filename not in ('__init__.py', 'ui.py'):
            filepath = os.path.join(src_dir, filename)
            try:
                os.utime(filepath, None)
                touched_count += 1
            except Exception as e:
                pass

    # Then touch tests/ files
    tests_dir = os.path.join(parent_dir, 'tests')
    if os.path.exists(tests_dir):
        for filename in os.listdir(tests_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(tests_dir, filename)
                try:
                    os.utime(filepath, None)
                    touched_count += 1
                except Exception as e:
                    pass
class StopHandle:
    """Handle returned by stop() that allows adding callbacks via .then()"""

    def __init__(self, state: RigState):
        self._state = state

    def then(self, callback):
        """Add a callback to be executed when the system fully stops

        The callback will only fire when:
        - The deceleration completes (if a transition time was specified)
        - The frame loop stops naturally
        - No other operations interrupt the stop

        Args:
            callback: Function to call when stopped
        """
        self._state.add_stop_callback(callback)
        return self


class Rig:
    """Main entry point for mouse rig operations

    All property accesses and methods return RigBuilder for fluent chaining.
    """

    def __init__(self):
        self._state = _get_global_state()

    # ========================================================================
    # PROPERTY ACCESSORS (base layer)
    # ========================================================================

    @property
    def pos(self):
        """Position property accessor (base layer)"""
        return RigBuilder(self._state).pos

    @property
    def speed(self):
        """Speed property accessor (base layer)"""
        return RigBuilder(self._state).speed

    @property
    def direction(self):
        """Direction property accessor (base layer)"""
        return RigBuilder(self._state).direction

    @property
    def vector(self):
        """Vector property accessor (base layer)"""
        return RigBuilder(self._state).vector

    # ========================================================================
    # LAYER METHOD
    # ========================================================================

    def layer(self, name: str, order: Optional[int] = None) -> RigBuilder:
        """Create a user layer

        Args:
            name: Layer name
            order: Optional execution order (lower numbers execute first)
        """
        return RigBuilder(self._state, layer=name, order=order)

    def api(self, api: str) -> RigBuilder:
        """Set API override for mouse operations

        Args:
            api: Mouse API to use ('talon', 'platform', 'windows_send_input', etc.)

        Returns:
            RigBuilder with API pre-configured

        Example:
            rig.api("talon").pos.by(100, 0)
        """
        return RigBuilder(self._state).api(api)

    # ========================================================================
    # BEHAVIOR SUGAR (returns builder with behavior pre-set)
    # ========================================================================

    @property
    def stack(self):
        """Stack behavior accessor"""
        return _BehaviorAccessor(self._state, "stack")

    @property
    def replace(self):
        """Replace behavior accessor"""
        return _BehaviorAccessor(self._state, "replace")

    @property
    def queue(self):
        """Queue behavior accessor"""
        return _BehaviorAccessor(self._state, "queue")

    @property
    def throttle(self):
        """Throttle behavior accessor"""
        return _BehaviorAccessor(self._state, "throttle")

    @property
    def debounce(self):
        """Debounce behavior accessor"""
        return _BehaviorAccessor(self._state, "debounce")

    # ========================================================================
    # SPECIAL OPERATIONS
    # ========================================================================

    def stop(self, ms: Optional[float] = None, easing: str = "linear") -> StopHandle:
        """Stop everything: bake all layers, clear builders, decelerate to 0

        Args:
            ms: Optional duration to decelerate over. If None, stops immediately.
            easing: Easing function for gradual deceleration

        Returns:
            StopHandle: Handle that allows chaining .then(callback) to execute
                       when the system fully stops
        """
        ms = validate_timing(ms, 'ms', method='stop')
        self._state.stop(ms, easing)
        return StopHandle(self._state)

    def reset(self):
        """Reset everything to default state

        Clears all layers, resets base speed to 0, base direction to (1, 0),
        and clears all tracking. Useful when properties persist unexpectedly.

        Example:
            rig.reset()  # Clean slate
        """
        self._state.reset()

    def reverse(self, ms: Optional[float] = None) -> RigBuilder:
        """Reverse direction (180° flip with optional smooth transition)

        Bakes all active layers first, then reverses. For gradual reversal,
        the current velocity is converted to a decaying offset that fades to zero
        while the reversed base direction takes effect. This allows new operations
        to blend naturally during the reversal.

        Example:
            Moving right at speed 3, direction (1, 0)
            After reverse():
                Instant: direction becomes (-1, 0), moving left
            After reverse(500):
                Smooth: Current velocity fades out as offset over 500ms
                while reversed base direction blends in
                New operations (wind, etc.) work during transition

        Args:
            ms: Optional duration for smooth reversal. If None, instant flip.

        Returns:
            RigBuilder for chaining
        """
        # First, bake all active layers to get clean base state
        self._state.bake_all()

        if ms is None:
            # Instant: just flip direction by 180°
            return self.direction.by(180)
        else:
            # Gradual: Bake current velocity as decaying offset
            # Capture current velocity from base state (everything is baked)
            current_velocity = self._state._base_direction * self._state._base_speed

            # Flip base direction immediately
            self._state._base_direction = self._state._base_direction * -1

            # The offset is (current_velocity - new_base_velocity)
            # which equals (current_velocity - (-current_velocity)) = 2 * current_velocity
            # This offset fades to zero, revealing the reversed base
            offset_vector = current_velocity * 2

            # Fade the offset from current to zero over duration
            return self.layer("reverse_fade").vector.offset.to(offset_vector.x, offset_vector.y).to(0, 0).over(ms)

    def bake(self):
        """Bake all active builders to base state"""
        self._state.bake_all()

    def emit(self, ms: float = 1000):
        """Bake all layers, convert current velocity to autonomous decaying offset

        Args:
            ms: Fade duration (default: 1000ms)
        """
        # Bake all active layers to get clean state
        self._state.bake_all()
        current_velocity = self._state._base_direction * self._state._base_speed
        self._state._base_speed = 0.0

        layer_name = f"_emit_{int(time.perf_counter() * 1000000)}"
        self.layer(layer_name).vector.offset.to(current_velocity.x, current_velocity.y).revert(ms)

    # ========================================================================
    # STATE ACCESS
    # ========================================================================

    @property
    def state(self):
        """Access to current computed state"""
        return self._state

    @property
    def base(self):
        """Access to base (baked) state"""
        return self._state.base

    def __getattr__(self, name: str):
        """Handle unknown attributes with helpful error messages"""
        # Combine all valid options
        all_valid = VALID_RIG_METHODS + VALID_RIG_PROPERTIES

        # Find closest match
        suggestion = find_closest_match(name, all_valid)

        msg = f"Rig has no attribute '{name}'"
        if suggestion:
            msg += f"\n\nDid you mean: '{suggestion}'?"
        else:
            msg += f"\n\nAvailable properties: {', '.join(VALID_RIG_PROPERTIES)}"
            msg += f"\nAvailable methods: {', '.join(VALID_RIG_METHODS)}"

        raise RigAttributeError(msg)


class _BehaviorAccessor:
    """Helper to allow behavior to be used as property or method"""

    def __init__(self, state: RigState, behavior: str):
        self._state = state
        self._behavior = behavior

    def __call__(self, *args) -> RigBuilder:
        """Called when used as method: rig.stack(3)"""
        builder = RigBuilder(self._state)
        builder.config.behavior = self._behavior
        builder.config.behavior_args = args
        return builder

    @property
    def pos(self):
        """Property access: rig.stack.pos"""
        builder = RigBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.pos

    @property
    def speed(self):
        """Property access: rig.stack.speed"""
        builder = RigBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.speed

    @property
    def direction(self):
        """Property access: rig.stack.direction"""
        builder = RigBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.direction


# Main entry point function
def rig() -> Rig:
    """Get a new Rig instance

    Returns:
        Rig instance for fluent API calls

    Example:
        rig = actions.user.mouse_rig()
        rig.speed.to(10)
        rig.direction(1, 0)
    """
    return Rig()


def get_version() -> tuple[int, int, int]:
    """Returns (major, minor, patch) from manifest.json"""
    import json
    src_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(src_dir)
    manifest_path = os.path.join(parent_dir, 'manifest.json')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        version_str = json.load(f)['version']
    return tuple(map(int, version_str.split('.')))


# Export public API
__all__ = ['rig', 'Rig', 'RigBuilder', 'RigState', 'reload_rig']
