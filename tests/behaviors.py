from talon import actions, ctrl, cron

CENTER_X = 960
CENTER_Y = 540
TEST_OFFSET = 200


# ============================================================================
# STACK BEHAVIOR TESTS
# ============================================================================

def test_behavior_stack_property_syntax(on_success, on_failure):
    """Test: layer().stack.pos.offset.by() - stack behavior using property syntax"""
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
    # First offset: down, shorter transition
    rig.layer("test").stack.pos.offset.by(dx1, dy1).over(400)
    # Second offset: right, longer transition, starts while first is active
    cron.after("200ms", lambda: rig.layer("test").stack.pos.offset.by(dx2, dy2).over(400))
    # Check after second completes (first will have finished already)
    cron.after("1000ms", check_stacked)


def test_behavior_stack_call_syntax_with_max(on_success, on_failure):
    """Test: layer().stack(max=2).pos.offset.by() - stack with max count"""
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
    # Add 3 stacks but max is 2
    rig.layer("test").stack(max=2).pos.offset.by(dx, 0).over(100)
    cron.after("50ms", lambda: rig.layer("test").stack(max=2).pos.offset.by(dx, 0).over(100))
    cron.after("100ms", lambda: rig.layer("test").stack(max=2).pos.offset.by(dx, 0).over(100))
    cron.after("400ms", check_result)


# ============================================================================
# REPLACE BEHAVIOR TESTS
# ============================================================================

def test_behavior_replace_property_syntax(on_success, on_failure):
    """Test: layer().replace.pos.offset.by() - replace old offset with new"""
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
    rig.layer("test").pos.offset.by(dx1, dy1).over(300).then(check_first)
    cron.after("100ms", lambda: rig.layer("test").replace.pos.offset.by(dx2, dy2).over(300).then(check_replace))


def test_behavior_replace_call_syntax(on_success, on_failure):
    """Test: layer().replace().pos.offset.by() - replace using call syntax"""
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
    rig.layer("test").pos.offset.by(dx1, 0).over(300)
    cron.after("100ms", lambda: rig.layer("test").replace().pos.offset.by(dx2, 0).over(300).then(check_replace))


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
    rig.layer("test").pos.offset.by(dx, 0).over(300).revert(300).then(check_pos)


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
    # Start first animation
    rig.layer("test").pos.offset.by(dx1, 0).over(300).revert(300)
    # Replace it mid-flight with a different offset
    cron.after("100ms", lambda: rig.layer("test").replace().pos.offset.by(dx2, 0).over(300).revert(300).then(check_pos))


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
    rig.layer("test").pos.override.to(target1_x, target1_y).over(300)
    cron.after("100ms", lambda: rig.layer("test").replace().pos.override.to(target2_x, target2_y).over(300).then(check_replace))


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
    # Start with speed 10
    rig.layer("test").speed.override.to(10).over(100)
    # Replace with speed 5 after 50ms
    cron.after("50ms", lambda: rig.layer("test").replace().speed.override.to(5).over(100))
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
    rig.layer("test").speed.offset.by(10).over(100)
    cron.after("50ms", lambda: rig.layer("test").replace().speed.offset.by(5).over(100).revert(100))
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
    # Start with rightward movement
    rig.layer("test").speed.override.to(10)
    rig.layer("test2").direction.offset.by(45).over(100)
    # Replace with different rotation
    cron.after("50ms", lambda: rig.layer("test2").replace().direction.offset.by(90).over(100).revert(100))
    # Check after animations
    cron.after("300ms", check_direction)


# ============================================================================
# QUEUE BEHAVIOR TESTS
# ============================================================================

def test_behavior_queue_property_syntax(on_success, on_failure):
    """Test: layer().queue.pos.offset.by() - queue executes sequentially"""
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
    rig.layer("test").queue.pos.offset.by(dx1, dy1).over(300).then(check_after_first)
    rig.layer("test").queue.pos.offset.by(dx2, dy2).over(300).then(check_after_second)


def test_behavior_queue_call_syntax_with_max(on_success, on_failure):
    """Test: layer().queue(max=2).pos.offset.by() - queue with max limit"""
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
    # Queue 3 items but max is 2
    rig.layer("test").queue(max=2).pos.offset.by(dx, 0).over(100)
    rig.layer("test").queue(max=2).pos.offset.by(dx, 0).over(100)
    rig.layer("test").queue(max=2).pos.offset.by(dx, 0).over(100)
    rig.layer("test").queue(max=2).pos.offset.by(dx, 0).over(100)
    cron.after("400ms", check_result)


# ============================================================================
# EXTEND BEHAVIOR TESTS
# ============================================================================

def test_behavior_extend_property_syntax(on_success, on_failure):
    """Test: layer().extend.pos.offset.by() - extend continues from current state"""
    start_x, start_y = ctrl.mouse_pos()
    dx1, dy1 = 100, 0
    dx2, dy2 = 50, 0

    def check_after_extend():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx1 + dx2
        if abs(x - expected_x) > 2:
            on_failure(f"After extend: expected x={expected_x}, got {x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.offset.by(dx1, dy1).over(300)
    cron.after("100ms", lambda: rig.layer("test").extend.pos.offset.by(dx2, dy2).over(300).then(check_after_extend))


def test_behavior_extend_call_syntax(on_success, on_failure):
    """Test: layer().extend().pos.offset.by() - extend using call syntax"""
    start_x, start_y = ctrl.mouse_pos()
    dx1 = 100
    dx2 = 50

    def check_result():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx1 + dx2
        if abs(x - expected_x) > 2:
            on_failure(f"Extend failed: expected x={expected_x}, got {x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.offset.by(dx1, 0).over(300)
    cron.after("100ms", lambda: rig.layer("test").extend().pos.offset.by(dx2, 0).over(300).then(check_result))


# ============================================================================
# THROTTLE BEHAVIOR TESTS
# ============================================================================

def test_behavior_throttle_property_syntax(on_success, on_failure):
    """Test: layer().throttle.pos.offset.by() - throttle ignores while layer active"""
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
    # Start a long-running builder with throttle
    rig.layer("test").throttle.pos.offset.by(dx, 0).over(300).then(first_done)
    # Try to add another immediately - should be ignored because first is still active
    cron.after("50ms", lambda: rig.layer("test").throttle.pos.offset.by(dx * 2, 0).over(100).then(second_done))
    # Check after both would have completed
    cron.after("500ms", check_throttle)


def test_behavior_throttle_call_syntax_with_ms(on_success, on_failure):
    """Test: layer().throttle(500).pos.offset.by() - throttle with custom ms"""
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
    # Fire every 200ms for 1 second
    rig.layer("test").throttle(500).pos.offset.by(dx, 0).over(100).then(increment_count)
    cron.after("200ms", lambda: rig.layer("test").throttle(500).pos.offset.by(dx, 0).over(100).then(increment_count))
    cron.after("400ms", lambda: rig.layer("test").throttle(500).pos.offset.by(dx, 0).over(100).then(increment_count))
    cron.after("600ms", lambda: rig.layer("test").throttle(500).pos.offset.by(dx, 0).over(100).then(increment_count))
    cron.after("800ms", lambda: rig.layer("test").throttle(500).pos.offset.by(dx, 0).over(100).then(increment_count))

    cron.after("1200ms", check_throttle)


# ============================================================================
# TEST REGISTRY
# ============================================================================

BEHAVIOR_TESTS = [
    ("behavior stack property syntax", test_behavior_stack_property_syntax),
    ("behavior stack(max=2)", test_behavior_stack_call_syntax_with_max),
    ("behavior replace property syntax", test_behavior_replace_property_syntax),
    ("behavior replace()", test_behavior_replace_call_syntax),
    ("behavior pos.offset.by().over().revert()", test_behavior_pos_offset_by_over_revert),
    ("behavior replace pos.offset.by().over().revert()", test_behavior_replace_pos_offset_by_over_revert),
    ("behavior replace pos.override.to().over()", test_behavior_replace_pos_override_to_over),
    ("behavior replace speed.override.to().over()", test_behavior_replace_speed_override_to_over),
    ("behavior replace speed.offset.by().over().revert()", test_behavior_replace_speed_offset_by_over_revert),
    ("behavior replace direction.offset.by().over().revert()", test_behavior_replace_direction_by_over_revert),
    ("behavior queue property syntax", test_behavior_queue_property_syntax),
    ("behavior queue(max=2)", test_behavior_queue_call_syntax_with_max),
    ("behavior extend property syntax", test_behavior_extend_property_syntax),
    ("behavior extend()", test_behavior_extend_call_syntax),
    ("behavior throttle property syntax", test_behavior_throttle_property_syntax),
    ("behavior throttle(500)", test_behavior_throttle_call_syntax_with_ms),
]
