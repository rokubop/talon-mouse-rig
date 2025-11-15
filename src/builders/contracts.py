"""Abstract base classes and protocols for builder contracts"""

from abc import ABC, abstractmethod
from typing import Union, Optional, TYPE_CHECKING, TypeVar, Generic, Callable

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
    - .then() - callback at current stage in lifecycle
    """

    def over(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> T:
        """Transition/fade in over duration or at rate - default implementation with hooks

        Args:
            duration_ms: Duration in milliseconds (time-based)
            easing: Easing function name
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
        # Hook for pre-validation
        self._before_over(duration_ms, easing, rate_speed, rate_accel, rate_rotation)

        # Validate inputs - common validation for rate vs duration
        rate_provided = rate_speed is not None or rate_accel is not None or rate_rotation is not None
        if duration_ms is not None and rate_provided:
            raise ValueError("Cannot specify both duration_ms and rate parameters")

        # Hook for calculating duration from rate (subclasses can override)
        if rate_provided:
            duration_ms = self._calculate_over_duration_from_rate(
                rate_speed, rate_accel, rate_rotation
            )

        # Hook for storing the configuration (different builders use different field names)
        self._store_over_config(duration_ms, easing)

        self._current_stage = "after_forward"

        # Hook for post-processing (start rig, create objects, disable instant mode, etc.)
        self._after_over_configured(duration_ms, easing)

        return self

    def hold(self, duration_ms: float) -> T:
        """Sustain/hold for duration - default implementation with hooks"""
        # Hook for pre-validation (e.g., check if operation was called first)
        self._before_hold(duration_ms)

        self._hold_duration_ms = duration_ms
        self._current_stage = "after_hold"

        # Hook for post-processing (e.g., start rig ticking, create effects)
        self._after_hold_configured(duration_ms)

        return self

    def revert(
        self,
        duration_ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate_speed: Optional[float] = None,
        rate_accel: Optional[float] = None,
        rate_rotation: Optional[float] = None
    ) -> T:
        """Fade out/restore over duration or at rate - default implementation with hooks

        Args:
            duration_ms: Duration in milliseconds (time-based), 0 for instant
            easing: Easing function name
            rate_speed: Speed rate in units/second (rate-based)
            rate_accel: Acceleration rate in units/second² (rate-based)
            rate_rotation: Rotation rate in degrees/second (rate-based)
        """
        # Hook for pre-validation
        self._before_revert(duration_ms, easing, rate_speed, rate_accel, rate_rotation)

        # Validate inputs
        rate_provided = rate_speed is not None or rate_accel is not None or rate_rotation is not None
        if duration_ms is not None and rate_provided:
            raise ValueError("Cannot specify both duration_ms and rate parameters")

        # Hook for calculating duration from rate (subclasses can override)
        if rate_provided:
            duration_ms = self._calculate_revert_duration_from_rate(
                rate_speed, rate_accel, rate_rotation
            )

        self._out_duration_ms = duration_ms if duration_ms is not None and duration_ms > 0 else 0
        self._out_easing = easing
        self._current_stage = "after_revert"

        # Hook for post-processing
        self._after_revert_configured(duration_ms, easing)

        return self

    def then(self, callback: 'Callable') -> T:
        """Execute callback at current point in lifecycle chain - default implementation

        Can be called after .over(), .hold(), or .revert() to fire callback
        when that stage completes.

        Args:
            callback: Function to call when current stage completes
        """
        if self._current_stage == "after_forward":
            self._after_forward_callback = callback
        elif self._current_stage == "after_hold":
            self._after_hold_callback = callback
        elif self._current_stage == "after_revert":
            self._after_revert_callback = callback
        return self

    # ===== HOOKS - Override in subclasses for special behavior =====

    def _before_over(
        self,
        duration_ms: Optional[float],
        easing: str,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> None:
        """Hook called before over() configuration. Override for validation (e.g., check operation called first)."""
        pass

    def _calculate_over_duration_from_rate(
        self,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> float:
        """Hook for calculating over duration from rate. Override to calculate based on delta, distance, angle, etc."""
        # Default: assume reasonable duration
        if rate_speed is not None:
            return 500.0  # Default for speed-based
        elif rate_accel is not None:
            return 500.0  # Default for accel-based
        elif rate_rotation is not None:
            return 500.0  # Default for rotation-based
        return 500.0

    def _store_over_config(self, duration_ms: Optional[float], easing: str) -> None:
        """Hook for storing over configuration. Override to use different field names (_duration_ms vs _in_duration_ms)."""
        # Default: store in _in_duration_ms and _in_easing (for lifecycle-based builders)
        if not hasattr(self, '_in_duration_ms'):
            self._in_duration_ms = duration_ms
        else:
            self._in_duration_ms = duration_ms

        if not hasattr(self, '_in_easing'):
            self._in_easing = easing
        else:
            self._in_easing = easing

    def _after_over_configured(self, duration_ms: Optional[float], easing: str) -> None:
        """Hook called after over() configuration. Override to start rig, disable instant mode, create objects, etc."""
        pass

    def _before_hold(self, duration_ms: float) -> None:
        """Hook called before hold() configuration. Override for validation."""
        pass

    def _after_hold_configured(self, duration_ms: float) -> None:
        """Hook called after hold() configuration. Override to start rig, create effects, etc."""
        pass

    def _before_revert(
        self,
        duration_ms: Optional[float],
        easing: str,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> None:
        """Hook called before revert() configuration. Override for validation."""
        pass

    def _calculate_revert_duration_from_rate(
        self,
        rate_speed: Optional[float],
        rate_accel: Optional[float],
        rate_rotation: Optional[float]
    ) -> float:
        """Hook for calculating revert duration from rate. Override to calculate based on current value."""
        return 500  # Default fallback

    def _after_revert_configured(self, duration_ms: Optional[float], easing: str) -> None:
        """Hook called after revert() configuration. Override to start rig, create effects, etc."""
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


class AutoExecuteBuilder(ABC):
    """
    Base class for builders that auto-execute on cleanup.

    Provides the common __del__ → _execute() pattern with error handling.
    Subclasses must implement _execute() to define their execution logic.
    """

    def __del__(self):
        """Execute when builder goes out of scope"""
        try:
            self._execute()
        except:
            pass  # Silently ignore errors during cleanup

    @abstractmethod
    def _execute(self):
        """Override this to define execution behavior"""
        pass


class PropertyChainingContract:
    """
    Unified property chaining via __getattr__ for all builders.

    Enables fluent chaining like: rig.speed(100).accel(50).pos.to(0, 0)

    Behavior:
    - If timing configured (.over, .hold, .revert): raise error (can't chain)
    - If no timing: execute immediately and return next controller
    - Non-chainable properties: raise helpful error
    - Unknown attributes: raise error with available methods

    Subclasses must implement:
    - _has_timing_configured() -> bool
    - _execute_for_chaining() -> None (prepare and execute immediately)
    - rig_state attribute
    """

    def __getattr__(self, name: str):
        """Enable property chaining or provide helpful error messages"""
        # Common rig properties that can be chained (if no timing configured)
        if name in ['speed', 'accel', 'pos', 'direction']:
            # Check if any timing has been configured
            if self._has_timing_configured():
                raise AttributeError(
                    f"Cannot chain .{name} after using timing methods (.over, .hold, .revert).\n\n"
                    "Use separate statements instead."
                )

            # Execute current operation immediately
            self._execute_for_chaining()

            # Return the appropriate property controller for chaining
            if name == 'speed':
                from .base_properties.speed import SpeedController
                return SpeedController(self.rig_state)
            elif name == 'accel':
                from .base_properties.accel import AccelController
                return AccelController(self.rig_state)
            elif name == 'pos':
                from .base_properties.position import PositionController
                return PositionController(self.rig_state)
            elif name == 'direction':
                from .base_properties.direction import DirectionController
                return DirectionController(self.rig_state)

        elif name in ['stop', 'modifier', 'force', 'bake', 'state', 'base']:
            raise AttributeError(
                f"Cannot chain '{name}' after property operation.\n\n"
                "Use separate statements instead."
            )

        # Unknown attribute
        from ..core import _error_unknown_builder_attribute
        raise AttributeError(_error_unknown_builder_attribute(
            self.__class__.__name__,
            name,
            'over, hold, revert, then'
        ))

    @abstractmethod
    def _has_timing_configured(self) -> bool:
        """Check if any timing has been configured (over/hold/revert)"""
        pass

    @abstractmethod
    def _execute_for_chaining(self) -> None:
        """Execute immediately for property chaining"""
        pass


class TransitionBasedBuilder(AutoExecuteBuilder):
    """
    Base class for builders that use transition vs instant execution pattern.

    Implements the common flow:
    1. Check if has transition timing
    2. Either create transition or apply instantly
    3. Register with rig_state
    4. Start rig
    5. Handle callbacks

    Subclasses provide specific implementations via abstract methods.
    """

    def _execute(self):
        """Execute the configured operation - transition or instant"""
        if self._has_transition():
            self._execute_transition()
        elif self._has_instant():
            self._execute_instant()

    @abstractmethod
    def _has_transition(self) -> bool:
        """Check if this builder should create a transition"""
        pass

    @abstractmethod
    def _has_instant(self) -> bool:
        """Check if this builder should execute instantly"""
        pass

    @abstractmethod
    def _execute_transition(self):
        """Execute with transition/animation"""
        pass

    @abstractmethod
    def _execute_instant(self):
        """Execute instantly without transition"""
        pass
