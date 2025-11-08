# Migration Plan: Current Implementation → PRD 5

## Overview

This document outlines the plan to migrate from the current `mouse_rig.py` implementation to the new API design specified in PRD 5.

---

## Current State Analysis

Based on `mouse_rig.py`, the current implementation has:

**Implemented:**
- ✓ Core properties: `speed`, `accel`, `direction`, `pos`
- ✓ Value modifiers: `.to()`, `.by()`, `.mul()`, `.div()`
- ✓ Timing: `.over(duration, easing?)`
- ✓ Temporary effects: `.fade_in()`, `.hold()`, `.fade_out()`, `.fade_in_out()`
- ✓ Named effects: `rig("name")`
- ✓ Builder pattern for fluent API
- ✓ Effect system with lifecycle management
- ✓ State tracking via `RigState` class
- ✓ Transition system for animations

**Not Yet Implemented (PRD 5 features):**
- ✗ Rate-based timing (`.rate()`)
- ✗ Split effects/forces (currently just `rig("name")`)
- ✗ Constraints on effects (relative only) vs forces (absolute only)
- ✗ `rig.state` / `rig.base` property accessors (currently uses dictionary)
- ✗ `rig.bake()` for flattening state
- ✗ Lambda support for dynamic values
- ✗ Updated `rig.stop()` behavior (bake + clear + decelerate)

---

## Key Changes Summary

### 1. **API Terminology**
- `.fade_in()` → `.over()`
- `.fade_out()` → `.revert()`
- `.fade_in_out()` → removed (use `.over().revert()`)
- `rig("name")` → `rig.effect("name")` or `rig.force("name")`

### 2. **New Features**
- Rate-based timing
- Effect/force distinction with constraints
- State management improvements
- Baking/flattening
- Lambda support

---

## Migration Steps

### Phase 1: Rename `.fade_in()` to `.over()` and `.fade_out()` to `.revert()`

**Impact:** All builder classes that implement these methods

**Current classes to update:**
- `SpeedAdjustBuilder`
- `SpeedMultiplyBuilder`
- `SpeedDivideBuilder`
- `PropertyEffectBuilder`
- `DirectionBuilder`
- `PositionToBuilder`
- `PositionByBuilder`

**Tasks:**
1. [ ] Rename `fade_in(duration, easing?)` → `over(duration, easing?)`
   - Note: `.over()` already exists for permanent changes, this is now used for both
   - Update distinction: presence of `.revert()` or `.hold()` = temporary
2. [ ] Rename `fade_out(duration?, easing?)` → `revert(duration?, easing?)`
3. [ ] Update all docstrings mentioning `.fade_in()` / `.fade_out()`
4. [ ] Update module docstring (lines 1-75)
5. [ ] Verify `.hold()` alone triggers auto-revert (should already work)

**Code Changes:**
```python
# In each builder class:
# OLD:
def fade_in(self, duration: int, easing: str = "linear"):
    ...
def fade_out(self, duration: int = 0, easing: str = "linear"):
    ...

# NEW:
# (already have .over() for permanent, reuse for temporary)
def revert(self, duration: int = 0, easing: str = "linear"):
    ...
```

---

### Phase 2: Remove `.fade_in_out()` Method

**Impact:** All builder classes

**Tasks:**
1. [ ] Remove `fade_in_out()` method from all builders
2. [ ] Update any examples or tests using `.fade_in_out()`

---

### Phase 3: Split Named Effects into Effects and Forces

**Current Implementation:**
- `class NamedEffectBuilder` (line 1527)
- `class NamedSpeedController` (line 1565)
- `class NamedAccelController` (line 1598)
- `RigState.__call__(name)` creates `NamedEffectBuilder` (line 1677)

**Target Implementation:**
- `rig.effect("name")` - modifiers only (`.mul`, `.by`, `.div`)
- `rig.force("name")` - absolute only (`.to`, direct setters)

**Tasks:**
1. [ ] Create `effect(name)` method on `RigState`
   ```python
   def effect(self, name: str) -> 'NamedEffectBuilder':
       """Create or access a named effect (modifiers on base)"""
       ...
   ```

2. [ ] Create `force(name)` method on `RigState`
   ```python
   def force(self, name: str) -> 'NamedForceBuilder':
       """Create or access a named force (independent entity)"""
       ...
   ```

3. [ ] Create `NamedForceBuilder` class (similar to `NamedEffectBuilder`)
   - Has `.speed`, `.accel`, `.direction` controllers
   - Controllers only allow `.to()` and absolute setters
   - Error on `.mul()`, `.by()`, `.div()`

4. [ ] Update `NamedEffectBuilder` constraints
   - Only allow `.mul()`, `.by()`, `.div()`
   - Error on `.to()` or absolute setters
   - Add validation in `NamedSpeedController` and `NamedAccelController`

5. [ ] Add `stop_all()` methods
   ```python
   @property
   def effect(self):
       return NamedEffectNamespace(self)

   class NamedEffectNamespace:
       def __call__(self, name: str):
           return NamedEffectBuilder(...)
       def stop_all(self, duration=0, easing="linear"):
           # Stop all named effects
           ...
   ```

6. [ ] Keep `__call__` for backward compatibility (optional transition period)
   ```python
   def __call__(self, name: str):
       # Deprecated: use .effect() or .force()
       return self.effect(name)
   ```

---

### Phase 4: Implement Rate-Based Timing

**New Feature:** `.rate(value)` and `.rate.property(value)`

**Tasks:**
1. [ ] Add `.rate(value)` method to all property builders
   ```python
   class SpeedAdjustBuilder:
       def rate(self, value: float):
           """Change speed at specified rate (speed/sec)"""
           # Calculate duration based on distance / rate
           distance = abs(self._target - current_speed)
           duration = (distance / value) * 1000  # convert to ms
           return self.over(duration)  # reuse .over() machinery
   ```

2. [ ] Add `.rate` namespace with property-specific methods
   ```python
   class SpeedRateNamespace:
       def __init__(self, builder):
           self._builder = builder

       def accel(self, value: float):
           """Change speed via acceleration rate (accel/sec²)"""
           # Physics-based: v = at, solve for t
           ...

   class SpeedAdjustBuilder:
       @property
       def rate(self):
           return SpeedRateNamespace(self)
   ```

3. [ ] Implement for each property type:
   - Speed: `.rate(speed/sec)`, `.rate.accel(accel/sec²)`
   - Accel: `.rate(accel/sec²)`, `.rate.accel(jerk)`
   - Direction: `.rate(degrees/sec)`
   - Position: `.rate.speed(px/sec)`

4. [ ] No easing support for `.rate()` - validate this

---

### Phase 5: State Management Improvements

**Current:** `RigState` class exists but state access is via methods returning dicts

**Target:** Property accessors for `rig.state` and `rig.base`

**Tasks:**
1. [ ] Create state accessor classes
   ```python
   class StateAccessor:
       def __init__(self, rig_state: RigState):
           self._rig = rig_state

       @property
       def speed(self) -> float:
           """Get computed speed (base + effects + forces)"""
           return self._rig._compute_final_speed()

       @property
       def accel(self) -> float:
           return self._rig._compute_final_accel()

       @property
       def direction(self) -> Tuple[float, float]:
           dir_vec = self._rig._compute_final_direction()
           return (dir_vec.x, dir_vec.y)

       @property
       def pos(self) -> Tuple[int, int]:
           return ctrl.mouse_pos()

   class BaseAccessor:
       def __init__(self, rig_state: RigState):
           self._rig = rig_state

       @property
       def speed(self) -> float:
           return self._rig._speed

       @property
       def accel(self) -> float:
           return self._rig._accel

       @property
       def direction(self) -> Tuple[float, float]:
           return (self._rig._direction.x, self._rig._direction.y)

       @property
       def pos(self) -> Tuple[int, int]:
           return ctrl.mouse_pos()
   ```

2. [ ] Add properties to `RigState`
   ```python
   @property
   def state(self) -> StateAccessor:
       """Access computed state (base + effects + forces)"""
       if not hasattr(self, '_state_accessor'):
           self._state_accessor = StateAccessor(self)
       return self._state_accessor

   @property
   def base(self) -> BaseAccessor:
       """Access base values only"""
       if not hasattr(self, '_base_accessor'):
           self._base_accessor = BaseAccessor(self)
       return self._base_accessor
   ```

3. [ ] Implement computation methods
   ```python
   def _compute_final_speed(self) -> float:
       # Start with base
       final = self._speed
       # Apply speed transitions
       if self._speed_transition:
           final = self._speed_transition.current_value(...)
       # Apply effects
       for effect in self._effects:
           if effect.property == "speed":
               final = effect.apply(final)
       return final
   ```

---

### Phase 6: Implement Baking

**New Feature:** `rig.bake()`

**Tasks:**
1. [ ] Implement `bake()` method on `RigState`
   ```python
   def bake(self):
       """Flatten computed state into base, clear all effects and forces"""
       # Compute final values
       final_speed = self._compute_final_speed()
       final_accel = self._compute_final_accel()
       final_direction = self._compute_final_direction()

       # Set as new base
       self._speed = final_speed
       self._accel = final_accel
       self._direction = final_direction

       # Clear all effects
       self._effects.clear()
       self._named_effects.clear()
       self._accel_velocities.clear()

       # Clear transitions
       self._speed_transition = None
       self._direction_transition = None
   ```

---

### Phase 7: Update Global Stop Behavior

**Current:** `stop()` exists but behavior unclear

**Target:** Bake, clear, decelerate to 0

**Tasks:**
1. [ ] Update `stop()` method
   ```python
   def stop(self, duration: int = 0, easing: str = "linear"):
       """Stop everything: bake state, clear effects/forces, decelerate to 0"""
       # 1. Bake current state
       self.bake()

       # 2. Effects/forces already cleared by bake()

       # 3. Decelerate speed to 0
       if duration > 0:
           self.speed.to(0).over(duration, easing)
       else:
           self._speed = 0
   ```

---

### Phase 8: Lambda Support

**New Feature:** Accept lambdas in value modifiers

**Tasks:**
1. [ ] Update value modifier signatures
   ```python
   def to(self, value: Union[float, Callable[[StateAccessor], float]]):
       """Set to absolute value or lambda"""
       if callable(value):
           # Evaluate lambda with current state
           value = value(self._rig.state)
       # Rest of implementation
       ...
   ```

2. [ ] Update all value modifiers: `.to()`, `.by()`, `.mul()`, `.div()`
3. [ ] Ensure evaluation happens at execution time, not definition time

---

### Phase 9: Error Handling

**Tasks:**
1. [ ] Add validation for property chaining
   ```python
   # In SpeedController, AccelController, etc.
   def __call__(self, value):
       # Return builder that checks if chained incorrectly
       return SpeedBuilder(self._rig, value, detect_chaining=True)
   ```

2. [ ] Add constraint violations for effects/forces
   ```python
   class NamedEffectBuilder:
       def _validate_relative_only(self):
           # Called when using .to() or absolute setter
           raise ValueError(
               "Effects can only use relative modifiers (.mul, .by, .div). "
               "Use rig.force('name') for absolute values."
           )

   class NamedForceBuilder:
       def _validate_absolute_only(self):
           # Called when using .mul(), .by(), .div()
           raise ValueError(
               "Forces can only use absolute setters (.to, direct values). "
               "Use rig.effect('name') for relative modifiers."
           )
   ```

---

### Phase 10: Testing and Documentation

**Tasks:**
1. [ ] Update all tests
2. [ ] Update module docstring (lines 1-75)
3. [ ] Update inline documentation
4. [ ] Create migration guide
5. [ ] Update examples in `examples.py` and `examples.talon`

---

## Breaking Changes for Users

1. **`.fade_in()` → `.over()`**
2. **`.fade_out()` → `.revert()`**
3. **`.fade_in_out()` removed - use `.over().revert()`**
4. **`rig("name")` → `rig.effect("name")` or `rig.force("name")`**
5. **State access: `rig.state()["speed"]` → `rig.state.speed`**

---

## Implementation Priority

1. **Phase 1** - Rename `.fade_in()`/`.fade_out()` (biggest breaking change)
2. **Phase 5** - State management (dict → class)
3. **Phase 3** - Split effects/forces
4. **Phase 4** - Rate-based timing
5. **Phase 6-7** - Baking and stop
6. **Phase 8** - Lambda support
7. **Phase 9** - Error handling
8. **Phase 2, 10** - Cleanup and docs

---

## File Changes Required

**Primary file:** `mouse_rig.py` (2195 lines)

**Classes to modify:**
- `RigState` - add `.effect()`, `.force()`, `.bake()`, state properties
- `SpeedAdjustBuilder` - rename methods, add `.rate()`
- `SpeedMultiplyBuilder` - rename methods
- `SpeedDivideBuilder` - rename methods
- `PropertyEffectBuilder` - rename methods
- `DirectionBuilder` - rename methods, add `.rate()`
- `PositionToBuilder` - rename methods, add `.rate()`
- `PositionByBuilder` - rename methods
- `NamedEffectBuilder` - add constraints
- `NamedSpeedController` - add constraints
- `NamedAccelController` - add constraints

**Classes to create:**
- `NamedForceBuilder`
- `NamedForceSpeedController`
- `NamedForceAccelController`
- `StateAccessor`
- `BaseAccessor`
- `SpeedRateNamespace`
- `DirectionRateNamespace`
- `PositionRateNamespace`
- `NamedEffectNamespace` / `NamedForceNamespace` (for `.stop_all()`)

---

## Testing Strategy

1. Create test suite for new API
2. Run existing tests with compatibility layer
3. Migrate tests incrementally
4. Remove compatibility layer
5. Verify all examples work

---

## Rollout

**Recommended approach:** Big Bang
- Implement all changes in feature branch
- Test thoroughly
- Deploy with clear migration guide
- Simpler than maintaining two APIs

---

## Success Criteria

- [ ] All PRD 5 features implemented
- [ ] All breaking changes documented
- [ ] Migration guide complete
- [ ] All tests passing
- [ ] Examples updated
- [ ] No regressions
