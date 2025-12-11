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
    rig.layer("test").stack.pos.offset.by(dx1, dy1).over(1000)
    # Second offset: right, longer transition, starts while first is active
    cron.after("500ms", lambda: rig.layer("test").stack.pos.offset.by(dx2, dy2).over(1500))
    # Check after second completes (first will have finished already)
    cron.after("2100ms", check_stacked)


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
# RESET BEHAVIOR TESTS
# ============================================================================

def test_behavior_reset_property_syntax(on_success, on_failure):
    """Test: layer().reset.pos.offset.by() - reset replaces previous offset"""
    start_x, start_y = ctrl.mouse_pos()
    dx1, dy1 = 100, 0
    dx2, dy2 = 50, 0

    def check_first():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx1
        if abs(x - expected_x) > 2 or abs(y - start_y) > 2:
            on_failure(f"First offset wrong: expected ({expected_x}, {start_y}), got ({x}, {y})")
            return

    def check_reset():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx2  # Should be dx2 only, not dx1+dx2
        if abs(x - expected_x) > 2 or abs(y - start_y) > 2:
            on_failure(f"Reset offset wrong: expected ({expected_x}, {start_y}), got ({x}, {y})")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.offset.by(dx1, dy1).over(300).then(check_first)
    cron.after("100ms", lambda: rig.layer("test").reset.pos.offset.by(dx2, dy2).over(300).then(check_reset))


def test_behavior_reset_call_syntax(on_success, on_failure):
    """Test: layer().reset().pos.offset.by() - reset using call syntax"""
    start_x, start_y = ctrl.mouse_pos()
    dx1 = 100
    dx2 = 50

    def check_reset():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx2
        if abs(x - expected_x) > 2:
            on_failure(f"Reset failed: expected x={expected_x}, got {x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    rig.layer("test").pos.offset.by(dx1, 0).over(300)
    cron.after("100ms", lambda: rig.layer("test").reset().pos.offset.by(dx2, 0).over(300).then(check_reset))


# ============================================================================
# QUEUE BEHAVIOR TESTS
# ============================================================================

def test_behavior_queue_property_syntax(on_success, on_failure):
    """Test: layer().queue.pos.offset.by() - queue executes sequentially"""
    start_x, start_y = ctrl.mouse_pos()
    dx1, dy1 = 100, 0
    dx2, dy2 = 50, 0

    def check_after_first():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx1
        if abs(x - expected_x) > 2:
            on_failure(f"After first: expected x={expected_x}, got {x}")
            return

    def check_after_second():
        x, y = ctrl.mouse_pos()
        expected_x = start_x + dx1 + dx2
        if abs(x - expected_x) > 2:
            on_failure(f"After second: expected x={expected_x}, got {x}")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Queue both immediately - second should wait for first to complete
    rig.layer("test").queue.pos.offset.by(dx1, dy1).over(300)
    rig.layer("test").queue.pos.offset.by(dx2, dy2).over(300)
    
    cron.after("350ms", check_after_first)
    cron.after("650ms", check_after_second)


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
    """Test: layer().throttle.pos.offset.by() - throttle limits execution rate"""
    start_x, start_y = ctrl.mouse_pos()
    dx = 100

    call_count = {"value": 0}

    def increment_count():
        call_count["value"] += 1

    def check_throttle():
        # Should have only executed once or twice due to default throttle
        if call_count["value"] > 2:
            on_failure(f"Throttle failed: executed {call_count['value']} times, expected <= 2")
            return
        on_success()

    rig = actions.user.mouse_rig()
    # Rapid fire - should be throttled
    for i in range(5):
        rig.layer("test").throttle.pos.offset.by(dx, 0).over(100).then(increment_count)
        actions.sleep("50ms")
    
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
    for i in range(5):
        rig.layer("test").throttle(500).pos.offset.by(dx, 0).over(100).then(increment_count)
        actions.sleep("200ms")
    
    cron.after("1200ms", check_throttle)


# ============================================================================
# TEST REGISTRY
# ============================================================================

BEHAVIOR_TESTS = [
    ("behavior stack property syntax", test_behavior_stack_property_syntax),
    ("behavior stack(max=2)", test_behavior_stack_call_syntax_with_max),
    ("behavior reset property syntax", test_behavior_reset_property_syntax),
    ("behavior reset()", test_behavior_reset_call_syntax),
    ("behavior queue property syntax", test_behavior_queue_property_syntax),
    ("behavior queue(max=2)", test_behavior_queue_call_syntax_with_max),
    ("behavior extend property syntax", test_behavior_extend_property_syntax),
    ("behavior extend()", test_behavior_extend_call_syntax),
    ("behavior throttle property syntax", test_behavior_throttle_property_syntax),
    ("behavior throttle(500)", test_behavior_throttle_call_syntax_with_ms),
]
