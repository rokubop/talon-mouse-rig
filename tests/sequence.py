"""
Sequence & Wait Tests

Tests for mouse_rig_sequence and mouse_rig_wait functionality.
Verifies step ordering, async waiting, sync passthrough, and timed delays.
"""

from talon import actions, ctrl, cron

CENTER_X = 960
CENTER_Y = 540


# ============================================================================
# SEQUENCE BASIC TESTS
# ============================================================================

def test_sequence_sync_steps(on_success, on_failure):
    """Test: sequence with all sync steps runs in order"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    results = []

    actions.user.mouse_rig_sequence([
        lambda: results.append("a"),
        lambda: results.append("b"),
        lambda: results.append("c"),
    ])

    def check():
        if results != ["a", "b", "c"]:
            on_failure(f"Expected ['a', 'b', 'c'], got {results}")
            return
        on_success()

    cron.after("50ms", check)


def test_sequence_async_step(on_success, on_failure):
    """Test: sequence waits for async rig animation before continuing"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    target_x = CENTER_X + 150
    target_y = CENTER_Y
    arrived = []

    actions.user.mouse_rig_sequence([
        lambda: actions.user.mouse_rig_pos_to(target_x, target_y, 300),
        lambda: arrived.append(True),
    ])

    # At 100ms the animation should still be running, arrived should be empty
    def check_mid():
        if arrived:
            on_failure("Sequence didn't wait for async step - arrived too early")
            return

    # At 500ms the animation (300ms) should be done and next step should have run
    def check_final():
        if not arrived:
            on_failure("Sequence didn't continue after async step completed")
            return
        x, y = ctrl.mouse_pos()
        if abs(x - target_x) > 2:
            on_failure(f"Position wrong after sequence: expected x={target_x}, got x={x}")
            return
        on_success()

    cron.after("100ms", check_mid)
    cron.after("500ms", check_final)


def test_sequence_sync_then_async(on_success, on_failure):
    """Test: sync steps run immediately, then waits for async"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    results = []
    target_x = CENTER_X + 100

    actions.user.mouse_rig_sequence([
        lambda: results.append("sync1"),
        lambda: results.append("sync2"),
        lambda: actions.user.mouse_rig_pos_to(target_x, CENTER_Y, 200),
        lambda: results.append("after_async"),
    ])

    # Sync steps should already be done
    def check_sync():
        if "sync1" not in results or "sync2" not in results:
            on_failure(f"Sync steps didn't run immediately: {results}")
            return
        if "after_async" in results:
            on_failure(f"Step after async ran too early: {results}")
            return

    def check_final():
        if results != ["sync1", "sync2", "after_async"]:
            on_failure(f"Expected ['sync1', 'sync2', 'after_async'], got {results}")
            return
        on_success()

    cron.after("50ms", check_sync)
    cron.after("400ms", check_final)


def test_sequence_multiple_async(on_success, on_failure):
    """Test: sequence chains multiple async animations"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    results = []

    actions.user.mouse_rig_sequence([
        lambda: actions.user.mouse_rig_pos_to(CENTER_X + 80, CENTER_Y, 150),
        lambda: results.append("first_done"),
        lambda: actions.user.mouse_rig_pos_to(CENTER_X + 160, CENTER_Y, 150),
        lambda: results.append("second_done"),
    ])

    # After first animation but before second finishes
    def check_mid():
        if "first_done" not in results:
            on_failure(f"First async didn't complete in time: {results}")
            return

    def check_final():
        if results != ["first_done", "second_done"]:
            on_failure(f"Expected ['first_done', 'second_done'], got {results}")
            return
        x, _ = ctrl.mouse_pos()
        if abs(x - (CENTER_X + 160)) > 2:
            on_failure(f"Final position wrong: expected x={CENTER_X + 160}, got x={x}")
            return
        on_success()

    cron.after("250ms", check_mid)
    cron.after("600ms", check_final)


def test_sequence_empty(on_success, on_failure):
    """Test: empty sequence doesn't error"""
    actions.user.mouse_rig_stop()

    try:
        actions.user.mouse_rig_sequence([])
    except Exception as e:
        on_failure(f"Empty sequence raised: {e}")
        return

    cron.after("50ms", on_success)


def test_sequence_single_step(on_success, on_failure):
    """Test: single-step sequence works"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    target_x = CENTER_X + 100
    actions.user.mouse_rig_sequence([
        lambda: actions.user.mouse_rig_pos_to(target_x, CENTER_Y),
    ])

    def check():
        x, _ = ctrl.mouse_pos()
        if x != target_x:
            on_failure(f"Position wrong: expected x={target_x}, got x={x}")
            return
        on_success()

    cron.after("50ms", check)


# ============================================================================
# WAIT TESTS
# ============================================================================

def test_wait_basic(on_success, on_failure):
    """Test: mouse_rig_wait delays execution in sequence"""
    actions.user.mouse_rig_stop()

    results = []

    actions.user.mouse_rig_sequence([
        lambda: results.append("before"),
        lambda: actions.user.mouse_rig_wait(300),
        lambda: results.append("after"),
    ])

    # At 100ms, "after" shouldn't have run yet
    def check_mid():
        if "after" in results:
            on_failure(f"Wait didn't delay: results={results}")
            return

    # At 500ms, "after" should have run
    def check_final():
        if results != ["before", "after"]:
            on_failure(f"Expected ['before', 'after'], got {results}")
            return
        on_success()

    cron.after("100ms", check_mid)
    cron.after("500ms", check_final)


def test_wait_between_animations(on_success, on_failure):
    """Test: wait between two position animations"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    mid_x = CENTER_X + 80
    final_x = CENTER_X + 160

    actions.user.mouse_rig_sequence([
        lambda: actions.user.mouse_rig_pos_to(mid_x, CENTER_Y, 150),
        lambda: actions.user.mouse_rig_wait(200),
        lambda: actions.user.mouse_rig_pos_to(final_x, CENTER_Y, 150),
    ])

    # After first move + part of wait, should be at mid_x
    def check_mid():
        x, _ = ctrl.mouse_pos()
        if abs(x - mid_x) > 5:
            on_failure(f"Mid position wrong: expected ~{mid_x}, got {x}")
            return

    # After everything (150 + 200 + 150 = 500ms), should be at final_x
    def check_final():
        x, _ = ctrl.mouse_pos()
        if abs(x - final_x) > 2:
            on_failure(f"Final position wrong: expected {final_x}, got {x}")
            return
        on_success()

    cron.after("250ms", check_mid)
    cron.after("700ms", check_final)


# ============================================================================
# SEQUENCE WITH STOP HANDLE
# ============================================================================

def test_sequence_with_stop(on_success, on_failure):
    """Test: sequence with stop handle waits for deceleration"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    results = []

    actions.user.mouse_rig_sequence([
        lambda: actions.user.mouse_rig_go("right", 5),
        lambda: actions.user.mouse_rig_wait(200),
        lambda: actions.user.mouse_rig_stop(300),
        lambda: results.append("stopped"),
    ])

    # At 300ms (200 wait + starting decel), shouldn't be stopped yet
    def check_mid():
        if "stopped" in results:
            on_failure("Stop completed too early")
            return

    # At 700ms (200 wait + 300 decel + buffer), should be stopped
    def check_final():
        if not results:
            on_failure("Stop callback never fired")
            return
        rig = actions.user.mouse_rig()
        if rig.state.speed > 0.1:
            on_failure(f"Speed not zero after stop: {rig.state.speed}")
            return
        on_success()

    cron.after("300ms", check_mid)
    cron.after("700ms", check_final)


# ============================================================================
# DRAG PATTERN TEST
# ============================================================================

def test_sequence_drag_pattern(on_success, on_failure):
    """Test: simulated drag pattern (hold → move → release) ordering"""
    actions.user.mouse_rig_stop()
    ctrl.mouse_move(CENTER_X, CENTER_Y)

    target_x = CENTER_X + 200
    results = []

    actions.user.mouse_rig_sequence([
        lambda: results.append("hold"),
        lambda: actions.user.mouse_rig_pos_to(target_x, CENTER_Y, 300),
        lambda: results.append("release"),
    ])

    # Mid-animation: hold should have fired, release should NOT have
    def check_mid():
        if "hold" not in results:
            on_failure(f"Hold didn't fire before move: {results}")
            return
        if "release" in results:
            on_failure(f"Release fired during move (didn't wait): {results}")
            return

    # After animation: release should have fired, position should be correct
    def check_final():
        if results != ["hold", "release"]:
            on_failure(f"Expected ['hold', 'release'], got {results}")
            return
        x, _ = ctrl.mouse_pos()
        if abs(x - target_x) > 2:
            on_failure(f"Final position wrong: expected x={target_x}, got x={x}")
            return
        on_success()

    cron.after("100ms", check_mid)
    cron.after("500ms", check_final)


# ============================================================================
# TEST REGISTRY
# ============================================================================

SEQUENCE_TESTS = [
    ("sequence: sync steps order", test_sequence_sync_steps),
    ("sequence: waits for async", test_sequence_async_step),
    ("sequence: sync then async", test_sequence_sync_then_async),
    ("sequence: multiple async", test_sequence_multiple_async),
    ("sequence: empty list", test_sequence_empty),
    ("sequence: single step", test_sequence_single_step),
    ("wait: basic delay", test_wait_basic),
    ("wait: between animations", test_wait_between_animations),
    ("sequence: with stop handle", test_sequence_with_stop),
    ("sequence: drag pattern", test_sequence_drag_pattern),
]
