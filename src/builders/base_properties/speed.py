"""Speed controller for base rig - speed control"""

from typing import TYPE_CHECKING
from .shared import PropertyEffectBuilder
from ..contracts import OperationsContract

if TYPE_CHECKING:
    from ...state import RigState


class SpeedController(OperationsContract['PropertyEffectBuilder']):
    """Controller for speed operations (accessed via rig.speed)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, value: float) -> PropertyEffectBuilder:
        """Set speed instantly or return builder for .over()"""
        # Immediate execution, then return builder for potential .over()/.hold()/.revert()
        self.rig_state._speed = max(0.0, value)
        max_speed = self.rig_state.limits_max_speed
        if max_speed is not None:
            self.rig_state._speed = min(self.rig_state._speed, max_speed)
        self.rig_state.start()
        return PropertyEffectBuilder(self.rig_state, "speed", "to", value, instant_done=True)

    def add(self, delta: float) -> PropertyEffectBuilder:
        """Add delta to current speed"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", delta)

    def sub(self, delta: float) -> PropertyEffectBuilder:
        """Subtract from current speed"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", -delta)

    def mul(self, factor: float) -> PropertyEffectBuilder:
        """Multiply speed by factor"""
        return PropertyEffectBuilder(self.rig_state, "speed", "mul", factor)

    def div(self, divisor: float) -> PropertyEffectBuilder:
        """Divide speed by divisor"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide speed by zero")
        return PropertyEffectBuilder(self.rig_state, "speed", "div", divisor)

    def to(self, value: float) -> PropertyEffectBuilder:
        """Set speed to absolute value (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "to", value)

    def by(self, delta: float) -> PropertyEffectBuilder:
        """Add delta to speed (alias for .add())"""
        return PropertyEffectBuilder(self.rig_state, "speed", "by", delta)
