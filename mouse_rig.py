"""
Talon Mouse Rig V2 - Unified continuous motion-based mouse control (PRD10)

A fluent, stateful mouse control API with unified builder pattern:
- Single builder type (RigBuilder) for all operations
- Order-agnostic fluent API
- Tagged and anonymous builders
- Smooth transitions with lifecycle (over/hold/revert)
- Behavior modes (stack, replace, queue, extend, throttle, ignore)
- Bake control for persistence
- Rate-based and time-based transitions

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

Operators:
    .to(value)       # Set absolute value
    .add(value)      # Add delta
    .by(value)       # Alias for add
    .sub(value)      # Subtract delta
    .mul(value)      # Multiply
    .div(value)      # Divide

    Shorthand (anonymous only):
        rig.speed(10)        # Shorthand for .to(10)
        rig.direction(1, 0)  # Shorthand for .to(1, 0)

Lifecycle (optional):
    Time-based:
        .over(ms, easing?)           # Transition duration
        .hold(ms)                     # Hold duration
        .revert(ms?, easing?)         # Revert duration
        .then(callback)               # Execute callback after stage

    Rate-based:
        .over(rate=X)                 # Transition at rate (units/sec, degrees/sec, pixels/sec)
        .revert(rate=X)               # Revert at rate

    Examples:
        rig.speed.to(20).over(500)                    # Time-based
        rig.speed.to(20).over(rate=10)                # Rate-based (10 units/sec)
        rig.direction.by(90).over(rate=45)            # 45 degrees/sec
        rig.pos.to(960, 540).over(rate=200)           # 200 pixels/sec

        rig.speed.add(10).over(300).hold(2000).revert(500)  # Full lifecycle
        rig.speed.add(10)\
            .over(300).then(lambda: print("ramped"))\
            .hold(2000).then(lambda: print("holding"))\
            .revert(500).then(lambda: print("done"))

Behavior Modes (what happens on repeat):
    .stack(max?)         # Stack effects (unlimited or max count)
    .replace()           # Cancel previous, start new
    .queue()             # Wait for current to finish
    .extend()            # Extend hold duration
    .throttle(ms)        # Rate limit
    .ignore()            # Ignore while active

    Can use as property or method:
        rig.stack.speed.add(5)           # Property
        rig.stack(3).speed.add(5)        # Method with max

    Defaults:
        Anonymous (no tag): stack() unlimited
        Tagged: stack() unlimited

Tagged vs Anonymous:
    # Anonymous (auto-bakes when complete)
    rig.speed.add(5)

    # Tagged (can be controlled/reverted)
    rig.tag("sprint").speed.mul(2)
    rig.tag("sprint").revert(500)        # Cancel it later

    Examples:
        rig.tag("boost").speed.add(10).stack(3).hold(2000)
        rig.tag("sprint").speed.mul(2).replace()
        rig.tag("dash").speed.add(20).throttle(500)

Bake Control:
    .bake(true/false)    # Control whether changes persist to base

    Defaults:
        Anonymous: bake=true (changes become permanent)
        Tagged: bake=false (changes are reversible)

    Examples:
        rig.speed.add(5)                           # Anonymous - bakes
        rig.speed.add(5).bake(false)               # Anonymous - reversible
        rig.tag("boost").speed.add(10)             # Tagged - reversible
        rig.tag("boost").speed.add(10).bake(true)  # Tagged - permanent

State Access:
    rig.state.speed       # Computed speed (base + all active builders)
    rig.state.accel       # Computed acceleration
    rig.state.direction   # Current direction
    rig.state.pos         # Current position

    rig.base.speed        # Base speed only (baked values)
    rig.base.accel        # Base acceleration only
    rig.base.direction    # Base direction only
    rig.base.pos          # Base position only

Special Operations:
    rig.stop()            # Speed to 0 (instant)
    rig.stop(1000)        # Speed to 0 over 1 second
    rig.reverse()         # 180° turn (instant)
    rig.reverse(1000)     # 180° turn over 1 second
    rig.bake()            # Commit all active builders to base

Direction:
    rig.direction(1, 0)                   # Set direction (right)
    rig.direction.to(0, 1)                # Set direction (down)
    rig.direction.by(90)                  # Rotate 90° clockwise
    rig.direction.by(-90)                 # Rotate 90° counter-clockwise
    rig.direction.to(1, 0).over(500)      # Smooth rotation
    rig.direction.by(180).over(rate=90)   # Rotate at 90°/sec

Position:
    rig.pos.to(960, 540)                  # Move to position (instant)
    rig.pos.to(960, 540).over(1000)       # Glide over 1 second
    rig.pos.by(50, 0)                     # Move by offset
    rig.pos.by(50, 0).over(rate=100)      # Move at 100 pixels/sec

Complete Examples:
    # Basic movement
    rig.direction(1, 0)
    rig.speed(10)

    # Temporary speed boost (anonymous)
    rig.speed.add(10).hold(2000)

    # Sprint (tagged, can cancel)
    rig.tag("sprint").speed.mul(2).over(500).hold(3000).revert(500)
    rig.tag("sprint").revert()            # Cancel early

    # Stacking boosts (max 3)
    rig.tag("rage").speed.add(5).stack(3).hold(2000)

    # Queued combo
    rig.tag("combo").pos.by(100, 0).queue().over(500)
    rig.tag("combo").pos.by(0, 100).queue().over(500)

    # Throttled ability
    rig.tag("dash").speed.add(20).throttle(500).hold(1000)

    # Order-agnostic
    rig.speed.add(5).over(300).tag("x")
    rig.tag("x").over(300).speed.add(5)   # Equivalent
"""

from talon import Module, actions, settings

# Import V2 implementation
from .settings import mod
from .src_v2 import rig as get_rig_v2, reload_rig
from .src_v2.core import _windows_raw_available


@mod.action_class
class Actions:
    def mouse_rig():
        """Get the mouse rig V2 instance

        Example:
            rig = actions.user.mouse_rig()
            rig.direction(1, 0)
            rig.speed(10)
        """
        return get_rig_v2()

    def mouse_rig_stop() -> None:
        """Stop the mouse rig (speed to 0)"""
        rig = get_rig_v2()
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

    def mouse_rig_bake() -> None:
        """Bake all active builders to base state"""
        rig = get_rig_v2()
        rig.bake()

    def mouse_rig_reverse(ms: float = None) -> None:
        """Reverse direction (180° turn)

        Args:
            ms: Optional transition duration in milliseconds
        """
        rig = get_rig_v2()
        rig.reverse(ms)

    def mouse_rig_reload() -> None:
        """Reload rig modules to pick up code changes

        Use this instead of restarting Talon when developing.
        """
        reload_rig()
