# Relative Delta Architecture Proposal

## Your Vision: Pure Delta System

You want:
- **`pos.to(x, y)`** → Only operation that uses absolute positioning
- **Everything else** → Pure delta producers (no knowledge of absolute position)
  - `pos.by(dx, dy)` → Just produces dx, dy deltas
  - `speed` → Produces velocity deltas over time
  - `direction` → Produces rotational deltas
  - No comparing to base position
  - No syncing to `ctrl.mouse_pos()`

## The Good News: Speed/Direction Already Work This Way! ✅

### Speed is Already Pure Delta

```python
# Speed doesn't care about absolute position at all
rig.speed.to(100)      # "Move at 100 pixels/sec" (produces velocity delta)
rig.speed.by(50)       # "Add 50 to speed" (pure delta)

# In frame loop (state.py line 461):
velocity = direction * speed
dx_int, dy_int = self._subpixel_adjuster.adjust(velocity.x, velocity.y)
self._internal_pos = Vec2(self._internal_pos.x + dx_int, self._internal_pos.y + dy_int)
```

Speed just produces `dx, dy` per frame. It never reads `ctrl.mouse_pos()`. Perfect!

### Direction is Already Pure Delta

```python
# Direction just rotates a normalized vector
rig.direction.to(1, 0)    # Point right (unit vector)
rig.direction.by(45)      # Rotate 45 degrees (pure rotation)

# Never reads ctrl.mouse_pos()
# Just composes rotations and produces normalized vectors
```

Direction is pure mathematical rotation. No absolute positioning involved. Perfect!

### The Problem: Position is Absolute-First

```python
# Current behavior - EVERYTHING needs absolute position
rig.pos.by(100, 0)  # "Move 100 pixels right"

# What happens internally:
1. Reads ctrl.mouse_pos() → (500, 300)
2. Calculates target: (500 + 100, 300) = (600, 300)  ← ABSOLUTE!
3. Stores absolute target in builder
4. Animates from absolute to absolute
5. Compares against _base_pos (absolute)
```

## The Key Insight: Position Has Two Personalities

### Personality 1: Absolute Positioning (Desktop Use)
```python
rig.pos.to(500, 300)  # "Put cursor at screen coords (500, 300)"
```
- Needs `ctrl.mouse_pos()` to know where we are
- Needs absolute target
- Can detect manual movement
- Can sync on frame start

### Personality 2: Pure Delta (Gaming / Relative Movement)
```python
rig.pos.by(10, 0)     # "Move 10 pixels right (don't care where I am)"
rig.speed.to(100)     # "Move at 100 px/s (produces deltas over time)"
```
- Never reads `ctrl.mouse_pos()`
- Just produces `dx, dy` each frame
- No concept of "where am I?"
- Uses `mouse_move_relative(dx, dy)` only

---

## Architecture Analysis: Can We Unify or Must We Duplicate?

### Current Code Structure

```
Position Operations:
├── calculate_position_target()  ← Assumes absolute coordinates
├── apply_position_mode()        ← Assumes absolute coordinates  
├── _apply_position_offset()     ← Compares to _base_pos (absolute)
├── _apply_position_updates()    ← Sets _internal_pos (absolute)
└── execute_synchronous()        ← Reads ctrl.mouse_pos()
```

### The Core Question: Same Abstraction or Different?

#### Speed/Direction: One Abstraction Works for Everything
```python
# Speed is ALWAYS a delta producer
speed.to(100)   # Produces 100 px/s velocity
speed.by(50)    # Adds 50 to current velocity

# No absolute vs relative split needed
# Because speed has no concept of "absolute speed in world"
```

#### Position: Two Fundamentally Different Abstractions?

**Absolute Position**:
- State: "I am at (500, 300) on screen"
- Operation: "Move to (600, 400)"
- Needs: Read current position, write target position

**Relative Position**:  
- State: "I've moved (+100, +50) from where I started"
- Operation: "Move by (+10, 0)"
- Needs: Just produce delta, never know absolute position

These are **semantically different operations**.

---

## Proposed Architecture: Strategic Branching

### Option A: Unified with Mode Flag (Recommended)

Add a **position mode** to distinguish absolute vs relative:

```python
class RigState:
    def __init__(self):
        # ... existing ...
        self._position_mode: str = "absolute"  # or "relative"
```

Then branch at **key decision points** (not everywhere):

#### 1. Builder Initialization (Only Place That Reads `ctrl.mouse_pos`)

```python
# builder.py - ActiveBuilder.__init__
def __init__(self, config, rig_state, is_anonymous):
    # ... existing setup ...
    
    # ONLY branching point for reading absolute position
    if config.property == "pos":
        if rig_state._position_mode == "absolute":
            # Current behavior - sync to absolute position
            if config.operator == "to":
                self.base_value = Vec2(*ctrl.mouse_pos())
            else:
                self.base_value = rig_state.base.pos
        else:  # relative
            # Relative mode - never read absolute position
            # Base is always (0, 0) in relative space
            self.base_value = Vec2(0, 0)
```

#### 2. Position State Variables

```python
class RigState:
    def __init__(self):
        # Absolute mode state
        self._base_pos: Vec2 = Vec2(*ctrl.mouse_pos()) if mode == "absolute" else Vec2(0, 0)
        self._internal_pos: Vec2 = Vec2(*ctrl.mouse_pos()) if mode == "absolute" else Vec2(0, 0)
        
        # Relative mode state (NEW)
        self._accumulated_delta: Vec2 = Vec2(0, 0)  # Total delta since start
```

#### 3. Frame Loop Application

```python
# state.py - _move_mouse_if_changed()
def _move_mouse_if_changed(self):
    if self._position_mode == "absolute":
        # Current behavior - absolute positioning
        new_x = int(round(self._internal_pos.x))
        new_y = int(round(self._internal_pos.y))
        current_x, current_y = ctrl.mouse_pos()
        if new_x != current_x or new_y != current_y:
            mouse_move(new_x, new_y)
    else:  # relative
        # Relative mode - just emit the delta
        dx = int(round(self._accumulated_delta.x))
        dy = int(round(self._accumulated_delta.y))
        if dx != 0 or dy != 0:
            mouse_move_relative(dx, dy)
            self._accumulated_delta = Vec2(0, 0)  # Reset after emitting
```

#### 4. Manual Movement Detection

```python
# state.py - _sync_to_manual_mouse_movement()
def _sync_to_manual_mouse_movement(self) -> bool:
    # Only works in absolute mode
    if self._position_mode == "relative":
        return False  # Can't detect manual movement in relative mode
    
    # ... existing absolute mode logic ...
```

#### 5. Mode Operations (NO CHANGE NEEDED!)

The beautiful thing: **`mode_operations.py` doesn't need to change at all!**

```python
# These still work exactly the same
calculate_position_target()  # Returns Vec2 - could be absolute or relative delta
apply_position_mode()        # Applies Vec2 - doesn't care if absolute or relative
```

In relative mode, we just interpret the Vec2 differently:
- Absolute mode: Vec2(600, 400) = "screen coordinate (600, 400)"
- Relative mode: Vec2(100, 50) = "delta of (+100, +50) from origin"

---

## What Would NOT Need Duplication

### ✅ Can Stay Unified (90% of code)

1. **All of `mode_operations.py`** - Works on Vec2 regardless of interpretation
2. **All of `lifecycle.py`** - Animation/timing logic is identical
3. **All of `contracts.py`** - Config/validation unchanged
4. **All of `builder.py`** - Fluent API unchanged
5. **All of `rate_utils.py`** - Duration calculations work the same
6. **Speed/direction operations** - Already pure delta
7. **Layer system** - Ordering/aggregation unchanged
8. **Queue system** - Unchanged
9. **Easing functions** - Unchanged

### ⚠️ Would Need Strategic Branching (10% of code)

Only **5 key decision points** where behavior differs:

1. **Builder initialization** - Read `ctrl.mouse_pos()` or not
2. **State initialization** - Initialize absolute position or start at (0,0)
3. **Frame loop mouse move** - `mouse_move()` vs `mouse_move_relative()`
4. **Manual movement detection** - Enable or disable
5. **Frame loop sync** - Sync to absolute position or not

### ❌ Features Lost in Relative Mode

1. **Manual movement detection** - Impossible without absolute position
2. **Position baking** - Would bake "accumulated delta" instead
3. **`pos.to(x, y)`** - Meaningless without absolute coordinates

---

## Implementation Strategy

### Phase 1: Add Position Mode Flag
```python
# settings.talon
user.mouse_rig_position_mode: str = "absolute"  # or "relative"
```

### Phase 2: Branch at 5 Key Points
1. `builder.py` - `ActiveBuilder.__init__()` - base value selection
2. `state.py` - `RigState.__init__()` - state variable initialization  
3. `state.py` - `_move_mouse_if_changed()` - mouse movement API
4. `state.py` - `_sync_to_manual_mouse_movement()` - disable in relative
5. `state.py` - `_ensure_frame_loop_running()` - disable sync in relative

### Phase 3: Add Relative State Tracking
```python
self._accumulated_delta: Vec2 = Vec2(0, 0)
```

### Phase 4: Update Position Application
```python
def _apply_position_updates(self, pos: Vec2, pos_is_override: bool):
    if self._position_mode == "absolute":
        # Existing absolute logic
    else:
        # Accumulate delta for next relative move
        self._accumulated_delta += pos
```

---

## How `pos.by` Would Work in Each Mode

### Absolute Mode (Current)
```python
rig.pos.by(100, 0)

# Flow:
1. Read current pos: ctrl.mouse_pos() → (500, 300)
2. Calculate target: (500 + 100, 300) = (600, 300)
3. Store target: Vec2(600, 300) [absolute]
4. Animate _internal_pos from (500, 300) → (600, 300)
5. Each frame: mouse_move(x, y) [absolute]
```

### Relative Mode (Proposed)
```python
rig.pos.by(100, 0)

# Flow:
1. Never read ctrl.mouse_pos()
2. Store delta: Vec2(100, 0) [relative]
3. Animate delta from (0, 0) → (100, 0)
4. Each frame: 
   - Add animated delta to _accumulated_delta
   - When ready: mouse_move_relative(dx, dy)
   - Reset _accumulated_delta
```

### The Key Difference

**Absolute**: "I need to end up at pixel (600, 300)"
**Relative**: "I need to emit +100 pixels of delta total"

Both use the **same animation system**, just different interpretation of the Vec2!

---

## Tracking Progress in Relative Mode

### Challenge: How to know when done?

```python
rig.pos.by(100, 0)  # Need to move 100 pixels right
```

In absolute mode: `_internal_pos` reaches `(600, 300)` → done

In relative mode: Track "remaining delta"

```python
class ActiveBuilder:
    def __init__(self, ...):
        if rig_state._position_mode == "relative" and config.property == "pos":
            self.target_delta = Vec2(100, 0)      # Target delta to emit
            self.emitted_delta = Vec2(0, 0)       # Delta emitted so far
```

Then in frame loop:
```python
# Animate from (0, 0) → target_delta
current_delta = animate_position(..., phase, progress)

# How much delta to emit this frame
frame_delta = current_delta - self.emitted_delta
self.emitted_delta = current_delta

# Accumulate for batched emission
rig_state._accumulated_delta += frame_delta
```

**Still uses same animation system!** Just tracking "delta emitted" instead of "position reached".

---

## Answer to Your Questions

### Q: Would it require rewriting a relative version of almost every class?

**A: No! Only 5 strategic branch points, ~10% of position code.**

### Q: How would you track reaching a goal like `pos.by(100)`?

**A: Same animation system, just track "delta emitted" vs "delta target":**

```python
# Absolute mode
progress = (current_pos - start_pos) / (target_pos - start_pos)

# Relative mode  
progress = emitted_delta / target_delta
```

Both use the **same lifecycle/animation infrastructure**.

### Q: Can we avoid duplication?

**A: Yes! Key insight:**

**Speed/Direction are ALREADY pure delta** → no changes needed
**Position mode_operations are math** → same for absolute/relative
**Only 5 places need branching** → builder init, state init, mouse move, manual detection, frame sync

---

## Recommendation: Unified Architecture with Strategic Branching

### Why This Works

1. **90% of code is identical** - animation, layers, lifecycle, modes
2. **Branch only where semantics differ** - reading/writing mouse position
3. **Same API surface** - users call same methods
4. **Feature flags control behavior** - `position_mode: "absolute"` vs `"relative"`

### Estimated Effort

- **Absolute mode changes**: 5 strategic `if` statements
- **Relative mode additions**: 
  - Add `_accumulated_delta` state variable
  - Add delta tracking to ActiveBuilder
  - Update frame loop position application
- **Testing**: Add relative mode test variants

**Total: 1-2 days** instead of 3-5 days of full rewrite.

### Migration Path

1. Add position mode flag (default: "absolute")
2. Add 5 strategic branch points
3. Absolute mode continues working exactly as before
4. Add relative mode branches (new behavior)
5. Test both modes independently
6. Ship with absolute as default, relative as opt-in

---

## Your Ideal Architecture is Achievable! ✅

> "ONLY produces dx, dy, and thats it. no comparing vs a base position."

This is **exactly** what speed/direction already do.

And with strategic branching, `pos.by()` can do this too in relative mode!

The trick: **Don't duplicate the classes**. Just branch where the semantics differ (reading/writing absolute vs relative coordinates).

**Key Insight**: Position operations are just animated Vec2 transformations. Whether that Vec2 represents absolute screen coords or relative deltas is an **interpretation concern**, not a fundamental difference in the math/animation/lifecycle code.
