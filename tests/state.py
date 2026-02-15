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
    print(f"rig.state.pos.current = {rig.state.pos.current}")
    print(f"rig.state.pos.target = {rig.state.pos.target}")
    print(f"rig.state.pos.x = {rig.state.pos.x}")
    print(f"rig.state.pos.y = {rig.state.pos.y}")
    print(f"rig.state.speed = {rig.state.speed}")
    print(f"rig.state.speed.current = {rig.state.speed.current}")
    print(f"rig.state.speed.target = {rig.state.speed.target}")
    print(f"rig.state.direction = {rig.state.direction}")
    print(f"rig.state.direction.current = {rig.state.direction.current}")
    print(f"rig.state.direction.target = {rig.state.direction.target}")
    print(f"rig.state.direction_cardinal = {rig.state.direction_cardinal}")
    print(f"rig.state.direction_cardinal.current = {rig.state.direction_cardinal.current}")
    print(f"rig.state.direction_cardinal.target = {rig.state.direction_cardinal.target}")
    print(f"rig.state.vector = {rig.state.vector}")
    print(f"rig.state.vector.current = {rig.state.vector.current}")
    print(f"rig.state.vector.target = {rig.state.vector.target}")
    print(f"rig.state.scroll = {rig.state.scroll}")
    print(f"rig.state.scroll.current = {rig.state.scroll.current}")
    print(f"rig.state.scroll.target = {rig.state.scroll.target}")
    print(f"rig.state.scroll.x = {rig.state.scroll.x}")
    print(f"rig.state.scroll.y = {rig.state.scroll.y}")
    print(f"rig.state.scroll.speed = {rig.state.scroll.speed}")
    print(f"rig.state.scroll.speed.current = {rig.state.scroll.speed.current}")
    print(f"rig.state.scroll.speed.target = {rig.state.scroll.speed.target}")
    print(f"rig.state.scroll.direction = {rig.state.scroll.direction}")
    print(f"rig.state.scroll.direction.current = {rig.state.scroll.direction.current}")
    print(f"rig.state.scroll.direction.target = {rig.state.scroll.direction.target}")
    print(f"rig.state.scroll.direction_cardinal = {rig.state.scroll.direction_cardinal}")
    print(f"rig.state.scroll.direction_cardinal.current = {rig.state.scroll.direction_cardinal.current}")
    print(f"rig.state.scroll.direction_cardinal.target = {rig.state.scroll.direction_cardinal.target}")
    print(f"rig.state.scroll.vector = {rig.state.scroll.vector}")
    print(f"rig.state.scroll.vector.current = {rig.state.scroll.vector.current}")
    print(f"rig.state.scroll.vector.target = {rig.state.scroll.vector.target}")
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
    print(f"rig.state.base.pos.current = {rig.state.base.pos.current}")
    print(f"rig.state.base.pos.target = {rig.state.base.pos.target}")
    print(f"rig.state.base.pos.x = {rig.state.base.pos.x}")
    print(f"rig.state.base.pos.y = {rig.state.base.pos.y}")
    print(f"rig.state.base.speed = {rig.state.base.speed}")
    print(f"rig.state.base.speed.current = {rig.state.base.speed.current}")
    print(f"rig.state.base.speed.target = {rig.state.base.speed.target}")
    print(f"rig.state.base.direction = {rig.state.base.direction}")
    print(f"rig.state.base.direction.current = {rig.state.base.direction.current}")
    print(f"rig.state.base.direction.target = {rig.state.base.direction.target}")
    print(f"rig.state.base.direction_cardinal = {rig.state.base.direction_cardinal}")
    print(f"rig.state.base.direction_cardinal.current = {rig.state.base.direction_cardinal.current}")
    print(f"rig.state.base.direction_cardinal.target = {rig.state.base.direction_cardinal.target}")
    print(f"rig.state.base.vector = {rig.state.base.vector}")
    print(f"rig.state.base.vector.current = {rig.state.base.vector.current}")
    print(f"rig.state.base.vector.target = {rig.state.base.vector.target}")
    print(f"rig.state.base.scroll = {rig.state.base.scroll}")
    print(f"rig.state.base.scroll.current = {rig.state.base.scroll.current}")
    print(f"rig.state.base.scroll.target = {rig.state.base.scroll.target}")
    print(f"rig.state.base.scroll.x = {rig.state.base.scroll.x}")
    print(f"rig.state.base.scroll.y = {rig.state.base.scroll.y}")
    print(f"rig.state.base.scroll.speed = {rig.state.base.scroll.speed}")
    print(f"rig.state.base.scroll.speed.current = {rig.state.base.scroll.speed.current}")
    print(f"rig.state.base.scroll.speed.target = {rig.state.base.scroll.speed.target}")
    print(f"rig.state.base.scroll.direction = {rig.state.base.scroll.direction}")
    print(f"rig.state.base.scroll.direction.current = {rig.state.base.scroll.direction.current}")
    print(f"rig.state.base.scroll.direction.target = {rig.state.base.scroll.direction.target}")
    print(f"rig.state.base.scroll.direction_cardinal = {rig.state.base.scroll.direction_cardinal}")
    print(f"rig.state.base.scroll.direction_cardinal.current = {rig.state.base.scroll.direction_cardinal.current}")
    print(f"rig.state.base.scroll.direction_cardinal.target = {rig.state.base.scroll.direction_cardinal.target}")
    print(f"rig.state.base.scroll.vector = {rig.state.base.scroll.vector}")
    print(f"rig.state.base.scroll.vector.current = {rig.state.base.scroll.vector.current}")
    print(f"rig.state.base.scroll.vector.target = {rig.state.base.scroll.vector.target}")

    return True, "BaseState repr shown"

def test_rig_state_with_animations():
    """Test RigState repr with active animations"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.speed.to(5).over(1000)
    rig.speed.offset.to(3).over(1000)
    rig.direction.to((1, 0)).over(500)
    rig.pos.offset.to((100, 100)).over(2000)
    rig.scroll.to((50, 50)).over(1500)
    rig.scroll.speed.to(10).over(800)
    rig.scroll.direction.to((0, 1)).over(600)

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
    rig.scroll.to((50, 50)).over(1500)
    rig.scroll.speed.to(10).over(800)
    rig.scroll.direction.to((0, 1)).over(600)

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

    layer = rig.state.layers["base.speed"]
    if not layer:
        return False, "base.speed layer not found"

    print("\nLayerState (base.speed):")
    print(layer)

    print("\nIndividual property access:")
    print(f"layer.prop = {layer.prop}")
    print(f"layer.mode = {layer.mode}")
    print(f"layer.current = {layer.current}")
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

    layer = rig.state.layers["speed.offset"]
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

    rig.layer("boost").speed.offset.to(10).over(1000)
    time.sleep(0.1)

    layer = rig.state.layers["boost"]
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

    layer = rig.state.layers["pos.offset"]
    if not layer:
        return False, "pos.offset layer not found"

    print("\nLayerState (pos.offset):")
    print(layer)

    rig.stop()
    return True, "pos.offset layer shown"

def test_layer_state_base_scroll():
    """Test LayerState repr for base.scroll"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.to((100, 50)).over(1000)
    time.sleep(0.1)

    layer = rig.state.layers["base.scroll"]
    if not layer:
        return False, "base.scroll layer not found"

    print("\nLayerState (base.scroll):")
    print(layer)

    print("\nIndividual property access:")
    print(f"layer.prop = {layer.prop}")
    print(f"layer.mode = {layer.mode}")
    print(f"layer.current = {layer.current}")
    print(f"layer.target = {layer.target}")
    print(f"layer.time_alive = {layer.time_alive:.2f}s")
    print(f"layer.time_left = {layer.time_left:.2f}s")

    rig.stop()
    return True, "base.scroll layer shown"

def test_layer_state_scroll_offset():
    """Test LayerState repr for scroll.offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.offset.to((50, 100)).over(1500)
    time.sleep(0.1)

    layer = rig.state.layers["scroll.offset"]
    if not layer:
        return False, "scroll.offset layer not found"

    print("\nLayerState (scroll.offset):")
    print(layer)

    print("\nIndividual property access:")
    print(f"layer.prop = {layer.prop}")
    print(f"layer.mode = {layer.mode}")
    print(f"layer.current = {layer.current}")
    print(f"layer.target = {layer.target}")
    print(f"layer.time_alive = {layer.time_alive:.2f}s")
    print(f"layer.time_left = {layer.time_left:.2f}s")

    rig.stop()
    return True, "scroll.offset layer shown"

def test_scroll_state_empty():
    """Test scroll state repr with no scroll animations"""
    rig = actions.user.mouse_rig()
    rig.stop()

    print("\nScroll state (empty):")
    print(f"rig.state.scroll = {rig.state.scroll}")
    print(f"rig.state.scroll.current = {rig.state.scroll.current}")
    print(f"rig.state.scroll.target = {rig.state.scroll.target}")
    print(f"rig.state.scroll.x = {rig.state.scroll.x}")
    print(f"rig.state.scroll.y = {rig.state.scroll.y}")
    print(f"rig.state.base.scroll = {rig.state.base.scroll}")
    print(f"rig.state.base.scroll.current = {rig.state.base.scroll.current}")
    print(f"rig.state.base.scroll.target = {rig.state.base.scroll.target}")

    return True, "Empty scroll state shown"

def test_scroll_state_with_animations():
    """Test scroll state with active animations on base and offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.to((100, 50)).over(1000)
    rig.scroll.offset.to((20, 30)).over(800)

    time.sleep(0.1)

    print("\nScroll state (with animations):")
    print(f"rig.state.scroll = {rig.state.scroll}")
    print(f"rig.state.scroll.current = {rig.state.scroll.current}")
    print(f"rig.state.scroll.target = {rig.state.scroll.target}")
    print(f"rig.state.scroll.x = {rig.state.scroll.x}")
    print(f"rig.state.scroll.y = {rig.state.scroll.y}")

    print("\nBase scroll state:")
    print(f"rig.state.base.scroll = {rig.state.base.scroll}")
    print(f"rig.state.base.scroll.current = {rig.state.base.scroll.current}")
    print(f"rig.state.base.scroll.target = {rig.state.base.scroll.target}")

    rig.stop()
    return True, "Scroll state with animations shown"

def test_scroll_layer_custom_named():
    """Test LayerState repr for custom named scroll layer"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.layer("wobble").scroll.offset.to((15, 25)).over(1000)
    time.sleep(0.1)

    layer = rig.state.layers["wobble"]
    if not layer:
        return False, "wobble layer not found"

    print("\nLayerState (wobble - custom named scroll):")
    print(layer)

    rig.stop()
    return True, "Custom named scroll layer shown"

def test_layer_state_scroll_pos():
    """Test LayerState repr for base.scroll.pos"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.pos.to((200, 150)).over(1200)
    time.sleep(0.1)

    layer = rig.state.layers["base.scroll.pos"]
    if not layer:
        return False, "base.scroll.pos layer not found"

    print("\nLayerState (base.scroll.pos):")
    print(layer)

    print("\nIndividual property access:")
    print(f"layer.prop = {layer.prop}")
    print(f"layer.mode = {layer.mode}")
    print(f"layer.current = {layer.current}")
    print(f"layer.target = {layer.target}")
    print(f"layer.time_alive = {layer.time_alive:.2f}s")
    print(f"layer.time_left = {layer.time_left:.2f}s")

    rig.stop()
    return True, "base.scroll.pos layer shown"

def test_layer_state_scroll_speed():
    """Test LayerState repr for base.scroll.speed"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.to(15).over(1000)
    time.sleep(0.1)

    layer = rig.state.layers["base.scroll.speed"]
    if not layer:
        return False, "base.scroll.speed layer not found"

    print("\nLayerState (base.scroll.speed):")
    print(layer)

    print("\nIndividual property access:")
    print(f"layer.prop = {layer.prop}")
    print(f"layer.mode = {layer.mode}")
    print(f"layer.current = {layer.current}")
    print(f"layer.target = {layer.target}")
    print(f"layer.time_alive = {layer.time_alive:.2f}s")
    print(f"layer.time_left = {layer.time_left:.2f}s")

    rig.stop()
    return True, "base.scroll.speed layer shown"

def test_layer_state_scroll_direction():
    """Test LayerState repr for base.scroll.direction"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.direction.to((1, 1)).over(800)
    time.sleep(0.1)

    layer = rig.state.layers["base.scroll.direction"]
    if not layer:
        return False, "base.scroll.direction layer not found"

    print("\nLayerState (base.scroll.direction):")
    print("test")
    print(layer)

    print("\nIndividual property access:")
    print(f"layer.prop = {layer.prop}")
    print(f"layer.mode = {layer.mode}")
    print(f"layer.current = {layer.current}")
    print(f"layer.target = {layer.target}")
    print(f"layer.time_alive = {layer.time_alive:.2f}s")
    print(f"layer.time_left = {layer.time_left:.2f}s")

    rig.stop()
    return True, "base.scroll.direction layer shown"

def test_layer_state_scroll_vector():
    """Test LayerState repr for base.scroll.vector"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.vector.to((10, 20)).over(1500)
    time.sleep(0.1)

    layer = rig.state.layers["base.scroll.vector"]
    if not layer:
        return False, "base.scroll.vector layer not found"

    print("\nLayerState (base.scroll.vector):")
    print(layer)

    print("\nIndividual property access:")
    print(f"layer.prop = {layer.prop}")
    print(f"layer.mode = {layer.mode}")
    print(f"layer.current = {layer.current}")
    print(f"layer.target = {layer.target}")
    print(f"layer.time_alive = {layer.time_alive:.2f}s")
    print(f"layer.time_left = {layer.time_left:.2f}s")

    rig.stop()
    return True, "base.scroll.vector layer shown"

def test_layer_state_scroll_pos_offset():
    """Test LayerState repr for scroll.pos.offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.pos.offset.to((30, 40)).over(1000)
    time.sleep(0.1)

    layer = rig.state.layers["scroll.pos.offset"]
    if not layer:
        return False, "scroll.pos.offset layer not found"

    print("\nLayerState (scroll.pos.offset):")
    print(layer)

    rig.stop()
    return True, "scroll.pos.offset layer shown"

def test_layer_state_scroll_speed_offset():
    """Test LayerState repr for scroll.speed.offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.speed.offset.to(5).over(800)
    time.sleep(0.1)

    layer = rig.state.layers["scroll.speed.offset"]
    if not layer:
        return False, "scroll.speed.offset layer not found"

    print("\nLayerState (scroll.speed.offset):")
    print(layer)

    rig.stop()
    return True, "scroll.speed.offset layer shown"

def test_layer_state_scroll_direction_offset():
    """Test LayerState repr for scroll.direction.offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.direction.offset.to((0.5, 0.5)).over(600)
    time.sleep(0.1)

    layer = rig.state.layers["scroll.direction.offset"]
    if not layer:
        return False, "scroll.direction.offset layer not found"

    print("\nLayerState (scroll.direction.offset):")
    print(layer)

    rig.stop()
    return True, "scroll.direction.offset layer shown"

def test_layer_state_scroll_vector_offset():
    """Test LayerState repr for scroll.vector.offset"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.vector.offset.to((5, 10)).over(1200)
    time.sleep(0.1)

    layer = rig.state.layers["scroll.vector.offset"]
    if not layer:
        return False, "scroll.vector.offset layer not found"

    print("\nLayerState (scroll.vector.offset):")
    print(layer)

    rig.stop()
    return True, "scroll.vector.offset layer shown"

def test_scroll_state_all_properties():
    """Test all scroll sub-properties with animations"""
    rig = actions.user.mouse_rig()
    rig.stop()

    rig.scroll.pos.to((100, 100)).over(1000)
    rig.scroll.speed.to(20).over(800)
    rig.scroll.direction.to((1, 0)).over(600)
    rig.scroll.vector.to((15, 0)).over(1200)

    time.sleep(0.1)

    print("\nAll scroll properties (with animations):")
    # print(f"rig.state.scroll.pos = {rig.state.scroll.pos}")
    # print(f"rig.state.scroll.pos.current = {rig.state.scroll.pos.current}")
    # print(f"rig.state.scroll.pos.target = {rig.state.scroll.pos.target}")
    print(f"rig.state.scroll.speed = {rig.state.scroll.speed}")
    print(f"rig.state.scroll.speed.current = {rig.state.scroll.speed.current}")
    print(f"rig.state.scroll.speed.target = {rig.state.scroll.speed.target}")
    print(f"rig.state.scroll.direction = {rig.state.scroll.direction}")
    print(f"rig.state.scroll.direction.current = {rig.state.scroll.direction.current}")
    print(f"rig.state.scroll.direction.target = {rig.state.scroll.direction.target}")
    print(f"rig.state.scroll.direction_cardinal = {rig.state.scroll.direction_cardinal}")
    print(f"rig.state.scroll.direction_cardinal.current = {rig.state.scroll.direction_cardinal.current}")
    print(f"rig.state.scroll.direction_cardinal.target = {rig.state.scroll.direction_cardinal.target}")
    print(f"rig.state.scroll.vector = {rig.state.scroll.vector}")
    print(f"rig.state.scroll.vector.current = {rig.state.scroll.vector.current}")
    print(f"rig.state.scroll.vector.target = {rig.state.scroll.vector.target}")

    rig.stop()
    return True, "All scroll properties shown"
    return True, "pos.offset layer shown"

def test_layers_view_dict_like():
    """Test LayersView dict-like behavior"""
    rig = actions.user.mouse_rig()
    rig.stop()

    # Empty layers
    layers = rig.state.layers
    print("\nLayersView (empty):")
    print(f"repr: {layers}")
    print(f"len: {len(layers)}")
    print(f"bool: {bool(layers)}")

    if len(layers) != 0:
        return False, f"Expected 0 layers, got {len(layers)}"
    if bool(layers):
        return False, "Expected empty layers to be falsy"

    # Missing key returns None
    missing = layers["nonexistent"]
    print(f"missing key: {missing}")
    if missing is not None:
        return False, f"Expected None for missing key, got {missing}"

    # .get() with default
    default_val = layers.get("nonexistent", "fallback")
    if default_val != "fallback":
        return False, f"Expected 'fallback' default, got {default_val}"

    # With active layers
    rig.speed.to(5).over(1000)
    rig.layer("sprint").speed.offset.to(3).over(500)
    time.sleep(0.1)

    layers = rig.state.layers
    print("\nLayersView (with layers):")
    print(f"repr: {layers}")
    print(f"len: {len(layers)}")
    print(f"bool: {bool(layers)}")

    if not bool(layers):
        return False, "Expected non-empty layers to be truthy"

    # Containment
    print(f"'base.speed' in layers: {'base.speed' in layers}")
    print(f"'sprint' in layers: {'sprint' in layers}")
    print(f"'missing' in layers: {'missing' in layers}")

    if "base.speed" not in layers:
        return False, "'base.speed' should be in layers"
    if "sprint" not in layers:
        return False, "'sprint' should be in layers"
    if "missing" in layers:
        return False, "'missing' should not be in layers"

    # Iteration
    keys_from_iter = list(layers)
    print(f"iteration: {keys_from_iter}")

    # .keys(), .values(), .items()
    print(f"keys: {list(layers.keys())}")
    print(f"values: {layers.values()}")
    print(f"items: {layers.items()}")

    if set(layers.keys()) != set(keys_from_iter):
        return False, "keys() should match iteration"
    if len(layers.items()) != len(layers):
        return False, "items() length should match len()"

    rig.stop()
    return True, "LayersView dict-like behavior verified"

def test_frame_loop_status():
    """Test frame loop status in RigState repr"""
    rig = actions.user.mouse_rig()

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
    ("LayerState - base.scroll", test_layer_state_base_scroll),
    ("LayerState - scroll.offset", test_layer_state_scroll_offset),
    # ("LayerState - base.scroll.pos", test_layer_state_scroll_pos),
    ("LayerState - base.scroll.speed", test_layer_state_scroll_speed),
    ("LayerState - base.scroll.direction", test_layer_state_scroll_direction),
    ("LayerState - base.scroll.vector", test_layer_state_scroll_vector),
    # ("LayerState - scroll.pos.offset", test_layer_state_scroll_pos_offset),
    ("LayerState - scroll.speed.offset", test_layer_state_scroll_speed_offset),
    ("LayerState - scroll.direction.offset", test_layer_state_scroll_direction_offset),
    ("LayerState - scroll.vector.offset", test_layer_state_scroll_vector_offset),
    ("LayerState - custom named", test_layer_state_custom_named),
    ("Scroll state (empty)", test_scroll_state_empty),
    ("Scroll state (with animations)", test_scroll_state_with_animations),
    ("Scroll all properties", test_scroll_state_all_properties),
    ("LayerState - custom scroll", test_scroll_layer_custom_named),
    ("LayersView - dict-like", test_layers_view_dict_like),
    ("Frame loop status", test_frame_loop_status),
]
