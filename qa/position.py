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

    assert abs(x - target_x) < 10, f"X position wrong: expected {target_x}, got {x}"
    assert abs(y - target_y) < 10, f"Y position wrong: expected {target_y}, got {y}"

    # State checks
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"
    assert rig._state._frame_loop_job is None, "Frame loop should be stopped"
    assert len(rig._state._active_builders) == 0, f"Expected no active builders, got {len(rig._state._active_builders)}"


def test_pos_to_over(on_success, on_failure):
    """Test: rig.pos.to(x, y).over(ms) - smooth transition"""
    from .main import wait_for_position_async

    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y + TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).over(1000)

    # Should reach target within reasonable time - use async wait
    def on_position_success():
        # Wait a bit for cleanup, then check state with fresh rig reference
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
            on_success()
        cron.after("200ms", check_state)

    wait_for_position_async(target_x, target_y, tolerance=10, timeout_ms=5000,
                           on_success=on_position_success, on_failure=on_failure)


def test_pos_to_over_hold_revert(on_success, on_failure):
    """Test: rig.pos.to(x, y).over(ms).hold(ms).revert(ms) - full lifecycle"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).over(300).hold(300).revert(300)

    # Wait for transition to target
    def check_target():
        x, y = ctrl.mouse_pos()
        if abs(x - target_x) < 10 and abs(y - target_y) < 10:
            # Reached target, now wait through hold and check revert
            cron.after("400ms", check_revert)
        else:
            on_failure(f"Failed to reach target ({target_x}, {target_y}), stuck at ({x}, {y})")

    def check_revert():
        # Check if reverted back to center
        cron.after("400ms", verify_revert)

    def verify_revert():
        x, y = ctrl.mouse_pos()
        if abs(x - CENTER_X) < 10 and abs(y - CENTER_Y) < 10:
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
            on_failure(f"Failed to revert to center ({CENTER_X}, {CENTER_Y}), stuck at ({x}, {y})")

    cron.after("400ms", check_target)


def test_pos_to_revert(on_success, on_failure):
    """Test: rig.pos.to(x, y).revert(ms) - instant move then revert"""
    target_x = CENTER_X - TEST_OFFSET
    target_y = CENTER_Y

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).revert(400)

    # Wait a moment for rig to process, then verify at target
    def check_target():
        x, y = ctrl.mouse_pos()
        if abs(x - target_x) > 50:
            on_failure(f"Not at target position ({target_x}, {target_y}), at ({x}, {y})")
            return
        # Now wait for the 400ms revert to complete
        cron.after("600ms", check_revert)

    def check_revert():
        x, y = ctrl.mouse_pos()
        if abs(x - CENTER_X) < 50 and abs(y - CENTER_Y) < 50:
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
            on_failure(f"Failed to revert to center ({CENTER_X}, {CENTER_Y}), stuck at ({x}, {y})")

    cron.after("100ms", check_target)


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
        if abs(x - expected_x) < 10 and abs(y - expected_y) < 10:
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
    from .main import wait_for_position_async

    start_x, start_y = ctrl.mouse_pos()
    dx, dy = -TEST_OFFSET, TEST_OFFSET
    target_x = start_x + dx
    target_y = start_y + dy

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).over(500)

    # Should reach target within reasonable time
    def on_position_success():
        # Wait a bit for cleanup, then check state with fresh rig reference
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
            on_success()
        cron.after("200ms", check_state)

    wait_for_position_async(target_x, target_y, tolerance=10, timeout_ms=5000,
                           on_success=on_position_success, on_failure=on_failure)


def test_pos_by_over_hold_revert(on_success, on_failure):
    """Test: rig.pos.by(dx, dy).over(ms).hold(ms).revert(ms)"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).over(300).hold(300).revert(300)

    # Check if reached target
    def check_target():
        x, y = ctrl.mouse_pos()
        if abs(x - (start_x + dx)) < 10 and abs(y - (start_y + dy)) < 10:
            # Wait through hold
            cron.after("400ms", check_revert)
        else:
            on_failure(f"Failed to reach target ({start_x + dx}, {start_y + dy}), at ({x}, {y})")

    def check_revert():
        # Check if reverted to start
        cron.after("400ms", verify_revert)

    def verify_revert():
        x, y = ctrl.mouse_pos()
        if abs(x - start_x) < 10 and abs(y - start_y) < 10:
            on_success()
        else:
            on_failure(f"Failed to revert to start ({start_x}, {start_y}), stuck at ({x}, {y})")

    cron.after("400ms", check_target)


def test_pos_by_revert(on_success, on_failure):
    """Test: rig.pos.by(dx, dy).revert(ms) - instant relative then revert"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = -TEST_OFFSET, -TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).revert(400)

    # Wait a moment for rig to process, then verify at offset position
    def check_target():
        x, y = ctrl.mouse_pos()
        if abs(x - (start_x + dx)) > 50 or abs(y - (start_y + dy)) > 50:
            on_failure(f"Not at offset position ({start_x + dx}, {start_y + dy}), at ({x}, {y})")
            return
        # Now wait for the 400ms revert to complete
        cron.after("600ms", check_revert)

    def check_revert():
        x, y = ctrl.mouse_pos()
        if abs(x - start_x) < 50 and abs(y - start_y) < 50:
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
            on_failure(f"Failed to revert to start ({start_x}, {start_y}), stuck at ({x}, {y})")

    cron.after("100ms", check_target)


# ============================================================================
# LAYER POSITION TESTS
# ============================================================================

def test_layer_pos_to(on_success, on_failure):
    """Test: layer().pos.override.to(x, y).hold(ms)"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y - TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.override.to(target_x, target_y).over(300)

    def verify_final():
        x, y = ctrl.mouse_pos()
        if abs(x - target_x) < 20 and abs(y - target_y) < 20:
            # State checks - layer should still be active since no revert
            rig_check = actions.user.mouse_rig()
            if "test" not in rig_check.state.layers:
                on_failure(f"Expected 'test' layer to be active, got: {rig_check.state.layers}")
                return
            on_success()
        else:
            on_failure(f"Position drifted after hold, expected ({target_x}, {target_y}), at ({x}, {y})")

    cron.after("400ms", verify_final)


def test_layer_pos_to_revert(on_success, on_failure):
    """Test: layer().pos.override.to(x, y).hold(ms).revert(ms)"""
    target_x = CENTER_X - TEST_OFFSET
    target_y = CENTER_Y + TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.override.to(target_x, target_y).hold(300).revert(300)

    # Check if reached target
    def check_target():
        x, y = ctrl.mouse_pos()
        if abs(x - target_x) < 10 and abs(y - target_y) < 10:
            # Wait through hold
            cron.after("400ms", check_revert)
        else:
            on_failure(f"Failed to reach target ({target_x}, {target_y}), at ({x}, {y})")

    def check_revert():
        # Check after revert should complete
        cron.after("400ms", verify_revert)

    def verify_revert():
        x, y = ctrl.mouse_pos()
        if abs(x - CENTER_X) < 10 and abs(y - CENTER_Y) < 10:
            # State checks - layer should be cleaned up after revert
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
            on_failure(f"Failed to revert to center ({CENTER_X}, {CENTER_Y}), stuck at ({x}, {y})")

    cron.after("200ms", check_target)


def test_layer_pos_by(on_success, on_failure):
    """Test: layer().pos.offset.by(dx, dy).hold(ms)"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, 0

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.offset.by(dx, dy).hold(500)

    # Check if reached target
    def check_target():
        x, y = ctrl.mouse_pos()
        if abs(x - (start_x + dx)) < 10 and abs(y - (start_y + dy)) < 10:
            # State checks - layer should still be active during hold
            rig_check = actions.user.mouse_rig()
            if "test" not in rig_check.state.layers:
                on_failure(f"Expected 'test' layer to be active, got: {rig_check.state.layers}")
                return
            on_success()
        else:
            on_failure(f"Failed to reach target ({start_x + dx}, {start_y + dy}), at ({x}, {y})")

    cron.after("200ms", check_target)


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

    assert abs(x - expected_x) < 10, f"X position wrong: expected {expected_x}, got {x}"
    assert abs(y - expected_y) < 10, f"Y position wrong: expected {expected_y}, got {y}"

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

    assert abs(x - expected_x) < 10, f"X position wrong: expected {expected_x}, got {x}"
    assert abs(y - expected_y) < 10, f"Y position wrong: expected {expected_y}, got {y}"

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
    ("pos.by() twice", test_pos_by_twice),
    ("pos.to() then by()", test_pos_to_then_by),
]
