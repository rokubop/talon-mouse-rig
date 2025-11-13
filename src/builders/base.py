"""Base builders - re-exports from split modules for backwards compatibility

This module maintains compatibility with existing imports while allowing
the codebase to be organized into focused, smaller modules.
"""

# Property builders (speed, accel)
from .property import (
    PropertyEffectBuilder,
    PropertyRateNamespace,
    SpeedBuilder,
    SpeedController,
    AccelController,
)

# Direction builders
from .direction import (
    DirectionBuilder,
    DirectionByBuilder,
    DirectionController,
)

# Position builders
from .position import (
    PositionController,
    PositionBuilder,
)

__all__ = [
    # Property
    "PropertyEffectBuilder",
    "PropertyRateNamespace",
    "SpeedBuilder",
    "SpeedController",
    "AccelController",
    # Direction
    "DirectionBuilder",
    "DirectionByBuilder",
    "DirectionController",
    # Position
    "PositionController",
    "PositionBuilder",
]
