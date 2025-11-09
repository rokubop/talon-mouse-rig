"""
Mouse Rig Examples - PRD 5 API

Basic examples demonstrating the PRD5 API:
- Direction control
- Speed control
- Temporary effects (.over/.hold/.revert)
- Named modifiers and forces
- Rate-based timing
- State management and baking
"""

from talon import Module, actions

mod = Module()

@mod.action_class
class Actions:
    # =========================================================================
    # DIRECTION CONTROL
    # =========================================================================

    def mouse_rig_go_right():
        """Move right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(2)
        # rig

    def mouse_rig_go_left():
        """Move left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        rig.speed(2)

    def mouse_rig_go_up():
        """Move up"""
        rig = actions.user.mouse_rig()
        rig.direction(0, -1)
        rig.speed(2)

    def mouse_rig_go_down():
        """Move down"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)
        rig.speed(2)

    def mouse_rig_go_up_right():
        """Move diagonally up-right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, -1)
        rig.speed(2)

    def mouse_rig_go_up_left():
        """Move diagonally up-left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, -1)
        rig.speed(2)

    def mouse_rig_go_down_right():
        """Move diagonally down-right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 1)
        rig.speed(2)

    def mouse_rig_go_down_left():
        """Move diagonally down-left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 1)
        rig.speed(2)

    # =========================================================================
    # SPEED CONTROL
    # =========================================================================

    def mouse_rig_speed_slow():
        """Set speed to slow"""
        rig = actions.user.mouse_rig()
        rig.speed(5)

    def mouse_rig_speed_normal():
        """Set speed to normal"""
        rig = actions.user.mouse_rig()
        rig.speed(10)

    def mouse_rig_speed_fast():
        """Set speed to fast"""
        rig = actions.user.mouse_rig()
        rig.speed(20)

    def mouse_rig_speed_up():
        """Increase speed"""
        rig = actions.user.mouse_rig()
        rig.speed.by(5)

    def mouse_rig_speed_down():
        """Decrease speed"""
        rig = actions.user.mouse_rig()
        rig.speed.by(-5)

    def mouse_rig_speed_ramp():
        """Smoothly ramp speed up"""
        rig = actions.user.mouse_rig()
        rig.speed.to(5).over(1000, "ease_out")

    # =========================================================================
    # STOP CONTROL
    # =========================================================================

    def mouse_rig_stop():
        """Stop immediately"""
        rig = actions.user.mouse_rig()
        rig.stop()

    def mouse_rig_stop_soft():
        """Stop gradually over 1 second"""
        rig = actions.user.mouse_rig()
        rig.stop(1000, "ease_out")

    def mouse_rig_stop_gentle():
        """Stop very gradually over 2 seconds"""
        rig = actions.user.mouse_rig()
        rig.stop(2000, "ease_in")

    # =========================================================================
    # TEMPORARY EFFECTS
    # =========================================================================

    def mouse_rig_boost_instant():
        """Speed boost - instant on, hold, instant off"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(2).hold(1000)

    def mouse_rig_boost_fade():
        """Speed boost - instant on, hold, fade off"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(4).hold(1000).revert(1000)

    def mouse_rig_boost_smooth():
        """Speed boost - fade in, hold, fade out"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(4).over(1000).hold(1000).revert(1000, "ease_in")

    def mouse_rig_slowdown():
        """Temporary slowdown"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(0.1).hold(1000).revert(500)

    # =========================================================================
    # NAMED MODIFIERS
    # =========================================================================

    def mouse_rig_turbo_on():
        """Start turbo mode (named modifier)"""
        rig = actions.user.mouse_rig()
        rig.modifier("turbo").speed.mul(2)

    def mouse_rig_turbo_off():
        """Stop turbo mode"""
        rig = actions.user.mouse_rig()
        rig.modifier("turbo").stop(500)

    def mouse_rig_thrust_on():
        """Start thrust acceleration (force)"""
        rig = actions.user.mouse_rig()
        rig.force("thrust").accel(10)

    def mouse_rig_thrust_off():
        """Stop thrust"""
        rig = actions.user.mouse_rig()
        rig.force("thrust").stop(2000)

    def mouse_rig_drift_on():
        """Add directional drift modifier"""
        rig = actions.user.mouse_rig()
        rig.modifier("drift").direction.by(15)

    def mouse_rig_drift_off():
        """Remove drift"""
        rig = actions.user.mouse_rig()
        rig.modifier("drift").stop(1000)

    # =========================================================================
    # NAMED FORCES
    # =========================================================================

    def mouse_rig_gravity_on():
        """Enable gravity force"""
        rig = actions.user.mouse_rig()
        gravity = rig.force("gravity")
        gravity.speed(9.8)
        gravity.direction(0, 1)  # Downward

    def mouse_rig_gravity_off():
        """Disable gravity"""
        rig = actions.user.mouse_rig()
        rig.force("gravity").stop(500)

    def mouse_rig_wind_on():
        """Enable wind force from left"""
        rig = actions.user.mouse_rig()
        wind = rig.force("wind")
        wind.speed(5)
        wind.direction(-1, 0)  # From right to left

    def mouse_rig_wind_off():
        """Disable wind"""
        rig = actions.user.mouse_rig()
        rig.force("wind").stop(500)

    # =========================================================================
    # ACCELERATION CONTROL
    # =========================================================================

    def mouse_rig_accel_on():
        """Start accelerating"""
        rig = actions.user.mouse_rig()
        rig.accel(5)  # Accelerate at 5 units/sec²

    def mouse_rig_accel_off():
        """Stop accelerating"""
        rig = actions.user.mouse_rig()
        rig.accel(0)

    def mouse_rig_accel_boost():
        """Temporary acceleration burst"""
        rig = actions.user.mouse_rig()
        rig.accel.to(10).over(500).revert(1000)

    # =========================================================================
    # RATE-BASED TIMING
    # =========================================================================

    def mouse_rig_ramp_by_rate():
        """Ramp speed at specific rate (10 units/sec)"""
        rig = actions.user.mouse_rig()
        rig.speed.to(50).rate(10)

    def mouse_rig_turn_by_rate():
        """Turn at specific rate (90 degrees/sec)"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1).rate(90)

    def mouse_rig_accel_speed():
        """Increase speed via acceleration"""
        rig = actions.user.mouse_rig()
        rig.speed.to(30).rate.accel(5)

    # =========================================================================
    # SMOOTH TURNS
    # =========================================================================

    def mouse_rig_turn_right():
        """Smooth turn to right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0).over(300)

    def mouse_rig_turn_down():
        """Smooth turn to down"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1).over(300)

    def mouse_rig_reverse():
        """Turn 180 degrees"""
        rig = actions.user.mouse_rig()
        rig.reverse().over(500)

    # =========================================================================
    # POSITION CONTROL
    # =========================================================================

    def mouse_rig_pos_center():
        """Move to screen center"""
        rig = actions.user.mouse_rig()
        rig.pos.to(960, 540).over(350, "ease_in_out")

    def mouse_rig_pos_corner():
        """Move to top-left corner"""
        rig = actions.user.mouse_rig()
        rig.pos.by(100, 100).over(800).revert(800).then(lambda: print("returned"))

    def mouse_rig_nudge_right():
        """Nudge position right"""
        rig = actions.user.mouse_rig()
        rig.pos.by(100, 0).over(200)

    # =========================================================================
    # STATE & BAKING
    # =========================================================================

    def mouse_rig_show_state():
        """Print current state"""
        rig = actions.user.mouse_rig()
        print(f"Speed: {rig.state.speed}")
        print(f"Base Speed: {rig.base.speed}")
        print(f"Position: {rig.state.pos}")
        print(f"Direction: {rig.state.direction}")

    def mouse_rig_bake_state():
        """Bake current state into base"""
        rig = actions.user.mouse_rig()
        rig.bake()
        print("State baked - effects cleared")

    # =========================================================================
    # LAMBDA EXAMPLES
    # =========================================================================

    def mouse_rig_relative_boost():
        """Boost by 50% of current speed"""
        rig = actions.user.mouse_rig()
        rig.speed.by(lambda state: state.speed * 0.5).revert(1000)

    def mouse_rig_double_speed():
        """Double current speed temporarily"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(lambda state: 2).hold(2000).revert(500)