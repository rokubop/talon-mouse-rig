# PRD 7: Mouse Rig API - Transform/Force Separation

**Status**: Draft
**Date**: 2024-11-11
**Previous**: PRD 6 (Named Entities with Type Inference)

## Overview

This PRD finalizes the mouse rig API with explicit separation between **transforms** (modifiers to base state) and **forces** (independent entities). This design prioritizes clarity and unambiguous behavior for voice-controlled cursor manipulation.

## Core Principles

1. **Explicit over Implicit**: Use `.transform()` and `.force()` rather than type inference
2. **Mathematical Operations**: Transforms use `.add()`, `.mul()`, `.sub()`, `.div()` directly (no ambiguous setters)

## Architecture

### Three Entity Types

#### 1. Base Rig
The direct cursor state. Has actual position, velocity, speed, direction, acceleration.

```python
rig = actions.user.mouse_rig()
rig.direction(1, 0)      # Set direction (direct setter allowed)
rig.speed(5)             # Set speed (direct setter allowed)
rig.accel(2)             # Set acceleration (direct setter allowed)
rig.pos(100, 200)        # Set position (direct setter allowed)
```

#### 2. Transforms
Named entities that modify base properties through operations. Do NOT have their own position/velocity.

**Key Rule**: Transforms MUST use explicit operations (`.add()`, `.mul()`, etc.), NOT direct setters.

```python
# ✅ CORRECT - Explicit operations
rig.transform("sprint").speed.mul(2)      # Multiply base speed by 2
rig.transform("boost").speed.add(10)      # Add 10 to base speed
rig.transform("slow").speed.mul(0.5)      # Multiply base speed by 0.5

# ❌ WRONG - Direct setter is ambiguous on transforms
rig.transform("sprint").speed(2)          # What does this mean? Unclear!
```

**Why?** Direct setters on transforms are ambiguous:
- `speed(2)` could mean "set base to 2" or "multiply base by 2" or "add 2"
- Explicit operations make intent crystal clear

**Transform Ownership**: A transform owns ALL operations applied through it. When you call `.stop()` or `.revert()` on a transform, it affects all properties that transform has modified:

```python
# A transform can modify multiple properties
rig.transform("sprint").speed.mul(2)
rig.transform("sprint").accel.mul(1.5)
rig.transform("sprint").direction.add(5)

# Stopping the transform reverts ALL of its changes
rig.transform("sprint").stop(500)  # Reverts speed, accel, AND direction
```

#### 3. Forces
Named independent entities with their own direction, velocity, and properties. Forces are vector-summed with the base rig result.

**Key Rule**: Forces CAN use direct setters (they have their own state).

```python
# ✅ CORRECT - Forces have their own state
rig.force("wind").velocity(5, 0)          # Wind has velocity (5, 0)
rig.force("wind").speed(5)                # Wind has speed 5
rig.force("gravity").direction(0, 1)      # Gravity points down
rig.force("gravity").accel(9.8)           # Gravity accelerates at 9.8

# Also valid - modify force properties
rig.force("wind").speed.add(2)            # Add to wind's speed
rig.force("wind").speed.mul(1.5)          # Scale wind's speed
```

## Operations

### Base Rig & Forces (Direct Setters)

```python
# Base rig - direct property setters (shorthand for .to())
rig.speed(10)           # Equivalent to: rig.speed.to(10)
rig.direction(1, 0)     # Equivalent to: rig.direction.to(1, 0)
rig.accel(5)            # Equivalent to: rig.accel.to(5)
rig.pos(100, 200)       # Equivalent to: rig.pos.to(100, 200)
rig.velocity(5, 3)      # Equivalent to: rig.velocity.to(5, 3)

# Forces - direct property setters (shorthand for .to())
rig.force("wind").speed(8)          # Equivalent to: rig.force("wind").speed.to(8)
rig.force("wind").velocity(5, 0)    # Equivalent to: rig.force("wind").velocity.to(5, 0)
rig.force("gravity").accel(9.8)     # Equivalent to: rig.force("gravity").accel.to(9.8)
```

**Note**: Direct setters are shorthand for `.to()` - use whichever feels more natural. The `.to()` / `.by()` syntax is useful when chaining with lifecycle methods.

### Transforms (Explicit Operations Only)

#### Speed & Accel (Mathematical Operations)

```python
# Multiplicative
rig.transform("sprint").speed.mul(2)        # speed *= 2
rig.transform("sprint").accel.mul(1.5)      # accel *= 1.5

# Additive
rig.transform("boost").speed.add(10)        # speed += 10
rig.transform("boost").accel.add(5)         # accel += 5

# Subtractive
rig.transform("drag").speed.sub(2)          # speed -= 2

# Division
rig.transform("slow").speed.div(2)          # speed /= 2
```

#### Position & Direction (Direct .by() and .to())

```python
# Position - offset from base position
rig.transform("offset").pos.by(10, 5)       # Offset by (10, 5)
rig.transform("offset").pos.to(10, 5)       # Set offset to (10, 5)

# Direction - rotation in degrees
rig.transform("drift").direction.by(15)     # Rotate by 15°
rig.transform("drift").direction.to(15)     # Set rotation to 15°
rig.transform("drift").direction.by(-30)    # Rotate by -30°
```

### Transform Operation Stacking

Transform operations stack by default - calling the same operation multiple times accumulates the effect:

```python
# Each call to .add() stacks
rig.transform("boost").speed.add(10)      # +10
rig.transform("boost").speed.add(10)      # +20 total
rig.transform("boost").speed.add(10)      # +30 total

# Each call to .mul() stacks
rig.transform("sprint").speed.mul(0.5)    # 1.5x total (base 1.0 + 0.5)
rig.transform("sprint").speed.mul(0.5)    # 2.0x total
rig.transform("sprint").speed.mul(0.5)    # 2.5x total

# Limit stacking with .max()
rig.transform("boost").speed.add(10).max(30)        # Cap at +30
rig.transform("boost").speed.add(10).max.stacks(3)  # Max 3 stacks (+30)
```

### Base Rig & Force Semantics

#### `.to(value)` - Set/Replace (Idempotent)
For base rig and forces, `.to()` sets the value. Calling multiple times with the same value has no additional effect.

```python
# Base rig: Set base speed to 10
rig.speed.to(10)
rig.speed.to(10)  # No change, still 10

# Force: Set the force's speed to 5
rig.force("wind").speed.to(5)
rig.force("wind").speed.to(5)  # No change, still 5
```

#### `.by(value)` - Add (Alias for `.add()`)
For base rig and forces, `.by()` adds to the current value.

```python
# Base rig: Add to base speed
rig.speed.by(5)   # Add 5
rig.speed.by(5)   # Add 5 more (10 total added)

# Force: Add to force's speed
rig.force("wind").speed.by(2)  # Add 2
rig.force("wind").speed.by(2)  # Add 2 more
```

**Note**: `.by()` is syntactic sugar for `.add()`. They are functionally identical.

## Timing & Lifecycle

### Duration-Based Transitions

#### `.over(duration_ms, easing?)`
Transition to the target value over a duration with optional easing.

```python
# Smooth speed ramp
rig.speed.to(20).over(1000, "ease_in_out")

# Transform fade-in
rig.transform("sprint").speed.mul(2).over(500)

# Force wind buildup
rig.force("wind").speed.to(10).over(1000, "ease_in")
```

**Easing curves**: `"linear"`, `"ease_in"`, `"ease_out"`, `"ease_in_out"`

### Rate-Based Transitions

#### `.rate(value_per_second)`
Change at a constant rate (no easing, no target value).

```python
# Speed increases at 5 units/second until reaching 10
rig.speed(10).rate(5)

# Transform multiplier increases at 0.1/second until reaching 2
rig.transform("sprint").speed.mul(2).rate(0.1)

# Equivalent with duration-based (for comparison)
rig.transform("sprint").speed.mul(2).over(1000)

# Force speed increases at 2 units/second until reaching 10
rig.force("wind").speed(10).rate(2)
```

**Key difference**: `.over()` has a target and duration, `.rate()` is continuous with no target.

### Lifecycle Methods

#### `.hold(duration_ms)`
Maintain the current value for a duration before proceeding to next lifecycle stage.

```python
# Ramp up, hold, then revert
rig.speed.to(20).over(500).hold(2000).revert(500)

# Transform: fade in, hold, fade out
rig.transform("boost").speed.add(10).over(300).hold(2000).revert(500)
```

#### `.revert(duration_ms?, easing?)`
Return to the state before this operation/entity was applied.

```python
# Instant revert
rig.speed.to(20).hold(1000).revert()

# Smooth revert
rig.speed.to(20).hold(1000).revert(500, "ease_out")

# Transform revert
rig.transform("sprint").speed.mul(2).hold(2000).revert(1000)

# Force revert (removes the force)
rig.force("wind").velocity(5, 0).hold(2000).revert(500)
```

#### `.stop(duration_ms?, easing?)`
Remove the entity/effect. For base rig, means decelerate to zero velocity.

```python
# Stop named transform
rig.transform("sprint").stop()
rig.transform("sprint").stop(500)  # Fade out over 500ms

# Stop named force
rig.force("wind").stop(1000)  # Remove over 1 second

# Stop base rig (decelerate to zero)
rig.stop()              # Instant stop
rig.stop(1000)          # Smooth deceleration over 1s
```

## Anonymous Effects

Operations directly on base rig properties without a name create temporary anonymous effects.

```python
# Temporary speed boost with auto-cleanup
rig.speed.by(10).hold(2000).revert(500)

# This creates an anonymous effect that:
# 1. Instantly adds 10 to speed
# 2. Holds for 2 seconds
# 3. Smoothly reverts over 500ms
# 4. Auto-cleans up when complete
```

Anonymous effects are useful for one-off temporary modifications that don't need a name.

## Complete Examples

### Sprint Toggle (Transform)

```python
def sprint_on():
    """Double speed while sprinting"""
    rig = actions.user.mouse_rig()
    rig.transform("sprint").speed.mul(2)

def sprint_off():
    """Stop sprinting"""
    rig = actions.user.mouse_rig()
    rig.transform("sprint").stop(300)
```

### Boost Pad (Stacking Transform)

```python
def boost_pad():
    """Hit a boost pad - stacks if hit multiple times"""
    rig = actions.user.mouse_rig()
    # Each hit adds 10 speed for 2 seconds
    rig.transform("boost_pad").speed.add(10).hold(2000).revert(1000)
```

### Wind Force

```python
def wind_on():
    """Wind blowing from the right"""
    rig = actions.user.mouse_rig()
    rig.force("wind").velocity(8, 0).over(500, "ease_in")

def wind_off():
    """Stop wind"""
    rig = actions.user.mouse_rig()
    rig.force("wind").stop(1000, "ease_out")
```

### Gravity Force

```python
def gravity_on():
    """Enable downward gravity"""
    rig = actions.user.mouse_rig()
    rig.force("gravity").direction(0, 1).accel(9.8)

def gravity_off():
    """Disable gravity"""
    rig = actions.user.mouse_rig()
    rig.force("gravity").stop(500)
```

### Temporary Boost (Anonymous)

```python
def quick_boost():
    """Quick boost that auto-reverts"""
    rig = actions.user.mouse_rig()
    # Fade in boost, hold 2s, fade out
    rig.speed.by(15).over(300).hold(2000).revert(500, "ease_out")
```

### Smooth Turn

```python
def turn_right():
    """Smooth 90° turn to the right"""
    rig = actions.user.mouse_rig()
    rig.direction.by(90).over(500, "ease_in_out")
```

### Drift (Transform + Direction)

```python
def drift_on():
    """Drift right by 15 degrees"""
    rig = actions.user.mouse_rig()
    rig.transform("drift").direction.add(15).over(300)

def drift_off():
    """Stop drift"""
    rig = actions.user.mouse_rig()
    rig.transform("drift").stop(500)
```

## State Access

### Reading State

```python
rig = actions.user.mouse_rig()

# Base state
speed = rig.state.speed
direction = rig.state.direction  # (x, y) tuple
position = rig.state.pos         # (x, y) tuple
velocity = rig.state.velocity    # (x, y) tuple
accel = rig.state.accel

# Transform state
sprint = rig.state.transforms["sprint"]  # Dict with speed.mul, accel.mul, etc.
sprint_speed_mul = rig.state.transforms["sprint"]["speed"]["mul"]
boost_speed_add = rig.state.transforms["boost"]["speed"]["add"]
drift_direction = rig.state.transforms["drift"]["direction"]

# Force state
wind = rig.state.forces["wind"]  # Dict with velocity, speed, etc.
wind_velocity = rig.state.forces["wind"]["velocity"]
gravity_accel = rig.state.forces["gravity"]["accel"]
```

### Baking State

```python
# Bake all transforms/forces into base state and remove them
rig.bake()

# After baking:
# - All transform multipliers/additions applied to base
# - All forces removed
# - Base state contains the combined result
# - Named entities cleared
```

## Property Reference

### Base Rig Properties

| Property | Type | Description |
|----------|------|-------------|
| `speed` | float | Movement speed magnitude |
| `direction` | (float, float) | Direction vector (x, y) |
| `accel` | float | Acceleration magnitude |
| `pos` | (float, float) | Position (x, y) |
| `velocity` | (float, float) | Velocity vector (x, y) - computed |

### Transform Properties

Transforms can modify:
- `speed` (via `.mul()`, `.add()`, `.sub()`, `.div()`)
- `accel` (via `.mul()`, `.add()`, `.sub()`, `.div()`)
- `pos` (via `.by(x, y)` or `.to(x, y)` for position offset)
- `direction` (via `.by(degrees)` or `.to(degrees)` for rotation)

### Force Properties

Forces have their own independent:
- `speed`
- `direction`
- `accel`
- `velocity`
- `pos` (force attachment point, if needed)

## Design Rationale

### Why Explicit `.transform()` and `.force()`?

**Problem**: `rig("sprint").speed.mul(2)` is ambiguous
- Is "sprint" a transform that multiplies base speed?
- Or a force with its own speed being multiplied from 0?

**Solution**: Make it explicit
- `rig.transform("sprint").speed.mul(2)` - clearly modifies base
- `rig.force("wind").speed(5)` - clearly independent entity

**Tradeoff**: Two extra words to say, but mental model is crystal clear.

### Why No Direct Setters on Transforms?

**Problem**: `rig.transform("sprint").speed(2)` is ambiguous
- Set base to 2?
- Multiply base by 2?
- Add 2 to base?

**Solution**: Force explicit operations
- `rig.transform("sprint").speed.mul(2)` - unambiguous
- `rig.transform("sprint").speed.add(10)` - unambiguous

**Decision**: Transforms use `.mul()`, `.add()`, `.sub()`, `.div()` directly. Operations stack by default - each call accumulates. Use `.max()` or `.max.stacks()` to limit stacking.

### Why Direct Setters on Base & Forces?

**Base Rig**: `rig.speed(10)` is unambiguous - set the base speed to 10. The base rig is the actual state, so setting it is clear.

**Forces**: `rig.force("wind").speed(5)` is unambiguous - the wind force has speed 5. Forces have their own state, so setting it is clear.

### Transform Stacking vs Base/Force `.to()` / `.by()`

**Transforms**: Operations stack by default
- `rig.transform("boost").speed.add(10)` - calling twice = +20 total
- Natural for temporary effects that can be triggered multiple times
- Use `.max()` to prevent unlimited stacking

**Base Rig & Forces**: `.to()` for set, `.by()` for add
- `rig.speed.to(10)` - set speed to 10 (idempotent)
- `rig.speed.by(5)` - add 5 to speed (accumulates)

## Voice Command Mapping

Example Talon voice commands:

```talon
sprint: user.mouse_rig_sprint_on()
sprint off: user.mouse_rig_sprint_off()

boost: user.mouse_rig_boost()
wind: user.mouse_rig_wind_on()
wind off: user.mouse_rig_wind_off()

turn right: user.mouse_rig_turn_right()
turn left: user.mouse_rig_turn_left()

stop: user.mouse_rig_stop()
```

The API is designed to make these actions concise to implement while being explicit about behavior.

## Future Considerations

### Max Constraints

Limit stacking on transforms:

```python
# Limit total value
rig.transform("boost").speed.add(10).max(30)  # Cap at +30

# Limit number of stacks
rig.transform("boost").speed.add(10).max.stacks(3)  # Max 3 stacks = +30
```

**Status**: Deferred to later version. Need use case validation.

### Rate-Based Operations

More sophisticated rate control:

```python
# Speed increases at 5/sec until reaching 20
rig.speed.rate(5).until(20)

# Transform multiplier increases at 0.1/sec
rig.transform("sprint").speed.mul.rate(0.1)
```

**Status**: Deferred to v2. Core duration-based transitions handle most cases.

### Direction as Angle

Currently using vector `(x, y)`. Consider adding angle-based API:

```python
rig.direction.angle(45)  # 45 degrees
rig.direction.angle.by(90)  # Rotate 90 degrees
```

**Status**: Deferred. Vector-based is working well.

## Migration from PRD 6

### Old Syntax (PRD 6)
```python
rig("sprint").scale.speed.to(2)
rig("boost").shift.speed.by(10)
rig("wind").direction(1, 0).velocity(5)
```

### New Syntax (PRD 7)
```python
rig.transform("sprint").speed.mul(2)
rig.transform("sprint").speed.to(2)  # Overwrite example - can be reverted with sprint stop
rig.transform("boost").speed.add(10)  # Stacks by default
rig.force("wind").direction(1, 0).velocity(5)
```

**Key Changes**:
1. Explicit `.transform()` and `.force()` instead of type inference
2. Direct operations (`.mul()`, `.add()`) that stack by default instead of `.scale`/`.shift` keywords
3. Forces remain largely the same (they always had their own state)

## Implementation Notes

### Transform Application Order

Transforms should apply in this order:
1. Multiplicative (`.mul()`, `.div()`)
2. Additive (`.add()`, `.sub()`)

```python
# If both exist:
rig.transform("sprint").speed.mul(2)  # Applied first
rig.transform("boost").speed.add(10)  # Applied second

# Effective calculation:
# final_speed = (base_speed * 2) + 10
```

### Force Vector Summation

Forces are vector-summed with the base rig's resulting velocity:

```python
# Base rig moving right at speed 5
rig.direction(1, 0).speed(5)  # velocity = (5, 0)

# Wind force blowing down
rig.force("wind").velocity(0, 3)  # velocity = (0, 3)

# Final velocity = (5, 0) + (0, 3) = (5, 3)
```

### Anonymous Effect Cleanup

Anonymous effects should auto-cleanup when their lifecycle completes:

```python
rig.speed.by(10).hold(2000).revert(500)

# After 2500ms total:
# - Effect is removed
# - No memory leak
# - No manual cleanup needed
```

## Summary

PRD 7 establishes a clear, unambiguous API for voice-controlled cursor manipulation:

- **Explicit entity types**: `.transform()` and `.force()`
- **Clear operations**: `.mul()`, `.add()`, `.sub()`, `.div()`
- **Direct setters**: Allowed on base & forces, not transforms
- **Timing**: `.over()` for duration, `.rate()` for continuous
- **Lifecycle**: `.hold()`, `.revert()`, `.stop()`
- **Voice-friendly**: Natural to say, easy to remember

The design prioritizes clarity over brevity, enabling mastery through consistent patterns and unambiguous behavior.
