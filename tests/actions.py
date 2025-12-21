"""
Talon Actions Integration Tests

High-level sanity checks for actions.user.mouse_rig_* actions.
These test the Talon action API layer rather than the core rig internals.
"""

from talon import actions, ctrl, cron

CENTER_X = 960
CENTER_Y = 540


# ============================================================================
# POSITION ACTION TESTS
# ============================================================================

def test_action_pos_to():
    """Test: actions.user.mouse_rig_pos_to(x, y) - instant position"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    target_x = CENTER_X + 100
    target_y = CENTER_Y + 50
    actions.user.mouse_rig_pos_to(target_x, target_y)

    x, y = ctrl.mouse_pos()
    assert x == target_x, f"X position wrong: expected {target_x}, got {x}"
    assert y == target_y, f"Y position wrong: expected {target_y}, got {y}"


def test_action_pos_by():
    """Test: actions.user.mouse_rig_pos_by(dx, dy, api='talon') - relative position"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    dx, dy = 75, -50
    actions.user.mouse_rig_pos_by(dx, dy, api="talon")

    x, y = ctrl.mouse_pos()
    assert abs(x - (CENTER_X + dx)) <= 2, f"X offset wrong: expected {CENTER_X + dx}, got {x}"
    assert abs(y - (CENTER_Y + dy)) <= 2, f"Y offset wrong: expected {CENTER_Y + dy}, got {y}"


def test_action_pos_to_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_pos_to(x, y, over_ms) - animated position"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    target_x = CENTER_X + 150
    target_y = CENTER_Y + 100

    def check_position():
        x, y = ctrl.mouse_pos()
        if x != target_x or y != target_y:
            on_failure(f"Final position wrong: expected ({target_x}, {target_y}), got ({x}, {y})")
            return
        on_success()

    actions.user.mouse_rig_pos_to(target_x, target_y, 500, "ease_in_out", check_position)


def test_action_pos_by_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_pos_by(dx, dy, over_ms, api='talon') - animated relative"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    dx, dy = 100, -75

    def check_position():
        x, y = ctrl.mouse_pos()
        if abs(x - (CENTER_X + dx)) > 2 or abs(y - (CENTER_Y + dy)) > 2:
            on_failure(f"Final position wrong: expected ({CENTER_X + dx}, {CENTER_Y + dy}), got ({x}, {y})")
            return
        on_success()

    actions.user.mouse_rig_pos_by(dx, dy, 500, "linear", check_position, api="talon")


# ============================================================================
# SPEED ACTION TESTS
# ============================================================================

def test_action_speed_to(on_success, on_failure):
    """Test: actions.user.mouse_rig_speed_to(value) - instant speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_right()
    actions.user.mouse_rig_speed_to(10)

    if actions.user.mouse_rig_state_speed() != 10:
        on_failure(f"Speed wrong: expected 10, got {actions.user.mouse_rig_state_speed()}")
        return

    def check_and_stop():
        actions.user.mouse_rig_stop()
        on_success()

    cron.after("500ms", check_and_stop)


def test_action_speed_add(on_success, on_failure):
    """Test: actions.user.mouse_rig_speed_add(delta) - add to speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_up()
    actions.user.mouse_rig_speed_to(5)
    actions.user.mouse_rig_speed_add(3)

    if actions.user.mouse_rig_state_speed() != 8:
        on_failure(f"Speed wrong: expected 8, got {actions.user.mouse_rig_state_speed()}")
        return

    def check_and_stop():
        actions.user.mouse_rig_stop()
        on_success()

    cron.after("500ms", check_and_stop)


def test_action_speed_mul(on_success, on_failure):
    """Test: actions.user.mouse_rig_speed_mul(factor) - multiply speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_left()
    actions.user.mouse_rig_speed_to(5)
    actions.user.mouse_rig_speed_mul(2)

    if actions.user.mouse_rig_state_speed() != 10:
        on_failure(f"Speed wrong: expected 10, got {actions.user.mouse_rig_state_speed()}")
        return

    def check_and_stop():
        actions.user.mouse_rig_stop()
        on_success()

    cron.after("500ms", check_and_stop)


def test_action_speed_to_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_speed_to(value, over_ms) - animated speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_speed_to(2)

    target_speed = 10

    def check_speed():
        speed = actions.user.mouse_rig_state_speed()
        if abs(speed - target_speed) > 0.1:
            on_failure(f"Final speed wrong: expected {target_speed}, got {speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    actions.user.mouse_rig_speed_to(target_speed, 500)
    cron.after("600ms", check_speed)


def test_action_speed_to_hold_revert(on_success, on_failure):
    """Test: actions.user.mouse_rig_speed_to(value, over, hold, revert) - full lifecycle"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_speed_to(5)

    def check_after_revert():
        speed = actions.user.mouse_rig_state_speed()
        if abs(speed - 5) > 0.1:
            on_failure(f"Speed after revert wrong: expected 5, got {speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    # Speed to 15 over 200ms, hold 200ms, revert over 200ms
    actions.user.mouse_rig_speed_to(15, 200, 200, 200)
    cron.after("700ms", check_after_revert)


def test_action_speed_to_hold(on_success, on_failure):
    """Test: actions.user.mouse_rig_speed_to(value, hold) - pulse with standalone hold"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_right()
    actions.user.mouse_rig_speed_to(5)

    def check_after_pulse():
        speed = actions.user.mouse_rig_state_speed()
        if abs(speed - 5) > 0.1:
            on_failure(f"Speed after pulse wrong: expected 5, got {speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    # Speed to 15, hold 500ms, then auto-revert instantly (pulse pattern)
    actions.user.mouse_rig_speed_to(15, 0, 500)
    cron.after("600ms", check_after_pulse)


# ============================================================================
# DIRECTION ACTION TESTS
# ============================================================================

def test_action_direction_to():
    """Test: actions.user.mouse_rig_direction_to(x, y) - set direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_to(1, 0)

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 1.0) < 0.01, f"Direction X wrong: expected 1.0, got {dx}"
    assert abs(dy - 0.0) < 0.01, f"Direction Y wrong: expected 0.0, got {dy}"


def test_action_direction_by():
    """Test: actions.user.mouse_rig_direction_by(degrees) - rotate direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_to(1, 0)  # Start facing right
    actions.user.mouse_rig_direction_by(90)    # Rotate 90° clockwise to down

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 0.0) < 0.01, f"Direction X wrong: expected 0.0, got {dx}"
    assert abs(dy - 1.0) < 0.01, f"Direction Y wrong: expected 1.0, got {dy}"


def test_action_direction_to_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_direction_to(x, y, over_ms) - animated direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_to(1, 0)  # Start facing right

    def check_direction():
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - 0.0) > 0.01 or abs(dy - 1.0) > 0.01:
            on_failure(f"Direction wrong: expected (0.0, 1.0), got ({dx}, {dy})")
            return
        on_success()

    # Curve to down over 300ms
    actions.user.mouse_rig_direction_to(0, 1, 300, "ease_in_out")
    cron.after("400ms", check_direction)


def test_action_direction_by_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_direction_by(degrees, over_ms) - animated rotation"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_to(1, 0)  # Start facing right

    def check_direction():
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - (-1.0)) > 0.01 or abs(dy - 0.0) > 0.01:
            on_failure(f"Direction wrong: expected (-1.0, 0.0), got ({dx}, {dy})")
            return
        on_success()

    # Rotate 180° over 400ms
    actions.user.mouse_rig_direction_by(180, 400, "linear")
    cron.after("500ms", check_direction)


def test_action_direction_left():
    """Test: actions.user.mouse_rig_direction_left() - cardinal direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_left()

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - (-1.0)) < 0.01, f"Direction X wrong: expected -1.0, got {dx}"
    assert abs(dy - 0.0) < 0.01, f"Direction Y wrong: expected 0.0, got {dy}"


def test_action_direction_right():
    """Test: actions.user.mouse_rig_direction_right() - cardinal direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_right()

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 1.0) < 0.01, f"Direction X wrong: expected 1.0, got {dx}"
    assert abs(dy - 0.0) < 0.01, f"Direction Y wrong: expected 0.0, got {dy}"


def test_action_direction_up():
    """Test: actions.user.mouse_rig_direction_up() - cardinal direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_up()

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 0.0) < 0.01, f"Direction X wrong: expected 0.0, got {dx}"
    assert abs(dy - (-1.0)) < 0.01, f"Direction Y wrong: expected -1.0, got {dy}"


def test_action_direction_down():
    """Test: actions.user.mouse_rig_direction_down() - cardinal direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_down()

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 0.0) < 0.01, f"Direction X wrong: expected 0.0, got {dx}"
    assert abs(dy - 1.0) < 0.01, f"Direction Y wrong: expected 1.0, got {dy}"


# ============================================================================
# GO ACTION TESTS
# ============================================================================

def test_action_go_direction():
    """Test: actions.user.mouse_rig_go_direction(x, y, speed) - set direction & speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_go_direction(1, 0, 5)

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 1.0) < 0.01, f"Direction X wrong: expected 1.0, got {dx}"
    assert abs(dy - 0.0) < 0.01, f"Direction Y wrong: expected 0.0, got {dy}"
    assert actions.user.mouse_rig_state_speed() == 5, f"Speed wrong: expected 5, got {actions.user.mouse_rig_state_speed()}"
    actions.user.mouse_rig_stop()


def test_action_go_left():
    """Test: actions.user.mouse_rig_go_left(speed) - go left"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_go_left(3)

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - (-1.0)) < 0.01, f"Direction X wrong: expected -1.0, got {dx}"
    assert abs(dy - 0.0) < 0.01, f"Direction Y wrong: expected 0.0, got {dy}"
    assert actions.user.mouse_rig_state_speed() == 3, f"Speed wrong: expected 3, got {actions.user.mouse_rig_state_speed()}"
    actions.user.mouse_rig_stop()


def test_action_go_right():
    """Test: actions.user.mouse_rig_go_right(speed) - go right"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_go_right(4)

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 1.0) < 0.01, f"Direction X wrong: expected 1.0, got {dx}"
    assert abs(dy - 0.0) < 0.01, f"Direction Y wrong: expected 0.0, got {dy}"
    assert actions.user.mouse_rig_state_speed() == 4, f"Speed wrong: expected 4, got {actions.user.mouse_rig_state_speed()}"
    actions.user.mouse_rig_stop()


def test_action_go_up():
    """Test: actions.user.mouse_rig_go_up(speed) - go up"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_go_up(6)

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 0.0) < 0.01, f"Direction X wrong: expected 0.0, got {dx}"
    assert abs(dy - (-1.0)) < 0.01, f"Direction Y wrong: expected -1.0, got {dy}"
    assert actions.user.mouse_rig_state_speed() == 6, f"Speed wrong: expected 6, got {actions.user.mouse_rig_state_speed()}"
    actions.user.mouse_rig_stop()


def test_action_go_down():
    """Test: actions.user.mouse_rig_go_down(speed) - go down"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_go_down(7)

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 0.0) < 0.01, f"Direction X wrong: expected 0.0, got {dx}"
    assert abs(dy - 1.0) < 0.01, f"Direction Y wrong: expected 1.0, got {dy}"
    assert actions.user.mouse_rig_state_speed() == 7, f"Speed wrong: expected 7, got {actions.user.mouse_rig_state_speed()}"
    actions.user.mouse_rig_stop()


# ============================================================================
# LAYER ACTION TESTS
# ============================================================================

def test_action_layer_speed_offset_by():
    """Test: actions.user.mouse_rig_layer_speed_offset_by() - speed layer offset"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_speed_to(5)
    actions.user.mouse_rig_layer_speed_offset_by("boost", 3)

    assert actions.user.mouse_rig_state_speed() == 8, f"Speed with offset wrong: expected 8, got {actions.user.mouse_rig_state_speed()}"

    actions.user.mouse_rig_layer_revert("boost")
    assert actions.user.mouse_rig_state_speed() == 5, f"Speed after revert wrong: expected 5, got {actions.user.mouse_rig_state_speed()}"
    actions.user.mouse_rig_stop()


def test_action_layer_speed_offset_to():
    """Test: actions.user.mouse_rig_layer_speed_offset_to() - speed layer offset to"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_speed_to(5)
    actions.user.mouse_rig_layer_speed_offset_to("adjust", 2)

    assert actions.user.mouse_rig_state_speed() == 7, f"Speed with offset wrong: expected 7, got {actions.user.mouse_rig_state_speed()}"

    actions.user.mouse_rig_layer_revert("adjust")
    assert actions.user.mouse_rig_state_speed() == 5, f"Speed after revert wrong: expected 5, got {actions.user.mouse_rig_state_speed()}"
    actions.user.mouse_rig_stop()


def test_action_layer_speed_override_to():
    """Test: actions.user.mouse_rig_layer_speed_override_to() - speed layer override"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_speed_to(10)
    actions.user.mouse_rig_layer_speed_override_to("precision", 2)

    assert actions.user.mouse_rig_state_speed() == 2, f"Speed with override wrong: expected 2, got {actions.user.mouse_rig_state_speed()}"

    actions.user.mouse_rig_layer_revert("precision")
    assert actions.user.mouse_rig_state_speed() == 10, f"Speed after revert wrong: expected 10, got {actions.user.mouse_rig_state_speed()}"
    actions.user.mouse_rig_stop()


def test_action_layer_speed_offset_over_hold_revert(on_success, on_failure):
    """Test: actions.user.mouse_rig_layer_speed_offset_by(name, val, over, hold, revert)"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_speed_to(5)

    def check_after_revert():
        speed = actions.user.mouse_rig_state_speed()
        if abs(speed - 5) > 0.1:
            on_failure(f"Speed after revert wrong: expected 5, got {speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    # Offset by 5 over 200ms, hold 200ms, revert over 200ms
    actions.user.mouse_rig_layer_speed_offset_by("temp_boost", 5, 200, 200, 200)
    cron.after("700ms", check_after_revert)


def test_action_layer_revert_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_layer_revert(name, over_ms) - animated revert"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_speed_to(5)
    actions.user.mouse_rig_layer_speed_offset_by("manual_layer", 5)

    # Speed should be 10 now
    if actions.user.mouse_rig_state_speed() != 10:
        on_failure(f"Speed before revert wrong: expected 10, got {actions.user.mouse_rig_state_speed()}")
        return

    def check_after_revert():
        speed = actions.user.mouse_rig_state_speed()
        if abs(speed - 5) > 0.1:
            on_failure(f"Speed after revert wrong: expected 5, got {speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    # Revert layer over 300ms
    actions.user.mouse_rig_layer_revert("manual_layer", 300, "ease_out")
    cron.after("400ms", check_after_revert)


# ============================================================================
# STATE GETTER TESTS
# ============================================================================

def test_action_state_getters():
    """Test: actions.user.mouse_rig_state_* - state getter actions"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_direction_right()
    actions.user.mouse_rig_speed_to(5)

    # Test state getters
    assert actions.user.mouse_rig_state_speed() == 5, "state_speed() failed"

    dx, dy = actions.user.mouse_rig_state_direction()
    assert abs(dx - 1.0) < 0.01, "state_direction() X failed"
    assert abs(dy - 0.0) < 0.01, "state_direction() Y failed"

    pos_x, pos_y = actions.user.mouse_rig_state_pos()
    mouse_x, mouse_y = ctrl.mouse_pos()
    assert pos_x == mouse_x, "state_pos() X failed"
    assert pos_y == mouse_y, "state_pos() Y failed"

    assert actions.user.mouse_rig_state_is_moving() == True, "state_is_moving() failed"
    assert actions.user.mouse_rig_state_direction_cardinal() == "right", "state_direction_cardinal() failed"

    actions.user.mouse_rig_stop()


def test_action_state_layer():
    """Test: actions.user.mouse_rig_state_layer() - layer state"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_speed_to(5)
    actions.user.mouse_rig_layer_speed_offset_by("test_layer", 2)

    assert actions.user.mouse_rig_state_layer("test_layer") == True, "Layer should exist"
    assert "test_layer" in actions.user.mouse_rig_state_layers(), "Layer should be in layers list"

    actions.user.mouse_rig_layer_revert("test_layer")
    assert actions.user.mouse_rig_state_layer("test_layer") == False, "Layer should not exist after revert"

    actions.user.mouse_rig_stop()


def test_action_stop(on_success, on_failure):
    """Test: actions.user.mouse_rig_stop() - stop action"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_go_right(5)

    def check_stopped():
        if actions.user.mouse_rig_state_speed() != 0:
            on_failure(f"Should be stopped, but speed is {actions.user.mouse_rig_state_speed()}")
            return
        on_success()

    actions.user.mouse_rig_stop()
    cron.after("100ms", check_stopped)


def test_action_stop_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_stop(over_ms) - animated stop"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_go_right(10)

    def check_stopped():
        speed = actions.user.mouse_rig_state_speed()
        if speed != 0:
            on_failure(f"Should be stopped, but speed is {speed}")
            return
        on_success()

    # Stop over 300ms
    actions.user.mouse_rig_stop(300, "ease_out")
    cron.after("400ms", check_stopped)


# ============================================================================
# TEST REGISTRY
# ============================================================================

ACTIONS_TESTS = [
    ("actions.user.mouse_rig_pos_to()", test_action_pos_to),
    ("actions.user.mouse_rig_pos_by()", test_action_pos_by),
    ("actions.user.mouse_rig_pos_to() over", test_action_pos_to_over),
    ("actions.user.mouse_rig_pos_by() over", test_action_pos_by_over),
    ("actions.user.mouse_rig_speed_to()", test_action_speed_to),
    ("actions.user.mouse_rig_speed_add()", test_action_speed_add),
    ("actions.user.mouse_rig_speed_mul()", test_action_speed_mul),
    ("actions.user.mouse_rig_speed_to() over", test_action_speed_to_over),
    ("actions.user.mouse_rig_speed_to() hold", test_action_speed_to_hold),
    ("actions.user.mouse_rig_speed_to() hold revert", test_action_speed_to_hold_revert),
    ("actions.user.mouse_rig_direction_to()", test_action_direction_to),
    ("actions.user.mouse_rig_direction_by()", test_action_direction_by),
    ("actions.user.mouse_rig_direction_to() over", test_action_direction_to_over),
    ("actions.user.mouse_rig_direction_by() over", test_action_direction_by_over),
    ("actions.user.mouse_rig_direction_left()", test_action_direction_left),
    ("actions.user.mouse_rig_direction_right()", test_action_direction_right),
    ("actions.user.mouse_rig_direction_up()", test_action_direction_up),
    ("actions.user.mouse_rig_direction_down()", test_action_direction_down),
    ("actions.user.mouse_rig_go_direction()", test_action_go_direction),
    ("actions.user.mouse_rig_go_left()", test_action_go_left),
    ("actions.user.mouse_rig_go_right()", test_action_go_right),
    ("actions.user.mouse_rig_go_up()", test_action_go_up),
    ("actions.user.mouse_rig_go_down()", test_action_go_down),
    ("actions.user.mouse_rig_layer_speed_offset_by()", test_action_layer_speed_offset_by),
    ("actions.user.mouse_rig_layer_speed_offset_to()", test_action_layer_speed_offset_to),
    ("actions.user.mouse_rig_layer_speed_override_to()", test_action_layer_speed_override_to),
    ("actions.user.mouse_rig_layer_speed_offset_by() hold revert", test_action_layer_speed_offset_over_hold_revert),
    ("actions.user.mouse_rig_layer_revert() over", test_action_layer_revert_over),
    ("actions.user.mouse_rig_state_*()", test_action_state_getters),
    ("actions.user.mouse_rig_state_layer()", test_action_state_layer),
    ("actions.user.mouse_rig_stop()", test_action_stop),
    ("actions.user.mouse_rig_stop() over", test_action_stop_over),
]
