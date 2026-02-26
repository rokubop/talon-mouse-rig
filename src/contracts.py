"""Mouse-specific contracts - extends rig-core BaseBuilderConfig

Imports shared validation/types from rig-core. Adds mouse-specific
constants, validation, and MouseBuilderConfig subclass.
"""

from typing import Protocol, Callable, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Vec2

# ============================================================================
# MOUSE-SPECIFIC CONSTANTS (stay here)
# ============================================================================

VALID_PROPERTIES = ['pos', 'speed', 'direction', 'vector', 'scroll_pos']

VALID_OPERATORS = {
    'speed': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'direction': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'pos': ['to', 'add', 'by', 'sub', 'bake'],
    'vector': ['to', 'add', 'by', 'sub', 'bake'],
    'scroll_pos': ['add', 'by'],
}

RESERVED_LAYERS = {}

VALID_RIG_METHODS = [
    'layer', 'api', 'stop', 'reverse', 'bake',
]

VALID_RIG_PROPERTIES = [
    'pos', 'speed', 'direction', 'vector',
    'scroll', 'move',
    'state', 'base',
    'stack', 'replace', 'queue', 'throttle', 'debounce',
]

VALID_BUILDER_METHODS = [
    'over', 'hold', 'revert', 'then', 'bake', 'api',
    'stack', 'replace', 'queue', 'throttle', 'debounce',
    'reverse', 'copy', 'emit',
    'max', 'min',
]

VALID_LAYER_STATE_ATTRS = [
    'prop', 'mode', 'operator', 'current', 'target', 'time_alive', 'time_left'
]


# ============================================================================
# SHARED IMPORTS — set by _build_classes()
# ============================================================================

BaseBuilderConfig = None
LifecyclePhase = None
LayerType = None
ConfigError = None
RigUsageError = None
RigAttributeError = None
validate_timing = None
validate_has_operation = None
find_closest_match = None
suggest_correction = None
format_validation_error = None
METHOD_SIGNATURES = None
VALID_MODES = None
VALID_EASINGS = None
VALID_INTERPOLATIONS = None
VALID_BEHAVIORS = None
PARAMETER_SUGGESTIONS = None

# Mouse-specific config — set by _build_classes()
BuilderConfig = None


def _build_classes(core):
    global BaseBuilderConfig, LifecyclePhase, LayerType, ConfigError, RigUsageError, RigAttributeError
    global validate_timing, validate_has_operation, find_closest_match, suggest_correction, format_validation_error
    global METHOD_SIGNATURES, VALID_MODES, VALID_EASINGS, VALID_INTERPOLATIONS, VALID_BEHAVIORS, PARAMETER_SUGGESTIONS
    global BuilderConfig

    BaseBuilderConfig = core.BaseBuilderConfig
    LifecyclePhase = core.LifecyclePhase
    LayerType = core.LayerType
    ConfigError = core.ConfigError
    RigUsageError = core.RigUsageError
    RigAttributeError = core.RigAttributeError
    validate_timing = core.validate_timing
    validate_has_operation = core.validate_has_operation
    find_closest_match = core.find_closest_match
    suggest_correction = core.suggest_correction
    format_validation_error = core.format_validation_error
    METHOD_SIGNATURES = core.METHOD_SIGNATURES
    VALID_MODES = core.VALID_MODES
    VALID_EASINGS = core.VALID_EASINGS
    VALID_INTERPOLATIONS = core.VALID_INTERPOLATIONS
    VALID_BEHAVIORS = core.VALID_BEHAVIORS
    PARAMETER_SUGGESTIONS = core.PARAMETER_SUGGESTIONS

    class _MouseBuilderConfig(core.BaseBuilderConfig):
        """Mouse-specific BuilderConfig with device, input_type, movement_type, etc."""
        def __init__(self):
            super().__init__()
            # Device and input_type
            self.device: str = "mouse"
            self.input_type: str = "move"  # 'move' or 'scroll'

            # Movement type (absolute vs relative positioning)
            self.movement_type: str = "relative"
            self._movement_type_explicit: bool = False

            # Scroll options
            self.by_lines: bool = True

            # API override (set via .api())
            self.api_override: Optional[str] = None

            # Execution mode
            self.is_synchronous: bool = False

        def validate_property_operator(self, mark_invalid: Optional[Callable[[], None]] = None) -> None:
            """Validate that operator is valid for the property (mouse-specific)"""
            if not self.property or not self.operator:
                return

            if self.property not in VALID_PROPERTIES:
                if mark_invalid:
                    mark_invalid()
                valid_str = ', '.join(repr(p) for p in VALID_PROPERTIES)
                raise core.ConfigError(
                    f"Invalid property: {repr(self.property)}\n"
                    f"Valid properties: {valid_str}"
                )

            valid_ops = VALID_OPERATORS.get(self.property, [])
            if self.operator not in valid_ops:
                if mark_invalid:
                    mark_invalid()
                valid_str = ', '.join(repr(op) for op in valid_ops)
                raise core.ConfigError(
                    f"Invalid operator {repr(self.operator)} for property {repr(self.property)}\n"
                    f"Valid operators for {self.property}: {valid_str}"
                )

            # Validate direction values
            if self.property == "direction" and self.operator in ("to", "add", "by"):
                if isinstance(self.value, (tuple, list)) and len(self.value) >= 2:
                    x, y = self.value[0], self.value[1]
                    if x == 0 and y == 0:
                        if mark_invalid:
                            mark_invalid()
                        raise core.ConfigError(
                            "Invalid direction vector (0, 0).\n\n"
                            "Direction cannot be a zero vector - it must have a magnitude.\n\n"
                            "To stop movement, use one of these instead:\n"
                            "  rig.stop()             # Stop all movement instantly\n"
                            "  rig.stop(500)          # Stop with 500ms transition\n"
                            "  rig.speed.to(0)        # Set speed to zero\n"
                            "  rig.layer('name').revert()  # Revert a layer"
                        )

            # Validate vector values
            if self.property == "vector" and self.operator in ("to", "add", "by"):
                if isinstance(self.value, (tuple, list)) and len(self.value) >= 2:
                    x, y = self.value[0], self.value[1]
                    if x == 0 and y == 0:
                        if mark_invalid:
                            mark_invalid()
                        raise core.ConfigError(
                            "Invalid vector (0, 0).\n\n"
                            "Vector cannot be a zero vector - it represents velocity (speed + direction).\n\n"
                            "To stop movement, use one of these instead:\n"
                            "  rig.stop()             # Stop all movement instantly\n"
                            "  rig.stop(500)          # Stop with 500ms transition\n"
                            "  rig.speed.to(0)        # Set speed to zero\n"
                            "  rig.layer('name').revert()  # Revert a layer"
                        )

    BuilderConfig = _MouseBuilderConfig


# ============================================================================
# PROTOCOLS (stay here — mouse-specific)
# ============================================================================

class PropertyOperations(Protocol):
    """Contract for property operations (to, add, sub, mul, div)"""
    def to(self, *args): ...
    def add(self, *args): ...
    def by(self, *args): ...
    def sub(self, *args): ...
    def mul(self, value: float): ...
    def div(self, value: float): ...


class LifecycleMethods(Protocol):
    """Contract for lifecycle methods (over, hold, revert, then)"""
    def over(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp"
    ): ...

    def hold(self, ms: float): ...

    def revert(
        self,
        ms: Optional[float] = None,
        easing: str = "linear",
        *,
        rate: Optional[float] = None,
        interpolation: str = "lerp"
    ): ...

    def then(self, callback: Callable): ...


class BehaviorMethods(Protocol):
    """Contract for behavior modes (stack, replace, queue, etc.)"""
    def stack(self, max: Optional[int] = None): ...
    def reset(self): ...
    def queue(self): ...
    def throttle(self, ms: Optional[float] = None): ...


def validate_api_has_operation(config, mark_invalid=None):
    """Validate that api() is not called alone without an operation"""
    if config.api_override is not None and config.property is None and config.operator is None:
        if mark_invalid:
            mark_invalid()
        raise ConfigError(
            "api() must be chained with an operation - it cannot be used alone.\n\n"
            "The api() method is for overriding the mouse API for specific one-line operations:\n\n"
            "  ✓ rig.api(\"talon\").pos.by(100, 0)\n"
            "  ✓ rig.pos.by(100, 0).api(\"talon\")\n"
            "  ✗ rig.api(\"talon\")  # No operation specified\n\n"
            "To change the default mouse API globally, use Talon settings:\n\n"
            "  # In your .talon or .py file:\n"
            "  settings():\n"
            "    user.mouse_rig_api = \"platform\"  # For relative movement\n"
            "  # Note: Absolute positioning (pos.to) always uses Talon"
        )
