"""Mouse Rig V2 - Unified fluent API for mouse movement

This is the main entry point for the mouse rig system.

Example usage:
    from .src_v2 import rig

    def my_action():
        r = rig()
        r.speed.to(10)
        r.direction(1, 0)  # Start moving right

    def boost():
        r = rig()
        r.tag("boost").speed.add(10).hold(2000)

    def sprint():
        r = rig()
        r.tag("sprint").speed.mul(2).over(500).hold(3000).revert(500)
"""

from typing import Optional
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


class Rig:
    """Main entry point for mouse rig operations

    All property accesses and methods return RigBuilder for fluent chaining.
    """

    def __init__(self):
        self._state = _get_global_state()

    # ========================================================================
    # PROPERTY ACCESSORS
    # ========================================================================

    @property
    def pos(self):
        """Position property accessor"""
        return RigBuilder(self._state).pos

    @property
    def speed(self):
        """Speed property accessor"""
        return RigBuilder(self._state).speed

    @property
    def direction(self):
        """Direction property accessor"""
        return RigBuilder(self._state).direction

    @property
    def accel(self):
        """Acceleration property accessor"""
        return RigBuilder(self._state).accel

    # ========================================================================
    # TAG ACCESSOR
    # ========================================================================

    def tag(self, name: str) -> RigBuilder:
        """Create a tagged builder"""
        return RigBuilder(self._state, tag=name)

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
    def extend(self):
        """Extend behavior accessor"""
        return _BehaviorAccessor(self._state, "extend")

    @property
    def throttle(self):
        """Throttle behavior accessor"""
        return _BehaviorAccessor(self._state, "throttle")

    @property
    def ignore(self):
        """Ignore behavior accessor"""
        return _BehaviorAccessor(self._state, "ignore")

    # ========================================================================
    # SPECIAL OPERATIONS
    # ========================================================================

    def stop(self, ms: Optional[float] = None, easing: str = "linear"):
        """Stop everything: bake all effects, clear builders, decelerate to 0

        Args:
            ms: Optional duration to decelerate over. If None, stops immediately.
            easing: Easing function for gradual deceleration
        """
        self._state.stop(ms, easing)

    def reverse(self, ms: Optional[float] = None) -> RigBuilder:
        """Reverse direction (180° turn)"""
        builder = RigBuilder(self._state)
        builder.config.property = "direction"
        builder.config.operator = "by"
        builder.config.value = 180
        if ms is not None:
            builder.over(ms)
        return builder

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

    @property
    def accel(self):
        """Property access: rig.stack.accel"""
        builder = RigBuilder(self._state)
        builder.config.behavior = self._behavior
        return builder.accel


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
__all__ = ['rig', 'Rig', 'RigBuilder', 'RigState']
