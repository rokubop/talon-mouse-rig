# PRD 8: Effect Rename + Strict Syntax Mode + On Repeat Strategies

## Overview
Rename `transform()` to `effect()` for better semantics, introduce strict vs loose syntax modes, and replace `.stack()` with comprehensive `.on_repeat()` strategies.

## Key Changes

### 1. Transform → Effect Rename
**Before:**
```python
rig.transform("boost").speed(10)
```

**After:**
```python
rig.effect("boost").speed.to(10)
```

**Rationale:** "Transform" sounds like a verb, which creates confusion. "Effect" is clearly a noun and better represents a named, revertible modification.

### 2. Strict vs Loose Syntax Modes

#### Loose Syntax (Base Rig & Forces)
- **Base rig:** `rig.speed(5)` → equivalent to `rig.speed.to(5)`
- **Forces:** `rig.force("wind").speed(10)` → equivalent to `speed.to(10)`
- **Loose = shorthand allowed:** `something(value)` is always `something.to(value)`

#### Strict Syntax (Effects - REQUIRED)
- **Effects MUST use explicit operations:**
  - `rig.effect("boost").speed.to(10)` ✅
  - `rig.effect("boost").speed(10)` ❌ (error - strict mode enforced)

**Implementation Note:** Strict mode is an actual implementation concept, not just documentation. Named effects should raise errors if shorthand syntax is used.

### 3. Property Operations (All Contexts)

#### Available Operations
All properties support these operations:
- **`.to(value)`** - Set absolute value
  - Base rig: sets base value
  - Effect: sets effect value (can be reverted)
  - Force: sets force value

- **`.by(delta)` / `.add(delta)`** - Add delta (aliases)
  - `.by()` is always an alias for `.add()`
  - Effect: delta from base (additive)

- **`.sub(delta)`** - Subtract delta

- **`.mul(factor)`** - Multiply by factor

- **`.div(divisor)`** - Divide by divisor

#### Property Coverage
- **speed:** `.to`, `.add`, `.by`, `.sub`, `.mul`, `.div`
- **accel:** `.to`, `.add`, `.by`, `.sub`, `.mul`, `.div`
- **direction:** `.to`, `.add`, `.by`, `.sub` (angles in degrees)
- **pos:** `.to(x, y)`, `.by(x, y)`, `.add(x, y)`, `.sub(x, y)`

### 4. Effect Semantics

#### `.to(value)` - Absolute Value
```python
# Effect sets its own value, overriding base
rig.effect("boost").speed.to(10)
# When reverted, returns to base speed
```

#### `.add(delta)` - Delta from Base
```python
# Effect adds to base
# Base speed: 5, effect adds 3 = total 8
rig.effect("boost").speed.add(3)
# When reverted, removes the +3
```

#### `.mul(factor)` - Multiplicative
```python
# Effect multiplies base
# Base speed: 5, effect ×2 = total 10
rig.effect("sprint").speed.mul(2)
```

### 5. On Repeat Strategies (Replaces `.stack()`)

**Before:**
```python
rig.transform("boost").speed(10).stack()      # Unlimited
rig.transform("boost").speed(10).stack(3)     # Max 3 stacks
```

**After:**
```python
rig.effect("boost").speed.add(10).on_repeat("stack")          # Unlimited
rig.effect("boost").speed.add(10).on_repeat("stack", 3)       # Max 3 stacks
rig.effect("boost").speed.add(10).on_repeat("replace")        # Default
rig.effect("boost").speed.add(10).on_repeat("extend")         # Extend duration
rig.effect("boost").speed.add(10).on_repeat("queue")          # Queue up
rig.effect("boost").speed.add(10).on_repeat("ignore")         # Ignore new calls
rig.effect("boost").speed.add(10).on_repeat("throttle", 500)  # Rate limit (ms)
```

#### Strategy Details

**`"replace"` (default)**
- New call replaces existing effect
- Resets duration and easing
```python
rig.effect("boost").speed.add(10).over(1000)
# Called again → restarts the 1000ms transition

# With full lifecycle
rig.effect("boost").speed.add(10).over(500).hold(2000).revert(500).on_repeat("replace")
```

**`"stack"` (unlimited or max)**
```python
# Each call adds another stack
rig.effect("boost").speed.add(5).on_repeat("stack")
# Call 1: +5, Call 2: +10, Call 3: +15...

# With max stacks
rig.effect("boost").speed.add(5).on_repeat("stack", 3)
# Caps at +15 (3 stacks)

# With full lifecycle - each stack fades in/out independently
rig.effect("boost").speed.add(5).over(300).hold(2000).revert(500).on_repeat("stack", 3)
```

**`"extend"`**
- Resets the lifecycle timer from current phase, cancels pending revert
- Effect value stays constant (doesn't stack), only duration extends
```python
rig.effect("boost").speed.add(10).over(1000).hold(2000).on_repeat("extend")
# Each call adds another 2000ms hold time

# With full lifecycle - behavior depends on when triggered:
rig.effect("boost").speed.add(10).over(500).hold(2000).revert(500).on_repeat("extend")
# During over (fading in at +5): Continues fade from +5 to +10, then holds 2000ms, reverts 500ms
# During hold (at +10): Extends hold by 2000ms, then reverts 500ms
# During revert (fading out at +5): Fades back up from +5 to +10 over 500ms, holds 2000ms, reverts 500ms
```

**`"queue"`**
- Queues up effects to run sequentially
```python
rig.effect("boost").speed.add(10).over(1000).on_repeat("queue")
# Call 1 runs, Call 2 waits, Call 3 waits...

# With full lifecycle - each queued effect runs its full lifecycle
rig.effect("boost").speed.add(10).over(500).hold(1000).revert(500).on_repeat("queue")
```

**`"ignore"`**
- Ignores new calls while effect is active
```python
rig.effect("boost").speed.add(10).hold(3000).on_repeat("ignore")
# Calls during 3s are ignored

# With full lifecycle - ignores calls during entire lifecycle
rig.effect("boost").speed.add(10).over(500).hold(2000).revert(500).on_repeat("ignore")
```

**`"throttle", ms`**
- Rate limits calls (minimum time between calls)
```python
rig.effect("boost").speed.add(10).on_repeat("throttle", 500)
# Maximum 1 call per 500ms

# With full lifecycle - throttles the activation, not the lifecycle
rig.effect("boost").speed.add(10).over(500).hold(1000).revert(500).on_repeat("throttle", 500)
```

## Examples

### Basic Effect Usage
```python
# Sprint mode (multiplicative)
rig.effect("sprint").speed.mul(2).over(500).revert(500)

# Slow mode (divisor)
rig.effect("slow").speed.div(2)

# Speed boost (additive)
rig.effect("boost").speed.add(10).hold(2000).revert(500)

# Position offset (absolute)
rig.effect("wobble").pos.to(100, 100).over(1000)
```

### Stacking Boosts
```python
# Boost pad - stacks up to 3 times
rig.effect("boost_pad").speed.add(10).on_repeat("stack", 3)

# Rage stacks - multiplicative stacking
rig.effect("rage").speed.mul(1.2).on_repeat("stack", 5)
```

### Drift with Extend
```python
# Drift that extends on repeated calls
rig.effect("drift").direction.add(15).hold(2000).on_repeat("extend")
```

### Invulnerability with Ignore
```python
# Can't be called again during active period
rig.effect("invuln").speed.mul(0).hold(2000).on_repeat("ignore")
```

### Forces (Loose Syntax Still Works)
```python
# Loose syntax OK for forces
rig.force("gravity").direction(0, 1).accel(9.8)
rig.force("wind").speed(10)

# Strict also works
rig.force("wind").speed.to(10).direction.to(1, 0)
```

### Base Rig (Loose Syntax)
```python
# Loose syntax
rig.speed(5)           # Same as speed.to(5)
rig.direction(1, 0)    # Same as direction.to(1, 0)
rig.accel(2)           # Same as accel.to(2)

# Strict syntax also works
rig.speed.to(5)
rig.speed.add(3)
rig.direction.by(45)   # Same as direction.add(45)
```

## Implementation Requirements

### Strict Mode Enforcement
- Create a `strict_mode` flag/context for effects
- When in strict mode (inside `.effect()`):
  - Shorthand syntax like `speed(5)` should raise an error
  - Must use `speed.to(5)`, `speed.add(5)`, etc.
- Base rig and forces operate in loose mode

### Backwards Compatibility
- All `transform()` references should be migrated to `effect()`
- All `.stack()` should be migrated to `.on_repeat("stack")`
- Default behavior (no `.on_repeat()` call) = `"replace"`

## Migration Guide

### PRD 7 → PRD 8

| PRD 7 | PRD 8 |
|-------|-------|
| `transform("name")` | `effect("name")` |
| `.speed(10)` (transform) | `.speed.add(10)` or `.speed.to(10)` |
| `.stack()` | `.on_repeat("stack")` |
| `.stack(3)` | `.on_repeat("stack", 3)` |

### Example Migration
```python
# PRD 7
rig.transform("boost").speed(10).stack(3)

# PRD 8
rig.effect("boost").speed.add(10).on_repeat("stack", 3)
```

```python
# PRD 7
rig.transform("sprint").speed.mul(2)

# PRD 8 (same, just renamed)
rig.effect("sprint").speed.mul(2)
```

## Summary

- ✅ `transform()` → `effect()` (better noun)
- ✅ Strict syntax enforced for effects (implementation requirement)
- ✅ Loose syntax allowed for base rig and forces
- ✅ `.by()` always aliases `.add()`
- ✅ `something(value)` always means `something.to(value)` in loose contexts
- ✅ `.stack()` → `.on_repeat()` with 7 strategies
- ✅ Clear semantics: `.to()` = absolute, `.add()` = delta, `.mul()` = factor
