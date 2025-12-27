"""Special operations tests: copy(), emit(), and reverse()"""

from talon import actions, cron, ctrl

CENTER_X = 960
CENTER_Y = 540


# ============================================================================
# EMIT TESTS
# ============================================================================

def test_layer_vector_emit(on_success, on_failure):
    """Test: layer().vector.offset emit() converts to decaying offset"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Create wind layer with velocity offset
        rig.layer("wind").vector.offset.add(3, 0)

        cron.after("300ms", check_during_wind)

    def check_during_wind():
        rig_check = actions.user.mouse_rig()
        # Should be moving: speed ~3
        if abs(rig_check.state.speed - 3) > 1:
            on_failure(f"Speed during wind is {rig_check.state.speed}, expected ~3")
            return
        if "wind" not in rig_check.state.layers:
            on_failure(f"Wind layer not found: {rig_check.state.layers}")
            return

        # Emit the wind - converts to autonomous decaying offset
        rig.layer("wind").emit(300)

        def check_after_emit():
            rig_mid = actions.user.mouse_rig()
            # Wind layer should be gone, replaced by anonymous emit layer
            if "wind" in rig_mid.state.layers:
                on_failure(f"Wind layer still exists after emit: {rig_mid.state.layers}")
                return
            # Should still be moving (offset fading)
            if rig_mid.state.speed < 1:
                on_failure(f"Speed after emit is {rig_mid.state.speed}, expected > 1")
                return

            def check_after_fade():
                rig_final = actions.user.mouse_rig()
                # Offset should have faded to zero
                if abs(rig_final.state.speed) > 0.5:
                    on_failure(f"Speed after fade is {rig_final.state.speed}, expected ~0")
                    return

                rig_final.stop()
                on_success()

            cron.after("400ms", check_after_fade)

        cron.after("100ms", check_after_emit)

    cron.after("100ms", start_test)


def test_rig_emit_with_new_operation(on_success, on_failure):
    """Test: rig.emit() with new operation blending"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Set base velocity
        rig.vector.to(4, 0)

        cron.after("300ms", check_initial)

    def check_initial():
        rig_check = actions.user.mouse_rig()
        if abs(rig_check.state.speed - 4) > 1:
            on_failure(f"Initial speed is {rig_check.state.speed}, expected ~4")
            return

        # Emit the velocity and immediately add new operation
        rig_check.emit(300)
        rig_check.vector.to(0, 3)  # New operation: move down

        def check_blending():
            rig_mid = actions.user.mouse_rig()
            # Should have both emitted offset and new velocity
            # Base speed should be ~3 (from new operation)
            # But total movement is affected by fading offset
            if rig_mid.state.speed < 2:
                on_failure(f"Speed during blend is {rig_mid.state.speed}, expected > 2")
                return

            def check_final():
                rig_final = actions.user.mouse_rig()
                # After emit fades, should be at new velocity: (0, 3)
                if abs(rig_final.state.speed - 3) > 1:
                    on_failure(f"Final speed is {rig_final.state.speed}, expected ~3")
                    return

                rig_final.stop()
                on_success()

            cron.after("400ms", check_final)

        cron.after("100ms", check_blending)

    cron.after("100ms", start_test)


def test_speed_offset_emit(on_success, on_failure):
    """Test: layer().speed.offset emit() converts to vector offset"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Set base velocity
        rig.speed.to(3)
        rig.direction.to(1, 0)

        # Add speed boost via offset
        rig.layer("boost").speed.offset.add(2)

        cron.after("300ms", check_during_boost)

    def check_during_boost():
        rig_check = actions.user.mouse_rig()
        # Should have combined speed: 3 + 2 = 5
        if abs(rig_check.state.speed - 5) > 1:
            on_failure(f"Speed during boost is {rig_check.state.speed}, expected ~5")
            return
        if "boost" not in rig_check.state.layers:
            on_failure(f"Boost layer not found: {rig_check.state.layers}")
            return

        # Emit the boost - converts to vector offset using current direction
        rig_check.layer("boost").emit(300)

        def check_after_emit():
            rig_mid = actions.user.mouse_rig()
            # Boost layer should be gone
            if "boost" in rig_mid.state.layers:
                on_failure(f"Boost layer still exists after emit: {rig_mid.state.layers}")
                return
            # Should still have elevated speed (from emitted offset)
            if rig_mid.state.speed < 4:
                on_failure(f"Speed after emit is {rig_mid.state.speed}, expected > 4")
                return

            def check_after_fade():
                rig_final = actions.user.mouse_rig()
                # Should be back to base speed: 3
                if abs(rig_final.state.speed - 3) > 1:
                    on_failure(f"Speed after fade is {rig_final.state.speed}, expected ~3")
                    return

                rig_final.stop()
                on_success()

            cron.after("400ms", check_after_fade)

        cron.after("100ms", check_after_emit)

    cron.after("100ms", start_test)


def test_base_emit_no_layers(on_success, on_failure):
    """Test: rig.emit() on base speed (no layers) converts to decaying offset"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Set base speed and direction
        rig.direction.to(1, 0)  # Right
        rig.speed.to(5)

        cron.after("300ms", check_initial)

    def check_initial():
        rig_check = actions.user.mouse_rig()
        # Should be moving at speed 5
        if abs(rig_check.state.speed - 5) > 1:
            on_failure(f"Initial speed is {rig_check.state.speed}, expected ~5")
            return

        # No layers should exist
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no layers, got: {rig_check.state.layers}")
            return

        # Emit the base movement - converts to decaying offset
        rig_check.emit(300)

        def check_after_emit():
            rig_mid = actions.user.mouse_rig()
            # Should still be moving (offset decaying)
            if rig_mid.state.speed < 2:
                on_failure(f"Speed after emit is {rig_mid.state.speed}, expected > 2")
                return

            def check_after_fade():
                rig_final = actions.user.mouse_rig()
                # Speed should have decayed to ~0
                if abs(rig_final.state.speed) > 0.5:
                    on_failure(f"Speed after fade is {rig_final.state.speed}, expected ~0")
                    return

                rig_final.stop()
                on_success()

            cron.after("400ms", check_after_fade)

        cron.after("100ms", check_after_emit)

    cron.after("100ms", start_test)


def test_emit_on_direction_layer_errors(on_success, on_failure):
    """Test: validate layer().direction.emit() errors"""
    rig = actions.user.mouse_rig()
    rig.layer("turn").direction.offset.by(45)

    def try_emit():
        try:
            rig_check = actions.user.mouse_rig()
            rig_check.layer("turn").emit(500)
            on_failure("Expected error for emit on direction layer but operation succeeded")
        except Exception as e:
            print(f"  Error message: {e}")
            error_msg = str(e).lower()
            if "emit" in error_msg and "direction" in error_msg:
                on_success()
            else:
                on_failure(f"Error occurred but message unclear: {e}")

    cron.after("100ms", try_emit)


def test_emit_on_position_layer_errors(on_success, on_failure):
    """Test: validate layer().pos.emit() errors"""
    rig = actions.user.mouse_rig()
    rig.layer("drift").pos.offset.by(10, 0)

    def try_emit():
        try:
            rig_check = actions.user.mouse_rig()
            rig_check.layer("drift").emit(500)
            on_failure("Expected error for emit on position layer but operation succeeded")
        except Exception as e:
            print(f"  Error message: {e}")
            error_msg = str(e).lower()
            if "emit" in error_msg and ("position" in error_msg or "pos" in error_msg):
                on_success()
            else:
                on_failure(f"Error occurred but message unclear: {e}")

    cron.after("100ms", try_emit)


def test_emit_on_speed_override_errors(on_success, on_failure):
    """Test: validate layer().speed.override.emit() errors"""
    rig = actions.user.mouse_rig()
    rig.speed.to(5)
    rig.direction.to(1, 0)
    rig.layer("boost").speed.override.to(10)

    def try_emit():
        try:
            rig_check = actions.user.mouse_rig()
            rig_check.layer("boost").emit(500)
            on_failure("Expected error for emit on speed.override but operation succeeded")
        except Exception as e:
            print(f"  Error message: {e}")
            error_msg = str(e).lower()
            if "emit" in error_msg and "override" in error_msg:
                on_success()
            else:
                on_failure(f"Error occurred but message unclear: {e}")

    cron.after("100ms", try_emit)


# ============================================================================
# COPY TESTS
# ============================================================================

def test_layer_copy_doubles(on_success, on_failure):
    """Test: layer().copy() duplicates a layer - both should be active"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Create boost layer
        rig.layer("boost").speed.offset.add(5)
        rig.speed.to(10)
        rig.direction.to(1, 0)

        cron.after("200ms", check_before_copy)

    def check_before_copy():
        rig_check = actions.user.mouse_rig()
        # Should have base speed 10 + boost 5 = 15
        if abs(rig_check.state.speed - 15) > 1:
            on_failure(f"Speed before copy is {rig_check.state.speed}, expected ~15")
            return
        if "boost" not in rig_check.state.layers:
            on_failure(f"Boost layer not found: {rig_check.state.layers}")
            return

        # Copy the boost layer
        rig_check.layer("boost").copy("boost_copy")

        def check_after_copy():
            rig_mid = actions.user.mouse_rig()
            # Should have both boost and boost_copy: 10 + 5 + 5 = 20
            if abs(rig_mid.state.speed - 20) > 1:
                on_failure(f"Speed after copy is {rig_mid.state.speed}, expected ~20")
                return
            if "boost" not in rig_mid.state.layers:
                on_failure(f"Original boost layer not found: {rig_mid.state.layers}")
                return
            if "boost_copy" not in rig_mid.state.layers:
                on_failure(f"Copied boost_copy layer not found: {rig_mid.state.layers}")
                return

            rig_mid.stop()
            on_success()

        cron.after("100ms", check_after_copy)

    cron.after("100ms", start_test)


def test_validate_nonexistent_layer_copy_errors(on_success, on_failure):
    """Test: validate layer('nonexistent').copy() errors (layer doesn't exist)"""
    rig = actions.user.mouse_rig()
    try:
        rig.layer("nonexistent").copy()
        on_failure("Expected error for copy on non-existent layer but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "copy" in error_msg and ("does not exist" in error_msg or "not found" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


# ============================================================================
# REVERSE TESTS
# ============================================================================

def test_reverse_preserves_layers(on_success, on_failure):
    """Test: rig.reverse() flips direction but preserves layer animations"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Base: speed 10 moving right
        rig.speed.to(10)
        rig.direction.to(1, 0)

        # Layer with over/revert: boost that ramps up and down
        rig.layer("boost").speed.offset.add(5).over(300).revert(300)

        # Base speed add with over/revert
        rig.speed.add(3).over(200).revert(200)

        cron.after("150ms", check_before_reverse)

    def check_before_reverse():
        rig_check = actions.user.mouse_rig()
        # Should be moving right with elevated speed (animations in progress)
        initial_speed = rig_check.state.speed
        initial_direction = rig_check.state.direction

        if initial_direction.x <= 0:
            on_failure(f"Direction before reverse should be right (positive x), got ({initial_direction.x}, {initial_direction.y})")
            return

        if "boost" not in rig_check.state.layers:
            on_failure(f"Boost layer not found before reverse: {rig_check.state.layers}")
            return

        # Reverse everything
        rig_check.reverse()

        def check_after_reverse():
            rig_mid = actions.user.mouse_rig()
            # Direction should be flipped (moving left now)
            if rig_mid.state.direction.x >= 0:
                on_failure(f"Direction after reverse should be left (negative x), got ({rig_mid.state.direction.x}, {rig_mid.state.direction.y})")
                return

            # Boost layer should still exist (preserved)
            if "boost" not in rig_mid.state.layers:
                on_failure(f"Boost layer lost after reverse: {rig_mid.state.layers}")
                return

            # Should still be moving (speed preserved, direction flipped)
            if rig_mid.state.speed < 5:
                on_failure(f"Speed after reverse is {rig_mid.state.speed}, expected > 5")
                return

            def check_animations_complete():
                rig_final = actions.user.mouse_rig()
                # Animations should have completed naturally
                # Back to base speed 10, but moving left
                if abs(rig_final.state.speed - 10) > 2:
                    on_failure(f"Final speed is {rig_final.state.speed}, expected ~10")
                    return
                if rig_final.state.direction.x >= 0:
                    on_failure(f"Final direction should still be left, got ({rig_final.state.direction.x}, {rig_final.state.direction.y})")
                    return

                rig_final.stop()
                on_success()

            cron.after("500ms", check_animations_complete)

        cron.after("100ms", check_after_reverse)

    cron.after("100ms", start_test)


def test_reverse_instant(on_success, on_failure):
    """Test: rig.reverse() - instant 180° turn with position verification"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Start moving right
    rig.speed.to(3)
    rig.direction.to(1, 0)
    actions.sleep("200ms")
    start_pos = ctrl.mouse_pos()

    # Instant reverse
    rig.reverse()

    def check_reversed():
        rig_check = actions.user.mouse_rig()
        end_pos = ctrl.mouse_pos()

        # Direction should be reversed (left)
        dir_x, dir_y = rig_check.state.direction.x, rig_check.state.direction.y
        if abs(dir_x - (-1.0)) > 0.1 or abs(dir_y) > 0.1:
            on_failure(f"Direction wrong: expected (-1, 0), got ({dir_x:.2f}, {dir_y:.2f})")
            return

        # Should be moving left
        dx = end_pos[0] - start_pos[0]
        if dx > -10:
            on_failure(f"Expected leftward movement, got dx={dx}")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_reversed)


def test_reverse_gradual(on_success, on_failure):
    """Test: rig.reverse(ms) - smooth 180° turn over time through zero"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Start moving right at speed 3
    rig.speed.to(3)
    rig.direction.to(1, 0)
    actions.sleep("200ms")
    start_pos = ctrl.mouse_pos()

    # Gradual reverse - smooth transition through zero
    # Direction lerps: (1,0) → (0,0) → (-1,0)
    # Velocity: slows down → stops → speeds up in opposite direction
    rig.reverse(1000)

    def check_midpoint():
        """At midpoint - should be near stop or moving slowly"""
        mid_pos = ctrl.mouse_pos()

        # Should have moved right initially, but be slowing down
        dx = mid_pos[0] - start_pos[0]
        if dx < 5:
            on_failure(f"Expected some rightward movement before stopping, got dx={dx}")
            return

        def check_final():
            """After reversal completes - should be moving left"""
            rig_final = actions.user.mouse_rig()
            end_pos = ctrl.mouse_pos()

            # Direction should be reversed (left)
            dir_x, dir_y = rig_final.state.direction.x, rig_final.state.direction.y
            if abs(dir_x - (-1.0)) > 0.1 or abs(dir_y) > 0.1:
                on_failure(f"Final direction wrong: expected (-1, 0), got ({dir_x:.2f}, {dir_y:.2f})")
                return

            # Should be moving left now
            dx_final = end_pos[0] - mid_pos[0]
            if dx_final > -5:
                on_failure(f"Expected leftward movement after reversal, got dx={dx_final}")
                return

            # Check final speed is back to original
            if rig_final.state.speed < 2:
                on_failure(f"Final speed is {rig_final.state.speed}, expected ~3")
                return

            rig_final.stop()
            on_success()

        cron.after("1200ms", check_final)

    cron.after("500ms", check_midpoint)


# ============================================================================
# TEST LIST
# ============================================================================

SPECIAL_TESTS = [
    ("layer().vector.emit()", test_layer_vector_emit),
    ("rig.emit() + new operation", test_rig_emit_with_new_operation),
    ("layer().speed.offset.emit()", test_speed_offset_emit),
    ("rig.emit()", test_base_emit_no_layers),
    ("validate layer().direction.emit()", test_emit_on_direction_layer_errors),
    ("validate layer().pos.emit()", test_emit_on_position_layer_errors),
    ("validate layer().speed.override.emit()", test_emit_on_speed_override_errors),
    ("layer().copy()", test_layer_copy_doubles),
    ("validate layer('nonexistent').copy()", test_validate_nonexistent_layer_copy_errors),
    ("rig.reverse() preserves layers", test_reverse_preserves_layers),
    ("rig.reverse()", test_reverse_instant),
    ("rig.reverse(ms)", test_reverse_gradual),
]
