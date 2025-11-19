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

### Tags for namespace you can revert later

```python
rig = actions.user.mouse_rig()
rig.tag("boost").speed.mul(4).over(1000)
rig.tag("boost").revert(500)
```

<details>
<summary>Read more...</summary>

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

## More Examples

### 1. Jump to a position smoothly

```python
rig = actions.user.mouse_rig()
rig.pos.to(960, 540).over(400, "ease_in_out")
```

**Variations:**
```python
rig.pos.to(100, 100).over(300)
rig.pos.to(1200, 600).over(500, "ease_out")
rig.pos.by(50, -30).over(200)
```

### 2. Game-style camera control

```python
rig = actions.user.mouse_rig()
rig.direction(1, 0)
rig.speed(8)
```

**Variations:**
```python
rig.direction(-1, 0)
rig.direction(0, -1)
rig.direction(0.707, 0.707)
rig.speed.mul(2)
rig.speed.div(2)
rig.stop(500)
```

### 3. Temporary speed boost

```python
rig = actions.user.mouse_rig()
rig.tag("boost").speed.add(10).over(300).hold(2000).revert(300)
```

**Variations:**
```python
rig.tag("sprint").speed.mul(2)
rig.tag("sprint").revert(500)

rig.tag("boost").speed.add(15).hold(1500)
rig.tag("boost").revert()
```

## API Reference

### Directional Movement

```python
rig.direction(1, 0)
rig.direction(-1, 0)
rig.direction(0, -1)
rig.direction(0, 1)
rig.direction(0.707, 0.707)
rig.direction.by(90).over(500)
```

### Speed Control

```python
rig.speed(3)
rig.speed(10)
rig.speed.mul(2)
rig.speed.div(2)
rig.speed.add(5)
rig.speed.to(10).over(1000)
```

### Position Control

```python
rig.pos.to(960, 540).over(350, "ease_in_out")
rig.pos.by(50, 0).over(200)
rig.pos.add(-20, 10)
```

### Effects & Lifecycle

```python
rig.speed.add(10).hold(2000)
rig.speed.by(20).over(500).hold(1500).revert(500)
rig.tag("sprint").speed.mul(2)
rig.tag("sprint").revert(500)
```

### Acceleration

```python
rig.accel(5)
rig.tag("boost").accel.add(10).hold(2000)
```

### Stacking Effects

```python
rig.tag("boost_pad").speed.add(10)
rig.tag("boost_pad").stack(3).speed.add(10)
rig.tag("rage").speed.mul(1.2).stack(5)
```

</details>

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

## License

MIT

## Contributing

Contributions welcome! Open an issue or PR on GitHub.

## Support

For issues or questions, please open an issue on GitHub.
