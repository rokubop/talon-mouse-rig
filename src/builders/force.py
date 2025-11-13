"""Force builders for PRD 8 - independent velocity sources"""

import time
from typing import Optional, Callable, TYPE_CHECKING, TypeVar, Generic
from ..core import Vec2
from ..effects import Force

if TYPE_CHECKING:
    from ..state import RigState

# Type variable for self-return types in base class
T = TypeVar('T', bound='ForcePropertyController')


class ForcePropertyController(Generic[T]):
    """
    Generic base class for force property controllers (speed/accel).
    Handles all operations (to/by/mul/div) and timing methods (over/hold/revert).
    Subclasses only need to specify _property_name.
    """
    # Override in subclasses: "speed" or "accel"
    _property_name: str = None

    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def _get_force(self) -> Force:
        """Get or create the Force object"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        return self.rig_state._named_forces[self.name]

    def _get_current_value(self) -> float:
        """Get the current property value from the force"""
        force = self._get_force()
        if self._property_name == "speed":
            return force._speed
        elif self._property_name == "accel":
            return force._accel
        else:
            raise ValueError(f"Unknown property: {self._property_name}")

    def _set_value(self, value: float) -> None:
        """Set the property value on the force"""
        force = self._get_force()
        if self._property_name == "speed":
            force._speed = value
        elif self._property_name == "accel":
            force._accel = value
        else:
            raise ValueError(f"Unknown property: {self._property_name}")
        self.rig_state.start()  # Ensure ticking is active

    def __call__(self, value: float) -> T:
        """Set property directly (absolute)"""
        return self.to(value)

    def to(self, value: float) -> T:
        """Set property to absolute value"""
        self._set_value(value)
        return self

    def by(self, delta: float) -> T:
        """Add delta to current property value"""
        current = self._get_current_value()
        self._set_value(current + delta)
        return self

    def mul(self, factor: float) -> T:
        """Multiply current property value by factor"""
        current = self._get_current_value()
        self._set_value(current * factor)
        return self

    def div(self, divisor: float) -> T:
        """Divide current property value by divisor"""
        if abs(divisor) < 1e-10:
            raise ValueError(f"Cannot divide {self._property_name} by zero")
        current = self._get_current_value()
        self._set_value(current / divisor)
        return self

    def add(self, delta: float) -> T:
        """Add delta to current property value (alias for .by())"""
        return self.by(delta)

    def sub(self, delta: float) -> T:
        """Subtract from current property value"""
        return self.by(-delta)

    def subtract(self, delta: float) -> T:
        """Subtract from current property value (alias for .sub())"""
        return self.sub(delta)

    def over(self, duration_ms: float, easing: str = "linear") -> T:
        """Fade in the force over duration"""
        force = self._get_force()
        force.in_duration_ms = duration_ms
        force.in_easing = easing
        return self

    def hold(self, duration_ms: float) -> T:
        """Hold the force at full strength for duration"""
        force = self._get_force()
        force.hold_duration_ms = duration_ms
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> T:
        """Fade out the force over duration"""
        force = self._get_force()
        force.out_duration_ms = duration_ms
        force.out_easing = easing
        return self


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



class NamedForceSpeedController(ForcePropertyController['NamedForceSpeedController']):
    """Speed controller for named forces - supports all operations (to/by/mul/div)"""
    _property_name = "speed"


class NamedForceAccelController(ForcePropertyController['NamedForceAccelController']):
    """Accel controller for named forces - supports all operations (to/by/mul/div)"""
    _property_name = "accel"



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
