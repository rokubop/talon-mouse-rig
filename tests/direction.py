from talon import actions, ctrl, cron
import math

CENTER_X = 960
CENTER_Y = 540
TEST_SPEED = 3
SAMPLE_INTERVAL_MS = 200
MOVEMENT_TOLERANCE = 50

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_angle(degrees):
    return degrees % 360


def get_angle_from_vector(x, y):
    radians = math.atan2(y, x)
    degrees = math.degrees(radians)
    return normalize_angle(degrees)


def angle_difference(angle1, angle2):
    diff = abs(angle1 - angle2)
    if diff > 180:
        diff = 360 - diff
    return diff


def check_movement_direction(start_pos, end_pos, expected_angle, tolerance_degrees=45):
    """Verify that movement from start to end is roughly in the expected direction"""
    dx = end_pos[0] - start_pos[0]
    dy = end_pos[1] - start_pos[1]

    # Check if there was significant movement
    distance = math.sqrt(dx**2 + dy**2)
    if distance < MOVEMENT_TOLERANCE:
        return False, f"Insufficient movement: {distance:.1f} pixels"

    actual_angle = get_angle_from_vector(dx, dy)
    angle_diff = angle_difference(actual_angle, expected_angle)

    if angle_diff <= tolerance_degrees:
        return True, None
    else:
        return False, f"Movement angle {actual_angle:.1f}deg differs from expected {expected_angle:.1f}deg by {angle_diff:.1f}deg"


# ============================================================================
# BASIC DIRECTION TESTS
# ============================================================================

def test_direction_to(on_success, on_failure):
    """Test: rig.direction.to(x, y) - set direction via vector"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    start_pos = ctrl.mouse_pos()
    expected_angle = 0

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)

    def check_movement():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no layers but got: {rig_check.state.layers}")
            return

        actual_angle = get_angle_from_vector(rig_check.state.direction.x, rig_check.state.direction.y)

        if angle_difference(actual_angle, expected_angle) > 5:
            on_failure(f"Direction in state is {actual_angle:.1f}deg, expected {expected_angle}deg")
            return

        success, error = check_movement_direction(start_pos, end_pos, expected_angle)
        if not success:
            on_failure(f"Movement check failed: {error}")
            return

        on_success()

    cron.after("600ms", check_movement)


def test_direction_to_over(on_success, on_failure):
    """Test: rig.direction.to(x, y).over(ms) - smooth rotation to direction"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)

    def start_rotation():
        rig_rotate = actions.user.mouse_rig()
        rig_rotate.direction.to(0, 1).over(500)

        def check_final_direction():
            rig_check = actions.user.mouse_rig()
            if len(rig_check.state.layers) != 0:
                on_failure(f"Expected no layers but got: {rig_check.state.layers}")
                return

            actual_angle = get_angle_from_vector(rig_check.state.direction.x, rig_check.state.direction.y)
            expected_angle = 90

            if angle_difference(actual_angle, expected_angle) > 5:
                on_failure(f"Direction after rotation is {actual_angle:.1f}deg, expected {expected_angle}deg")
                return

            on_success()

        cron.after("800ms", check_final_direction)

    cron.after("300ms", start_rotation)


def test_direction_by(on_success, on_failure):
    """Test: rig.direction.by(degrees) - rotate by degrees instantly"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    start_pos = ctrl.mouse_pos()

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)

    def rotate_and_check():
        rig_rotate = actions.user.mouse_rig()
        rig_rotate.direction.by(90)

        def check_movement():
            end_pos = ctrl.mouse_pos()
            rig_check = actions.user.mouse_rig()

            if len(rig_check.state.layers) != 0:
                on_failure(f"Expected no layers but got: {rig_check.state.layers}")
                return

            actual_angle = get_angle_from_vector(rig_check.state.direction.x, rig_check.state.direction.y)
            expected_angle = 90

            if angle_difference(actual_angle, expected_angle) > 5:
                on_failure(f"Direction after rotation is {actual_angle:.1f}deg, expected {expected_angle}deg")
                return

            mid_pos = (start_pos[0] + 100, start_pos[1])
            success, error = check_movement_direction(mid_pos, end_pos, expected_angle, tolerance_degrees=60)
            if not success:
                on_failure(f"Movement check after rotation failed: {error}")
                return

            on_success()

        cron.after("400ms", check_movement)

    cron.after("200ms", rotate_and_check)


def test_direction_by_over(on_success, on_failure):
    """Test: rig.direction.by(degrees).over(ms) - smooth rotation by degrees"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)

    def start_rotation():
        rig_rotate = actions.user.mouse_rig()
        rig_rotate.direction.by(-90).over(500)

        def check_final_direction():
            rig_check = actions.user.mouse_rig()
            if len(rig_check.state.layers) != 0:
                on_failure(f"Expected no layers but got: {rig_check.state.layers}")
                return

            actual_angle = get_angle_from_vector(rig_check.state.direction.x, rig_check.state.direction.y)
            expected_angle = 270

            if angle_difference(actual_angle, expected_angle) > 5:
                on_failure(f"Direction after rotation is {actual_angle:.1f}deg, expected {expected_angle}deg")
                return

            on_success()

        cron.after("800ms", check_final_direction)

    cron.after("300ms", start_rotation)


def test_direction_add(on_success, on_failure):
    """Test: rig.direction.add(degrees) - add degrees to current direction"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)

    def add_rotation():
        rig_add = actions.user.mouse_rig()
        rig_add.direction.add(45)

        def add_again():
            rig_add2 = actions.user.mouse_rig()
            rig_add2.direction.add(45)

            def check_final():
                rig_check = actions.user.mouse_rig()
                if len(rig_check.state.layers) != 0:
                    on_failure(f"Expected no layers but got: {rig_check.state.layers}")
                    return

                actual_angle = get_angle_from_vector(rig_check.state.direction.x, rig_check.state.direction.y)
                expected_angle = 90

                if angle_difference(actual_angle, expected_angle) > 5:
                    on_failure(f"Direction after adds is {actual_angle:.1f}deg, expected {expected_angle}deg")
                    return

                on_success()

            cron.after("300ms", check_final)

        cron.after("200ms", add_again)

    cron.after("200ms", add_rotation)


def test_direction_add_vector(on_success, on_failure):
    """Test: rig.direction.add(x, y) - add vector to current direction"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)

    def add_vector():
        rig_add = actions.user.mouse_rig()
        rig_add.direction.add(0, 1)

        def check_final():
            rig_check = actions.user.mouse_rig()
            if len(rig_check.state.layers) != 0:
                on_failure(f"Expected no layers but got: {rig_check.state.layers}")
                return

            actual_angle = get_angle_from_vector(rig_check.state.direction.x, rig_check.state.direction.y)
            expected_angle = 45

            if angle_difference(actual_angle, expected_angle) > 5:
                on_failure(f"Direction after add vector is {actual_angle:.1f}deg, expected {expected_angle}deg")
                return

            on_success()

        cron.after("400ms", check_final)

    cron.after("200ms", add_vector)


# ============================================================================
# LAYER DIRECTION TESTS
# ============================================================================

def test_layer_direction_offset_by(on_success, on_failure):
    """Test: layer().direction.offset.by(degrees) - layer direction offset"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)  # Base: 0deg
    rig.layer("wind").direction.offset.by(90)  # Offset: +90deg

    def check_result():
        rig_check = actions.user.mouse_rig()

        if "wind" not in rig_check.state.layers:
            on_failure("Expected 'wind' layer but not found")
            return

        # Check overall rig direction (should be pointing down/right at 90deg)
        direction = rig_check.state.direction
        if abs(direction.x) > 0.1 or abs(direction.y - 1.0) > 0.1:
            on_failure(f"Rig direction is ({direction.x:.2f}, {direction.y:.2f}), expected (0, 1)")
            return

        # Check layer properties
        layer_state = rig_check.state.layer("wind")
        if layer_state.mode != "offset":
            on_failure(f"Layer mode is '{layer_state.mode}', expected 'offset'")
            return

        if layer_state.current_value != 90:
            on_failure(f"Layer value is {layer_state.current_value}, expected 90")
            return

        on_success()

    cron.after("300ms", check_result)


def test_layer_direction_offset_by_over(on_success, on_failure):
    """Test: layer().direction.offset.by(degrees).over(ms) - smooth layer offset rotation"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)
    rig.layer("wind").direction.offset.by(180).over(500)

    def check_final_direction():
        rig_check = actions.user.mouse_rig()

        if "wind" not in rig_check.state.layers:
            on_failure("Expected 'wind' layer but not found")
            return

        # Check overall rig direction (should be pointing left at 180deg)
        direction = rig_check.state.direction
        if abs(direction.x + 1.0) > 0.1 or abs(direction.y) > 0.1:
            on_failure(f"Rig direction is ({direction.x:.2f}, {direction.y:.2f}), expected (-1, 0)")
            return

        # Check layer properties
        layer_state = rig_check.state.layer("wind")
        if layer_state.mode != "offset":
            on_failure(f"Layer mode is '{layer_state.mode}', expected 'offset'")
            return

        if layer_state.current_value != 180:
            on_failure(f"Layer value is {layer_state.current_value}, expected 180")
            return

        on_success()

    cron.after("800ms", check_final_direction)


def test_layer_direction_offset_add_vector(on_success, on_failure):
    """Test: layer().direction.offset.add(x, y) - add vector to layer direction offset"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    start_pos = ctrl.mouse_pos()

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)
    rig.layer("wind").direction.offset.add(0, 1)

    def check_movement():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        if "wind" not in rig_check.state.layers:
            on_failure("Expected 'wind' layer but not found")
            return

        # Check overall rig direction (base (1,0) + offset (0,1) normalized = (0.71, 0.71))
        direction = rig_check.state.direction
        expected_x, expected_y = 0.707, 0.707
        if abs(direction.x - expected_x) > 0.1 or abs(direction.y - expected_y) > 0.1:
            on_failure(f"Rig direction is ({direction.x:.2f}, {direction.y:.2f}), expected ({expected_x:.2f}, {expected_y:.2f})")
            return

        # Check layer properties
        layer_state = rig_check.state.layer("wind")
        if layer_state.mode != "offset":
            on_failure(f"Layer mode is '{layer_state.mode}', expected 'offset'")
            return

        success, error = check_movement_direction(start_pos, end_pos, 45, tolerance_degrees=60)
        if not success:
            on_failure(f"Movement check failed: {error}")
            return

        on_success()

    cron.after("600ms", check_movement)


def test_layer_direction_override_to(on_success, on_failure):
    """Test: layer().direction.override.to(x, y) - layer absolute direction"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    start_pos = ctrl.mouse_pos()

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)
    rig.layer("wind").direction.override.to(0, -1)

    def check_movement():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        if "wind" not in rig_check.state.layers:
            on_failure("Expected 'wind' layer but not found")
            return

        # Check overall rig direction (should be overridden to up at 270deg)
        direction = rig_check.state.direction
        if abs(direction.x) > 0.1 or abs(direction.y + 1.0) > 0.1:
            on_failure(f"Rig direction is ({direction.x:.2f}, {direction.y:.2f}), expected (0, -1)")
            return

        # Check layer properties
        layer_state = rig_check.state.layer("wind")
        if layer_state.mode != "override":
            on_failure(f"Layer mode is '{layer_state.mode}', expected 'override'")
            return

        success, error = check_movement_direction(start_pos, end_pos, 270)
        if not success:
            on_failure(f"Movement check failed: {error}")
            return

        on_success()

    cron.after("600ms", check_movement)


def test_layer_direction_override_to_over(on_success, on_failure):
    """Test: layer().direction.override.to(x, y).over(ms) - smooth layer override rotation"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)
    rig.layer("wind").direction.override.to(1, 0)

    def start_override():
        rig_override = actions.user.mouse_rig()
        rig_override.layer("wind").direction.override.to(0, 1).over(500)

        def check_final_direction():
            rig_check = actions.user.mouse_rig()

            if "wind" not in rig_check.state.layers:
                on_failure("Expected 'wind' layer but not found")
                return

            # Check overall rig direction (should be down at 90deg)
            direction = rig_check.state.direction
            if abs(direction.x) > 0.1 or abs(direction.y - 1.0) > 0.1:
                on_failure(f"Rig direction is ({direction.x:.2f}, {direction.y:.2f}), expected (0, 1)")
                return

            # Check layer properties
            layer_state = rig_check.state.layer("wind")
            if layer_state.mode != "override":
                on_failure(f"Layer mode is '{layer_state.mode}', expected 'override'")
                return

            on_success()

        cron.after("800ms", check_final_direction)

    cron.after("300ms", start_override)


def test_layer_direction_override_to_over_revert(on_success, on_failure):
    """Test: layer().direction.override.to(x, y).over(ms).revert(ms) - override with revert"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    rig.speed(TEST_SPEED)
    rig.direction.to(0, 1)
    rig.layer("wind").direction.override.to(1, 0).over(500).hold(300).revert(500)

    def check_during_override():
        rig_check = actions.user.mouse_rig()

        if "wind" not in rig_check.state.layers:
            on_failure("Expected 'wind' layer during override")
            return

        # Check overall rig direction during override (should be right at 0deg)
        direction = rig_check.state.direction
        if abs(direction.x - 1.0) > 0.1 or abs(direction.y) > 0.1:
            on_failure(f"Rig direction during override is ({direction.x:.2f}, {direction.y:.2f}), expected (1, 0)")
            return

        # Check layer properties
        layer_state = rig_check.state.layer("wind")
        if layer_state.mode != "override":
            on_failure(f"Layer mode is '{layer_state.mode}', expected 'override'")
            return

        def check_after_revert():
            rig_check2 = actions.user.mouse_rig()

            # Check rig direction after revert (should be back to base: down at 90deg)
            direction2 = rig_check2.state.direction
            if abs(direction2.x) > 0.1 or abs(direction2.y - 1.0) > 0.1:
                on_failure(f"Rig direction after revert is ({direction2.x:.2f}, {direction2.y:.2f}), expected (0, 1)")
                return

            on_success()

        cron.after("700ms", check_after_revert)

    cron.after("700ms", check_during_override)


def test_layer_direction_with_callbacks(on_success, on_failure):
    """Test: layer().direction.override.to().over().then().hold().then().revert().then()"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    actions.sleep("100ms")

    callback_order = []

    def callback1():
        callback_order.append("after_over")

    def callback2():
        callback_order.append("after_hold")

    def callback3():
        callback_order.append("after_revert")

    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)
    rig.layer("wind").direction.override.to(0, 1).over(300).then(callback1).hold(300).then(callback2).revert(300).then(callback3)

    def check_callbacks():
        expected_order = ["after_over", "after_hold", "after_revert"]
        if callback_order != expected_order:
            on_failure(f"Callback order is {callback_order}, expected {expected_order}")
            return

        rig_check = actions.user.mouse_rig()
        if len(rig_check.state.layers) != 0:
            on_failure(f"Expected no active layers, got: {rig_check.state.layers}")
            return

        on_success()

    cron.after("1200ms", check_callbacks)


# ============================================================================
# DIRECTION REVERSAL / INVERSION TESTS
# ============================================================================

def test_direction_reverse_180_over_time(on_success, on_failure):
    """Test: rig.direction.to(-x, -y).over(ms) - 180° reversal should be smooth"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Start moving right
    rig.speed(TEST_SPEED)
    rig.direction.to(1, 0)  # 0° (right)
    actions.sleep("200ms")
    start_pos = ctrl.mouse_pos()

    # Reverse direction over time (180° turn)
    rig.direction.to(-1, 0).over(500)  # Should rotate to 180° (left)

    def check_midpoint():
        """During rotation - should be transitioning"""
        mid_pos = ctrl.mouse_pos()

        # Should have some rightward movement initially
        dx = mid_pos[0] - start_pos[0]
        if dx < 5:
            on_failure(f"Expected some rightward movement during transition, got dx={dx}")
            return

        def check_final():
            """After rotation completes - should be moving left"""
            rig_final = actions.user.mouse_rig()
            end_pos = ctrl.mouse_pos()

            # Direction should be left (-1, 0)
            dir_x, dir_y = rig_final.state.direction.x, rig_final.state.direction.y
            if abs(dir_x - (-1.0)) > 0.1 or abs(dir_y) > 0.1:
                on_failure(f"Final direction wrong: expected (-1, 0), got ({dir_x:.2f}, {dir_y:.2f})")
                return

            # Should be moving left now
            dx_final = end_pos[0] - mid_pos[0]
            if dx_final > -5:
                on_failure(f"Expected leftward movement after reversal, got dx={dx_final}")
                return

            rig_final.stop()
            on_success()

        cron.after("400ms", check_final)

    cron.after("300ms", check_midpoint)


def test_reverse_method_instant(on_success, on_failure):
    """Test: rig.reverse() - instant 180° turn"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Start moving right
    rig.speed(TEST_SPEED)
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


def test_reverse_method_over_time(on_success, on_failure):
    """Test: rig.reverse(ms) - smooth 180° turn over time through zero"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Start moving right at speed 3
    rig.speed(TEST_SPEED)
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
# TEST REGISTRY
# ============================================================================

DIRECTION_TESTS = [
    ("direction.to(x, y)", test_direction_to),
    ("direction.to(x, y).over(ms)", test_direction_to_over),
    ("direction.by(degrees)", test_direction_by),
    ("direction.by(degrees).over(ms)", test_direction_by_over),
    ("direction.add(degrees)", test_direction_add),
    ("direction.add(x, y)", test_direction_add_vector),
    ("layer direction.offset.by(degrees)", test_layer_direction_offset_by),
    ("layer direction.offset.by(degrees).over(ms)", test_layer_direction_offset_by_over),
    ("layer direction.offset.add(x, y)", test_layer_direction_offset_add_vector),
    ("layer direction.override.to(x, y)", test_layer_direction_override_to),
    ("layer direction.override.to(x, y).over(ms)", test_layer_direction_override_to_over),
    ("layer direction.override.to().over().revert()", test_layer_direction_override_to_over_revert),
    ("layer direction with callbacks", test_layer_direction_with_callbacks),
    ("direction 180° reversal over time", test_direction_reverse_180_over_time),
    ("reverse() instant", test_reverse_method_instant),
    ("reverse(ms) over time", test_reverse_method_over_time),
]
