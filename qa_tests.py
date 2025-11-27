"""QA Tests for Mouse Rig Position Operations

Run these tests to verify position operations work correctly.
Each test moves the mouse and validates the result.
"""

from talon import Module, actions, ctrl, cron
import time
import inspect

mod = Module()

# Test configuration
CENTER_X = 960
CENTER_Y = 540
TEST_OFFSET = 200
TIMEOUT = 5.0  # Max seconds to wait for position

def wait_for_position_async(target_x, target_y, tolerance, timeout_ms, on_success, on_failure):
    """Asynchronously wait for mouse position using cron polling"""
    start = time.perf_counter()

    def check_position():
        nonlocal start
        x, y = ctrl.mouse_pos()
        elapsed = (time.perf_counter() - start) * 1000

        if abs(x - target_x) < tolerance and abs(y - target_y) < tolerance:
            on_success()
        elif elapsed >= timeout_ms:
            on_failure(f"Timeout: Failed to reach ({target_x}, {target_y}), stuck at ({x}, {y})")
        else:
            # Check again in 100ms
            cron.after("100ms", check_position)

    check_position()

def wait_for_stop(check_duration=0.3, timeout=TIMEOUT):
    """Wait for mouse to stop moving"""
    start = time.perf_counter()
    last_pos = ctrl.mouse_pos()
    stable_start = None

    while time.perf_counter() - start < timeout:
        actions.sleep("500ms")
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
    # Stop any active rig operations first
    actions.user.mouse_rig().stop()
    actions.sleep("100ms")

    # Use rig to move to center so it knows the position
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("200ms")

def test_buttons_ui():
    """UI element showing all test buttons on left side"""
    screen, div, button, state = actions.user.ui_elements(["screen", "div", "button", "state"])

    tests = [
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

    buttons = []
    for test_name, test_func in tests:
        buttons.append(
            button(
                test_name,
                padding=8,
                margin=2,
                background_color="#333333",
                color="white",
                border_radius=5,
                on_click=lambda e, f=test_func, n=test_name: run_single_test(n, f)
            )
        )

    return screen(align_items="flex_start", justify_content="flex_end")[
        div(
            padding=10,
            background_color="#000000dd",
            border_radius=10,
            margin_bottom=10,
            margin_left=10,
            overflow_y="auto"
        )[*buttons]
    ]

def test_result_ui():
    """UI element showing test result in center bottom"""
    screen, div, text, state, icon = actions.user.ui_elements(["screen", "div", "text", "state", "icon"])

    result = state.get("test_result", None)
    if result is None:
        return screen()

    is_success = result.get("success", False)

    bg_color = "#00ff00dd" if is_success else "#ff0000dd"
    icon_name = "check" if is_success else "close"
    icon_color = "white"
    label = "PASSED" if is_success else "FAILED"

    return screen(align_items="center", justify_content="flex_end")[
        div(
            padding=30,
            margin_bottom=100,
            background_color=bg_color,
            border_radius=15,
            flex_direction="row",
            align_items="center",
            gap=15
        )[
            icon(icon_name, color=icon_color, size=48, stroke_width=3),
            text(label, font_size=48, color="white", font_weight="bold")
        ]
    ]

def run_single_test(test_name, test_func):
    """Run a single test and show result - supports both sync and async tests"""

    # Clear previous result
    actions.user.ui_elements_set_state("test_result", None)

    def on_test_success():
        # Show success
        actions.user.ui_elements_set_state("test_result", {
            "success": True,
            "message": "✓ PASSED"
        })
        print(f"✓ PASSED: {test_name}")

        # Clear result after delay
        cron.after("2s", lambda: actions.user.ui_elements_set_state("test_result", None))

    def on_test_failure(error_msg):
        # Show failure
        actions.user.ui_elements_set_state("test_result", {
            "success": False,
            "message": "✗ FAILED"
        })
        print(f"✗ FAILED: {test_name}")
        print(f"  Error: {error_msg}")

        # Clear result after delay
        cron.after("2s", lambda: actions.user.ui_elements_set_state("test_result", None))

    try:
        # Move to center first
        move_to_center()

        # Check if test function takes callbacks (async test)
        sig = inspect.signature(test_func)
        is_async_test = len(sig.parameters) >= 2

        if is_async_test:
            # Run async test with callbacks
            test_func(on_test_success, on_test_failure)
        else:
            # Run synchronous test
            try:
                test_func()
                on_test_success()
            except AssertionError as e:
                on_test_failure(str(e))
            except Exception as e:
                on_test_failure(f"Exception: {e}")

    except Exception as e:
        # Show error
        actions.user.ui_elements_set_state("test_result", {
            "success": False,
            "message": "✗ ERROR"
        })
        print(f"✗ ERROR: {test_name}")
        print(f"  Exception: {e}")

        cron.after("2s", lambda: actions.user.ui_elements_set_state("test_result", None))

@mod.action_class
class Actions:
    def qa_show_test_ui():
        """Show the QA test UI with buttons"""
        actions.user.ui_elements_show(test_buttons_ui)
        actions.user.ui_elements_show(test_result_ui)

    def qa_hide_test_ui():
        """Hide the QA test UI"""
        actions.user.ui_elements_hide(test_buttons_ui)
        actions.user.ui_elements_hide(test_result_ui)
        actions.user.mouse_rig().stop()

    def qa_run_all_position_tests():
        """Run all position QA tests sequentially"""
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
            ("layer pos.override.to()", test_layer_pos_to),
            ("layer pos.override.to() with revert", test_layer_pos_to_revert),
            ("layer pos.offset.by()", test_layer_pos_by),

            # Multiple operations
            ("pos.by() twice", test_pos_by_twice),
            ("pos.to() then pos.by()", test_pos_to_then_by),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
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

            actions.sleep("200ms")

        print(f"\n{'='*60}")
        print(f"RESULTS: {passed} passed, {failed} failed")
        print(f"{'='*60}")

# ============================================================================
# BASIC POSITION TESTS
# ============================================================================

def test_pos_to():
    """Test: rig.pos.to(x, y) - instant move"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y)

    # time.sleep(0.2)  # Give it a moment
    x, y = ctrl.mouse_pos()

    assert abs(x - target_x) < 10, f"X position wrong: expected {target_x}, got {x}"
    assert abs(y - target_y) < 10, f"Y position wrong: expected {target_y}, got {y}"

def test_pos_to_over(on_success, on_failure):
    """Test: rig.pos.to(x, y).over(ms) - smooth transition"""
    target_x = CENTER_X + TEST_OFFSET
    target_y = CENTER_Y + TEST_OFFSET

    rig = actions.user.mouse_rig()
    rig.pos.to(target_x, target_y).over(1000)

    # Should reach target within reasonable time - use async wait
    wait_for_position_async(target_x, target_y, tolerance=10, timeout_ms=5000,
                           on_success=on_success, on_failure=on_failure)

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

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, dy).over(500)

    # Should reach target within reasonable time
    wait_for_position_async(target_x, target_y, tolerance=10, timeout_ms=5000,
                           on_success=on_success, on_failure=on_failure)

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
    rig.layer("test").pos.override.to(target_x, target_y)

    # Check if reached target
    def check_target():
        x, y = ctrl.mouse_pos()
        if abs(x - target_x) < 10 and abs(y - target_y) < 10:
            # Wait for hold to complete
            cron.after("600ms", verify_final)
        else:
            on_failure(f"Failed to reach target ({target_x}, {target_y}), at ({x}, {y})")

    def verify_final():
        x, y = ctrl.mouse_pos()
        if abs(x - target_x) < 20 and abs(y - target_y) < 20:
            on_success()
        else:
            on_failure(f"Position drifted after hold, expected ({target_x}, {target_y}), at ({x}, {y})")

    cron.after("200ms", check_target)

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
