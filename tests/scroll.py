from talon import actions, cron

# ============================================================================
# BASIC SCROLL TESTS
# ============================================================================

def test_scroll_speed_to(on_success, on_failure):
    """Test: rig.scroll.speed.to(value) - instant scroll speed change"""
    rig = actions.user.mouse_rig()
    rig.stop()

    target_speed = 0.5
    rig.scroll.direction.to(0, 1)  # Down
    rig.scroll.speed.to(target_speed)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed - target_speed) > 0.1:
            on_failure(f"Scroll speed wrong: expected {target_speed}, got {rig_check.state.scroll_speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("1s", check_scroll)


def test_scroll_direction_to(on_success, on_failure):
    """Test: rig.scroll.direction.to(x, y) - instant and animated direction changes"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.to(0.5)
    rig.scroll.direction.to(0, 1)  # Down

    def check_first_direction():
        rig_check = actions.user.mouse_rig()
        direction = rig_check.state.scroll_direction
        if abs(direction.x) > 0.1 or abs(direction.y - 1) > 0.1:
            on_failure(f"Initial scroll direction wrong: expected (0, 1), got ({direction.x}, {direction.y})")
            return
        # Change direction with animation
        rig.scroll.direction.to(1, 0).over(1000)  # Right, animated

    def check_intermediate_direction():
        rig_mid = actions.user.mouse_rig()
        direction = rig_mid.state.scroll_direction
        # Should be somewhere between (0, 1) and (1, 0)
        if not (0.1 < direction.x < 0.9):
            on_failure(f"Intermediate direction X wrong: expected between 0.1 and 0.9, got {direction.x}")
            return

    def check_final_direction():
        rig_check = actions.user.mouse_rig()
        direction = rig_check.state.scroll_direction
        if abs(direction.x - 1) > 0.1 or abs(direction.y) > 0.1:
            on_failure(f"Final scroll direction wrong: expected (1, 0), got ({direction.x}, {direction.y})")
            return
        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", check_first_direction)
    cron.after("600ms", check_intermediate_direction)
    cron.after("1200ms", check_final_direction)


def test_scroll_vector_to(on_success, on_failure):
    """Test: rig.scroll.vector.to(x, y) - set scroll vector (combines speed and direction)"""
    rig = actions.user.mouse_rig()
    rig.stop()

    target_x = 0
    target_y = 0.5

    rig.scroll.vector.to(target_x, target_y)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        vector = rig_check.state.scroll_vector
        if abs(vector.x - target_x) > 0.1 or abs(vector.y - target_y) > 0.1:
            on_failure(f"Scroll vector wrong: expected ({target_x}, {target_y}), got ({vector.x}, {vector.y})")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", check_scroll)


def test_scroll_speed_over(on_success, on_failure):
    """Test: rig.scroll.speed.to().over() - smooth scroll speed transition"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.direction.to(0, 1)
    rig.scroll.speed.to(0.5).over(1000)

    def check_intermediate():
        rig_mid = actions.user.mouse_rig()
        if rig_mid.state.scroll_speed <= 0 or rig_mid.state.scroll_speed >= 0.5:
            on_failure(f"Intermediate scroll speed wrong: got {rig_mid.state.scroll_speed}")
            return

    def check_final():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed - 0.5) > 0.1:
            on_failure(f"Final scroll speed wrong: expected 0.5, got {rig_check.state.scroll_speed}")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_intermediate)
    cron.after("1200ms", check_final)


def test_scroll_stop(on_success, on_failure):
    """Test: rig.scroll.speed.to().stop() - stop scrolling"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.to(0.5)
    rig.scroll.direction.to(0, 1)

    def stop_scroll():
        rig.stop()

    def check_stopped():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed) > 0.1:
            on_failure(f"Scroll speed should be 0 after stop, got {rig_check.state.scroll_speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no layers after stop, got: {rig_check.state.layers}")
            return
        on_success()

    cron.after("100ms", stop_scroll)
    cron.after("200ms", check_stopped)


def test_scroll_stop_with_transition(on_success, on_failure):
    """Test: rig.stop(ms) - smooth stop for scroll"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.to(0.5)
    rig.scroll.direction.to(0, 1)

    def stop_scroll():
        rig.stop(1000)

    def check_intermediate():
        rig_mid = actions.user.mouse_rig()
        if rig_mid.state.scroll_speed <= 0 or rig_mid.state.scroll_speed >= 0.5:
            on_failure(f"Intermediate scroll speed during stop wrong: got {rig_mid.state.scroll_speed}")
            return

    def check_stopped():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed) > 0.1:
            on_failure(f"Scroll speed should be ~0 after stop transition, got {rig_check.state.scroll_speed}")
            return
        on_success()

    cron.after("100ms", stop_scroll)
    cron.after("600ms", check_intermediate)
    cron.after("1200ms", check_stopped)


# ============================================================================
# SCROLL OFFSET/OVERRIDE TESTS
# ============================================================================

def test_scroll_speed_offset_add(on_success, on_failure):
    """Test: rig.scroll.speed.offset.add() - additive speed offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    base_speed = 5
    offset = 3
    expected_speed = base_speed + offset

    rig.scroll.direction.to(0, 1)
    rig.scroll.speed.to(base_speed)

    def add_offset():
        rig.scroll.speed.offset.add(offset)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed - expected_speed) > 0.1:
            on_failure(f"Scroll speed with offset wrong: expected {expected_speed}, got {rig_check.state.scroll_speed}")
            return
        if "scroll.speed.offset" not in rig_check.state.layers:
            on_failure(f"Expected scroll.speed.offset layer, got: {rig_check.state.layers}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", add_offset)
    cron.after("200ms", check_scroll)


def test_scroll_speed_offset_over(on_success, on_failure):
    """Test: rig.scroll.speed.offset.add().over() - smooth offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    base_speed = 0.5
    offset = 0.5
    expected_speed = base_speed + offset

    rig.scroll.direction.to(0, 1)
    rig.scroll.speed.to(base_speed)

    def add_offset():
        rig.scroll.speed.offset.add(offset).over(1000)

    def check_intermediate():
        rig_mid = actions.user.mouse_rig()
        if rig_mid.state.scroll_speed <= base_speed or rig_mid.state.scroll_speed >= expected_speed:
            on_failure(f"Intermediate scroll speed wrong: expected between {base_speed} and {expected_speed}, got {rig_mid.state.scroll_speed}")
            return

    def check_final():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed - expected_speed) > 0.1:
            on_failure(f"Final scroll speed wrong: expected {expected_speed}, got {rig_check.state.scroll_speed}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", add_offset)
    cron.after("600ms", check_intermediate)
    cron.after("1200ms", check_final)


def test_scroll_speed_offset_revert(on_success, on_failure):
    """Test: rig.scroll.speed.offset.add().revert() - remove offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    base_speed = 0.5
    offset = 0.3

    rig.scroll.direction.to(0, 1)
    rig.scroll.speed.to(base_speed)

    def add_offset():
        rig.scroll.speed.offset.add(offset).hold(200)

    def check_reverted():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed - base_speed) > 0.1:
            on_failure(f"Scroll speed after revert wrong: expected {base_speed}, got {rig_check.state.scroll_speed}")
            return
        if "scroll.speed.offset" in rig_check.state.layers:
            on_failure(f"scroll.speed.offset layer should be gone, got: {rig_check.state.layers}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", add_offset)
    cron.after("400ms", check_reverted)


def test_scroll_layer_offset(on_success, on_failure):
    """Test: rig.layer("boost").scroll.speed.offset.add() - named layer offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    base_speed = 0.5
    offset = 0.3
    expected_speed = base_speed + offset

    rig.scroll.direction.to(0, 1)
    rig.scroll.speed.to(base_speed)

    def add_layer():
        rig.layer("boost").scroll.speed.offset.add(offset)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed - expected_speed) > 0.1:
            on_failure(f"Scroll speed with layer wrong: expected {expected_speed}, got {rig_check.state.scroll_speed}")
            return
        if "boost" not in rig_check.state.layers:
            on_failure(f"Expected boost layer, got: {rig_check.state.layers}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", add_layer)
    cron.after("200ms", check_scroll)


# ============================================================================
# SCROLL DIRECTION TESTS
# ============================================================================

def test_scroll_direction_down(on_success, on_failure):
    """Test: rig.scroll.direction.to(0, 1) - scroll down"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.to(0.5)
    rig.scroll.direction.to(0, 1)  # Down

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        direction = rig_check.state.scroll_direction
        vector = rig_check.state.scroll_vector

        if abs(direction.y - 1) > 0.1:
            on_failure(f"Scroll direction Y should be 1 (down), got {direction.y}")
            return
        if vector.y <= 0:
            on_failure(f"Scroll vector Y should be positive (down), got {vector.y}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", check_scroll)


def test_scroll_direction_up(on_success, on_failure):
    """Test: rig.scroll.direction.to(0, -1) - scroll up"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.to(0.5)
    rig.scroll.direction.to(0, -1)  # Up

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        direction = rig_check.state.scroll_direction
        vector = rig_check.state.scroll_vector

        if abs(direction.y + 1) > 0.1:
            on_failure(f"Scroll direction Y should be -1 (up), got {direction.y}")
            return
        if vector.y >= 0:
            on_failure(f"Scroll vector Y should be negative (up), got {vector.y}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", check_scroll)


def test_scroll_horizontal(on_success, on_failure):
    """Test: rig.scroll.direction.to(1, 0) - horizontal scroll"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.to(0.5)
    rig.scroll.direction.to(1, 0)  # Right

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        direction = rig_check.state.scroll_direction
        vector = rig_check.state.scroll_vector

        if abs(direction.x - 1) > 0.1:
            on_failure(f"Scroll direction X should be 1 (right), got {direction.x}")
            return
        if vector.x <= 0:
            on_failure(f"Scroll vector X should be positive (right), got {vector.x}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", check_scroll)


# Export test list
SCROLL_TESTS = [
    ("scroll.speed.to()", test_scroll_speed_to),
    ("scroll.direction.to()", test_scroll_direction_to),
    ("scroll.vector.to()", test_scroll_vector_to),
    ("scroll.speed.over()", test_scroll_speed_over),
    ("scroll.stop()", test_scroll_stop),
    ("scroll.stop(ms)", test_scroll_stop_with_transition),
    ("scroll.speed.offset.add()", test_scroll_speed_offset_add),
    ("scroll.speed.offset.over()", test_scroll_speed_offset_over),
    ("scroll.speed.offset.revert()", test_scroll_speed_offset_revert),
    ("layer().scroll.speed.offset", test_scroll_layer_offset),
    ("scroll down", test_scroll_direction_down),
    ("scroll up", test_scroll_direction_up),
    ("scroll horizontal", test_scroll_horizontal),
]
