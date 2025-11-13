"""Accel builder for base rig - acceleration control"""

from typing import TYPE_CHECKING
from .shared import PropertyEffectBuilder
from ..contracts import PropertyOperationsContract

if TYPE_CHECKING:
    from ...state import RigState


class AccelController(PropertyOperationsContract['PropertyEffectBuilder']):
    """Controller for acceleration operations (accessed via rig.accel)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, value: float) -> PropertyEffectBuilder:
        """Set acceleration instantly or return builder for transitions/effects"""
        # Immediate set
        self.rig_state._accel = value
        self.rig_state.start()
        return PropertyEffectBuilder(self.rig_state, "accel", "to", value, instant_done=True)

    def to(self, value: float) -> PropertyEffectBuilder:
        """Set accel to absolute value (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "accel", "to", value)

    def add(self, delta: float) -> PropertyEffectBuilder:
        """Add delta to current accel"""
        return PropertyEffectBuilder(self.rig_state, "accel", "by", delta)

    def by(self, delta: float) -> PropertyEffectBuilder:
        """Add delta to accel (alias for .add())"""
        return PropertyEffectBuilder(self.rig_state, "accel", "by", delta)

    def sub(self, delta: float) -> PropertyEffectBuilder:
        """Subtract from current accel"""
        return PropertyEffectBuilder(self.rig_state, "accel", "by", -delta)

    def mul(self, factor: float) -> PropertyEffectBuilder:
        """Multiply accel by factor (can use with .over(), .hold(), .revert())"""
        return PropertyEffectBuilder(self.rig_state, "accel", "mul", factor)

    def div(self, divisor: float) -> PropertyEffectBuilder:
        """Divide accel by divisor (can use with .over(), .hold(), .revert())"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide accel by zero")
        return PropertyEffectBuilder(self.rig_state, "accel", "div", divisor)
