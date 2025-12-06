# Talon Mouse Rig

All purpose mouse rig for Talon with a fluent API for position, speed, direction, layers, callbacks, durations, easing, and reverts.

## Examples

### Position

```python
rig = actions.user.mouse_rig()
rig.pos(960, 540)
rig.pos.to(960, 540).over(400)
rig.pos.to(960, 540).over(400, "ease_in_out")
rig.pos.by(10, 0)
rig.pos.by(10, 0).over(200).then(lambda: print("Moved mouse"))
```

### Speed

```python
rig = actions.user.mouse_rig()
rig.direction(1, 0)
rig.speed(8)
rig.speed.to(8).over(500)
rig.speed.to(8).over(500).revert(500)
rig.stop()
rig.stop(1000)
```

### Direction

```python
rig = actions.user.mouse_rig()
rig.direction.to(0, 1)
rig.speed(2)
rig.direction.by(90)
rig.direction.by(90).over(500) # rotate
rig.direction.by(90).over(rate=45) # rotate
```

### layers

layers are a namespace for temporary state you can revert later.
layers are calculated AFTER the base values.

**layers support two operation categories** (but not mixed on same layer):
- **Additive**: `.add()`, `.by()`, `.sub()` - stack by adding/subtracting
- **Multiplicative**: `.mul()`, `.div()` - stack by multiplying/dividing

Use `.revert()` to remove a layer's effect, or anonymous builders for absolute positioning with `.to()`.

```python
rig = actions.user.mouse_rig()
rig.layer("boost").speed.add(10).over(1000)  # Additive
rig.layer("slowmo").speed.mul(0.5).over(1000)  # Multiplicative

# Revert effect after 1 second and remove layer operations
rig.layer("boost").revert(1000)

# Bake current state into base values and remove layer operations
rig.layer("boost").bake()
```

#### Repeat behaviors
```python
rig = actions.user.mouse_rig()
rig.layer("boost").speed.add(10)
rig.layer("boost").stack.speed.add(10) # Default behavior stacks
rig.layer("boost").stack(3).speed.add(10) # Max 3 stacks
rig.layer("boost").queue.speed.add(10) # Queue instead of stack
rig.layer("boost").queue().speed.add(10) # Queue until finished
rig.layer("boost").extend.speed.add(10) # Extend hold time
rig.layer("boost").reset.speed.add(10) # reset instead of stack
rig.layer("boost").throttle.speed.add(10) # Ignore while active
rig.layer("boost").throttle(500).speed.add(10) # Throttle calls to once per 500ms
```

### Revert and callbacks

```python
rig = actions.user.mouse_rig()
rig.speed.add(10).over(300).hold(2000).revert(300)
rig.layer("boost").speed.add(10).over(300).hold(2000).revert(300)
rig.speed.add(10).over(300) \
    .then(lambda: print("Speed boost applied")) \
    .hold(2000) \
    .then(lambda: print("Holding speed boost")) \
    .revert(300) \
    .then(lambda: print("Speed boost reverted"))
```

## Installation

### Prerequisites
- [Talon](https://talonvoice.com/)

### Install
Clone into your Talon user directory:

```sh
# mac/linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

git clone https://github.com/rokubop/talon-mouse-rig.git
```

Done! 🎉

## Reference

### Properties

- `pos` - Position (x, y coordinates)
- `speed` - Movement speed magnitude
- `direction` - Direction vector or angle

### Operators

- `.to(value)` - Set absolute value (anonymous builders only)

**Additive (can be mixed on same layer):**
- `.add(value)` / `.by(value)` - Add delta (aliases)
- `.sub(value)` - Subtract

**Multiplicative (can be mixed on same layer, but not with additive):**
- `.mul(value)` - Multiply
- `.div(value)` - Divide

### Lifecycle Methods

- `.over(ms, easing?)` - Transition duration with optional easing
- `.over(rate=X)` - Rate-based transition (e.g., 5 units/sec)
- `.hold(ms)` - Sustain duration
- `.revert(ms?, easing?)` - Fade out duration
- `.then(callback)` - Execute callback after stage completes

### Behavior Modes

- `.stack(max?)` - Stack effects (default: unlimited)
- `.reset()` - reset previous effect
- `.queue()` - Queue until current finishes
- `.extend()` - Extend hold duration
- `.throttle()` - Ignore while active (same as calling without args)
- `.throttle(ms)` - Rate limit calls to once per ms

### Easing Functions

`linear`, `ease_in`, `ease_out`, `ease_in_out`, `ease_in_2`, `ease_out_2`, `ease_in_out_2`, `ease_in_3`, `ease_out_3`, `ease_in_out_3`, `ease_in_4`, `ease_out_4`, `ease_in_out_4`

### Shortcuts

```python
rig.stop(ms?)
rig.reverse(ms?)
rig.bake()
```

### State

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

### layers

Use `.layer(name)` to create named effects that can be reverted later.

### Interpolation

Interpolation modes for `.over()` and `.revert()`:
- `interpolation='lerp'` - Linear interpolation (default for direction)
- `interpolation='slerp'` - Spherical interpolation (smooth rotation along arc)
- `interpolation='linear'` - Linear component interpolation (for smooth zero transitions in vectors)

```python
rig.direction.by(90).over(500, interpolation='slerp')
```

### Helpers

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

## License

MIT

## Contributing

Contributions welcome! Open an issue or PR on GitHub.

## Support

For issues or questions, please open an issue on GitHub.
