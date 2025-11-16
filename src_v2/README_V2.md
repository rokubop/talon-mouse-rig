# Mouse Rig V2

**Unity above all else.** One builder type. One state manager. One execution model.

## What's New in V2

### Complete Architectural Redesign

V2 is a ground-up rebuild with a unified philosophy:

- **Single Builder Type**: `RigBuilder` handles ALL operations (speed, direction, position, acceleration)
- **No Distinction**: No separate "effects" vs "base rig" vs "forces" - everything is a builder
- **Unified Execution**: All builders execute on `__del__` (garbage collection)
- **Order-Agnostic**: Call fluent methods in any order (except lifecycle must be sequential)
- **Simplified State**: Base state + active builders = current state

### What Was Kept from V1

Critical low-level utilities proven to work:
- **Vec2 class** for 2D vector math
- **Easing functions** (linear, ease_in, ease_out, ease_in_out, smoothstep)
- **Mouse movement API** with platform detection (Talon vs Windows raw input)
- **SubpixelAdjuster** for smooth fractional movement
- **Rate calculation logic** for time vs rate-based transitions

### What Was Redesigned

Everything architectural:
- **State Management**: Single unified structure (no separate effect lists)
- **Builder System**: One `RigBuilder` class instead of builder hierarchy
- **Lifecycle**: Unified manager for over/hold/revert phases
- **Queue System**: Single implementation for all behavior modes
- **Frame Loop**: Simplified update cycle

## Quick Start

```python
from src_v2 import rig

# Basic movement
r = rig()
r.speed.to(10)
r.direction(1, 0)  # Start moving right

# Temporary boost
r.speed.add(10).hold(2000)

# Named effect with lifecycle
r.tag("sprint").speed.mul(2).over(500).hold(3000).revert(500)

# Stop
r.stop(1000)  # Smooth stop over 1 second
```

## Core Concepts

### 1. Universal Builder

There is only ONE builder type: `RigBuilder`. All fluent methods return `RigBuilder`.

```python
r = rig()
r.speed.add(5)           # RigBuilder
r.direction.by(90)       # RigBuilder
r.tag("x").speed.mul(2)  # RigBuilder
r.stack().pos.to(0, 0)   # RigBuilder
```

### 2. Execution Model

Builders execute when garbage collected (`__del__`):

```python
def my_action():
    r = rig()
    r.speed.to(10)
    # Executes HERE when builder goes out of scope
```

### 3. Execution Order

- **Anonymous builders** (no tag) execute FIRST
- **Tagged builders** execute AFTER anonymous

This ensures base modifications happen before named effects.

### 4. State Composition

Current state = Base state + All active builders (in order)

```python
# Base speed: 5
r = rig()
r.speed.add(10)          # Anonymous: 5 + 10 = 15
r.tag("boost").speed.mul(2)  # Tagged: 15 * 2 = 30
# Final speed: 30
```

## Builder Requirements

Every builder must have:

**1 Property** × **1 Operator** × **(optional) Lifecycle** × **(optional) Behavior** × **(optional) Tag**

### Properties

- `pos` - Position (x, y)
- `speed` - Speed magnitude
- `direction` - Direction vector/angle
- `accel` - Acceleration magnitude

Special shortcuts:
- `rig.stop(ms?)` - Speed to 0
- `rig.reverse(ms?)` - 180° turn
- `rig.bake()` - Commit all to base

### Operators

- `.to(value)` - Set absolute
- `.add(value)` / `.by(value)` - Add delta (aliases)
- `.sub(value)` - Subtract
- `.mul(value)` - Multiply
- `.div(value)` - Divide

Shorthand (anonymous only):
```python
r.speed(10)      # Shorthand for r.speed.to(10)
r.direction(1, 0)  # Shorthand for r.direction.to(1, 0)
```

### Lifecycle (Optional)

Control timing of changes:

- `.over(ms, easing?)` - Transition duration
- `.over(rate=X)` - Rate-based transition
- `.hold(ms)` - Sustain duration
- `.revert(ms?, easing?)` - Fade out duration
- `.revert(rate=X)` - Rate-based revert
- `.then(callback)` - Execute callback after current stage

**Order**: `over` → `then`* → `hold` → `then`* → `revert` → `then`*

**Time-based**:
```python
r.speed.to(10).over(500)  # 500ms transition
r.speed.add(5).over(300).hold(2000).revert(500)
```

**Rate-based**:
```python
r.speed.to(10).over(rate=5)        # 5 units/sec
r.direction.by(90).over(rate=45)   # 45 degrees/sec
r.pos.to(960, 540).over(rate=200)  # 200 pixels/sec
```

### Behavior (Optional)

What happens on repeat calls:

- `.stack(max?)` - Stack effects (unlimited or max)
- `.replace()` - Cancel previous
- `.queue()` - Wait for current to finish
- `.extend()` - Extend hold duration
- `.throttle(ms)` - Rate limit
- `.ignore()` - Ignore while active

Defaults:
- **Anonymous**: `.stack()` (unlimited)
- **Tagged**: `.stack()` (unlimited)

Can use as property or method:
```python
r.stack.speed.add(5)      # Property
r.stack(3).speed.add(5)   # Method with args
```

### Tag (Optional)

Name the builder for identity and control:

```python
r.tag("sprint").speed.mul(2)

# Later, cancel it
r.tag("sprint").revert(500)
```

Anonymous builders get auto-generated tags (`__anon_1`, `__anon_2`, etc.)

### Bake (Optional)

Control persistence:

- `bake=true` - Changes merge into base state (permanent)
- `bake=false` - Changes remain reversible

Defaults:
- **Anonymous**: `bake=true`
- **Tagged**: `bake=false`

```python
r.speed.add(5)  # Anonymous - becomes permanent
r.tag("boost").speed.add(10)  # Tagged - reversible
r.tag("boost").speed.add(10).bake(true)  # Force permanent
```

## Order-Agnostic API

Call fluent methods in ANY order (except lifecycle must be sequential):

```python
# All equivalent
r.speed.add(5).over(300).tag("x")
r.tag("x").speed.add(5).over(300)
r.over(300).tag("x").speed.add(5)
r.tag("x").over(300).speed.add(5)

# Lifecycle MUST be ordered
r.speed.add(5).over(300).hold(1000).revert(500)  # ✅
r.speed.add(5).revert(500).over(300)             # ❌
```

## Examples

### Basic Movement

```python
r = rig()
r.direction(1, 0)
r.speed(10)
```

### Temporary Boost

```python
r = rig()
r.speed.add(10).hold(2000)  # +10 speed for 2 seconds
```

### Named Sprint

```python
r = rig()
r.tag("sprint").speed.mul(2).over(500).hold(3000).revert(500)

# Cancel early
r.tag("sprint").revert(500)
```

### Stacking

```python
# Unlimited (default)
r = rig()
r.speed.add(5)  # Call multiple times to stack

# Limited
r.tag("rage").speed.add(5).stack(3)  # Max 3 stacks
```

### Queuing

```python
r = rig()
r.tag("combo").pos.by(100, 0).queue().over(500)
r.tag("combo").pos.by(0, 100).queue().over(500)
# Second waits for first
```

### Complex Lifecycle

```python
r = rig()
r.speed.add(10)\
    .over(300).then(lambda: print("ramped"))\
    .hold(2000).then(lambda: print("holding"))\
    .revert(500).then(lambda: print("done"))
```

### Position Movement

```python
# Move to screen center
r.pos.to(960, 540).over(1000, "ease_in_out")

# Offset and return
r.pos.by(50, 0).over(200).hold(1000).revert(200)
```

## State Access

```python
r = rig()

# Current computed state (base + all active)
current_speed = r.state.speed
current_pos = r.state.pos
current_direction = r.state.direction

# Base state only (baked values)
base_speed = r.base.speed
base_pos = r.base.pos
```

## Architecture

### File Structure

```
src_v2/
  __init__.py        # Main API entry point
  contracts.py       # All interfaces/protocols
  core.py           # Reused utilities (Vec2, easing, mouse, subpixel)
  rate_utils.py     # Rate calculations
  lifecycle.py      # Lifecycle manager (over/hold/revert)
  queue.py          # Queue system
  state.py          # Unified state manager
  builder.py        # RigBuilder (universal builder)
```

### Key Classes

- **`RigBuilder`**: The universal builder - all fluent methods return this
- **`RigState`**: Global state manager (base + active builders)
- **`Lifecycle`**: Manages over/hold/revert phases
- **`ActiveBuilder`**: A builder being executed in the state
- **`PropertyAnimator`**: Handles value interpolation during lifecycle

### Execution Flow

1. User creates builder: `r.speed.add(5).over(300)`
2. Python creates `RigBuilder` with configuration
3. Builder goes out of scope
4. `__del__` called → validation → execution
5. `ActiveBuilder` created and added to state
6. Frame loop updates all active builders
7. State composed: base + all active → move mouse

## Migration from V1

V2 is NOT backward compatible. Key differences:

| V1 | V2 |
|----|-----|
| `rig.speed(10)` | `rig.speed(10)` (same) |
| `rig.speed.add(5, hold=2000)` | `rig.speed.add(5).hold(2000)` |
| `rig.effect().speed.add(5)` | `rig.speed.add(5)` (no separate effect) |
| `rig.force("boost").add(5)` | `rig.tag("boost").speed.add(5)` |
| Multiple builder types | Single `RigBuilder` |

## Design Principles

1. **Unity**: One builder type, one execution model
2. **Simplicity**: No special cases between effects/base/forces
3. **Composition**: State = base + ordered builders
4. **Explicitness**: No magic, clear execution order
5. **Flexibility**: Order-agnostic API for ergonomics

## Success Criteria

✅ Single unified builder type (`RigBuilder`)  
✅ No distinction between "effects" and "base rig" in API  
✅ Order-agnostic fluent API (except lifecycle)  
✅ Clean execution model (del-based)  
✅ Simple state management (base + active builders)  
✅ Behavior system works for all builders  
✅ Bake system provides persistence control  
✅ Reuses proven V1 utilities (SubpixelAdjuster, Vec2, easing)  

## Performance

- Frame loop: 60 FPS (~16.67ms per frame)
- Subpixel adjustment prevents drift on slow movement
- Builders clean up automatically on completion
- Minimal overhead: simple list iteration for composition

## Future Considerations

- Multi-segment chaining (`.to(10).over(500).to(20).over(500)`)
- Force system integration (vector addition of tagged effects)
- Explicit layer system (beyond tag + bake)
