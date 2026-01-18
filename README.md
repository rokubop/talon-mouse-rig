# Talon Mouse Rig

![Version](https://img.shields.io/badge/version-0.5.0-blue)
![Status](https://img.shields.io/badge/status-prototype-red)

All purpose mouse rig for Talon with control over position, speed, direction, vectors, interpolation, timing, stacking, callbacks, and behaviors, favoring OS-level APIs for game compatibility.

## Overview

The rig gives you full control over these properties:

- **Direction** - A normalized vector (x, y) indicating movement direction
- **Speed** - Movement magnitude in pixels per frame
- **Vector** - Direction × Speed (velocity)
- **Position** - Absolute or relative positioning with interpolation
- **Scroll** - Continuous scrolling with independent speed, direction, and vector control (just like mouse movement)

## Talon Actions

Convenience actions for voice commands. See [`mouse_rig_user.talon`](mouse_rig_user.talon) for examples.

**Direction + Speed**
```python
user.mouse_rig_go_left(3.2)
user.mouse_rig_go_left(speed)
user.mouse_rig_go_right(speed)
user.mouse_rig_go_up(speed)
user.mouse_rig_go_down(speed)
user.mouse_rig_go_left(initial_speed, target_speed, over_ms, easing)
```

**Direction:**
```python
user.mouse_rig_direction_left()
user.mouse_rig_direction_to(x, y, over_ms, easing)
user.mouse_rig_direction_by(degrees, over_ms, easing)
```

**Speed:**
```python
user.mouse_rig_speed_to(5)
user.mouse_rig_speed_to(5, 1000)
user.mouse_rig_speed_to(value, over_ms, hold_ms, revert_ms)
user.mouse_rig_speed_add(value, over_ms, hold_ms, revert_ms)
user.mouse_rig_speed_mul(value, over_ms, hold_ms, revert_ms)
```

**Stop:**
```python
user.mouse_rig_stop()
user.mouse_rig_stop(1000)
user.mouse_rig_stop(over_ms, easing)
```

**Position:**
```python
user.mouse_rig_pos_to(500, 500)
user.mouse_rig_pos_to(500, 500, 1000, "ease_in_out")
user.mouse_rig_pos_to(x, y, over_ms, easing)
user.mouse_rig_pos_by(dx, dy, over_ms, easing)
user.mouse_rig_pos_by_value(distance, over_ms, easing)
```

**Ready to use example talon commands:**

[mouse_rig_user.talon](mouse_rig_user.talon)

**Advanced:**

For full control, use the fluent API with `rig = actions.user.mouse_rig()`. See the [Fluent API](#fluent-api) section below for details.

## Installation

### Development Dependencies

Optional dependencies for development and testing:
- [**talon-ui-elements**](https://github.com/rokubop/talon-ui-elements) (v0.10.0+)

### Install

Clone this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# mac and linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

# This repo
git clone https://github.com/rokubop/talon-mouse-rig

# Dev Dependencies (optional)
git clone https://github.com/rokubop/talon-ui-elements
```

## Fluent API

For full control, use `rig = actions.user.mouse_rig()`. The Talon actions are convenience wrappers around this API.

### Position

```python
rig.pos(960, 540)
rig.pos.to(960, 540).over(400)
rig.pos.to(960, 540).over(400, "ease_in_out")
rig.pos.by(10, 0)
rig.pos.by(10, 0).over(200).then(lambda: print("Moved mouse"))
```

### Speed

```python
rig.direction(1, 0)
rig.speed(8)
rig.speed.to(8).over(500)
rig.speed.to(8).over(500).revert(500)
rig.stop()
rig.stop(1000)
```

### Direction

```python
rig.direction.to(0, 1)
rig.speed(2)
rig.direction.by(90)
rig.direction.by(90).over(500)  # rotate
rig.direction.by(90).over(rate=45)  # rotate at rate
```

### Scroll

Scroll works just like mouse movement with speed, direction, and vector control:

```python
# Set scroll speed and direction
rig.scroll.speed.to(5)
rig.scroll.direction.to(0, 1)  # scroll down
rig.scroll.direction.to(0, -1)  # scroll up
rig.scroll.direction.to(1, 0)  # scroll right

# Set scroll vector (combines speed and direction)
rig.scroll.vector.to(0, 5)  # scroll down at speed 5
rig.scroll.vector.to(3, 5)  # diagonal scroll

# Smooth transitions
rig.scroll.speed.to(10).over(1000)
rig.scroll.direction.by(90).over(500)  # rotate scroll direction

# Add to current values
rig.scroll.speed.add(5)
rig.scroll.vector.add(0, 2)

# Offset layers for temporary boosts
rig.scroll.speed.offset.add(10).over(1000)
rig.scroll.speed.offset.revert()
rig.layer("boost").scroll.speed.offset.add(10).over(1000)

# Control scroll units (default is by_lines)
rig.scroll.speed.by_lines.to(5)
rig.scroll.speed.by_pixels.to(100)

# Stop scrolling
rig.scroll.speed.to(0)
rig.stop()  # stops all movement including scroll
rig.stop(1000)  # smooth stop
```

### Layers

Layers provide isolated namespaces for temporary state modifications. They're composable, revertible, and calculated after base values, allowing you to build complex, layered behaviors.

**Layers support two operation categories** (but not mixed on same layer):
- **Additive**: `.add()`, `.by()`, `.sub()` - stack by adding/subtracting
- **Multiplicative**: `.mul()`, `.div()` - stack by multiplying/dividing

Use `.revert()` to remove a layer's effect, or anonymous builders for absolute positioning with `.to()`.

```python
rig.layer("boost").speed.add(10).over(1000)  # Additive
rig.layer("slowmo").speed.mul(0.5).over(1000)  # Multiplicative

# Revert effect after 1 second and remove layer operations
rig.layer("boost").revert(1000)

# Bake current state into base values and remove layer operations
rig.layer("boost").bake()
```

#### Repeat Behaviors
```python
rig.layer("boost").speed.add(10)
rig.layer("boost").stack.speed.add(10)  # Default behavior stacks
rig.layer("boost").stack(3).speed.add(10)  # Max 3 stacks
rig.layer("boost").queue.speed.add(10)  # Queue instead of stack
rig.layer("boost").queue().speed.add(10)  # Queue until finished
rig.layer("boost").reset.speed.add(10)  # Reset instead of stack
rig.layer("boost").throttle.speed.add(10)  # Ignore while active
rig.layer("boost").throttle(500).speed.add(10)  # Throttle to once per 500ms
```

### Revert and Callbacks

```python
rig.speed.add(10).over(300).hold(2000).revert(300)
rig.layer("boost").speed.add(10).over(300).hold(2000).revert(300)
rig.speed.add(10).over(300) \
    .then(lambda: print("Speed boost applied")) \
    .hold(2000) \
    .then(lambda: print("Holding speed boost")) \
    .revert(300) \
    .then(lambda: print("Speed boost reverted"))
```

### API Reference

#### Properties

- `pos` - Position (x, y coordinates)
- `speed` - Movement speed magnitude
- `direction` - Direction vector or angle
- `scroll.speed` - Scroll speed magnitude
- `scroll.direction` - Scroll direction vector
- `scroll.vector` - Scroll velocity (speed × direction)

#### Operators

- `.to(value)` - Set absolute value (anonymous builders only)

**Additive (can be mixed on same layer):**
- `.add(value)` / `.by(value)` - Add delta (aliases)
- `.sub(value)` - Subtract

**Multiplicative (can be mixed on same layer, but not with additive):**
- `.mul(value)` - Multiply
- `.div(value)` - Divide

#### Lifecycle Methods

- `.over(ms, easing?)` - Transition duration with optional easing
- `.over(rate=X)` - Rate-based transition (e.g., 5 units/sec)
- `.hold(ms)` - Sustain duration
- `.revert(ms?, easing?)` - Fade out duration
- `.then(callback)` - Execute callback after stage completes

#### Behavior Modes

- `.stack(max?)` - Stack effects (default: unlimited)
- `.reset()` - Reset previous effect
- `.queue()` - Queue until current finishes
- `.throttle()` - Ignore while active (same as calling without args)
- `.throttle(ms)` - Rate limit calls to once per ms

#### Easing Functions

`linear`, `ease_in`, `ease_out`, `ease_in_out`, `ease_in_2`, `ease_out_2`, `ease_in_out_2`, `ease_in_3`, `ease_out_3`, `ease_in_out_3`, `ease_in_4`, `ease_out_4`, `ease_in_out_4`

#### Shortcuts

```python
rig.stop(ms?)
rig.reverse(ms?)
rig.bake()
```

#### State

Access current computed state (base + all active effects):

```python
rig.state.pos
rig.state.speed
rig.state.direction
```

Access base state only:

```python
rig.state.base.pos
rig.state.base.speed
rig.state.base.direction
```

List active layers:

```python
rig.state.layers  # ["sprint", "drift"]
```

Get info about a specific layer:

```python
sprint = rig.state.layer("sprint")
if sprint:
    print(sprint.speed)
    print(sprint.phase)  # 'over', 'hold', 'revert', or None
    print(sprint.prop)   # 'speed', 'direction', 'pos'
    print(sprint.operator)  # 'add', 'mul', 'sub', etc.
```

#### Interpolation

Interpolation modes for `.over()` and `.revert()`:
- `interpolation='lerp'` - Linear interpolation (default for direction)
- `interpolation='slerp'` - Spherical interpolation (smooth rotation along arc)
- `interpolation='linear'` - Linear component interpolation (for smooth zero transitions in vectors)

```python
rig.direction.by(90).over(500, interpolation='slerp')
```

#### Helpers

Direction helpers:

```python
# Convert direction to cardinal string
cardinal = rig.state.direction.to_cardinal()
# Returns: "right", "left", "up", "down",
#          "up_right", "up_left", "down_right", "down_left"

# Vector operations
rig.state.direction.magnitude()
rig.state.direction.normalized()
```