# Mouse Rig Examples - Voice Commands
# Comprehensive feature showcase for PRD6

# =============================================================================
# BASIC MOVEMENT
# =============================================================================

rig right: user.mouse_rig_go_right()
rig left: user.mouse_rig_go_left()
rig up: user.mouse_rig_go_up()
rig down: user.mouse_rig_go_down()

rig up right: user.mouse_rig_go_up_right()
rig up left: user.mouse_rig_go_up_left()
rig down right: user.mouse_rig_go_down_right()
rig down left: user.mouse_rig_go_down_left()

# =============================================================================
# SPEED CONTROL
# =============================================================================

rig slow: user.mouse_rig_speed_slow()
rig normal: user.mouse_rig_speed_normal()
rig fast: user.mouse_rig_speed_fast()
rig ramp up: user.mouse_rig_speed_ramp_up()
rig ramp down: user.mouse_rig_speed_ramp_down()

# =============================================================================
# TEMPORARY SPEED BOOSTS
# =============================================================================

rig boost: user.mouse_rig_boost_instant()
rig boost fade: user.mouse_rig_boost_fade()
rig boost smooth: user.mouse_rig_boost_smooth()
rig slowdown: user.mouse_rig_slowdown()

# =============================================================================
# TRANSFORM SYSTEM - SCALE
# =============================================================================

rig sprint: user.mouse_rig_sprint_on()
rig sprint off: user.mouse_rig_sprint_off()
rig sprint smooth: user.mouse_rig_sprint_smooth()
rig boost pad: user.mouse_rig_boost_pad()
rig boost pad max: user.mouse_rig_boost_pad_max()

# =============================================================================
# TRANSFORM SYSTEM - DIRECTION
# =============================================================================

rig drift: user.mouse_rig_drift_on()
rig drift off: user.mouse_rig_drift_off()
rig drift smooth: user.mouse_rig_drift_smooth()

# =============================================================================
# FORCE SYSTEM
# =============================================================================

rig gravity: user.mouse_rig_gravity_on()
rig gravity off: user.mouse_rig_gravity_off()
rig wind: user.mouse_rig_wind_on()
rig wind smooth: user.mouse_rig_wind_smooth()

# =============================================================================
# ACCELERATION
# =============================================================================

rig accel: user.mouse_rig_accel_on()
rig decel: user.mouse_rig_accel_off()
rig accel burst: user.mouse_rig_accel_burst()

# =============================================================================
# SMOOTH TURNS
# =============================================================================

rig turn right: user.mouse_rig_turn_right()
rig turn left: user.mouse_rig_turn_left()
rig reverse: user.mouse_rig_reverse()

# =============================================================================
# POSITION CONTROL
# =============================================================================

rig center: user.mouse_rig_pos_center()
rig nudge right: user.mouse_rig_nudge_right()
rig nudge down: user.mouse_rig_nudge_down()

# =============================================================================
# STOPPING & STATE
# =============================================================================

rig stop: user.mouse_rig_stop()
rig stop smooth: user.mouse_rig_stop_smooth()
rig bake: user.mouse_rig_bake()
rig state: user.mouse_rig_show_state()
