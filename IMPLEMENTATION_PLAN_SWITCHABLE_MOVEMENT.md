# Implementation Plan: Switchable Movement Models

## Core Insight: Builders Already Know Their Own Progress ✅

Each `ActiveBuilder` already tracks:
- `base_value` - Starting value
- `target_value` - Ending value  
- `lifecycle` - Current animation phase and progress
- `_get_own_value()` - Returns current animated value

**The builder doesn't care if these are absolute or relative** - it just animates between two values!

---

## The Strategy: Defer Interpretation Until `_tick_frame()`

### Current Architecture (Absolute-First)
```python
# Builder stores ABSOLUTE positions
builder.base_value = Vec2(*ctrl.mouse_pos())  # (500, 300)
builder.target_value = Vec2(600, 300)         # Absolute target

# Frame loop computes ABSOLUTE position
pos = _compute_current_state()  # Returns Vec2(550, 300) - absolute
_internal_pos = pos             # Store absolute
mouse_move(pos.x, pos.y)        # Write absolute
```

### New Architecture (Interpretation at End)
```python
# Builder stores VALUES (meaning depends on movement type)
builder.base_value = ???  # Depends on movement type
builder.target_value = ???  # Depends on movement type

# Frame loop collects CONTRIBUTIONS from all builders
contributions = _compute_frame_contributions()  # List of (property, value, movement_type)

# ONLY IN _tick_frame(), decide how to move mouse:
if any_absolute_position:
    # Mix relative + absolute
    final_pos = _resolve_absolute_position(contributions)
    mouse_move(final_pos.x, final_pos.y)
else:
    # Pure relative
    total_dx, total_dy = _sum_relative_deltas(contributions)
    mouse_move_relative(total_dx, total_dy)
```

---

## Movement Types Per Builder

### Add movement type to config
```python
class BuilderConfig:
    # ... existing fields ...
    movement_type: str = "relative"  # "relative" or "absolute"
```

### Determine movement type based on operation
```python
# In PropertyBuilder.to()
def to(self, *args) -> RigBuilder:
    self.rig_builder.config.operator = "to"
    self.rig_builder.config.value = args[0] if len(args) == 1 else args
    
    # Set movement type based on property and operator
    if self.rig_builder.config.property == "pos":
        # pos.to() is ALWAYS absolute
        self.rig_builder.config.movement_type = "absolute"
    # else: keep default "relative"
    
    return self.rig_builder

# In PropertyBuilder.by()
def by(self, *args) -> RigBuilder:
    self.rig_builder.config.operator = "add"
    self.rig_builder.config.value = args[0] if len(args) == 1 else args
    
    # pos.by() is ALWAYS relative (never needs absolute position)
    self.rig_builder.config.movement_type = "relative"
    
    return self.rig_builder
```

**Key Rules**:
- `pos.to(x, y)` → `movement_type = "absolute"` (only operation that needs screen coordinates)
- `pos.by(dx, dy)` → `movement_type = "relative"` (pure delta)
- `speed.*` → `movement_type = "relative"` (always pure delta)
- `direction.*` → `movement_type = "relative"` (always pure delta)

---

## Builder Initialization Changes

### Current (Always reads absolute position)
```python
# builder.py - ActiveBuilder.__init__
if config.operator == "to":
    if config.property == "pos":
        self.base_value = Vec2(*ctrl.mouse_pos())  # ALWAYS reads absolute
```

### New (Only read absolute if movement_type is absolute)
```python
# builder.py - ActiveBuilder.__init__
if config.operator == "to":
    if config.property == "pos":
        if config.movement_type == "absolute":
            # Only pos.to() needs absolute position
            self.base_value = Vec2(*ctrl.mouse_pos())
            self.target_value = Vec2.from_tuple(config.value)
        else:
            # Shouldn't happen (pos.to is always absolute)
            pass
    else:
        # speed.to(), direction.to() - use computed state (relative)
        self.base_value = getattr(rig_state, config.property)
        
elif config.operator in ("by", "add"):
    # pos.by(), speed.by(), direction.by() - NEVER read ctrl.mouse_pos()
    if config.property == "pos":
        # Store just the delta
        self.base_value = Vec2(0, 0)  # Start at zero delta
        self.target_value = Vec2.from_tuple(config.value)  # Target delta
    else:
        # speed/direction use base state (relative)
        self.base_value = self._get_base_value()
```

**Key Change**: `pos.by()` stores delta (0, 0) → (100, 0), not absolute positions!

---

## State Model Changes

### Add movement tracking to state
```python
class RigState:
    def __init__(self):
        # Absolute position tracking (ONLY for pos.to operations)
        self._base_pos: Vec2 = Vec2(0, 0)  # Only updated by pos.to
        self._internal_pos: Vec2 = Vec2(0, 0)  # Only used with absolute operations
        
        # Relative delta tracking (for everything else)
        self._frame_delta: Vec2 = Vec2(0, 0)  # Accumulated dx, dy this frame
```

**Key Insight**: We keep both! But only use `_internal_pos` when there's an absolute operation.

---

## Frame Loop Changes: The Core Logic

### Current `_tick_frame()`
```python
def _tick_frame(self):
    # ...
    pos, speed, direction, pos_is_override = self._compute_current_state()
    self._apply_velocity_movement(speed, direction)
    self._apply_position_updates(pos, pos_is_override)
    self._move_mouse_if_changed()
```

### New `_tick_frame()`
```python
def _tick_frame(self):
    current_time, dt = self._calculate_delta_time()
    if dt is None:
        return

    manual_movement_detected = self._sync_to_manual_mouse_movement()
    phase_transitions = self._advance_all_builders(current_time)

    if manual_movement_detected:
        # ... handle manual movement ...
        return

    # Collect contributions from all builders
    frame_delta = Vec2(0, 0)
    has_absolute_position = False
    absolute_target = None

    # Process velocity (speed + direction) - ALWAYS relative
    speed, direction = self._compute_velocity()
    velocity = direction * speed
    if speed != 0:
        dx, dy = self._subpixel_adjuster.adjust(velocity.x, velocity.y)
        frame_delta += Vec2(dx, dy)

    # Process position builders
    for layer, builder in self._active_builders.items():
        if builder.config.property != "pos":
            continue
            
        if builder.config.movement_type == "absolute":
            # pos.to() - need absolute positioning
            has_absolute_position = True
            absolute_target = builder.get_interpolated_value()  # Absolute coordinate
        else:
            # pos.by() - pure delta
            delta = builder.get_interpolated_value()  # Delta vector
            frame_delta += delta

    # Decide how to move mouse
    if has_absolute_position:
        # Mix: absolute target + relative deltas
        final_pos = absolute_target + frame_delta
        self._internal_pos = final_pos
        mouse_move(int(final_pos.x), int(final_pos.y))
    else:
        # Pure relative: just emit accumulated delta
        if frame_delta.x != 0 or frame_delta.y != 0:
            from .core import mouse_move_relative
            mouse_move_relative(int(frame_delta.x), int(frame_delta.y))

    # ... rest of frame loop ...
```

**Key Logic**:
1. Accumulate all relative deltas (speed, direction, pos.by)
2. Check if any builder needs absolute position (pos.to)
3. If absolute: compute final position and use `mouse_move()`
4. If pure relative: use `mouse_move_relative()`

---

## How Each Operation Works

### `pos.to(500, 300)` - Absolute
```python
# Builder init
config.movement_type = "absolute"
base_value = Vec2(*ctrl.mouse_pos())  # (400, 250)
target_value = Vec2(500, 300)

# Each frame: _get_own_value() returns animated absolute position
progress = 0.5
current = Vec2(450, 275)  # Interpolated absolute position

# In _tick_frame()
has_absolute_position = True
absolute_target = Vec2(450, 275)
mouse_move(450, 275)  # Absolute positioning
```

### `pos.by(100, 0)` - Relative
```python
# Builder init
config.movement_type = "relative"
base_value = Vec2(0, 0)  # Zero delta
target_value = Vec2(100, 0)  # Target delta

# Each frame: _get_own_value() returns animated delta
progress = 0.5
current_delta = Vec2(50, 0)  # 50% of target delta

# In _tick_frame()
frame_delta += Vec2(50, 0)
# ... accumulate more deltas ...
mouse_move_relative(50, 0)  # Relative movement
```

### `speed.to(100)` + `direction.to(1, 0)` - Relative
```python
# These produce velocity
velocity = direction * speed = Vec2(1, 0) * 100 = Vec2(100, 0)

# Each frame
dx, dy = subpixel_adjuster.adjust(100, 0)  # Say (5, 0) this frame
frame_delta += Vec2(5, 0)

# In _tick_frame()
mouse_move_relative(5, 0)  # Relative movement
```

### Mixed: `pos.to(500, 300)` + `pos.by(100, 0)`
```python
# pos.to provides absolute anchor
absolute_target = Vec2(500, 300)

# pos.by provides relative delta
frame_delta = Vec2(100, 0)

# Combined
final_pos = Vec2(500, 300) + Vec2(100, 0) = Vec2(600, 300)
mouse_move(600, 300)  # Absolute (because pos.to is present)
```

---

## Tracking Delta Progress for `pos.by`

### Challenge: How does builder know when done?

**Current solution already works!** The builder tracks:
```python
base_value = Vec2(0, 0)      # Start
target_value = Vec2(100, 0)  # Goal
lifecycle.progress  # 0.0 → 1.0
```

When `lifecycle.is_complete()` returns true, we've emitted the full delta.

**No additional tracking needed** - the existing lifecycle system handles it!

---

## State Changes Summary

### Minimal State Changes

```python
class RigState:
    def __init__(self):
        # Keep existing (used when pos.to is active)
        self._base_pos: Vec2
        self._internal_pos: Vec2
        
        # Keep existing (already works for velocity)
        self._base_speed: float
        self._base_direction: Vec2
        
        # No new state needed!
```

**Key insight**: We don't need `_accumulated_delta` because builders already track their own progress!

---

## Files That Need Changes

### 1. `contracts.py` - Add movement_type field
```python
class BuilderConfig:
    movement_type: str = "relative"  # "relative" or "absolute"
```

### 2. `builder.py` - Update initialization logic
- `PropertyBuilder.to()` - Set movement_type based on property
- `PropertyBuilder.by()` - Always set to "relative"
- `ActiveBuilder.__init__()` - Branch on movement_type for base_value

**Changes**: ~30 lines

### 3. `state.py` - Rewrite `_tick_frame()` logic
- Replace `_compute_current_state()` with contribution gathering
- Collect deltas from relative builders
- Check for absolute builders
- Decide `mouse_move()` vs `mouse_move_relative()`

**Changes**: ~100 lines

### 4. `state.py` - Update helper methods
- `_compute_velocity()` - Extract speed/direction computation
- Remove `_apply_position_updates()` (logic moves to _tick_frame)
- Keep `_apply_velocity_movement()` for subpixel adjustment

**Changes**: ~50 lines

### 5. Remove absolute position dependencies
- `_sync_to_manual_mouse_movement()` - Only works with absolute builders
- Frame loop sync - Only sync if absolute builder exists
- Position baking - Only bake if absolute

**Changes**: ~20 lines

---

## What Stays the Same (No Changes)

✅ All of `mode_operations.py` - Just math on Vec2
✅ All of `lifecycle.py` - Animation timing
✅ All of `rate_utils.py` - Duration calculations
✅ Layer system - Ordering unchanged
✅ Queue system - Unchanged
✅ Builder fluent API - Same interface
✅ Speed/direction operations - Already relative

---

## Migration Path

### Phase 1: Add movement_type field (1 hour)
- Add to `BuilderConfig`
- Set in `PropertyBuilder.to()` and `.by()`
- Default to "relative"

### Phase 2: Update builder initialization (2 hours)
- Branch in `ActiveBuilder.__init__()` based on movement_type
- `pos.to()` reads `ctrl.mouse_pos()` only if `movement_type == "absolute"`
- `pos.by()` stores deltas with base=(0,0)

### Phase 3: Rewrite `_tick_frame()` (4 hours)
- Gather contributions from all builders
- Accumulate relative deltas
- Check for absolute operations
- Emit via `mouse_move()` or `mouse_move_relative()`

### Phase 4: Testing (4 hours)
- Test pure relative (speed + direction)
- Test relative position (pos.by)
- Test absolute position (pos.to)
- Test mixed (pos.to + pos.by + speed)

### Phase 5: Clean up (2 hours)
- Remove unused code paths
- Update documentation
- Add settings for manual movement detection control

**Total: ~13 hours / 1.5-2 days**

---

## Benefits of This Approach

✅ **No separate API** - Same fluent interface
✅ **Switchable per-operation** - Mix absolute and relative freely
✅ **Minimal state** - Builders track their own progress
✅ **Clean separation** - Decision deferred to `_tick_frame()`
✅ **Use `mouse_move_relative`** - For pure relative scenarios
✅ **Keep absolute features** - Manual detection, baking (when needed)

---

## Example Usage Scenarios

### Gaming (Pure Relative)
```python
# Never calls ctrl.mouse_pos(), uses mouse_move_relative() exclusively
rig.speed.to(100)
rig.direction.to(1, 0)
rig.pos.by(50, 0)  # Pure delta
```

### Desktop (Absolute + Relative)
```python
# Reads ctrl.mouse_pos() once for pos.to, then mixes with relative
rig.pos.to(500, 300)  # Absolute anchor
rig.pos.by(100, 0)    # Relative offset
rig.speed.to(50)      # Relative velocity
```

### Navigation (Pure Absolute)
```python
# Uses mouse_move() with absolute coordinates
rig.pos.to(500, 300).over(200)
```

---

## The Key Innovation

**Don't change what builders store - change how we interpret it in `_tick_frame()`!**

Builders already know:
- Their base and target values
- Their current progress
- Their animated value

The movement_type just tells us:
- How to interpret those values (absolute coordinates vs deltas)
- Which mouse API to use at the end (mouse_move vs mouse_move_relative)

This is **much simpler** than rewriting the entire state model!
