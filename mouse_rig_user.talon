# Your file to customize - Add / modify / or comment out commands as desired

rig left: user.mouse_rig_go_left(4)
rig right: user.mouse_rig_go_right(4)
rig up: user.mouse_rig_go_up(4)
rig down: user.mouse_rig_go_down(4)

rig left slow:
    user.mouse_rig_direction_left()
    user.mouse_rig_speed_to(1.0)
rig right slow:
    user.mouse_rig_direction_right()
    user.mouse_rig_speed_to(1.0)
rig up slow:
    user.mouse_rig_direction_up()
    user.mouse_rig_speed_to(1.0)
rig down slow:
    user.mouse_rig_direction_down()
    user.mouse_rig_speed_to(1.0)

rig left fast:
    user.mouse_rig_direction_left()
    user.mouse_rig_speed_to(10)
rig right fast:
    user.mouse_rig_direction_right()
    user.mouse_rig_speed_to(10)
rig up fast:
    user.mouse_rig_direction_up()
    user.mouse_rig_speed_to(10)
rig down fast:
    user.mouse_rig_direction_down()
    user.mouse_rig_speed_to(10)

rig slow: user.mouse_rig_speed_to(1.0)
rig normal: user.mouse_rig_speed_to(4)
rig fast: user.mouse_rig_speed_to(10)

rig [speed | slow] down: user.mouse_rig_speed_mul(0.5)
rig speed up: user.mouse_rig_speed_mul(2)
rig speed <number>: user.mouse_rig_speed_to(number)

rig boost: user.mouse_rig_speed_mul(3, 800, 0, 800)

rig stop: user.mouse_rig_stop()
rig stop smooth: user.mouse_rig_stop(1000)

rig center: user.mouse_rig_pos_to(1920/2, 1080/2, 300, "ease_in_out")
rig side left: user.mouse_rig_pos_to(100, 1080/2, 300, "ease_in_out")
rig side right: user.mouse_rig_pos_to(1820, 1080/2, 300, "ease_in_out")
rig side [down | bottom]: user.mouse_rig_pos_to(1920/2, 1000, 300, "ease_in_out")
rig side [up | top]: user.mouse_rig_pos_to(1920/2, 80, 300, "ease_in_out")

rig hop: user.mouse_rig_pos_by_value(30, 100)
rig hop left: user.mouse_rig_pos_by(-30, 0, 100)
rig hop right: user.mouse_rig_pos_by(30, 0, 100)
rig hop up: user.mouse_rig_pos_by(0, -30, 100)
rig hop down: user.mouse_rig_pos_by(0, 30, 100)

rig jump: user.mouse_rig_pos_by_value(200, 200)
rig jump left: user.mouse_rig_pos_by(-200, 0, 200)
rig jump right: user.mouse_rig_pos_by(200, 0, 200)
rig jump up: user.mouse_rig_pos_by(0, -200, 200)
rig jump down: user.mouse_rig_pos_by(0, 200, 200)

rig [curve | turn] left: user.mouse_rig_direction_to(-1, 0, 1000)
rig [curve | turn] right: user.mouse_rig_direction_to(1, 0, 1000)
rig [curve | turn] up: user.mouse_rig_direction_to(0, -1, 1000)
rig [curve | turn] down: user.mouse_rig_direction_to(0, 1, 1000)
rig [curve | turn] around: user.mouse_rig_direction_by(180, 1000)

rig rotate left: user.mouse_rig_direction_by(-90, 1000)
rig rotate right: user.mouse_rig_direction_by(90, 1000)

rig bank left: user.mouse_rig_direction_by(-90)
rig bank right: user.mouse_rig_direction_by(90)

rig reverse: user.mouse_rig_reverse(1000)

# One-time scroll
rig scroll up: user.mouse_rig_scroll_by(0, -3)
rig scroll down: user.mouse_rig_scroll_by(0, 3)
rig scroll left: user.mouse_rig_scroll_by(-3, 0)
rig scroll right: user.mouse_rig_scroll_by(3, 0)
rig page up: user.mouse_rig_scroll_by(0, -10)
rig page down: user.mouse_rig_scroll_by(0, 10)

# Continuous scroll
rig scroll go up: user.mouse_rig_scroll_go_up(1)
rig scroll go down: user.mouse_rig_scroll_go_down(1)
rig scroll go left: user.mouse_rig_scroll_go_left(1)
rig scroll go right: user.mouse_rig_scroll_go_right(1)

rig scroll go up slow: user.mouse_rig_scroll_go_up(2)
rig scroll go down slow: user.mouse_rig_scroll_go_down(2)
rig scroll go up fast: user.mouse_rig_scroll_go_up(15)
rig scroll go down fast: user.mouse_rig_scroll_go_down(15)

rig scroll slow: user.mouse_rig_scroll_speed_to(2)
rig scroll normal: user.mouse_rig_scroll_speed_to(5)
rig scroll fast: user.mouse_rig_scroll_speed_to(15)

rig scroll speed up: user.mouse_rig_scroll_speed_add(3)
rig scroll speed down: user.mouse_rig_scroll_speed_add(-3)
rig scroll speed <number>: user.mouse_rig_scroll_speed_to(number)

rig scroll stop: user.mouse_rig_scroll_stop()
rig scroll reverse: user.mouse_rig_scroll_direction_by(180)
