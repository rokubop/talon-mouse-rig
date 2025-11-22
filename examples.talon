# Mouse Rig - Comprehensive Test Commands
# Organized into 14 categories for systematic manual testing

# =========================================================================
# 1. BASIC MOVEMENT & DIRECTION
# =========================================================================

rig right: user.test_move_right()
rig left: user.test_move_left()
rig up: user.test_move_up()
rig down: user.test_move_down()
rig diagonal: user.test_move_diagonal()
rig rotate: user.test_direction_rotate()
rig reverse: user.test_reverse()

# =========================================================================
# 2. SPEED & ACCELERATION
# =========================================================================

rig speed set: user.test_speed_set()
rig speed add: user.test_speed_add()
rig speed add negative: user.test_speed_add_negative()
rig speed multiply: user.test_speed_mul()
rig speed over: user.test_speed_over()
rig stop: user.test_stop()
rig stop gradual: user.test_stop_gradual()

# =========================================================================
# 3. LAYER SYSTEM - BASE, USER LAYERS, FINAL
# =========================================================================

rig layer basic: user.test_layer_basic()
rig layer stacking: user.test_layer_stacking()
rig layer ordering: user.test_layer_ordering()
rig layer replace: user.test_layer_lifecycle_replace()
rig layer stack: user.test_layer_lifecycle_stack()

# =========================================================================
# 4. PHASES - INCOMING VS OUTGOING
# =========================================================================

rig phase incoming: user.test_phase_incoming()
rig phase outgoing: user.test_phase_outgoing()
rig phase both: user.test_phase_both()
rig phase sequence: user.test_phase_sequence()

# =========================================================================
# 5. FINAL LAYER
# =========================================================================

rig final speed: user.test_final_speed()
rig final direction: user.test_final_direction()
rig final force: user.test_final_force()

# =========================================================================
# 6. OVERRIDE SCOPE
# =========================================================================

rig override speed: user.test_override_speed()
rig override direction: user.test_override_direction()
# =========================================================================
# 7. LIFECYCLE METHODS - QUEUE, EXTEND, THROTTLE, IGNORE
# =========================================================================

rig lifecycle queue: user.test_lifecycle_queue()
rig lifecycle extend: user.test_lifecycle_extend()
rig lifecycle throttle: user.test_lifecycle_throttle()
rig lifecycle ignore: user.test_lifecycle_ignore()

# =========================================================================
# 8. BEHAVIOR MODES - HOLD, RELEASE
# =========================================================================

rig hold: user.test_hold()
rig release: user.test_release()

# =========================================================================
# 9. SCALE - GLOBAL MULTIPLIER
# =========================================================================

rig scale: user.test_scale()
rig scale add: user.test_scale_add()
rig scale layer: user.test_scale_layer()

# =========================================================================
# 10. POSITION CONTROL
# =========================================================================

rig position to: user.test_position_to()
rig position by: user.test_position_by()

# =========================================================================
# 11. EASING & INTERPOLATION
# =========================================================================

rig easing: user.test_easing()

# =========================================================================
# 12. STATE ACCESS & BAKING
# =========================================================================

rig state read: user.test_state_read()
rig bake: user.test_bake()

# =========================================================================
# 13. ERROR CASES & EDGE CONDITIONS
# =========================================================================

# test error base incoming: user.test_error_base_incoming()
# test error final incoming: user.test_error_final_incoming()
# test error layer mul: user.test_error_layer_mul_without_phase()

# =========================================================================
# 14. REAL-WORLD SCENARIOS
# =========================================================================

rig sprint: user.test_scenario_sprint()
rig precision: user.test_scenario_precision()
rig acceleration ramp: user.test_scenario_acceleration_ramp()
rig drift: user.test_scenario_drift()
rig rubber band: user.test_scenario_rubber_band()
rig orbit: user.test_scenario_orbit()
rig multi layer: user.test_scenario_multi_layer_combo()

# =========================================================================
# LEGACY COMMANDS (for backward compatibility testing)
# =========================================================================

rig turn right: user.mouse_rig_turn_right()
rig turn left: user.mouse_rig_turn_left()
rig turn lerp: user.mouse_rig_turn_lerp()
# rig reverse: user.mouse_rig_reverse()
rig position center: user.mouse_rig_pos_center()
rig nudge right: user.mouse_rig_nudge_right()
rig nudge down: user.mouse_rig_nudge_down()
rig stop smooth: user.mouse_rig_stop_smooth()
rig bake: user.mouse_rig_bake()
rig show state: user.mouse_rig_show_state()
