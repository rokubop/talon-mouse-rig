# Simple commands
# You can do much more complex things with user.mouse_rig() directly.
# Feel free to update or remove these commands as you see fit.
rig left: user.mouse_rig_go_left(3)
rig right: user.mouse_rig_go_right(3)
rig up: user.mouse_rig_go_up(3)
rig down: user.mouse_rig_go_down(3)
rig speed up: user.mouse_rig_speed_mul(2)
rig slow down: user.mouse_rig_speed_mul(0.5)
rig center: user.mouse_rig_pos_to(1920/2, 1080/2)
rig stop: user.mouse_rig_stop()
rig short left: user.mouse_rig_pos_by(-30, 0)
rig short right: user.mouse_rig_pos_by(30, 0)
rig short up: user.mouse_rig_pos_by(0, -30)
rig short down: user.mouse_rig_pos_by(0, 30)

# Development
rig [reload | reset]: user.mouse_rig_reload()
rig test [show | hide]: user.mouse_rig_test_toggle_ui()
