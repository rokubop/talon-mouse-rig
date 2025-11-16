"""
Mouse Rig Examples - Comprehensive Feature Showcase

Demonstrates all core mouse rig features:
- Basic movement (direction, speed, acceleration)
- Effect system with strict syntax:
  * Effects use strict syntax: .speed.to(10), .speed.add(10), etc.
  * Shorthand like .speed(10) raises error for effects
  * Base rig and forces still allow shorthand
- On-repeat strategies: replace, stack, extend, queue, ignore, throttle
- Force system (independent entities with vector addition)
- Lifecycle effects (.over/.hold/.revert)
- Named entities with stopping
- State access and baking
- Interpolation modes for direction (slerp vs lerp)
"""

from talon import Module, actions

mod = Module()

@mod.action_class
class Actions:
    # =========================================================================
    # BASIC MOVEMENT
    # =========================================================================

    def mouse_rig_test():
        """Test function"""
        rig = actions.user.mouse_rig()
        rig.effect("test").speed.add(5).over(500).hold(1000).revert(500)

    def mouse_rig_test_two():
        """Second test function"""
        rig = actions.user.mouse_rig()
        rig.stop(500)

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

    # =========================================================================
    # SPEED CONTROL
    # =========================================================================

    def mouse_rig_speed_slow():
        """Set speed to slow"""
        rig = actions.user.mouse_rig()
        rig.speed.div(2)

    def mouse_rig_speed_normal():
        """Set speed to normal"""
        rig = actions.user.mouse_rig()
        rig.speed(3)

    def mouse_rig_speed_fast():
        """Set speed to fast"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(2)

    def mouse_rig_speed_ramp_up():
        """Smoothly ramp speed up to 30 over 1 second"""
        rig = actions.user.mouse_rig()
        rig.speed.to(10).over(1000)

    def mouse_rig_speed_ramp_down():
        """Smoothly ramp speed down to 5 over 1 second"""
        rig = actions.user.mouse_rig()
        rig.speed.to(2).over(1000, "ease_out")

    # =========================================================================
    # TEMPORARY SPEED BOOSTS (Anonymous Effects)
    # =========================================================================

    def mouse_rig_boost_instant():
        """Instant speed boost, hold 2s, instant revert"""
        rig = actions.user.mouse_rig()
        rig.speed(10)

    def mouse_rig_boost_fade():
        """Fade in boost over 300ms, hold 2s, fade out over 500ms"""
        rig = actions.user.mouse_rig()
        rig.speed.by(10).over(300).hold(1000).revert(500)

    def mouse_rig_boost_smooth():
        """Smooth boost with easing"""
        rig = actions.user.mouse_rig()
        rig.speed.by(20).over(500, "ease_in_out").hold(1500).revert(500, "ease_out")

    # =========================================================================
    # EFFECT SYSTEM (Multiplicative - Replace Mode)
    # =========================================================================

    def mouse_rig_sprint_on():
        """Enable sprint mode (2x speed) - replaces on repeated calls"""
        rig = actions.user.mouse_rig()
        rig.effect("sprint").speed.mul(2).over(1000).revert(1000)

    def mouse_rig_sprint_off():
        """Disable sprint mode"""
        rig = actions.user.mouse_rig()
        rig.effect("sprint").revert(500)

    def mouse_rig_slow_mode_on():
        """Enable slow mode (half speed) - replaces on repeated calls"""
        rig = actions.user.mouse_rig()
        rig.effect("slow").speed.div(2)

    def mouse_rig_slow_mode_off():
        """Disable slow mode"""
        rig = actions.user.mouse_rig()
        rig.effect("slow").revert(500)

    # =========================================================================
    # EFFECT SYSTEM - Strict Syntax (REQUIRED for effects)
    # =========================================================================

    def mouse_rig_boost_strict():
        """Speed boost using strict syntax - REQUIRED for effects"""
        rig = actions.user.mouse_rig()
        rig.effect("boost").speed.add(10)  # ✅ Explicit operation required

    def mouse_rig_drift_strict():
        """Drift using strict syntax"""
        rig = actions.user.mouse_rig()
        rig.effect("drift").direction.add(15)  # ✅ Explicit operation

    def mouse_rig_offset_strict():
        """Position offset using strict syntax"""
        rig = actions.user.mouse_rig()
        rig.effect("wobble").pos.add(5, 5)

    def mouse_rig_offset_reset():
        """Reset position offset"""
        rig = actions.user.mouse_rig()
        rig.effect("wobble").revert()

    # =========================================================================
    # EFFECT SYSTEM (On-Repeat Strategies)
    # =========================================================================

    def mouse_rig_boost_pad():
        """Boost pad that stacks when hit multiple times (unlimited)"""
        rig = actions.user.mouse_rig()
        rig.effect("boost_pad").speed.add(2)

    def mouse_rig_boost_pad_max():
        """Boost pad with max 3 stacks (max +30)"""
        rig = actions.user.mouse_rig()
        rig.effect("boost_pad").speed.add(10).on_repeat("stack", 3)

    def mouse_rig_boost_pad_with_timeout():
        """Boost pad that fades in/out with unlimited stacks"""
        rig = actions.user.mouse_rig()
        rig.effect("boost_pad").speed.add(10).over(1000).revert(1000)

    def mouse_rig_rage_stacks():
        """Rage buff - each stack multiplies speed by 1.2 (max 5 stacks)"""
        rig = actions.user.mouse_rig()
        rig.effect("rage").speed.mul(1.2).on_repeat("stack", 5)

    def mouse_rig_drift_extend():
        """Drift that extends duration on repeated calls"""
        rig = actions.user.mouse_rig()
        rig.effect("drift").direction.add(15).hold(2000).on_repeat("extend")

    def mouse_rig_invuln():
        """Invulnerability - ignores new calls while active"""
        rig = actions.user.mouse_rig()
        rig.effect("invuln").speed.mul(0).hold(2000).on_repeat("ignore")

    def mouse_rig_dash_throttle():
        """Dash with rate limiting (max 1 per 500ms)"""
        rig = actions.user.mouse_rig()
        rig.effect("dash").speed.add(20).hold(200).on_repeat("throttle", 500)

    # =========================================================================
    # EFFECT SYSTEM - DIRECTION (Rotation)
    # =========================================================================

    def mouse_rig_drift_on():
        """Drift right by 15 degrees"""
        rig = actions.user.mouse_rig()
        rig.effect("drift").direction.add(90)

    def mouse_rig_drift_off():
        """Stop drift"""
        rig = actions.user.mouse_rig()
        rig.effect("drift").revert(1000)

    def mouse_rig_drift_smooth():
        """Smooth drift with lifecycle"""
        rig = actions.user.mouse_rig()
        rig.effect("drift").direction.add(30)\
            .over(500)\
            .then(lambda: print("over"))\
            .hold(2000)\
            .then(lambda: print("hold"))\
            .revert(500)\
            .then(lambda: print("revert"))

    # =========================================================================
    # FORCE SYSTEM (Independent Entities)
    # =========================================================================

    def mouse_rig_gravity_on():
        """Enable gravity force"""
        rig = actions.user.mouse_rig()
        rig.force("gravity").direction(0, 1).accel(9.8)

    def mouse_rig_gravity_off():
        """Disable gravity"""
        rig = actions.user.mouse_rig()
        rig.force("gravity").stop(500)

    def mouse_rig_wind_on():
        """Wind gust from the right"""
        rig = actions.user.mouse_rig()
        rig.force("wind").direction(1, 0).speed(10)

    def mouse_rig_wind_smooth():
        """Wind with smooth fade"""
        rig = actions.user.mouse_rig()
        rig.force("wind").direction(1, 0).speed(8).over(500).hold(3000).revert(1000)

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
        rig.pos.by(10, 10).over(400)\
            .then(lambda: print("over"))\
            .hold(10000)\
            .then(lambda: print("hold"))\
            .revert(1000)\
            .then(lambda: print("revert"))

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

    def mouse_rig_turn_lerp():
        """Turn using linear interpolation (default)

        Lerp interpolates the x,y components directly (cuts across),
        while slerp rotates along the arc. Lerp is the default and works
        well for most cases. Use slerp when you want smooth rotation along
        the circular arc.rr
        """
        rig = actions.user.mouse_rig()
        rig.reverse().over(1000).revert(1000)

    def mouse_rig_reverse():
        """Smooth linear reverse - backs up motion"""
        rig = actions.user.mouse_rig()
        rig.reverse()

    # =========================================================================
    # POSITION CONTROL
    # =========================================================================

    def mouse_rig_pos_center():
        """Glide to screen center"""
        rig = actions.user.mouse_rig()
        rig.pos.to(960, 540).over(350, "ease_in_out")

    def mouse_rig_nudge_right():
        """Nudge position right"""
        rig = actions.user.mouse_rig()
        rig.pos.by(10, 10).over(400)\
            .then(lambda: print("over"))\
            .hold(2000)\
            .then(lambda: print("hold"))\
            .revert(400)\
            .then(lambda: print("revert"))

    def mouse_rig_nudge_down():
        """Nudge position down"""
        rig = actions.user.mouse_rig()
        rig.pos.by(0, 50).over(200)

    # =========================================================================
    # STOPPING & STATE
    # =========================================================================

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
