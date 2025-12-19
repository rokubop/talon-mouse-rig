"""Quick test to verify constraint refactor works"""
from talon import actions

def test_constraint_chaining():
    """Test that new chaining API works"""
    print("\n=== Testing Constraint Chaining ===\n")

    rig = actions.user.mouse_rig()
    rig.stop()

    # Test 1: mul with max
    print("Test 1: speed.mul(4).max(10)")
    rig.speed.to(3)
    rig.speed.mul(4).max(10)  # 3 * 4 = 12, capped at 10

    # Give it a moment to apply
    actions.sleep("50ms")

    rig_check = actions.user.mouse_rig()
    print(f"  Base speed: 3")
    print(f"  After mul(4).max(10): {rig_check.state.speed}")
    print(f"  Expected: 10 (3 * 4 = 12, capped)")

    if abs(rig_check.state.speed - 10) < 1:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")

    # Test 2: add with min
    print("\nTest 2: speed.add(-10).min(2)")
    rig.speed.to(5)
    rig.speed.add(-10).min(2)  # 5 + -10 = -5, floored at 2

    actions.sleep("50ms")

    rig_check = actions.user.mouse_rig()
    print(f"  Base speed: 5")
    print(f"  After add(-10).min(2): {rig_check.state.speed}")
    print(f"  Expected: 2 (5 + -10 = -5, floored)")

    if abs(rig_check.state.speed - 2) < 1:
        print("  ✓ PASS")
    else:
        print("  ✗ FAIL")

    # Test 3: chaining order flexibility
    print("\nTest 3: speed.add(10).max(12).over(300)")
    rig.speed.to(5)
    rig.speed.add(10).max(12).over(300)  # Chain max before over

    actions.sleep("50ms")

    rig_check = actions.user.mouse_rig()
    print(f"  Base speed: 5")
    print(f"  After add(10).max(12).over(300): {rig_check.state.speed}")
    print(f"  Expected: transitioning towards 12")

    if rig_check.state.speed > 5 and rig_check.state.speed <= 12:
        print("  ✓ PASS (transitioning)")
    else:
        print("  ✗ FAIL")

    rig.stop()
    print("\n=== Tests Complete ===\n")

# Run test
test_constraint_chaining()
