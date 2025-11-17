"""Force builders - independent velocity sources"""

from typing import Optional, TYPE_CHECKING, TypeVar
from ..core import Vec2
from ..effects import Force
from .contracts import PropertyOperationsContract, TimingMethodsContract, TransitionBasedBuilder
from .rate_utils import (
    validate_rate_params,
    calculate_duration_from_rate,
    calculate_over_duration_for_property,
    calculate_revert_duration_for_property
)

if TYPE_CHECKING:
    from ..state import RigState

# Type variable for self-return types in base class
T = TypeVar('T', bound='ForcePropertyController')


class ForcePropertyController(PropertyOperationsContract[T]):
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
        """Subtract delta from current property value"""
        current = self._get_current_value()
        self._set_value(current - delta)
        return self

    # ===== Hooks for PropertyOperationsContract (includes TimingMethodsContract) =====

    def _calculate_over_duration_from_rate(
        self,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> float:
        """Calculate duration from rate based on current force value (fading from 0)"""
        current = self._get_current_value()
        # For forces, we're fading in from 0 to current value
        return calculate_over_duration_for_property(
            self._property_name, 0.0, current,
            rate_speed, rate_accel, rate_rotation
        )

    def _store_over_config(self, duration_ms: Optional[float], easing: str) -> None:
        """Store configuration on Force object, not builder fields"""
        force = self._get_force()
        force.in_duration_ms = duration_ms
        force.in_easing = easing

    def _calculate_revert_duration_from_rate(self, rate_speed: Optional[float],
                                            rate_accel: Optional[float],
                                            rate_rotation: Optional[float]) -> Optional[float]:
        """Calculate revert duration from rate parameters"""
        current = self._get_current_value()
        return calculate_revert_duration_for_property(
            self._property_name, current,
            rate_speed, rate_accel, rate_rotation
        )

    def _after_hold_configured(self, duration_ms: float) -> None:
        """Apply hold to force"""
        force = self._get_force()
        force.hold_duration_ms = duration_ms

    def _after_revert_configured(self, duration_ms: float, easing: str) -> None:
        """Apply revert to force"""
        force = self._get_force()
        force.out_duration_ms = duration_ms
        force.out_easing = easing


class NamedForceBuilder(TimingMethodsContract['NamedForceBuilder']):
    """Builder for named forces - independent entities with their own speed/direction/accel"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name
        self._ensure_force_exists()

    def _ensure_force_exists(self):
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

    # ===== Hooks for TimingMethodsContract =====

    def _store_over_config(self, duration_ms: Optional[float], easing: str) -> None:
        """Store configuration on Force object"""
        force = self._get_force()
        force.in_duration_ms = duration_ms
        force.in_easing = easing

    def _after_hold_configured(self, duration_ms: float) -> None:
        """Apply hold to force"""
        force = self._get_force()
        force.hold_duration_ms = duration_ms

    def _after_revert_configured(self, duration_ms: float, easing: str) -> None:
        """Apply revert to force"""
        force = self._get_force()
        force.out_duration_ms = duration_ms
        force.out_easing = easing

    def stop(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None,
        interpolation: str = "lerp"
    ) -> 'ForcePropertyController':
        """Stop the named force

        Args:
            duration_ms: Optional duration to fade out. If None, stops immediately.
            easing: Easing function for gradual stop
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
            interpolation: Interpolation method - "lerp" (linear, default) or "slerp" (rotation)

        Examples:
            rig.force("wind").stop()  # Immediate stop
            rig.force("wind").stop(500, "ease_out")  # Fade out over 500ms
            rig.force("wind").stop(rate_speed=30)  # Decelerate at 30 units/s
        """
        # Validate and check if rate parameters are provided
        rate_provided = validate_rate_params(duration_ms, rate_speed, rate_accel, rate_rotation)

        # Calculate duration from rate if provided
        if rate_provided:
            # Get the force to calculate current values
            if self.name in self.rig_state._named_forces:
                force = self.rig_state._named_forces[self.name]
                current = self._get_current_value()
                duration_ms = calculate_revert_duration_for_property(
                    self._property_name, current,
                    rate_speed, rate_accel, rate_rotation
                )

        if self.name in self.rig_state._named_forces:
            force = self.rig_state._named_forces[self.name]
            force.request_stop(duration_ms, easing)

        return self



class NamedForceSpeedController(ForcePropertyController['NamedForceSpeedController']):
    """Speed controller for named forces - supports all operations (to/by/mul/div)"""
    _property_name = "speed"


class NamedForceAccelController(ForcePropertyController['NamedForceAccelController']):
    """Accel controller for named forces - supports all operations (to/by/mul/div)"""
    _property_name = "accel"



class NamedForceDirectionBuilder(TimingMethodsContract['NamedForceDirectionBuilder'], TransitionBasedBuilder):
    """Direction builder for named forces"""
    def __init__(self, rig_state: 'RigState', name: str, x: float, y: float):
        self.rig_state = rig_state
        self.name = name
        self.x = x
        self.y = y

    def _has_transition(self) -> bool:
        """Named force direction always executes (no transition concept)"""
        return False

    def _has_instant(self) -> bool:
        """Always execute instantly"""
        return True

    def _execute_transition(self):
        """Not used for force direction"""
        pass

    def _execute_instant(self):
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)

        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()
        self.rig_state.start()  # Ensure ticking is active

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

    # ===== Hooks for TimingMethodsContract =====

    def _store_over_config(self, duration_ms: Optional[float], easing: str) -> None:
        """Store configuration on Force object and set direction"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()
        force.in_duration_ms = duration_ms
        force.in_easing = easing

    def _after_hold_configured(self, duration_ms: float) -> None:
        """Apply hold to force"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()
        force.hold_duration_ms = duration_ms

    def _after_revert_configured(self, duration_ms: float, easing: str) -> None:
        """Apply revert to force"""
        if self.name not in self.rig_state._named_forces:
            self.rig_state._named_forces[self.name] = Force(self.name, self.rig_state)
        force = self.rig_state._named_forces[self.name]
        force._direction = Vec2(self.x, self.y).normalized()
        force.out_duration_ms = duration_ms
        force.out_easing = easing


class NamedForceNamespace:
    """Namespace for rig.force operations"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, name: str) -> NamedForceBuilder:
        """Create or access a named force"""
        return NamedForceBuilder(self.rig_state, name)

    def stop_all(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None,
        interpolation: str = "lerp"
    ) -> None:
        """Stop all named forces

        Args:
            duration_ms: Optional duration to fade out. If None, stops immediately.
            easing: Easing function for gradual stop
            rate_speed: Speed deceleration rate in units/second (rate-based)
            rate_accel: Acceleration deceleration rate in units/second² (rate-based)
            interpolation: Interpolation method - "lerp" (linear, default) or "slerp" (rotation)
        """
        # Note: For stop_all, rate-based stopping applies per-force
        # Each force will calculate its own duration based on its current values
        for force in list(self.rig_state._named_forces.values()):
            force.request_stop(duration_ms, easing)

        # Clean up force metadata
        if hasattr(self.rig_state, '_named_forces'):
            self.rig_state._named_forces.clear()
