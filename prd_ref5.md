# Mouse Rig API PRD 5

## Overview

Simplified API using `speed`, `accel`, `direction` primitives with:
- `.over()` for time-based changes
- `.rate()` for rate-based changes
- `.hold()` and `.revert()` for temporary effects
- Named effects (modifiers on base)
- Named forces (independent entities)
- Baking/flattening for state management

---

## Core Concepts

**Base Rig**: The primary mouse movement state (speed, direction, accel, position)

**Effects**: Named modifiers that transform base properties (multiply, add, etc.)

**Forces**: Named independent entities with their own speed/direction/accel that combine with base via vector addition

**Temporary Changes**: Auto-remove via `.revert()` - can be used on base rig, effects, or forces

---

## Property Access

```python
rig.pos        # position (x, y)
rig.speed      # speed scalar
rig.accel      # acceleration scalar
rig.direction  # direction vector (x, y)
```

---

## Value Modifiers

Different properties support different modifiers:

### Speed & Accel (scalars)
```python
.to(value)     # set to absolute value
.by(delta)     # add/subtract relative value
.mul(factor)   # multiply by factor
.div(divisor)  # divide by divisor
```

### Direction (vector/angle)
```python
.to(x, y)      # set to vector
.by(degrees)   # rotate by degrees
```

### Position (vector)
```python
.to(x, y)      # set to position
.by(x, y)      # offset by vector
```

---

## Timing

### Time-based: `.over(duration, easing?)`
Animate change over specified duration (milliseconds)

```python
rig.speed.to(20).over(1000)                    # reach 20 in 1 second
rig.direction.by(90).over(500, "ease_out")     # rotate over 500ms with easing
rig.pos.to(100, 200).over(2000)                # move to position in 2 seconds
```

### Rate-based: `.rate(value)` or `.rate.property(value)`
Change at specified rate (duration derived from distance to target)

**Note**: Rate does not support easing - it applies a constant rate of change.

#### Simple Rate (context-aware)
When the rate type matches the property being changed:

```python
# Speed changes - rate is speed/sec
rig.speed.to(50).rate(10)           # increase speed at 10/sec (takes 5s if starting from 0)

# Accel changes - rate is accel/sec²
rig.accel.to(20).rate(5)            # increase accel at 5/sec² (takes 4s if starting from 0)

# Direction changes - rate is degrees/sec
rig.direction.by(90).rate(45)       # rotate at 45°/sec (takes 2s)
```

#### Explicit Rate Type (when rate differs from target)
Use `.rate.property()` to specify a different rate type:

```python
# Change speed via acceleration rate
rig.speed.to(50).rate.accel(10)     # accelerate at 10/sec² until reaching speed 50

# Change accel via jerk rate (rate of accel change)
rig.accel.to(20).rate.accel(5)      # change accel at 5/sec² (jerk)

# Move position at specific speed
rig.pos.to(100, 100).rate.speed(50) # move at 50 px/sec (temporary speed, doesn't affect base)
```

**Available rate types**:
- `.rate.speed(value)` - rate in speed units per second
- `.rate.accel(value)` - rate in accel units per second (acceleration)

---

## Temporary Effects

### Lifecycle
```python
.hold(duration)          # maintain value for duration
.revert(duration?, easing?)  # return to original state
```

**Rules**:
- Presence of `.revert()` or `.hold()` = temporary (auto-removes after lifecycle)
- `.hold()` alone = hold then instant revert
- `.hold().revert(duration)` = hold then gradual revert
- No `.hold()` or `.revert()` = permanent change
- Timeline sequence: apply → hold (optional) → revert

### Examples

```python
# Immediate application, revert over 500ms
rig.speed.mul(2).revert(500)

# Hold for 1s, then instant revert
rig.speed.mul(2).hold(1000)

# Fade in over 300ms, instant revert
rig.speed.mul(2).over(300).revert()

# Fade in, fade out
rig.speed.mul(2).over(300).revert(500)

# Full envelope: fade in, hold, fade out
rig.speed.mul(2).over(300).hold(1000).revert(500, "ease_in")

# Rate-based with hold and revert
rig.direction.by(90).rate(45).hold(2000).revert(1000)
```

---

## Named Effects (Modifiers)

Effects modify base rig properties using relative operations (`.mul()`, `.by()`, `.div()`).
They stay active until explicitly stopped.

### Creating Effects
```python
rig.effect("boost").speed.mul(2)              # multiply base speed by 2
rig.effect("drift").direction.by(15)          # rotate base direction by 15°
rig.effect("slow").speed.mul(0.5)             # half the base speed
```

### Effect Composition
Effects recalculate when base changes:

```python
rig.speed(10)                                 # base = 10
rig.effect("boost").speed.mul(2)              # total = 20
rig.speed(20)                                 # change base = 20
# boost recalculates: total = 40
```

### Stopping Effects
```python
# Stop specific effect
rig.effect("boost").stop()                    # immediate stop
rig.effect("boost").stop(500)                 # stop over 500ms
rig.effect("boost").stop(500, "ease_in_out")  # with easing

# Stop all effects
rig.effect.stop_all()
rig.effect.stop_all(1000)                     # all effects stop over 1s
```

### Imperative Control Pattern
Named effects are designed for imperative control (like key press/release):

```python
# Key down - apply effect (repeatable)
rig.effect("thrust").accel(10).rate(20)       # ramp to 10 at rate 20/sec
rig.effect("thrust").accel(10).rate(20)       # continue/maintain
rig.effect("thrust").accel(10).rate(20)       # still maintaining

# Key up - stop effect
rig.effect("thrust").stop(2000)               # graceful stop over 2s
```

### Constraints
Effects can **only** use relative modifiers:
- ✓ `.mul()`, `.by()`, `.div()`
- ✗ `.to()` or absolute setters - will raise an error (use forces for absolute values)

```python
# Valid
rig.effect("boost").speed.mul(2)        # ✓ relative modifier
rig.effect("drift").direction.by(15)    # ✓ relative modifier

# Invalid - will error
rig.effect("boost").speed.to(20)        # ✗ ERROR: effects cannot use .to()
rig.effect("boost").speed(20)           # ✗ ERROR: effects cannot use absolute setters
```

---

## Named Forces (Independent Entities)

Forces are independent entities with their own speed, direction, and accel.
They combine with base rig via vector addition.

### Creating Forces
```python
# Gravity - constant downward pull
gravity = rig.force("gravity")
gravity.speed(9.8)
gravity.direction(0, 1)

# Wind - push from left
wind = rig.force("wind")
wind.speed(5).direction(-1, 0)

# With timing
rig.force("magnet").speed(10).direction(0.7, 0.7).over(1000)
```

### Force Composition
Forces maintain their values regardless of base changes:

```python
rig.speed(10).direction(1, 0)                 # base: moving right at 10
rig.force("wind").speed(5).direction(0, 1)    # force: down at 5
# Result: vector (10, 0) + vector (0, 5) = (10, 5)

rig.speed(20)                                 # change base to 20
# Force unchanged: vector (20, 0) + vector (0, 5) = (20, 5)
```

### Stopping Forces
```python
# Stop specific force
rig.force("wind").stop()
rig.force("wind").stop(1000, "ease_out")

# Stop all forces
rig.force.stop_all()
rig.force.stop_all(500)
```

### Constraints
Forces can **only** use absolute setters:
- ✓ `.to()` or direct setters like `.speed(value)`
- ✗ `.mul()`, `.by()`, `.div()` - will raise an error (use effects for relative operations)

```python
# Valid
rig.force("wind").speed(5)              # ✓ absolute setter
rig.force("wind").direction.to(0, 1)    # ✓ absolute setter

# Invalid - will error
rig.force("wind").speed.mul(2)          # ✗ ERROR: forces cannot use .mul()
rig.force("wind").speed.by(10)          # ✗ ERROR: forces cannot use .by()
```

---

## State Management

### Reading State

**Note**: Currently implemented as a dictionary, but should be converted to a class/object for better IDE support, autocomplete, and type safety.

```python
# Current computed values (base + effects + forces)
rig.state.speed         # total computed speed
rig.state.accel         # total computed accel
rig.state.direction     # combined direction vector
rig.state.pos           # current position

# Base values only
rig.base.speed
rig.base.accel
rig.base.direction
rig.base.pos
```

### Baking/Flattening
Collapse current computed state into base, removing all effects and forces:

```python
# Setup
rig.speed(10)
rig.effect("boost").speed.mul(2)              # computed speed = 20
rig.force("wind").speed(5).direction(0, 1)    # adds vector

# Bake
rig.bake()
# Now: base.speed = 20, base.direction = combined vector
# All effects and forces cleared
```

### Global Stop
Stop everything and bring rig to rest:

```python
rig.stop()              # immediate stop: bakes state, clears effects/forces, sets speed to 0
rig.stop(500)           # bakes, clears, then decelerates to 0 over 500ms
rig.stop(1000, "ease_out")  # with easing
```

**`rig.stop()` behavior**:
1. Computes final state (base + effects + forces)
2. Flattens to base
3. Clears all effects and forces
4. Decelerates speed to 0 (over duration if specified)

---

## Complete Examples

### Speed Boost Pads
```python
# Instant boost, hold, fade out
rig.speed.mul(1.5).hold(2000).revert(1000)

# Fade in, hold, fade out
rig.speed.mul(2).over(300).hold(1000).revert(500)
```

### Thrust/Acceleration Control
```python
# Key down (repeatable - can call multiple times)
rig.effect("thrust").accel(10).rate(20)

# Key up
rig.effect("thrust").stop(2000, "ease_in")
```

### Gravity Effect
```python
gravity = rig.force("gravity")
gravity.speed(9.8)
gravity.direction(0, 1)

# Later, remove gravity
gravity.stop(500)
```

### Direction Changes
```python
# Temporary rotation
rig.direction.by(45).over(500).hold(1000).revert(500)

# Permanent rotation
rig.direction.by(90).over(1000)

# Rate-based rotation
rig.direction.by(180).rate(30)  # rotate at 30°/sec
```

### Complex Scenario
```python
# Base movement (separate calls - chaining not supported)
rig.speed(20)
rig.direction(-1, 0)

# Accel boost with decay
rig.effect("accel_boost").accel(10).over(500).hold(1000).revert(1500)

# Turn base rig
rig.direction.by(45).over(300)

# Quick speed boost during turn
rig.effect("quick_boost").speed.mul(1.5).hold(200).revert(100)

# Flatten and stop
rig.bake()
rig.accel(0)
rig.stop(500)
```

**Note**: Property setters return their builders, so `rig.speed(20).direction(-1, 0)` won't work. Use separate calls or consider throwing a helpful error if chaining is attempted.

### Boost Based on Current Speed
```python
# Option 1: Read state explicitly
current = rig.state.speed
rig.speed.by(current * 0.5).revert(1000)  # +50% boost, fade over 1s

# Option 2: Use lambda for dynamic calculation
rig.speed.by(lambda state: state.speed * 0.5).revert(1000)  # evaluated at execution time
```

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
rig.speed.to(20).over(1000, "ease_out")
rig.effect("boost").speed.mul(2).over(300, "ease_in").revert(500, "ease_out")
rig.direction.by(90).rate(45)  # rate does not support easing
```

---

## Summary Table

| Feature | Syntax | Notes |
|---------|--------|-------|
| Base properties | `rig.speed(10)` | Permanent changes to base rig |
| Temporary on base | `rig.speed.mul(2).revert(500)` | Auto-removes after lifecycle |
| Named effects | `rig.effect("boost").speed.mul(2)` | Modifiers on base (relative ops only) |
| Named forces | `rig.force("wind").speed(5)` | Independent entities (absolute only) |
| Time-based | `.over(duration, easing?)` | Animate over fixed duration |
| Rate-based | `.rate(value)` | Change at fixed rate (no easing) |
| Hold state | `.hold(duration)` | Maintain for duration |
| Auto-revert | `.revert(duration?, easing?)` | Return to original |
| Stop effect | `rig.effect("name").stop(duration?, easing?)` | Remove effect |
| Stop force | `rig.force("name").stop(duration?, easing?)` | Remove force |
| Stop all effects | `rig.effect.stop_all(duration?, easing?)` | Clear all effects |
| Stop all forces | `rig.force.stop_all(duration?, easing?)` | Clear all forces |
| Bake state | `rig.bake()` | Flatten to base, clear all |
| Global stop | `rig.stop(duration?, easing?)` | Bake, clear, decelerate to 0 |
| Read computed | `rig.state.speed` | Total with effects/forces |
| Read base | `rig.base.speed` | Base value only |

---

## Key Distinctions

**Permanent vs Temporary**:
- No `.revert()` or `.hold()` = permanent
- With `.revert()` or `.hold()` = temporary (auto-removes)
- `.hold()` alone implies instant revert after hold period

**Effects vs Forces**:
- Effects = modifiers on base (`.mul()`, `.by()`, `.div()`)
- Forces = independent entities (absolute values only)
- Effects recalculate when base changes
- Forces remain constant regardless of base

**`.over()` vs `.rate()`**:
- `.over(duration)` = time is input, change happens in fixed time, supports easing
- `.rate(value)` = rate is input, time varies based on distance, no easing (constant rate)

**Named vs Anonymous**:
- Named: `rig.effect("boost")` or `rig.force("wind")` - can be stopped explicitly
- Anonymous: `rig.speed.mul(2).revert(500)` - fire-and-forget, auto-cleanup
