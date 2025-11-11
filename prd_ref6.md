# Mouse Rig API PRD 6

## Overview

Unified API using named entities that infer type (transform vs force) based on operations used:
- **Transforms**: Modify base properties using `scale.*` or `shift.*`
- **Forces**: Independent entities with their own direction/properties
- `.to()` for set/replace operations
- `.by()` for add/stack operations
- `.over()` / `.rate()` for timing
- `.hold()` / `.revert()` for temporary effects

---

## Core Concepts

**Base Rig**: Primary mouse movement state
```python
rig.speed(10)
rig.direction(1, 0)
rig.accel(5)
rig.pos(100, 100)
```

**Transforms**: Modify base properties (no inherent direction, recalculate when base changes)
```python
rig("sprint").scale.speed.to(2)           # Multiply base speed
rig("boost").shift.speed.by(10)           # Add to base speed
```

**Forces**: Independent entities with their own direction and properties
```python
rig("gravity").direction(0, 1).accel(9.8)  # Always pulls down
rig("wind").velocity(5, 0)                 # Independent velocity
```

**Type Inference**: The system determines if an entity is a transform or force based on operations:
- Uses `scale.*` or `shift.*` → Transform
- Sets properties like `direction()`, `speed()`, `velocity()` → Force
- Mixing transform and force operations on same entity → Error

---

## Operations

### Set vs Stack

**`.to(value)`** - Set/replace (idempotent)
```python
rig("a").scale.speed.to(2)    # scale = ×2
rig("a").scale.speed.to(3)    # scale = ×3 (replaced)
```

**`.by(value)`** - Add/stack (accumulates)
```python
rig("b").scale.speed.by(2)    # scale = ×2
rig("b").scale.speed.by(1)    # scale = ×3 (added: 2+1)
```

### For Scalars (speed, accel)

**Scale operations** (multiplicative):
```python
.scale.speed.to(2)      # Set scale to ×2
.scale.speed.by(0.5)    # Add 0.5 to scale multiplier (stacks)
.scale.accel.to(3)      # Set scale to ×3
.scale.accel.by(1)      # Add 1 to scale multiplier (stacks)
```

**Shift operations** (additive):
```python
.shift.speed.to(10)     # Set shift to +10
.shift.speed.by(5)      # Add 5 to shift (stacks)
.shift.accel.to(20)     # Set shift to +20
.shift.accel.by(3)      # Add 3 to shift (stacks)
```

### For Vectors (direction, position)

**Direction** (angles in degrees):
```python
.direction.to(x, y)     # Set to vector
.direction.by(degrees)  # Rotate by degrees (stacks)
```

**Position**:
```python
.pos.to(x, y)          # Set to position
.pos.by(x, y)          # Offset by vector (stacks)
```

---

## Transform Examples

### Scale (Multiplicative)

```python
rig.speed(10)

# Sprint - double speed
rig("sprint").scale.speed.to(2)
# Computed: 10 × 2 = 20

# Call again with different value - replaces
rig("sprint").scale.speed.to(3)
# Computed: 10 × 3 = 30

# Using .by() to stack
rig("stack").scale.speed.by(2)    # ×2
rig("stack").scale.speed.by(1)    # ×3 (added 2+1)
# Computed: 10 × 3 = 30
```

### Shift (Additive)

```python
rig.speed(10)

# Boost - add 5
rig("boost").shift.speed.to(5)
# Computed: 10 + 5 = 15

# Hit another boost pad - stacks
rig("boost").shift.speed.by(5)
# Computed: 10 + 5 + 5 = 20

# Set to specific value - replaces
rig("boost").shift.speed.to(15)
# Computed: 10 + 15 = 25
```

### Combined Scale + Shift

When a transform has both scale and shift on the same property:
```python
rig.speed(10)

rig("combo").scale.speed.to(2)     # ×2
rig("combo").shift.speed.to(5)     # +5

# Application order: scale first, then shift
# Computed: (10 × 2) + 5 = 25
```

**Rule**: Scale always applies before shift within a transform.

---

## Force Examples

### Independent Velocity

```python
# Base movement - going right
rig.speed(10).direction(1, 0)
# Base velocity: (10, 0)

# Wind force - pushing down
rig("wind").velocity(0, 5)
# Wind velocity: (0, 5)

# Final velocity: (10, 0) + (0, 5) = (10, 5)
# Via vector addition
```

### Gravity

```python
# Gravity - constant downward acceleration
rig("gravity").direction(0, 1).accel(9.8)
# Always accelerates downward at 9.8

# Later, disable gravity
rig("gravity").stop()
```

### Setting Force Properties

```python
# Method 1: Direct velocity vector
rig("wind").velocity(5, 3)

# Method 2: Direction + speed
rig("wind").direction(1, 0).speed(5)
# Combines to velocity (5, 0)

# Both work, use whichever is clearer
```

---

## Timing

### Time-based: `.over(duration, easing?)`
```python
rig("sprint").scale.speed.to(2).over(500)
# Fade in over 500ms

rig.direction.to(1, 0).over(1000, "ease_out")
# Smooth turn over 1s
```

### Rate-based: `.rate(value)`
```python
rig.direction.by(90).rate(45)
# Rotate at 45°/sec (takes 2 seconds)

rig.speed.to(50).rate(10)
# Increase speed at 10/sec
```

**Note**: Rate does not support easing - constant rate of change.

---

## Temporary Effects

### Lifecycle

```python
.hold(duration)          # Maintain value for duration
.revert(duration?, easing?)  # Return to original state
```

**Timeline**: apply → hold (optional) → revert

### Examples

```python
# Boost pad - instant apply, hold, fade out
rig("boost").shift.speed.by(10).hold(2000).revert(1000)

# Sprint with fade in/out
rig("sprint").scale.speed.to(2).over(300).hold(1000).revert(500)

# Temporary force
rig("wind").velocity(5, 0).hold(3000).revert(1000)
```

**With lifecycle** (`.hold()` or `.revert()`): Entity auto-removes after completion
**Without lifecycle**: Entity persists until explicitly stopped

---

## Stopping

### Stop Specific Entity

```python
rig("sprint").stop()              # Instant removal
rig("sprint").stop(500)           # Fade out over 500ms
rig("sprint").stop(500, "ease_out")  # With easing
```

### Stop All

```python
rig.stop_all()           # Stop all transforms and forces
rig.stop_all(500)        # Fade all out over 500ms
```

### Global Stop

```python
rig.stop()               # Bake state, clear all, speed=0 (instant)
rig.stop(500)            # Bake, clear, decelerate over 500ms
```

---

## Constraints & Max Values

### Max Speed/Accel

```python
# Max final computed value
rig("boost").shift.speed.by(10).max.speed(50)
# Even if stacks go higher, caps at 50

rig("boost").shift.accel.by(5).max.accel(20)
# Caps acceleration at 20
```

### Max Stack Count

```python
# Limit number of stacks
rig("boost").shift.speed.by(10).max.stack(3)
# Only first 3 calls will stack, 4th ignored
```

### Shorthand

```python
# If context is clear, can use .max(value)
rig("boost").shift.speed.by(10).max(50)
# Infers max.speed since operating on speed
```

---

## State Management

### Reading State

```python
# Computed state (base + transforms + forces)
rig.state.speed         # Total computed speed
rig.state.accel         # Total computed acceleration
rig.state.direction     # Current direction
rig.state.pos           # Current position
rig.state.velocity      # Total velocity vector

# Base values only
rig.base.speed
rig.base.accel
rig.base.direction
rig.base.pos

# Property getter (returns base)
rig.speed()             # Returns base speed
```

### Baking

```python
# Flatten all transforms/forces into base, clear all
rig.bake()

# Example:
rig.speed(10)
rig("sprint").scale.speed.to(2)     # computed = 20
rig("boost").shift.speed.to(5)      # computed = 25
rig("wind").velocity(3, 0)          # velocity = (25, 0) + (3, 0) = (28, 0)

rig.bake()
# Now: base.velocity = (28, 0)
# All transforms and forces cleared
```

---

## Composition & Pipeline

### Transform Composition

Multiple transforms on the same entity accumulate:
```python
rig("combo").scale.speed.to(2)      # ×2
rig("combo").scale.speed.by(1)      # ×3 (added 2+1)
rig("combo").shift.speed.to(10)     # +10

# Within entity: scale applies before shift
# Result: (base × 3) + 10
```

Multiple transforms compose sequentially (order of creation):
```python
rig("first").scale.speed.to(2)      # Created first
rig("second").shift.speed.to(5)     # Created second

# Pipeline: base → first (×2) → second (+5)
# Result: (base × 2) + 5
```

### Transform vs Force Pipeline

Fixed pipeline order:
```
Base State
    ↓
Transform 1 (modifies base)
    ↓
Transform 2 (modifies result of transform 1)
    ↓
Transform N
    ↓
Force 1 (adds independent vector)
    ↓
Force 2 (adds independent vector)
    ↓
Force N
    ↓
Final State
```

**Example**:
```python
rig.speed(10).direction(1, 0)           # base velocity: (10, 0)
rig("sprint").scale.speed.to(2)         # transform: (20, 0)
rig("wind").velocity(0, 5)              # force: add (0, 5)
# Final: (20, 0) + (0, 5) = (20, 5)
```

### Transform Recalculation

Transforms recalculate when base changes:
```python
rig.speed(10)
rig("sprint").scale.speed.to(2)
# Computed: 20

rig.speed(20)  # Change base
# Computed: 40 (transform recalculates)
```

Forces remain constant regardless of base:
```python
rig.speed(10).direction(1, 0)
rig("wind").velocity(5, 0)
# velocity: (10, 0) + (5, 0) = (15, 0)

rig.speed(20)  # Change base
# velocity: (20, 0) + (5, 0) = (25, 0)
# Wind stays at (5, 0)
```

---

## Anonymous Entities

Support for unnamed entities (auto-cleanup with lifecycle):

```python
# Anonymous transform
rig.speed.by(10).hold(2000).revert(1000)
# System auto-names (e.g., "anon_1")
# Auto-removes after lifecycle

# Anonymous force
rig.velocity(5, 0).hold(1000).revert(500)
# Auto-named and auto-removed
```

**Use cases**:
- One-off temporary effects (boost pads)
- Fire-and-forget behaviors
- No need to track/stop manually

---

## Complete Examples

### WASD Movement with Sprint

```python
# Press W - move up
rig.direction(0, -1)
rig.speed(10)

# Press Shift - sprint (toggle)
rig("sprint").scale.speed.to(2)
# Now: 10 × 2 = 20

# Release Shift
rig("sprint").stop()
# Back to: 10
```

### Boost Pad (Stacking)

```python
# Hit first boost pad
rig("boost_pad").shift.speed.by(5).hold(2000).revert(1000)
# +5 for 2s, fade out over 1s

# Hit second pad while first active
rig("boost_pad").shift.speed.by(5).hold(2000).revert(1000)
# Now +10 total (stacks)

# Hit third pad
rig("boost_pad").shift.speed.by(5).hold(2000).revert(1000)
# Now +15 total

# After 2s, all start fading out
# After 3s, all cleared
```

### Gravity + Wind

```python
# Base movement - going right
rig.speed(10).direction(1, 0)
# velocity: (10, 0)

# Enable gravity
rig("gravity").direction(0, 1).accel(9.8)
# Always accelerates down

# Wind gust
rig("wind").velocity(5, 0).hold(3000).revert(1000)
# Pushes right for 3s, fades over 1s

# Total velocity includes all forces via vector addition
```

### Acceleration Burst

```python
rig.accel(5)

# Temporarily boost acceleration
rig("accel_boost").scale.accel.to(3).hold(1000).revert(500)
# accel: 5 × 3 = 15 for 1s, then fade back over 500ms
```

### Drift Turn

```python
# Moving right
rig.direction(1, 0).speed(10)

# Add upward drift
rig("drift").shift.direction.by(-15)
# Rotates direction by -15° while active

# Stop drift
rig("drift").stop(500)
# Smoothly rotate back over 500ms
```

### Complex Combo

```python
# Base state
rig.speed(10).direction(1, 0)

# Permanent sprint modifier
rig("sprint").scale.speed.to(2)
# Computed: 20

# Temporary boost
rig().shift.speed.by(10).hold(1000).revert(500)
# Computed: (10 × 2) + 10 = 30

# Add gravity force
rig("gravity").velocity(0, 9.8)
# velocity: (30, 0) + (0, 9.8) = (30, 9.8)

# After boost fades
# velocity: (20, 0) + (0, 9.8) = (20, 9.8)
```

---

## Error Cases

### Mixing Transform and Force Operations

```python
# Error: Can't mix transform and force operations
rig("bad").scale.speed.to(2)      # Locks to transform mode
rig("bad").direction(1, 0)        # ERROR: transforms can't set direction

rig("bad2").velocity(5, 0)        # Locks to force mode
rig("bad2").shift.speed.by(5)    # ERROR: forces can't use shift/scale
```

### Transform Setting Direction

```python
# Error: Transforms don't have inherent direction
rig("sprint").scale.speed.to(2)
rig("sprint").direction(1, 0)     # ERROR
```

**Why**: Transforms modify base properties, they don't have their own direction.
If you need direction, use a force.

---

## Key Design Decisions

| Aspect | Decision |
|--------|----------|
| **Type inference** | Presence of `scale.*`/`shift.*` vs direct properties |
| **`.to()` behavior** | Set/replace value (idempotent) |
| **`.by()` behavior** | Add/stack value (accumulates) |
| **Transform recalculation** | Always recalculate when base changes |
| **Force behavior** | Independent, constant regardless of base |
| **Scale + shift order** | Scale first, then shift |
| **Transform composition** | Sequential (order of creation matters) |
| **Pipeline order** | Base → Transforms → Forces → Final |
| **Anonymous entities** | Supported via `rig()` without name |
| **Lifecycle cleanup** | Auto-remove when `.hold()` or `.revert()` used |
| **Stop behavior** | Instant or fade with optional duration |
| **Max constraints** | Per-property or per-stack-count |

---

## Easing

All timing methods support optional easing:

```python
"linear"
"ease_in"
"ease_out"
"ease_in_out"
```

**Examples**:
```python
rig("sprint").scale.speed.to(2).over(500, "ease_in")
rig("boost").shift.speed.by(10).hold(1000).revert(500, "ease_out")
rig.direction.to(1, 0).over(1000, "ease_in_out")
```

**Note**: `.rate()` does not support easing (constant rate of change).

---

## Summary Table

| Feature | Syntax | Notes |
|---------|--------|-------|
| Base properties | `rig.speed(10)` | Permanent changes |
| Transform (scale) | `rig("name").scale.speed.to(2)` | Multiply base |
| Transform (shift) | `rig("name").shift.speed.by(10)` | Add to base |
| Force | `rig("name").velocity(5, 0)` | Independent vector |
| Set/replace | `.to(value)` | Idempotent |
| Add/stack | `.by(value)` | Accumulates |
| Time-based | `.over(duration, easing?)` | Animate over time |
| Rate-based | `.rate(value)` | Change at fixed rate |
| Hold | `.hold(duration)` | Maintain for duration |
| Revert | `.revert(duration?, easing?)` | Return to original |
| Stop entity | `rig("name").stop(duration?, easing?)` | Remove entity |
| Stop all | `rig.stop_all(duration?)` | Clear all entities |
| Bake | `rig.bake()` | Flatten to base |
| Global stop | `rig.stop(duration?)` | Bake, clear, decelerate |
| Max value | `.max.speed(value)` or `.max(value)` | Cap computed value |
| Max stacks | `.max.stack(count)` | Limit stack count |
| Anonymous | `rig().shift.speed.by(10)...` | Auto-named, auto-cleanup |
| State (computed) | `rig.state.speed` | Includes transforms/forces |
| State (base) | `rig.base.speed` | Base only |

---

## Differences from PRD 5

1. **Unified API**: `rig(name)` instead of separate `rig.modifier()` and `rig.force()`
2. **Type inference**: System determines transform vs force based on operations used
3. **Scale/shift separation**: Explicit `scale.*` and `shift.*` keywords for transforms
4. **Stacking with `.by()`**: Consistent add/stack behavior across all properties
5. **Max constraints**: Added `.max.speed()`, `.max.stack()`, etc.
6. **Anonymous entities**: Support for `rig()` without name for auto-cleanup
7. **Clearer composition**: Explicit scale-before-shift rule within transforms
8. **Error on mixing**: Can't mix transform and force operations on same entity
