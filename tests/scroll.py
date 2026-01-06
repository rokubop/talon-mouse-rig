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

    base_speed = 0.5
    offset = 0.3
    expected_speed = base_speed + offset

    rig.scroll.direction.to(0, 1)
    rig.scroll.speed.to(base_speed)

    def add_offset():
        rig.scroll.speed.offset.add(offset)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        print(f"DEBUG: scroll_speed={rig_check.state.scroll_speed}, expected={expected_speed}")
        print(f"DEBUG: layers={rig_check.state.layers}")
        print(f"DEBUG: layer_groups={list(rig_check.state._layer_groups.keys())}")

        # Check if any offset layer exists
        for layer_name in rig_check.state._layer_groups.keys():
            if "offset" in layer_name:
                group = rig_check.state._layer_groups[layer_name]
                print(f"DEBUG: Found offset layer: {layer_name}")
                print(f"DEBUG:   property={group.property}, mode={group.mode}")
                print(f"DEBUG:   accumulated_value={group.accumulated_value}")
                print(f"DEBUG:   get_current_value()={group.get_current_value()}")
                if group.builders:
                    builder = group.builders[0]
                    print(f"DEBUG:   input_type={getattr(builder.config, 'input_type', 'move')}")
                else:
                    print(f"DEBUG:   No active builders (completed instantly)")

        if abs(rig_check.state.scroll_speed - expected_speed) > 0.1:
            on_failure(f"Scroll speed with offset wrong: expected {expected_speed}, got {rig_check.state.scroll_speed}")
            return
        if "scroll:speed.offset" not in rig_check.state.layers:
            on_failure(f"Expected scroll:speed.offset layer, got: {rig_check.state.layers}")
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
        if "scroll:speed.offset" in rig_check.state.layers:
            on_failure(f"scroll:speed.offset layer should be gone, got: {rig_check.state.layers}")
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


def test_scroll_emit(on_success, on_failure):
    """Test: rig.scroll.speed.offset.emit() - emit layer for scroll converts to decaying offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    base_speed = 0.5
    emit_offset = 0.3

    rig.scroll.direction.to(0, 1)
    rig.scroll.speed.to(base_speed)

    def add_offset():
        rig.scroll.speed.offset.add(emit_offset).emit(300)

    def check_after_emit():
        rig_mid = actions.user.mouse_rig()
        # Offset layer should be gone, replaced by emit layer
        if "scroll:speed.offset" in rig_mid.state.layers:
            on_failure(f"Offset layer still exists after emit: {rig_mid.state.layers}")
            return
        # Should still have elevated speed (from emitted offset)
        if rig_mid.state.scroll_speed < base_speed + 0.2:
            on_failure(f"Speed after emit too low: got {rig_mid.state.scroll_speed}")
            return
        # Check that an emit layer exists
        has_emit_layer = any("emit" in layer for layer in rig_mid.state.layers)
        if not has_emit_layer:
            on_failure(f"Expected emit layer, got: {rig_mid.state.layers}")
            return

    def check_after_fade():
        rig_final = actions.user.mouse_rig()
        # Should be back to base speed after decay
        if abs(rig_final.state.scroll_speed - base_speed) > 0.1:
            on_failure(f"Speed after fade wrong: expected {base_speed}, got {rig_final.state.scroll_speed}")
            return
        # Emit layer should be gone
        has_emit_layer = any("emit" in layer for layer in rig_final.state.layers)
        if has_emit_layer:
            on_failure(f"Emit layer should be gone after fade, got: {rig_final.state.layers}")
            return

        rig_final.stop()
        on_success()

    cron.after("100ms", add_offset)
    cron.after("200ms", check_after_emit)
    cron.after("500ms", check_after_fade)


def test_scroll_speed_offset_add_revert(on_success, on_failure):
    """Test: scroll.speed.offset.add().over().revert() - offset with revert"""
    rig = actions.user.mouse_rig()
    rig.stop()

    base_speed = 0.5
    offset = 3

    rig.scroll.direction.to(0, 1)
    rig.scroll.speed.to(base_speed)

    def start_offset():
        rig.scroll.speed.offset.add(offset).over(1000).revert(1000)

    def check_initial():
        rig_check = actions.user.mouse_rig()
        # Should have offset layer active
        if "scroll:speed.offset" not in rig_check.state.layers:
            on_failure(f"Expected scroll:speed.offset layer, got: {rig_check.state.layers}")
            return
        # Should be ramping up
        if rig_check.state.scroll_speed <= base_speed:
            on_failure(f"Speed should be increasing, got {rig_check.state.scroll_speed}")
            return

    def check_peak():
        rig_mid = actions.user.mouse_rig()
        expected_peak = base_speed + offset
        # Should still have offset layer
        if "scroll:speed.offset" not in rig_mid.state.layers:
            on_failure(f"Expected scroll:speed.offset layer at peak, got: {rig_mid.state.layers}")
            return
        if abs(rig_mid.state.scroll_speed - expected_peak) > 0.2:
            on_failure(f"Peak scroll speed wrong: expected {expected_peak}, got {rig_mid.state.scroll_speed}")
            return

    def check_reverting():
        rig_rev = actions.user.mouse_rig()
        expected_peak = base_speed + offset
        # Should still have offset layer during revert
        if "scroll:speed.offset" not in rig_rev.state.layers:
            on_failure(f"Expected scroll:speed.offset layer during revert, got: {rig_rev.state.layers}")
            return
        # Should be between base and peak
        if not (base_speed < rig_rev.state.scroll_speed < expected_peak):
            on_failure(f"Speed during revert should be between {base_speed} and {expected_peak}, got {rig_rev.state.scroll_speed}")
            return

    def check_reverted():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.scroll_speed - base_speed) > 0.1:
            on_failure(f"Reverted scroll speed wrong: expected {base_speed}, got {rig_check.state.scroll_speed}")
            return
        # Offset layer should be gone after revert completes
        if "scroll:speed.offset" in rig_check.state.layers:
            on_failure(f"scroll:speed.offset layer should be gone after revert, got: {rig_check.state.layers}")
            return

        rig_check.stop()
        on_success()

    cron.after("100ms", start_offset)
    cron.after("300ms", check_initial)
    cron.after("1100ms", check_peak)
    cron.after("1600ms", check_reverting)
    cron.after("2200ms", check_reverted)


# ============================================================================
# SCROLL API TESTS (one-time scroll amounts)
# ============================================================================

def test_scroll_to_amount(on_success, on_failure):
    """Test: rig.scroll.to(x, y) - one-time scroll amount (like pos for movement)"""
    rig = actions.user.mouse_rig()
    rig.stop()

    target = (50, 100)
    rig.scroll.to(*target)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        scroll = rig_check.state.scroll
        if abs(scroll.x - target[0]) > 0.1 or abs(scroll.y - target[1]) > 0.1:
            on_failure(f"Scroll amount wrong: expected {target}, got ({scroll.x}, {scroll.y})")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", check_scroll)


def test_scroll_pos_alias(on_success, on_failure):
    """Test: rig.scroll.pos.to() - alias for scroll.to()"""
    rig = actions.user.mouse_rig()
    rig.stop()

    target = (75, 25)
    rig.scroll.pos.to(*target)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        scroll_pos = rig_check.state.scroll.pos
        if abs(scroll_pos.current.x - target[0]) > 0.1 or abs(scroll_pos.current.y - target[1]) > 0.1:
            on_failure(f"Scroll pos wrong: expected {target}, got ({scroll_pos.current.x}, {scroll_pos.current.y})")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", check_scroll)


def test_scroll_by_amount(on_success, on_failure):
    """Test: rig.scroll.by(x, y) - scroll by delta amount"""
    rig = actions.user.mouse_rig()
    rig.stop()

    initial = (10, 10)
    delta = (20, 30)
    expected = (initial[0] + delta[0], initial[1] + delta[1])

    rig.scroll.to(*initial)

    def add_delta():
        rig.scroll.by(*delta)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        scroll = rig_check.state.scroll
        if abs(scroll.x - expected[0]) > 0.1 or abs(scroll.y - expected[1]) > 0.1:
            on_failure(f"Scroll by wrong: expected {expected}, got ({scroll.x}, {scroll.y})")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", add_delta)
    cron.after("200ms", check_scroll)


def test_scroll_over_time(on_success, on_failure):
    """Test: rig.scroll.to().over() - animated scroll amount"""
    rig = actions.user.mouse_rig()
    rig.stop()

    start = (0, 0)
    target = (100, 50)
    duration_ms = 1000

    rig.scroll.to(*start)

    def start_animation():
        rig.scroll.to(*target).over(duration_ms)

    def check_midpoint():
        rig_mid = actions.user.mouse_rig()
        scroll = rig_mid.state.scroll
        # Should be somewhere between start and target
        if not (10 < scroll.x < 90):
            on_failure(f"Midpoint scroll.x should be between 10 and 90, got {scroll.x}")
            return

    def check_final():
        rig_check = actions.user.mouse_rig()
        scroll = rig_check.state.scroll
        if abs(scroll.x - target[0]) > 1 or abs(scroll.y - target[1]) > 1:
            on_failure(f"Final scroll wrong: expected {target}, got ({scroll.x}, {scroll.y})")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", start_animation)
    cron.after("600ms", check_midpoint)
    cron.after("1200ms", check_final)


def test_scroll_state_properties(on_success, on_failure):
    """Test: scroll state property access - .current, .target, .x, .y"""
    rig = actions.user.mouse_rig()
    rig.stop()

    target = (80, 60)
    rig.scroll.to(*target).over(500)

    def check_properties():
        rig_check = actions.user.mouse_rig()
        scroll = rig_check.state.scroll

        # Check .current property
        if not hasattr(scroll, 'current'):
            on_failure("scroll should have .current property")
            return

        # Check .target property
        if not hasattr(scroll, 'target'):
            on_failure("scroll should have .target property")
            return

        # Check .x and .y shortcuts
        if not hasattr(scroll, 'x') or not hasattr(scroll, 'y'):
            on_failure("scroll should have .x and .y properties")
            return

        # Verify target is set correctly
        if scroll.target is None:
            on_failure("scroll.target should not be None during animation")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", check_properties)


def test_scroll_offset_mode(on_success, on_failure):
    """Test: rig.scroll.offset.to() - scroll offset layer"""
    rig = actions.user.mouse_rig()
    rig.stop()

    base = (10, 10)
    offset = (5, 15)
    expected = (base[0] + offset[0], base[1] + offset[1])

    rig.scroll.to(*base)

    def add_offset():
        rig.scroll.offset.to(*offset)

    def check_scroll():
        rig_check = actions.user.mouse_rig()
        scroll = rig_check.state.scroll
        if abs(scroll.x - expected[0]) > 0.1 or abs(scroll.y - expected[1]) > 0.1:
            on_failure(f"Scroll with offset wrong: expected {expected}, got ({scroll.x}, {scroll.y})")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", add_offset)
    cron.after("200ms", check_scroll)


def test_scroll_nested_properties(on_success, on_failure):
    """Test: scroll nested properties - speed, direction, vector access"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.to(10)
    rig.scroll.direction.to(1, 0)

    def check_properties():
        rig_check = actions.user.mouse_rig()
        scroll = rig_check.state.scroll

        # Check nested properties exist
        if not hasattr(scroll, 'speed'):
            on_failure("scroll should have .speed property")
            return
        if not hasattr(scroll, 'direction'):
            on_failure("scroll should have .direction property")
            return
        if not hasattr(scroll, 'vector'):
            on_failure("scroll should have .vector property")
            return

        # Check speed value
        speed = scroll.speed
        if abs(speed.current - 10) > 0.1:
            on_failure(f"scroll.speed.current should be 10, got {speed.current}")
            return

        # Check direction value
        direction = scroll.direction
        if abs(direction.current.x - 1) > 0.1 or abs(direction.current.y) > 0.1:
            on_failure(f"scroll.direction.current should be (1, 0), got ({direction.current.x}, {direction.current.y})")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", check_properties)


def test_scroll_base_state(on_success, on_failure):
    """Test: rig.state.base.scroll - base scroll state access"""
    rig = actions.user.mouse_rig()
    rig.stop()

    base_amount = (30, 40)
    rig.scroll.to(*base_amount)

    def check_base():
        rig_check = actions.user.mouse_rig()
        base_scroll = rig_check.state.base.scroll

        if not hasattr(base_scroll, 'current'):
            on_failure("base.scroll should have .current property")
            return

        if not hasattr(base_scroll, 'speed'):
            on_failure("base.scroll should have .speed property")
            return

        if not hasattr(base_scroll, 'direction'):
            on_failure("base.scroll should have .direction property")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("100ms", check_base)


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
    ("scroll.emit()", test_scroll_emit),
    ("scroll.speed.offset.add().revert()", test_scroll_speed_offset_add_revert),
    ("scroll.to() - one-time amount", test_scroll_to_amount),
    ("scroll.pos.to() - alias", test_scroll_pos_alias),
    ("scroll.by() - delta", test_scroll_by_amount),
    ("scroll.to().over() - animated", test_scroll_over_time),
    ("scroll state properties", test_scroll_state_properties),
    ("scroll.offset.to()", test_scroll_offset_mode),
    ("scroll nested properties", test_scroll_nested_properties),
    ("scroll base state", test_scroll_base_state),
]
