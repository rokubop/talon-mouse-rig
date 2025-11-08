# Mouse Rig QA Testing Commands
# Use these voice commands to test all mouse rig functionality

# =============================================================================
# SETTINGS AND CONFIGURATION
# =============================================================================

# Movement type
mouse type talon: user.mouse_rig_use_talon_type()
mouse type windows raw: user.mouse_rig_use_windows_raw_type()
mouse type raw: user.mouse_rig_use_windows_raw_type()

# Scale adjustments
mouse scale double: user.mouse_rig_scale_double()
mouse scale half: user.mouse_rig_scale_half()
mouse scale normal: user.mouse_rig_scale_normal()

# Show settings
mouse rig settings: user.mouse_rig_show_settings()

# =============================================================================
# BASIC EXAMPLES
# =============================================================================

rig test basic motion: user.mouse_rig_example_basic()
# rig test stop: user.mouse_rig_example_stop()
rig test cruise: user.mouse_rig_example_cruise()
rig test smooth speed: user.mouse_rig_example_smooth_speed()
rig test turn: user.mouse_rig_example_turn()

# =============================================================================
# DIRECTION CONTROL
# =============================================================================

# Cardinal directions
rig go right: user.mouse_rig_go_right()
rig go left: user.mouse_rig_go_left()
rig go up: user.mouse_rig_go_up()
rig go down: user.mouse_rig_go_down()

# With speed variants
rig go right slow: user.mouse_rig_go_right(3)
rig go right fast: user.mouse_rig_go_right(10)
rig go left slow: user.mouse_rig_go_left(3)
rig go left fast: user.mouse_rig_go_left(10)

# Diagonals
rig go up right: user.mouse_rig_go_up_right()
rig go up left: user.mouse_rig_go_up_left()
rig go down right: user.mouse_rig_go_down_right()
rig go down left: user.mouse_rig_go_down_left()

# =============================================================================
# SPEED CONTROL
# =============================================================================




rig one: user.mouse_rig_example_test_1()
rig two: user.mouse_rig_example_test_2()






rig speed up: user.mouse_rig_speed_up()
rig speed down: user.mouse_rig_speed_down()
rig turbo: user.mouse_rig_turbo()
rig accelerate: user.mouse_rig_accelerate()
rig slow down: user.mouse_rig_slow_down()
rig thrust burst: user.mouse_rig_thrust_burst()
rig resist bump: user.mouse_rig_resist_bump()

# Primitive commands
rig resist: user.mouse_rig_resist()
rig boost: user.mouse_rig_boost()
rig reverse: user.mouse_rig_reverse()
rig turn up: user.mouse_rig_turn_up()
rig turn down: user.mouse_rig_turn_down()
rig turn left: user.mouse_rig_turn_left()
rig turn right: user.mouse_rig_turn_right()
rig turn one eighty: user.mouse_rig_turn_one_eighty()

# =============================================================================
# SPEED TRANSITION TESTS
# =============================================================================

rig test speed instant: user.mouse_rig_test_speed_instant()
rig test speed ramp: user.mouse_rig_test_speed_ramp()
rig test speed add: user.mouse_rig_test_speed_add()
rig test speed add over: user.mouse_rig_test_speed_add_over()

# =============================================================================
# ACCELERATE, DECELERATE AND HALT TESTS
# =============================================================================

rig test decelerate: user.mouse_rig_test_decelerate()
rig test accelerate: user.mouse_rig_test_accelerate()
rig test halt: user.mouse_rig_test_halt()
rig test decelerate cancels ramp: user.mouse_rig_test_decelerate_cancels_ramp()

# =============================================================================
# SPEED LIMITS
# =============================================================================

rig test max speed: user.mouse_rig_test_max_speed()
rig test speed add with limit: user.mouse_rig_test_speed_add_with_limit()

# =============================================================================
# DIRECTION OVER TIME
# =============================================================================

rig test smooth turn: user.mouse_rig_test_smooth_turn()
rig test rate turn slow: user.mouse_rig_test_rate_turn_slow()
rig test rate turn medium: user.mouse_rig_test_rate_turn_medium()
rig test rate turn fast: user.mouse_rig_test_rate_turn_fast()
rig test one eighty turn: user.mouse_rig_test_one_eighty_turn()
rig test small angle turn: user.mouse_rig_test_small_angle_turn()

# =============================================================================
# POSITION CONTROL
# =============================================================================

# Position commands
rig position middle: user.mouse_rig_position_middle()
rig position top left: user.mouse_rig_position_top_left()
rig position top right: user.mouse_rig_position_top_right()
rig position bottom left: user.mouse_rig_position_bottom_left()
rig position bottom right: user.mouse_rig_position_bottom_right()

# Nudge commands
rig nudge right: user.mouse_rig_nudge_right()
rig nudge left: user.mouse_rig_nudge_left()
rig nudge up: user.mouse_rig_nudge_up()
rig nudge down: user.mouse_rig_nudge_down()

# Position tests
rig test position snap: user.mouse_rig_test_position_snap()
rig test position glide: user.mouse_rig_test_position_glide()
rig test position by instant: user.mouse_rig_test_position_by_instant()
rig test position by glide: user.mouse_rig_test_position_by_glide()
rig test glide while moving: user.mouse_rig_test_glide_while_moving()
rig test multiple glides: user.mouse_rig_test_multiple_glides()

# =============================================================================
# EASING
# =============================================================================

rig test ease in speed: user.mouse_rig_test_ease_in_speed()
rig test ease out speed: user.mouse_rig_test_ease_out_speed()
rig test ease in out speed: user.mouse_rig_test_ease_in_out_speed()
rig test smooth step speed: user.mouse_rig_test_smooth_step_speed()
rig test ease turn: user.mouse_rig_test_ease_turn()
rig test ease rate turn: user.mouse_rig_test_ease_rate_turn()
rig test ease glide: user.mouse_rig_test_ease_glide()

# =============================================================================
# THRUST
# =============================================================================

rig test thrust timed: user.mouse_rig_test_thrust_timed()
rig test thrust different direction: user.mouse_rig_test_thrust_different_direction()
rig test thrust multiple: user.mouse_rig_test_thrust_multiple()
rig test thrust eased: user.mouse_rig_test_thrust_eased()

# =============================================================================
# RESIST
# =============================================================================

rig test resist timed: user.mouse_rig_test_resist_timed()
rig test resist different direction: user.mouse_rig_test_resist_different_direction()
rig test resist eased: user.mouse_rig_test_resist_eased()

# =============================================================================
# BOOST
# =============================================================================

rig test boost forward: user.mouse_rig_test_boost_forward()
rig test boost different direction: user.mouse_rig_test_boost_different_direction()
rig test boost multiple: user.mouse_rig_test_boost_multiple()
rig test dash: user.mouse_rig_example_dash()

# =============================================================================
# ADVANCED EXAMPLES
# =============================================================================

rig test smooth cruise: user.mouse_rig_example_smooth_cruise()
rig test orbit: user.mouse_rig_example_orbit()
rig test glide corner: user.mouse_rig_example_glide_to_corner()
rig test patrol: user.mouse_rig_example_patrol()

# =============================================================================
# PEDAL PATTERN
# =============================================================================

rig pedal left press: user.mouse_rig_pedal_left_press()
rig pedal left release: user.mouse_rig_pedal_left_release()
rig pedal right press: user.mouse_rig_pedal_right_press()
rig pedal right release: user.mouse_rig_pedal_right_release()

# =============================================================================
# PRECEDENCE & EDGE CASES
# =============================================================================

rig test halt beats brake: user.mouse_rig_test_halt_beats_brake()
rig test new direction replaces turn: user.mouse_rig_test_new_direction_replaces_turn()
rig test speed transition chaining: user.mouse_rig_test_speed_transition_chaining()

# =============================================================================
# STATE INSPECTION
# =============================================================================

show rig state: user.mouse_rig_show_state()

# =============================================================================
# UTILITY COMMANDS
# =============================================================================

rig reset: user.mouse_rig_reset()
rig stop: user.mouse_rig_example_stop()
rig stop soft: user.mouse_rig_example_stop_soft()
rig halt: user.mouse_rig_example_stop()
set max speed <number_small>: user.mouse_rig_set_max_speed(number_small)


# =============================================================================
# REAL-WORLD SCENARIOS
# =============================================================================

rig test correction while cruising: user.mouse_rig_test_correction_while_cruising()
rig test rate based navigation: user.mouse_rig_test_rate_based_navigation()
rig test analog acceleration: user.mouse_rig_test_analog_acceleration()

# =============================================================================
# SEQUENCE AND CALLBACK TESrTS
# =============================================================================

rig test then callback: user.mouse_rig_test_then_callback()
rig test then chain: user.mouse_rig_test_then_chain()
rig test sequence clicks: user.mouse_rig_test_sequence_clicks()
rig test sequence drag: user.mouse_rig_test_sequence_drag()
rig test sequence with movement: user.mouse_rig_test_sequence_with_movement()
rig test then with speed: user.mouse_rig_test_then_with_speed()
rig test sequence square pattern: user.mouse_rig_test_sequence_square_pattern()
rig test then direction: user.mouse_rig_test_then_direction()

# =============================================================================
# WAIT TESTS
# =============================================================================

rig test speed wait: user.mouse_rig_test_speed_wait()
rig test speed wait chain: user.mouse_rig_test_speed_wait_chain()
rig test direction wait: user.mouse_rig_test_direction_wait()
rig test position wait: user.mouse_rig_test_position_wait()
rig test patrol with wait: user.mouse_rig_test_patrol_with_wait()
rig test wait versus over: user.mouse_rig_test_wait_vs_over()
rig test drag with wait: user.mouse_rig_test_drag_with_wait()

# =============================================================================
# ERROR TESTS - These should intentionally raise ValueError
# =============================================================================

rig test error wait then over: user.mouse_rig_test_error_wait_then_over()
rig test over then wait valid: user.mouse_rig_test_over_then_wait_valid()
rig test over only: user.mouse_rig_test_over_only()
rig test wait only: user.mouse_rig_test_wait_only()
rig test error speed wait over: user.mouse_rig_test_error_speed_wait_over()
rig test error direction wait over: user.mouse_rig_test_error_direction_wait_over()
rig test error direction wait rate: user.mouse_rig_test_error_direction_wait_rate()
