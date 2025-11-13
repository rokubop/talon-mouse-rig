"""Named entity builders for PRD 8 forces"""

import time
from typing import Optional, Callable, TYPE_CHECKING
from ..core import Vec2
from ..effects import Force

if TYPE_CHECKING:
    from ..state import RigState


class NamedForceBuilder:
    """Builder for named forces - independent entities with their own speed/direction/accel"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name
        self._ensure_force_exists()

    def _ensure_force_exists(self):
        """Ensure a Force object exists for this name"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)

    def _get_force(self) -> Force:
        """Get the Force object for this name"""
        self._ensure_force_exists()
        return self.rig_state._named_forces[self.name]

    @property
    def speed(self) -> 'NamedForceSpeedController':
        """Access speed property for this named force"""
        return NamedForceSpeedController(self.rig_state, self.name)

    @property
    def accel(self) -> 'NamedForceAccelController':
        """Access accel property for this named force"""
        return NamedForceAccelController(self.rig_state, self.name)

    def direction(self, x: float, y: float) -> 'NamedForceDirectionBuilder':
        """Set direction for this named force"""
        return NamedForceDirectionBuilder(self.rig_state, self.name, x, y)

    def over(self, duration_ms: float, easing: str = "linear") -> 'NamedForceBuilder':
        """Fade in the force over duration"""
        force = self._get_force()
        force.in_duration_ms = duration_ms
        force.in_easing = easing
        return self

    def hold(self, duration_ms: float) -> 'NamedForceBuilder':
        """Hold the force at full strength for duration"""
        force = self._get_force()
        force.hold_duration_ms = duration_ms
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'NamedForceBuilder':
        """Fade out the force over duration"""
        force = self._get_force()
        force.out_duration_ms = duration_ms
        force.out_easing = easing
        return self

    def stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop the named force

        Args:
            duration_ms: Optional duration to fade out. If None, stops immediately.
            easing: Easing function for gradual stop

        Examples:
            rig.force("wind").stop()  # Immediate stop
            rig.force("wind").stop(500, "ease_out")  # Fade out over 500ms
        """
        if self.name in self.rig_state._named_forces:
            force = self.rig_state._named_forces[self.name]
            force.request_stop(duration_ms, easing)



class NamedForceSpeedController:
    """Speed controller for named forces - only allows absolute setters"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def _get_force(self) -> Force:
        """Get or create the Force object"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        return self.rig_state._named_forces[self.name]

    def __call__(self, value: float) -> 'NamedForceSpeedController':
        """Set speed directly (absolute)"""
        return self.to(value)

    def to(self, value: float) -> 'NamedForceSpeedController':
        """Set speed to absolute value"""
        force = self._get_force()
        force._speed = value
        self.rig_state.start()  # Ensure ticking is active
        return self

    def over(self, duration_ms: float, easing: str = "linear") -> 'NamedForceSpeedController':
        """Fade in the force over duration"""
        force = self._get_force()
        force.in_duration_ms = duration_ms
        force.in_easing = easing
        return self

    def hold(self, duration_ms: float) -> 'NamedForceSpeedController':
        """Hold the force at full strength for duration"""
        force = self._get_force()
        force.hold_duration_ms = duration_ms
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'NamedForceSpeedController':
        """Fade out the force over duration"""
        force = self._get_force()
        force.out_duration_ms = duration_ms
        force.out_easing = easing
        return self

    def by(self, delta: float) -> 'NamedForceSpeedController':
        """ERROR: Forces cannot use .by() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.by)."
        )

    def mul(self, factor: float) -> 'NamedForceSpeedController':
        """ERROR: Forces cannot use .mul() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.mul)."
        )

    def div(self, divisor: float) -> 'NamedForceSpeedController':
        """ERROR: Forces cannot use .div() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.div)."
        )



class NamedForceAccelController:
    """Accel controller for named forces - only allows absolute setters"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def _get_force(self) -> Force:
        """Get or create the Force object"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        return self.rig_state._named_forces[self.name]

    def __call__(self, value: float) -> 'NamedForceAccelController':
        """Set accel directly (absolute)"""
        return self.to(value)

    def to(self, value: float) -> 'NamedForceAccelController':
        """Set accel to absolute value"""
        force = self._get_force()
        force._accel = value
        self.rig_state.start()  # Ensure ticking is active
        return self

    def over(self, duration_ms: float, easing: str = "linear") -> 'NamedForceAccelController':
        """Fade in the force over duration"""
        force = self._get_force()
        force.in_duration_ms = duration_ms
        force.in_easing = easing
        return self

    def hold(self, duration_ms: float) -> 'NamedForceAccelController':
        """Hold the force at full strength for duration"""
        force = self._get_force()
        force.hold_duration_ms = duration_ms
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'NamedForceAccelController':
        """Fade out the force over duration"""
        force = self._get_force()
        force.out_duration_ms = duration_ms
        force.out_easing = easing
        return self

    def by(self, delta: float) -> 'NamedForceAccelController':
        """ERROR: Forces cannot use .by() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.by)."
        )

    def mul(self, factor: float) -> 'NamedForceAccelController':
        """ERROR: Forces cannot use .mul() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.mul)."
        )

    def div(self, divisor: float) -> 'NamedForceAccelController':
        """ERROR: Forces cannot use .div() - use rig.modifier() for relative modifiers"""
        raise ValueError(
            f"Forces can only use absolute setters (.to, direct values). "
            f"Use rig.modifier('{self.name}') for relative modifiers (.div)."
        )



class NamedForceDirectionBuilder:
    """Direction builder for named forces"""
    def __init__(self, rig_state: 'RigState', name: str, x: float, y: float):
        self.rig_state = rig_state
        self.name = name
        self.x = x
        self.y = y

    def __del__(self):
        """Execute when builder goes out of scope"""
        try:
            # Set direction on the Force object
            if self.name not in self.rig_state._named_forces:
                self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)

            force = self.rig_state._named_forces[self.name]
            force._direction = Vec2(self.x, self.y).normalized()
            self.rig_state.start()  # Ensure ticking is active
        except:
            pass

    @property
    def speed(self) -> 'NamedForceSpeedController':
        """Access speed property for chaining"""
        # Set direction immediately
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()

        return NamedForceSpeedController(self.rig_state, self.name)

    @property
    def accel(self) -> 'NamedForceAccelController':
        """Access accel property for chaining"""
        # Set direction immediately
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()

        return NamedForceAccelController(self.rig_state, self.name)

    def over(self, duration_ms: float, easing: str = "linear") -> 'NamedForceDirectionBuilder':
        """Fade in the force over duration"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()
        force.in_duration_ms = duration_ms
        force.in_easing = easing
        return self

    def hold(self, duration_ms: float) -> 'NamedForceDirectionBuilder':
        """Hold the force at full strength for duration"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()
        force.hold_duration_ms = duration_ms
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'NamedForceDirectionBuilder':
        """Fade out the force over duration"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()
        force.out_duration_ms = duration_ms
        force.out_easing = easing
        return self


class NamedForceNamespace:
    """Namespace for rig.force operations"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, name: str) -> NamedForceBuilder:
        """Create or access a named force"""
        return NamedForceBuilder(self.rig_state, name)

    def stop_all(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop all named forces"""
        for force in list(self.rig_state._named_forces.values()):
            force.request_stop(duration_ms, easing)

        # Clean up force metadata
        if hasattr(self.rig_state, '_named_forces'):
            self.rig_state._named_forces.clear()

# STATE ACCESSORS
# ============================================================================
