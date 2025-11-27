"""QA Tests for Mouse Rig Position Operations

Run these tests to verify position operations work correctly.
Each test moves the mouse and validates the result.
"""

from talon import Module, actions, ctrl
import time

mod = Module()

# Test configuration
CENTER_X = 960
CENTER_Y = 540
TEST_OFFSET = 200
TIMEOUT = 5.0  # Max seconds to wait for position

def wait_for_position(target_x, target_y, tolerance=10, timeout=TIMEOUT):
    """Wait for mouse to reach target position within tolerance"""
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        x, y = ctrl.mouse_pos()
        if abs(x - target_x) < tolerance and abs(y - target_y) < tolerance:
            return True
        time.sleep(0.5)
    return False

def wait_for_stop(check_duration=0.3, timeout=TIMEOUT):
    """Wait for mouse to stop moving"""
    start = time.perf_counter()
    last_pos = ctrl.mouse_pos()
    stable_start = None

    while time.perf_counter() - start < timeout:
        time.sleep(0.5)
        current_pos = ctrl.mouse_pos()

        if current_pos == last_pos:
            if stable_start is None:
                stable_start = time.perf_counter()
            elif time.perf_counter() - stable_start >= check_duration:
                return True
        else:
            stable_start = None
            last_pos = current_pos

    return False

def move_to_center():
    """Move mouse to center position instantly"""
    ctrl.mouse_move(CENTER_X, CENTER_Y)
    time.sleep(0.1)

def current_test_ui():
    """UI element to display current test name"""
    screen, div, text, state = actions.user.ui_elements(["screen", "div", "text", "state"])
    test_name = state.get("test_name", "")
    return screen(align_items="center", justify_content="flex_end")[
        div(padding=20, background_color="#000000cc", border_radius=10)[
            text(test_name, font_size=24, color="white")
        ]
    ]

@mod.action_class
class Actions:
    def qa_run_all_position_tests():
        """Run all position QA tests"""
        try:
            actions.user.ui_elements_show(current_test_ui)

            tests = [
                # Basic position operations
                ("pos.to()", test_pos_to),
                ("pos.to() with over", test_pos_to_over),
                ("pos.to() with over hold revert", test_pos_to_over_hold_revert),
                ("pos.to() with revert", test_pos_to_revert),

                # Position by operations
                ("pos.by()", test_pos_by),
                ("pos.by() with over", test_pos_by_over),
                ("pos.by() with over hold revert", test_pos_by_over_hold_revert),
                ("pos.by() with revert", test_pos_by_revert),

                # Layer position operations
                ("layer pos.to()", test_layer_pos_to),
                ("layer pos.to() with revert", test_layer_pos_to_revert),
                ("layer pos.by()", test_layer_pos_by),

                # Multiple operations
                ("pos.by() twice", test_pos_by_twice),
                ("pos.to() then pos.by()", test_pos_to_then_by),
            ]

            passed = 0
            failed = 0

            for test_name, test_func in tests:
                actions.user.ui_elements_set_state("test_name", f"Running: {test_name}")
                print(f"\n{'='*60}")
                print(f"TEST: {test_name}")
                print(f"{'='*60}")

                try:
                    move_to_center()
                    test_func()
                    print(f"✓ PASSED: {test_name}")
                    passed += 1
                except AssertionError as e:
                    print(f"✗ FAILED: {test_name}")
                    print(f"  Error: {e}")
                    failed += 1
                except Exception as e:
                    print(f"✗ ERROR: {test_name}")
                    print(f"  Exception: {e}")
                    failed += 1

                # Stop everything between tests
                actions.user.mouse_rig().stop()
                time.sleep(0.2)

            print(f"\n{'='*60}")
            print(f"RESULTS: {passed} passed, {failed} failed")
            print(f"{'='*60}")

            actions.user.ui_elements_set_state("test_name", f"Done: {passed} passed, {failed} failed")
            time.sleep(2)

        finally:
            actions.user.ui_elements_hide(current_test_ui)
            actions.user.mouse_rig().stop()

# ============================================================================
# BASIC POSITION TESTS
# ============================================================================

def test_pos_to():
    """Test: rig.pos.to(x, y) - instant move"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y)

    time.sleep(0.1)  # Give it a moment
    x, y = ctrl.mouse_pos()

    assert abs(x - target_x) < 10, f"X position wrong: expected {target_x}, got {x}"
    assert abs(y - target_y) < 10, f"Y position wrong: expected {target_y}, got {y}"

def test_pos_to_over():
    """Test: rig.pos.to(x, y).over(ms) - smooth transition"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y + TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).over(500)

    # Should not be at target immediately
    time.sleep(0.05)
    x, y = ctrl.mouse_pos()
    distance = ((x - target_x)**2 + (y - target_y)**2)**0.5
    assert distance > 50, "Mouse moved too fast, should be transitioning"

    # Should reach target
    assert wait_for_position(target_x, target_y), f"Failed to reach target position"

def test_pos_to_over_hold_revert():
    """Test: rig.pos.to(x, y).over(ms).hold(ms).revert(ms) - full lifecycle"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).over(300).hold(300).revert(300)

    # Wait for transition
    assert wait_for_position(target_x, target_y, timeout=3), "Failed to reach target"

    # Wait through hold
    time.sleep(0.4)

    # Should revert back to center
    assert wait_for_position(CENTER_X, CENTER_Y, timeout=3), "Failed to revert to start"

def test_pos_to_revert():
    """Test: rig.pos.to(x, y).revert(ms) - instant move then revert"""
    target_x = CENTER_X - TEST_OFFSET
    target_y = CENTER_Y

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).revert(400)

    # Should be at target quickly
    time.sleep(0.1)
    assert wait_for_position(target_x, target_y, timeout=2), "Failed to reach target"

    # Should revert back
    assert wait_for_position(CENTER_X, CENTER_Y, timeout=3), "Failed to revert"

# ============================================================================
# POSITION BY TESTS
# ============================================================================

def test_pos_by():
    """Test: rig.pos.by(dx, dy) - relative instant move"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, -TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy)

    time.sleep(0.1)
    x, y = ctrl.mouse_pos()

    assert abs(x - (start_x + dx)) < 10, f"X offset wrong: expected {start_x + dx}, got {x}"
    assert abs(y - (start_y + dy)) < 10, f"Y offset wrong: expected {start_y + dy}, got {y}"

def test_pos_by_over():
    """Test: rig.pos.by(dx, dy).over(ms) - relative smooth transition"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = -TEST_OFFSET, TEST_OFFSET
    target_x = start_x + dx
    target_y = start_y + dy

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).over(500)

    # Should be moving
    time.sleep(0.05)
    x, y = ctrl.mouse_pos()
    distance_from_start = ((x - start_x)**2 + (y - start_y)**2)**0.5
    assert distance_from_start < abs(dx), "Mouse moved too fast"

    # Should reach target
    assert wait_for_position(target_x, target_y), "Failed to reach target"

def test_pos_by_over_hold_revert():
    """Test: rig.pos.by(dx, dy).over(ms).hold(ms).revert(ms)"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).over(300).hold(300).revert(300)

    # Should reach offset position
    assert wait_for_position(start_x + dx, start_y + dy, timeout=3), "Failed to reach target"

    # Wait through hold
    time.sleep(0.4)

    # Should revert to start
    assert wait_for_position(start_x, start_y, timeout=3), "Failed to revert"

def test_pos_by_revert():
    """Test: rig.pos.by(dx, dy).revert(ms) - instant relative then revert"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = -TEST_OFFSET, -TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).revert(400)

    # Should reach offset
    time.sleep(0.1)
    assert wait_for_position(start_x + dx, start_y + dy, timeout=2), "Failed to reach target"

    # Should revert
    assert wait_for_position(start_x, start_y, timeout=3), "Failed to revert"

# ============================================================================
# LAYER POSITION TESTS
# ============================================================================

def test_layer_pos_to():
    """Test: layer().pos.to(x, y).hold(ms)"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y - TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.to(target_x, target_y).hold(500)

    # Should reach target
    time.sleep(0.1)
    assert wait_for_position(target_x, target_y, timeout=2), "Failed to reach target"

    # Wait for hold to complete
    time.sleep(0.6)

    # Layer should clean up (stay at position since no revert)
    x, y = ctrl.mouse_pos()
    assert abs(x - target_x) < 20, "Position drifted after hold"

def test_layer_pos_to_revert():
    """Test: layer().pos.to(x, y).hold(ms).revert(ms)"""
    target_x = CENTER_X - TEST_OFFSET
    target_y = CENTER_Y + TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.to(target_x, target_y).hold(300).revert(300)

    # Should reach target
    assert wait_for_position(target_x, target_y, timeout=2), "Failed to reach target"

    # Wait through hold
    time.sleep(0.4)

    # Should revert to center
    assert wait_for_position(CENTER_X, CENTER_Y, timeout=3), "Failed to revert"

def test_layer_pos_by():
    """Test: layer().pos.by(dx, dy).hold(ms)"""
    start_x, start_y = ctrl.mouse_pos()
    dx, dy = TEST_OFFSET, 0

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.by(dx, dy).hold(500)

    # Should reach target
    time.sleep(0.1)
    assert wait_for_position(start_x + dx, start_y + dy, timeout=2), "Failed to reach target"

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

    time.sleep(0.1)
    x, y = ctrl.mouse_pos()

    expected_x = start_x + dx1 + dx2
    expected_y = start_y + dy1 + dy2

    assert abs(x - expected_x) < 10, f"X position wrong: expected {expected_x}, got {x}"
    assert abs(y - expected_y) < 10, f"Y position wrong: expected {expected_y}, got {y}"

def test_pos_to_then_by():
    """Test: pos.to() followed by pos.by()"""
    target_x = CENTER_X + 100
    target_y = CENTER_Y
    dx, dy = 50, 50

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y)
    time.sleep(0.1)

    rig.pos.by(dx, dy)
    time.sleep(0.1)

    x, y = ctrl.mouse_pos()
    expected_x = target_x + dx
    expected_y = target_y + dy

    assert abs(x - expected_x) < 10, f"X position wrong: expected {expected_x}, got {x}"
    assert abs(y - expected_y) < 10, f"Y position wrong: expected {expected_y}, got {y}"
