"""Examples demonstrating Mouse Rig V2 API

This file shows the unified fluent API in action.
All examples use the same RigBuilder type - no special cases.
"""

from src_v2 import rig


# ============================================================================
# BASIC MOVEMENT
# ============================================================================

def start_moving():
    """Start moving right at constant speed"""
    r = rig()
    r.direction.to(1, 0)
    r.speed.to(10)


def start_moving_shorthand():
    """Same as above using shorthand (anonymous only)"""
    r = rig()
    r.direction(1, 0)  # Shorthand for .to()
    r.speed(10)        # Shorthand for .to()


def stop():
    """Stop movement"""
    r = rig()
    r.stop()


def stop_smooth():
    """Stop smoothly over 1 second"""
    r = rig()
    r.stop(1000)


def reverse():
    """Reverse direction (180° turn)"""
    r = rig()
    r.reverse()


def reverse_smooth():
    """Smooth reverse over 1 second"""
    r = rig()
    r.reverse(1000)


# ============================================================================
# TRANSITIONS (over)
# ============================================================================

def accelerate():
    """Accelerate to speed 20 over 1 second"""
    r = rig()
    r.speed.to(20).over(1000)


def accelerate_with_easing():
    """Accelerate with ease-in-out"""
    r = rig()
    r.speed.to(20).over(1000, "ease_in_out")


def turn():
    """Turn to face upward over 500ms"""
    r = rig()
    r.direction.to(0, -1).over(500)


def rotate():
    """Rotate 90° clockwise"""
    r = rig()
    r.direction.by(90).over(500)


# ============================================================================
# RATE-BASED TRANSITIONS
# ============================================================================

def accelerate_at_rate():
    """Accelerate to 20 at a rate of 10 units/second"""
    r = rig()
    r.speed.to(20).over(rate=10)  # Takes 2 seconds if starting from 0


def rotate_at_rate():
    """Rotate 180° at 90 degrees/second"""
    r = rig()
    r.direction.by(180).over(rate=90)  # Takes 2 seconds


def move_to_position_at_rate():
    """Move to screen center at 200 pixels/second"""
    r = rig()
    r.pos.to(960, 540).over(rate=200)


# ============================================================================
# TEMPORARY EFFECTS (hold + revert)
# ============================================================================

def speed_boost():
    """Temporary speed boost for 2 seconds"""
    r = rig()
    r.speed.add(10).hold(2000)


def sprint():
    """Sprint: ramp up, hold, ramp down"""
    r = rig()
    r.speed.add(10).over(300).hold(2000).revert(500)


def dash():
    """Quick dash forward and back"""
    r = rig()
    r.pos.by(100, 0).over(200).revert(200)


# ============================================================================
# NAMED EFFECTS (tagged)
# ============================================================================

def named_boost():
    """Named speed boost that can be cancelled"""
    r = rig()
    r.tag("boost").speed.add(10).hold(5000)


def cancel_boost():
    """Cancel the boost early"""
    r = rig()
    r.tag("boost").revert(500)


def named_sprint():
    """Named sprint with full lifecycle"""
    r = rig()
    r.tag("sprint").speed.mul(2).over(500).hold(3000).revert(500)


# ============================================================================
# STACKING
# ============================================================================

def stackable_boost():
    """Speed boost that stacks (default for anonymous)"""
    r = rig()
    r.speed.add(5).hold(2000)
    # Call multiple times to stack


def limited_stack():
    """Speed boost with max 3 stacks"""
    r = rig()
    r.tag("rage").speed.add(5).stack(3).hold(2000)


# ============================================================================
# BEHAVIOR MODES
# ============================================================================

def replace_mode():
    """Each call replaces the previous"""
    r = rig()
    r.tag("dash").speed.add(20).replace().hold(1000)


def queue_mode():
    """Queue operations to execute in sequence"""
    r = rig()
    r.tag("combo").pos.by(100, 0).queue().over(500)
    # Second call waits for first to complete


def throttle_mode():
    """Ignore rapid calls (max once per 500ms)"""
    r = rig()
    r.tag("ability").speed.add(10).throttle(500).hold(1000)


def extend_mode():
    """Extend hold duration instead of stacking"""
    r = rig()
    r.tag("channel").speed.mul(0.5).extend().hold(1000)
    # Calling again extends the hold


# ============================================================================
# CALLBACKS (then)
# ============================================================================

def with_callbacks():
    """Execute callbacks at each lifecycle stage"""
    def on_ramp():
        print("Ramped up!")

    def on_hold():
        print("Holding...")

    def on_complete():
        print("Complete!")

    r = rig()
    r.speed.add(10)\
        .over(300).then(on_ramp)\
        .hold(2000).then(on_hold)\
        .revert(500).then(on_complete)


# ============================================================================
# BAKING
# ============================================================================

def permanent_change():
    """Anonymous builders bake by default"""
    r = rig()
    r.speed.add(5)  # This becomes permanent when complete


def non_baking_anonymous():
    """Anonymous but reversible"""
    r = rig()
    r.speed.add(10).bake(False).hold(2000)


def baking_tagged():
    """Tagged but permanent"""
    r = rig()
    r.tag("upgrade").speed.mul(1.5).bake(True)


def bake_all():
    """Commit all active changes to base immediately"""
    r = rig()
    r.bake()


# ============================================================================
# ORDER-AGNOSTIC API
# ============================================================================

def order_agnostic():
    """All these are equivalent (except lifecycle must be ordered)"""

    # Standard order
    r = rig()
    r.speed.add(5).over(300).hold(1000)

    # Different order
    r = rig()
    r.tag("x").over(300).speed.add(5).hold(1000)

    # Another order
    r = rig()
    r.stack().over(300).speed.add(5).tag("y")


# ============================================================================
# BEHAVIOR AS PROPERTY OR METHOD
# ============================================================================

def behavior_property():
    """Use behavior as property accessor"""
    r = rig()
    r.stack.speed.add(5)
    r.replace.direction.by(90)


def behavior_method():
    """Use behavior as method call"""
    r = rig()
    r.stack(3).speed.add(5)
    r.throttle(500).speed.add(10)


# ============================================================================
# READING STATE
# ============================================================================

def read_state():
    """Access current computed state"""
    r = rig()

    # Current state (base + all active builders)
    current_speed = r.state.speed
    current_pos = r.state.pos
    current_direction = r.state.direction

    # Base state only (baked values)
    base_speed = r.base.speed
    base_pos = r.base.pos


# ============================================================================
# COMPLEX EXAMPLES
# ============================================================================

def advanced_movement():
    """Complex movement with multiple effects"""
    r = rig()

    # Base movement
    r.direction(1, 0)
    r.speed(10)

    # Temporary boost
    r.tag("boost").speed.mul(2).hold(3000)

    # Dodge movement
    r.tag("dodge").pos.by(0, -50).over(200).revert(200)


def combo_system():
    """Chain multiple operations in sequence"""
    r = rig()

    # Each queued operation waits for previous
    r.tag("combo").pos.by(100, 0).queue().over(300)
    r.tag("combo").pos.by(0, 100).queue().over(300)
    r.tag("combo").pos.by(-100, 0).queue().over(300)
    r.tag("combo").pos.by(0, -100).queue().over(300)


def dynamic_difficulty():
    """Speed scales with stacks"""
    r = rig()

    # Each kill adds a speed boost (max 5)
    r.tag("difficulty").speed.add(2).stack(5).hold(10000)


# ============================================================================
# MIXED TIME AND RATE
# ============================================================================

def mixed_timing():
    """Mix time-based and rate-based timing"""
    r = rig()
    r.speed.to(20).over(500).hold(2000).revert(rate=10)
    # Ramp up over 500ms, hold 2s, ramp down at 10 units/sec


# ============================================================================
# POSITION EXAMPLES
# ============================================================================

def move_to_center():
    """Move to screen center"""
    r = rig()
    r.pos.to(960, 540).over(1000, "ease_in_out")


def offset_movement():
    """Move by offset"""
    r = rig()
    r.pos.by(100, 50).over(500)


def temporary_offset():
    """Move and return"""
    r = rig()
    r.pos.by(50, 0).over(200).hold(1000).revert(200)
