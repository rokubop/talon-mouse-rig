"""Type contracts and protocols for mouse rig V2

This is the single source of truth for all interfaces in the system.
"""

from typing import Protocol, Callable, Any, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from .core import Vec2

VALID_PROPERTIES = ['pos', 'speed', 'direction', 'vector']

VALID_OPERATORS = {
    'speed': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'direction': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'pos': ['to', 'add', 'by', 'sub', 'bake'],
    'vector': ['to', 'add', 'by', 'sub', 'bake']
}

VALID_MODES = ['offset', 'override', 'scale']

# ============================================================================
# LAYER CLASSIFICATION
# ============================================================================
#
# There are two fundamental layer types:
#
# 1. BASE LAYERS: "base.{property}" (e.g., "base.speed", "base.direction")
#    - Direct property operations without modes (e.g., rig.speed.to(10))
#    - Always auto-generated, never user-named
#    - Transient: auto-bakes when animation completes
#
# 2. MODIFIER LAYERS: Use modes (.offset/.override/.scale)
#    - Can be auto-named or user-named:
#      a) Auto-named: "{property}.{mode}" (e.g., "speed.offset", "pos.override")
#         - Generated when mode used without explicit name
#         - Persistent: does NOT auto-bake
#      b) User-named: Custom name (e.g., "boost", "cap")
#         - User provides explicit name with mode
#         - User has full lifecycle control
#
RESERVED_LAYERS = {}

def is_base_layer(layer_name: str) -> bool:
    """Check if layer is a base layer (transient, auto-bakes)

    Base layers are auto-generated for operations without modes.
    Pattern: 'base.{property}' (e.g., 'base.speed', 'base.direction')
    """
    return layer_name is not None and layer_name.startswith("base.")

def is_modifier_layer(layer_name: str) -> bool:
    """Check if layer is a modifier layer (uses mode, persistent)

    Modifier layers use modes (.offset/.override/.scale) and can be
    either auto-named or user-named.
    """
    if layer_name is None:
        return False
    # Auto-named modifier: property.mode pattern
    parts = layer_name.split(".")
    if len(parts) == 2:
        prop, mode = parts
        if prop in ["pos", "speed", "direction", "vector"] and mode in ["offset", "override", "scale"]:
            return True
    # User-named modifiers are detected by having a mode in config
    # (checked elsewhere via BuilderConfig.mode)
    return False

def is_auto_named_modifier(layer_name: str) -> bool:
    """Check if layer is an auto-named modifier (e.g., 'speed.offset')

    Auto-named modifiers are generated when using modes without explicit names.
    They persist until explicitly removed.
    """
    if layer_name is None:
        return False
    parts = layer_name.split(".")
    if len(parts) == 2:
        prop, mode = parts
        return prop in ["pos", "speed", "direction", "vector"] and mode in ["offset", "override", "scale"]
    return False

def is_implicit_layer(layer_name: str) -> bool:
    """Alias for is_auto_named_modifier() for backwards compatibility"""
    return is_auto_named_modifier(layer_name)

VALID_EASINGS = [
    'linear',
    'ease_in', 'ease_out', 'ease_in_out',
    'ease_in2', 'ease_out2', 'ease_in_out2',
    'ease_in3', 'ease_out3', 'ease_in_out3',
    'ease_in4', 'ease_out4', 'ease_in_out4',
]
VALID_INTERPOLATIONS = ['lerp', 'slerp', 'linear']
VALID_BEHAVIORS = ['stack', 'replace', 'queue', 'throttle', 'debounce']

METHOD_SIGNATURES = {
    'over': {
        'params': ['ms', 'easing', 'rate', 'interpolation'],
        'signature': "over(ms=None, easing='linear', *, rate=None, interpolation='lerp')",
        'validations': {
            'easing': ('easing', VALID_EASINGS),
            'interpolation': ('interpolation', VALID_INTERPOLATIONS)
        }
    },
    'revert': {
        'params': ['ms', 'easing', 'rate', 'interpolation'],
        'signature': "revert(ms=None, easing='linear', *, rate=None, interpolation='lerp')",
        'validations': {
            'easing': ('easing', VALID_EASINGS),
            'interpolation': ('interpolation', VALID_INTERPOLATIONS)
        }
    },
    'hold': {
        'params': ['ms'],
        'signature': 'hold(ms)',
        'validations': {}
    },
    'then': {
        'params': ['callback'],
        'signature': 'then(callback)',
        'validations': {}
    },
    'stop': {
        'params': ['transition_ms', 'easing'],
        'signature': "stop(transition_ms=None, easing='linear')",
        'validations': {
            'easing': ('easing', VALID_EASINGS)
        }
    },
    'bake': {
        'params': ['value'],
        'signature': 'bake(value=True)',
        'validations': {}
    }
}

# Add behavior methods
for behavior in VALID_BEHAVIORS:
    if behavior in ('throttle', 'debounce'):
        METHOD_SIGNATURES[behavior] = {
            'params': ['ms'],
            'signature': f'{behavior}(ms=None)',
            'validations': {}
        }
    elif behavior == 'stack':
        METHOD_SIGNATURES[behavior] = {
            'params': ['max'],
            'signature': f'{behavior}(max=None)',
            'validations': {}
        }
    else:
        METHOD_SIGNATURES[behavior] = {
            'params': [],
            'signature': f'{behavior}()',
            'validations': {}
        }

# Common typos and their corrections
PARAMETER_SUGGESTIONS = {
    'ease': 'easing',
    'duration': 'ms',
    'time': 'ms',
    'milliseconds': 'ms',
    'millis': 'ms',
    'transition': 'ms',
}

# Valid method/property names for Rig class
VALID_RIG_METHODS = [
    'layer', 'api', 'stop', 'reverse', 'bake',
]

VALID_RIG_PROPERTIES = [
    'pos', 'speed', 'direction', 'vector',
    'state', 'base',
    'stack', 'replace', 'queue', 'throttle', 'debounce',
]

VALID_BUILDER_METHODS = [
    'over', 'hold', 'revert', 'then', 'bake', 'api',
    'stack', 'replace', 'queue', 'throttle', 'debounce',
]

# Valid LayerState attributes (properties and methods)
VALID_LAYER_STATE_ATTRS = [
    'prop', 'mode', 'operator', 'value', 'target', 'time_alive', 'time_left'
]


# ============================================================================
# VALIDATION ERROR HANDLING
# ============================================================================

class ConfigError(TypeError):
    """Configuration validation error with rich formatting

    Automatically stops the mouse rig to prevent runaway movement
    when validation fails during command building.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Auto-stop rig on validation errors to prevent runaway movement
        try:
            from talon import actions
            actions.user.mouse_rig_stop()
        except Exception:
            # Fail silently if rig unavailable
            pass


class RigAttributeError(AttributeError):
    """Attribute error with helpful suggestions"""
    pass


class RigUsageError(Exception):
    """Error for incorrect API usage"""
    pass


def find_closest_match(name: str, valid_options: list[str], max_distance: int = 2) -> Optional[str]:
    """Find closest match using simple edit distance

    Args:
        name: The invalid name
        valid_options: List of valid options
        max_distance: Maximum Levenshtein distance to consider a match

    Returns:
        Closest matching option or None
    """
    name_lower = name.lower()
    best_match = None
    best_distance = max_distance + 1

    for option in valid_options:
        option_lower = option.lower()

        # Check for substring match first
        if name_lower in option_lower or option_lower in name_lower:
            return option

        # Simple Levenshtein distance
        distance = _levenshtein(name_lower, option_lower)
        if distance < best_distance:
            best_distance = distance
            best_match = option

    return best_match if best_distance <= max_distance else None


def _levenshtein(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings"""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def suggest_correction(provided: str, valid_options: list[str]) -> Optional[str]:
    """Find close match for typos using simple heuristics"""
    provided_lower = provided.lower()

    # Check parameter suggestions first
    if provided_lower in PARAMETER_SUGGESTIONS:
        return PARAMETER_SUGGESTIONS[provided_lower]

    # Check for close matches in valid options
    for option in valid_options:
        if provided_lower in option.lower() or option.lower() in provided_lower:
            return option

    return None


def format_validation_error(
    method: str,
    unknown_params: Optional[list[str]] = None,
    invalid_values: Optional[dict[str, tuple[Any, list]]] = None,
    provided_kwargs: Optional[dict] = None
) -> str:
    """Format a comprehensive validation error message

    Args:
        method: Name of the method
        unknown_params: List of unknown parameter names
        invalid_values: Dict of {param: (value, valid_options)}
        provided_kwargs: All kwargs that were provided
    """
    schema = METHOD_SIGNATURES.get(method, {})
    signature = schema.get('signature', f'{method}(...)')

    msg = f"{method}() validation failed\n"
    msg += f"\nSignature: {signature}\n"

    if provided_kwargs:
        provided_str = ', '.join(f"{k}={repr(v)}" for k, v in provided_kwargs.items())
        msg += f"You provided: {provided_str}\n"

    if unknown_params:
        msg += f"\nUnknown parameter(s): {', '.join(repr(p) for p in unknown_params)}\n"

        # Suggest corrections
        suggestions = []
        valid_params = schema.get('params', [])
        for param in unknown_params:
            suggestion = suggest_correction(param, valid_params)
            if suggestion:
                suggestions.append(f"  - '{param}' → '{suggestion}'")

        if suggestions:
            msg += "\nDid you mean:\n" + "\n".join(suggestions) + "\n"

    if invalid_values:
        msg += "\nInvalid value(s):\n"
        for param, (value, valid_options) in invalid_values.items():
            msg += f"  - {param}={repr(value)}\n"
            msg += f"    Valid options: {', '.join(repr(v) for v in valid_options)}\n"

            # Suggest close match
            if isinstance(value, str):
                suggestion = suggest_correction(value, valid_options)
                if suggestion:
                    msg += f"    Did you mean: {repr(suggestion)}?\n"

    return msg


# ============================================================================
# PROTOCOLS
# ============================================================================

class PropertyOperations(Protocol):
    """Contract for property operations (to, add, sub, mul, div)"""
    def to(self, *args): ...
    def add(self, *args): ...
    def by(self, *args): ...  # alias for add
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


class LifecyclePhase:
    """Represents a phase in the lifecycle (over/hold/revert)"""
    OVER = "over"
    HOLD = "hold"
    REVERT = "revert"


class LayerType:
    """Layer type classification"""
    BASE = "base"                           # base.{property} - transient, auto-bakes
    AUTO_NAMED_MODIFIER = "auto_modifier"   # {property}.{mode} - persistent, auto-named
    USER_NAMED_MODIFIER = "user_modifier"   # custom name + mode - persistent, user-named


class BuilderConfig:
    """Configuration collected by RigBuilder during fluent API calls"""
    def __init__(self):
        # Property and operator
        self.property: Optional[str] = None  # pos, speed, direction
        self.operator: Optional[str] = None  # to, by, add, sub, mul, div
        self.value: Any = None
        self.mode: Optional[str] = None  # 'offset', 'override', or 'scale'
        self.order: Optional[int] = None  # Explicit layer ordering

        # Movement type (absolute vs relative positioning)
        self.movement_type: str = "relative"  # 'relative' or 'absolute'
        self._movement_type_explicit: bool = False  # True if user explicitly set via .absolute or .relative

        # Identity
        self.layer_name: Optional[str] = None  # Layer name (base.{property}, {property}.{mode}, or user name)
        self.layer_type: str = LayerType.BASE  # Default to base, will be overwritten for modifiers
        self.is_user_named: bool = False  # True if user explicitly provided layer name via rig.layer()

        # Behavior
        self.behavior: Optional[str] = None  # stack, replace, queue, throttle
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

        # API override (set via .api())
        self.api_override: Optional[str] = None

        # Callbacks (stage -> callback)
        self.then_callbacks: list[tuple[str, Callable]] = []

        # Persistence
        self.bake_value: Optional[bool] = None

        # Execution mode
        self.is_synchronous: bool = False  # True for instant/sync execution, False for frame loop

    # ========================================================================
    # LAYER CLASSIFICATION (First-class properties)
    # ========================================================================

    def is_base_layer(self) -> bool:
        return self.layer_type == LayerType.BASE

    def is_modifier_layer(self) -> bool:
        return self.layer_type in (LayerType.AUTO_NAMED_MODIFIER, LayerType.USER_NAMED_MODIFIER)

    def is_auto_named_modifier(self) -> bool:
        return self.layer_type == LayerType.AUTO_NAMED_MODIFIER

    def is_user_named_modifier(self) -> bool:
        return self.layer_type == LayerType.USER_NAMED_MODIFIER

    def get_effective_behavior(self) -> str:
        """Get behavior with defaults applied"""
        if self.behavior is not None:
            return self.behavior
        # Default based on operator semantics:
        # .to() = absolute value, should reset (anonymous only)
        # .add()/.by()/.sub()/.mul()/.div() = relative, should stack
        if self.operator == "to":
            return "reset"
        return "stack"

    def get_effective_bake(self) -> bool:
        """Get bake setting with defaults applied"""
        if self.bake_value is not None:
            return self.bake_value
        # Default: base layers auto-bake, modifier layers don't
        # Modifier layers must be explicitly reverted or baked
        return self.is_base_layer()

    def validate_method_kwargs(self, method: str, mark_invalid: Optional[Callable[[], None]] = None, **kwargs) -> None:
        """Validate kwargs for a method call

        Args:
            method: Method name ('over', 'revert', 'hold', etc.)
            mark_invalid: Optional callback to mark builder as invalid before raising
            **kwargs: The kwargs to validate

        Raises:
            ConfigError: If validation fails
        """
        if not kwargs:
            return

        schema = METHOD_SIGNATURES.get(method)
        if not schema:
            return  # No schema defined, skip validation

        valid_params = schema['params']
        validations = schema.get('validations', {})

        # Check for unknown parameters
        unknown = [k for k in kwargs.keys() if k not in valid_params]

        # Check for invalid values
        invalid_values = {}
        for param, value in kwargs.items():
            if param in validations:
                param_name, valid_options = validations[param]
                # Skip validation for None values (optional parameters)
                if value is not None and value not in valid_options:
                    invalid_values[param] = (value, valid_options)

        # Raise error if any issues found
        if unknown or invalid_values:
            if mark_invalid:
                mark_invalid()
            raise ConfigError(format_validation_error(
                method=method,
                unknown_params=unknown if unknown else None,
                invalid_values=invalid_values if invalid_values else None,
                provided_kwargs=kwargs
            ))

    def validate_property_operator(self, mark_invalid: Optional[Callable[[], None]] = None) -> None:
        """Validate that operator is valid for the property

        Args:
            mark_invalid: Optional callback to mark builder as invalid before raising

        Raises:
            ConfigError: If validation fails
        """
        if not self.property or not self.operator:
            return

        if self.property not in VALID_PROPERTIES:
            if mark_invalid:
                mark_invalid()
            valid_str = ', '.join(repr(p) for p in VALID_PROPERTIES)
            raise ConfigError(
                f"Invalid property: {repr(self.property)}\n"
                f"Valid properties: {valid_str}"
            )

        valid_ops = VALID_OPERATORS.get(self.property, [])
        if self.operator not in valid_ops:
            if mark_invalid:
                mark_invalid()
            valid_str = ', '.join(repr(op) for op in valid_ops)
            raise ConfigError(
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
                    raise ConfigError(
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
                    raise ConfigError(
                        "Invalid vector (0, 0).\n\n"
                        "Vector cannot be a zero vector - it represents velocity (speed + direction).\n\n"
                        "To stop movement, use one of these instead:\n"
                        "  rig.stop()             # Stop all movement instantly\n"
                        "  rig.stop(500)          # Stop with 500ms transition\n"
                        "  rig.speed.to(0)        # Set speed to zero\n"
                        "  rig.layer('name').revert()  # Revert a layer"
                    )

    def validate_easing(self, easing: str, context: str = "easing", mark_invalid: Optional[Callable[[], None]] = None) -> None:
        """Validate an easing value

        Args:
            easing: The easing string to validate
            context: Context for error message (e.g., 'over_easing', 'revert_easing')
            mark_invalid: Optional callback to mark builder as invalid before raising

        Raises:
            ConfigError: If easing is invalid
        """
        if easing not in VALID_EASINGS:
            if mark_invalid:
                mark_invalid()
            valid_str = ', '.join(repr(e) for e in VALID_EASINGS)
            suggestion = suggest_correction(easing, VALID_EASINGS)
            msg = f"Invalid {context}: {repr(easing)}\n"
            msg += f"Valid options: {valid_str}"
            if suggestion:
                msg += f"\nDid you mean: {repr(suggestion)}?"
            raise ConfigError(msg)

    def validate_mode(self, mark_invalid: Optional[Callable[[], None]] = None) -> None:
        """Validate that mode is set for layer operations

        Args:
            mark_invalid: Optional callback to mark builder as invalid before raising

        Raises:
            ConfigError: If mode is missing or invalid
        """
        # Mode is only required for modifier layers (not base)
        if not self.is_modifier_layer():
            return

        if self.mode is None:
            if mark_invalid:
                mark_invalid()
            raise ConfigError(
                f"Layer operations require an explicit mode.\n\n"
                f"Available modes (modify the incoming value):\n"
                f"  - .offset   - offset the incoming value\n"
                f"  - .override - replace the incoming value\n"
                f"  - .scale    - multiply the incoming value\n\n"
                f"Examples:\n"
                f"  rig.layer('boost').speed.offset.to(100)       # set offset to 100\n"
                f"  rig.layer('boost').speed.offset.add(10)       # add 10 to offset (auto-stacks)\n"
                f"  rig.layer('cap').speed.override.to(200)       # replace with 200\n"
                f"  rig.layer('slowmo').speed.scale.by(0.5)       # multiply by 0.5 (auto-stacks)"
            )

        if self.mode not in VALID_MODES:
            if mark_invalid:
                mark_invalid()
            valid_str = ', '.join(repr(m) for m in VALID_MODES)
            raise ConfigError(
                f"Invalid mode: {repr(self.mode)}\n"
                f"Valid modes: {valid_str}"
            )

def validate_timing(value: Any, param_name: str, method: str = None, mark_invalid: Optional[Callable[[], None]] = None) -> Optional[float]:
    """Validate timing parameters (ms, rate, etc.)

    Args:
        value: The value to validate
        param_name: Name of the parameter ('ms', 'rate', etc.)
        method: Name of the method being called ('over', 'hold', 'revert', 'stop')
        mark_invalid: Optional callback to mark builder as invalid before raising
    """
    if value is None:
        return None

    method_str = f".{method}({param_name}=...)" if method else f"'{param_name}'"

    if not isinstance(value, (int, float)):
        if mark_invalid:
            mark_invalid()
        raise TypeError(
            f"Invalid type for {method_str}\n\n"
            f"Expected: number (int or float)\n"
            f"Got: {type(value).__name__} = {repr(value)}\n\n"
            f"Timing parameters must be numeric values."
        )

    float_value = float(value)

    if float_value < 0:
        if mark_invalid:
            mark_invalid()
        raise ConfigError(
            f"Negative duration not allowed: {method_str}\n\n"
            f"Got: {value}\n\n"
            f"Duration values must be >= 0."
        )

    return float_value


def validate_has_operation(config: 'BuilderConfig', method_name: str, mark_invalid: Optional[Callable[[], None]] = None) -> None:
    """Validate that a timing method has a prior operation to apply to

    Args:
        config: The builder config to check
        method_name: Name of the timing method being called (for error message)
        mark_invalid: Optional callback to mark builder as invalid before raising

    Raises:
        RigUsageError: If no operation (property/operator) has been set
    """
    if config.property is None or config.operator is None:
        if mark_invalid:
            mark_invalid()
        raise RigUsageError(
            f"Cannot call .{method_name}() without a prior operation. "
            f"You must set a property (e.g., .speed.to(5), .direction.by(90)) before calling .{method_name}()."
        )


def validate_api_has_operation(config: 'BuilderConfig', mark_invalid: Optional[Callable] = None):
    """Validate that api() is not called alone without an operation

    Args:
        config: BuilderConfig to validate
        mark_invalid: Optional callback to mark builder invalid

    Raises:
        ConfigError: If api() was called without any operation
    """
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