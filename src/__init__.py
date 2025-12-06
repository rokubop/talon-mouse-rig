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
from .state import RigState
from .builder import RigBuilder


# Global singleton state
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
            print(f"Error stopping frame loop: {e}")
        _global_state = None

    # Touch all Python files in src/ and tests/ to trigger Talon's file watcher
    # Touch src/__init__.py FIRST so module reinitializes properly
    import time
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
            print(f"Error updating __init__.py: {e}")

    # Then touch other src/ files
    for filename in os.listdir(src_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(src_dir, filename)
            try:
                os.utime(filepath, None)  # Updates to current time
                touched_count += 1
            except Exception as e:
                print(f"Error updating {filename}: {e}")

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
                    print(f"Error updating tests/{filename}: {e}")

    print(f"✓ Rig state cleared and {touched_count} files touched for reload")


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

    # ========================================================================
    # BEHAVIOR SUGAR (returns builder with behavior pre-set)
    # ========================================================================

    @property
    def stack(self):
        """Stack behavior accessor"""
        return _BehaviorAccessor(self._state, "stack")

    @property
    def reset(self):
        """Reset behavior accessor"""
        return _BehaviorAccessor(self._state, "reset")

    @property
    def queue(self):
        """Queue behavior accessor"""
        return _BehaviorAccessor(self._state, "queue")

    @property
    def extend(self):
        """Extend behavior accessor"""
        return _BehaviorAccessor(self._state, "extend")

    @property
    def throttle(self):
        """Throttle behavior accessor"""
        return _BehaviorAccessor(self._state, "throttle")

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
        from .contracts import validate_timing
        ms = validate_timing(ms, 'ms')
        self._state.stop(ms, easing)
        return StopHandle(self._state)

    def reverse(self, ms: Optional[float] = None) -> RigBuilder:
        """Reverse direction and speed (instant 180° flip with optional inertia transition)

        Uses a high-priority override layer to instantly negate velocity, preserving
        all existing layers. If ms is provided, applies counter-force over time.

        Example:
            Moving right at speed 3, direction (1, 0)
            After reverse(500):
            - Instant: Override layer sets velocity to (-3, 0) in world space
            - This makes it move right due to negative speed × reversed direction
            - Over 500ms: Offset layer adds (6, 0) to counter momentum
            - Result: Moving left at speed 3, direction (-1, 0)
        """
        from .core import Vec2

        # Get current computed velocity (includes all layers)
        current_speed = self._state.speed
        current_direction = self._state.direction
        current_velocity = current_direction * current_speed
        inverted_velocity = current_velocity * -1

        # Use override layer to instantly set inverted velocity
        # This preserves all existing layers underneath
        self.layer("__reverse__").vector.override.to(inverted_velocity.x, inverted_velocity.y)

        # If over time, apply counter-force via offset layer
        if ms is not None:
            # Counter-force needs to be 2x the original velocity to transition fully
            counter_vector = current_velocity * 2

            # Apply counter-force over time, then clean up reverse layer
            builder = self.layer("__reverse_counter__").vector.offset.add(counter_vector.x, counter_vector.y).over(ms)

            # After transition completes, remove the override layer
            # The counter-force will have moved us to the correct final velocity
            builder.then(lambda: self._state.remove_layer("__reverse__"))

            return builder

        # Instant reverse, no builder needed
        return RigBuilder(self._state)

    def bake(self):
        """Bake all active builders to base state"""
        self._state.bake_all()

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
        from .contracts import RigAttributeError, find_closest_match, VALID_RIG_METHODS, VALID_RIG_PROPERTIES

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


# Export public API
__all__ = ['rig', 'Rig', 'RigBuilder', 'RigState', 'reload_rig']
