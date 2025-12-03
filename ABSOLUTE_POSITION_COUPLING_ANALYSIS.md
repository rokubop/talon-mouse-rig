# Absolute Position Coupling Analysis

## Executive Summary

This codebase is **heavily coupled to absolute positioning** via `ctrl.mouse_pos()`. The entire architecture assumes:
1. Mouse cursor has an absolute screen position
2. All position operations work in screen coordinates
3. The system can read and write absolute positions at any time

## Critical Dependencies on `ctrl.mouse_pos()`

### 1. **State Initialization** (High Impact)
**Location**: `src/state.py` lines 28, 47

```python
self._base_pos: Vec2 = Vec2(*ctrl.mouse_pos())
self._internal_pos: Vec2 = Vec2(*ctrl.mouse_pos())
```

**Impact**: System starts with absolute cursor position as its foundation.

**Relative Architecture Concern**: In a relative system, there would be no "current absolute position" to initialize from.

---

### 2. **Builder Base Value Calculation** (Critical)
**Location**: `src/builder.py` line 662

```python
# EXCEPT for position - use actual mouse position instead of base
self.base_value = Vec2(*ctrl.mouse_pos())
```

**Impact**: Every position operation reads the **current absolute mouse position** to determine its starting point. This is fundamental to how operators like `.to()`, `.by()`, `.add()` calculate their targets.

**Relative Architecture Concern**: In relative mode, there's no concept of "where am I now on screen?" - only "how much should I move?"

---

### 3. **Synchronous Position Execution** (Critical)
**Location**: `src/builder.py` lines 739-751

```python
def execute_synchronous(self):
    """Execute this builder synchronously (instant, no animation)"""
    if self.config.property == "pos":
        mode = self.config.mode
        current_value = self.target_value

        # Sync to actual current mouse position (in case user manually moved it)
        current_mouse_pos = ctrl.mouse_pos()
        self.rig_state._internal_pos = Vec2(current_mouse_pos[0], current_mouse_pos[1])
        self.rig_state._base_pos = Vec2(current_mouse_pos[0], current_mouse_pos[1])

        # Apply mode to current internal position
        new_pos = mode_operations.apply_position_mode(mode, current_value, self.rig_state._internal_pos)
        self.rig_state._internal_pos = new_pos
        self.rig_state._base_pos = Vec2(new_pos.x, new_pos.y)

        # Move mouse immediately
        from .core import mouse_move
        mouse_move(int(self.rig_state._internal_pos.x), int(self.rig_state._internal_pos.y))
```

**Impact**: Every instant position operation:
1. Reads absolute position via `ctrl.mouse_pos()`
2. Calculates absolute target
3. Writes absolute position via `mouse_move()`

**Relative Architecture Concern**: This entire flow assumes absolute coordinate system.

---

### 4. **Manual Movement Detection** (Medium-High Impact)
**Location**: `src/state.py` lines 487-505

```python
def _sync_to_manual_mouse_movement(self) -> bool:
    """Detect and sync to manual mouse movements by the user"""
    current_x, current_y = ctrl.mouse_pos()
    expected_x = int(round(self._internal_pos.x))
    expected_y = int(round(self._internal_pos.y))

    # If mouse position differs from our internal position, user moved it manually
    if current_x != expected_x or current_y != expected_y:
        manual_move = Vec2(current_x, current_y)

        # Update internal position to match manual movement
        self._internal_pos = manual_move
        # Update base position to match (this effectively "bakes" the manual movement)
        self._base_pos = manual_move
        # Reset position offset tracking
        self._last_position_offset = Vec2(0, 0)

        # Record time of manual movement
        self._last_manual_movement_time = time.perf_counter()

        return True
```

**Impact**: System detects when user moves mouse by comparing expected vs actual absolute position. Syncs internal state to new absolute position.

**Relative Architecture Concern**: In relative mode, there's no way to detect "user moved mouse" because we never know absolute position.

---

### 5. **Frame Loop Synchronization** (Medium Impact)
**Location**: `src/state.py` lines 634-640

```python
def _ensure_frame_loop_running(self):
    """Start frame loop if not already running"""
    if self._frame_loop_job is None:
        # ...
        # Sync to actual mouse position when starting (handles manual movements)
        current_mouse = Vec2(*ctrl.mouse_pos())
        self._internal_pos = current_mouse
        self._base_pos = current_mouse
        self._last_position_offset = Vec2(0, 0)
```

**Impact**: When frame loop starts, it syncs to absolute mouse position.

---

### 6. **Mouse Movement Verification** (Low-Medium Impact)
**Location**: `src/state.py` lines 613-618

```python
def _move_mouse_if_changed(self):
    """Move mouse if position has changed"""
    new_x = int(round(self._internal_pos.x))
    new_y = int(round(self._internal_pos.y))

    current_x, current_y = ctrl.mouse_pos()
    if new_x != current_x or new_y != current_y:
        mouse_move(new_x, new_y)
```

**Impact**: Optimization to avoid unnecessary mouse moves by checking current absolute position.

**Relative Architecture Concern**: In relative mode, you can't check "did the move happen?" without tracking.

---

### 7. **Position Mode Operations** (Architectural Core)
**Location**: `src/mode_operations.py` lines 249-323

All position operations in `calculate_position_target()` and `apply_position_mode()` work with absolute `Vec2` coordinates:

```python
def calculate_position_target(operator: str, value: Union[tuple, Vec2], current: Vec2, mode: str) -> Union[Vec2, float]:
    """Convert operator + value to canonical form for position mode."""
    if mode == "override":
        # Override mode: store absolute position
        if operator == "to":
            return Vec2.from_tuple(value)  # Absolute screen coordinates
        elif operator in ("by", "add"):
            return current + Vec2.from_tuple(value)  # Still absolute result
```

**Impact**: All position calculations assume absolute coordinate space.

---

### 8. **Position Baking** (State Management)
**Location**: `src/state.py` lines 289-311

```python
elif prop == "pos":
    if mode == "offset":
        # Offset mode: current_value is an offset vector, add to base position
        if builder.lifecycle.over_ms is not None and builder.lifecycle.over_ms > 0:
            # Was animated - position tracking already moved, just sync base
            self._base_pos = Vec2(self._internal_pos.x, self._internal_pos.y)
        else:
            # Instant operation - apply offset
            self._base_pos = Vec2(self._base_pos.x + current_value.x, self._base_pos.y + current_value.y)
            self._internal_pos = Vec2(self._base_pos.x, self._base_pos.y)
    elif mode == "override":
        # Override mode: current_value is absolute position, set base to it
        self._base_pos = Vec2(current_value.x, current_value.y)
        self._internal_pos = Vec2(current_value.x, current_value.y)
```

**Impact**: Baking always stores absolute positions in `_base_pos` and `_internal_pos`.

---

### 9. **Position Application** (Frame Loop Core)
**Location**: `src/state.py` lines 600-610

```python
def _apply_position_updates(self, pos: Vec2, pos_is_override: bool):
    """Apply position changes based on mode"""
    if pos_is_override:
        self._internal_pos = Vec2(pos.x, pos.y)  # Absolute position
        self._base_pos = Vec2(pos.x, pos.y)      # Absolute position
        self._last_position_offset = Vec2(0, 0)
    else:
        self._apply_position_offset(pos)
        self._base_pos = Vec2(self._internal_pos.x, self._internal_pos.y)
```

**Impact**: All position updates work in absolute coordinates.

---

## Architecture Summary

### Core Position State Variables
1. **`_base_pos: Vec2`** - Base absolute position (baked state)
2. **`_internal_pos: Vec2`** - Current absolute position (with subpixel precision)
3. **`_last_position_offset: Vec2`** - Delta tracking for position layers

All three track **absolute screen coordinates**.

### Position Flow
```
1. Read absolute position: ctrl.mouse_pos()
   ↓
2. Store in _base_pos, _internal_pos
   ↓
3. Calculate target (absolute coords)
   ↓
4. Apply mode operations (still absolute)
   ↓
5. Write absolute position: mouse_move(x, y)
```

### Mode Semantics (All Absolute)
- **offset**: Adds delta to absolute position → new absolute position
- **override**: Sets absolute position directly
- **scale**: Multiplies absolute coordinates (rarely useful for position)

---

## Coupling Assessment by Component

### Very Tight Coupling (Cannot work without absolute positioning)
1. ✅ Manual movement detection (`_sync_to_manual_mouse_movement`)
2. ✅ Builder base value initialization (`base_value = Vec2(*ctrl.mouse_pos())`)
3. ✅ Synchronous execution (`execute_synchronous`)
4. ✅ Frame loop sync (`_ensure_frame_loop_running`)
5. ✅ Position state initialization

### Tight Coupling (Major refactor needed)
1. ✅ All position mode operations
2. ✅ Position baking
3. ✅ Position application in frame loop
4. ✅ State computation (`_compute_current_state`)

### Medium Coupling (Could be abstracted)
1. ⚠️ Movement verification (`_move_mouse_if_changed`)
2. ⚠️ Subpixel adjuster (works in absolute space currently)

### Low Coupling (Easily adaptable)
1. ✅ Speed operations (already relative)
2. ✅ Direction operations (already relative)
3. ✅ Vector operations (already relative)

---

## Test Suite Dependencies

**Location**: `tests/position.py`, `tests/speed.py`, `tests/validation.py`

All position tests use `ctrl.mouse_pos()` to verify results:
```python
x, y = ctrl.mouse_pos()
assert x == target_x, f"X position wrong: expected {target_x}, got {x}"
```

**Impact**: 100% of position tests assume absolute positioning.

---

## Mouse API Layer

**Location**: `src/mouse_api.py`, `src/core.py`

All mouse movement APIs provide **absolute** positioning:
- `mouse_move(x, y)` - Move to absolute screen coordinates
- `mouse_move_relative(dx, dy)` - Exists but only used for gaming scenarios

**Note**: The codebase already has `mouse_move_relative()` but position operations don't use it.

---

## Implications for Relative Architecture

### What Would Need to Change

#### 1. **State Model**
- Remove `_base_pos` and `_internal_pos` (absolute coords)
- Replace with `_accumulated_delta: Vec2` (relative offset since start)
- No concept of "where am I on screen?"

#### 2. **Position Operations**
- `pos.to(x, y)` becomes meaningless (no absolute target)
- `pos.by(dx, dy)` becomes the only operation
- No "sync to current mouse position" - we never know it

#### 3. **Manual Movement Detection**
- **Cannot detect** user manually moving mouse
- No way to "sync" because we don't track absolute position
- Would need different approach (timeout? motion sensors? external signal?)

#### 4. **Baking**
- Cannot "bake absolute position"
- Would bake "accumulated delta" instead
- Different semantics entirely

#### 5. **Mode Operations**
- `override` mode becomes problematic (override to what absolute value?)
- `offset` mode remains viable (add delta to delta)
- `scale` mode remains viable (multiply delta)

#### 6. **Builder Initialization**
- Cannot read `ctrl.mouse_pos()` as base
- Would need to assume "current position is (0,0) in relative space"

### Gaming vs Desktop Use Cases

#### Gaming (Relative makes sense)
- First-person shooters with infinite rotation
- Mouse is captured, no absolute position concept
- Only deltas matter: "turn 10 degrees right"
- **Already partially supported** via `mouse_move_relative()`

#### Desktop (Absolute required)
- "Move cursor to coordinates (500, 300)"
- "Move to center of window"
- "Move to button location"
- **Current architecture** - 100% of codebase

---

## Recommendation

### For Introducing Relative Architecture:

#### Option 1: Dual-Mode System (Recommended)
Add a **mode flag** at the RigState level:
```python
self._position_mode: str = "absolute"  # or "relative"
```

Branch behavior based on mode:
- **Absolute mode**: Current behavior (read/write `ctrl.mouse_pos()`)
- **Relative mode**: Never read absolute position, only track deltas

Challenges:
- Cannot switch modes mid-operation
- Two completely different code paths for position
- Testing complexity doubles

#### Option 2: Abstraction Layer
Create `PositionTracker` interface:
```python
class PositionTracker(ABC):
    @abstractmethod
    def get_position(self) -> Vec2: ...

    @abstractmethod
    def set_position(self, pos: Vec2) -> None: ...

    @abstractmethod
    def move_by(self, delta: Vec2) -> None: ...

class AbsolutePositionTracker(PositionTracker):
    """Uses ctrl.mouse_pos()"""

class RelativePositionTracker(PositionTracker):
    """Tracks deltas only, never knows absolute"""
```

Challenges:
- Large refactor to thread this through
- Still need to handle semantic differences (manual movement detection, baking, etc.)

#### Option 3: Gaming-Specific Branch
Keep absolute positioning as primary, add special "gaming mode" for FPS use:
```python
rig.gaming_mode(True)  # Disables absolute positioning features
rig.pos.by(10, 0)      # Uses mouse_move_relative()
```

Gaming mode disables:
- Manual movement detection
- Position baking
- Position sync on frame loop start
- `pos.to()` operations

Challenges:
- Feature parity issues
- User confusion about what works in which mode

---

## Conclusion

**Coupling Level**: ⚠️ **EXTREMELY TIGHT**

The system is fundamentally architected around absolute positioning. Roughly **80% of position-related code** depends on `ctrl.mouse_pos()` either directly or architecturally.

### Key Architectural Assumptions:
1. ✅ Mouse cursor has absolute screen position
2. ✅ We can read this position at any time
3. ✅ We can write absolute positions
4. ✅ Position operations are meaningful in screen coordinates
5. ✅ Manual movement can be detected by position delta

**To support relative positioning would require**:
- Fundamental architecture redesign
- New state model (no `_base_pos`, `_internal_pos`)
- New semantics for position operations
- Loss of features (manual movement detection)
- Separate code paths for absolute vs relative
- Complete rewrite of position tests

**Estimated effort**: 3-5 days of focused refactoring + testing.
