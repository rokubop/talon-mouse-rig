# User talon commands - Customize this file
# Comment out, add to, or modify commands as desired.

# Movement commands - composed from direction + speed
# Uses current speed or 3 if not moving

rig left: user.mouse_rig_go_left()
rig right: user.mouse_rig_go_right()
rig up: user.mouse_rig_go_up()
rig down: user.mouse_rig_go_down()

test one: user.mouse_rig_test_one()

rig stop: user.mouse_rig_stop()
rig stop smooth: user.mouse_rig_stop(1000)

rig curve left: user.mouse_rig_direction_to(-1, 0, 1000)
rig curve right: user.mouse_rig_direction_to(1, 0, 1000)
rig curve up: user.mouse_rig_direction_to(0, -1, 1000)
rig curve down: user.mouse_rig_direction_to(0, 1, 1000)

rig boost: user.mouse_rig_speed_add(10, 1000, 0, 1000)
rig speed <number>: user.mouse_rig_speed_to(number)
rig speed up: user.mouse_rig_speed_mul(2)
rig [speed | slow] down: user.mouse_rig_speed_mul(0.5)

rig [position] center: user.mouse_rig_pos_to(1920/2, 1080/2, 300, "ease_in_out")
rig position left: user.mouse_rig_pos_to(100, 1080/2, 300, "ease_in_out")
rig position right: user.mouse_rig_pos_to(1820, 1080/2, 300, "ease_in_out")
rig position [down | bottom]: user.mouse_rig_pos_to(1920/2, 1000, 300, "ease_in_out")
rig position [up | top]: user.mouse_rig_pos_to(1920/2, 80, 300, "ease_in_out")

rig small left: user.mouse_rig_pos_by(-30, 0)
rig small right: user.mouse_rig_pos_by(30, 0)
rig small up: user.mouse_rig_pos_by(0, -30)
rig small down: user.mouse_rig_pos_by(0, 30)

rig big left: user.mouse_rig_pos_by(-300, 0)
rig big right: user.mouse_rig_pos_by(300, 0)
rig big up: user.mouse_rig_pos_by(0, -300)
rig big down: user.mouse_rig_pos_by(0, 300)

# Direction rotation
rig rotate <number>: user.mouse_rig_direction_by(number)
rig rotate left: user.mouse_rig_direction_by(-90, 1000)
rig rotate right: user.mouse_rig_direction_by(90, 1000)
rig rotate around: user.mouse_rig_direction_by(180, 1000)