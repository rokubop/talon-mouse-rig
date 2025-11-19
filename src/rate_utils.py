"""Rate-based timing calculations for transitions

This module handles converting rate parameters (units/second, degrees/second, pixels/second)
into duration values for lifecycle transitions.
"""

from typing import Optional
import math
from .core import Vec2, EPSILON


def calculate_duration_from_rate(
    value: float,
    rate: float,
    min_duration_ms: float = 1.0
) -> float:
    """Calculate duration in milliseconds from a value and rate.

    Args:
        value: The absolute value to transition (e.g., speed delta, rotation degrees)
        rate: The rate per second (e.g., units/second, degrees/second)
        min_duration_ms: Minimum duration to return

    Returns:
        Duration in milliseconds
    """
    if abs(value) < 0.01:
        return min_duration_ms
    duration_sec = abs(value) / rate
    return max(duration_sec * 1000, min_duration_ms)


def calculate_speed_duration(
    current: float,
    target: float,
    rate: float
) -> float:
    """Calculate duration for speed transition based on rate.

    Args:
        current: Current speed value
        target: Target speed value
        rate: Speed rate in units/second

    Returns:
        Duration in milliseconds
    """
    delta = abs(target - current)
    return calculate_duration_from_rate(delta, rate)


def calculate_direction_duration(
    current: Vec2,
    target: Vec2,
    rate: float
) -> float:
    """Calculate duration for direction rotation based on rate.

    Args:
        current: Current direction vector (should be normalized)
        target: Target direction vector (should be normalized)
        rate: Rotation rate in degrees/second

    Returns:
        Duration in milliseconds
    """
    # Calculate angle between vectors
    dot = current.dot(target)
    dot = max(-1.0, min(1.0, dot))  # Clamp to avoid math domain errors
    angle_rad = math.acos(dot)
    angle_deg = math.degrees(angle_rad)

    return calculate_duration_from_rate(angle_deg, rate)


def calculate_direction_by_duration(
    angle_delta: float,
    rate: float
) -> float:
    """Calculate duration for relative direction rotation based on rate.

    Args:
        angle_delta: Angle to rotate in degrees (can be positive or negative)
        rate: Rotation rate in degrees/second

    Returns:
        Duration in milliseconds
    """
    return calculate_duration_from_rate(abs(angle_delta), rate)


def calculate_position_duration(
    current: Vec2,
    target: Vec2,
    rate: float
) -> float:
    """Calculate duration for position movement based on rate.

    Args:
        current: Current position
        target: Target position
        rate: Movement rate in pixels/second

    Returns:
        Duration in milliseconds
    """
    delta = target - current
    distance = delta.magnitude()
    return calculate_duration_from_rate(distance, rate)


def calculate_position_by_duration(
    offset: Vec2,
    rate: float
) -> float:
    """Calculate duration for relative position movement based on rate.

    Args:
        offset: Position offset vector
        rate: Movement rate in pixels/second

    Returns:
        Duration in milliseconds
    """
    distance = offset.magnitude()
    return calculate_duration_from_rate(distance, rate)
