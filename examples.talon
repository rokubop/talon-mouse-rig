# Mouse Rig - Comprehensive Test Commands
# Organized into 14 categories for systematic manual testing

# =========================================================================
# 1. BASIC MOVEMENT & DIRECTION
# =========================================================================

test move right: user.test_move_right()
test move left: user.test_move_left()
test move up: user.test_move_up()
test move down: user.test_move_down()
test move diagonal: user.test_move_diagonal()
test rotate: user.test_direction_rotate()
test reverse: user.test_reverse()

# =========================================================================
# 2. SPEED & ACCELERATION
# =========================================================================

test speed set: user.test_speed_set()
test speed add: user.test_speed_add()
test speed add negative: user.test_speed_add_negative()
test speed multiply: user.test_speed_mul()
test speed over: user.test_speed_over()
test stop: user.test_stop()
test stop gradual: user.test_stop_gradual()

# =========================================================================
# 3. LAYER SYSTEM - BASE, USER LAYERS, FINAL
# =========================================================================

test layer basic: user.test_layer_basic()
test layer stacking: user.test_layer_stacking()
test layer ordering: user.test_layer_ordering()
test layer replace: user.test_layer_lifecycle_replace()
test layer stack: user.test_layer_lifecycle_stack()

# =========================================================================
# 4. PHASES - INCOMING VS OUTGOING
# =========================================================================

test phase incoming: user.test_phase_incoming()
test phase outgoing: user.test_phase_outgoing()
test phase both: user.test_phase_both()
test phase sequence: user.test_phase_sequence()

# =========================================================================
# 5. FINAL LAYER
# =========================================================================

test final speed: user.test_final_speed()
test final direction: user.test_final_direction()
test final force: user.test_final_force()

# =========================================================================
# 6. OVERRIDE SCOPE
# =========================================================================

test override speed: user.test_override_speed()
test override direction: user.test_override_direction()

# =========================================================================
# 7. LIFECYCLE METHODS - QUEUE, EXTEND, THROTTLE, IGNORE
# =========================================================================

test lifecycle queue: user.test_lifecycle_queue()
test lifecycle extend: user.test_lifecycle_extend()
test lifecycle throttle: user.test_lifecycle_throttle()
test lifecycle ignore: user.test_lifecycle_ignore()

# =========================================================================
# 8. BEHAVIOR MODES - HOLD, RELEASE
# =========================================================================

test hold: user.test_hold()
test release: user.test_release()

# =========================================================================
# 9. SCALE - GLOBAL MULTIPLIER
# =========================================================================

test scale: user.test_scale()
test scale add: user.test_scale_add()
test scale layer: user.test_scale_layer()

# =========================================================================
# 10. POSITION CONTROL
# =========================================================================

test position to: user.test_position_to()
test position by: user.test_position_by()

# =========================================================================
# 11. EASING & INTERPOLATION
# =========================================================================

test easing: user.test_easing()

# =========================================================================
# 12. STATE ACCESS & BAKING
# =========================================================================

test state read: user.test_state_read()
test bake: user.test_bake()

# =========================================================================
# 13. ERROR CASES & EDGE CONDITIONS
# =========================================================================

# test error base incoming: user.test_error_base_incoming()
# test error final incoming: user.test_error_final_incoming()
# test error layer mul: user.test_error_layer_mul_without_phase()

# =========================================================================
# 14. REAL-WORLD SCENARIOS
# =========================================================================

test sprint: user.test_scenario_sprint()
test precision: user.test_scenario_precision()
test acceleration ramp: user.test_scenario_acceleration_ramp()
test drift: user.test_scenario_drift()
test rubber band: user.test_scenario_rubber_band()
test orbit: user.test_scenario_orbit()
test multi layer: user.test_scenario_multi_layer_combo()

# =========================================================================
# LEGACY COMMANDS (for backward compatibility testing)
# =========================================================================

mouse rig turn right: user.mouse_rig_turn_right()
mouse rig turn left: user.mouse_rig_turn_left()
mouse rig turn lerp: user.mouse_rig_turn_lerp()
mouse rig reverse: user.mouse_rig_reverse()
mouse rig position center: user.mouse_rig_pos_center()
mouse rig nudge right: user.mouse_rig_nudge_right()
mouse rig nudge down: user.mouse_rig_nudge_down()
mouse rig stop smooth: user.mouse_rig_stop_smooth()
mouse rig bake: user.mouse_rig_bake()
mouse rig show state: user.mouse_rig_show_state()
