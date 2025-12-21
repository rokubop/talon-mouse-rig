from talon import actions, ctrl, cron

CENTER_X = 960
CENTER_Y = 540
TEST_OFFSET = 200


# ============================================================================
# STACK BEHAVIOR TESTS
# ============================================================================

def test_behavior_stack_property_syntax(on_success, on_failure):
    """Test: pos.offset.by().stack() - stack behavior using implicit layers"""
    start_x, start_y = ctrl.mouse_pos()
    dx1, dy1 = 0, 100
    dx2, dy2 = 100, 0

    def check_stacked():
        x, y = ctrl.mouse_pos()
        # Both offsets should be stacked
        expected_x = start_x + dx2
        expected_y = start_y + dy1
        if abs(x - expected_x) > 2 or abs(y - expected_y) > 2:
            on_failure(f"Stacked offset wrong: expected ({expected_x}, {expected_y}), got ({x}, {y})")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # First offset: down, shorter transition (implicit layer: "pos.offset")
    rig.pos.offset.by(dx1, dy1).stack().api("talon").over(400)
    # Second offset: right, longer transition, starts while first is active
    cron.after("200ms", lambda: rig.pos.offset.by(dx2, dy2).stack().api("talon").over(400))
    # Check after second completes (first will have finished already)
    cron.after("1000ms", check_stacked)


def test_behavior_stack_call_syntax_with_max(on_success, on_failure):
    """Test: pos.offset.by().stack(max=2) - stack with max count"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 50

    def check_result():
        x, y = ctrl.mouse_pos()
        # With max=2, should only have 2 stacks (100px total), not 3 (150px)
        expected_x = start_x + (dx * 2)
        if abs(x - expected_x) > 2:
            on_failure(f"Stack max failed: expected x={expected_x}, got {x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Add 3 stacks but max is 2 (implicit layer: "pos.offset")
    rig.pos.offset.by(dx, 0).stack(max=2).api("talon").over(100)
    cron.after("50ms", lambda: rig.pos.offset.by(dx, 0).stack(max=2).api("talon").over(100))
    cron.after("100ms", lambda: rig.pos.offset.by(dx, 0).stack(max=2).api("talon").over(100))
    cron.after("400ms", check_result)


# ============================================================================
# REPLACE BEHAVIOR TESTS
# ============================================================================

def test_behavior_replace_property_syntax(on_success, on_failure):
    """Test: pos.offset.by().replace() - replace old offset with new"""
    start_x, start_y = ctrl.mouse_pos()
    dx1, dy1 = 100, 0
    dx2, dy2 = 50, 0

    def check_first():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx1
        if abs(x - expected_x) > 2 or abs(y - start_y) > 2:
            on_failure(f"First offset wrong: expected ({expected_x}, {start_y}), got ({x}, {y})")
            return

    def check_replace():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx2  # Should be dx2 only, not dx1+dx2
        if abs(x - expected_x) > 2 or abs(y - start_y) > 2:
            on_failure(f"Replace offset wrong: expected ({expected_x}, {start_y}), got ({x}, {y})")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Implicit layer "pos.offset"
    rig.pos.offset.by(dx1, dy1).api("talon").over(300).then(check_first)
    cron.after("100ms", lambda: rig.pos.offset.by(dx2, dy2).replace().api("talon").over(300).then(check_replace))


def test_behavior_replace_call_syntax(on_success, on_failure):
    """Test: pos.offset.by().replace() - replace using call syntax"""
    start_x, start_y = ctrl.mouse_pos()
    dx1 = 100
    dx2 = 50

    def check_replace():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx2
        if abs(x - expected_x) > 2:
            on_failure(f"Replace failed: expected x={expected_x}, got {x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Implicit layer "pos.offset"
    rig.pos.offset.by(dx1, 0).api("talon").over(300)
    cron.after("100ms", lambda: rig.pos.offset.by(dx2, 0).replace().api("talon").over(300).then(check_replace))


def test_behavior_pos_offset_by_over_revert(on_success, on_failure):
    """Test: pos.offset.by().over().revert() - should revert back to start position"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 50

    def check_pos():
        x, y = ctrl.mouse_pos()
        # After revert, should be back at start position
        if x != start_x or y != start_y:
            on_failure(f"After revert: expected ({start_x}, {start_y}), got ({x}, {y})")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Implicit layer "pos.offset"
    rig.pos.offset.by(dx, 0).api("talon").over(300).revert(300).then(check_pos)


def test_behavior_replace_pos_offset_by_over_revert(on_success, on_failure):
    """Test: replace().pos.offset.by().over().revert() - replace during animation, should still revert to start"""
    start_x, start_y = ctrl.mouse_pos()
    dx1 = 100
    dx2 = 50

    def check_pos():
        x, y = ctrl.mouse_pos()
        # After replace and revert, should be back at start position
        if x != start_x or y != start_y:
            on_failure(f"After replace+revert: expected ({start_x}, {start_y}), got ({x}, {y})")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Start first animation (implicit layer "pos.offset")
    rig.pos.offset.by(dx1, 0).api("talon").over(300).revert(300)
    # Replace it mid-flight with a different offset
    cron.after("100ms", lambda: rig.pos.offset.by(dx2, 0).replace().api("talon").over(300).revert(300).then(check_pos))


def test_behavior_replace_pos_override_to_over(on_success, on_failure):
    """Test: replace with pos.override.to().over() - absolute positioning"""
    start_x, start_y = ctrl.mouse_pos()
    target1_x, target1_y = start_x + 100, start_y
    target2_x, target2_y = start_x + 50, start_y

    def check_replace():
        x, y = ctrl.mouse_pos()
        if abs(x - target2_x) > 2 or abs(y - target2_y) > 2:
            on_failure(f"Replace position wrong: expected ({target2_x}, {target2_y}), got ({x}, {y})")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Implicit layer "pos.override"
    rig.pos.override.to(target1_x, target1_y).over(300)
    cron.after("100ms", lambda: rig.pos.override.to(target2_x, target2_y).replace().over(300).then(check_replace))


def test_behavior_replace_speed_override_to_over(on_success, on_failure):
    """Test: replace with speed.override.to().over()"""
    start_x, start_y = ctrl.mouse_pos()

    def check_movement():
        x, y = ctrl.mouse_pos()
        # Should have moved right due to speed=5
        if x <= start_x:
            on_failure(f"No movement detected: start={start_x}, current={x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Start with speed 10 (implicit layer "speed.override")
    rig.speed.override.to(10).over(100)
    # Replace with speed 5 after 50ms
    cron.after("50ms", lambda: rig.speed.override.to(5).replace().over(100))
    # Check after movement (200ms total)
    cron.after("250ms", check_movement)


def test_behavior_replace_speed_offset_by_over_revert(on_success, on_failure):
    """Test: replace with speed.offset.by().over().revert()"""
    start_x, start_y = ctrl.mouse_pos()

    def check_revert():
        x, y = ctrl.mouse_pos()
        # After revert, speed should be 0, so minimal/no movement after this point
        pos_at_revert = x

        def check_stopped():
            x2, y2 = ctrl.mouse_pos()
            # Should have stopped (no significant movement after revert)
            if abs(x2 - pos_at_revert) > 5:
                on_failure(f"Speed not reverted: moved {abs(x2 - pos_at_revert)} pixels after revert")
                return
            on_success()

        cron.after("100ms", check_stopped)

    rig = actions.user.mouse_rig()
    # Implicit layer "speed.offset"
    rig.speed.offset.by(10).over(100)
    cron.after("50ms", lambda: rig.speed.offset.by(5).replace().over(100).revert(100))
    cron.after("300ms", check_revert)


def test_behavior_replace_direction_by_over_revert(on_success, on_failure):
    """Test: replace with direction.offset.by().over().revert()"""
    start_x, start_y = ctrl.mouse_pos()

    def check_direction():
        x, y = ctrl.mouse_pos()
        # After rotation, should have moved both right and down
        if x <= start_x or y <= start_y:
            on_failure(f"Direction change not detected: start=({start_x}, {start_y}), current=({x}, {y})")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Start with rightward movement (implicit layer "speed.override")
    rig.speed.override.to(10)
    # Rotate direction (implicit layer "direction.offset")
    rig.direction.offset.by(45).over(100)
    # Replace with different rotation
    cron.after("50ms", lambda: rig.direction.offset.by(90).replace().over(100).revert(100))
    # Check after animations
    cron.after("300ms", check_direction)


# ============================================================================
# QUEUE BEHAVIOR TESTS
# ============================================================================

def test_behavior_queue_property_syntax(on_success, on_failure):
    """Test: pos.offset.by().queue() - queue executes sequentially"""
    start_x, start_y = ctrl.mouse_pos()
    dx1, dy1 = 100, 0
    dx2, dy2 = 0, 100

    def check_after_first():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx1
        print("Checking after first:", x, y)
        if x != expected_x:
            on_failure(f"After first: expected x={expected_x}, got {x}")
            return

    def check_after_second():
        x, y = ctrl.mouse_pos()
        expected_y = start_y + dy2
        print("Checking after second:", x, y)
        if y != expected_y:
            on_failure(f"After second: expected y={expected_y}, got {y}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Implicit layer "pos.offset"
    rig.pos.offset.by(dx1, dy1).queue().api("talon").over(300).then(check_after_first)
    rig.pos.offset.by(dx2, dy2).queue().api("talon").over(300).then(check_after_second)


def test_behavior_queue_call_syntax_with_max(on_success, on_failure):
    """Test: pos.offset.by().queue(max=2) - queue with max limit"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 50

    def check_result():
        x, y = ctrl.mouse_pos()
        # With max=2, should only execute 2 items (100px total), not 3 (150px)
        expected_x = start_x + (dx * 2)
        if abs(x - expected_x) > 2:
            on_failure(f"Queue max failed: expected x={expected_x}, got {x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Queue 3 items but max is 2 (implicit layer "pos.offset")
    rig.pos.offset.by(dx, 0).queue(max=2).api("talon").over(100)
    rig.pos.offset.by(dx, 0).queue(max=2).api("talon").over(100)
    rig.pos.offset.by(dx, 0).queue(max=2).api("talon").over(100)
    rig.pos.offset.by(dx, 0).queue(max=2).api("talon").over(100)
    cron.after("400ms", check_result)


# ============================================================================
# THROTTLE BEHAVIOR TESTS
# ============================================================================

def test_behavior_throttle_property_syntax(on_success, on_failure):
    """Test: pos.offset.by().throttle() - throttle ignores while layer active"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 100

    first_completed = {"value": False}
    second_completed = {"value": False}

    def first_done():
        first_completed["value"] = True

    def second_done():
        second_completed["value"] = True

    def check_throttle():
        # First should complete, second should have been ignored (throttled)
        if not first_completed["value"]:
            on_failure(f"Throttle: first builder didn't complete")
            return
        if second_completed["value"]:
            on_failure(f"Throttle: second builder should have been ignored but it executed")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Start a long-running builder with throttle (implicit layer "pos.offset")
    rig.pos.offset.by(dx, 0).throttle().api("talon").over(300).then(first_done)
    # Try to add another immediately - should be ignored because first is still active
    cron.after("50ms", lambda: rig.pos.offset.by(dx * 2, 0).throttle().api("talon").over(100).then(second_done))
    # Check after both would have completed
    cron.after("500ms", check_throttle)


def test_behavior_throttle_call_syntax_with_ms(on_success, on_failure):
    """Test: pos.offset.by().throttle(500) - throttle with custom ms"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 50

    call_count = {"value": 0}

    def increment_count():
        call_count["value"] += 1

    def check_throttle():
        # With 500ms throttle and 200ms interval, should execute ~2 times
        if call_count["value"] > 3:
            on_failure(f"Throttle 500ms failed: executed {call_count['value']} times, expected <= 3")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Fire every 200ms for 1 second (implicit layer "pos.offset")
    rig.pos.offset.by(dx, 0).throttle(500).api("talon").over(100).then(increment_count)
    cron.after("200ms", lambda: rig.pos.offset.by(dx, 0).throttle(500).api("talon").over(100).then(increment_count))
    cron.after("400ms", lambda: rig.pos.offset.by(dx, 0).throttle(500).api("talon").over(100).then(increment_count))
    cron.after("600ms", lambda: rig.pos.offset.by(dx, 0).throttle(500).api("talon").over(100).then(increment_count))
    cron.after("800ms", lambda: rig.pos.offset.by(dx, 0).throttle(500).api("talon").over(100).then(increment_count))

    cron.after("1200ms", check_throttle)


def test_behavior_throttle_base_per_operation(on_success, on_failure):
    """Test: base throttle with different property+operation combinations"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 50

    pos_count = {"value": 0}
    speed_count = {"value": 0}

    def increment_pos():
        pos_count["value"] += 1

    def increment_speed():
        speed_count["value"] += 1

    def check_throttle():
        # pos.by should be throttled (called twice within 500ms)
        # speed.to should execute both (different operation)
        if pos_count["value"] > 1:
            on_failure(f"Base throttle pos.by failed: executed {pos_count['value']} times, expected 1")
            return
        if speed_count["value"] < 2:
            on_failure(f"Base throttle speed.to failed: executed {speed_count['value']} times, expected 2")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # First pos.by - should execute
    rig.pos.by(dx, 0).throttle(500).api("talon").over(100).then(increment_pos)
    # Second pos.by after 200ms - should be throttled
    cron.after("200ms", lambda: rig.pos.by(dx, 0).throttle(500).api("talon").over(100).then(increment_pos))
    # First speed.to after 100ms - should execute (different operation)
    cron.after("100ms", lambda: rig.speed.to(5).throttle(500).over(100).then(increment_speed))
    # Second speed.to after 300ms - should be throttled
    cron.after("300ms", lambda: rig.speed.to(10).throttle(500).over(100).then(increment_speed))
    # Third speed.to after 700ms - should execute (past throttle window)
    cron.after("700ms", lambda: rig.speed.to(0).throttle(500).over(100).then(increment_speed))

    cron.after("1000ms", check_throttle)


# ============================================================================
# DEBOUNCE BEHAVIOR TESTS
# ============================================================================

def test_behavior_debounce_basic(on_success, on_failure):
    """Test: basic debounce delays execution"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 100

    executed = {"value": False}

    def mark_executed():
        executed["value"] = True

    def check_not_executed_yet():
        if executed["value"]:
            on_failure("Debounce: executed too early (should wait 200ms)")
            return

    def check_executed():
        if not executed["value"]:
            on_failure("Debounce: didn't execute after delay")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, 0).debounce(200).api("talon").over(100).then(mark_executed)

    # Check it hasn't executed yet at 100ms
    cron.after("100ms", check_not_executed_yet)
    # Check it has executed at 400ms (200ms debounce + 100ms over)
    cron.after("400ms", check_executed)


def test_behavior_debounce_cancels_previous(on_success, on_failure):
    """Test: calling debounce again cancels previous pending"""
    start_x, start_y = ctrl.mouse_pos()
    dx1 = 100
    dx2 = 50

    first_executed = {"value": False}
    second_executed = {"value": False}

    def mark_first():
        first_executed["value"] = True

    def mark_second():
        second_executed["value"] = True

    def check_results():
        if first_executed["value"]:
            on_failure("Debounce cancel: first should have been cancelled")
            return
        if not second_executed["value"]:
            on_failure("Debounce cancel: second should have executed")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # First call with 200ms debounce
    rig.pos.by(dx1, 0).debounce(200).api("talon").over(100).then(mark_first)
    # Second call after 100ms should cancel first and restart debounce
    cron.after("100ms", lambda: rig.pos.by(dx2, 0).debounce(200).api("talon").over(100).then(mark_second))

    # Check results at 500ms (first would be done, second should be executing)
    cron.after("500ms", check_results)


def test_behavior_debounce_layer(on_success, on_failure):
    """Test: debounce works with implicit layers"""
    start_x, start_y = ctrl.mouse_pos()

    executed = {"value": False}

    def mark_executed():
        executed["value"] = True

    def check_executed():
        if not executed["value"]:
            on_failure("Layer debounce: didn't execute")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Implicit layer "speed.offset"
    rig.speed.offset.by(10).debounce(150).over(100).then(mark_executed)

    cron.after("400ms", check_executed)


# ============================================================================
# RATE-BASED BUILDER REUSE TESTS
# ============================================================================

def test_rate_reuse_same_target_ignored(on_success, on_failure):
    """Test: rate-based calls to same target are ignored if in progress"""
    start_x, start_y = ctrl.mouse_pos()

    call_count = {"value": 0}

    def increment():
        call_count["value"] += 1

    def check_single_execution():
        # Only first call should execute
        if call_count["value"] != 1:
            on_failure(f"Rate reuse: expected 1 execution, got {call_count['value']}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.speed.to(10).over(rate=10).then(increment)
    # Call again immediately - should be ignored (same target in progress)
    cron.after("50ms", lambda: rig.speed.to(10).over(rate=10).then(increment))
    cron.after("100ms", lambda: rig.speed.to(10).over(rate=10).then(increment))

    cron.after("1500ms", check_single_execution)


def test_rate_reuse_different_target_replaces(on_success, on_failure):
    """Test: rate-based calls to different target replace existing"""
    start_x, start_y = ctrl.mouse_pos()

    first_completed = {"value": False}
    second_completed = {"value": False}

    def mark_first():
        first_completed["value"] = True

    def mark_second():
        second_completed["value"] = True

    def check_replacement():
        # First should be cancelled (not completed)
        if first_completed["value"]:
            on_failure("Rate replace: first should have been cancelled")
            return
        # Second should complete
        if not second_completed["value"]:
            on_failure("Rate replace: second should have completed")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Start going to speed 10 (takes ~1 second at rate=10)
    rig.speed.to(10).over(rate=10).then(mark_first)
    # After 200ms, change target to 0 - should replace
    cron.after("200ms", lambda: rig.speed.to(0).over(rate=10).then(mark_second))

    # Check at 600ms - first cancelled, second should be done
    cron.after("600ms", check_replacement)


def test_rate_reuse_different_property_independent(on_success, on_failure):
    """Test: rate-based caching is per property+operation"""
    start_x, start_y = ctrl.mouse_pos()

    speed_count = {"value": 0}
    direction_count = {"value": 0}

    def increment_speed():
        speed_count["value"] += 1

    def increment_direction():
        direction_count["value"] += 1

    def check_independent():
        # Both should execute (different properties)
        if speed_count["value"] != 1:
            on_failure(f"Rate independent: speed executed {speed_count['value']} times, expected 1")
            return
        if direction_count["value"] != 1:
            on_failure(f"Rate independent: direction executed {direction_count['value']} times, expected 1")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Set direction first
    rig.direction.to(1, 0)
    # Both should execute independently
    rig.speed.to(10).over(rate=10).then(increment_speed)
    rig.direction.by(90).over(rate=45).then(increment_direction)

    cron.after("300ms", check_independent)


# ============================================================================
# QUEUE BASE OPERATION TESTS
# ============================================================================

def test_queue_base_operations(on_success, on_failure):
    """Test: queue works with base operations (no layer)"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 50

    first_done = {"value": False}
    second_done = {"value": False}

    def mark_first():
        first_done["value"] = True

    def mark_second():
        second_done["value"] = True

    def check_queue():
        x, y = ctrl.mouse_pos()
        # Both should have executed sequentially
        if not first_done["value"] or not second_done["value"]:
            on_failure(f"Base queue: first={first_done['value']}, second={second_done['value']}, expected both true")
            return
        # Total movement should be dx * 2
        expected_x = start_x + (dx * 2)
        if abs(x - expected_x) > 5:
            on_failure(f"Base queue position: expected x={expected_x}, got {x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.pos.by(dx, 0).queue().api("talon").over(200).then(mark_first)
    rig.pos.by(dx, 0).queue().api("talon").over(200).then(mark_second)

    cron.after("600ms", check_queue)


def test_queue_base_independent_properties(on_success, on_failure):
    """Test: queue on base is independent per property+operation"""
    start_x, start_y = ctrl.mouse_pos()

    pos_count = {"value": 0}
    speed_count = {"value": 0}

    def increment_pos():
        pos_count["value"] += 1

    def increment_speed():
        speed_count["value"] += 1

    def check_independent():
        # Both queues should have executed both items
        if pos_count["value"] != 2:
            on_failure(f"Base queue independent: pos executed {pos_count['value']}, expected 2")
            return
        if speed_count["value"] != 2:
            on_failure(f"Base queue independent: speed executed {speed_count['value']}, expected 2")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Queue two pos.by operations
    rig.pos.by(30, 0).queue().api("talon").over(100).then(increment_pos)
    rig.pos.by(30, 0).queue().api("talon").over(100).then(increment_pos)
    # Queue two speed.to operations (different property - independent queue)
    rig.speed.to(5).queue().over(100).then(increment_speed)
    rig.speed.to(0).queue().over(100).then(increment_speed)

    cron.after("600ms", check_independent)


# ============================================================================
# TEST REGISTRY
# ============================================================================

BEHAVIOR_TESTS = [
    ("pos.offset.by().stack()", test_behavior_stack_property_syntax),
    ("pos.offset.by().stack(max)", test_behavior_stack_call_syntax_with_max),
    ("pos.offset.by().replace()", test_behavior_replace_property_syntax),
    ("pos.offset.by().replace() call", test_behavior_replace_call_syntax),
    ("pos.offset.by().over().revert()", test_behavior_pos_offset_by_over_revert),
    ("pos.offset.by().replace().revert()", test_behavior_replace_pos_offset_by_over_revert),
    ("pos.override.to().replace()", test_behavior_replace_pos_override_to_over),
    ("speed.override.to().replace()", test_behavior_replace_speed_override_to_over),
    ("speed.offset.by().replace().revert()", test_behavior_replace_speed_offset_by_over_revert),
    ("direction.offset.by().replace().revert()", test_behavior_replace_direction_by_over_revert),
    ("pos.offset.by().queue()", test_behavior_queue_property_syntax),
    ("pos.offset.by().queue(max)", test_behavior_queue_call_syntax_with_max),
    ("pos.offset.by().throttle()", test_behavior_throttle_property_syntax),
    ("pos.offset.by().throttle(ms)", test_behavior_throttle_call_syntax_with_ms),
    ("base throttle per property+operation", test_behavior_throttle_base_per_operation),
    ("debounce basic delay", test_behavior_debounce_basic),
    ("debounce cancels previous", test_behavior_debounce_cancels_previous),
    ("implicit layer debounce", test_behavior_debounce_layer),
    ("rate reuse same target ignored", test_rate_reuse_same_target_ignored),
    ("rate reuse different target replaces", test_rate_reuse_different_target_replaces),
    ("rate reuse different property independent", test_rate_reuse_different_property_independent),
    ("queue base operations", test_queue_base_operations),
    ("queue base independent properties", test_queue_base_independent_properties),
]
