# Talon Mouse Rig

Continuous motion-based mouse control system for Talon voice commands.

## Features

### Base Movement
- **Direction**: Set movement direction as a vector
- **Speed**: Control base speed (pixels per frame)
- **Acceleration**: Continuous acceleration over time
- **Position**: Absolute positioning and relative offsets

### Named Effects
Effects modify base properties with explicit operations and support lifecycle management:

**Operations**:
- `.to(value)` - Set absolute value
- `.add(value)` / `.by(value)` - Add delta
- `.sub(value)` - Subtract
- `.mul(value)` - Multiply
- `.div(value)` - Divide

**On-Repeat Strategies**:
- `replace` (default) - New call replaces existing
- `stack` - Unlimited stacking
- `stack(n)` - Max n stacks
- `extend` - Extend duration
- `queue` - Queue sequential effects
- `ignore` - Ignore new calls while active
- `throttle(ms)` - Rate limit calls

### Forces
Independent velocity sources with their own speed, direction, and acceleration. Forces combine with base movement via vector addition.

### Transitions & Timing
- **Time-based**: `.over(duration_ms, easing?)`
- **Rate-based**: `.over(rate_speed=x)` or `.over(rate_rotation=x)`
- **Easing**: `linear`, `ease_in`, `ease_out`, `ease_in_out`, `smoothstep`

### Lifecycle Management
- `.over(duration)` - Fade in over time
- `.hold(duration)` - Maintain for duration
- `.revert(duration?, easing?)` - Fade out and revert

### State Access
- `rig.state.speed` - Computed speed (base + effects + forces)
- `rig.state.accel` - Computed acceleration
- `rig.state.direction` - Current direction
- `rig.state.velocity` - Total velocity vector
- `rig.base.speed` - Base speed only (no modifiers)

## Usage Examples

### Basic Movement
```python
rig = actions.user.mouse_rig()

# Set direction and speed
rig.direction(1, 0)  # Move right
rig.speed(10)        # Set speed

# Smooth transitions
rig.speed.to(20).over(500)           # Ramp to 20 over 500ms
rig.direction(0, 1).over(500, "ease_out")  # Turn smoothly
```

### Named Effects (Strict Syntax)
```python
# Sprint effect (2x speed multiplier)
rig.effect("sprint").speed.mul(2)
rig.effect("sprint").revert(500)  # Stop sprinting

# Speed boost with stacking
rig.effect("boost").speed.add(10).on_repeat("stack")  # Unlimited
rig.effect("boost").speed.add(10).on_repeat("stack", 3)  # Max 3

# Drift (rotate direction)
rig.effect("drift").direction.add(15)  # Rotate 15 degrees
rig.effect("drift").revert(500)

# Throttled dash
rig.effect("dash").speed.add(20).hold(200).on_repeat("throttle", 500)
```

### Forces (Loose Syntax)
```python
# Gravity force
rig.force("gravity").direction(0, 1).accel(9.8)
rig.force("gravity").stop(500)

# Wind force with smooth fade
rig.force("wind").direction(1, 0).speed(10).over(500).hold(3000).revert(1000)
```

### Temporary Effects (Anonymous)
```python
# Quick speed boost
rig.speed.add(10).hold(1000).revert(500)

# Smooth boost with easing
rig.speed.add(20).over(500, "ease_in_out").hold(1500).revert(500)
```

### Position Control
```python
# Jump to screen center
rig.pos.to(960, 540).over(350, "ease_in_out")

# Nudge position
rig.pos.by(50, 0).over(200)  # Nudge right

# Position with lifecycle
rig.pos.by(100, 0).over(300).hold(1000).revert(300)
```

### Rotation
```python
# Smooth turn
rig.direction.by(90).over(500, "ease_in_out")  # Turn 90° right

# 180° reverse
rig.reverse().over(500)

# Rate-based rotation
rig.direction(0, 1).over(rate_rotation=90)  # Rotate at 90°/s
```

### State Management
```python
# Stop movement
rig.stop()  # Immediate
rig.stop(1000, "ease_out")  # Smooth deceleration

# Bake effects into base state
rig.bake()

# Access computed state
current_speed = rig.state.speed
current_direction = rig.state.direction
total_velocity = rig.state.velocity

# Access base values
base_speed = rig.base.speed
```

## Composition Pipeline

Effects and forces are applied in this order:
1. **Base properties** (speed, accel, direction)
2. **Effect stacks** (multiplicative → additive, in creation order)
3. **Forces** (independent velocity vectors, summed)

## Settings

Configure via Talon settings:
- `user.mouse_rig_frame_interval` - Frame interval in ms (default: 16ms ≈ 60fps)
- `user.mouse_rig_max_speed` - Max speed limit (default: 15.0)
- `user.mouse_rig_movement_type` - `"talon"` or `"windows_raw"`
- `user.mouse_rig_scale` - Movement scale multiplier (default: 1.0)
- `user.mouse_rig_default_turn_rate` - Default rotation rate in deg/s (default: 180.0)
