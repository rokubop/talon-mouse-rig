# Customize your mouse rig commands here

# Movement
rig left: user.mouse_rig_go("left", 4.0)
rig right: user.mouse_rig_go("right", 4.0)
rig up: user.mouse_rig_go("up", 4.0)
rig down: user.mouse_rig_go("down", 4.0)

rig go left: user.mouse_rig_go_natural("left", 4.0)
rig go right: user.mouse_rig_go_natural("right", 4.0)
rig go up: user.mouse_rig_go_natural("up", 4.0)
rig go down: user.mouse_rig_go_natural("down", 4.0)

# Speed
rig slow: user.mouse_rig_speed_to(1.0)
rig normal: user.mouse_rig_speed_to(4.0)
rig fast: user.mouse_rig_speed_to(10.0)
rig [speed | slow] down: user.mouse_rig_speed_mul(0.5)
rig speed up: user.mouse_rig_speed_mul(2)
rig speed <number>: user.mouse_rig_speed_to(number)
rig boost: user.mouse_rig_boost(8, 800, 0, 800)
rig boost start: user.mouse_rig_boost_start(8, 800)
rig boost stop: user.mouse_rig_boost_stop(800)

# Stop
rig stop: user.mouse_rig_stop()
rig stop smooth: user.mouse_rig_stop(1000)

# Position
rig center: user.mouse_rig_pos_to(1920/2, 1080/2, 300, "ease_in_out")
rig side left: user.mouse_rig_pos_to(100, 1080/2, 300, "ease_in_out")
rig side right: user.mouse_rig_pos_to(1820, 1080/2, 300, "ease_in_out")
rig side [down | bottom]: user.mouse_rig_pos_to(1920/2, 1000, 300, "ease_in_out")
rig side [up | top]: user.mouse_rig_pos_to(1920/2, 80, 300, "ease_in_out")

# Hop / Jump
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

# Direction
rig curve left: user.mouse_rig_direction_by(-90, 1000)
rig curve right: user.mouse_rig_direction_by(90, 1000)
rig turn left: user.mouse_rig_direction_by(-90)
rig turn right: user.mouse_rig_direction_by(90)
rig reverse: user.mouse_rig_reverse(1000)

# Scroll
rig scroll up: user.mouse_rig_scroll_by(0, -10, 200)
rig scroll down: user.mouse_rig_scroll_by(0, 10, 200)
rig scroll left: user.mouse_rig_scroll_by(-10, 0, 200)
rig scroll right: user.mouse_rig_scroll_by(10, 0, 200)
rig page up: user.mouse_rig_scroll_by(0, -25, 400, "ease_in_out")
rig page down: user.mouse_rig_scroll_by(0, 25, 400, "ease_in_out")
rig scroll go up: user.mouse_rig_scroll_go_natural("up", 0.1)
rig scroll go down: user.mouse_rig_scroll_go_natural("down", 0.1)
rig scroll go left: user.mouse_rig_scroll_go_natural("left", 0.1)
rig scroll go right: user.mouse_rig_scroll_go_natural("right", 0.1)
rig scroll stop: user.mouse_rig_scroll_stop()
rig scroll [speed | slow] down: user.mouse_rig_scroll_speed_mul(0.5)
rig scroll speed up: user.mouse_rig_scroll_speed_mul(2)
rig scroll speed <number>: user.mouse_rig_scroll_speed_to(number)
rig scroll boost: user.mouse_rig_scroll_boost(0.3, 800, 0, 800)
rig scroll boost start: user.mouse_rig_scroll_boost_start(0.3, 800)
rig scroll boost stop: user.mouse_rig_scroll_boost_stop(800)

# Pan (middle-click drag)
rig pan left:
    mouse_drag(2)
    user.mouse_rig_pos_by(-200, 0, 300)
    sleep(300ms)
    mouse_release(2)
rig pan right:
    mouse_drag(2)
    user.mouse_rig_pos_by(200, 0, 300)
    sleep(300ms)
    mouse_release(2)
rig pan up:
    mouse_drag(2)
    user.mouse_rig_pos_by(0, -200, 300)
    sleep(300ms)
    mouse_release(2)
rig pan down:
    mouse_drag(2)
    user.mouse_rig_pos_by(0, 200, 300)
    sleep(300ms)
    mouse_release(2)
rig pan go left:
    mouse_drag(2)
    user.mouse_rig_go("left", 4.0)
rig pan go right:
    mouse_drag(2)
    user.mouse_rig_go("right", 4.0)
rig pan go up:
    mouse_drag(2)
    user.mouse_rig_go("up", 4.0)
rig pan go down:
    mouse_drag(2)
    user.mouse_rig_go("down", 4.0)
rig pan stop:
    user.mouse_rig_stop()
    mouse_release(2)
