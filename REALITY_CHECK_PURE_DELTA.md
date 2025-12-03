# Reality Check: Current Architecture vs Pure Delta Goal

## What Currently Happens (The Truth)

### Current Flow for `rig.pos.by(100, 0)`

```python
# Step 1: Builder Creation (builder.py line 662)
rig.pos.by(100, 0)
→ config.operator = "by"
→ config.value = (100, 0)
→ config.property = "pos"

# Step 2: ActiveBuilder Init - READS ABSOLUTE POSITION
base_value = Vec2(*ctrl.mouse_pos())  # Say this returns (500, 300)
target_value = calculate_position_target("by", (100, 0), Vec2(500, 300), "offset")
→ target_value = Vec2(100, 0)  # Just the delta in offset mode

# Step 3: Frame Loop - Every Frame
pos, speed, direction = _compute_current_state()
→ pos = _base_pos + animated_delta  # e.g., (500, 300) + (50, 0) at 50% progress
→ pos = Vec2(550, 300)  # ABSOLUTE COORDINATE

# Step 4: Apply Position - WRITES ABSOLUTE POSITION
_internal_pos = pos  # Vec2(550, 300)
mouse_move(550, 300)  # Absolute screen coordinate
```

**Reality**: Even though offset mode stores a "delta" (100, 0), it's immediately **applied to an absolute base position** and the entire system works in absolute coordinates throughout.

### Current Flow for `rig.speed.to(100)`

```python
# Step 1: Builder Creation
rig.speed.to(100)
→ target_value = 100  # Just a scalar

# Step 2: Frame Loop - Every Frame
speed = _base_speed + animated_delta  # e.g., 0 + 100 = 100
direction = Vec2(1, 0)  # Current direction

# Step 3: Apply Velocity - PRODUCES DELTA
velocity = direction * speed  # Vec2(100, 0)
dx, dy = subpixel_adjuster.adjust(100, 0)  # Say dx=5, dy=0 for this frame
_internal_pos += Vec2(dx, dy)  # ADD DELTA TO POSITION

# Step 4: Move Mouse - WRITES ABSOLUTE POSITION
mouse_move(_internal_pos.x, _internal_pos.y)  # Still absolute!
```

**Reality**: Speed produces `dx, dy` per frame, but those deltas are **immediately added to `_internal_pos` (absolute)**, and mouse_move still gets absolute coordinates.

---

## The Core Issue: Two Different Concepts of "Position"

### Concept 1: Speed/Direction (Already Pure Delta) ✅
```python
speed = 100        # "Move at 100 px/frame"
direction = (1, 0) # "Move rightward"
→ Produces: dx=100, dy=0 per frame

# No absolute position needed!
# Just accumulate deltas: _internal_pos += Vec2(dx, dy)
```

### Concept 2: Position Operations (Currently Absolute) ❌
```python
pos.by(100, 0)  # "Move 100 pixels right FROM CURRENT POSITION"

# Current implementation:
1. Read current position: ctrl.mouse_pos() → (500, 300)
2. Calculate absolute target: (500, 300) + (100, 0) = (600, 300)
3. Track absolute position: _internal_pos = (600, 300)
4. Write absolute position: mouse_move(600, 300)
```

---

## What You Want: Pure Delta for Position Too

### Your Goal
```python
pos.by(100, 0)  # "Emit 100 pixels of rightward delta"

# Desired implementation:
1. NEVER read ctrl.mouse_pos()
2. Store target delta: Vec2(100, 0)
3. Track emitted delta: (0, 0) → (100, 0) as it animates
4. Each frame: emit delta via mouse_move_relative(dx, dy)
5. Done when emitted_delta == target_delta
```

This is **fundamentally different** from current architecture.

---

## The Hard Truth: It's a Significant Rewrite

### Why? Because Position is the Anchor Point

Currently, **everything flows through absolute position**:

```
Speed/Direction (pure delta)
    ↓
    Produces velocity (dx, dy)
    ↓
    Added to _internal_pos (ABSOLUTE)  ← Anchor point
    ↓
    mouse_move(absolute_x, absolute_y)
```

Even though speed/direction are pure delta, they're **anchored to absolute position** as the accumulation point.

### Your Goal: Remove the Anchor

```
Speed/Direction (pure delta)
    ↓
    Produces velocity (dx, dy)
    ↓
    Added to _accumulated_delta (RELATIVE)  ← No absolute anchor
    ↓
    mouse_move_relative(dx, dy)
```

This requires changing the **fundamental accumulation model**.

---

## What Would Actually Need to Change (Revised Assessment)

### ❌ Small Changes Won't Work

My earlier "5 strategic branch points" was too optimistic. Here's why:

#### Problem 1: State Model is Absolute-Centric
```python
# Current
self._internal_pos: Vec2  # Absolute screen coordinate
self._base_pos: Vec2      # Absolute screen coordinate

# These appear EVERYWHERE in the codebase:
- _compute_current_state() returns absolute pos
- _apply_position_offset() compares to _base_pos (absolute)
- _apply_velocity_movement() adds to _internal_pos (absolute)
- _move_mouse_if_changed() uses _internal_pos (absolute)
- Every position builder stores absolute base_value
```

You can't just add a mode flag - **the entire state model is absolute**.

#### Problem 2: Position Computation is Absolute
```python
def _compute_current_state(self) -> tuple[Vec2, float, Vec2, bool]:
    # Start with base
    pos = Vec2(self._base_pos.x, self._base_pos.y)  # ABSOLUTE
    
    # Apply layers
    for builder in builders:
        pos = apply_position_mode(mode, value, pos)  # pos is ABSOLUTE throughout
    
    return pos  # Returns ABSOLUTE position
```

Every layer computation assumes `pos` is an absolute coordinate. You can't make this relative without changing every caller.

#### Problem 3: Velocity is Anchored to Absolute Position
```python
def _apply_velocity_movement(self, speed: float, direction: Vec2):
    velocity = direction * speed
    dx_int, dy_int = self._subpixel_adjuster.adjust(velocity.x, velocity.y)
    self._internal_pos = Vec2(self._internal_pos.x + dx_int, self._internal_pos.y + dy_int)
    #                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                         Adding to ABSOLUTE position
```

Even pure velocity movement is anchored to absolute position.

---

## What Actually Needs Rewriting

### 1. State Model (Major Rewrite)
```python
# Current: Absolute-centric
class RigState:
    self._base_pos: Vec2       # Absolute
    self._internal_pos: Vec2   # Absolute
    
# Pure Delta Version: Relative-centric
class RigState:
    self._accumulated_delta: Vec2      # Total delta emitted so far
    self._pending_delta: Vec2          # Delta to emit next frame
    # No concept of "where we are" - just "how much we've moved"
```

**Impact**: Every method that uses `_internal_pos` or `_base_pos` needs rewriting.

**Files affected**:
- `state.py` - ~30 references to `_internal_pos` and `_base_pos`
- `builder.py` - Builder initialization, synchronous execution

### 2. Position Computation (Major Rewrite)
```python
# Current: Accumulates absolute positions
def _compute_current_state(self) -> Vec2:
    pos = self._base_pos  # Start with absolute
    for layer in layers:
        pos = apply_mode(layer, pos)  # pos is absolute
    return pos  # Return absolute

# Pure Delta Version: Accumulates deltas
def _compute_current_delta(self) -> Vec2:
    delta = Vec2(0, 0)  # Start with zero delta
    for layer in layers:
        delta = apply_mode(layer, delta)  # delta is relative
    return delta  # Return delta to emit
```

**Impact**: Signature changes propagate everywhere.

**Files affected**:
- `state.py` - All position computation logic
- Every caller of `_compute_current_state()`

### 3. Position Application (Complete Rewrite)
```python
# Current: Writes absolute position
def _apply_position_updates(self, pos: Vec2, pos_is_override: bool):
    self._internal_pos = pos  # Absolute
    mouse_move(pos.x, pos.y)  # Absolute

# Pure Delta Version: Emits relative delta
def _emit_position_delta(self, delta: Vec2):
    self._accumulated_delta += delta
    mouse_move_relative(delta.x, delta.y)
```

**Files affected**:
- `state.py` - Position application
- `core.py` - Would need to use `mouse_move_relative` exclusively

### 4. Position Builders (Significant Changes)
```python
# Current: Store absolute base and target
class ActiveBuilder:
    self.base_value = Vec2(*ctrl.mouse_pos())  # Absolute
    self.target_value = calculate_target(base)  # Absolute
    
# Pure Delta Version: Store delta target only
class ActiveBuilder:
    # No base_value needed!
    self.target_delta = Vec2(100, 0)  # Just the delta goal
    self.emitted_delta = Vec2(0, 0)   # Track progress
```

**Files affected**:
- `builder.py` - ActiveBuilder initialization and animation
- All position animation logic

### 5. Manual Movement Detection (Remove Feature)
```python
# Current: Detects when user moves mouse
def _sync_to_manual_mouse_movement(self) -> bool:
    current = ctrl.mouse_pos()  # Absolute
    expected = self._internal_pos  # Absolute
    if current != expected:
        # User moved mouse!
        
# Pure Delta Version: IMPOSSIBLE
# Cannot detect manual movement without knowing absolute position
```

**Impact**: Lose this feature entirely in pure delta mode.

### 6. Position Baking (Different Semantics)
```python
# Current: Bake absolute position to base
self._base_pos = final_absolute_position

# Pure Delta Version: Bake accumulated delta
self._accumulated_delta = total_delta_emitted
```

**Impact**: Completely different meaning of "baking".

### 7. Frame Loop (Restructure)
```python
# Current: Compute absolute, move to absolute
pos = _compute_current_state()  # Absolute
mouse_move(pos.x, pos.y)

# Pure Delta Version: Compute delta, emit delta
delta = _compute_current_delta()  # Relative
mouse_move_relative(delta.x, delta.y)
```

**Files affected**:
- `state.py` - Frame tick logic

---

## Can We Use the Same Classes? (Reality Check)

### Speed/Direction: Yes ✅
These are already pure delta. No changes needed.

### Position: No ❌

The entire position infrastructure assumes absolute coordinates:

- **State variables** - Store absolute positions
- **Computation** - Accumulates absolute positions
- **Application** - Writes absolute positions
- **Builders** - Store absolute base and target
- **Baking** - Stores absolute base
- **Manual detection** - Compares absolute positions

**You can't just add a flag** - the data model is fundamentally different.

---

## Two Possible Paths Forward

### Path 1: Full Rewrite (Clean but Expensive)

Create separate position systems:

```python
# Absolute position (current system)
class AbsolutePositionSystem:
    _internal_pos: Vec2  # Absolute
    _base_pos: Vec2      # Absolute
    
    def compute_position(self) -> Vec2:
        # Returns absolute position
        
    def move_mouse(self, pos: Vec2):
        mouse_move(pos.x, pos.y)  # Absolute

# Relative position (new system)  
class RelativePositionSystem:
    _accumulated_delta: Vec2  # Relative
    _pending_delta: Vec2      # Relative
    
    def compute_delta(self) -> Vec2:
        # Returns delta to emit
        
    def emit_delta(self, delta: Vec2):
        mouse_move_relative(delta.x, delta.y)  # Relative
```

**Pros**: Clean separation, each system is simple
**Cons**: Code duplication, testing overhead
**Effort**: 4-5 days

### Path 2: Hybrid System (Pragmatic)

Keep position as absolute, but add a "pure delta mode" for gaming:

```python
# Position stays absolute (current system)
rig.pos.by(100, 0)  # Still uses absolute positioning

# Add new API for pure delta
rig.delta.by(100, 0)  # NEW: Pure delta emission
# OR
rig.pos.relative.by(100, 0)  # Pure delta variant
```

Pure delta would:
- Skip position tracking entirely
- Just emit deltas via `mouse_move_relative()`
- No animation, no baking, no manual detection
- Simple, limited feature set

**Pros**: Minimal changes, no duplication
**Cons**: Two APIs, potential user confusion
**Effort**: 1-2 days

---

## My Revised Assessment

### Original Claim: "Only 5 branch points, 10% of code"
**This was wrong.** I was thinking about adding a mode flag, not changing the fundamental data model.

### Reality: "Full position subsystem rewrite, 40-50% of position code"

**Files needing significant changes**:
- `state.py` - State model, computation, application (~400 lines)
- `builder.py` - Position builder init, animation (~200 lines)
- `mode_operations.py` - Minor (interpretation changes)
- Tests - All position tests (~300 lines)

**Total rewrite estimate**: 900+ lines of position-related code

---

## Recommendation

### If You Want Pure Delta Position:

**Don't try to retrofit the current system.** The absolute position model is too deeply embedded.

**Instead**:

1. **Keep absolute positioning for desktop use** - It's valuable and works well
2. **Add a separate "relative delta" API for gaming**:
   ```python
   # Gaming mode - pure delta emission
   rig.delta.by(10, 0)  # Emit 10 pixels right
   rig.delta.continuous(100, 0)  # Continuous delta at 100 px/s
   ```

3. **Share what you can**:
   - Speed/direction (already pure delta)
   - Lifecycle/animation timing
   - Easing functions
   - Layer system (if useful for gaming)

4. **Keep it simple** for delta mode:
   - No baking
   - No manual movement detection  
   - No absolute positioning features
   - Just: store delta goal, emit deltas, done when goal reached

This way you get pure delta for gaming **without** breaking the absolute positioning that works for desktop use.

**Effort**: 2-3 days to add delta API alongside existing system.

---

## The Bottom Line

**Yes, it's a significant rewrite to make ALL position operations work as pure delta.**

The system is more tightly coupled to absolute positioning than I initially assessed. It's not just "5 branch points" - it's the entire data model.

But you don't have to rewrite everything if you:
1. Keep absolute positioning for `pos.to()`
2. Add a separate pure delta API for gaming scenarios
3. Share the infrastructure that doesn't care (speed, direction, timing)

That's the pragmatic path that gives you pure delta without throwing away a working system.
