"""Abstract base classes and protocols for builder contracts"""

from abc import ABC, abstractmethod
from typing import Union, TYPE_CHECKING, TypeVar, Generic

if TYPE_CHECKING:
    from ..state import RigState
    from ..core import Vec2

# Type variable for self-return types
T = TypeVar('T')


class OperationsContract(ABC, Generic[T]):
    """
    Contract for classes that support standard operations.

    All property builders (base, effect, force) must implement:
    - () - shorthand for .to()
    - .to(value) - set absolute value
    - .add(delta) - add delta
    - .by(delta) - alias for .add()
    - .sub(delta) - subtract
    - .mul(factor) - multiply
    - .div(divisor) - divide
    """

    @abstractmethod
    def __call__(self, value: Union[float, 'Vec2']) -> T:
        """Shorthand for .to() - set absolute value"""
        pass

    @abstractmethod
    def to(self, value: Union[float, 'Vec2']) -> T:
        """Set absolute value"""
        pass

    @abstractmethod
    def add(self, value: Union[float, 'Vec2']) -> T:
        """Add delta"""
        pass

    @abstractmethod
    def by(self, value: Union[float, 'Vec2']) -> T:
        """Add delta (alias for .add())"""
        pass

    @abstractmethod
    def sub(self, value: Union[float, 'Vec2']) -> T:
        """Subtract delta"""
        pass

    @abstractmethod
    def mul(self, factor: float) -> T:
        """Multiply by factor"""
        pass

    @abstractmethod
    def div(self, divisor: float) -> T:
        """Divide by divisor"""
        pass


class TimingMethodsContract(ABC, Generic[T]):
    """
    Contract for classes that support timing methods.

    All builders with animations/transitions must implement:
    - .over(duration_ms, easing) - transition/fade in over duration
    - .hold(duration_ms) - sustain/hold for duration
    - .revert(duration_ms, easing) - fade out/restore over duration
    - .stop() - stop/cancel (optional depending on entity type)
    """

    @abstractmethod
    def over(self, duration_ms: float, easing: str = "linear") -> T:
        """Transition/fade in over duration"""
        pass

    @abstractmethod
    def hold(self, duration_ms: float) -> T:
        """Sustain/hold for duration"""
        pass

    @abstractmethod
    def revert(self, duration_ms: float = 0, easing: str = "linear") -> T:
        """Fade out/restore over duration"""
        pass


class BasePropertyContract(ABC, Generic[T]):
    """
    Contract for base properties (speed, accel, direction, pos).

    Base properties are fundamental rig properties that can be:
    - Modified directly via operations
    - Modified temporarily via effects
    - Influenced by forces
    - Transitioned over time
    """

    @abstractmethod
    def __init__(self, rig_state: 'RigState'):
        """Initialize with reference to rig state"""
        pass


class PropertyOperationsContract(OperationsContract[T], TimingMethodsContract[T], ABC):
    """
    Combined contract for property builders that support both operations and timing.

    This is the full contract for property builders like:
    - SpeedController, AccelController (base properties)
    - EffectSpeedBuilder, EffectAccelBuilder (effects)
    - NamedForceSpeedController, NamedForceAccelController (forces)
    """
    pass
