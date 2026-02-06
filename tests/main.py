from talon import actions, ctrl, cron
import time
import inspect
import re
from datetime import datetime

CENTER_X = 960
CENTER_Y = 540
TIMEOUT = 5.0

_test_runner_state = {
    "running": False,
    "current_test_index": 0,
    "tests": [],
    "interval_job": None,
    "stop_requested": False,
    "passed_count": 0,
    "failed_count": 0,
    "all_tests_running": False,
    "test_results_file": None
}


def toggle_test_ui(show: bool = None):
    """Main entry point - toggle the QA test UI"""
    try:
        from .position import POSITION_TESTS
        from .speed import SPEED_TESTS
        from .direction import DIRECTION_TESTS
        from .vector import VECTOR_TESTS
        from .validation import VALIDATION_TESTS
        from .contracts import CONTRACTS_TESTS
        from .behaviors import BEHAVIOR_TESTS
        from .actions import ACTIONS_TESTS
        from .special import SPECIAL_TESTS
        from .state import STATE_TESTS
        from .scroll import SCROLL_TESTS
        from .actions_scroll import ACTIONS_SCROLL_TESTS

        test_groups = [
            ("Position", POSITION_TESTS),
            ("Speed", SPEED_TESTS),
            ("Direction", DIRECTION_TESTS),
            ("Vector", VECTOR_TESTS),
            ("Scroll", SCROLL_TESTS),
            ("Validation", VALIDATION_TESTS),
            ("Contracts", CONTRACTS_TESTS),
            ("Behaviors", BEHAVIOR_TESTS),
            ("Special", SPECIAL_TESTS),
            ("Actions", ACTIONS_TESTS),
            ("Actions Scroll", ACTIONS_SCROLL_TESTS),
            ("State", STATE_TESTS)
        ]

        show = show if show is not None else not actions.user.ui_elements_get_trees()

        if show:
            actions.user.ui_elements_show(lambda: test_runner_ui(test_groups))
            actions.user.ui_elements_show(test_result_ui)
            actions.user.ui_elements_show(test_status_ui)
            actions.user.ui_elements_show(test_summary_ui)
        else:
            actions.user.ui_elements_hide(lambda: test_runner_ui(test_groups))
            actions.user.ui_elements_hide(test_result_ui)
            actions.user.ui_elements_hide(test_status_ui)
            actions.user.ui_elements_hide(test_summary_ui)
            actions.user.mouse_rig().stop()
            stop_all_tests()
    except KeyError as e:
        if "ui_elements" in str(e):
            print("\n" + "="*70)
            print("ERROR: Mouse rig testing requires talon-ui-elements")
            print("Get version 0.10.0 or higher from:")
            print("https://github.com/rokubop/talon-ui-elements")
            print("="*70 + "\n")
        raise


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


def move_to_center(fast_mode=False):
    """Move mouse to center position instantly"""
    actions.user.mouse_rig().stop()
    actions.sleep("50ms" if fast_mode else "100ms")

    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("50ms" if fast_mode else "200ms")


def run_single_test(test_name, test_func, on_complete=None, test_group=None, fast_mode=False):
    actions.user.ui_elements_set_state("current_test", test_name)
    actions.user.ui_elements_set_state("test_result", None)

    # Sanitize ID to match ui_elements behavior
    sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', test_name)
    test_button_id = f"test_button_{test_group}_{sanitized_name}"
    actions.user.ui_elements_highlight(test_button_id)

    def on_test_success():
        actions.user.mouse_rig().stop()

        actions.user.ui_elements_set_state("test_result", {
            "success": True,
            "message": "PASSED"
        })
        print(f"PASSED: {test_name}")

        def clear_and_complete():
            actions.user.ui_elements_set_state("test_result", None)
            actions.user.ui_elements_set_state("current_test", None)
            actions.user.ui_elements_unhighlight(test_button_id)
            if on_complete:
                on_complete(True)
        delay = "200ms" if fast_mode else "1s"
        cron.after(delay, clear_and_complete)

    def on_test_failure(error_msg):
        actions.user.mouse_rig().stop()

        actions.user.ui_elements_set_state("test_result", {
            "success": False,
            "message": "FAILED"
        })
        print(f"FAILED: {test_name}")
        print(f"  Error: {error_msg}")

        def clear_and_complete():
            actions.user.ui_elements_set_state("test_result", None)
            actions.user.ui_elements_set_state("current_test", None)
            actions.user.ui_elements_unhighlight(test_button_id)
            if on_complete:
                on_complete(False)
        delay = "200ms" if fast_mode else "1s"
        cron.after(delay, clear_and_complete)

    try:
        # Skip move_to_center for validation and contract tests
        if test_group not in ("Validation", "Contracts"):
            move_to_center(fast_mode)

        sig = inspect.signature(test_func)
        is_async_test = len(sig.parameters) >= 2

        if is_async_test:
            test_func(on_test_success, on_test_failure)
        else:
            try:
                test_func()
                on_test_success()
            except AssertionError as e:
                on_test_failure(str(e))
            except Exception as e:
                on_test_failure(f"Exception: {e}")

    except Exception as e:
        actions.user.ui_elements_set_state("test_result", {
            "success": False,
            "message": "ERROR"
        })
        print(f"ERROR: {test_name}")
        print(f"  Exception: {e}")

        def clear_and_complete():
            actions.user.ui_elements_set_state("test_result", None)
            actions.user.ui_elements_set_state("current_test", None)
            actions.user.ui_elements_unhighlight(test_button_id)
            if on_complete:
                on_complete(False)
        delay = "200ms" if fast_mode else "2s"
        cron.after(delay, clear_and_complete)


def run_all_tests(tests, group_name):
    if _test_runner_state["running"]:
        return

    # Reset rig to clean state before starting test group
    actions.user.mouse_rig().reset()

    _test_runner_state["running"] = True
    _test_runner_state["current_test_index"] = 0
    _test_runner_state["tests"] = tests
    _test_runner_state["group_name"] = group_name
    _test_runner_state["stop_requested"] = False
    _test_runner_state["passed_count"] = 0
    _test_runner_state["failed_count"] = 0

    actions.user.ui_elements_set_state("run_all_active", True)

    def run_next_test():
        if _test_runner_state["stop_requested"]:
            stop_all_tests()
            return

        if _test_runner_state["current_test_index"] >= len(_test_runner_state["tests"]):
            show_summary()
            return

        test_name, test_func = _test_runner_state["tests"][_test_runner_state["current_test_index"]]
        _test_runner_state["current_test_index"] += 1

        def on_test_complete(success):
            actions.user.mouse_rig().stop()

            if success:
                _test_runner_state["passed_count"] += 1
            else:
                _test_runner_state["failed_count"] += 1

            stop_on_fail = actions.user.ui_elements_get_state("stop_on_fail", True)
            if not success and stop_on_fail:
                print("Stopping test run due to failure")
                show_summary()
            elif _test_runner_state["running"]:
                fast_mode = actions.user.ui_elements_get_state("fast_mode", True)
                delay = "50ms" if fast_mode else "200ms"
                cron.after(delay, run_next_test)

        fast_mode = actions.user.ui_elements_get_state("fast_mode", True)
        run_single_test(test_name, test_func, on_complete=on_test_complete, test_group=_test_runner_state["group_name"], fast_mode=fast_mode)

    run_next_test()


def show_summary():
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

    def clear_summary():
        actions.user.ui_elements_set_state("test_summary", None)
        stop_all_tests()

    cron.after("3s", clear_summary)


def stop_all_tests():
    if _test_runner_state["interval_job"]:
        cron.cancel(_test_runner_state["interval_job"])
        _test_runner_state["interval_job"] = None

    _test_runner_state["running"] = False
    _test_runner_state["stop_requested"] = False
    _test_runner_state["current_test_index"] = 0
    _test_runner_state["tests"] = []
    _test_runner_state["all_tests_running"] = False
    _test_runner_state["test_results_file"] = None

    actions.user.ui_elements_set_state("run_all_Position", False)
    actions.user.ui_elements_set_state("run_all_Speed", False)
    actions.user.ui_elements_set_state("run_all_Direction", False)
    actions.user.ui_elements_set_state("run_all_Vector", False)
    actions.user.ui_elements_set_state("run_all_Scroll", False)
    actions.user.ui_elements_set_state("run_all_Validation", False)
    actions.user.ui_elements_set_state("run_all_Contracts", False)
    actions.user.ui_elements_set_state("run_all_Behaviors", False)
    actions.user.ui_elements_set_state("run_all_Special", False)
    actions.user.ui_elements_set_state("run_all_Actions", False)
    actions.user.ui_elements_set_state("run_all_Actions Scroll", False)
    actions.user.ui_elements_set_state("run_all_State", False)
    actions.user.ui_elements_set_state("run_all_tests_global", False)
    actions.user.ui_elements_set_state("current_test", None)


def run_all_tests_global(test_groups):
    """Run all tests from all groups with 0 delay"""
    import os

    if _test_runner_state["running"]:
        return

    # Create test results file
    test_dir = os.path.dirname(os.path.abspath(__file__))
    results_file = os.path.join(os.path.dirname(test_dir), "test_results.txt")
    _test_runner_state["test_results_file"] = results_file

    # Write header to file
    with open(results_file, "w") as f:
        f.write(f"Test Run Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

    # Collect all tests from all groups
    all_tests = []
    for group_name, tests in test_groups:
        for test_name, test_func in tests:
            all_tests.append((test_name, test_func, group_name))

    # Reset rig to clean state before starting global test run
    actions.user.mouse_rig().reset()

    _test_runner_state["running"] = True
    _test_runner_state["all_tests_running"] = True
    _test_runner_state["current_test_index"] = 0
    _test_runner_state["tests"] = all_tests
    _test_runner_state["stop_requested"] = False
    _test_runner_state["passed_count"] = 0
    _test_runner_state["failed_count"] = 0

    actions.user.ui_elements_set_state("run_all_tests_global", True)

    def run_next_test():
        if _test_runner_state["stop_requested"]:
            finalize_results()
            return

        if _test_runner_state["current_test_index"] >= len(_test_runner_state["tests"]):
            finalize_results()
            return

        test_name, test_func, group_name = _test_runner_state["tests"][_test_runner_state["current_test_index"]]
        _test_runner_state["current_test_index"] += 1

        def on_test_complete(success):
            actions.user.mouse_rig().stop()

            if success:
                _test_runner_state["passed_count"] += 1
                result_msg = f"PASSED: {group_name} - {test_name}\n"
            else:
                _test_runner_state["failed_count"] += 1
                result_msg = f"FAILED: {group_name} - {test_name}\n"

            # Write result to file only if running global tests
            if _test_runner_state["test_results_file"]:
                with open(_test_runner_state["test_results_file"], "a") as f:
                    f.write(result_msg)

            stop_on_fail = actions.user.ui_elements_get_state("stop_on_fail", True)
            if not success and stop_on_fail:
                print("Stopping test run due to failure")
                finalize_results()
            elif _test_runner_state["running"]:
                run_next_test()

        fast_mode = actions.user.ui_elements_get_state("fast_mode", True)
        run_single_test(test_name, test_func, on_complete=on_test_complete, test_group=group_name, fast_mode=fast_mode)

    def finalize_results():
        passed = _test_runner_state["passed_count"]
        failed = _test_runner_state["failed_count"]
        total = passed + failed
        all_passed = failed == 0

        # Write summary to file
        with open(_test_runner_state["test_results_file"], "a") as f:
            f.write("\n" + "="*70 + "\n")
            f.write(f"Test Run Complete: {passed}/{total} passed\n")
            if failed > 0:
                f.write(f"Failed: {failed}\n")
            f.write("="*70 + "\n")

        print(f"Test results written to: {_test_runner_state['test_results_file']}")

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

        def clear_summary():
            actions.user.ui_elements_set_state("test_summary", None)
            stop_all_tests()

        cron.after("3s", clear_summary)

    run_next_test()


def toggle_run_all_tests_global(test_groups):
    """Toggle running all tests from all groups"""
    if _test_runner_state["all_tests_running"]:
        _test_runner_state["stop_requested"] = True
        stop_all_tests()
    else:
        run_all_tests_global(test_groups)


def toggle_run_all(tests, group_name):
    state_key = f"run_all_{group_name}"
    if _test_runner_state["running"] and actions.user.ui_elements_get_state(state_key, False):
        _test_runner_state["stop_requested"] = True
        stop_all_tests()
        actions.user.ui_elements_set_state(state_key, False)
    else:
        # Expand the group so test buttons are visible for highlighting
        actions.user.ui_elements_set_state(f"collapsed_{group_name}", False)
        actions.user.ui_elements_set_state(state_key, True)
        run_all_tests(tests, group_name)


def test_runner_ui(test_groups):
    """UI element showing test runner with collapsible groups and run controls"""
    screen, window, div, button, state, icon, text, checkbox = actions.user.ui_elements(
        ["screen", "window", "div", "button", "state", "icon", "text", "checkbox"]
    )

    # Fast mode checkbox (applies to all test runs)
    fast_mode, set_fast_mode = state.use("fast_mode", True)
    stop_on_fail, set_stop_on_fail = state.use("stop_on_fail", True)

    # Run All Tests button at top
    run_all_tests_active = state.get("run_all_tests_global", False)
    run_all_tests_icon = "stop" if run_all_tests_active else "play"
    run_all_tests_label = "Stop All Tests" if run_all_tests_active else "Run All Tests"
    run_all_tests_color = "#ff5555" if run_all_tests_active else "#0088ff"

    checkbox_props = {
        "background_color": "#1e1e1e",
        "border_color": "#3e3e3e",
        "border_width": 1,
        "border_radius": 2,
    }

    run_all_tests_button = div(
        flex_direction="column",
        justify_content="center",
        align_items="center",
        gap=20,
        margin_bottom=32
    )[
        button(
            padding=10,
            padding_left=16,
            padding_right=16,
            background_color=run_all_tests_color,
            flex_direction="row",
            align_items="center",
            gap=8,
            border_radius=4,
            on_click=lambda e: toggle_run_all_tests_global(test_groups)
        )[
            icon(run_all_tests_icon, size=14, color="white"),
            text(run_all_tests_label, color="white", font_weight="bold", font_size=13)
        ],
        div(flex_direction="row", gap=24, align_items="center")[
            div(flex_direction="row", gap=8, align_items="center")[
                checkbox(checkbox_props, background_color="#454545", id="fast_mode", checked=fast_mode, on_change=lambda e: set_fast_mode(e.checked)),
                text("Fast", for_id="fast_mode", color="#cccccc", font_size=14, font_weight="bold"),
            ],
            div(flex_direction="row", gap=8, align_items="center")[
                checkbox(checkbox_props, background_color="#454545", id="stop_on_fail", checked=stop_on_fail, on_change=lambda e: set_stop_on_fail(e.checked)),
                text("Stop on fail", for_id="stop_on_fail", color="#cccccc", font_size=14, font_weight="bold"),
            ]
        ]
    ]

    groups = []

    for group_name, tests in test_groups:
        state_key = f"run_all_{group_name}"
        run_all_active = state.get(state_key, False)
        is_collapsed, set_collapsed = state.use(f"collapsed_{group_name}", True)
        run_all_icon = "stop" if run_all_active else "play"
        run_all_label = f"Stop All {group_name}" if run_all_active else f"Run All {group_name}"
        run_all_color = "#ff5555" if run_all_active else "#00aa00"
        chevron_icon = "chevron_right" if is_collapsed else "chevron_down"

        group_header = div(
            flex_direction="row",
            gap=10,
            align_items="center",
            padding=8,
            background_color="#222222",
            border_radius=4
        )[
            button(
                padding=8,
                padding_right=12,
                background_color="#2a2a2a",
                flex_direction="row",
                align_items="center",
                gap=8,
                flex=1,
                border_radius=3,
                on_click=lambda e, sc=set_collapsed, ic=is_collapsed: sc(not ic)
            )[
                icon(chevron_icon, size=14, color="white"),
                text(group_name, color="white", font_weight="bold", font_size=14)
            ],
            button(
                padding=8,
                padding_left=12,
                padding_right=12,
                background_color=run_all_color,
                flex_direction="row",
                align_items="center",
                gap=8,
                border_radius=3,
                on_click=lambda e, t=tests, g=group_name: toggle_run_all(t, g)
            )[
                icon(run_all_icon, size=14, color="white"),
                text(run_all_label, color="white", font_weight="bold", font_size=13)
            ]
        ]

        test_buttons = []
        if not is_collapsed:
            test_items = []
            for test_name, test_func in tests:
                test_button_id = f"test_button_{group_name}_{test_name}"
                test_items.append(
                    button(
                        test_name,
                        id=test_button_id,
                        padding=8,
                        padding_left=16,
                        margin_bottom=2,
                        background_color="#2a2a2a",
                        color="#cccccc",
                        font_size=13,
                        border_radius=2,
                        on_click=lambda e, f=test_func, n=test_name, g=group_name: run_single_test(n, f, test_group=g, fast_mode=actions.user.ui_elements_get_state("fast_mode", True))
                    )
                )

            test_buttons.append(
                div(
                    flex_direction="column",
                    padding=8,
                    padding_top=4,
                    background_color="#1a1a1a",
                    border_radius=4
                )[
                    *test_items
                ]
            )

        groups.append(
            div(
                flex_direction="column",
                margin_bottom=16
            )[
                group_header,
                *test_buttons
            ]
        )

    return screen(align_items="flex_start", justify_content="flex_start")[
        window(
            title="Mouse Rig Tests",
            on_close=lambda e: (
                e.prevent_default(),
                toggle_test_ui(show=False),
            ),
            padding=12,
            margin=10,
            background_color="#1a1a1a",
            overflow_y="auto",
            max_height=1000
        )[
            run_all_tests_button,
            *groups
        ]
    ]


def test_status_ui():
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
