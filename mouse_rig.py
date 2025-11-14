"""
Talon Mouse Rig - Continuous motion-based mouse control system (PRD 8)

A fluent, stateful mouse control API with:
- Named effects with strict syntax (.effect())
- Independent force entities (.force())
- Direct mathematical operations (.to(), .mul(), .add(), .sub(), .div())
- Smooth transitions with easing
- Temporary effects with lifecycle (.over()/.hold()/.revert())
- On-repeat strategies for effect behavior
- State management and baking

Core Properties:
    rig.speed      # Speed scalar
    rig.accel      # Acceleration scalar
    rig.direction  # Direction vector
    rig.pos        # Position

Basic Usage:
    rig = actions.user.mouse_rig()
    rig.direction(1, 0)          # Set direction (right)
    rig.speed(10)                # Set base speed
    rig.speed.to(20).over(500)   # Ramp to 20 over 500ms

Explicit Entity API (PRD 8):
    rig.effect("name")   # Named effect (modifies base properties) - STRICT syntax
    rig.force("name")    # Named force (independent entity) - loose syntax

Effects (modify base properties with explicit operations - STRICT mode):
    Absolute value:
        rig.effect("boost").speed.to(10)            # Set speed to 10

    Multiplicative:
        rig.effect("sprint").speed.mul(2)           # Multiply speed by 2
        rig.effect("sprint").speed.div(2)           # Divide speed by 2

    Additive:
        rig.effect("boost").speed.add(10)           # Add 10 to speed
        rig.effect("boost").speed.by(10)            # Alias for add
        rig.effect("boost").speed.sub(5)            # Subtract 5 from speed

    On-Repeat Strategies:
        rig.effect("boost").speed.add(10).on_repeat("stack")          # Unlimited stacking
        rig.effect("boost").speed.add(10).on_repeat("stack", 3)       # Max 3 stacks
        rig.effect("boost").speed.add(10).on_repeat("replace")        # Default - replace existing
        rig.effect("boost").speed.add(10).on_repeat("extend")         # Extend duration
        rig.effect("boost").speed.add(10).on_repeat("queue")          # Queue effects
        rig.effect("boost").speed.add(10).on_repeat("ignore")         # Ignore new calls
        rig.effect("boost").speed.add(10).on_repeat("throttle", 500)  # Rate limit (ms)

    Stop:
        rig.effect("sprint").revert()               # Immediate revert
        rig.effect("sprint").revert(500)            # Fade out over 500ms

Forces (independent entities with their own state - LOOSE mode):
    Direct setters (shorthand for .to()):
        rig.force("gravity").direction(0, 1)        # Set direction
        rig.force("gravity").accel(9.8)             # Set acceleration
        rig.force("wind").velocity(5, 0)            # Set velocity directly
        rig.force("wind").speed(5)                  # Set speed

    Or explicit .to():
        rig.force("wind").speed.to(5)               # Same as .speed(5)
        rig.force("wind").direction.to(1, 0)        # Same as .direction(1, 0)

    Modifications:
        rig.force("wind").speed.add(2)              # Add to force's speed
        rig.force("wind").speed.mul(1.5)            # Scale force's speed

    Stop:
        rig.force("wind").stop(500)                 # Fade out

Composition Pipeline:
    base → effects (.mul then .add, in creation order) → forces (vector addition)

Direct Temporary Effects (anonymous, no naming needed):
    rig.speed.by(10).hold(1000).revert(500)     # Temporary speed boost
    rig.speed.by(10).over(300).revert(300)      # Fade in/out

Timing:
    Time-based:
        .over(duration, easing?)  # Animate over fixed duration

    Rate-based (no easing, constant rate):
        .rate(value)              # Context-aware rate

Lifecycle:
    .over(duration)                # Fade in over duration
    .hold(duration)                # Maintain for duration
    .revert(duration?, easing?)    # Revert to original

State Management:
    rig.state.speed       # Computed speed (base + effects + forces)
    rig.state.accel       # Computed acceleration
    rig.state.direction   # Current direction
    rig.state.pos         # Current position
    rig.state.velocity    # Total velocity vector

    rig.base.speed        # Base speed only
    rig.base.accel        # Base acceleration only
    rig.base.direction    # Base direction only

Baking & Stopping:
    rig.bake()                      # Flatten effects into base, clear all
    rig.stop()                      # Bake, clear, speed=0 (instant)
    rig.stop(500, "ease_out")       # Bake, clear, decelerate over 500ms

Direction:
    rig.direction(1, 0)              # Right
    rig.direction(0, 1)              # Down
    rig.direction(-1, -1)            # Up-left diagonal
    rig.direction(1, 0).over(500)    # Smooth rotation
    rig.direction(1, 0).rate(90)     # Rotate at 90°/sec
    rig.reverse()                    # 180° turn

Position:
    rig.pos.to(100, 200)             # Instant move
    rig.pos.to(100, 200).over(1000)  # Glide over 1s
    rig.pos.by(50, 0)                # Move by offset

Complete Examples:
    # WASD with sprint
    rig.direction(1, 0).speed(10)                       # Move right
    rig.effect("sprint").speed.mul(2)                   # Hold shift to sprint
    rig.effect("sprint").stop()                         # Release shift

    # Stacking boost pads
    rig.effect("boost").speed.add(5).max.stacks(3)      # Hit pad (stacks up to 3)

    # Gravity + wind
    rig.force("gravity").direction(0, 1).accel(9.8)     # Always pulls down
    rig.force("wind").velocity(5, 0).hold(3000).revert(1000)  # Temporary gust

    # Temporary speed boost (anonymous)
    rig.speed.by(10).hold(2000).revert(1000)
"""

from talon import Module, actions, settings

# Import from refactored modules using relative imports
from .settings import mod
from .src.state import RigState, get_rig
from .src.core import _windows_raw_available


@mod.action_class
class Actions:
    def mouse_rig() -> RigState:
        """Get the mouse rig instance

        Example:
            rig = actions.user.mouse_rig()
            rig.direction((1, 0))
            rig.speed(10)
        """
        return get_rig()

    def mouse_rig_state() -> dict:
        """Get the current state of the mouse rig

        Returns a dictionary with current rig state including:
        - position: Current mouse position (x, y)
        - direction: Direction vector (x, y)
        - direction_cardinal: Cardinal direction name ("right", "left", "up", "down", etc.)
        - speed: Current cruise speed
        - cruise_velocity: Cruise velocity (x, y)
        - total_velocity: Total velocity including overlays (x, y)
        - Active overlays/transitions counts
        - is_ticking: Whether the rig is actively running

        Example:
            state = actions.user.mouse_rig_state()
            print(f"Speed: {state['speed']}")
            print(f"Direction: {state['direction_cardinal']}")
        """
        rig = get_rig()
        return rig.state_dict

    def mouse_rig_stop() -> None:
        """Stop the mouse rig frame loop"""
        rig = get_rig()
        rig.stop()

    def mouse_rig_set_type_talon() -> None:
        """Set mouse movement type to Talon (default, works for most apps)"""
        settings.set("user.mouse_rig_movement_type", "talon")

    def mouse_rig_set_type_windows_raw() -> None:
        """Set mouse movement type to Windows raw input (for some games)"""
        if not _windows_raw_available:
            print("Warning: Windows raw input not available (pywin32 not installed)")
            return
        settings.set("user.mouse_rig_movement_type", "windows_raw")

    def mouse_rig_set_scale(scale: float) -> None:
        """Set movement scale multiplier

        Args:
            scale: Scale factor (1.0 = normal, 2.0 = double, 0.5 = half)
        """
        settings.set("user.mouse_rig_scale", scale)
