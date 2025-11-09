"""
Test property chaining functionality

This file tests the new property chaining feature where you can do:
    rig.speed(4).accel(3).direction(1, 0)

But NOT mix timing with chaining:
    rig.speed(4).over(100).accel(3)  # ERROR
    rig.speed(4).accel(3).over(100)  # ERROR
"""

# These should work (chaining without timing)
def test_basic_chaining():
    rig = actions.user.mouse_rig()
    
    # Chain speed and accel
    rig.speed(4).accel(3)
    
    # Chain speed, accel, and direction
    rig.speed(5).accel(2).direction(1, 0)
    
    # Chain all properties
    rig.speed(10).accel(5).direction(0, 1).pos.to(500, 500)
    
    # Different order
    rig.direction(1, 1).speed(8).accel(4)


# These should fail with helpful errors
def test_timing_before_chain():
    rig = actions.user.mouse_rig()
    
    try:
        # Timing in middle, then chain - should fail
        rig.speed(4).over(100).accel(3)
        print("ERROR: Should have raised AttributeError")
    except AttributeError as e:
        print(f"✓ Correctly blocked timing before chain: {e}")


def test_timing_after_chain():
    rig = actions.user.mouse_rig()
    
    try:
        # Chain, then timing at end - should fail
        rig.speed(4).accel(3).over(100)
        print("ERROR: Should have raised AttributeError")
    except AttributeError as e:
        print(f"✓ Correctly blocked timing after chain: {e}")


def test_direction_timing_chain():
    rig = actions.user.mouse_rig()
    
    try:
        # Direction with .over() then chain
        rig.direction(1, 0).over(500).speed(10)
        print("ERROR: Should have raised AttributeError")
    except AttributeError as e:
        print(f"✓ Correctly blocked direction timing + chain: {e}")


def test_position_timing_chain():
    rig = actions.user.mouse_rig()
    
    try:
        # Position with .over() then chain
        rig.pos.to(100, 100).over(500).speed(5)
        print("ERROR: Should have raised AttributeError")
    except AttributeError as e:
        print(f"✓ Correctly blocked position timing + chain: {e}")


# Valid separate statements (these should always work)
def test_separate_statements():
    rig = actions.user.mouse_rig()
    
    # This is the correct way to use timing
    rig.speed(4).over(100)
    rig.accel(3).over(200)
    
    # Or chain without timing
    rig.speed(5).accel(2)
