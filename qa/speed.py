"""Speed tests for Mouse Rig

Tests for:
- speed.to(value) - set speed to absolute value
- speed.add(delta) - add to current speed
- speed.mul(multiplier) - multiply current speed
- stop(ms) - decelerate to stop over time
- stop(ms).then(callback) - stop with callback
"""

from talon import actions, ctrl, cron


# Test configuration
CENTER_X = 960
CENTER_Y = 540


# ============================================================================
# BASIC SPEED TESTS
# ============================================================================

def test_speed_to():
    """Test: rig.speed.to(value) - instant speed change"""
    rig = actions.user.mouse_rig()
    rig.stop()

    target_speed = 10
    rig.speed.to(target_speed)

    assert rig.state.speed == target_speed, f"Speed wrong: expected {target_speed}, got {rig.state.speed}"
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"
    assert rig._state._frame_loop_job is None, "Frame loop should be stopped"


def test_speed_to_over(on_success, on_failure):
    """Test: rig.speed.to(value).over(ms) - smooth speed transition"""
    rig = actions.user.mouse_rig()
    rig.stop()
    rig.speed.to(5)

    target_speed = 15

    def check_speed():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.speed - target_speed) > 0.1:
            on_failure(f"Final speed wrong: expected {target_speed}, got {rig_check.state.speed}")
            return
        on_success()

    def check_state():
        rig_check = actions.user.mouse_rig()
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return
        if rig_check._state._frame_loop_job is not None:
            on_failure("Frame loop should be stopped")
            return

    rig.speed.to(target_speed).over(500).then(check_speed)
    cron.after("600ms", check_state)


def test_speed_add():
    """Test: rig.speed.add(delta) - add to current speed"""
    rig = actions.user.mouse_rig()
    rig.stop()

    initial_speed = 10
    delta = 5
    expected_speed = initial_speed + delta

    rig.speed.to(initial_speed)
    rig.speed.add(delta)

    assert abs(rig.state.speed - expected_speed) < 0.1, f"Speed wrong: expected {expected_speed}, got {rig.state.speed}"
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"


def test_speed_mul():
    """Test: rig.speed.mul(multiplier) - multiply current speed"""
    rig = actions.user.mouse_rig()
    rig.stop()

    initial_speed = 8
    multiplier = 2
    expected_speed = initial_speed * multiplier

    rig.speed.to(initial_speed)
    rig.speed.mul(multiplier)

    assert abs(rig.state.speed - expected_speed) < 0.1, f"Speed wrong: expected {expected_speed}, got {rig.state.speed}"
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"


# ============================================================================
# STOP TESTS
# ============================================================================

def test_stop_immediate():
    """Test: rig.stop() - immediate stop"""
    rig = actions.user.mouse_rig()
    rig.speed.to(10)
    rig.direction.to(1, 0)

    rig.stop()

    assert rig.state.speed == 0, f"Speed should be 0, got {rig.state.speed}"
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"
    assert rig._state._frame_loop_job is None, "Frame loop should be stopped"
    assert len(rig._state._active_builders) == 0, f"Expected no active builders, got {len(rig._state._active_builders)}"


def test_stop_over(on_success, on_failure):
    """Test: rig.stop(ms) - decelerate to stop over time"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.speed.to(10)
    rig.direction.to(1, 0)

    def check_stopped():
        rig_check = actions.user.mouse_rig()
        if rig_check.state.speed != 0:
            on_failure(f"Speed should be 0, got {rig_check.state.speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return
        if rig_check._state._frame_loop_job is not None:
            on_failure("Frame loop should be stopped")
            return
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return
        on_success()

    rig.stop(500)
    cron.after("600ms", check_stopped)


def test_stop_over_then_callback(on_success, on_failure):
    """Test: rig.stop(ms).then(callback) - stop with callback"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.speed.to(10)
    rig.direction.to(1, 0)

    callback_fired = {"value": False}

    def stop_callback():
        callback_fired["value"] = True
        rig_check = actions.user.mouse_rig()
        if rig_check.state.speed != 0:
            on_failure(f"Speed should be 0 when callback fires, got {rig_check.state.speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return
        if rig_check._state._frame_loop_job is not None:
            on_failure("Frame loop should be stopped when callback fires")
            return

    def verify_callback_fired():
        if not callback_fired["value"]:
            on_failure("Stop callback was never fired")
            return
        on_success()

    rig.stop(500).then(stop_callback)
    cron.after("700ms", verify_callback_fired)


def test_stop_callback_not_fired_on_interrupt(on_success, on_failure):
    """Test: stop callback not fired if interrupted by another operation"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.speed.to(10)
    rig.direction.to(1, 0)

    callback_fired = {"value": False}

    def stop_callback():
        callback_fired["value"] = True

    def interrupt_stop():
        # Start moving again before stop completes
        rig_interrupt = actions.user.mouse_rig()
        rig_interrupt.speed.to(5)

    def verify_callback_not_fired():
        if callback_fired["value"]:
            on_failure("Stop callback should not have fired when interrupted")
            return
        # Clean up
        rig_check = actions.user.mouse_rig()
        rig_check.stop()
        on_success()

    rig.stop(500).then(stop_callback)
    cron.after("200ms", interrupt_stop)  # Interrupt before stop completes
    cron.after("700ms", verify_callback_not_fired)


# ============================================================================
# TEST LIST
# ============================================================================

SPEED_TESTS = [
    test_speed_to,
    test_speed_to_over,
    test_speed_add,
    test_speed_mul,
    test_stop_immediate,
    test_stop_over,
    test_stop_over_then_callback,
    test_stop_callback_not_fired_on_interrupt,
]
