"""Named entity builders for PRD 5/8"""

import time
from typing import Optional, Callable, TYPE_CHECKING
from ..core import Vec2
from ..effects import Effect, DirectionEffect, Force

if TYPE_CHECKING:
    from ..state import RigState
    from .base import PropertyEffectBuilder

class NamedModifierBuilder:
    """Builder for named modifiers that can be stopped early"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name
        self._speed_controller = None
        self._accel_controller = None
        self._direction_controller = None

    @property
    def speed(self) -> 'NamedSpeedController':
        """Access speed property for this named modifier"""
        if self._speed_controller is None:
            self._speed_controller = NamedSpeedController(self.rig_state, self.name)
        return self._speed_controller

    @property
    def accel(self) -> 'NamedAccelController':
        """Access accel property for this named modifier"""
        if self._accel_controller is None:
            self._accel_controller = NamedAccelController(self.rig_state, self.name)
        return self._accel_controller

    @property
    def direction(self) -> 'NamedDirectionController':
        """Access direction property for this named modifier"""
        if self._direction_controller is None:
            self._direction_controller = NamedDirectionController(self.rig_state, self.name)
        return self._direction_controller

    def stop(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop the named modifier

        Args:
            duration_ms: Optional duration to fade out. If None, stops immediately.
            easing: Easing function for gradual stop

        Examples:
            rig("boost").stop()  # Immediate stop
            rig("boost").stop(500, "ease_out")  # Fade out over 500ms
        """
        # Stop speed/accel modifiers
        if self.name in self.rig_state._named_modifiers:
            effect = self.rig_state._named_modifiers[self.name]
            effect.request_stop(duration_ms, easing)

        # Stop direction modifiers
        if self.name in self.rig_state._named_direction_modifiers:
            dir_effect = self.rig_state._named_direction_modifiers[self.name]
            dir_effect.request_stop(duration_ms, easing)



class NamedSpeedController:
    """Speed controller for named modifiers - only allows relative modifiers"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def to(self, value: float) -> 'PropertyEffectBuilder':
        """ERROR: Modifiers cannot use .to() - use rig.force() for absolute values"""
        raise ValueError(
            f"Modifiers can only use relative operations (.mul, .by, .div). "
            f"Use rig.force('{self.name}') for absolute values (.to)."
        )

    def by(self, delta: float) -> 'PropertyEffectBuilder':
        """Add delta to speed"""
        builder = PropertyEffectBuilder(self.rig_state, "speed", "by", delta)
        builder._effect_name = self.name
        return builder

    def mul(self, factor: float) -> 'PropertyEffectBuilder':
        """Multiply speed by factor"""
        builder = PropertyEffectBuilder(self.rig_state, "speed", "mul", factor)
        builder._effect_name = self.name
        return builder

    def div(self, divisor: float) -> 'PropertyEffectBuilder':
        """Divide speed by divisor"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide speed by zero")
        builder = PropertyEffectBuilder(self.rig_state, "speed", "div", divisor)
        builder._effect_name = self.name
        return builder



class NamedAccelController:
    """Accel controller for named modifiers - only allows relative modifiers"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def to(self, value: float) -> 'PropertyEffectBuilder':
        """ERROR: Modifiers cannot use .to() - use rig.force() for absolute values"""
        raise ValueError(
            f"Modifiers can only use relative operations (.mul, .by, .div). "
            f"Use rig.force('{self.name}') for absolute values (.to)."
        )

    def by(self, delta: float) -> 'PropertyEffectBuilder':
        """Add delta to accel"""
        builder = PropertyEffectBuilder(self.rig_state, "accel", "by", delta)
        builder._effect_name = self.name
        return builder

    def mul(self, factor: float) -> 'PropertyEffectBuilder':
        """Multiply accel by factor"""
        builder = PropertyEffectBuilder(self.rig_state, "accel", "mul", factor)
        builder._effect_name = self.name
        return builder

    def div(self, divisor: float) -> 'PropertyEffectBuilder':
        """Divide accel by divisor"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide accel by zero")
        builder = PropertyEffectBuilder(self.rig_state, "accel", "div", divisor)
        builder._effect_name = self.name
        return builder



class NamedDirectionController:
    """Direction controller for named modifiers - only allows relative modifiers"""
    def __init__(self, rig_state: 'RigState', name: str):
        self.rig_state = rig_state
        self.name = name

    def by(self, degrees: float) -> 'NamedDirectionByBuilder':
        """Rotate by relative angle in degrees (for modifiers)

        Positive = clockwise, Negative = counter-clockwise

        Examples:
            rig.modifier("drift").direction.by(15)              # Rotate 15° clockwise instantly
            rig.modifier("drift").direction.by(-45).over(500)   # Rotate 45° counter-clockwise over 500ms
        """
        return NamedDirectionByBuilder(self.rig_state, self.name, degrees)



class NamedDirectionByBuilder:
    """Builder for named direction modifiers - similar to DirectionByBuilder but for modifiers"""
    def __init__(self, rig_state: 'RigState', name: str, degrees: float):
        self.rig_state = rig_state
        self.name = name
        self.degrees = degrees
        self._easing = "linear"

        # Timing configuration
        self._in_duration_ms: Optional[float] = None
        self._hold_duration_ms: Optional[float] = None
        self._out_duration_ms: Optional[float] = None
        self._out_easing: str = "linear"
        self._use_rate: bool = False
        self._rate_degrees_per_second: Optional[float] = None

    def __del__(self):
        """Execute the operation when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass

    def _execute(self):
        """Execute the configured operation"""
        # Calculate duration from rate if needed
        in_duration_ms = self._in_duration_ms
        if self._use_rate and self._rate_degrees_per_second is not None:
            angle_deg = abs(self.degrees)
            if angle_deg < 0.1:
                in_duration_ms = 1  # Minimal duration for near-zero turns
            else:
                duration_sec = angle_deg / self._rate_degrees_per_second
                in_duration_ms = duration_sec * 1000

        # Create and register named direction effect
        dir_effect = DirectionEffect(self.degrees, self.name)
        dir_effect.in_duration_ms = in_duration_ms  # Can be None for instant application
        dir_effect.in_easing = self._easing
        dir_effect.hold_duration_ms = self._hold_duration_ms

        # PRD5: .hold() alone implies instant revert after hold period
        if self._hold_duration_ms is not None and self._out_duration_ms is None:
            dir_effect.out_duration_ms = 0
        else:
            dir_effect.out_duration_ms = self._out_duration_ms
        dir_effect.out_easing = self._out_easing

        self.rig_state.start()
        self.rig_state._direction_effects.append(dir_effect)

        # Track named modifier
        # Remove any existing modifier with same name
        if self.name in self.rig_state._named_direction_modifiers:
            old_effect = self.rig_state._named_direction_modifiers[self.name]
            if old_effect in self.rig_state._direction_effects:
                self.rig_state._direction_effects.remove(old_effect)
        self.rig_state._named_direction_modifiers[self.name] = dir_effect

    def over(self, duration_ms: float, easing: str = "linear") -> 'NamedDirectionByBuilder':
        """Apply change over duration"""
        self._in_duration_ms = duration_ms
        self._easing = easing
        return self

    def rate(self, degrees_per_second: float) -> 'NamedDirectionByBuilder':
        """Rotate by degrees at specified rate"""
        self._use_rate = True
        self._rate_degrees_per_second = degrees_per_second
        return self

    def hold(self, duration_ms: float) -> 'NamedDirectionByBuilder':
        """Hold rotation at full strength for duration"""
        self._hold_duration_ms = duration_ms
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> 'NamedDirectionByBuilder':
        """Revert to original direction - instant if duration=0, gradual otherwise"""
        self._out_duration_ms = duration_ms if duration_ms > 0 else 0
        self._out_easing = easing
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


class NamedModifierNamespace:
    """Namespace for rig.modifier operations"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, name: str) -> NamedModifierBuilder:
        """Create or access a named modifier"""
        return NamedModifierBuilder(self.rig_state, name)

    def stop_all(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Stop all named modifiers"""
        for effect in list(self.rig_state._named_modifiers.values()):
            effect.request_stop(duration_ms, easing)



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


# ============================================================================
# STATE ACCESSORS
# ============================================================================
