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
            rig_check.stop()
            on_failure("Expected error for emit on direction layer but operation succeeded")
        except Exception as e:
            print(f"  Error message: {e}")
            rig_final = actions.user.mouse_rig()
            rig_final.stop()
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
            rig_check.stop()
            on_failure("Expected error for emit on position layer but operation succeeded")
        except Exception as e:
            print(f"  Error message: {e}")
            rig_final = actions.user.mouse_rig()
            rig_final.stop()
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
            rig_check.stop()
            on_failure("Expected error for emit on speed.override but operation succeeded")
        except Exception as e:
            print(f"  Error message: {e}")
            rig_final = actions.user.mouse_rig()
            rig_final.stop()
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
        rig.stop()
        on_failure("Expected error for copy on non-existent layer but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        rig.stop()
        error_msg = str(e).lower()
        if "copy" in error_msg and ("does not exist" in error_msg or "not found" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


# ============================================================================
# REVERSE TESTS
# ============================================================================

def test_reverse_preserves_layers_instant(on_success, on_failure):
    """Test: rig.reverse() instant - flips direction but preserves layer animations"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Base: speed 5 moving right
        rig.speed.to(5)
        rig.direction.to(1, 0)

        # Layer with over/revert: boost that ramps up and down
        # Use longer durations so animations are still active during checks
        rig.layer("boost").speed.offset.add(3).over(500).revert(500)

        # Base speed add with over/revert
        rig.speed.add(3).over(400).revert(400)

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

        speed_before_reverse = rig_check.state.speed

        # Reverse everything - instant
        rig_check.reverse()

        def check_immediate():
            rig_immediate = actions.user.mouse_rig()
            speed_immediate = rig_immediate.state.speed

            # Speed should not suddenly spike up
            if speed_immediate > speed_before_reverse * 1.5:
                on_failure(f"Speed spiked immediately after reverse: {speed_immediate} (was {speed_before_reverse}, ratio: {speed_immediate/speed_before_reverse:.2f}x)")
                return

        cron.after("50ms", check_immediate)

        def check_after_reverse():
            rig_mid = actions.user.mouse_rig()

            # Verify layer counts: boost + base.speed
            layer_count = len(rig_mid.state.layers)
            if layer_count != 2:
                on_failure(f"Expected 2 layers after reverse (boost + base.speed), got {layer_count}: {rig_mid.state.layers}")
                return

            # Boost layer should still exist (preserved)
            if "boost" not in rig_mid.state.layers:
                on_failure(f"Boost layer lost after reverse: {rig_mid.state.layers}")
                return

            # Base.speed layer should exist (from speed.add with over/revert)
            if "base.speed" not in rig_mid.state.layers:
                on_failure(f"base.speed layer lost after reverse: {rig_mid.state.layers}")
                return

            # Check for emit layers (should be 0 for instant reverse)
            emit_layer_count = sum(1 for name in rig_mid.state.layers if "emit" in name.lower())
            if emit_layer_count != 0:
                on_failure(f"Expected 0 emit layers after instant reverse, got {emit_layer_count}")
                return

            # Net state: direction should be flipped (moving left now)
            if rig_mid.state.direction.x >= 0:
                on_failure(f"Net direction should be left (negative x), got ({rig_mid.state.direction.x}, {rig_mid.state.direction.y})")
                return

            # Net base state: base speed should be animating (from speed.add with over/revert)
            base_speed = rig_mid.state.base.speed
            if base_speed < 5 or base_speed > 10:
                on_failure(f"Base speed should be animating between 5-10, got {base_speed}")
                return

            # Base direction should be reversed
            if rig_mid.state.base.direction.x >= 0:
                on_failure(f"Base direction should be left, got ({rig_mid.state.base.direction.x}, {rig_mid.state.base.direction.y})")
                return

            # Net layer state: boost layer contributing to speed
            if len(rig_mid.state.layers) > 0:
                # Should have boost layer contribution
                net_speed = rig_mid.state.speed
                if net_speed < 5:
                    on_failure(f"Net speed after reverse is {net_speed}, expected > 5")
                    return

            def check_animations_complete():
                rig_final = actions.user.mouse_rig()
                # Animations should have completed naturally
                # Back to base speed 5, but moving left
                if abs(rig_final.state.speed - 5) > 2:
                    on_failure(f"Final speed is {rig_final.state.speed}, expected ~5")
                    return
                if rig_final.state.direction.x >= 0:
                    on_failure(f"Final direction should still be left, got ({rig_final.state.direction.x}, {rig_final.state.direction.y})")
                    return

                rig_final.stop()
                on_success()

            cron.after("500ms", check_animations_complete)

        cron.after("500ms", check_after_reverse)

    cron.after("100ms", start_test)


def test_reverse_preserves_layers_gradual(on_success, on_failure):
    """Test: rig.reverse(ms) gradual - smooth turn preserving layer animations"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Base: speed 5 moving right
        rig.speed.to(5)
        rig.direction.to(1, 0)

        # Layer with over/revert: boost that ramps up and down
        # Use longer durations so animations are still active during checks
        rig.layer("boost").speed.offset.add(3).over(500).revert(500)

        # Base speed add with over/revert
        rig.speed.add(3).over(400).revert(400)

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

        speed_before_reverse = rig_check.state.speed

        # Reverse everything - gradual transition over 400ms
        rig_check.reverse(400)

        def check_immediate():
            rig_immediate = actions.user.mouse_rig()
            speed_immediate = rig_immediate.state.speed

            # Speed should not suddenly spike up
            if speed_immediate > speed_before_reverse * 1.5:
                on_failure(f"Speed spiked immediately after reverse: {speed_immediate} (was {speed_before_reverse}, ratio: {speed_immediate/speed_before_reverse:.2f}x)")
                return

        cron.after("50ms", check_immediate)

        def check_during_reverse():
            """Check state during the gradual reverse process"""
            rig_during = actions.user.mouse_rig()

            # During gradual reverse: should have emit layers + original layers
            # Expected: boost layer + base animation layer + emit layers from reverse
            layer_count = len(rig_during.state.layers)

            # Count emit layers (created by gradual reverse)
            emit_layer_count = sum(1 for name in rig_during.state.layers if "emit" in name.lower())

            # Should have emit layers during gradual reverse
            if emit_layer_count == 0:
                on_failure(f"Expected emit layers during gradual reverse, got 0. Layers: {rig_during.state.layers}")
                return

            # Original boost layer should still exist
            if "boost" not in rig_during.state.layers:
                on_failure(f"Boost layer lost during reverse: {rig_during.state.layers}")
                return

            print(f"  During reverse: {layer_count} total layers, {emit_layer_count} emit layers")
            print(f"  Layers: {rig_during.state.layers}")

        def check_after_reverse():
            rig_mid = actions.user.mouse_rig()

            # Verify layer counts: boost + base.speed (no copy/emit layers should remain)
            layer_count = len(rig_mid.state.layers)
            non_emit_layers = [name for name in rig_mid.state.layers if "emit" not in name.lower() and "copy" not in name.lower()]
            if len(non_emit_layers) != 2:
                on_failure(f"Expected 2 preserved layers (boost + base.speed), got {len(non_emit_layers)}: {rig_mid.state.layers}")
                return

            # Boost layer should still exist (preserved)
            if "boost" not in rig_mid.state.layers:
                on_failure(f"Boost layer lost after reverse: {rig_mid.state.layers}")
                return

            # Base.speed layer should exist (from speed.add with over/revert)
            if "base.speed" not in rig_mid.state.layers:
                on_failure(f"base.speed layer lost after reverse: {rig_mid.state.layers}")
                return

            # Check for emit/copy layers (should be 0 after gradual reverse completes)
            temp_layer_count = sum(1 for name in rig_mid.state.layers if "emit" in name.lower() or "copy" in name.lower())
            if temp_layer_count != 0:
                on_failure(f"Expected 0 temporary emit/copy layers after gradual reverse, got {temp_layer_count}: {rig_mid.state.layers}")
                return

            # Net state: direction should be flipped (moving left now) after 400ms reverse + 500ms wait
            if rig_mid.state.direction.x >= 0:
                on_failure(f"Net direction should be left (negative x), got ({rig_mid.state.direction.x}, {rig_mid.state.direction.y})")
                return

            # Net base state: base speed should be animating (from speed.add with over/revert)
            base_speed = rig_mid.state.base.speed
            if base_speed < 5 or base_speed > 10:
                on_failure(f"Base speed should be animating between 5-10, got {base_speed}")
                return

            # Base direction should be reversed
            if rig_mid.state.base.direction.x >= 0:
                on_failure(f"Base direction should be left, got ({rig_mid.state.base.direction.x}, {rig_mid.state.base.direction.y})")
                return

            # Net layer state: boost layer contributing to speed
            net_speed = rig_mid.state.speed
            if net_speed < 5:
                on_failure(f"Net speed after reverse is {net_speed}, expected > 5")
                return

            def check_animations_complete():
                rig_final = actions.user.mouse_rig()
                # Animations should have completed naturally
                # Back to base speed 5, but moving left
                if abs(rig_final.state.speed - 5) > 2:
                    on_failure(f"Final speed is {rig_final.state.speed}, expected ~5")
                    return
                if rig_final.state.direction.x >= 0:
                    on_failure(f"Final direction should still be left, got ({rig_final.state.direction.x}, {rig_final.state.direction.y})")
                    return

                rig_final.stop()
                on_success()

            cron.after("500ms", check_animations_complete)

        # Check during the reverse (200ms into the 400ms reverse)
        cron.after("200ms", check_during_reverse)

        # Check after reverse completes (500ms = after 400ms reverse finishes)
        cron.after("500ms", check_after_reverse)

    cron.after("100ms", start_test)


def test_reverse_instant(on_success, on_failure):
    """Test: rig.reverse() - instant 180° turn with position verification"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_movement():
        # Start moving right
        rig.speed.to(3)
        rig.direction.to(1, 0)

        cron.after("200ms", do_reverse)

    def do_reverse():
        start_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()
        speed_before_reverse = rig_check.state.speed

        # Instant reverse
        rig.reverse()

        def check_immediate():
            rig_immediate = actions.user.mouse_rig()
            speed_immediate = rig_immediate.state.speed

            # Speed should not suddenly spike up
            if speed_immediate > speed_before_reverse * 1.5:
                on_failure(f"Speed spiked immediately after reverse: {speed_immediate} (was {speed_before_reverse}, ratio: {speed_immediate/speed_before_reverse:.2f}x)")
                return

        cron.after("50ms", check_immediate)

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

    cron.after("100ms", start_movement)


def test_reverse_gradual(on_success, on_failure):
    """Test: rig.reverse(ms) - smooth 180° turn over time through zero"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_movement():
        # Start moving right at speed 3
        rig.speed.to(3)
        rig.direction.to(1, 0)

        cron.after("200ms", do_reverse)

    def do_reverse():
        start_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()
        speed_before_reverse = rig_check.state.speed

        # Gradual reverse - smooth transition through zero
        # Direction lerps: (1,0) → (0,0) → (-1,0)
        # Velocity: slows down → stops → speeds up in opposite direction
        rig.reverse(1000)

        def check_immediate():
            rig_immediate = actions.user.mouse_rig()
            speed_immediate = rig_immediate.state.speed

            # Speed should not suddenly spike up
            if speed_immediate > speed_before_reverse * 1.5:
                on_failure(f"Speed spiked immediately after reverse: {speed_immediate} (was {speed_before_reverse}, ratio: {speed_immediate/speed_before_reverse:.2f}x)")
                return

        cron.after("50ms", check_immediate)

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

    cron.after("100ms", start_movement)


def test_reverse_with_speed_add_animation(on_success, on_failure):
    """Test: rig.reverse() with speed.add().over() - should emit base animation layer"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Base speed with direction
        rig.speed.to(5)
        rig.direction.to(1, 0)

        # Add speed with animation - creates a base layer (ephemeral)
        rig.speed.add(5).over(1000)

        cron.after("300ms", check_before_reverse)

    def check_before_reverse():
        rig_check = actions.user.mouse_rig()

        # Should have 1 layer from speed.add()
        layer_count = len(rig_check.state.layers)
        if layer_count != 1:
            on_failure(f"Expected 1 layer before reverse, got {layer_count}: {rig_check.state.layers}")
            return

        # Should be moving right with elevated speed
        if rig_check.state.direction.x <= 0:
            on_failure(f"Direction should be right before reverse, got ({rig_check.state.direction.x}, {rig_check.state.direction.y})")
            return

        # Capture speed before reverse for comparison
        speed_before_reverse = rig_check.state.speed
        print(f"  Before reverse - Layers: {rig_check.state.layers}")
        print(f"  Before reverse - Speed: {speed_before_reverse}")

        # Gradual reverse
        rig_check.reverse(1000)

        # Immediately check speed after calling reverse
        def check_immediate():
            rig_immediate = actions.user.mouse_rig()
            speed_immediate = rig_immediate.state.speed

            print(f"  Immediately after reverse() - Speed: {speed_immediate}")

            # Speed should not suddenly spike up
            # Emit layers should smooth transition, not cause spikes
            # Allow modest increase (up to 1.5x) for emit layer dynamics
            if speed_immediate > speed_before_reverse * 1.5:
                on_failure(f"Speed spiked immediately after reverse: {speed_immediate} (was {speed_before_reverse}, ratio: {speed_immediate/speed_before_reverse:.2f}x)")
                return

        cron.after("50ms", check_immediate)

        def check_during_reverse():
            """Check state during the gradual reverse process"""
            rig_during = actions.user.mouse_rig()

            layer_count = len(rig_during.state.layers)
            emit_layer_count = sum(1 for name in rig_during.state.layers if "emit" in name.lower())
            speed_during = rig_during.state.speed

            print(f"  During reverse - Layers: {rig_during.state.layers}")
            print(f"  During reverse - {layer_count} total layers, {emit_layer_count} emit layers")
            print(f"  During reverse - Speed: {speed_during}")

            # Should have emit layers during gradual reverse
            if emit_layer_count == 0:
                on_failure(f"Expected emit layers during reverse, got 0. Layers: {rig_during.state.layers}")
                return

            # Speed should be reasonable - emit creates 2x base contribution
            # With base speed 5 + add(5) animation, at 300ms we're around 6-7
            # Emit creates 2x base (10), so total could be up to ~17, but should fade
            # At 500ms into reverse (halfway), emit should be fading
            if speed_during > 20:
                on_failure(f"Speed during reverse is too high: {speed_during}, expected < 20")
                return

            def check_after_reverse():
                rig_final = actions.user.mouse_rig()

                # Direction should be reversed (left)
                if rig_final.state.direction.x >= 0:
                    on_failure(f"Direction should be left after reverse, got ({rig_final.state.direction.x}, {rig_final.state.direction.y})")
                    return

                # Base layer animation has completed by now (ephemeral), so expect 0 layers
                final_layer_count = len(rig_final.state.layers)
                if final_layer_count != 0:
                    on_failure(f"Expected 0 layers after animation completes, got {final_layer_count}: {rig_final.state.layers}")
                    return

                print(f"  After reverse - Layers: {rig_final.state.layers}")
                print(f"  After reverse - Speed: {rig_final.state.speed}")

                rig_final.stop()
                on_success()

            cron.after("1100ms", check_after_reverse)

        cron.after("500ms", check_during_reverse)

    cron.after("100ms", start_test)


def test_reverse_with_speed_add_animation_from_zero(on_success, on_failure):
    """Test: rig.reverse() with speed.add().over() starting from zero base speed"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()

    def start_test():
        # Set base speed to 0 first, then add with animation
        rig.speed.to(0)
        rig.direction.to(1, 0)

        # Add speed with animation from zero - creates a base layer (ephemeral)
        rig.speed.add(5).over(1000)

        cron.after("300ms", check_before_reverse)

    def check_before_reverse():
        rig_check = actions.user.mouse_rig()

        # Should have 1 layer from speed.add()
        layer_count = len(rig_check.state.layers)
        if layer_count != 1:
            on_failure(f"Expected 1 layer before reverse, got {layer_count}: {rig_check.state.layers}")
            return

        # Should be moving right with some speed
        if rig_check.state.direction.x <= 0:
            on_failure(f"Direction should be right before reverse, got ({rig_check.state.direction.x}, {rig_check.state.direction.y})")
            return

        if rig_check.state.speed < 1:
            on_failure(f"Speed should be > 1 during animation, got {rig_check.state.speed}")
            return

        print(f"  Before reverse - Layers: {rig_check.state.layers}")
        print(f"  Before reverse - Speed: {rig_check.state.speed}")

        speed_before_reverse = rig_check.state.speed

        # Gradual reverse
        rig_check.reverse(1000)

        def check_immediate():
            rig_immediate = actions.user.mouse_rig()
            speed_immediate = rig_immediate.state.speed

            # Speed should not suddenly spike up
            if speed_immediate > speed_before_reverse * 1.5:
                on_failure(f"Speed spiked immediately after reverse: {speed_immediate} (was {speed_before_reverse}, ratio: {speed_immediate/speed_before_reverse:.2f}x)")
                return

        cron.after("50ms", check_immediate)

        def check_during_reverse():
            """Check state during the gradual reverse process"""
            rig_during = actions.user.mouse_rig()

            layer_count = len(rig_during.state.layers)
            emit_layer_count = sum(1 for name in rig_during.state.layers if "emit" in name.lower())

            print(f"  During reverse - Layers: {rig_during.state.layers}")
            print(f"  During reverse - {layer_count} total layers, {emit_layer_count} emit layers")

            # Should have emit layers during gradual reverse
            if emit_layer_count == 0:
                on_failure(f"Expected emit layers during reverse, got 0. Layers: {rig_during.state.layers}")
                return

            def check_after_reverse():
                rig_final = actions.user.mouse_rig()

                # Direction should be reversed (left)
                if rig_final.state.direction.x >= 0:
                    on_failure(f"Direction should be left after reverse, got ({rig_final.state.direction.x}, {rig_final.state.direction.y})")
                    return

                # Base layer animation has completed by now (ephemeral), so expect 0 layers
                final_layer_count = len(rig_final.state.layers)
                if final_layer_count != 0:
                    on_failure(f"Expected 0 layers after animation completes, got {final_layer_count}: {rig_final.state.layers}")
                    return

                print(f"  After reverse - Layers: {rig_final.state.layers}")
                print(f"  After reverse - Speed: {rig_final.state.speed}")

                rig_final.stop()
                on_success()

            cron.after("1100ms", check_after_reverse)

        cron.after("500ms", check_during_reverse)

    cron.after("100ms", start_test)


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
    ("rig.reverse() preserves layers - instant", test_reverse_preserves_layers_instant),
    ("rig.reverse() preserves layers - gradual", test_reverse_preserves_layers_gradual),
    ("rig.reverse() with speed.add().over()", test_reverse_with_speed_add_animation),
    ("rig.reverse() with speed.add().over() from zero", test_reverse_with_speed_add_animation_from_zero),
    ("rig.reverse()", test_reverse_instant),
    ("rig.reverse(ms)", test_reverse_gradual),
]
