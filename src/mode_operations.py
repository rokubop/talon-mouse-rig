"""Mode operations - unified abstractions for offset/override/scale transformations

This module provides the core abstractions for how modes interact with operators:

Phase 1: Operator → Canonical Value
    Convert user operator + value into the canonical form for the mode:
    - offset: contribution (additive delta)
    - override: absolute value
    - scale: multiplier

Phase 2: Canonical Value → Application
    Apply the canonical value to accumulated state:
    - offset: accumulated + canonical
    - override: canonical
    - scale: accumulated × canonical
"""

import math
from typing import Any, Union
from .core import Vec2, EPSILON


# =============================================================================
# SCALAR OPERATIONS (speed, numeric values)
# =============================================================================

def calculate_scalar_target(
    operator: str,
    value: float,
    current: float,
    mode: str
) -> float:
    """Convert operator + value to canonical form for mode.

    Args:
        operator: The operation (to, add, sub, mul, div)
        value: The input value
        current: The current/base value
        mode: The mode (offset, override, scale)

    Returns:
        Canonical value for the mode:
        - offset: contribution amount (additive)
        - override: absolute target value
        - scale: multiplier factor
    """
    if mode == "scale":
        # Scale mode: store multiplier
        if operator == "to":
            return value
        elif operator in ("by", "add"):
            return 1.0 + value
        elif operator == "sub":
            return 1.0 - value
        elif operator == "mul":
            return value
        elif operator == "div":
            return 1.0 / value if value != 0 else 1.0

    elif mode == "override":
        # Override mode: store absolute value
        if operator == "to":
            return value
        elif operator in ("by", "add"):
            return current + value
        elif operator == "sub":
            return current - value
        elif operator == "mul":
            return current * value
        elif operator == "div":
            return current / value if value != 0 else current

    else:  # offset
        # Offset mode: store contribution
        if operator == "to":
            return value
        elif operator in ("by", "add"):
            return value
        elif operator == "sub":
            return -value
        elif operator == "mul":
            return current * (value - 1)
        elif operator == "div":
            return current * (1 - 1/value) if value != 0 else 0

    return value


def apply_scalar_mode(
    mode: str,
    canonical_value: float,
    accumulated: float
) -> float:
    """Apply canonical value to accumulated state based on mode.

    Args:
        mode: The mode (offset, override, scale)
        canonical_value: The canonical value from calculate_scalar_target
        accumulated: The current accumulated value

    Returns:
        New accumulated value after applying the mode operation
    """
    if mode == "offset":
        return accumulated + canonical_value
    elif mode == "override":
        return canonical_value
    elif mode == "scale":
        return accumulated * canonical_value

    return accumulated


# =============================================================================
# DIRECTION OPERATIONS (vector normalization, rotation)
# =============================================================================

def calculate_direction_target(
    operator: str,
    value: Union[tuple, float],
    current: Vec2,
    mode: str
) -> Union[Vec2, float]:
    """Convert operator + value to canonical form for direction mode.

    Args:
        operator: The operation (to, add, sub, mul)
        value: The input value (tuple for vector, float for angle)
        current: The current direction vector
        mode: The mode (offset, override, scale)

    Returns:
        Canonical value for the mode:
        - offset: angle (float) or delta vector (Vec2)
        - override: absolute direction vector (Vec2)
        - scale: multiplier factor (float)
    """
    if mode == "scale":
        # Scale mode: store multiplier
        if operator == "to":
            return value
        elif operator in ("by", "add"):
            return 1.0 + value
        elif operator == "mul":
            return value

    elif mode == "override":
        # Override mode: store absolute direction
        if operator == "to":
            return Vec2.from_tuple(value).normalized()
        elif operator in ("by", "add"):
            # Calculate absolute target from rotation
            if isinstance(value, tuple) and len(value) == 2:
                delta = Vec2.from_tuple(value)
                return (current + delta).normalized()
            else:
                # Rotation by angle
                angle_deg = value[0] if isinstance(value, tuple) else value
                angle_rad = math.radians(angle_deg)
                cos_a = math.cos(angle_rad)
                sin_a = math.sin(angle_rad)
                new_x = current.x * cos_a - current.y * sin_a
                new_y = current.x * sin_a + current.y * cos_a
                return Vec2(new_x, new_y).normalized()
        elif operator == "sub":
            if isinstance(value, tuple) and len(value) == 2:
                delta = Vec2.from_tuple(value)
                return (current - delta).normalized()
            else:
                angle_deg = value[0] if isinstance(value, tuple) else value
                angle_rad = math.radians(-angle_deg)
                cos_a = math.cos(angle_rad)
                sin_a = math.sin(angle_rad)
                new_x = current.x * cos_a - current.y * sin_a
                new_y = current.x * sin_a + current.y * cos_a
                return Vec2(new_x, new_y).normalized()
        elif operator == "mul":
            # Multiply direction by scalar
            # For negative scalars (like -1 for reverse), keep unnormalized
            # to allow smooth magnitude transitions during lerp
            scalar = value[0] if isinstance(value, tuple) else value
            result = Vec2(current.x * scalar, current.y * scalar)
            # Only normalize if scalar is positive (normal scaling)
            # Negative scalars indicate reversal - preserve for magnitude lerp
            return result.normalized() if scalar >= 0 else result

    else:  # offset
        # Offset mode: store rotation angle or delta vector
        if operator == "to":
            return Vec2.from_tuple(value).normalized()
        elif operator in ("by", "add"):
            if isinstance(value, tuple) and len(value) == 2:
                return Vec2.from_tuple(value)
            else:
                # Store angle for rotation
                angle_deg = value[0] if isinstance(value, tuple) else value
                return angle_deg
        elif operator == "sub":
            if isinstance(value, tuple) and len(value) == 2:
                return -Vec2.from_tuple(value)
            else:
                angle_deg = value[0] if isinstance(value, tuple) else value
                return -angle_deg

    return current


def apply_direction_mode(
    mode: str,
    canonical_value: Union[Vec2, float],
    accumulated: Vec2
) -> Vec2:
    """Apply canonical value to accumulated direction based on mode.

    Args:
        mode: The mode (offset, override, scale)
        canonical_value: The canonical value from calculate_direction_target
        accumulated: The current accumulated direction

    Returns:
        New accumulated direction after applying the mode operation
    """
    if mode == "offset":
        # Offset: apply rotation or delta
        if isinstance(canonical_value, (int, float)):
            # It's an angle, rotate direction
            angle_rad = math.radians(canonical_value)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            new_x = accumulated.x * cos_a - accumulated.y * sin_a
            new_y = accumulated.x * sin_a + accumulated.y * cos_a
            return Vec2(new_x, new_y).normalized()
        else:
            # It's a vector, add and normalize
            try:
                return (accumulated + canonical_value).normalized()
            except Exception:
                return canonical_value.normalized()

    elif mode == "override":
        # Override: replace with absolute direction
        return canonical_value

    elif mode == "scale":
        # Scale: multiply components
        return Vec2(accumulated.x * canonical_value, accumulated.y * canonical_value).normalized()

    return accumulated


# =============================================================================
# POSITION OPERATIONS (2D vectors)
# =============================================================================

def calculate_position_target(
    operator: str,
    value: Union[tuple, Vec2],
    current: Vec2,
    mode: str
) -> Union[Vec2, float]:
    """Convert operator + value to canonical form for position mode.

    Args:
        operator: The operation (to, add, by)
        value: The input value (tuple or Vec2)
        current: The current position
        mode: The mode (offset, override, scale)

    Returns:
        Canonical value for the mode:
        - offset: offset vector (Vec2)
        - override: absolute position (Vec2)
        - scale: multiplier factor (float)
    """
    if mode == "scale":
        # Scale mode: store multiplier
        if operator == "to":
            return value
        elif operator in ("by", "add"):
            return 1.0 + value

    elif mode == "override":
        # Override mode: store absolute position
        if operator == "to":
            return Vec2.from_tuple(value)
        elif operator in ("by", "add"):
            return current + Vec2.from_tuple(value)

    else:  # offset
        # Offset mode: store offset vector
        if operator == "to":
            return Vec2.from_tuple(value)
        elif operator in ("by", "add"):
            return Vec2.from_tuple(value)

    return current


def apply_position_mode(
    mode: str,
    canonical_value: Union[Vec2, float],
    accumulated: Vec2
) -> Vec2:
    """Apply canonical value to accumulated position based on mode.

    Args:
        mode: The mode (offset, override, scale)
        canonical_value: The canonical value from calculate_position_target
        accumulated: The current accumulated position

    Returns:
        New accumulated position after applying the mode operation
    """
    if mode == "offset":
        # Offset: add offset vector
        return accumulated + canonical_value
    elif mode == "override":
        # Override: replace with absolute position
        return canonical_value
    elif mode == "scale":
        # Scale: multiply components
        return Vec2(accumulated.x * canonical_value, accumulated.y * canonical_value)

    return accumulated


# =============================================================================
# VECTOR OPERATIONS (velocity = speed + direction)
# =============================================================================

def calculate_vector_target(
    operator: str,
    value: Union[tuple, Vec2],
    current_speed: float,
    current_direction: Vec2,
    mode: str
) -> Vec2:
    """Convert operator + value to canonical form for vector mode.

    Args:
        operator: The operation (to, add, sub)
        value: The input value (x, y tuple or Vec2)
        current_speed: Current speed magnitude
        current_direction: Current direction vector
        mode: The mode (offset, override, scale)

    Returns:
        Canonical Vec2 for the mode:
        - offset: velocity contribution (additive)
        - override: absolute velocity
        - scale: multiplier as Vec2
    """
    vec = Vec2.from_tuple(value)

    if mode == "scale":
        # Scale mode: store multiplier as magnitude
        if operator == "to":
            return Vec2(vec.magnitude(), 0)  # Store as scalar in x component
        elif operator in ("by", "add"):
            return Vec2(1.0 + vec.magnitude(), 0)
        elif operator == "sub":
            return Vec2(1.0 - vec.magnitude(), 0)

    elif mode == "override":
        # Override mode: store absolute velocity vector
        if operator == "to":
            return vec
        elif operator in ("by", "add"):
            current_velocity = current_direction * current_speed
            return current_velocity + vec
        elif operator == "sub":
            current_velocity = current_direction * current_speed
            return current_velocity - vec

    else:  # offset
        # Offset mode: store velocity contribution
        if operator == "to":
            return vec
        elif operator in ("by", "add"):
            return vec
        elif operator == "sub":
            return -vec

    return vec


def apply_vector_mode(
    mode: str,
    canonical_value: Vec2,
    accumulated_speed: float,
    accumulated_direction: Vec2
) -> tuple[float, Vec2]:
    """Apply canonical vector value to accumulated speed and direction.

    Args:
        mode: The mode (offset, override, scale)
        canonical_value: The canonical vector value
        accumulated_speed: Current accumulated speed
        accumulated_direction: Current accumulated direction

    Returns:
        Tuple of (new_speed, new_direction)
    """
    if mode == "offset":
        # Offset: additive contribution - add velocity vectors
        accumulated_velocity = accumulated_direction * accumulated_speed
        new_velocity = accumulated_velocity + canonical_value

        speed = new_velocity.magnitude()
        # Preserve direction if new velocity is zero (from offsetting to zero)
        if speed < EPSILON:
            direction = accumulated_direction
        else:
            direction = new_velocity.normalized()

        return speed, direction

    elif mode == "override":
        # Override: replace accumulated value
        # Note: vector.to(0, 0) is now blocked by validation in contracts.py
        speed = canonical_value.magnitude()
        direction = canonical_value.normalized()
        return speed, direction

    elif mode == "scale":
        # Scale: multiplicative factor
        speed = accumulated_speed * canonical_value.magnitude()
        # Preserve direction if speed becomes zero (from scaling to zero)
        if speed < EPSILON:
            direction = accumulated_direction
        else:
            direction = (accumulated_direction * canonical_value.magnitude()).normalized()
        return speed, direction

    return accumulated_speed, accumulated_direction
