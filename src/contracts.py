"""Type contracts and protocols for mouse rig V2

This is the single source of truth for all interfaces in the system.
"""

from typing import Protocol, Callable, Any, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from .core import Vec2


# ============================================================================
# VALIDATION SCHEMAS - Single source of truth for what's valid
# ============================================================================

VALID_PROPERTIES = ['pos', 'speed', 'direction', 'vector']

VALID_OPERATORS = {
    'speed': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake', 'scale'],
    'direction': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake', 'scale'],
    'pos': ['to', 'add', 'by', 'sub', 'bake', 'scale'],
    'vector': ['to', 'add', 'by', 'sub', 'bake']
}

"""Valid blend modes (override replaces accumulated value at layer position)"""
VALID_BLEND_MODES = ['contribute', 'override']

# Layer types
LAYER_TYPES = {
    '__base__': {'order': float('-inf')},
    '__final__': {'order': float('inf')},
}

VALID_EASINGS = [
    'linear',
    'ease_in', 'ease_out', 'ease_in_out',
    'ease_in_2', 'ease_out_2', 'ease_in_out_2',
    'ease_in_3', 'ease_out_3', 'ease_in_out_3',
    'ease_in_4', 'ease_out_4', 'ease_in_out_4',
]
VALID_INTERPOLATIONS = ['lerp', 'slerp']
VALID_BEHAVIORS = ['stack', 'reset', 'queue', 'extend', 'throttle', 'ignore']  # ignore is internal for throttle()

# Method signatures for validation
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
    if behavior == 'throttle':
        METHOD_SIGNATURES[behavior] = {
            'params': ['ms'],
            'signature': f'{behavior}(ms=None)',
            'validations': {}
        }
    elif behavior == 'stack':
        METHOD_SIGNATURES[behavior] = {
            'params': ['max_count'],
            'signature': f'{behavior}(max_count=None)',
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
    'layer', 'stop', 'reverse', 'bake',
]

VALID_RIG_PROPERTIES = [
    'pos', 'speed', 'direction',
    'state', 'base',
    'final', 'override',  # Layer accessors
    'stack', 'reset', 'queue', 'extend', 'throttle',
]

VALID_BUILDER_METHODS = [
    'over', 'hold', 'revert', 'then', 'bake',
    'stack', 'reset', 'queue', 'extend', 'throttle',
]


# ============================================================================
# VALIDATION ERROR HANDLING
# ============================================================================

class ConfigError(TypeError):
    """Configuration validation error with rich formatting"""
    pass


class RigAttributeError(AttributeError):
    """Attribute error with helpful suggestions"""
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
    """Contract for behavior modes (stack, reset, queue, etc.)"""
    def stack(self, max_count: Optional[int] = None): ...
    def reset(self): ...
    def queue(self): ...
    def extend(self): ...
    def throttle(self, ms: Optional[float] = None): ...


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
        self.property: Optional[str] = None  # pos, speed, direction
        self.operator: Optional[str] = None  # to, by, add, sub, mul, div, scale
        self.value: Any = None
        self.blend_mode: str = 'contribute'  # 'contribute' (default) or 'override'
        self.order: Optional[int] = None  # Explicit layer ordering

        # Identity
        self.layer_name: Optional[str] = None  # Layer name (__base__, user name, __final__)

        # Behavior
        self.behavior: Optional[str] = None  # stack, reset, queue, extend, throttle, ignore
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
        """Check if this builder is anonymous (auto-generated base layer)"""
        return self.layer_name is not None and self.layer_name.startswith("__base_")

    def is_base_layer(self) -> bool:
        """Check if this is a base layer (anonymous)"""
        return self.is_anonymous()

    def is_final_layer(self) -> bool:
        """Check if this is the final layer"""
        return self.layer_name is not None and self.layer_name.startswith("__final_")

    def is_user_layer(self) -> bool:
        """Check if this is a user layer (named layer, not base or final)"""
        return not self.is_base_layer() and not self.is_final_layer()

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
        # Default: anonymous bakes, is_named_layer doesn't
        # is_named_layer builders must be explicitly reverted or baked
        return self.is_anonymous()

    def validate_method_kwargs(self, method: str, **kwargs) -> None:
        """Validate kwargs for a method call

        Args:
            method: Method name ('over', 'revert', 'hold', etc.)
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
                if value not in valid_options:
                    invalid_values[param] = (value, valid_options)

        # Raise error if any issues found
        if unknown or invalid_values:
            raise ConfigError(format_validation_error(
                method=method,
                unknown_params=unknown if unknown else None,
                invalid_values=invalid_values if invalid_values else None,
                provided_kwargs=kwargs
            ))

    def validate_property_operator(self) -> None:
        """Validate that operator is valid for the property

        Raises:
            ConfigError: If validation fails
        """
        if not self.property or not self.operator:
            return

        if self.property not in VALID_PROPERTIES:
            valid_str = ', '.join(repr(p) for p in VALID_PROPERTIES)
            raise ConfigError(
                f"Invalid property: {repr(self.property)}\n"
                f"Valid properties: {valid_str}"
            )

        valid_ops = VALID_OPERATORS.get(self.property, [])
        if self.operator not in valid_ops:
            valid_str = ', '.join(repr(op) for op in valid_ops)
            raise ConfigError(
                f"Invalid operator {repr(self.operator)} for property {repr(self.property)}\n"
                f"Valid operators for {self.property}: {valid_str}"
            )

    def validate_easing(self, easing: str, context: str = "easing") -> None:
        """Validate an easing value

        Args:
            easing: The easing string to validate
            context: Context for error message (e.g., 'over_easing', 'revert_easing')

        Raises:
            ConfigError: If easing is invalid
        """
        if easing not in VALID_EASINGS:
            valid_str = ', '.join(repr(e) for e in VALID_EASINGS)
            suggestion = suggest_correction(easing, VALID_EASINGS)
            msg = f"Invalid {context}: {repr(easing)}\n"
            msg += f"Valid options: {valid_str}"
            if suggestion:
                msg += f"\nDid you mean: {repr(suggestion)}?"
            raise ConfigError(msg)
