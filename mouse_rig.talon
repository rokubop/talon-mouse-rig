# Simple commands
# You can do much more complex things with user.mouse_rig() directly.
# Feel free to update or remove these commands as you see fit.
rig left: user.mouse_rig_go_left(3)
rig right: user.mouse_rig_go_right(3)
rig up: user.mouse_rig_go_up(3)
rig down: user.mouse_rig_go_down(3)

rig curve left: user.mouse_rig_direction_to(-1, 0, 800)
rig curve right: user.mouse_rig_direction_to(1, 0, 800)
rig curve up: user.mouse_rig_direction_to(0, -1, 800)
rig curve down: user.mouse_rig_direction_to(0, 1, 800)

rig stop: user.mouse_rig_stop()

rig boost: user.mouse_rig_boost(10, 1000, 1000)
rig speed <number>: user.mouse_rig_set_speed(number)
rig speed up: user.mouse_rig_speed_mul(2)
rig [speed | slow] down: user.mouse_rig_speed_mul(0.5)

rig [position] center: user.mouse_rig_pos_to(1920/2, 1080/2)
rig position left: user.mouse_rig_pos_to(100, 1080/2)
rig position right: user.mouse_rig_pos_to(1820, 1080/2)
rig position [down | bottom]: user.mouse_rig_pos_to(1920/2, 1000)
rig position [up | top]: user.mouse_rig_pos_to(1920/2, 80)

rig small left: user.mouse_rig_pos_by(-30, 0)
rig small right: user.mouse_rig_pos_by(30, 0)
rig small up: user.mouse_rig_pos_by(0, -30)
rig small down: user.mouse_rig_pos_by(0, 30)

rig big left: user.mouse_rig_pos_by(-300, 0)
rig big right: user.mouse_rig_pos_by(300, 0)
rig big up: user.mouse_rig_pos_by(0, -300)
rig big down: user.mouse_rig_pos_by(0, 300)

# Development
rig reload: user.mouse_rig_reload()
rig test: user.mouse_rig_test_toggle_ui()
