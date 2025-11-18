"""Type contracts and protocols for mouse rig V2

This is the single source of truth for all interfaces in the system.
"""

from typing import Protocol, Callable, Any, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from .core import Vec2


class PropertyOperations(Protocol):
    """Contract for property operations (to, add, sub, mul, div)"""
    def to(self, *args) -> 'RigBuilder': ...
    def add(self, *args) -> 'RigBuilder': ...
    def by(self, *args) -> 'RigBuilder': ...  # alias for add
    def sub(self, *args) -> 'RigBuilder': ...
    def mul(self, value: float) -> 'RigBuilder': ...
    def div(self, value: float) -> 'RigBuilder': ...


class LifecycleMethods(Protocol):
    """Contract for lifecycle methods (over, hold, revert, then)"""
    def over(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp"
    ) -> 'RigBuilder': ...

    def hold(self, ms: float) -> 'RigBuilder': ...

    def revert(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp"
    ) -> 'RigBuilder': ...

    def then(self, callback: Callable) -> 'RigBuilder': ...


class BehaviorMethods(Protocol):
    """Contract for behavior modes (stack, replace, queue, etc.)"""
    def stack(self, max_count: Optional[int] = None) -> 'RigBuilder': ...
    def replace(self) -> 'RigBuilder': ...
    def queue(self) -> 'RigBuilder': ...
    def extend(self) -> 'RigBuilder': ...
    def throttle(self, ms: float) -> 'RigBuilder': ...
    def ignore(self) -> 'RigBuilder': ...


class Updatable(ABC):
    """Interface for objects that update each frame"""
    @abstractmethod
    def update(self, dt: float) -> bool:
        """Update state. Returns True if still active, False if complete."""
        pass


class LifecyclePhase:
    """Represents a phase in the lifecycle (over/hold/revert)"""
    OVER = "over"
    HOLD = "hold"
    REVERT = "revert"


class BuilderConfig:
    """Configuration collected by RigBuilder during fluent API calls"""
    def __init__(self):
        # Property and operation
        self.property: Optional[str] = None  # pos, speed, direction, accel
        self.operator: Optional[str] = None  # to, by, add, sub, mul, div
        self.value: Any = None

        # Identity
        self.tag_name: Optional[str] = None

        # Behavior
        self.behavior: Optional[str] = None  # stack, replace, queue, extend, throttle, ignore
        self.behavior_args: tuple = ()

        # Lifecycle timing
        self.over_ms: Optional[float] = None
        self.over_easing: str = "linear"
        self.over_rate: Optional[float] = None
        self.over_interpolation: str = "lerp"

        self.hold_ms: Optional[float] = None

        self.revert_ms: Optional[float] = None
        self.revert_easing: str = "linear"
        self.revert_rate: Optional[float] = None
        self.revert_interpolation: str = "lerp"

        # Callbacks (stage -> callback)
        self.then_callbacks: list[tuple[str, Callable]] = []

        # Persistence
        self.bake_value: Optional[bool] = None

    def is_anonymous(self) -> bool:
        """Check if this builder is anonymous (auto-generated tag)"""
        return self.tag_name is not None and self.tag_name.startswith("__anon_")

    def get_effective_behavior(self) -> str:
        """Get behavior with defaults applied"""
        if self.behavior is not None:
            return self.behavior
        # Default to stack for all properties
        return "stack"

    def get_effective_bake(self) -> bool:
        """Get bake setting with defaults applied"""
        if self.bake_value is not None:
            return self.bake_value
        # Default: anonymous bakes, tagged doesn't
        # Tagged builders must be explicitly reverted or baked
        return self.is_anonymous()
