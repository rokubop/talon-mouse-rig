"""Position tests for Mouse Rig

Tests for:
- pos.to() - absolute positioning
- pos.by() - relative positioning
- layer pos.override.to() - layer absolute positioning
- layer pos.offset.by() - layer relative positioning
"""

from talon import actions, ctrl, cron


# Test configuration
CENTER_X = 960
CENTER_Y = 540
TEST_OFFSET = 200


# ============================================================================
# BASIC POSITION TESTS
# ============================================================================

def test_pos_to():
    """Test: rig.pos.to(x, y) - instant move"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y)

    x, y = ctrl.mouse_pos()

    assert x == target_x, f"X position wrong: expected {target_x}, got {x}"
    assert y == target_y, f"Y position wrong: expected {target_y}, got {y}"

    # State checks
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"
    assert rig._state._frame_loop_job is None, "Frame loop should be stopped"
    assert len(rig._state._active_builders) == 0, f"Expected no active builders, got {len(rig._state._active_builders)}"


def test_pos_to_over(on_success, on_failure):
    """Test: rig.pos.to(x, y).over(ms) - smooth transition"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y + TEST_OFFSET

    def check_position():
        x, y = ctrl.mouse_pos()
        if x != target_x or y != target_y:
            on_failure(f"Final position wrong: expected ({target_x}, {target_y}), got ({x}, {y})")
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
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).over(1000).then(check_position)
    cron.after("1100ms", check_state)


def test_pos_to_over_hold_revert(on_success, on_failure):
    """Test: rig.pos.to(x, y).over(ms).hold(ms).revert(ms) - full lifecycle"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y

    def check_after_over():
        x, y = ctrl.mouse_pos()
        if x != target_x or y != target_y:
            on_failure(f"After over: expected ({target_x}, {target_y}), got ({x}, {y})")

    def check_after_hold():
        x, y = ctrl.mouse_pos()
        if x != target_x or y != target_y:
            on_failure(f"After hold: expected ({target_x}, {target_y}), got ({x}, {y})")

    def check_after_revert():
        x, y = ctrl.mouse_pos()
        if x != CENTER_X or y != CENTER_Y:
            on_failure(f"After revert: expected ({CENTER_X}, {CENTER_Y}), got ({x}, {y})")
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
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).over(300).then(check_after_over).hold(300).then(check_after_hold).revert(300).then(check_after_revert)
    cron.after("1000ms", check_state)


def test_pos_to_revert(on_success, on_failure):
    """Test: rig.pos.to(x, y).revert(ms) - instant move then revert"""
    target_x = CENTER_X - TEST_OFFSET
    target_y = CENTER_Y

    def check_position():
        x, y = ctrl.mouse_pos()
        if x != CENTER_X or y != CENTER_Y:
            on_failure(f"After revert: expected ({CENTER_X}, {CENTER_Y}), got ({x}, {y})")
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
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).revert(400).then(check_position)
    cron.after("500ms", check_state)


# ============================================================================
# POSITION BY TESTS
# ============================================================================

def test_pos_by(on_success, on_failure):
    """Test: rig.pos.by(dx, dy) - relative instant move"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, -TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy)

    # Wait for garbage collection, then check position
    def check_position():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx
        expected_y = start_y + dy
        if x == expected_x and y == expected_y:
            # State checks with fresh rig reference
            rig_check = actions.user.mouse_rig()
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
        else:
            on_failure(f"Position wrong: expected ({expected_x}, {expected_y}), got ({x}, {y})")

    cron.after("100ms", check_position)


def test_pos_by_over(on_success, on_failure):
    """Test: rig.pos.by(dx, dy).over(ms) - relative smooth transition"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = -TEST_OFFSET, TEST_OFFSET
    target_x = start_x + dx
    target_y = start_y + dy

    def check_position():
        x, y = ctrl.mouse_pos()
        if x != target_x or y != target_y:
            on_failure(f"Final position wrong: expected ({target_x}, {target_y}), got ({x}, {y})")
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
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).over(500).then(check_position)
    cron.after("600ms", check_state)


def test_pos_by_over_hold_revert(on_success, on_failure):
    """Test: rig.pos.by(dx, dy).over(ms).hold(ms).revert(ms)"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, TEST_OFFSET

    def check_after_over():
        x, y = ctrl.mouse_pos()
        if x != (start_x + dx) or y != (start_y + dy):
            on_failure(f"After over: expected ({start_x + dx}, {start_y + dy}), got ({x}, {y})")

    def check_after_hold():
        x, y = ctrl.mouse_pos()
        if x != (start_x + dx) or y != (start_y + dy):
            on_failure(f"After hold: expected ({start_x + dx}, {start_y + dy}), got ({x}, {y})")

    def check_after_revert():
        x, y = ctrl.mouse_pos()
        if x != start_x or y != start_y:
            on_failure(f"After revert: expected ({start_x}, {start_y}), got ({x}, {y})")
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
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).over(300).then(check_after_over).hold(300).then(check_after_hold).revert(300).then(check_after_revert)
    cron.after("1000ms", check_state)


def test_pos_by_revert(on_success, on_failure):
    """Test: rig.pos.by(dx, dy).revert(ms) - instant relative then revert"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = -TEST_OFFSET, -TEST_OFFSET

    def check_position():
        x, y = ctrl.mouse_pos()
        if x != start_x or y != start_y:
            on_failure(f"After revert: expected ({start_x}, {start_y}), got ({x}, {y})")
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
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).revert(400).then(check_position)
    cron.after("500ms", check_state)


# ============================================================================
# LAYER POSITION TESTS
# ============================================================================

def test_layer_pos_to(on_success, on_failure):
    """Test: layer().pos.override.to(x, y) - without revert keeps position"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y - TEST_OFFSET

    def verify_final():
        x, y = ctrl.mouse_pos()
        if x != target_x or y != target_y:
            on_failure(f"Final position wrong: expected ({target_x}, {target_y}), got ({x}, {y})")
            return
        # State checks - layer should still be active since no revert
        rig_check = actions.user.mouse_rig()
        if "test" not in rig_check.state.layers:
            on_failure(f"Expected 'test' layer to be active, got: {rig_check.state.layers}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.override.to(target_x, target_y).over(300).then(verify_final)


def test_layer_pos_to_revert(on_success, on_failure):
    """Test: layer().pos.override.to(x, y).hold(ms).revert(ms)"""
    target_x = CENTER_X - TEST_OFFSET
    target_y = CENTER_Y + TEST_OFFSET

    def check_after_hold():
        x, y = ctrl.mouse_pos()
        if x != target_x or y != target_y:
            on_failure(f"After hold: expected ({target_x}, {target_y}), got ({x}, {y})")

    def check_after_revert():
        x, y = ctrl.mouse_pos()
        if x != CENTER_X or y != CENTER_Y:
            on_failure(f"After revert: expected ({CENTER_X}, {CENTER_Y}), got ({x}, {y})")
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
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.override.to(target_x, target_y).hold(300).then(check_after_hold).revert(300).then(check_after_revert)
    cron.after("700ms", check_state)


def test_layer_pos_by(on_success, on_failure):
    """Test: layer().pos.offset.by(dx, dy) - without revert keeps offset"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, 0

    def check_target():
        x, y = ctrl.mouse_pos()
        if x != (start_x + dx) or y != (start_y + dy):
            on_failure(f"Final position wrong: expected ({start_x + dx}, {start_y + dy}), got ({x}, {y})")
            return
        # State checks - layer should still be active since no revert
        rig_check = actions.user.mouse_rig()
        if "test" not in rig_check.state.layers:
            on_failure(f"Expected 'test' layer to be active, got: {rig_check.state.layers}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.offset.by(dx, dy).over(300).then(check_target)


def test_layer_pos_by_revert(on_success, on_failure):
    """Test: layer().pos.offset.by(dx, dy).hold(ms).revert(ms)"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, 0

    def check_after_hold():
        x, y = ctrl.mouse_pos()
        if x != (start_x + dx) or y != (start_y + dy):
            on_failure(f"After hold: expected ({start_x + dx}, {start_y + dy}), got ({x}, {y})")

    def check_after_revert():
        x, y = ctrl.mouse_pos()
        if x != start_x or y != start_y:
            on_failure(f"After revert: expected ({start_x}, {start_y}), got ({x}, {y})")
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
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.offset.by(dx, dy).hold(500).then(check_after_hold).revert(300).then(check_after_revert)
    cron.after("900ms", check_state)


# ============================================================================
# MULTIPLE OPERATIONS TESTS
# ============================================================================

def test_pos_by_twice():
    """Test: Two pos.by() calls should stack"""
    start_x, start_y = ctrl.mouse_pos()
    dx1, dy1 = 100, 0
    dx2, dy2 = 0, 100

    rig = actions.user.mouse_rig()
    rig.pos.by(dx1, dy1)
    rig.pos.by(dx2, dy2)

    actions.sleep("100ms")
    x, y = ctrl.mouse_pos()

    expected_x = start_x + dx1 + dx2
    expected_y = start_y + dy1 + dy2

    assert x == expected_x, f"X position wrong: expected {expected_x}, got {x}"
    assert y == expected_y, f"Y position wrong: expected {expected_y}, got {y}"

    # State checks
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"
    assert rig._state._frame_loop_job is None, "Frame loop should be stopped"
    assert len(rig._state._active_builders) == 0, f"Expected no active builders, got {len(rig._state._active_builders)}"


def test_pos_to_then_by():
    """Test: pos.to() followed by pos.by()"""
    target_x = CENTER_X + 100
    target_y = CENTER_Y
    dx, dy = 50, 50

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y)
    actions.sleep("100ms")

    rig.pos.by(dx, dy)
    actions.sleep("100ms")

    x, y = ctrl.mouse_pos()
    expected_x = target_x + dx
    expected_y = target_y + dy

    assert x == expected_x, f"X position wrong: expected {expected_x}, got {x}"
    assert y == expected_y, f"Y position wrong: expected {expected_y}, got {y}"

    # State checks
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"
    assert rig._state._frame_loop_job is None, "Frame loop should be stopped"
    assert len(rig._state._active_builders) == 0, f"Expected no active builders, got {len(rig._state._active_builders)}"


# ============================================================================
# TEST REGISTRY
# ============================================================================

POSITION_TESTS = [
    ("pos.to()", test_pos_to),
    ("pos.to() over", test_pos_to_over),
    ("pos.to() over hold revert", test_pos_to_over_hold_revert),
    ("pos.to() revert", test_pos_to_revert),
    ("pos.by()", test_pos_by),
    ("pos.by() over", test_pos_by_over),
    ("pos.by() over hold revert", test_pos_by_over_hold_revert),
    ("pos.by() revert", test_pos_by_revert),
    ("layer pos.override.to()", test_layer_pos_to),
    ("layer pos.override.to() revert", test_layer_pos_to_revert),
    ("layer pos.offset.by()", test_layer_pos_by),
    ("layer pos.offset.by() revert", test_layer_pos_by_revert),
    ("pos.by() twice", test_pos_by_twice),
    ("pos.to() then by()", test_pos_to_then_by),
]
