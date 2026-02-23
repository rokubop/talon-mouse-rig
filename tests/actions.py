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

def test_action_pos_to(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_to(x, y) - instant position"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    target_x = CENTER_X + 100
    target_y = CENTER_Y + 50
    actions.user.mouse_rig_move_to(target_x, target_y)

    def check_position():
        x, y = ctrl.mouse_pos()
        if x != target_x:
            on_failure(f"X position wrong: expected {target_x}, got {x}")
            return
        if y != target_y:
            on_failure(f"Y position wrong: expected {target_y}, got {y}")
            return
        on_success()

    cron.after("50ms", check_position)


def test_action_pos_to_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_to(x, y, over_ms) - animated position"""
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

    actions.user.mouse_rig_move_to(target_x, target_y, 500, "ease_in_out", check_position)


# ============================================================================
# SPEED ACTION TESTS
# ============================================================================

def test_action_speed_to(on_success, on_failure):
    """Test: actions.user.mouse_rig_speed_to(value) - instant speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("right", 10)

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
    actions.user.mouse_rig_move_continuous("up", 5)
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
    actions.user.mouse_rig_move_continuous("left", 5)
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
    actions.user.mouse_rig_move_continuous("right", 5)

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

def test_action_move_continuous_smooth_turn(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_continuous_smooth() - smooth direction change"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("right", 5)

    def check_direction():
        actions.user.mouse_rig_stop()
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - 0.0) > 0.01 or abs(dy - 1.0) > 0.01:
            on_failure(f"Direction wrong: expected (0.0, 1.0), got ({dx}, {dy})")
            return
        on_success()

    # Smooth turn to down; turn_ms = base_turn_ms * speed_factor (~833ms at speed 5)
    actions.user.mouse_rig_move_continuous_smooth("down")
    cron.after("1000ms", check_direction)


def test_action_move_reverse(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_reverse(over_ms) - reverse direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("right", 5)

    def check_direction():
        actions.user.mouse_rig_stop()
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - (-1.0)) > 0.01 or abs(dy - 0.0) > 0.01:
            on_failure(f"Direction wrong: expected (-1.0, 0.0), got ({dx}, {dy})")
            return
        on_success()

    # Reverse over 500ms, check after 600ms
    actions.user.mouse_rig_move_reverse(500)
    cron.after("600ms", check_direction)


def test_action_direction_by(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_rotate(degrees) - rotate direction"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("right", 5)
    actions.user.mouse_rig_move_rotate(90)    # Rotate 90° clockwise to down

    def check_direction():
        actions.user.mouse_rig_stop()
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - 0.0) >= 0.01 or abs(dy - 1.0) >= 0.01:
            on_failure(f"Direction wrong: expected (0.0, 1.0), got ({dx}, {dy})")
            return
        on_success()

    cron.after("500ms", check_direction)


def test_action_direction_by_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_rotate(degrees, over_ms) - animated rotation"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("right", 5)

    def check_direction():
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - (-1.0)) > 0.01 or abs(dy - 0.0) > 0.01:
            on_failure(f"Direction wrong: expected (-1.0, 0.0), got ({dx}, {dy})")
            return
        on_success()

    # Rotate 180° over 400ms
    actions.user.mouse_rig_move_rotate(180, 400, "linear")
    cron.after("500ms", check_direction)


# ============================================================================
# GO ACTION TESTS
# ============================================================================

def test_action_go_left(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_continuous("left", speed) - go left"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("left", 3)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - (-1.0)) >= 0.01 or abs(dy - 0.0) >= 0.01:
            on_failure(f"Direction wrong: expected (-1.0, 0.0), got ({dx}, {dy})")
            return
        on_success()

    cron.after("500ms", check_and_stop)


def test_action_go_right(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_continuous("right", speed) - go right"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("right", 4)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - 1.0) >= 0.01 or abs(dy - 0.0) >= 0.01:
            on_failure(f"Direction wrong: expected (1.0, 0.0), got ({dx}, {dy})")
            return
        on_success()

    cron.after("500ms", check_and_stop)


def test_action_go_up(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_continuous("up", speed) - go up"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("up", 6)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - 0.0) >= 0.01 or abs(dy - (-1.0)) >= 0.01:
            on_failure(f"Direction wrong: expected (0.0, -1.0), got ({dx}, {dy})")
            return
        on_success()

    cron.after("500ms", check_and_stop)


def test_action_go_down(on_success, on_failure):
    """Test: actions.user.mouse_rig_move_continuous("down", speed) - go down"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("down", 7)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - 0.0) >= 0.01 or abs(dy - 1.0) >= 0.01:
            on_failure(f"Direction wrong: expected (0.0, 1.0), got ({dx}, {dy})")
            return
        on_success()

    cron.after("500ms", check_and_stop)


# ============================================================================
# STATE GETTER TESTS
# ============================================================================

def test_action_state_getters(on_success, on_failure):
    """Test: actions.user.mouse_rig_state_* - state getter actions"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("right", 5)

    def check_state():
        # Test state getters
        speed = actions.user.mouse_rig_state_speed()
        if speed != 5:
            on_failure(f"state_speed() failed: expected 5, got {speed}")
            return

        dx, dy = actions.user.mouse_rig_state_direction()
        if abs(dx - 1.0) >= 0.01:
            on_failure(f"state_direction() X failed: expected 1.0, got {dx}")
            return
        if abs(dy - 0.0) >= 0.01:
            on_failure(f"state_direction() Y failed: expected 0.0, got {dy}")
            return

        if actions.user.mouse_rig_state_is_moving() != True:
            on_failure("state_is_moving() failed: expected True")
            return

        cardinal = actions.user.mouse_rig_state_direction_cardinal()
        if cardinal != "right":
            on_failure(f"state_direction_cardinal() failed: expected 'right', got '{cardinal}'")
            return

        actions.user.mouse_rig_stop()
        on_success()

    cron.after("50ms", check_state)


def test_action_stop(on_success, on_failure):
    """Test: actions.user.mouse_rig_stop() - stop action"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_move_continuous("right", 5)

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
    actions.user.mouse_rig_move_continuous("right", 10)

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
    ("actions.user.mouse_rig_move_to()", test_action_pos_to),
    ("actions.user.mouse_rig_move_to() over", test_action_pos_to_over),
    ("actions.user.mouse_rig_speed_to()", test_action_speed_to),
    ("actions.user.mouse_rig_speed_add()", test_action_speed_add),
    ("actions.user.mouse_rig_speed_mul()", test_action_speed_mul),
    ("actions.user.mouse_rig_speed_to() over", test_action_speed_to_over),
    ("actions.user.mouse_rig_speed_to() hold", test_action_speed_to_hold),
    ("actions.user.mouse_rig_speed_to() hold revert", test_action_speed_to_hold_revert),
    ("actions.user.mouse_rig_move_continuous_smooth() turn", test_action_move_continuous_smooth_turn),
    ("actions.user.mouse_rig_move_reverse()", test_action_move_reverse),
    ("actions.user.mouse_rig_move_rotate()", test_action_direction_by),
    ("actions.user.mouse_rig_move_rotate() over", test_action_direction_by_over),
    ("actions.user.mouse_rig_move_continuous('left')", test_action_go_left),
    ("actions.user.mouse_rig_move_continuous('right')", test_action_go_right),
    ("actions.user.mouse_rig_move_continuous('up')", test_action_go_up),
    ("actions.user.mouse_rig_move_continuous('down')", test_action_go_down),
    ("actions.user.mouse_rig_state_*()", test_action_state_getters),
    ("actions.user.mouse_rig_stop()", test_action_stop),
    ("actions.user.mouse_rig_stop() over", test_action_stop_over),
]
