from talon import actions, cron, ctrl

CENTER_X = 960
CENTER_Y = 540


# ============================================================================
# MOVE PROXY TESTS
# ============================================================================

def test_move_stop_stops_movement_not_scroll(on_success, on_failure):
    """Test: rig.move.stop() stops movement but scroll continues"""
    rig = actions.user.mouse_rig()
    rig.stop()

    def start_test():
        # Start both movement and scroll
        rig.speed.to(5)
        rig.direction.to(1, 0)
        rig.scroll.speed.to(0.5)
        rig.scroll.direction.to(0, 1)

        cron.after("200ms", check_both_active)

    def check_both_active():
        rig_check = actions.user.mouse_rig()
        if rig_check.state.speed < 3:
            on_failure(f"Movement speed should be ~5, got {rig_check.state.speed}")
            return
        if rig_check.state.scroll_speed < 0.3:
            on_failure(f"Scroll speed should be ~0.5, got {rig_check.state.scroll_speed}")
            return

        # Stop only movement
        rig.move.stop()

        cron.after("200ms", check_after_move_stop)

    def check_after_move_stop():
        rig_check = actions.user.mouse_rig()
        # Movement should be stopped
        if rig_check.state.speed > 0.1:
            on_failure(f"Movement speed should be ~0 after move.stop(), got {rig_check.state.speed}")
            return
        # Scroll should still be active
        if rig_check.state.scroll_speed < 0.3:
            on_failure(f"Scroll speed should still be ~0.5 after move.stop(), got {rig_check.state.scroll_speed}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", start_test)


def test_move_stop_with_transition(on_success, on_failure):
    """Test: rig.move.stop(ms) decelerates movement while scroll continues"""
    rig = actions.user.mouse_rig()
    rig.stop()

    def start_test():
        rig.speed.to(10)
        rig.direction.to(1, 0)
        rig.scroll.speed.to(0.5)
        rig.scroll.direction.to(0, 1)

        cron.after("200ms", do_move_stop)

    def do_move_stop():
        rig.move.stop(500)

        cron.after("250ms", check_mid_transition)

    def check_mid_transition():
        rig_check = actions.user.mouse_rig()
        # Should be decelerating (between 0 and 10)
        if rig_check.state.speed < 0.5 or rig_check.state.speed > 9:
            on_failure(f"Expected speed mid-deceleration, got {rig_check.state.speed}")
            return
        # Scroll should be unaffected
        if rig_check.state.scroll_speed < 0.3:
            on_failure(f"Scroll should be unaffected, got {rig_check.state.scroll_speed}")
            return

        cron.after("400ms", check_fully_stopped)

    def check_fully_stopped():
        rig_check = actions.user.mouse_rig()
        if rig_check.state.speed > 0.5:
            on_failure(f"Movement should be stopped, got {rig_check.state.speed}")
            return
        if rig_check.state.scroll_speed < 0.3:
            on_failure(f"Scroll should still be active, got {rig_check.state.scroll_speed}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", start_test)


def test_move_stop_then_callback(on_success, on_failure):
    """Test: rig.move.stop().then(callback) fires callback"""
    rig = actions.user.mouse_rig()
    rig.stop()
    callback_fired = {"value": False}

    def start_test():
        rig.speed.to(5)
        rig.direction.to(1, 0)

        cron.after("200ms", do_stop)

    def do_stop():
        rig.move.stop().then(lambda: callback_fired.__setitem__("value", True))

        cron.after("300ms", check_callback)

    def check_callback():
        if not callback_fired["value"]:
            on_failure("move.stop().then() callback was not fired")
            return

        rig_final = actions.user.mouse_rig()
        rig_final.stop()
        on_success()

    cron.after("100ms", start_test)


def test_move_speed_passthrough(on_success, on_failure):
    """Test: rig.move.speed, rig.move.direction etc. work as passthrough"""
    rig = actions.user.mouse_rig()
    rig.stop()

    def start_test():
        # Use move proxy to set speed and direction
        rig.move.speed.to(7)
        rig.move.direction.to(0, 1)

        cron.after("200ms", check_values)

    def check_values():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.speed - 7) > 1:
            on_failure(f"Speed via move proxy wrong: expected ~7, got {rig_check.state.speed}")
            return
        direction = rig_check.state.direction
        if abs(direction.y - 1) > 0.2:
            on_failure(f"Direction via move proxy wrong: expected (0,1), got ({direction.x}, {direction.y})")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", start_test)


def test_move_scroll_raises_error(on_success, on_failure):
    """Test: rig.move.scroll raises AttributeError"""
    rig = actions.user.mouse_rig()
    rig.stop()

    try:
        _ = rig.move.scroll
        on_failure("rig.move.scroll should raise AttributeError")
    except AttributeError:
        on_success()


def test_move_move_raises_error(on_success, on_failure):
    """Test: rig.move.move raises AttributeError"""
    rig = actions.user.mouse_rig()
    rig.stop()

    try:
        _ = rig.move.move
        on_failure("rig.move.move should raise AttributeError")
    except AttributeError:
        on_success()


def test_move_reset_raises_error(on_success, on_failure):
    """Test: rig.move.reset raises AttributeError"""
    rig = actions.user.mouse_rig()
    rig.stop()

    try:
        rig.move.reset()
        on_failure("rig.move.reset() should raise AttributeError")
    except AttributeError:
        on_success()


def test_move_state_raises_error(on_success, on_failure):
    """Test: rig.move.state raises AttributeError"""
    rig = actions.user.mouse_rig()
    rig.stop()

    try:
        _ = rig.move.state
        on_failure("rig.move.state should raise AttributeError")
    except AttributeError:
        on_success()


def test_move_base_raises_error(on_success, on_failure):
    """Test: rig.move.base raises AttributeError"""
    rig = actions.user.mouse_rig()
    rig.stop()

    try:
        _ = rig.move.base
        on_failure("rig.move.base should raise AttributeError")
    except AttributeError:
        on_success()


def test_move_layer_passthrough(on_success, on_failure):
    """Test: rig.move.layer() works as passthrough"""
    rig = actions.user.mouse_rig()
    rig.stop()

    def start_test():
        rig.speed.to(5)
        rig.direction.to(1, 0)
        rig.move.layer("boost").speed.offset.add(5)

        cron.after("300ms", check_values)

    def check_values():
        rig_check = actions.user.mouse_rig()
        # Base 5 + offset 5 = 10
        if abs(rig_check.state.speed - 10) > 1.5:
            on_failure(f"Speed with move.layer('boost') wrong: expected ~10, got {rig_check.state.speed}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", start_test)


MOVE_TESTS = [
    ("move.stop() movement only", test_move_stop_stops_movement_not_scroll),
    ("move.stop(ms) deceleration", test_move_stop_with_transition),
    ("move.stop().then()", test_move_stop_then_callback),
    ("move.speed passthrough", test_move_speed_passthrough),
    ("move.scroll raises error", test_move_scroll_raises_error),
    ("move.move raises error", test_move_move_raises_error),
    ("move.reset raises error", test_move_reset_raises_error),
    ("move.state raises error", test_move_state_raises_error),
    ("move.base raises error", test_move_base_raises_error),
    ("move.layer() passthrough", test_move_layer_passthrough),
]
