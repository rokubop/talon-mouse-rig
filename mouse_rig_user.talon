# Customize your mouse rig commands here

# Continuous move sharp
rig left: user.mouse_rig_move_continuous("left", 4.0)
rig right: user.mouse_rig_move_continuous("right", 4.0)
rig up: user.mouse_rig_move_continuous("up", 4.0)
rig down: user.mouse_rig_move_continuous("down", 4.0)

# Continuous move smooth
rig go left: user.mouse_rig_move_continuous_smooth("left", 4.0)
rig go right: user.mouse_rig_move_continuous_smooth("right", 4.0)
rig go up: user.mouse_rig_move_continuous_smooth("up", 4.0)
rig go down: user.mouse_rig_move_continuous_smooth("down", 4.0)

# Move finite amount
rig move left: user.mouse_rig_move_delta_smooth("left", 150)
rig move right: user.mouse_rig_move_delta_smooth("right", 150)
rig move up: user.mouse_rig_move_delta_smooth("up", 150)
rig move down: user.mouse_rig_move_delta_smooth("down", 150)

# Speed
rig slow: user.mouse_rig_speed_to(1.0)
rig normal: user.mouse_rig_speed_to(4.0)
rig fast: user.mouse_rig_speed_to(10.0)
rig [speed | slow] down: user.mouse_rig_speed_mul(0.5)
rig speed up: user.mouse_rig_speed_mul(2)
rig speed <number>: user.mouse_rig_speed_to(number)

# Speed offset
rig boost: user.mouse_rig_boost(8, 800, 0, 800)
rig boost start: user.mouse_rig_boost_start(8, 800)
rig boost stop: user.mouse_rig_boost_stop(800)

# Stop
rig stop: user.mouse_rig_stop()
rig break: user.mouse_rig_stop(1000)

# Position
rig center: user.mouse_rig_move_to_smooth(1920/2, 1080/2)
rig side left: user.mouse_rig_move_to_smooth(100, 1080/2)
rig side right: user.mouse_rig_move_to_smooth(1820, 1080/2)
rig side [down | bottom]: user.mouse_rig_move_to_smooth(1920/2, 1000)
rig side [up | top]: user.mouse_rig_move_to_smooth(1920/2, 80)

# Direction
rig curve left: user.mouse_rig_move_rotate(-90, 1000)
rig curve right: user.mouse_rig_move_rotate(90, 1000)
rig turn left: user.mouse_rig_move_rotate(-90)
rig turn right: user.mouse_rig_move_rotate(90)
rig reverse: user.mouse_rig_move_reverse(1000)

# Scroll
rig scroll down one: user.mouse_rig_scroll_delta("down", 1)
rig scroll up one: user.mouse_rig_scroll_delta("up", 1)
rig scroll up: user.mouse_rig_scroll_delta_smooth("up", 8)
rig scroll down: user.mouse_rig_scroll_delta_smooth("down", 8)
rig scroll left: user.mouse_rig_scroll_delta_smooth("left", 8)
rig scroll right: user.mouse_rig_scroll_delta_smooth("right", 8)
rig scroll go up: user.mouse_rig_scroll_continuous_smooth("up", 0.1)
rig scroll go down: user.mouse_rig_scroll_continuous_smooth("down", 0.1)
rig scroll go left: user.mouse_rig_scroll_continuous_smooth("left", 0.1)
rig scroll go right: user.mouse_rig_scroll_continuous_smooth("right", 0.1)

# Scroll stop
rig scroll stop: user.mouse_rig_scroll_stop()
rig scroll break: user.mouse_rig_scroll_stop(1000)

rig scroll [speed | slow] down: user.mouse_rig_scroll_speed_mul(0.5)
rig scroll speed up: user.mouse_rig_scroll_speed_mul(2)
rig scroll speed <number>: user.mouse_rig_scroll_speed_to(number)
rig scroll boost: user.mouse_rig_scroll_boost(0.15, 800, 0, 800)
rig scroll boost start: user.mouse_rig_scroll_boost_start(0.15, 800)
rig scroll boost stop: user.mouse_rig_scroll_boost_stop(800)

# Pan (middle-click drag)
rig pan left:
    user.mouse_rig_button_prime("middle")
    user.mouse_rig_move_delta_smooth("left", 200)
rig pan right:
    user.mouse_rig_button_prime("middle")
    user.mouse_rig_move_delta_smooth("right", 200)
rig pan up:
    user.mouse_rig_button_prime("middle")
    user.mouse_rig_move_delta_smooth("up", 200)
rig pan down:
    user.mouse_rig_button_prime("middle")
    user.mouse_rig_move_delta_smooth("down", 200)
rig pan go left:
    user.mouse_rig_button_prime("middle")
    user.mouse_rig_move_continuous("left", 4.0)
rig pan go right:
    user.mouse_rig_button_prime("middle")
    user.mouse_rig_move_continuous("right", 4.0)
rig pan go up:
    user.mouse_rig_button_prime("middle")
    user.mouse_rig_move_continuous("up", 4.0)
rig pan go down:
    user.mouse_rig_button_prime("middle")
    user.mouse_rig_move_continuous("down", 4.0)
rig pan stop: user.mouse_rig_stop()
