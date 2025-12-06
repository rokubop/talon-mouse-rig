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

def get_angle_from_vector(x, y):
    radians = math.atan2(y, x)
    degrees = math.degrees(radians)
    return degrees % 360


def angle_difference(angle1, angle2):
    diff = abs(angle1 - angle2)
    if diff > 180:
        diff = 360 - diff
    return diff


def check_velocity(start_pos, end_pos, expected_velocity_x, expected_velocity_y, tolerance=0.5):
    """Verify that velocity matches expected vector"""
    dx = end_pos[0] - start_pos[0]
    dy = end_pos[1] - start_pos[1]

    # Check if there was significant movement
    distance = math.sqrt(dx**2 + dy**2)
    if distance < MOVEMENT_TOLERANCE:
        return False, f"Insufficient movement: {distance:.1f} pixels"

    # Calculate actual velocity (approximate)
    time_elapsed = SAMPLE_INTERVAL_MS / 1000.0
    actual_vx = dx / (time_elapsed * 16.67)  # Approximate frame time
    actual_vy = dy / (time_elapsed * 16.67)

    # Check magnitude and direction roughly match
    expected_mag = math.sqrt(expected_velocity_x**2 + expected_velocity_y**2)
    actual_mag = math.sqrt(actual_vx**2 + actual_vy**2)

    if abs(expected_mag - actual_mag) / max(expected_mag, 1) > tolerance:
        return False, f"Velocity magnitude {actual_mag:.1f} differs from expected {expected_mag:.1f}"

    # Check direction if velocity is non-zero
    if expected_mag > 0.1:
        expected_angle = get_angle_from_vector(expected_velocity_x, expected_velocity_y)
        actual_angle = get_angle_from_vector(dx, dy)
        angle_diff = angle_difference(expected_angle, actual_angle)

        if angle_diff > 45:
            return False, f"Velocity angle {actual_angle:.1f}deg differs from expected {expected_angle:.1f}deg"

    return True, None


# ============================================================================
# BASIC VECTOR TESTS
# ============================================================================

def test_vector_to(on_success, on_failure):
    """Test: rig.vector.to(x, y) - set velocity directly"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Set velocity vector (speed=5, direction=right)
    rig.vector.to(5, 0)
    start_pos = ctrl.mouse_pos()

    def check_movement():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        # Check that speed and direction were set
        if abs(rig_check.state.speed - 5) > 1:
            on_failure(f"Speed is {rig_check.state.speed}, expected ~5")
            return

        # Check direction is right (1, 0)
        dir_x, dir_y = rig_check.state.direction.x, rig_check.state.direction.y
        if abs(dir_x - 1.0) > 0.1 or abs(dir_y) > 0.1:
            on_failure(f"Direction is ({dir_x:.2f}, {dir_y:.2f}), expected (1, 0)")
            return

        # Check actual movement
        dx = end_pos[0] - start_pos[0]
        if dx < MOVEMENT_TOLERANCE:
            on_failure(f"Expected rightward movement, only moved {dx}px")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


def test_vector_to_diagonal(on_success, on_failure):
    """Test: rig.vector.to(x, y) - set velocity diagonally"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Set velocity vector diagonal (3, 4) -> speed=5, direction=(0.6, 0.8)
    rig.vector.to(3, 4)
    start_pos = ctrl.mouse_pos()

    def check_movement():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        # Check that speed is magnitude of (3, 4) = 5
        expected_speed = math.sqrt(3**2 + 4**2)
        if abs(rig_check.state.speed - expected_speed) > 1:
            on_failure(f"Speed is {rig_check.state.speed}, expected ~{expected_speed:.1f}")
            return

        # Check direction is normalized (3, 4)
        expected_dir_x = 3 / expected_speed
        expected_dir_y = 4 / expected_speed
        dir_x, dir_y = rig_check.state.direction.x, rig_check.state.direction.y

        if abs(dir_x - expected_dir_x) > 0.1 or abs(dir_y - expected_dir_y) > 0.1:
            on_failure(f"Direction is ({dir_x:.2f}, {dir_y:.2f}), expected ({expected_dir_x:.2f}, {expected_dir_y:.2f})")
            return

        # Check actual movement direction
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = math.sqrt(dx**2 + dy**2)

        if distance < MOVEMENT_TOLERANCE:
            on_failure(f"Insufficient movement: {distance:.1f} pixels")
            return

        actual_angle = get_angle_from_vector(dx, dy)
        expected_angle = get_angle_from_vector(3, 4)

        if angle_difference(actual_angle, expected_angle) > 20:
            on_failure(f"Movement angle {actual_angle:.1f}deg differs from expected {expected_angle:.1f}deg")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


def test_vector_add(on_success, on_failure):
    """Test: rig.vector.add(x, y) - add velocity vector"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Start with velocity (2, 0)
    rig.vector.to(2, 0)
    actions.sleep("100ms")

    # Add velocity (0, 3) -> should result in (2, 3)
    rig.vector.add(0, 3)
    start_pos = ctrl.mouse_pos()

    def check_movement():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        # Check that resulting velocity is ~(2, 3)
        expected_speed = math.sqrt(2**2 + 3**2)  # ~3.6
        if abs(rig_check.state.speed - expected_speed) > 1.5:
            on_failure(f"Speed is {rig_check.state.speed}, expected ~{expected_speed:.1f}")
            return

        # Check direction
        expected_angle = get_angle_from_vector(2, 3)
        actual_angle = get_angle_from_vector(rig_check.state.direction.x, rig_check.state.direction.y)

        if angle_difference(actual_angle, expected_angle) > 20:
            on_failure(f"Direction angle {actual_angle:.1f}deg differs from expected {expected_angle:.1f}deg")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_movement)


def test_vector_to_over(on_success, on_failure):
    """Test: rig.vector.to(x, y).over(ms) - smooth velocity transition"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Start with velocity (5, 0)
    rig.vector.to(5, 0)
    actions.sleep("200ms")

    # Transition to velocity (0, 10) over 500ms
    rig.vector.to(0, 10).over(500)

    def check_final():
        rig_check = actions.user.mouse_rig()

        # After transition, should be moving down with speed ~10
        if abs(rig_check.state.speed - 10) > 1.5:
            on_failure(f"Final speed is {rig_check.state.speed}, expected ~10")
            return

        # Direction should be down (0, 1)
        dir_x, dir_y = rig_check.state.direction.x, rig_check.state.direction.y
        if abs(dir_y - 1.0) > 0.1 or abs(dir_x) > 0.1:
            on_failure(f"Final direction is ({dir_x:.2f}, {dir_y:.2f}), expected (0, 1)")
            return

        rig_check.stop()
        on_success()

    cron.after("700ms", check_final)


# ============================================================================
# LAYER VECTOR TESTS
# ============================================================================

def test_layer_vector_offset_add(on_success, on_failure):
    """Test: layer().vector.offset.add(x, y) - add velocity as separate force"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Base velocity: (3, 0) moving right
    rig.vector.to(3, 0)
    actions.sleep("100ms")

    # Add wind force: (0, 2) pushing down
    rig.layer("wind").vector.offset.add(0, 2)
    start_pos = ctrl.mouse_pos()

    def check_combined():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        # Combined velocity should be (3, 2)
        expected_speed = math.sqrt(3**2 + 2**2)  # ~3.6
        if abs(rig_check.state.speed - expected_speed) > 1.5:
            on_failure(f"Combined speed is {rig_check.state.speed}, expected ~{expected_speed:.1f}")
            return

        # Check movement direction is southeast-ish
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]

        if dx < 50 or dy < 20:
            on_failure(f"Expected right-down movement, got dx={dx}, dy={dy}")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_combined)


def test_layer_vector_offset_multiple(on_success, on_failure):
    """Test: Multiple offset layers compose as independent forces"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Base: no movement - test pure offset composition
    # (don't set base velocity, layers should start the rig)

    # Force 1: Wind pushing right (2, 0)
    rig.layer("wind").vector.offset.add(2, 0)

    # Force 2: Gravity pulling down (0, 3)
    rig.layer("gravity").vector.offset.add(0, 3)

    # # Force 3: Drift pushing left-up (-1, -1)
    # rig.layer("drift").vector.offset.add(-1, -1)

    actions.sleep("100ms")
    start_pos = ctrl.mouse_pos()

    def check_combined():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        # Combined: (2, 0) + (0, 3) = (2, 3)
        expected_speed = math.sqrt(2**2 + 3**2)  # ~3.6
        if abs(rig_check.state.speed - expected_speed) > 1.5:
            on_failure(f"Combined speed is {rig_check.state.speed}, expected ~{expected_speed:.1f}")
            return

        # Check movement is generally right-down
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]

        if dx < 20 or dy < 30:
            on_failure(f"Expected right-down movement, got dx={dx}, dy={dy}")
            return

        rig_check.stop()
        on_success()

    cron.after("500ms", check_combined)


def test_layer_vector_override(on_success, on_failure):
    """Test: layer().vector.override.to(x, y) - override velocity"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Base velocity: (5, 0) moving right fast
    rig.vector.to(5, 0)
    actions.sleep("100ms")

    # Override with slow upward movement
    rig.layer("override").vector.override.to(0, 2)
    start_pos = ctrl.mouse_pos()

    def check_override():
        end_pos = ctrl.mouse_pos()
        rig_check = actions.user.mouse_rig()

        # Should be moving up with speed ~2 (base ignored)
        if abs(rig_check.state.speed - 2) > 1:
            on_failure(f"Speed is {rig_check.state.speed}, expected ~2")
            return

        # Check direction is up (0, 1)
        dir_x, dir_y = rig_check.state.direction.x, rig_check.state.direction.y
        if abs(dir_y - 1.0) > 0.2 or abs(dir_x) > 0.2:
            on_failure(f"Direction is ({dir_x:.2f}, {dir_y:.2f}), expected (0, 1)")
            return

        # Check actual movement is upward
        dy = end_pos[1] - start_pos[1]
        if dy < 20:
            on_failure(f"Expected upward movement, got dy={dy}")
            return

        rig_check.stop()
        on_success()

    cron.after("400ms", check_override)


def test_layer_vector_revert(on_success, on_failure):
    """Test: layer().vector revert removes force"""
    rig = actions.user.mouse_rig()
    rig.pos.to(CENTER_X, CENTER_Y)
    rig.stop()
    actions.sleep("100ms")

    # Base velocity: (3, 0) moving right
    rig.vector.to(3, 0)

    # Add boost force: (2, 0) for extra speed
    rig.layer("boost").vector.offset.add(2, 0)

    def check_during_boost():
        rig_check = actions.user.mouse_rig()
        # Should be faster: (3, 0) + (2, 0) = (5, 0)
        if abs(rig_check.state.speed - 5) > 1.5:
            on_failure(f"Speed during boost is {rig_check.state.speed}, expected ~5")
            return

        # Now revert the boost
        rig_check.layer("boost").revert(200)

        def check_after_revert():
            rig_final = actions.user.mouse_rig()
            # Should be back to base: speed ~3
            if abs(rig_final.state.speed - 3) > 1:
                on_failure(f"Speed after revert is {rig_final.state.speed}, expected ~3")
                return

            rig_final.stop()
            on_success()

        cron.after("300ms", check_after_revert)

    cron.after("400ms", check_during_boost)


# ============================================================================
# TEST SUITE
# ============================================================================

VECTOR_TESTS = [
    ("vector.to(x, y)", test_vector_to),
    ("vector.to(x, y) diagonal", test_vector_to_diagonal),
    ("vector.add(x, y)", test_vector_add),
    ("vector.to(x, y).over(ms)", test_vector_to_over),
    ("layer vector.offset.add(x, y)", test_layer_vector_offset_add),
    ("layer vector multiple forces", test_layer_vector_offset_multiple),
    ("layer vector.override.to(x, y)", test_layer_vector_override),
    ("layer vector revert", test_layer_vector_revert),
]
