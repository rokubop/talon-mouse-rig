from talon import actions, ctrl, cron
from .direction import get_angle_from_vector, angle_difference

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
    """Test: negative duration should error"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed.to(5).over(-500)
        on_failure("Expected error for negative duration but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "negative" in error_msg or "duration" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_layer_empty_name(on_success, on_failure):
    """Test: layer("") with empty string should error or handle gracefully"""
    try:
        rig = actions.user.mouse_rig()
        rig.layer('').direction.override.to(1, 0)
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
        print(f"  Error message: {e}")
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
        print(f"  Error message: {e}")
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
                actual_angle = get_angle_from_vector(layer_state.direction_x, layer_state.direction_y)

                if angle_difference(actual_angle, 0) < 5:
                    on_success()
                else:
                    on_failure(f"Angle not normalized correctly: {actual_angle} degrees, expected 0 degrees")

            cron.after("300ms", check_angle)

        cron.after("200ms", rotate)
    except Exception as e:
        print(f"  Error message: {e}")
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
        if "direction_x" in error_msg and "Available attributes" in error_msg:
            on_success()
        else:
            on_failure(f"AttributeError raised but message not helpful: {e}")
    except Exception as e:
        on_failure(f"Wrong exception type: {type(e).__name__}: {e}")


def test_duplicate_operator_calls(on_success, on_failure):
    """Test: calling .to().to() should error - duplicate operators not allowed"""
    try:
        rig = actions.user.mouse_rig()
        builder = rig.speed.to(5).to(10)
        on_failure("Expected error for duplicate operator calls but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "operator" in error_msg or "already" in error_msg or "duplicate" in error_msg or "cannot" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_duplicate_by_calls(on_success, on_failure):
    """Test: calling .by().by() should error - duplicate operators not allowed"""
    try:
        rig = actions.user.mouse_rig()
        builder = rig.direction.by(45).by(90)
        on_failure("Expected error for duplicate .by() calls but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "operator" in error_msg or "already" in error_msg or "duplicate" in error_msg or "cannot" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_mixed_operators(on_success, on_failure):
    """Test: calling .to().add() should error - cannot mix operators"""
    try:
        rig = actions.user.mouse_rig()
        builder = rig.speed.to(5).add(3)
        on_failure("Expected error for mixed operators but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "operator" in error_msg or "already" in error_msg or "cannot" in error_msg:
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_layer_without_mode(on_success, on_failure):
    """Test: layer("name").speed.to(100) without .offset/.override/.scale should error"""
    try:
        rig = actions.user.mouse_rig()
        builder = rig.layer("test").speed.to(100)
        builder._execute()  # Force execution to catch validation error
        on_failure("Expected error for layer without mode but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "mode" in error_msg and ("offset" in error_msg or "override" in error_msg or "scale" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_layer_direction_without_mode(on_success, on_failure):
    """Test: layer("name").direction.to() without mode should error"""
    try:
        rig = actions.user.mouse_rig()
        builder = rig.layer("test").direction.to(1, 0)
        builder._execute()  # Force execution to catch validation error
        on_failure("Expected error for layer direction without mode but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "mode" in error_msg and ("offset" in error_msg or "override" in error_msg or "scale" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_vector_zero_zero(on_success, on_failure):
    """Test: vector.to(0, 0) should error - invalid zero vector"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(5)
        rig.direction.to(1, 0)
        rig.vector.to(0, 0)
        on_failure("Expected error for zero vector but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if ("zero" in error_msg or "invalid" in error_msg) and ("stop" in error_msg or "speed.to(0)" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_position_zero_zero(on_success, on_failure):
    """Test: pos.to(0, 0) should be allowed (moves to origin)"""
    try:
        rig = actions.user.mouse_rig()
        rig.pos.to(0, 0)

        actions.sleep("50ms")

        # Position operations are instant, so check immediately
        x, y = ctrl.mouse_pos()
        if abs(x) < 2 and abs(y) < 2:
            on_success()
        else:
            on_failure(f"Expected position ~(0, 0), got ({x}, {y})")
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error: {e}")


def test_duplicate_mode_specification(on_success, on_failure):
    """Test: layer().direction.offset.override.to() - duplicate mode should error"""
    try:
        rig = actions.user.mouse_rig()
        # This should error - can't specify both offset and override
        rig.layer("test").direction.offset.override.to(1, 0)
        on_failure("Expected error for duplicate mode specification but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "mode" in error_msg and ("only one" in error_msg or "duplicate" in error_msg or "already" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


def test_accessing_property_as_value(on_success, on_failure):
    """Test: rig.speed used as a value should give helpful error"""
    try:
        rig = actions.user.mouse_rig()
        rig.speed(5)

        # Try multiple scenarios that should all error with helpful message
        rig_check = actions.user.mouse_rig()

        # Test 1: print/str conversion
        try:
            _ = str(rig_check.speed)
            on_failure("str(rig.speed) should have errored")
            return
        except Exception as e:
            print(f"    str() error: {e}")
            if "rig.state.speed" not in str(e):
                on_failure(f"str(rig.speed) error not helpful: {e}")
                return

        # Test 2: multiplication
        try:
            _ = rig_check.speed * 2
            on_failure("rig.speed * 2 should have errored")
            return
        except Exception as e:
            print(f"    multiplication error: {e}")
            if "rig.state.speed" not in str(e):
                on_failure(f"rig.speed * 2 error not helpful: {e}")
                return

        # Test 3: addition
        try:
            _ = rig_check.speed + 5
            on_failure("rig.speed + 5 should have errored")
            return
        except Exception as e:
            print(f"    addition error: {e}")
            if "rig.state.speed" not in str(e):
                on_failure(f"rig.speed + 5 error not helpful: {e}")
                return

        # Test 4: abs()
        try:
            _ = abs(rig_check.speed)
            on_failure("abs(rig.speed) should have errored")
            return
        except Exception as e:
            print(f"    abs() error: {e}")
            if "rig.state.speed" not in str(e):
                on_failure(f"abs(rig.speed) error not helpful: {e}")
                return

        on_success()
    except Exception as e:
        print(f"  Error message: {e}")
        on_failure(f"Unexpected error in test setup: {e}")


def test_api_without_operation(on_success, on_failure):
    """Test: calling .api() without an operation should error"""
    try:
        rig = actions.user.mouse_rig()
        builder = rig.api("talon")
        builder._execute()  # Force execution to catch validation error
        on_failure("Expected error but operation succeeded")
    except Exception as e:
        print(f"  Error message: {e}")
        error_msg = str(e).lower()
        if "api" in error_msg and ("operation" in error_msg or "chained" in error_msg):
            on_success()
        else:
            on_failure(f"Error occurred but message unclear: {e}")


# ============================================================================
# TEST REGISTRY
# ============================================================================

VALIDATION_TESTS = [
    ("multiple properties not allowed", test_multiple_properties_not_allowed),
    ("hold without operation", test_hold_without_operation),
    ("over without operation", test_over_without_operation),
    ("revert without operation", test_revert_without_operation),
    ("layer operation without mode", test_layer_operation_without_mode),
    ("zero direction vector", test_invalid_direction_vector_zero),
    ("negative duration", test_negative_duration),
    ("empty layer name", test_layer_empty_name),
    ("invalid layer state attribute", test_invalid_layer_state_attribute),
    ("duplicate operator calls (.to.to)", test_duplicate_operator_calls),
    ("duplicate .by() calls", test_duplicate_by_calls),
    ("mixed operators (.to.add)", test_mixed_operators),
    ("layer without mode (speed)", test_layer_without_mode),
    ("layer without mode (direction)", test_layer_direction_without_mode),
    ("zero vector not allowed", test_vector_zero_zero),
    ("pos.to(0, 0) allowed", test_position_zero_zero),
    ("duplicate mode specification", test_duplicate_mode_specification),
    ("accessing property as value", test_accessing_property_as_value),
    ("api without operation", test_api_without_operation),
]
