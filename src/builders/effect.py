"""Effect builders for PRD 8 named effects"""

from typing import Optional, TYPE_CHECKING, Union, TypeVar, Generic
from ..core import Vec2
from ..effects import EffectStack, EffectLifecycle

if TYPE_CHECKING:
    from ..state import RigState

# Type variable for self-return types in base class
T = TypeVar('T', bound='EffectBuilderBase')


class EffectBuilderBase(Generic[T]):
    """
    Base class for all effect property builders.
    Consolidates shared implementation for operations and lifecycle methods.
    Subclasses only need to specify property name and override type hints.
    """
    # Override in subclasses
    _property_name: str = None

    def __init__(self, rig_state: 'RigState', name: str, strict_mode: bool = False):
        self.rig_state = rig_state
        self.name = name
        self.strict_mode = strict_mode
        self._last_op_type: Optional[str] = None
        self._started = False

    def __del__(self):
        """Auto-start when builder goes out of scope if not already started"""
        try:
            if not self._started and self._last_op_type is not None:
                self.rig_state.start()
        except:
            pass

    def __call__(self, value: Union[float, Vec2]) -> T:
        """Shorthand for add/to operation - strict mode disallows this"""
        if self.strict_mode:
            raise ValueError(
                f"Strict syntax required for effects. "
                f"Use .to({value}) for absolute value or .add({value}) for delta. "
                f"Shorthand syntax like .{self._property_name}({value}) is not allowed for effects."
            )
        return self.to(value)

    def _get_or_create_stack(self, op_type: str) -> EffectStack:
        """Get or create the effect stack for this operation type"""
        key = f"{self.name}:{self._property_name}:{op_type}"
        if key not in self.rig_state._effect_stacks:
            stack = EffectStack(
                name=self.name,
                property=self._property_name,
                operation_type=op_type
            )
            self.rig_state._effect_stacks[key] = stack
            if key not in self.rig_state._effect_order:
                self.rig_state._effect_order.append(key)
        return self.rig_state._effect_stacks[key]

    def _get_or_create_effect(self, op_type: str) -> EffectLifecycle:
        """Get or create the effect lifecycle wrapper"""
        key = f"{self.name}:{self._property_name}:{op_type}"
        if key not in self.rig_state._effect_lifecycles:
            stack = self._get_or_create_stack(op_type)
            self.rig_state._effect_lifecycles[key] = EffectLifecycle(stack)
        return self.rig_state._effect_lifecycles[key]

    def to(self, value: Union[float, Vec2]) -> T:
        """Set absolute value"""
        stack = self._get_or_create_stack("to")
        stack.add_operation(value)
        self._last_op_type = "to"
        return self

    def mul(self, value: float) -> T:
        """Multiply (default: replaces, use .on_repeat("stack") for multiple)"""
        stack = self._get_or_create_stack("mul")
        stack.add_operation(value)
        self._last_op_type = "mul"
        return self

    def div(self, value: float) -> T:
        """Divide (default: replaces, use .on_repeat("stack") for multiple)"""
        if abs(value) < 1e-6:
            raise ValueError("Cannot divide by zero or near-zero value")
        stack = self._get_or_create_stack("div")
        stack.add_operation(1.0 / value)
        self._last_op_type = "div"
        return self

    def add(self, value: Union[float, Vec2]) -> T:
        """Add delta (default: replaces, use .on_repeat("stack") for multiple)"""
        stack = self._get_or_create_stack("add")
        stack.add_operation(value)
        self._last_op_type = "add"
        return self

    def by(self, value: Union[float, Vec2]) -> T:
        """Alias for add() - add delta"""
        return self.add(value)

    def sub(self, value: Union[float, Vec2]) -> T:
        """Subtract (default: replaces, use .on_repeat("stack") for multiple)"""
        stack = self._get_or_create_stack("sub")
        stack.add_operation(-value if isinstance(value, (int, float)) else Vec2(-value.x, -value.y))
        self._last_op_type = "sub"
        return self

    def on_repeat(self, strategy: str = "replace", *args) -> T:
        """Configure behavior when effect is called multiple times

        Strategies:
            "replace" (default): New call replaces existing effect, resets duration
            "stack" [max_count]: Stack effects (unlimited or with max count)
            "extend": Extend duration from current phase, cancel pending revert
            "queue": Queue effects to run sequentially
            "ignore": Ignore new calls while effect is active
            "throttle" [ms]: Rate limit calls (minimum time between calls)

        Examples:
            .add(10).on_repeat("stack")          # Unlimited stacking
            .add(10).on_repeat("stack", 3)       # Max 3 stacks
            .add(10).on_repeat("replace")        # Default behavior
            .add(10).on_repeat("extend")         # Extend duration
            .add(10).on_repeat("throttle", 500)  # Max 1 call per 500ms
        """
        if self._last_op_type is None:
            raise ValueError("No operation to apply .on_repeat() to - call .to()/.mul()/.div()/.add()/.sub() first")

        key = f"{self.name}:{self._property_name}:{self._last_op_type}"

        if strategy == "stack":
            max_count = args[0] if args else None
            if key in self.rig_state._effect_stacks:
                self.rig_state._effect_stacks[key].max_stack_count = max_count
        elif strategy == "replace":
            pass
        elif strategy in ("extend", "queue", "ignore", "throttle"):
            if key in self.rig_state._effect_lifecycles:
                self.rig_state._effect_lifecycles[key].repeat_strategy = strategy
                if strategy == "throttle" and args:
                    self.rig_state._effect_lifecycles[key].throttle_ms = args[0]
        else:
            raise ValueError(f"Unknown repeat strategy: {strategy}. Use: replace, stack, extend, queue, ignore, throttle")

        return self

    def over(self, duration_ms: float, easing: str = "linear") -> T:
        """Fade in over duration"""
        if self._last_op_type is None:
            raise ValueError("No operation to apply .over() to - call .mul()/.div()/.add()/.sub() first")

        effect = self._get_or_create_effect(self._last_op_type)
        effect.in_duration_ms = duration_ms
        effect.in_easing = easing

        if not self._started:
            self.rig_state.start()
            self._started = True
        return self

    def hold(self, duration_ms: float) -> T:
        """Maintain for duration"""
        if self._last_op_type is None:
            raise ValueError("No operation to apply .hold() to - call .mul()/.div()/.add()/.sub() first")

        effect = self._get_or_create_effect(self._last_op_type)
        effect.hold_duration_ms = duration_ms

        if not self._started:
            self.rig_state.start()
            self._started = True
        return self

    def revert(self, duration_ms: float = 0, easing: str = "linear") -> T:
        """Revert to original state"""
        if self._last_op_type is None:
            raise ValueError("No operation to apply .revert() to - call .mul()/.div()/.add()/.sub() first")

        effect = self._get_or_create_effect(self._last_op_type)

        # If no hold duration is set and we have fade-in, add instant hold
        if effect.in_duration_ms is not None and effect.hold_duration_ms is None:
            effect.hold_duration_ms = 0

        effect.out_duration_ms = duration_ms
        effect.out_easing = easing

        if not self._started:
            self.rig_state.start()
            self._started = True
        return self

class EffectBuilder:
    """
    PRD 8: Builder for named effect entities.

    Effects modify base properties using direct operations:
    - .to(value): Set absolute value
    - .add(value) / .by(value): Add delta (aliases)
    - .sub(value): Subtract
    - .mul(value): Multiply
    - .div(value): Divide

    Effects use strict syntax - shorthand like speed(10) is not allowed.
    Use explicit operations like speed.to(10) or speed.add(10).

    Examples:
        rig.effect("sprint").speed.mul(2)       # Double speed
        rig.effect("boost").speed.add(10)       # Add 10 to speed
        rig.effect("drift").direction.add(15)   # Rotate 15 degrees
    """
    def __init__(self, rig_state: 'RigState', name: str, strict_mode: bool = True):
        self.rig_state = rig_state
        self.name = name
        self.strict_mode = strict_mode
        self._speed_builder = None
        self._accel_builder = None
        self._direction_builder = None
        self._pos_builder = None

    @property
    def speed(self) -> 'EffectSpeedBuilder':
        """Access speed effect operations"""
        if self._speed_builder is None:
            self._speed_builder = EffectSpeedBuilder(self.rig_state, self.name, self.strict_mode)
        return self._speed_builder

    @property
    def accel(self) -> 'EffectAccelBuilder':
        """Access accel effect operations"""
        if self._accel_builder is None:
            self._accel_builder = EffectAccelBuilder(self.rig_state, self.name, self.strict_mode)
        return self._accel_builder

    @property
    def direction(self) -> 'EffectDirectionBuilder':
        """Access direction effect operations (rotation)"""
        if self._direction_builder is None:
            self._direction_builder = EffectDirectionBuilder(self.rig_state, self.name, self.strict_mode)
        return self._direction_builder

    @property
    def pos(self) -> 'EffectPosBuilder':
        """Access position effect operations (offsets)"""
        if self._pos_builder is None:
            self._pos_builder = EffectPosBuilder(self.rig_state, self.name, self.strict_mode)
        return self._pos_builder

    def revert(self, duration_ms: Optional[float] = None, easing: str = "linear") -> None:
        """Revert this effect (removes all operations)"""
        # Revert all effect stacks for this entity
        keys_to_revert = [key for key in self.rig_state._effect_stacks
                         if key.startswith(f"{self.name}:")]

        for key in keys_to_revert:
            if key in self.rig_state._effect_lifecycles:
                effect = self.rig_state._effect_lifecycles[key]
                effect.request_stop(duration_ms, easing)
            else:
                # Immediate removal if no lifecycle
                del self.rig_state._effect_stacks[key]
                if key in self.rig_state._effect_order:
                    self.rig_state._effect_order.remove(key)

        # Start the update loop to apply the revert (especially important when stopped)
        self.rig_state.start()




class EffectSpeedBuilder(EffectBuilderBase['EffectSpeedBuilder']):
    """Builder for effect speed operations (to/mul/div/add/sub)"""
    _property_name = "speed"

    @property
    def max(self) -> 'MaxBuilder':
        """Access max constraints"""
        return MaxBuilder(self.rig_state, self.name, "speed", None)



class EffectAccelBuilder(EffectBuilderBase['EffectAccelBuilder']):
    """Builder for effect accel operations (to/mul/div/add/sub)"""
    _property_name = "accel"



class EffectDirectionBuilder(EffectBuilderBase['EffectDirectionBuilder']):
    """Builder for effect direction operations (rotation in degrees)"""
    _property_name = "direction"

    def to(self, *args) -> 'EffectDirectionBuilder':
        """Set direction to specific angle (degrees) or vector (x, y)"""
        stack = self._get_or_create_stack("to")
        if len(args) == 1:
            # Angle in degrees
            stack.values = [args[0]]
        elif len(args) == 2:
            # Vector (x, y)
            stack.values = [Vec2(args[0], args[1])]
        else:
            raise ValueError("direction.to() requires 1 arg (degrees) or 2 args (x, y)")
        self._last_op_type = "to"
        return self



class EffectPosBuilder(EffectBuilderBase['EffectPosBuilder']):
    """Builder for effect position operations (offsets)"""
    _property_name = "pos"

    def to(self, x: float, y: float) -> 'EffectPosBuilder':
        """Set offset to specific position"""
        stack = self._get_or_create_stack("to")
        stack.values = [Vec2(x, y)]
        self._last_op_type = "to"
        return self

    def add(self, x: float, y: float) -> 'EffectPosBuilder':
        """Add position offset (default: replaces, use .on_repeat("stack") for multiple)"""
        stack = self._get_or_create_stack("add")
        stack.add_operation(Vec2(x, y))
        self._last_op_type = "add"
        return self

    def by(self, x: float, y: float) -> 'EffectPosBuilder':
        """Alias for add (offset by vector)"""
        return self.add(x, y)

    def sub(self, x: float, y: float) -> 'EffectPosBuilder':
        """Subtract position offset (default: replaces, use .on_repeat("stack") for multiple)"""
        stack = self._get_or_create_stack("sub")
        stack.add_operation(Vec2(-x, -y))
        self._last_op_type = "sub"
        return self



class MaxBuilder:
    """Builder for max constraints on effect operations"""
    def __init__(self, rig_state: 'RigState', name: str, property: str, operation_type: str):
        self.rig_state = rig_state
        self.name = name
        self.property = property
        self.operation_type = operation_type

    def __call__(self, value: Union[float, int]) -> 'MaxBuilder':
        """Set max constraint on current property (context-aware shorthand)

        Examples:
            rig("boost").shift.speed.by(10).max(50)         # max speed value
            rig("drift").shift.direction.by(45).max(90)     # max rotation degrees
            rig("boost").shift.speed.by(10).max.stack(3)    # max stack count
        """
        if self.property == "speed":
            return self.speed(value)
        elif self.property == "accel":
            return self.accel(value)
        elif self.property == "direction":
            return self.direction(value)
        elif self.property == "pos":
            return self.pos(value)
        return self

    def speed(self, value: float) -> 'MaxBuilder':
        """Set maximum speed constraint"""
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_value = value
        return self

    def accel(self, value: float) -> 'MaxBuilder':
        """Set maximum accel constraint"""
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_value = value
        return self

    def direction(self, value: float) -> 'MaxBuilder':
        """Set maximum direction rotation constraint (in degrees)

        Example:
            rig("drift").shift.direction.by(45).max.direction(90)  # Cap at 90° total
        """
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_value = value
        return self

    def pos(self, value: float) -> 'MaxBuilder':
        """Set maximum position offset magnitude constraint

        Example:
            rig("shake").shift.pos.by(10, 10).max.pos(50)  # Cap total offset magnitude
        """
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_value = value
        return self

    def stack(self, count: int) -> 'MaxBuilder':
        """Set maximum stack count"""
        key = f"{self.name}:{self.property}:{self.operation_type}"
        if key in self.rig_state._effect_stacks:
            self.rig_state._effect_stacks[key].max_stack_count = count
        return self
