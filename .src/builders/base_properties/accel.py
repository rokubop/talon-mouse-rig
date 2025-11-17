"""Accel builder for base rig - acceleration control"""

from typing import TYPE_CHECKING
from .shared import SpeedAccelBuilder
from ..contracts import OperationsContract

if TYPE_CHECKING:
    from ...state import RigState


class AccelController(OperationsContract['SpeedAccelBuilder']):
    """Controller for acceleration operations (accessed via rig.accel)"""
    def __init__(self, rig_state: 'RigState'):
        self.rig_state = rig_state

    def __call__(self, value: float) -> SpeedAccelBuilder:
        """Set acceleration instantly or return builder for transitions/effects"""
        # Immediate set
        self.rig_state._accel = value
        self.rig_state.start()
        return SpeedAccelBuilder(self.rig_state, "accel", "to", value, instant_done=True)

    def to(self, value: float) -> SpeedAccelBuilder:
        """Set accel to absolute value (can use with .over(), .hold(), .revert())"""
        return SpeedAccelBuilder(self.rig_state, "accel", "to", value)

    def add(self, delta: float) -> SpeedAccelBuilder:
        """Add delta to current accel"""
        return SpeedAccelBuilder(self.rig_state, "accel", "by", delta)

    def by(self, delta: float) -> SpeedAccelBuilder:
        """Add delta to accel (alias for .add())"""
        return SpeedAccelBuilder(self.rig_state, "accel", "by", delta)

    def sub(self, delta: float) -> SpeedAccelBuilder:
        """Subtract from current accel"""
        return SpeedAccelBuilder(self.rig_state, "accel", "by", -delta)

    def mul(self, factor: float) -> SpeedAccelBuilder:
        """Multiply accel by factor (can use with .over(), .hold(), .revert())"""
        return SpeedAccelBuilder(self.rig_state, "accel", "mul", factor)

    def div(self, divisor: float) -> SpeedAccelBuilder:
        """Divide accel by divisor (can use with .over(), .hold(), .revert())"""
        if abs(divisor) < 1e-10:
            raise ValueError("Cannot divide accel by zero")
        return SpeedAccelBuilder(self.rig_state, "accel", "div", divisor)
