"""QA Test Core - UI, Test Runner, and Helper Functions

This module provides the core test infrastructure:
- Test UI with buttons for running tests
- Test result display
- Async test runner with callbacks
- Helper functions for test setup and validation
"""

from talon import actions, ctrl, cron
import time
import inspect


# Test configuration
CENTER_X = 960
CENTER_Y = 540
TIMEOUT = 5.0  # Max seconds to wait for position

# Test runner state
_test_runner_state = {
    "running": False,
    "current_test_index": 0,
    "tests": [],
    "interval_job": None,
    "stop_requested": False,
    "passed_count": 0,
    "failed_count": 0
}


# ============================================================================
# PUBLIC API
# ============================================================================

def toggle_test_ui(show: bool = None):
    """Main entry point - toggle the QA test UI"""
    # Import test lists directly to avoid circular import issues
    from .position import POSITION_TESTS
    from .speed import SPEED_TESTS
    from .direction import DIRECTION_TESTS

    all_tests = POSITION_TESTS + SPEED_TESTS + DIRECTION_TESTS

    show = show if show is not None else not actions.user.ui_elements_get_trees()

    if show:
        actions.user.ui_elements_show(lambda: test_buttons_ui(all_tests))
        actions.user.ui_elements_show(test_result_ui)
        actions.user.ui_elements_show(test_status_ui)
        actions.user.ui_elements_show(test_summary_ui)
    else:
        actions.user.ui_elements_hide(lambda: test_buttons_ui(all_tests))
        actions.user.ui_elements_hide(test_result_ui)
        actions.user.ui_elements_hide(test_status_ui)
        actions.user.ui_elements_hide(test_summary_ui)
        actions.user.mouse_rig().stop()
        stop_all_tests()


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

def run_single_test(test_name, test_func, on_complete=None):
    """Run a single test and show result - supports both sync and async tests"""

    # Set current test name
    actions.user.ui_elements_set_state("current_test", test_name)
    actions.user.ui_elements_set_state("test_result", None)

    def on_test_success():
        # Show success
        actions.user.ui_elements_set_state("test_result", {
            "success": True,
            "message": "PASSED"
        })
        print(f"PASSED: {test_name}")

        # Clear result after delay
        def clear_and_complete():
            actions.user.ui_elements_set_state("test_result", None)
            actions.user.ui_elements_set_state("current_test", None)
            if on_complete:
                on_complete(True)
        cron.after("1s", clear_and_complete)

    def on_test_failure(error_msg):
        # Show failure
        actions.user.ui_elements_set_state("test_result", {
            "success": False,
            "message": "FAILED"
        })
        print(f"FAILED: {test_name}")
        print(f"  Error: {error_msg}")

        # Clear result after delay
        def clear_and_complete():
            actions.user.ui_elements_set_state("test_result", None)
            actions.user.ui_elements_set_state("current_test", None)
            if on_complete:
                on_complete(False)
        cron.after("1s", clear_and_complete)

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
            "message": "ERROR"
        })
        print(f"ERROR: {test_name}")
        print(f"  Exception: {e}")

        def clear_and_complete():
            actions.user.ui_elements_set_state("test_result", None)
            actions.user.ui_elements_set_state("current_test", None)
            if on_complete:
                on_complete(False)
        cron.after("2s", clear_and_complete)


def run_all_tests(tests):
    """Run all tests in sequence"""
    if _test_runner_state["running"]:
        return

    _test_runner_state["running"] = True
    _test_runner_state["current_test_index"] = 0
    _test_runner_state["tests"] = tests
    _test_runner_state["stop_requested"] = False
    _test_runner_state["passed_count"] = 0
    _test_runner_state["failed_count"] = 0

    actions.user.ui_elements_set_state("run_all_active", True)

    def run_next_test():
        if _test_runner_state["stop_requested"]:
            stop_all_tests()
            return

        if _test_runner_state["current_test_index"] >= len(_test_runner_state["tests"]):
            # All tests complete - show summary
            show_summary()
            return

        test_name, test_func = _test_runner_state["tests"][_test_runner_state["current_test_index"]]
        _test_runner_state["current_test_index"] += 1

        def on_test_complete(success):
            if success:
                _test_runner_state["passed_count"] += 1
            else:
                _test_runner_state["failed_count"] += 1
                
            if not success:
                # Stop on failure and show summary
                print("Stopping test run due to failure")
                show_summary()
            elif _test_runner_state["running"]:
                # Continue to next test
                cron.after("200ms", run_next_test)

        run_single_test(test_name, test_func, on_complete=on_test_complete)

    run_next_test()


def show_summary():
    """Show test run summary"""
    passed = _test_runner_state["passed_count"]
    failed = _test_runner_state["failed_count"]
    total = passed + failed
    
    all_passed = failed == 0
    
    actions.user.ui_elements_set_state("test_summary", {
        "passed": passed,
        "failed": failed,
        "total": total,
        "all_passed": all_passed
    })
    
    print(f"\n{'='*50}")
    print(f"Test Run Complete: {passed}/{total} passed")
    if failed > 0:
        print(f"Failed: {failed}")
    print(f"{'='*50}\n")
    
    # Clear summary after 3 seconds
    def clear_summary():
        actions.user.ui_elements_set_state("test_summary", None)
        stop_all_tests()
    
    cron.after("3s", clear_summary)


def stop_all_tests():
    """Stop the test runner"""
    if _test_runner_state["interval_job"]:
        cron.cancel(_test_runner_state["interval_job"])
        _test_runner_state["interval_job"] = None

    _test_runner_state["running"] = False
    _test_runner_state["stop_requested"] = False
    _test_runner_state["current_test_index"] = 0
    _test_runner_state["tests"] = []

    actions.user.ui_elements_set_state("run_all_active", False)
    actions.user.ui_elements_set_state("current_test", None)


def toggle_run_all(tests):
    """Toggle running all tests"""
    if _test_runner_state["running"]:
        _test_runner_state["stop_requested"] = True
        stop_all_tests()
    else:
        run_all_tests(tests)


# ============================================================================
# UI COMPONENTS
# ============================================================================

def test_buttons_ui(tests):
    """UI element showing all test buttons on left side"""
    screen, window, div, button, state, icon, text = actions.user.ui_elements(
        ["screen", "window", "div", "button", "state", "icon", "text"]
    )

    run_all_active = state.get("run_all_active", False)
    run_all_icon = "stop" if run_all_active else "play"
    run_all_label = "Stop All" if run_all_active else "Run All"
    run_all_color = "#ff5555" if run_all_active else "#00aa00"

    buttons = [
        button(
            padding=10,
            margin=2,
            margin_bottom=8,
            background_color=run_all_color,
            border_radius=5,
            flex_direction="row",
            align_items="center",
            gap=8,
            on_click=lambda e: toggle_run_all(tests)
        )[
            icon(run_all_icon, size=16, color="white"),
            text(run_all_label, color="white", font_weight="bold")
        ]
    ]

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
        window(
            title="Mouse Rig Tests",
            on_close=lambda e: (
                e.prevent_default(),
                toggle_test_ui(show=False),
            ),
            padding=10,
            background_color="#04120A",
            border_radius=4,
            # margin_bottom=10,
            # margin_left=10,
            overflow_y="auto",
            max_height=1000
        )[
            *buttons
        ]
    ]


def test_status_ui():
    """UI element showing currently running test name"""
    screen, div, text, state = actions.user.ui_elements(["screen", "div", "text", "state"])

    current_test = state.get("current_test", None)
    if current_test is None:
        return screen()

    return screen(align_items="center", justify_content="flex_end")[
        div(
            padding=15,
            margin_bottom=250,
            background_color="#0088ffdd",
            border_radius=10
        )[
            text(f"Running: {current_test}", font_size=20, color="white", font_weight="bold")
        ]
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


def test_summary_ui():
    """UI element showing test run summary"""
    screen, div, text, state = actions.user.ui_elements(["screen", "div", "text", "state"])

    summary = state.get("test_summary", None)
    if summary is None:
        return screen()

    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    total = summary.get("total", 0)
    all_passed = summary.get("all_passed", False)

    bg_color = "#00aa00dd" if all_passed else "#ff8800dd"
    
    return screen(align_items="center", justify_content="center")[
        div(
            padding=40,
            background_color=bg_color,
            border_radius=20,
            flex_direction="column",
            align_items="center",
            gap=10
        )[
            text("Test Run Complete", font_size=32, color="white", font_weight="bold"),
            text(f"{passed}/{total} Passed", font_size=24, color="white"),
            text(f"{failed} Failed", font_size=24, color="white") if failed > 0 else div()
        ]
    ]
