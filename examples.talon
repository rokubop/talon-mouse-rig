# Mouse Rig Examples - PRD 5 Voice Commands
# Use these voice commands to test the mouse rig functionality

# =============================================================================
# DIRECTION CONTROL
# =============================================================================

rig go right: user.mouse_rig_go_right()
rig go left: user.mouse_rig_go_left()
rig go up: user.mouse_rig_go_up()
rig go down: user.mouse_rig_go_down()

rig go up right: user.mouse_rig_go_up_right()
rig go up left: user.mouse_rig_go_up_left()
rig go down right: user.mouse_rig_go_down_right()
rig go down left: user.mouse_rig_go_down_left()

# =============================================================================
# SPEED CONTROL
# =============================================================================

rig speed slow: user.mouse_rig_speed_slow()
rig speed normal: user.mouse_rig_speed_normal()
rig speed fast: user.mouse_rig_speed_fast()

rig speed up: user.mouse_rig_speed_up()
rig speed down: user.mouse_rig_speed_down()
rig speed ramp: user.mouse_rig_speed_ramp()

# =============================================================================
# STOP CONTROL
# =============================================================================

rig stop: user.mouse_rig_stop()
rig stop soft: user.mouse_rig_stop_soft()
rig stop gentle: user.mouse_rig_stop_gentle()

# =============================================================================
# TEMPORARY EFFECTS
# =============================================================================

rig boost instant: user.mouse_rig_boost_instant()
rig boost fade: user.mouse_rig_boost_fade()
rig boost smooth: user.mouse_rig_boost_smooth()
rig slow down: user.mouse_rig_slowdown()

# =============================================================================
# NAMED EFFECTS
# =============================================================================

rig turbo on: user.mouse_rig_turbo_on()
rig turbo off: user.mouse_rig_turbo_off()

rig thrust on: user.mouse_rig_thrust_on()
rig thrust off: user.mouse_rig_thrust_off()

rig drift on: user.mouse_rig_drift_on()
rig drift off: user.mouse_rig_drift_off()

# =============================================================================
# NAMED FORCES
# =============================================================================

rig gravity on: user.mouse_rig_gravity_on()
rig gravity off: user.mouse_rig_gravity_off()

rig wind on: user.mouse_rig_wind_on()
rig wind off: user.mouse_rig_wind_off()

# =============================================================================
# ACCELERATION CONTROL
# =============================================================================

rig accel on: user.mouse_rig_accel_on()
rig accel off: user.mouse_rig_accel_off()
rig accel boost: user.mouse_rig_accel_boost()

# =============================================================================
# RATE-BASED TIMING
# =============================================================================

rig ramp by rate: user.mouse_rig_ramp_by_rate()
rig turn by rate: user.mouse_rig_turn_by_rate()
rig accel speed: user.mouse_rig_accel_speed()

# =============================================================================
# SMOOTH TURNS
# =============================================================================

rig turn right: user.mouse_rig_turn_right()
rig turn down: user.mouse_rig_turn_down()
rig reverse: user.mouse_rig_reverse()

# =============================================================================
# POSITION CONTROL
# =============================================================================

rig pos center: user.mouse_rig_pos_center()
rig pos corner: user.mouse_rig_pos_corner()
rig nudge right: user.mouse_rig_nudge_right()

# =============================================================================
# STATE & BAKING
# =============================================================================

rig show state: user.mouse_rig_show_state()
rig bake: user.mouse_rig_bake_state()

# =============================================================================
# LAMBDA EXAMPLES
# =============================================================================

rig relative boost: user.mouse_rig_relative_boost()
rig double speed: user.mouse_rig_double_speed()
