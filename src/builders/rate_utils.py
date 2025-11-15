"""Utilities for rate-based timing calculations"""

from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..state import RigState


def validate_rate_params(
    duration_ms: Optional[float],
    rate_speed: Optional[float],
    rate_accel: Optional[float],
    rate_rotation: Optional[float]
) -> bool:
    """Validate that duration and rate parameters are not both specified.

    Returns:
        True if rate parameters are provided, False otherwise

    Raises:
        ValueError if both duration_ms and rate parameters are specified
    """
    rate_provided = rate_speed is not None or rate_accel is not None or rate_rotation is not None
    if duration_ms is not None and rate_provided:
        raise ValueError("Cannot specify both duration_ms and rate parameters")
    return rate_provided


def calculate_duration_from_rate(
    value: float,
    rate: float,
    min_duration_ms: float = 1.0
) -> float:
    """Calculate duration in milliseconds from a value and rate.

    Args:
        value: The absolute value to fade (e.g., speed, rotation degrees)
        rate: The rate per second (e.g., units/second, degrees/second)
        min_duration_ms: Minimum duration to return

    Returns:
        Duration in milliseconds
    """
    if abs(value) < 0.01:
        return min_duration_ms
    duration_sec = abs(value) / rate
    return max(duration_sec * 1000, min_duration_ms)


def _calculate_duration_for_property_impl(
    property_name: str,
    current_value: float,
    target_value: float,
    rate_speed: Optional[float],
    rate_accel: Optional[float],
    rate_rotation: Optional[float],
    default_if_no_rate: Optional[float]
) -> Optional[float]:
    """Internal implementation for calculating property transition duration from rate.

    Args:
        property_name: "speed" or "accel" (direction not supported - uses Vec2)
        current_value: Current property value
        target_value: Target property value (0 for revert)
        rate_speed: Speed rate in units/second
        rate_accel: Acceleration rate in units/second²
        rate_rotation: Not supported (direction uses its own rate calculation)
        default_if_no_rate: Default duration if no rate provided, or None

    Returns:
        Duration in milliseconds, or default_if_no_rate if no rate provided

    Raises:
        ValueError if rate parameter doesn't match property type or direction is used
    """
    # Direction is not supported - it uses Vec2 and needs dot product calculation
    if property_name == "direction" or rate_rotation is not None:
        raise ValueError(
            "rate_rotation parameter not supported with rate_speed or rate_accel. "
            "For direction transitions, use .rotate().over(rate_rotation=...) or "
            ".rotate().revert(rate_rotation=...) instead."
        )

    rate_provided = rate_speed is not None or rate_accel is not None
    if not rate_provided:
        return default_if_no_rate

    # Determine which rate to use
    if rate_speed is not None:
        if property_name != "speed":
            raise ValueError(f"rate_speed only valid for speed property, not {property_name}")
        rate_value = rate_speed
    elif rate_accel is not None:
        if property_name != "accel":
            raise ValueError(f"rate_accel only valid for accel property, not {property_name}")
        rate_value = rate_accel
    else:
        return default_if_no_rate

    # Calculate duration based on delta (scalar values only)
    delta = abs(target_value - current_value)
    return calculate_duration_from_rate(delta, rate_value)


def calculate_over_duration_for_property(
    property_name: str,
    current_value: float,
    target_value: float,
    rate_speed: Optional[float],
    rate_accel: Optional[float],
    rate_rotation: Optional[float]
) -> float:
    """Calculate .over() duration from rate for scalar property builders (speed/accel only).

    Args:
        property_name: "speed" or "accel" (direction not supported - uses Vec2)
        current_value: Current property value
        target_value: Target property value after operation
        rate_speed: Speed rate in units/second
        rate_accel: Acceleration rate in units/second²
        rate_rotation: Not supported (direction uses its own rate calculation)

    Returns:
        Duration in milliseconds (defaults to 500ms if no rate provided)

    Raises:
        ValueError if rate parameter doesn't match property type or direction is used
    """
    return _calculate_duration_for_property_impl(
        property_name, current_value, target_value,
        rate_speed, rate_accel, rate_rotation,
        default_if_no_rate=500.0
    )


def calculate_revert_duration_for_property(
    property_name: str,
    current_value: float,
    rate_speed: Optional[float],
    rate_accel: Optional[float],
    rate_rotation: Optional[float]
) -> Optional[float]:
    """Calculate .revert() duration from rate for scalar property builders (speed/accel only).

    Args:
        property_name: "speed" or "accel" (direction not supported - uses Vec2)
        current_value: Current property value to revert from
        rate_speed: Speed rate in units/second
        rate_accel: Acceleration rate in units/second²
        rate_rotation: Not supported (direction uses its own rate calculation)

    Returns:
        Duration in milliseconds, or None if no rate provided

    Raises:
        ValueError if rate parameter doesn't match property type or direction is used
    """
    return _calculate_duration_for_property_impl(
        property_name, current_value, 0.0,  # Revert to 0
        rate_speed, rate_accel, rate_rotation,
        default_if_no_rate=None
    )
