"""Test state repr output for RigState, BaseState, and LayerState"""
from talon import actions
import time

def test_rig_state_empty():
    """Test RigState repr with no animations"""
    rig = actions.user.mouse_rig()
    rig.stop()
    print("\nRigState (empty):")
    print(rig.state)

    print("\nIndividual property access:")
    print(f"rig.state.pos = {rig.state.pos}")
    print(f"rig.state.pos.value = {rig.state.pos.value}")
    print(f"rig.state.pos.target = {rig.state.pos.target}")
    print(f"rig.state.pos.x = {rig.state.pos.x}")
    print(f"rig.state.pos.y = {rig.state.pos.y}")
    print(f"rig.state.speed = {rig.state.speed}")
    print(f"rig.state.speed.value = {rig.state.speed.value}")
    print(f"rig.state.speed.target = {rig.state.speed.target}")
    print(f"rig.state.direction = {rig.state.direction}")
    print(f"rig.state.direction.value = {rig.state.direction.value}")
    print(f"rig.state.direction.target = {rig.state.direction.target}")
    print(f"rig.state.direction_cardinal = {rig.state.direction_cardinal}")
    print(f"rig.state.direction_cardinal.value = {rig.state.direction_cardinal.value}")
    print(f"rig.state.direction_cardinal.target = {rig.state.direction_cardinal.target}")
    print(f"rig.state.vector = {rig.state.vector}")
    print(f"rig.state.vector.value = {rig.state.vector.value}")
    print(f"rig.state.vector.target = {rig.state.vector.target}")
    print(f"rig.state.layers = {rig.state.layers}")
    print(f"rig.state.frame_loop_active = {rig.state._frame_loop_job is not None}")

    return True, "RigState repr shown"

def test_base_state_empty():
    """Test BaseState repr with no animations"""
    rig = actions.user.mouse_rig()
    rig.stop()
    print("\nBaseState (empty):")
    print(rig.state.base)

    print("\nIndividual property access:")
    print(f"rig.state.base.pos = {rig.state.base.pos}")
    print(f"rig.state.base.pos.value = {rig.state.base.pos.value}")
    print(f"rig.state.base.pos.target = {rig.state.base.pos.target}")
    print(f"rig.state.base.pos.x = {rig.state.base.pos.x}")
    print(f"rig.state.base.pos.y = {rig.state.base.pos.y}")
    print(f"rig.state.base.speed = {rig.state.base.speed}")
    print(f"rig.state.base.speed.value = {rig.state.base.speed.value}")
    print(f"rig.state.base.speed.target = {rig.state.base.speed.target}")
    print(f"rig.state.base.direction = {rig.state.base.direction}")
    print(f"rig.state.base.direction.value = {rig.state.base.direction.value}")
    print(f"rig.state.base.direction.target = {rig.state.base.direction.target}")
    print(f"rig.state.base.direction_cardinal = {rig.state.base.direction_cardinal}")
    print(f"rig.state.base.direction_cardinal.value = {rig.state.base.direction_cardinal.value}")
    print(f"rig.state.base.direction_cardinal.target = {rig.state.base.direction_cardinal.target}")
    print(f"rig.state.base.vector = {rig.state.base.vector}")
    print(f"rig.state.base.vector.value = {rig.state.base.vector.value}")
    print(f"rig.state.base.vector.target = {rig.state.base.vector.target}")

    return True, "BaseState repr shown"

def test_rig_state_with_animations():
    """Test RigState repr with active animations"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.speed.to(5).over(1000)
    rig.speed.offset.to(3).over(1000)
    rig.direction.to((1, 0)).over(500)
    rig.pos.offset.to((100, 100)).over(2000)

    time.sleep(0.1)

    print("\nRigState (with animations):")
    print(rig.state)

    rig.stop()
    return True, "RigState with animations shown"

def test_base_state_with_animations():
    """Test BaseState repr with active animations"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.speed.to(5).over(1000)
    rig.direction.to((1, 0)).over(500)

    time.sleep(0.1)

    print("\nBaseState (with animations):")
    print(rig.state.base)

    rig.stop()
    return True, "BaseState with animations shown"

def test_layer_state_base_speed():
    """Test LayerState repr for base.speed"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.speed.to(5).over(1000)
    time.sleep(0.1)

    layer = rig.state.layer("base.speed")
    if not layer:
        return False, "base.speed layer not found"

    print("\nLayerState (base.speed):")
    print(layer)

    print("\nIndividual property access:")
    print(f"layer.prop = {layer.prop}")
    print(f"layer.mode = {layer.mode}")
    print(f"layer.value = {layer.value}")
    print(f"layer.target = {layer.target}")
    print(f"layer.time_alive = {layer.time_alive:.2f}s")
    print(f"layer.time_left = {layer.time_left:.2f}s")

    rig.stop()
    return True, "base.speed layer shown"

def test_layer_state_offset():
    """Test LayerState repr for speed.offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.speed.offset.to(10).over(1000)
    time.sleep(0.1)

    layer = rig.state.layer("speed.offset")
    if not layer:
        return False, "speed.offset layer not found"

    print("\nLayerState (speed.offset):")
    print(layer)

    rig.stop()
    return True, "speed.offset layer shown"

def test_layer_state_custom_named():
    """Test LayerState repr for custom named layer"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.speed.offset.to(10).over(1000).on("boost")
    time.sleep(0.1)

    layer = rig.state.layer("boost")
    if not layer:
        return False, "boost layer not found"

    print("\nLayerState (boost - custom named):")
    print(layer)

    rig.stop()
    return True, "Custom named layer shown"

def test_layer_state_pos_offset():
    """Test LayerState repr for pos.offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.pos.offset.to((100, 100)).over(2000)
    time.sleep(0.1)

    layer = rig.state.layer("pos.offset")
    if not layer:
        return False, "pos.offset layer not found"

    print("\nLayerState (pos.offset):")
    print(layer)

    rig.stop()
    return True, "pos.offset layer shown"

def test_frame_loop_status():
    """Test frame loop status in RigState repr"""
    rig = actions.user.mouse_rig()
    rig.stop()

    print("\nFrame loop status (stopped):")
    print(f"frame_loop_active = {rig.state._frame_loop_job is not None}")

    rig.speed.to(5)
    time.sleep(0.05)

    print("\nFrame loop status (running):")
    print(f"frame_loop_active = {rig.state._frame_loop_job is not None}")

    rig.stop()
    return True, "Frame loop status shown"

STATE_TESTS = [
    ("RigState (empty)", test_rig_state_empty),
    ("BaseState (empty)", test_base_state_empty),
    ("RigState (with animations)", test_rig_state_with_animations),
    ("BaseState (with animations)", test_base_state_with_animations),
    ("LayerState - base.speed", test_layer_state_base_speed),
    ("LayerState - speed.offset", test_layer_state_offset),
    ("LayerState - pos.offset", test_layer_state_pos_offset),
    ("LayerState - custom named", test_layer_state_custom_named),
    ("Frame loop status", test_frame_loop_status),
]
