"""
Mouse Rig - Example Usage

This file demonstrates various ways to use the mouse rig system.
Use these examples as a starting point for your own commands.
"""

from talon import Module, actions, cron, screen
import time

mod = Module()

# =============================================================================
# BASIC EXAMPLES
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_example_basic():
        """Basic continuous motion"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)  # Move right
        rig.speed(5)

    def mouse_rig_example_stop():
        """Stop all movement"""
        rig = actions.user.mouse_rig()
        # rig.halt()
        rig.stop()

    def mouse_rig_example_stop_soft():
        """Stop movement gradually"""
        rig = actions.user.mouse_rig()
        rig.stop().over(500)

    def mouse_rig_example_cruise():
        """Set direction and cruise speed"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)  # Move down
        rig.speed(3)

    def mouse_rig_example_smooth_speed():
        """Smoothly change speed"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(0)
        rig.speed(10).over(5000)  # Ramp to 10 over 500ms

    def mouse_rig_example_turn():
        """Smooth turn while moving"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)  # Set direction to right (instant)
        rig.speed(5)  # Set speed to 5 (instant)
        rig.direction(0, 1).over(300)  # Smoothly turn from right to down over 300ms

    def mouse_rig_example_decelerate():
        """Gentle deceleration to stop"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10)
        rig.decelerate(2)  # Cruise speed decreases at 2 units/sec until 0
        # Can also use alias: rig.decel(2)

# =============================================================================
# CARDINAL DIRECTIONS (useful for voice commands)
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_go_right(speed: int = 5):
        """Move right at specified speed"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(speed)

    def mouse_rig_go_left(speed: int = 5):
        """Move left at specified speed"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        rig.speed(speed)

    def mouse_rig_go_up(speed: int = 5):
        """Move up at specified speed"""
        rig = actions.user.mouse_rig()
        rig.direction(0, -1)
        rig.speed(speed)

    def mouse_rig_go_down(speed: int = 5):
        """Move down at specified speed"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)
        rig.speed(speed)

    def mouse_rig_go_up_right(speed: int = 5):
        """Move diagonally up-right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, -1)
        rig.speed(speed)

    def mouse_rig_go_up_left(speed: int = 5):
        """Move diagonally up-left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, -1)
        rig.speed(speed)

    def mouse_rig_go_down_right(speed: int = 5):
        """Move diagonally down-right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 1)
        rig.speed(speed)

    def mouse_rig_go_down_left(speed: int = 5):
        """Move diagonally down-left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 1)
        rig.speed(speed)

# =============================================================================
# SPEED CONTROLS
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_speed_up():
        """Increase speed by 2"""
        rig = actions.user.mouse_rig()
        rig.speed.add(2)

    def mouse_rig_speed_down():
        """Decrease speed by 2"""
        rig = actions.user.mouse_rig()
        rig.speed.sub(2)

    def mouse_rig_turbo():
        """Boost speed temporarily"""
        rig = actions.user.mouse_rig()
        rig.boost(16).over(800)

    def mouse_rig_accelerate():
        """Continuously accelerate (like pressing gas pedal)"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(2)
        rig.accelerate(5)  # Speed increases at 5 units/sec

    def mouse_rig_slow_down():
        """Continuously decelerate (like light braking)"""
        rig = actions.user.mouse_rig()
        rig.decelerate(3)  # Speed decreases at 3 units/sec until 0

    def mouse_rig_thrust_burst():
        """Temporary acceleration burst"""
        rig = actions.user.mouse_rig()
        rig.thrust(8).over(500)  # Accelerate for 0.5 seconds

    def mouse_rig_resist_bump():
        """Temporary slowdown (like hitting rough terrain)"""
        rig = actions.user.mouse_rig()
        rig.resist(4).over(300)  # Temporary deceleration for 0.3 seconds

    def mouse_rig_resist():
        """Basic resist command"""
        rig = actions.user.mouse_rig()
        rig.resist(5).over(500)

    def mouse_rig_boost():
        """Basic boost command"""
        rig = actions.user.mouse_rig()
        rig.boost(10).over(500)

    def mouse_rig_reverse():
        """Reverse direction"""
        rig = actions.user.mouse_rig()
        rig.reverse().over(500)

    def mouse_rig_turn_up():
        """Turn to up direction"""
        rig = actions.user.mouse_rig()
        rig.direction(0, -1).over(300)

    def mouse_rig_turn_down():
        """Turn to down direction"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1).over(300)

    def mouse_rig_turn_left():
        """Turn to left direction"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0).over(300)

    def mouse_rig_turn_right():
        """Turn to right direction"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0).over(300)

    def mouse_rig_turn_one_eighty():
        """Turn 180 degrees"""
        rig = actions.user.mouse_rig()
        rig.reverse().over(500)

# =============================================================================
# POSITION CONTROLS
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_position_middle():
        """Move to middle of screen"""
        rig = actions.user.mouse_rig()
        main_screen = screen.main()
        center_x = main_screen.width // 2
        center_y = main_screen.height // 2
        rig.pos.to(center_x, center_y).over(500).ease("ease_in_out")

    def mouse_rig_position_top_left():
        """Move to top left corner"""
        rig = actions.user.mouse_rig()
        rig.pos.to(100, 100).over(500)

    def mouse_rig_position_top_right():
        """Move to top right corner"""
        rig = actions.user.mouse_rig()
        main_screen = screen.main()
        rig.pos.to(main_screen.width - 100, 100).over(500).ease("ease_in_out")

    def mouse_rig_position_bottom_left():
        """Move to bottom left corner"""
        rig = actions.user.mouse_rig()
        main_screen = screen.main()
        rig.pos.to(100, main_screen.height - 100).over(500).ease("ease_in_out")

    def mouse_rig_position_bottom_right():
        """Move to bottom right corner"""
        rig = actions.user.mouse_rig()
        main_screen = screen.main()
        rig.pos.to(main_screen.width - 100, main_screen.height - 100).over(500).ease("ease_in_out")

    def mouse_rig_nudge_right():
        """Nudge right 50px while maintaining cruise"""
        rig = actions.user.mouse_rig()
        rig.pos.by(50, 0).over(150).ease("ease_out")

    def mouse_rig_nudge_left():
        """Nudge left 50px while maintaining cruise"""
        rig = actions.user.mouse_rig()
        rig.pos.by(-50, 0).over(150).ease("ease_out")

    def mouse_rig_nudge_up():
        """Nudge up 50px while maintaining cruise"""
        rig = actions.user.mouse_rig()
        rig.pos.by(0, -50).over(150).ease("ease_out")

    def mouse_rig_nudge_down():
        """Nudge down 50px while maintaining cruise"""
        rig = actions.user.mouse_rig()
        rig.pos.by(0, 50).over(150).ease("ease_out")

# =============================================================================
# ADVANCED EXAMPLES
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_example_dash():
        """Quick dash in current direction"""
        rig = actions.user.mouse_rig()
        rig.boost(15).over(150)

    def mouse_rig_example_smooth_cruise():
        """Start cruising with eased acceleration"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(0)
        rig.speed(8).over(400).ease("ease_in_out")

    def mouse_rig_example_orbit():
        """Circle motion (requires continuous direction updates)"""
        rig = actions.user.mouse_rig()
        rig.speed(5)

        # This is a conceptual example - in practice you'd need
        # a loop or repeated voice commands to continuously update direction
        angles = [0, 45, 90, 135, 180, 225, 270, 315]
        for angle in angles:
            import math
            rad = math.radians(angle)
            x = math.cos(rad)
            y = math.sin(rad)
            rig.direction(x, y).over(200)
            time.sleep(0.2)

    def mouse_rig_example_glide_to_corner():
        """Glide to screen corner with easing"""
        rig = actions.user.mouse_rig()
        rig.pos.to(100, 100).over(600).ease("ease_in_out")

    def mouse_rig_example_patrol():
        """Patrol back and forth"""
        rig = actions.user.mouse_rig()

        # Move right
        rig.direction(1, 0)
        rig.speed(5)

        def reverse():
            rig.direction(-1, 0)
            cron.after("2s", go_right)

        def go_right():
            rig.direction(1, 0)
            cron.after("2s", reverse)

        cron.after("2s", reverse)

# =============================================================================
# PEDAL-BASED MOVEMENT (from PRD)
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_pedal_left_press():
        """Press left pedal - accelerate left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        rig.accelerate(8)  # Start accelerating left continuously

    def mouse_rig_pedal_left_release():
        """Release left pedal - decelerate"""
        rig = actions.user.mouse_rig()
        rig.decelerate(3.0)  # Slow down at 3 units/sec

    def mouse_rig_pedal_right_press():
        """Press right pedal - accelerate right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.accelerate(8)  # Start accelerating right continuously

    def mouse_rig_pedal_right_release():
        """Release right pedal - decelerate"""
        rig = actions.user.mouse_rig()
        rig.decelerate(3.0)  # Slow down at 3 units/sec

# =============================================================================
# UTILITY ACTIONS
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_reset():
        """Reset rig to stopped state"""
        rig = actions.user.mouse_rig()
        rig.halt()
        rig.direction(1, 0)

    def mouse_rig_set_max_speed(speed: float):
        """Set maximum speed limit"""
        rig = actions.user.mouse_rig()
        rig.limits_max_speed = speed

# =============================================================================
# QA TEST ACTIONS - SPEED TRANSITIONS
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_speed_instant():
        """Test instant speed change"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.speed(10)

    def mouse_rig_test_speed_ramp():
        """Test speed ramp over time"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(2)
        rig.speed(10).over(5000)

    def mouse_rig_test_speed_add():
        """Test adding to speed instantly"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("200ms")
        rig.speed.add(3)

    def mouse_rig_test_speed_add_over():
        """Test adding to speed over time"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("200ms")
        rig.speed.add(5).over(500)

# =============================================================================
# QA TEST ACTIONS - ACCELERATE, DECELERATE AND HALT
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_decelerate():
        """Test decelerate to stop"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10)
        # actions.sleep("500ms")
        rig.decelerate(10)  # Slow down at 2 units/sec

    def mouse_rig_test_accelerate():
        """Test accelerate from low speed"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(2)
        actions.sleep("500ms")
        rig.accelerate(3.0)  # Speed up at 3 units/sec

    def mouse_rig_test_halt():
        """Test immediate halt"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10)
        actions.sleep("500ms")
        rig.halt()

    def mouse_rig_test_decelerate_cancels_ramp():
        """Test that decelerate cancels speed ramp"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.speed(10).over(1000)
        actions.sleep("200ms")
        rig.decelerate(3.0)

# =============================================================================
# QA TEST ACTIONS - SPEED LIMITS
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_max_speed():
        """Test max speed clamping"""
        rig = actions.user.mouse_rig()
        rig.limits_max_speed = 10.0
        rig.direction(1, 0)
        rig.speed(20)

    def mouse_rig_test_speed_add_with_limit():
        """Test speed add respects max speed"""
        rig = actions.user.mouse_rig()
        rig.limits_max_speed = 10.0
        rig.direction(1, 0)
        rig.speed(8)
        actions.sleep("200ms")
        rig.speed.add(5)

# =============================================================================
# QA TEST ACTIONS - DIRECTION OVER TIME
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_smooth_turn():
        """Test smooth direction transition"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.direction(0, 1).over(300)

    def mouse_rig_test_rate_turn_slow():
        """Test rate-based turn (45 deg/s)"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.direction(0, 1).rate(45)

    def mouse_rig_test_rate_turn_medium():
        """Test rate-based turn (90 deg/s)"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.direction(0, 1).rate(90)

    def mouse_rig_test_rate_turn_fast():
        """Test rate-based turn (180 deg/s)"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.direction(-1, 0).rate(180)

    def mouse_rig_test_one_eighty_turn():
        """Test 180 degree turn"""
        rig = actions.user.mouse_rig()
        rig.reverse().over(500)

    def mouse_rig_test_small_angle_turn():
        """Test small angle turn"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.direction(0.9, 0.1).over(200)

# =============================================================================
# QA TEST ACTIONS - POSITION CONTROL
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_position_snap():
        """Test instant position change"""
        rig = actions.user.mouse_rig()
        rig.pos.to(500, 500)

    def mouse_rig_test_position_glide():
        """Test position glide"""
        rig = actions.user.mouse_rig()
        rig.pos.to(800, 600).over(500)

    def mouse_rig_test_position_by_instant():
        """Test instant relative position"""
        rig = actions.user.mouse_rig()
        rig.pos.by(100, -50)

    def mouse_rig_test_position_by_glide():
        """Test relative position glide"""
        rig = actions.user.mouse_rig()
        rig.pos.by(200, 0).over(300)

    def mouse_rig_test_glide_while_moving():
        """Test glide while cruising"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        actions.sleep("200ms")
        rig.pos.by(0, 100).over(500)

    def mouse_rig_test_multiple_glides():
        """Test multiple simultaneous glides"""
        rig = actions.user.mouse_rig()
        rig.pos.by(100, 0).over(300)
        rig.pos.by(0, 100).over(300)

# =============================================================================
# QA TEST ACTIONS - EASING
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_ease_in_speed():
        """Test ease_in for speed ramp"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(2)
        actions.sleep("200ms")
        rig.speed(10).over(500).ease("ease_in")

    def mouse_rig_test_ease_out_speed():
        """Test ease_out for speed ramp"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10)
        actions.sleep("200ms")
        rig.speed(2).over(500).ease("ease_out")

    def mouse_rig_test_ease_in_out_speed():
        """Test ease_in_out for speed ramp"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(2)
        actions.sleep("200ms")
        rig.speed(10).over(500).ease("ease_in_out")

    def mouse_rig_test_smooth_step_speed():
        """Test smoothstep for speed ramp"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(2)
        actions.sleep("200ms")
        rig.speed(10).over(500).ease("smoothstep")

    def mouse_rig_test_ease_turn():
        """Test eased direction transition"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.direction(0, 1).over(400).ease("ease_in_out")

    def mouse_rig_test_ease_rate_turn():
        """Test eased rate-based turn"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.direction(0, 1).rate(120).ease("ease_in_out")

    def mouse_rig_test_ease_glide():
        """Test eased position glide"""
        rig = actions.user.mouse_rig()
        rig.pos.by(300, 0).over(500).ease("ease_out")

# =============================================================================
# QA TEST ACTIONS - THRUST
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_thrust_timed():
        """Test thrust over time"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        actions.sleep("200ms")
        rig.thrust(20).over(500)

    def mouse_rig_test_thrust_different_direction():
        """Test thrust in different direction"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        actions.sleep("200ms")
        rig.thrust(5).dir(0, 1).over(300)

    def mouse_rig_test_thrust_multiple():
        """Test multiple simultaneous thrusts"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        actions.sleep("200ms")
        rig.thrust(2).over(500)
        rig.thrust(3).dir(0, 1).over(500)

    def mouse_rig_test_thrust_eased():
        """Test eased thrust"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        actions.sleep("200ms")
        rig.thrust(10).over(500).ease("ease_out")

# =============================================================================
# QA TEST ACTIONS - RESIST
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_resist_timed():
        """Test resist (temporary deceleration) over time"""
        rig = actions.user.mouse_rig()
        rig.resist(2).over(1000)

    def mouse_rig_test_resist_different_direction():
        """Test resist in specific direction"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0)
        # rig.speed(8)
        # actions.sleep("200ms")
        rig.resist(3).over(400)  # Resist in opposite direction

    def mouse_rig_test_resist_eased():
        """Test eased resist"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10)
        actions.sleep("200ms")
        rig.resist(8).over(500).ease("ease_in")

# =============================================================================
# QA TEST ACTIONS - BOOST
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_boost_forward():
        """Test boost in cruise direction"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        actions.sleep("200ms")
        rig.boost(10).over(300)

    def mouse_rig_test_boost_different_direction():
        """Test boost in different direction"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        actions.sleep("200ms")
        rig.boost(10).dir(0, 1).over(300)

    def mouse_rig_test_boost_multiple():
        """Test multiple boosts"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        actions.sleep("200ms")
        rig.boost(5).over(200)
        actions.sleep("50ms")
        rig.boost(5).over(200)

# =============================================================================
# QA TEST ACTIONS - PRECEDENCE & EDGE CASES
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_halt_beats_brake():
        """Test halt cancels brake"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10)
        rig.speed.brake(2.0)
        actions.sleep("100ms")
        rig.halt()

    def mouse_rig_test_new_direction_replaces_turn():
        """Test new direction cancels turn"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.direction(0, 1).over(500)
        actions.sleep("100ms")
        rig.direction(-1, 0)

    def mouse_rig_test_speed_transition_chaining():
        """Test chaining speed transitions"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(2)
        rig.speed(5).over(300)
        actions.sleep("150ms")
        rig.speed(10).over(300)

# =============================================================================
# QA TEST ACTIONS - STATE INSPECTION
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_show_state():
        """Print current rig state"""
        rig = actions.user.mouse_rig()
        state = rig.state
        for key, value in state.items():
            print(f"{key}: {value}")

# =============================================================================
# MOVEMENT API SWITCHING
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_use_talon_type():
        """Switch to Talon mouse movement type (default, works for most apps)"""
        actions.user.mouse_rig_set_type_talon()
        print("Mouse rig type: Talon (ctrl.mouse_move)")

    def mouse_rig_use_windows_raw_type():
        """Switch to Windows raw input type (for some games)"""
        actions.user.mouse_rig_set_type_windows_raw()
        rig = actions.user.mouse_rig()
        movement_type = rig.settings["movement_type"]
        print(f"Mouse rig type: {movement_type}")

    def mouse_rig_show_settings():
        """Show current rig settings"""
        rig = actions.user.mouse_rig()
        print("Mouse rig settings:")
        for key, value in rig.settings.items():
            print(f"  {key}: {value}")

    def mouse_rig_scale_double():
        """Double the movement scale (for large monitors)"""
        actions.user.mouse_rig_set_scale(2.0)
        print("Mouse rig scale: 2.0 (double)")

    def mouse_rig_scale_half():
        """Half the movement scale (for precise control)"""
        actions.user.mouse_rig_set_scale(0.5)
        print("Mouse rig scale: 0.5 (half)")

    def mouse_rig_scale_normal():
        """Reset to normal scale"""
        actions.user.mouse_rig_set_scale(1.0)
        print("Mouse rig scale: 1.0 (normal)")

    def mouse_rig_scale_custom(scale: float):
        """Set custom scale"""
        actions.user.mouse_rig_set_scale(scale)
        print(f"Mouse rig scale: {scale}")

# =============================================================================
# QA TEST ACTIONS - REAL-WORLD SCENARIOS
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_correction_while_cruising():
        """Test position correction while moving"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.pos.by(0, 100).over(500).ease("ease_out")

    def mouse_rig_test_rate_based_navigation():
        """Test navigation using rate-based turns"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        actions.sleep("500ms")
        rig.direction(0, 1).rate(90)
        actions.sleep("1000ms")
        rig.direction(-1, 0).rate(180)

    def mouse_rig_test_analog_acceleration():
        """Test analog-style acceleration and deceleration"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(0)
        rig.speed(8).over(400).ease("ease_in_out")
        actions.sleep("800ms")
        rig.speed(0).over(300).ease("ease_out")

# =============================================================================
# SEQUENCE AND CALLBACK EXAMPLES
# =============================================================================

    def mouse_rig_test_then_callback():
        """Test .then() callback after position movement"""
        rig = actions.user.mouse_rig()

        def print_done():
            print("Movement complete!")

        rig.pos.to(500, 500).over(500).ease().then(print_done)

    def mouse_rig_test_then_chain():
        """Test chaining multiple operations with .then()"""
        rig = actions.user.mouse_rig()

        def move_back():
            print("Moving back...")
            actions.mouse_drag(0)
            rig.pos.to(200, 200).over(500).ease().then(
                lambda: (
                    print("Returned to start!"),
                    actions.mouse_release(0)
                )
            )

        print("Moving to (500, 500)...")
        rig.pos.to(500, 500).over(500).ease("ease_in_out").then(move_back)

    def mouse_rig_test_sequence_clicks():
        """Test clicking multiple points in sequence"""
        rig = actions.user.mouse_rig()

        points = [(200, 200), (400, 300), (600, 200), (400, 400)]

        steps = []
        for x, y in points:
            steps.append(lambda x=x, y=y: rig.pos.to(x, y).over(350))
            steps.append(lambda: print("actions.mouse_click(0)"))

        rig.sequence(steps)

    def mouse_rig_test_sequence_drag():
        """Test drag operation using sequence"""
        rig = actions.user.mouse_rig()

        rig.sequence([
            lambda: rig.pos.to(200, 200).over(500),
            lambda: actions.mouse_click(0, hold=True),
            lambda: rig.pos.to(600, 400).over(1000),
            lambda: actions.mouse_click(0, hold=False),
        ])

    def mouse_rig_test_sequence_with_movement():
        """Test sequence with continuous movement and speed changes"""
        rig = actions.user.mouse_rig()

        rig.sequence([
            lambda: rig.direction(1, 0),
            lambda: rig.speed(5).over(1000),
            lambda: rig.direction(0, 1).over(1000),
            lambda: rig.speed(10).over(1000),
            lambda: rig.speed(0).over(1000),
        ])

    def mouse_rig_test_then_with_speed():
        """Test .then() callback with speed transitions"""
        rig = actions.user.mouse_rig()

        def accelerate():
            print("Accelerating!")
            rig.speed(10).over(1000)

        rig.direction(1, 0)
        rig.speed(3).then(accelerate)

    def mouse_rig_test_sequence_square_pattern():
        """Test drawing a square pattern with sequence"""
        rig = actions.user.mouse_rig()

        rig.sequence([
            lambda: rig.pos.to(300, 300).over(500),
            lambda: rig.pos.to(600, 300).over(500),
            lambda: rig.pos.to(600, 600).over(500),
            lambda: rig.pos.to(300, 600).over(500),
            lambda: rig.pos.to(300, 300).over(500),
        ])

    def mouse_rig_test_then_direction():
        """Test .then() callback with direction changes"""
        rig = actions.user.mouse_rig()

        def turn_down():
            print("Turning down!")
            rig.direction(0, 1).over(300)

        rig.direction(1, 0)
        rig.speed(5)
        rig.direction(1, 0).over(500).then(turn_down)

# =============================================================================
# QA TEST ACTIONS - WAIT
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_speed_wait():
        """Test speed wait before callback"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10)
        # Immediately change to speed 3, wait for 2 seconds, then do something
        rig.speed(3).wait(2000).then(lambda: print("Speed waited for 2 seconds!"))

    def mouse_rig_test_speed_wait_chain():
        """Test chaining speed changes with wait"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        # Sprint for 1 second, then cruise, then stop
        rig.speed(15).wait(1000).then(
            lambda: rig.speed(5).wait(2000).then(
                lambda: rig.halt()
            )
        )

    def mouse_rig_test_direction_wait():
        """Test direction wait before callback"""
        rig = actions.user.mouse_rig()
        rig.speed(5)
        # Turn right, wait for 1s, then turn down
        rig.direction(1, 0).wait(1000).then(
            lambda: rig.direction(0, 1)
        )

    def mouse_rig_test_position_wait():
        """Test position wait before callback"""
        rig = actions.user.mouse_rig()
        # Jump to position instantly, wait 500ms, then click
        rig.pos.to(500, 500).wait(500).then(
            lambda: actions.mouse_click(0)
        )

    def mouse_rig_test_patrol_with_wait():
        """Test patrol pattern using wait"""
        rig = actions.user.mouse_rig()

        def patrol_loop():
            rig.direction(1, 0)
            rig.speed(5).wait(3000).then(
                lambda: rig.direction(-1, 0).wait(3000).then(patrol_loop)
            )

        patrol_loop()

    def mouse_rig_test_wait_vs_over():
        """Compare wait (instant) vs over (transition)"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10)

        # Wait: instantly changes to 3, waits 1s, then callback
        # rig.speed(3).wait(1000).then(lambda: print("Wait complete"))

        # Over: ramps from 10 to 3 over 1s, then callback
        rig.speed(3).over(1000).then(lambda: print("Over complete"))

    def mouse_rig_test_drag_with_wait():
        """Test drag operation using wait for timing"""
        rig = actions.user.mouse_rig()

        rig.pos.to(200, 200).wait(200).then(
            lambda: (
                actions.mouse_drag(0),
                rig.pos.to(600, 400).wait(100).then(
                    lambda: actions.mouse_release(0)
                )
            )
        )

# =============================================================================
# ERROR TESTING - Intentional errors to test validation
# =============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_error_wait_then_over():
        """ERROR TEST: .wait() then .over() should raise ValueError"""
        rig = actions.user.mouse_rig()
        # This should error with clear message
        rig.pos.to(500, 500).wait(500).over(2000).then(
            lambda: actions.mouse_click(0)
        )

    def mouse_rig_test_over_then_wait_valid():
        """VALID TEST: .over() then .wait() adds delay after glide completes"""
        rig = actions.user.mouse_rig()
        print("Starting over+wait test...")
        # Glide to position over 2000ms, wait 500ms more, then click
        # Total time: 2500ms (2000ms glide + 500ms wait)
        rig.pos.to(500, 500).over(2000).wait(500).then(
            lambda: (print("Callback firing!"), actions.mouse_click(0))
        )
        print("Command issued")

    def mouse_rig_test_over_only():
        """Test .over() without .wait()"""
        rig = actions.user.mouse_rig()
        print("Starting over-only test...")
        rig.pos.to(500, 500).over(2000).then(
            lambda: (print("Over-only callback!"), actions.mouse_click(0))
        )
        print("Command issued")

    def mouse_rig_test_wait_only():
        """Test .wait() without .over()"""
        rig = actions.user.mouse_rig()
        print("Starting wait-only test...")
        rig.pos.to(500, 500).wait(500).then(
            lambda: (print("Wait-only callback!"), actions.mouse_click(0))
        )
        print("Command issued")

    def mouse_rig_test_error_speed_wait_over():
        """ERROR TEST: speed .wait() then .over() should raise ValueError"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        # This should error with clear message
        rig.speed(10).wait(500).over(1000)

    def mouse_rig_test_error_direction_wait_over():
        """ERROR TEST: direction .wait() then .over() should raise ValueError"""
        rig = actions.user.mouse_rig()
        # This should error with clear message
        rig.direction(1, 0).wait(500).over(1000)

    def mouse_rig_test_error_direction_wait_rate():
        """ERROR TEST: direction .wait() then .rate() should raise ValueError"""
        rig = actions.user.mouse_rig()
        # This should error with clear message
        rig.direction(1, 0).wait(500).rate(180)
