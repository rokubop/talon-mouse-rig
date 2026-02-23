"""
Talon Scroll Actions Integration Tests

High-level sanity checks for actions.user.mouse_rig_scroll_* actions.
These test the Talon action API layer for scroll functionality.
"""

from talon import actions, cron


# ============================================================================
# SCROLL SPEED ACTION TESTS
# ============================================================================

def test_action_scroll_speed_to(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_speed_to(value) - instant speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("down", 5)

    def check_speed():
        rig = actions.user.mouse_rig()
        if abs(rig.state.scroll_speed - 5) > 0.1:
            on_failure(f"Scroll speed wrong: expected 5, got {rig.state.scroll_speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    cron.after("50ms", check_speed)


def test_action_scroll_speed_add(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_speed_add(delta) - add to speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("up", 3)
    actions.user.mouse_rig_scroll_speed_add(2)

    def check_speed():
        rig = actions.user.mouse_rig()
        if abs(rig.state.scroll_speed - 5) > 0.1:
            on_failure(f"Scroll speed wrong: expected 5, got {rig.state.scroll_speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    cron.after("50ms", check_speed)


def test_action_scroll_speed_to_over(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_speed_to(value, over_ms) - animated speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("down", 2)

    target_speed = 8

    def check_speed():
        rig = actions.user.mouse_rig()
        speed = rig.state.scroll_speed
        if abs(speed - target_speed) > 0.2:
            on_failure(f"Final scroll speed wrong: expected {target_speed}, got {speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    actions.user.mouse_rig_scroll_speed_to(target_speed, 500)
    cron.after("600ms", check_speed)


def test_action_scroll_speed_to_hold_revert(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_speed_to(value, over, hold, revert) - full lifecycle"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("down", 3)

    def check_after_revert():
        rig = actions.user.mouse_rig()
        speed = rig.state.scroll_speed
        if abs(speed - 3) > 0.2:
            on_failure(f"Scroll speed after revert wrong: expected 3, got {speed}")
            return
        actions.user.mouse_rig_stop()
        on_success()

    # Speed to 10 over 200ms, hold 200ms, revert over 200ms
    actions.user.mouse_rig_scroll_speed_to(10, 200, 200, 200)
    cron.after("700ms", check_after_revert)


# ============================================================================
# SCROLL DIRECTION ACTION TESTS
# ============================================================================

def test_action_scroll_continuous_smooth_turn(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_continuous_smooth() - smooth direction change"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("right", 3)

    def check_direction():
        actions.user.mouse_rig_stop()
        rig = actions.user.mouse_rig()
        direction = rig.state.scroll_direction
        if abs(direction.x - 0.0) > 0.01 or abs(direction.y - 1.0) > 0.01:
            on_failure(f"Scroll direction wrong: expected (0.0, 1.0), got ({direction.x}, {direction.y})")
            return
        on_success()

    # Smooth turn to down; turn_ms = base_turn_ms * speed_factor (~500ms at speed 3)
    actions.user.mouse_rig_scroll_continuous_smooth("down")
    cron.after("700ms", check_direction)


# ============================================================================
# SCROLL GO ACTION TESTS
# ============================================================================

def test_action_scroll_go_vector(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_continuous(direction) via vector - set direction & speed"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("right", 4)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        rig = actions.user.mouse_rig()
        direction = rig.state.scroll_direction
        if abs(direction.x - 1.0) >= 0.01 or abs(direction.y - 0.0) >= 0.01:
            on_failure(f"Scroll direction wrong: expected (1.0, 0.0), got ({direction.x}, {direction.y})")
            return
        on_success()

    cron.after("100ms", check_and_stop)


def test_action_scroll_go_left(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_continuous("left", speed) - scroll left"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("left", 3)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        rig = actions.user.mouse_rig()
        direction = rig.state.scroll_direction
        if abs(direction.x - (-1.0)) >= 0.01 or abs(direction.y - 0.0) >= 0.01:
            on_failure(f"Scroll direction wrong: expected (-1.0, 0.0), got ({direction.x}, {direction.y})")
            return
        on_success()

    cron.after("100ms", check_and_stop)


def test_action_scroll_go_right(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_continuous("right", speed) - scroll right"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("right", 4)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        rig = actions.user.mouse_rig()
        direction = rig.state.scroll_direction
        if abs(direction.x - 1.0) >= 0.01 or abs(direction.y - 0.0) >= 0.01:
            on_failure(f"Scroll direction wrong: expected (1.0, 0.0), got ({direction.x}, {direction.y})")
            return
        on_success()

    cron.after("100ms", check_and_stop)


def test_action_scroll_go_up(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_continuous("up", speed) - scroll up"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("up", 5)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        rig = actions.user.mouse_rig()
        direction = rig.state.scroll_direction
        if abs(direction.x - 0.0) >= 0.01 or abs(direction.y - (-1.0)) >= 0.01:
            on_failure(f"Scroll direction wrong: expected (0.0, -1.0), got ({direction.x}, {direction.y})")
            return
        on_success()

    cron.after("100ms", check_and_stop)


def test_action_scroll_go_down(on_success, on_failure):
    """Test: actions.user.mouse_rig_scroll_continuous("down", speed) - scroll down"""
    actions.user.mouse_rig_stop()
    actions.user.mouse_rig_scroll_continuous("down", 6)

    def check_and_stop():
        actions.user.mouse_rig_stop()
        rig = actions.user.mouse_rig()
        direction = rig.state.scroll_direction
        if abs(direction.x - 0.0) >= 0.01 or abs(direction.y - 1.0) >= 0.01:
            on_failure(f"Scroll direction wrong: expected (0.0, 1.0), got ({direction.x}, {direction.y})")
            return
        on_success()

    cron.after("100ms", check_and_stop)


# ============================================================================
# TEST REGISTRY
# ============================================================================

ACTIONS_SCROLL_TESTS = [
    ("actions.user.mouse_rig_scroll_speed_to()", test_action_scroll_speed_to),
    ("actions.user.mouse_rig_scroll_speed_add()", test_action_scroll_speed_add),
    ("actions.user.mouse_rig_scroll_speed_to() over", test_action_scroll_speed_to_over),
    ("actions.user.mouse_rig_scroll_speed_to() hold revert", test_action_scroll_speed_to_hold_revert),
    ("actions.user.mouse_rig_scroll_continuous_smooth() turn", test_action_scroll_continuous_smooth_turn),
    ("actions.user.mouse_rig_scroll_continuous() vector", test_action_scroll_go_vector),
    ("actions.user.mouse_rig_scroll_continuous('left')", test_action_scroll_go_left),
    ("actions.user.mouse_rig_scroll_continuous('right')", test_action_scroll_go_right),
    ("actions.user.mouse_rig_scroll_continuous('up')", test_action_scroll_go_up),
    ("actions.user.mouse_rig_scroll_continuous('down')", test_action_scroll_go_down),
]
