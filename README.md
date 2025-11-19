# Talon Mouse Rig

All purpose mouse rig for Talon with a fluent API for position, speed, direction, acceleration, tags, callbacks, durations, easing, and reverts.

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

### Tags

Tags are a namespace for temporary state you can revert later.
Tags are calculated AFTER the base values.

```python
rig = actions.user.mouse_rig()
rig.tag("boost").speed.mul(4).over(1000)
rig.tag("boost").revert(1000)

# Bake current state into base values
rig.tag("boost").bake()
```

#### Repeat behaviors
```python
rig = actions.user.mouse_rig()
rig.tag("boost").speed.add(10)
rig.tag("boost").stack.speed.add(10) # Default behavior stacks
rig.tag("boost").stack(3).speed.add(10) # Max 3 stacks
rig.tag("boost").queue.speed.add(10) # Queue instead of stack
rig.tag("boost").queue().speed.add(10) # Queue until finished
rig.tag("boost").extend.speed.add(10) # Extend hold time
rig.tag("boost").replace.speed.add(10) # Replace instead of stack
rig.tag("boost").throttle.speed.add(10) # Throttle calls
rig.tag("boost").throttle(500).speed.add(10) # Throttle calls to once per 500ms
rig.tag("boost").ignore.speed.add(10) # Ignore while active
```


### Revert and callbacks

```python
rig = actions.user.mouse_rig()
rig.speed.add(10).over(300).hold(2000).revert(300)
rig.tag("boost").speed.add(10).over(300).hold(2000).revert(300)
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
- `accel` - Acceleration magnitude

### Operators

- `.to(value)` - Set absolute value
- `.add(value)` / `.by(value)` - Add delta (aliases)
- `.sub(value)` - Subtract
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
- `.replace()` - Replace previous effect
- `.queue()` - Queue until current finishes
- `.extend()` - Extend hold duration
- `.throttle(ms)` - Rate limit calls
- `.ignore()` - Ignore while active

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
rig.state.accel
```

Access base state only:

```python
rig.state.base.pos
rig.state.base.speed
rig.state.base.direction
rig.state.base.accel
```

List active tags:

```python
rig.state.tags  # ["sprint", "drift"]
```

Get info about a specific tag:

```python
sprint = rig.state.tag("sprint")
if sprint:
    print(sprint.speed)
    print(sprint.phase)  # 'over', 'hold', 'revert', or None
    print(sprint.prop)   # 'speed', 'direction', 'pos', 'accel'
    print(sprint.operator)  # 'to', 'add', 'mul', etc.
```

### Tags

Use `.tag(name)` to create named effects that can be reverted later.

### Interpolation

Direction interpolation modes for `.over()` and `.revert()`:
- `interpolation='lerp'` - Linear interpolation (default)
- `interpolation='slerp'` - Spherical interpolation (smooth rotation along arc)

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
