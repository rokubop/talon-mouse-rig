"""
Mouse Rig Examples - Comprehensive Feature Showcase

Demonstrates all core mouse rig features:
- Basic movement (direction, speed, acceleration)
- Transform system (scale/shift with .to/.by stacking)
- Force system (independent entities with vector addition)
- Lifecycle effects (.over/.hold/.revert)
- Named entities with stopping
- State access and baking
"""

from talon import Module, actions

mod = Module()

@mod.action_class
class Actions:
    # =========================================================================
    # BASIC MOVEMENT
    # =========================================================================

    def mouse_rig_go_right():
        """Move right at normal speed"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(rig.state.speed or 3)

    def mouse_rig_go_left():
        """Move left at normal speed"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        rig.speed(rig.state.speed or 3)

    def mouse_rig_go_up():
        """Move up at normal speed"""
        rig = actions.user.mouse_rig()
        rig.direction(0, -1)
        rig.speed(rig.state.speed or 3)

    def mouse_rig_go_down():
        """Move down at normal speed"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)
        rig.speed(rig.state.speed or 3)

    def mouse_rig_go_up_right():
        """Move diagonally up-right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, -1)
        rig.speed(rig.state.speed or 3)

    def mouse_rig_go_up_left():
        """Move diagonally up-left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, -1)
        rig.speed(rig.state.speed or 3)

    def mouse_rig_go_down_right():
        """Move diagonally down-right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 1)
        rig.speed(rig.state.speed or 3)

    def mouse_rig_go_down_left():
        """Move diagonally down-left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 1)
        rig.speed(rig.state.speed or 3)

    # =========================================================================
    # SPEED CONTROL
    # =========================================================================

    def mouse_rig_speed_slow():
        """Set speed to slow"""
        rig = actions.user.mouse_rig()
        rig.speed(1)

    def mouse_rig_speed_normal():
        """Set speed to normal"""
        rig = actions.user.mouse_rig()
        rig.speed(3)

    def mouse_rig_speed_fast():
        """Set speed to fast"""
        rig = actions.user.mouse_rig()
        rig.speed(7)

    def mouse_rig_speed_ramp_up():
        """Smoothly ramp speed up to 30 over 1 second"""
        rig = actions.user.mouse_rig()
        rig.speed.to(10).over(1000)

    def mouse_rig_speed_ramp_down():
        """Smoothly ramp speed down trro 5 over 1 second"""
        rig = actions.user.mouse_rig()
        rig.speed.to(2).over(1000, "ease_out")

    # =========================================================================
    # TEMPORARY SPEED BOOSTS (Anonymous Effects)
    # =========================================================================

    def mouse_rig_boost_instant():
        """Instant speed boost, hold 2s, instant revert"""
        rig = actions.user.mouse_rig()
        rig.speed.by(10).over(2000).revert(1000)

    def mouse_rig_boost_fade():
        """Fade in boost over 300ms, hold 2s, fade out over 500ms"""
        rig = actions.user.mouse_rig()
        rig.speed.by(10).over(300).hold(2000).revert(500, "ease_out")

    def mouse_rig_boost_smooth():
        """Smooth boost with easing"""
        rig = actions.user.mouse_rig()
        rig.speed.by(20).over(500, "ease_in_out").hold(1500).revert(500, "ease_out")

    def mouse_rig_slowdown():
        """Temporary slowdown effect"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(0.3).hold(1000).revert(500)

    # =========================================================================
    # TRANSFORM SYSTEM - SCALE (Multiplicative)
    # =========================================================================

    def mouse_rig_sprint_on():
        """Enable sprint mode (2x speed)"""
        rig = actions.user.mouse_rig()
        rig("sprint").scale.speed.to(2)
        rig("sprint").scale.speed.to(2)

    def mouse_rig_sprint_off():
        """Disable sprint mode"""
        rig = actions.user.mouse_rig()
        rig("sprint").stop(500)

    def mouse_rig_sprint_smooth():
        """Sprint with smooth fade in/out"""
        rig = actions.user.mouse_rig()
        rig("sprint").scale.speed.to(2).over(300).hold(2000).revert(500)

    def mouse_rig_boost_pad():
        """Boost pad that stacks when hit multiple times"""
        rig = actions.user.mouse_rig()
        rig("boost_pad").shift.speed.by(10).hold(2000).revert(1000)

    def mouse_rig_boost_pad_max():
        """Boost pad with max 3 stacks"""
        rig = actions.user.mouse_rig()
        rig("boost_pad").shift.speed.by(10).hold(2000).revert(1000).max.stack(3)

    # =========================================================================
    # TRANSFORM SYSTEM - DIRECTION (Rotation)
    # =========================================================================

    def mouse_rig_drift_on():
        """Drift right by 15 degrees"""
        rig = actions.user.mouse_rig()
        rig("drift").shift.direction.to(15)

    def mouse_rig_drift_off():
        """Stop drift"""
        rig = actions.user.mouse_rig()
        rig("drift").stop(500)

    def mouse_rig_drift_smooth():
        """Smooth drift with lifecycle"""
        rig = actions.user.mouse_rig()
        rig("drift").shift.direction.to(30).over(500).hold(2000).revert(500)

    # =========================================================================
    # FORCE SYSTEM (Independent Entities)
    # =========================================================================

    def mouse_rig_gravity_on():
        """Enable gravity force"""
        rig = actions.user.mouse_rig()
        rig("gravity").direction(0, 1).accel(9.8)

    def mouse_rig_gravity_off():
        """Disable gravity"""
        rig = actions.user.mouse_rig()
        rig("gravity").stop(500)

    def mouse_rig_wind_on():
        """Wind gust from the right"""
        rig = actions.user.mouse_rig()
        rig("wind").velocity(10, 0).hold(2000).revert(1000)

    def mouse_rig_wind_smooth():
        """Wind with smooth fade"""
        rig = actions.user.mouse_rig()
        rig("wind").direction(1, 0).speed(8).over(500).hold(3000).revert(1000)

    # =========================================================================
    # ACCELERATION
    # =========================================================================

    def mouse_rig_accel_on():
        """Enable constant acceleration"""
        rig = actions.user.mouse_rig()
        rig.accel(5)

    def mouse_rig_accel_off():
        """Disable acceleration"""
        rig = actions.user.mouse_rig()
        rig.accel(0)

    def mouse_rig_accel_burst():
        """Temporary acceleration boost"""
        rig = actions.user.mouse_rig()
        rig.accel.by(10).hold(2000).revert(500)

    # =========================================================================
    # SMOOTH TURNS
    # =========================================================================

    def mouse_rig_turn_right():
        """Smooth 90° turn right"""
        rig = actions.user.mouse_rig()
        rig.direction.by(90).over(500, "ease_in_out")

    def mouse_rig_turn_left():
        """Smooth 90° turn left"""
        rig = actions.user.mouse_rig()
        rig.direction.by(-90).over(500, "ease_in_out")

    def mouse_rig_reverse():
        """180° turn"""
        rig = actions.user.mouse_rig()
        rig.reverse().over(500)

    # =========================================================================
    # POSITION CONTROL
    # =========================================================================

    def mouse_rig_pos_center():
        """Glide to screen center"""
        rig = actions.user.mouse_rig()
        rig.pos.to(960, 540).over(1000, "ease_in_out")

    def mouse_rig_nudge_right():
        """Nudge position right"""
        rig = actions.user.mouse_rig()
        rig.pos.by(50, 0).over(200)

    def mouse_rig_nudge_down():
        """Nudge position down"""
        rig = actions.user.mouse_rig()
        rig.pos.by(0, 50).over(200)

    # =========================================================================
    # STOPPING & STATE
    # =========================================================================

    def mouse_rig_stop():
        """Immediate stop"""
        rig = actions.user.mouse_rig()
        rig.stop()

    def mouse_rig_stop_smooth():
        """Smooth deceleration to stop"""
        rig = actions.user.mouse_rig()
        rig.stop(1000, "ease_out")

    def mouse_rig_bake():
        """Bake all transforms/forces into base state"""
        rig = actions.user.mouse_rig()
        rig.bake()

    def mouse_rig_show_state():
        """Print current state"""
        rig = actions.user.mouse_rig()
        print(f"Speed: {rig.state.speed}")
        print(f"Direction: {rig.state.direction}")
        print(f"Position: {rig.state.pos}")
