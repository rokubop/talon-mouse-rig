"""Validation and Error tests for Mouse Rig

Tests for:
- Invalid operation sequences that should raise errors
- Error messages are clear and helpful
- Edge cases and boundary conditions
"""

from talon import actions, ctrl, cron


# Test configuration
CENTER_X = 960
CENTER_Y = 540


# ============================================================================
# VALIDATION TESTS
# ============================================================================

def test_multiple_properties_not_allowed(on_success, on_failure):
    """Test: rig.speed().direction.to() should error - cannot combine multiple properties"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(3).direction.to(1, 0).hold(1000)
        on_failure("Expected error but operation succeeded")
    except Exception as e:
        error_msg = str(e).lower()
        # Check if error message mentions combining properties or similar helpful info
        if "combine" in error_msg or "multiple" in error_msg or "cannot" in error_msg or "property" in error_msg or "properties" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_hold_without_layer(on_success, on_failure):
    """Test: rig.hold() without layer should error"""
    try:
        rig = actions.user.mouse_rig()
        rig.hold(1000)
        on_failure("Expected error but operation succeeded")
    except Exception as e:
        error_msg = str(e).lower()
        if "layer" in error_msg or "must" in error_msg or "cannot" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_direction_without_layer(on_success, on_failure):
    """Test: rig.direction.to() without layer should error"""
    try:
        rig = actions.user.mouse_rig()
        rig.direction.to(1, 0)
        on_failure("Expected error but operation succeeded")
    except Exception as e:
        error_msg = str(e).lower()
        if "layer" in error_msg or "must" in error_msg or "cannot" in error_msg:
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
        # If it errors, that's also acceptable
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
        rig.direction.to(1, 0).hold(500)
        on_failure("Expected error for hold() without revert() but operation succeeded")
    except Exception as e:
        error_msg = str(e).lower()
        if "hold" in error_msg or "revert" in error_msg or "requires" in error_msg or "must" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_layer_operation_without_mode(on_success, on_failure):
    """Test: layer operation without mode (.offset/.override/.scale) should error"""
    try:
        rig = actions.user.mouse_rig()
        rig.layer("test").speed.to(100)
        on_failure("Expected error for layer operation without mode but operation succeeded")
    except Exception as e:
        error_msg = str(e).lower()
        # Check if error mentions mode or provides helpful guidance
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
        error_msg = str(e).lower()
        if "zero" in error_msg or "invalid" in error_msg or "direction" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_negative_duration(on_success, on_failure):
    """Test: negative duration should error or be treated as 0"""
    try:
        rig = actions.user.mouse_rig()
        rig.pos.to(CENTER_X, CENTER_Y)
        rig.layer("test").hold(-500)
        # If it succeeds, check that it doesn't create a weird state
        actions.sleep("100ms")
        rig_check = actions.user.mouse_rig()
        # Should either error or handle gracefully
        on_success()  # If no crash, consider it handled
    except Exception as e:
        error_msg = str(e).lower()
        if "negative" in error_msg or "invalid" in error_msg or "duration" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_invalid_speed_zero(on_success, on_failure):
    """Test: speed(0) should error - invalid zero speed"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(0)
        rig.layer("test").direction.to(1, 0).hold(500)
        on_failure("Expected error for zero speed but operation succeeded")
    except Exception as e:
        error_msg = str(e).lower()
        if "speed" in error_msg or "zero" in error_msg or "invalid" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_invalid_speed_negative(on_success, on_failure):
    """Test: speed(-1) should error - invalid negative speed"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(-1)
        rig.layer("test").direction.to(1, 0).hold(500)
        on_failure("Expected error for negative speed but operation succeeded")
    except Exception as e:
        error_msg = str(e).lower()
        if "speed" in error_msg or "negative" in error_msg or "invalid" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


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
        error_msg = str(e).lower()
        if "empty" in error_msg or "name" in error_msg or "invalid" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


# ============================================================================
# BOUNDARY/EDGE CASE TESTS
# ============================================================================

def test_very_large_speed(on_success, on_failure):
    """Test: speed(1000000) - very large speed value"""
    try:
        rig = actions.user.mouse_rig()
        rig.pos.to(CENTER_X, CENTER_Y)
        actions.sleep("100ms")

        start_pos = ctrl.mouse_pos()
        rig.speed(1000000)
        rig.layer("test").direction.to(1, 0).hold(100)

        def check_moved():
            end_pos = ctrl.mouse_pos()
            # Should have moved very far or clamped to screen bounds
            if end_pos[0] > start_pos[0] + 100:  # Moved significantly
                on_success()
            else:
                on_failure(f"Very large speed didn't move mouse significantly: {start_pos} -> {end_pos}")

        cron.after("200ms", check_moved)
    except Exception as e:
        # If it errors with a reasonable message about speed limits, that's ok
        error_msg = str(e).lower()
        if "speed" in error_msg or "too large" in error_msg or "maximum" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_very_small_duration(on_success, on_failure):
    """Test: hold(1) - very small duration (1ms)"""
    try:
        rig = actions.user.mouse_rig()
        rig.pos.to(CENTER_X, CENTER_Y)
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

        actions.sleep("100ms")
        x, y = ctrl.mouse_pos()

        # Should clamp to screen bounds or handle gracefully
        # Just check it doesn't crash
        on_success()
    except Exception as e:
        on_failure(f"Error with large position: {e}")


def test_angle_normalization(on_success, on_failure):
    """Test: direction.by(720) - large angle should normalize"""
    try:
        rig = actions.user.mouse_rig()
        rig.pos.to(CENTER_X, CENTER_Y)
        actions.sleep("100ms")

        # 720° = 2 full rotations = 0° final
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
                # Should still be facing right (0°) after 720° rotation
                from .direction import get_angle_from_vector, angle_difference
                actual_angle = get_angle_from_vector(layer_state.direction_x, layer_state.direction_y)

                if angle_difference(actual_angle, 0) < 5:
                    on_success()
                else:
                    on_failure(f"Angle not normalized correctly: {actual_angle}°, expected 0°")

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
        error_msg = str(e)
        # Check if error message is helpful and mentions the correct way to access it
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
    ("hold without layer", test_hold_without_layer),
    ("direction without layer", test_direction_without_layer),
    ("over without operation", test_over_without_operation),
    ("revert without operation", test_revert_without_operation),
    ("hold without revert", test_hold_without_revert),
    ("layer operation without mode", test_layer_operation_without_mode),
    ("zero direction vector", test_invalid_direction_vector_zero),
    ("negative duration", test_negative_duration),
    ("zero speed", test_invalid_speed_zero),
    ("negative speed", test_invalid_speed_negative),
    ("empty layer name", test_layer_empty_name),
    ("very large speed", test_very_large_speed),
    ("very small duration", test_very_small_duration),
    ("very large position", test_very_large_position),
    ("large angle normalization", test_angle_normalization),
    ("invalid layer state attribute", test_invalid_layer_state_attribute),
]
