from talon import actions, ctrl, cron

CENTER_X = 960
CENTER_Y = 540

# ============================================================================
# BASIC SPEED TESTS
# ============================================================================

def test_speed_to(on_success, on_failure):
    """Test: rig.speed.to(value) - instant speed change"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    target_speed = 10
    rig.direction.to(1, 0)  # Set direction for movement
    start_pos = ctrl.mouse_pos()
    rig.speed.to(target_speed)

    def check_movement():
        rig_check = actions.user.mouse_rig()
        end_pos = ctrl.mouse_pos()

        if rig_check.state.speed != target_speed:
            on_failure(f"Speed wrong: expected {target_speed}, got {rig_check.state.speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return
        if rig_check._state._frame_loop_job is None:
            on_failure("Frame loop should be running with speed set")
            return

        # Verify actual movement occurred
        distance_moved = end_pos[0] - start_pos[0]
        if distance_moved < 10:  # Should have moved significantly
            on_failure(f"Expected movement, only moved {distance_moved}px")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


def test_speed_to_over(on_success, on_failure):
    """Test: rig.speed.to(value).over(ms) - smooth speed transition"""
    rig = actions.user.mouse_rig()
    rig.stop()
    rig.speed.to(5)

    target_speed = 15

    def check_speed():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.speed - target_speed) > 0.1:
            on_failure(f"Final speed wrong: expected {target_speed}, got {rig_check.state.speed}")
            return
        on_success()

    def check_state():
        rig_check = actions.user.mouse_rig()
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return
        if rig_check._state._frame_loop_job is not None:
            on_failure("Frame loop should be stopped")
            return

    rig.speed.to(target_speed).over(500).then(check_speed)
    cron.after("600ms", check_state)


def test_speed_add(on_success, on_failure):
    """Test: rig.speed.add(delta) - add to current speed"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    initial_speed = 10
    delta = 5
    expected_speed = initial_speed + delta

    rig.direction.to(1, 0)
    rig.speed.to(initial_speed)
    start_pos = ctrl.mouse_pos()
    rig.speed.add(delta)

    def check_movement():
        rig_check = actions.user.mouse_rig()
        end_pos = ctrl.mouse_pos()

        if abs(rig_check.state.speed - expected_speed) > 0.1:
            on_failure(f"Speed wrong: expected {expected_speed}, got {rig_check.state.speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return

        # Verify movement with increased speed
        distance_moved = end_pos[0] - start_pos[0]
        if distance_moved < 10:
            on_failure(f"Expected movement with speed {expected_speed}, only moved {distance_moved}px")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


def test_speed_mul(on_success, on_failure):
    """Test: rig.speed.mul(multiplier) - multiply current speed"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    initial_speed = 8
    multiplier = 2
    expected_speed = initial_speed * multiplier

    rig.direction.to(1, 0)
    rig.speed.to(initial_speed)
    start_pos = ctrl.mouse_pos()
    rig.speed.mul(multiplier)

    def check_movement():
        rig_check = actions.user.mouse_rig()
        end_pos = ctrl.mouse_pos()

        if abs(rig_check.state.speed - expected_speed) > 0.1:
            on_failure(f"Speed wrong: expected {expected_speed}, got {rig_check.state.speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return

        # Verify movement with multiplied speed
        distance_moved = end_pos[0] - start_pos[0]
        if distance_moved < 10:
            on_failure(f"Expected movement with speed {expected_speed}, only moved {distance_moved}px")
            return

        # Clean up
        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


def test_speed_to_negative(on_success, on_failure):
    """Test: rig.speed.to(-5) - negative speed should reverse direction"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    # Start moving right
    rig.direction.to(1, 0)
    rig.speed.to(5)
    actions.sleep("200ms")

    # Set negative speed
    start_pos = ctrl.mouse_pos()
    rig.speed.to(-5)

    def check_movement():
        rig_check = actions.user.mouse_rig()
        end_pos = ctrl.mouse_pos()

        # Speed should be negative
        if abs(rig_check.state.speed - (-5)) > 0.1:
            on_failure(f"Speed wrong: expected -5, got {rig_check.state.speed}")
            return

        # Direction should stay right (1, 0) - negative speed reverses movement
        dir_x, dir_y = rig_check.state.direction.x, rig_check.state.direction.y
        if abs(dir_x - 1.0) > 0.1 or abs(dir_y) > 0.1:
            on_failure(f"Direction wrong: expected (1, 0), got ({dir_x:.2f}, {dir_y:.2f})")
            return

        # Should be moving left (direction × negative speed)
        dx = end_pos[0] - start_pos[0]
        if dx > -10:
            on_failure(f"Expected leftward movement, got dx={dx}")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


def test_speed_add_negative(on_success, on_failure):
    """Test: rig.speed.add(-7) - subtracting speed that goes negative"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    # Start at speed 5 moving right
    rig.direction.to(1, 0)
    rig.speed.to(5)
    actions.sleep("200ms")

    # Add -7, resulting in -2 (should reverse)
    start_pos = ctrl.mouse_pos()
    rig.speed.add(-7)

    def check_movement():
        rig_check = actions.user.mouse_rig()
        end_pos = ctrl.mouse_pos()

        # Speed should be -2 (5 + -7 = -2)
        if abs(rig_check.state.speed - (-2)) > 0.1:
            on_failure(f"Speed wrong: expected -2, got {rig_check.state.speed}")
            return

        # Direction should stay right (1, 0) - negative speed reverses movement
        dir_x, dir_y = rig_check.state.direction.x, rig_check.state.direction.y
        if abs(dir_x - 1.0) > 0.1 or abs(dir_y) > 0.1:
            on_failure(f"Direction wrong: expected (1, 0), got ({dir_x:.2f}, {dir_y:.2f})")
            return

        # Should be moving left (direction × negative speed)
        dx = end_pos[0] - start_pos[0]
        if dx > -5:
            on_failure(f"Expected leftward movement, got dx={dx}")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


def test_speed_add_negative_over(on_success, on_failure):
    """Test: rig.speed.add(-10).over(ms) - gradual deceleration through zero to reverse"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    # Start at speed 5 moving right
    rig.direction.to(1, 0)
    rig.speed.to(5)
    actions.sleep("200ms")
    start_pos = ctrl.mouse_pos()

    # Add -10 over time, should slow, stop, reverse
    rig.speed.add(-10).over(500)

    def check_midpoint():
        """Should still be moving right but slower"""
        mid_pos = ctrl.mouse_pos()

        dx = mid_pos[0] - start_pos[0]
        if dx < 5:
            on_failure(f"Expected rightward movement at midpoint, got dx={dx}")
            return

        def check_final():
            """Should be moving left at speed -5"""
            rig_final = actions.user.mouse_rig()
            end_pos = ctrl.mouse_pos()

            # Final speed should be -5 (5 + -10 = -5)
            if abs(rig_final.state.speed - (-5)) > 1:
                on_failure(f"Final speed wrong: expected -5, got {rig_final.state.speed}")
                return

            # Direction should stay right (1, 0) - negative speed reverses movement
            dir_x, dir_y = rig_final.state.direction.x, rig_final.state.direction.y
            if abs(dir_x - 1.0) > 0.1 or abs(dir_y) > 0.1:
                on_failure(f"Final direction wrong: expected (1, 0), got ({dir_x:.2f}, {dir_y:.2f})")
                return

            rig_final.stop()
            on_success()

        cron.after("400ms", check_final)

    cron.after("300ms", check_midpoint)


# ============================================================================
# STOP TESTS
# ============================================================================

def test_stop_immediate():
    """Test: rig.stop() - immediate stop"""
    rig = actions.user.mouse_rig()
    rig.speed.to(10)
    rig.direction.to(1, 0)

    rig.stop()

    assert rig.state.speed == 0, f"Speed should be 0, got {rig.state.speed}"
    assert len(rig.state.layers) == 0, f"Expected no active layers, got: {rig.state.layers}"
    assert rig._state._frame_loop_job is None, "Frame loop should be stopped"
    assert len(rig._state._active_builders) == 0, f"Expected no active builders, got {len(rig._state._active_builders)}"


def test_stop_over(on_success, on_failure):
    """Test: rig.stop(ms) - decelerate to stop over time"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.speed.to(10)
    rig.direction.to(1, 0)

    def check_stopped():
        rig_check = actions.user.mouse_rig()
        if rig_check.state.speed != 0:
            on_failure(f"Speed should be 0, got {rig_check.state.speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return
        if rig_check._state._frame_loop_job is not None:
            on_failure("Frame loop should be stopped")
            return
        if len(rig_check._state._active_builders) != 0:
            on_failure(f"Expected no active builders, got {len(rig_check._state._active_builders)}")
            return
        on_success()

    rig.stop(500)
    cron.after("600ms", check_stopped)


def test_stop_over_then_callback(on_success, on_failure):
    """Test: rig.stop(ms).then(callback) - stop with callback"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.speed.to(10)
    rig.direction.to(1, 0)

    callback_fired = {"value": False}

    def stop_callback():
        callback_fired["value"] = True
        rig_check = actions.user.mouse_rig()
        if rig_check.state.speed != 0:
            on_failure(f"Speed should be 0 when callback fires, got {rig_check.state.speed}")
            return
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return
        if rig_check._state._frame_loop_job is not None:
            on_failure("Frame loop should be stopped when callback fires")
            return

    def verify_callback_fired():
        if not callback_fired["value"]:
            on_failure("Stop callback was never fired")
            return
        on_success()

    rig.stop(500).then(stop_callback)
    cron.after("700ms", verify_callback_fired)


def test_stop_callback_not_fired_on_interrupt(on_success, on_failure):
    """Test: stop callback not fired if interrupted by another operation"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.speed.to(10)
    rig.direction.to(1, 0)

    callback_fired = {"value": False}

    def stop_callback():
        callback_fired["value"] = True

    def interrupt_stop():
        # Start moving again before stop completes
        rig_interrupt = actions.user.mouse_rig()
        rig_interrupt.speed.to(5)

    def verify_callback_not_fired():
        if callback_fired["value"]:
            on_failure("Stop callback should not have fired when interrupted")
            return
        # Clean up
        rig_check = actions.user.mouse_rig()
        rig_check.stop()
        on_success()

    rig.stop(500).then(stop_callback)
    cron.after("200ms", interrupt_stop)  # Interrupt before stop completes
    cron.after("700ms", verify_callback_not_fired)


# ============================================================================
# TEST LIST
# ============================================================================

def test_layer_speed_offset_from_stopped(on_success, on_failure):
    """Test: layer().speed.offset.add() when base speed is 0 - should start movement"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Set direction but no base speed
    rig.direction.to(1, 0)

    # Add speed via layer offset
    rig.layer("boost").speed.offset.add(5)
    start_pos = ctrl.mouse_pos()

    def check_movement():
        rig_check = actions.user.mouse_rig()
        end_pos = ctrl.mouse_pos()

        # Should have computed speed from layer
        if abs(rig_check.state.speed - 5) > 1:
            on_failure(f"Speed is {rig_check.state.speed}, expected ~5")
            return

        # Frame loop should be running
        if rig_check._state._frame_loop_job is None:
            on_failure("Frame loop should be running with layer speed")
            return

        # Should have actual movement
        dx = end_pos[0] - start_pos[0]
        if dx < 10:
            on_failure(f"Expected rightward movement, only moved {dx}px")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


# ============================================================================
# TEST LIST
# ============================================================================

SPEED_TESTS = [
    ("speed.to()", test_speed_to),
    ("speed.to().over()", test_speed_to_over),
    ("speed.add()", test_speed_add),
    ("speed.mul()", test_speed_mul),
    ("speed.to() negative", test_speed_to_negative),
    ("speed.add() negative", test_speed_add_negative),
    ("speed.add().over() negative", test_speed_add_negative_over),
    ("stop()", test_stop_immediate),
    ("stop().over()", test_stop_over),
    ("stop().over().then()", test_stop_over_then_callback),
    ("stop() callback not fired on interrupt", test_stop_callback_not_fired_on_interrupt),
    ("layer().speed.offset.add() from stopped", test_layer_speed_offset_from_stopped),
]
