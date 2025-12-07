from talon import actions, ctrl, cron

CENTER_X = 960
CENTER_Y = 540

# ============================================================================
# VALIDATION TESTS
# ============================================================================

def test_multiple_properties_not_allowed(on_success, on_failure):
    """Test: rig.speed(3).direction.to() should error - cannot combine multiple properties"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(3).direction.to(1, 0)
        on_failure("Expected error but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "combine" in error_msg and "properties" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_hold_without_operation(on_success, on_failure):
    """Test: rig.hold() without a property operation should error"""
    try:
        rig = actions.user.mouse_rig()
        rig.hold(1000)
        on_failure("Expected error but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "hold" in error_msg and ("attribute" in error_msg or "operation" in error_msg or "property" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_over_without_operation(on_success, on_failure):
    """Test: calling .over() without a prior operation should error"""
    try:
        rig = actions.user.mouse_rig()
        rig.layer("test").over(500)
        on_failure("Expected error but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "over" in error_msg or "transition" in error_msg or "cannot" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_revert_without_operation(on_success, on_failure):
    """Test: calling .revert() without a prior operation should error or no-op gracefully"""
    try:
        rig = actions.user.mouse_rig()
        rig.layer("test").revert(500)
        # This might be a no-op rather than error, check state
        actions.sleep("100ms")
        rig_check = actions.user.mouse_rig()
        if len(rig_check.state.layers) == 0:
            on_success()  # Graceful no-op
        else:
            on_failure("Layer created but no operation was performed")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "revert" in error_msg or "nothing" in error_msg or "cannot" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_hold_without_revert(on_success, on_failure):
    """Test: calling .hold() without .revert() should error"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(3)
        builder = rig.direction.to(1, 0).hold(500)
        builder._execute()  # Force execution to catch validation error
        on_failure("Expected error for hold() without revert() but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "hold" in error_msg or "revert" in error_msg or "requires" in error_msg or "must" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_layer_operation_without_mode(on_success, on_failure):
    """Test: layer operation without mode (.offset/.override/.scale) should error"""
    try:
        rig = actions.user.mouse_rig()
        builder = rig.layer("test").speed.to(100)
        builder._execute()  # Force execution to catch validation error
        on_failure("Expected error for layer operation without mode but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "mode" in error_msg or "offset" in error_msg or "override" in error_msg or "scale" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_invalid_direction_vector_zero(on_success, on_failure):
    """Test: direction.to(0, 0) should error - invalid zero vector"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(3)
        rig.direction.to(0, 0)
        on_failure("Expected error for zero vector but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if ("zero" in error_msg or "invalid" in error_msg) and ("stop" in error_msg or "speed.to(0)" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_negative_duration(on_success, on_failure):
    """Test: negative duration should error or be treated as 0"""
    try:
        rig = actions.user.mouse_rig()
        rig.pos.to(CENTER_X, CENTER_Y)
        rig.speed.to(5).over(-500)
        # If it succeeds, check that it doesn't create a weird state
        actions.sleep("100ms")
        # Should either error or handle gracefully
        on_success()  # If no crash, consider it handled
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "negative" in error_msg or "invalid" in error_msg or "duration" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_invalid_speed_zero(on_success, on_failure):
    """Test: speed(0) - zero speed should be handled gracefully (no movement)"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(0)
        rig.layer("test").direction.to(1, 0).hold(500)
        # Should handle gracefully - just won't move
        on_success()
    except Exception as e:
        on_failure(f"Unexpected error with zero speed: {e}")


def test_invalid_speed_negative(on_success, on_failure):
    """Test: speed(-1) - negative speed should be handled gracefully (abs value or no movement)"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(-1)
        rig.layer("test").direction.to(1, 0).hold(500)
        # Should handle gracefully
        on_success()
    except Exception as e:
        on_failure(f"Unexpected error with negative speed: {e}")


def test_layer_empty_name(on_success, on_failure):
    """Test: layer("") with empty string should error or handle gracefully"""
    try:
        rig = actions.user.mouse_rig()
        rig.layer("").direction.to(1, 0).hold(500)
        # If it succeeds, check state
        actions.sleep("100ms")
        rig_check = actions.user.mouse_rig()
        if "" in rig_check.state.layers:
            on_failure("Empty layer name was allowed")
        else:
            on_success()  # Handled gracefully
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "empty" in error_msg or "name" in error_msg or "invalid" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


# ============================================================================
# BOUNDARY/EDGE CASE TESTS
# ============================================================================

def test_very_small_duration(on_success, on_failure):
    """Test: hold(1) - very small duration (1ms)"""
    try:
        rig = actions.user.mouse_rig()
        rig.layer("test").direction.to(1, 0).hold(1)

        # Should complete quickly
        def check_cleanup():
            rig_check = actions.user.mouse_rig()
            # Layer should be cleaned up after such short duration
            if len(rig_check.state.layers) == 0:
                on_success()
            else:
                on_failure("Layer still active after very short hold")

        cron.after("100ms", check_cleanup)
    except Exception as e:
        on_failure(f"Unexpected error with small duration: {e}")


def test_very_large_position(on_success, on_failure):
    """Test: pos.to(1000000, 1000000) - position far outside screen"""
    try:
        rig = actions.user.mouse_rig()
        rig.pos.to(1000000, 1000000)
        # Should clamp to screen bounds or handle gracefully
        # Just check it doesn't crash
        on_success()
    except Exception as e:
        on_failure(f"Error with large position: {e}")


def test_angle_normalization(on_success, on_failure):
    """Test: direction.by(720) - large angle should normalize"""
    try:
        rig = actions.user.mouse_rig()
        # 720 degrees = 2 full rotations = 0 degrees final
        rig.speed(3)
        rig.layer("test").direction.to(1, 0).hold(200)

        def rotate():
            rig_rotate = actions.user.mouse_rig()
            rig_rotate.direction.by(720).hold(400)

            def check_angle():
                rig_check = actions.user.mouse_rig()
                if len(rig_check.state.layers) == 0:
                    on_failure("Expected active layer")
                    return

                layer_state = list(rig_check.state.layers.values())[0]
                # Should still be facing right (0 degrees) after 720 degrees rotation
                from .direction import get_angle_from_vector, angle_difference
                actual_angle = get_angle_from_vector(layer_state.direction_x, layer_state.direction_y)

                if angle_difference(actual_angle, 0) < 5:
                    on_success()
                else:
                    on_failure(f"Angle not normalized correctly: {actual_angle} degrees, expected 0 degrees")

            cron.after("300ms", check_angle)

        cron.after("200ms", rotate)
    except Exception as e:
        on_failure(f"Error with large angle: {e}")


def test_invalid_layer_state_attribute(on_success, on_failure):
    """Test: accessing invalid attribute on layer state should give helpful error"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(3)
        rig.layer("test").direction.offset.by(90)

        actions.sleep("100ms")

        rig_check = actions.user.mouse_rig()
        layer_state = rig_check.state.layer("test")

        # Try to access invalid attribute
        _ = layer_state.direction_x

        on_failure("Expected AttributeError for invalid layer state attribute")
    except AttributeError as e:
        print(f"  Error message: {e}")
        error_msg = str(e)
        if "direction_x" in error_msg and "direction.x" in error_msg:
            on_success()
        else:
            on_failure(f"AttributeError raised but message not helpful: {e}")
    except Exception as e:
        on_failure(f"Wrong exception type: {type(e).__name__}: {e}")


# ============================================================================
# TEST REGISTRY
# ============================================================================

VALIDATION_TESTS = [
    ("multiple properties not allowed", test_multiple_properties_not_allowed),
    ("hold without operation", test_hold_without_operation),
    ("over without operation", test_over_without_operation),
    ("revert without operation", test_revert_without_operation),
    ("hold without revert", test_hold_without_revert),
    ("layer operation without mode", test_layer_operation_without_mode),
    ("zero direction vector", test_invalid_direction_vector_zero),
    ("negative duration", test_negative_duration),
    ("zero speed", test_invalid_speed_zero),
    ("negative speed", test_invalid_speed_negative),
    ("empty layer name", test_layer_empty_name),
    ("very small duration", test_very_small_duration),
    ("very large position", test_very_large_position),
    ("large angle normalization", test_angle_normalization),
    ("invalid layer state attribute", test_invalid_layer_state_attribute),
]
