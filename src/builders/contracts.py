"""Abstract base classes and protocols for builder contracts"""

from abc import ABC, abstractmethod
from typing import Union, Optional, TYPE_CHECKING, TypeVar, Generic

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
    - .over() - transition/fade in over duration or at rate
    - .hold() - sustain/hold for duration
    - .revert() - fade out/restore over duration or at rate
    """

    @abstractmethod
    def over(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> T:
        """Transition/fade in over duration or at rate

        Args:
            duration_ms: Duration in milliseconds (time-based)
            easing: Easing function name
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
        pass

    @abstractmethod
    def hold(self, duration_ms: float) -> T:
        """Sustain/hold for duration"""
        pass

    @abstractmethod
    def revert(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> T:
        """Fade out/restore over duration or at rate

        Args:
            duration_ms: Duration in milliseconds (time-based), 0 for instant
            easing: Easing function name
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
        pass


class StoppableContract(ABC):
    """
    Contract for entities that can be stopped.

    Applies to:
    - Rig (stop all motion)
    - Effect namespaces (stop specific/all effects)
    - Force namespaces (stop specific/all forces)
    """

    @abstractmethod
    def stop(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> None:
        """Stop/cancel the entity

        Args:
            duration_ms: Optional fade-out duration. None = immediate stop
            easing: Easing function for gradual stop
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
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
    Combined contract for property BUILDERS that support both operations and timing.

    This is the full contract for builders like:
    - PropertyEffectBuilder (returned from controllers)
    - EffectSpeedBuilder, EffectAccelBuilder (effects)
    - NamedForceSpeedController, NamedForceAccelController (forces)
    """
    pass
