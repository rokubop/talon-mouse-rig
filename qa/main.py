"""QA Test Core - UI, Test Runner, and Helper Functions

This module provides the core test infrastructure:
- Test UI with buttons for running tests
- Test result display
- Async test runner with callbacks
- Helper functions for test setup and validation
"""

from talon import Module, actions, ctrl, cron
import time
import inspect


mod = Module()


# Test configuration
CENTER_X = 960
CENTER_Y = 540
TIMEOUT = 5.0  # Max seconds to wait for position


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

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


# ============================================================================
# TEST RUNNER
# ============================================================================

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


# ============================================================================
# UI COMPONENTS
# ============================================================================

def test_buttons_ui(tests):
    """UI element showing all test buttons on left side"""
    screen, div, button, state = actions.user.ui_elements(["screen", "div", "button", "state"])

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


# ============================================================================
# ACTIONS
# ============================================================================

@mod.action_class
class Actions:
    def mouse_rig_test_toggle_ui(tests: list):
        """Show the QA test UI with buttons for the given test list"""
        actions.user.ui_elements_toggle(lambda: test_buttons_ui(tests))
        actions.user.ui_elements_toggle(test_result_ui)

        if not actions.user.ui_elements_get_trees():
            actions.user.mouse_rig().stop()
