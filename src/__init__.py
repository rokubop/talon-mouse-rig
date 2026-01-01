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

    def reverse(self, ms: Optional[float] = None, easing: str = "linear"):
        """Reverse direction of all movement (base + layers)

        Args:
            ms: Optional transition duration. If None, reverses instantly.
                If provided, creates smooth transition through zero.
            easing: Easing function for gradual reversal

        Examples:
            rig.reverse()         # Instant 180° turn
            rig.reverse(1000)     # Smooth turn over 1 second
        """
        ms = validate_timing(ms, 'ms', method='reverse') if ms is not None else None

        if ms is not None:
            # Gradual reverse: emit copies to bridge transition
            self._emit_reverse_copies(ms, easing)

        # Always reverse all directions (instant or gradual)
        self._reverse_all_directions()

    def _emit_reverse_copies(self, ms: float, easing: str = "linear"):
        """Helper: Emit copies of all layers and base velocity for gradual reverse transitions

        Copies each layer twice to provide 2x contribution that fades out,
        which bridges from current velocity to reversed velocity smoothly.
        """
        print(f"\n=== _emit_reverse_copies ===")
        print(f"Active layers: {list(self._state._layer_groups.keys())}")
        print(f"Base velocity: {self._state._base_direction} * {self._state._base_speed}")

        for layer_name in list(self._state._layer_groups.keys()):
            try:
                # Intentional - 2 copies
                print(f"Copying and emitting layer: {layer_name}")
                self.layer(layer_name).copy().emit(ms, easing)
                self.layer(layer_name).copy().emit(ms, easing)
            except Exception as e:
                print(f"Failed to copy/emit layer {layer_name}: {e}")

        # Create 2x base velocity as decaying offset
        current_base_velocity = self._state._base_direction * self._state._base_speed
        offset_velocity = current_base_velocity * 2

        print(f"Creating base emit layer with offset: ({offset_velocity.x}, {offset_velocity.y})")

        layer_name = f"emit.base.{int(time.perf_counter() * 1000000)}"
        self.layer(layer_name).vector.offset.to(offset_velocity.x, offset_velocity.y).revert(ms, easing)

        # Mark as emit layer so it won't be reversed
        if layer_name in self._state._layer_groups:
            self._state._layer_groups[layer_name].is_emit_layer = True
            print(f"Marked {layer_name} as emit layer")

        print(f"After creating layer, layers: {list(self._state._layer_groups.keys())}")

    def _reverse_all_directions(self):
        """Helper: Reverse base direction, all layer accumulated values, and active builders

        Only reverses user-named layers, not emit layers (which should fade in their original direction).
        """
        print(f"\n=== _reverse_all_directions ===")
        print(f"Base direction before: {self._state._base_direction}")

        self._state._base_direction = self._state._base_direction * -1

        print(f"Base direction after: {self._state._base_direction}")
        print(f"Reversing {len(self._state._layer_groups)} layer groups")

        for layer_group in self._state._layer_groups.values():
            # Skip emit/copy layers - they should fade in their original direction
            if layer_group.is_emit_layer:
                print(f"  Skipping emit layer: {layer_group.layer_name}")
                continue

            if layer_group.property in ("direction", "vector") and layer_group.accumulated_value is not None:
                print(f"  Reversing {layer_group.layer_name} accumulated value: {layer_group.accumulated_value} -> {layer_group.accumulated_value * -1}")
                layer_group.accumulated_value = layer_group.accumulated_value * -1

            for builder in layer_group.builders:
                if builder.config.property in ("direction", "vector") and builder.target_value is not None:
                    print(f"  Reversing {layer_group.layer_name} builder target: {builder.target_value} -> {builder.target_value * -1}")
                    builder.target_value = builder.target_value * -1
                    if builder.base_value is not None:
                        builder.base_value = builder.base_value * -1

    def bake(self):
        """Bake all active builders to base state"""
        self._state.bake_all()

    def emit(self, ms: float = 1000, easing: str = "linear") -> RigBuilder:
        """Convert current total velocity to autonomous decaying offset

        Args:
            ms: Fade duration (default: 1000ms)
            easing: Easing function for the decay (default: "linear")

        Example:
            rig.emit(500, "ease_out").then(lambda: print("Momentum faded"))
        """
        # Get total current velocity (includes all layers)
        speed, direction = self._state._compute_velocity()
        current_velocity = direction * speed

        # Bake everything and zero out base speed
        self._state.bake_all()
        self._state._base_speed = 0.0

        layer_name = f"emit.base.{int(time.perf_counter() * 1000000)}"
        return self.layer(layer_name).vector.offset.to(current_velocity.x, current_velocity.y).revert(ms, easing)

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
