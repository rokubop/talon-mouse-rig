# Migration Plan: PRD 5 → PRD 6

## Overview

This document outlines the comprehensive plan to migrate from the current PRD 5 implementation to the PRD 6 API design. PRD 6 introduces a unified API with named entities, type inference, and clearer semantics around transforms vs forces.

**Document Purpose:** Each step is enumerated for sign-off before implementation.

---

## Current State (PRD 5)

**Implemented:**
- ✓ Core properties: `speed`, `accel`, `direction`, `pos`
- ✓ Value modifiers: `.to()`, `.by()`, `.mul()`, `.div()`
- ✓ Timing: `.over(duration, easing?)`
- ✓ Temporary effects: `.hold()`, `.revert()`
- ✓ Named modifiers: `rig.modifier("name")`
- ✓ Named forces: `rig.force("name")`
- ✓ Effect system with lifecycle management
- ✓ State accessors: `rig.state`, `rig.base`
- ✓ Baking: `rig.bake()`
- ✓ Rate-based timing: `.rate()`

**Key Differences from PRD 6:**
- Separate APIs: `rig.modifier()` vs `rig.force()`
- No `scale.*` / `shift.*` distinction (uses `.mul()`, `.by()`, `.div()`)
- No unified `rig(name)` entry point
- No type inference (explicit modifier vs force)
- No max constraints (`.max.speed()`, `.max.stack()`)
- No anonymous entities (`rig()` without name)
- Forces use separate property setters instead of unified `velocity()`

---

## PRD 6 Key Changes

### 1. **Unified Entry Point**
```python
# PRD 5
rig.modifier("sprint").speed.mul(2)
rig.force("gravity").speed(9.8).direction(0, 1)

# PRD 6
rig("sprint").scale.speed.to(2)
rig("gravity").direction(0, 1).accel(9.8)
```

### 2. **Type Inference**
Entities infer type based on operations:
- Uses `scale.*` or `shift.*` → Transform
- Sets properties like `direction()`, `speed()`, `velocity()` → Force
- Mixing transform and force operations → Error

### 3. **Transform Operations: Scale vs Shift**
```python
# PRD 5: .mul() and .by()
rig.modifier("sprint").speed.mul(2)
rig.modifier("boost").speed.by(10)

# PRD 6: .scale and .shift with .to()/.by()
rig("sprint").scale.speed.to(2)      # Multiply
rig("boost").shift.speed.by(10)      # Add/stack
```

### 4. **Stacking Semantics**
- `.to(value)` → Set/replace (idempotent)
- `.by(value)` → Add/stack (accumulates)

### 5. **Max Constraints**
```python
rig("boost").shift.speed.by(10).max.speed(50)
rig("boost").shift.speed.by(10).max.stack(3)
```

### 6. **Anonymous Entities**
```python
rig().shift.speed.by(10).hold(2000).revert(1000)
```

### 7. **Force Unification**
```python
# PRD 5: Separate setters
rig.force("wind").speed(5).direction(1, 0)

# PRD 6: Can use velocity() or separate setters
rig("wind").velocity(5, 0)
rig("wind").direction(1, 0).speed(5)
```

---

## Migration Steps

Each step is designed to be independently implementable and testable.

---

### **STEP 1: Create Unified Entry Point `rig(name)`**

**Goal:** Add `rig(name)` method that returns a unified entity builder.

**Changes:**
- Add `rig.__call__(name: Optional[str] = None)` method to `RigState`
- Create new `EntityBuilder` class that:
  - Defers type inference until operations are used
  - Tracks whether it's a transform or force
  - Throws error if mixing transform/force operations
- Keep existing `rig.modifier()` and `rig.force()` for backward compatibility

**Implementation Notes:**
- Initially, `EntityBuilder` delegates to existing modifier/force builders
- Type is determined on first operation:
  - `.scale` or `.shift` → Transform mode
  - `.direction()`, `.speed()`, `.velocity()`, `.accel()` → Force mode
- Store entity type in internal flag: `_entity_type: Optional[Literal["transform", "force"]]`

**Testing:**
```python
# Should work - transform
rig("sprint").scale.speed.to(2)

# Should work - force
rig("gravity").direction(0, 1).accel(9.8)

# Should error - mixing
rig("bad").scale.speed.to(2)
rig("bad").direction(1, 0)  # Error!
```

**Sign-off required before proceeding to Step 2**

---

### **STEP 2: Implement Scale/Shift Transform Operations**

**Goal:** Replace `.mul()` with `.scale.*` and consolidate `.by()` into `.shift.*`

**Changes:**
- Add `ScaleBuilder` class with properties:
  - `.speed` → returns `ScaleSpeedBuilder`
  - `.accel` → returns `ScaleAccelBuilder`
- Add `ShiftBuilder` class with properties:
  - `.speed` → returns `ShiftSpeedBuilder`
  - `.accel` → returns `ShiftAccelBuilder`
  - `.direction` → returns `ShiftDirectionBuilder`
  - `.pos` → returns `ShiftPosBuilder`
- Each builder supports `.to(value)` and `.by(value)`
- Add `.scale` and `.shift` properties to `EntityBuilder` (transform mode only)

**Implementation Details:**

**Scale Operations (multiplicative):**
```python
# .to() = set multiplier
rig("sprint").scale.speed.to(2)      # scale = ×2
rig("sprint").scale.speed.to(3)      # scale = ×3 (replaced)

# .by() = add to multiplier (stacking)
rig("stack").scale.speed.by(2)       # scale = ×2
rig("stack").scale.speed.by(1)       # scale = ×3 (2+1 stacked)
```

**Shift Operations (additive):**
```python
# .to() = set offset
rig("boost").shift.speed.to(10)      # offset = +10
rig("boost").shift.speed.to(15)      # offset = +15 (replaced)

# .by() = add to offset (stacking)
rig("boost").shift.speed.by(5)       # offset = +5
rig("boost").shift.speed.by(5)       # offset = +10 (stacked)
```

**Internal Representation:**
- Store scale and shift separately in effect:
  - `_scale_multiplier: float = 1.0`
  - `_shift_offset: float = 0.0`
- Application order: `(base * scale) + shift`
- Track `.to()` vs `.by()` operations per entity for stacking logic

**Testing:**
```python
# Scale
rig.speed(10)
rig("sprint").scale.speed.to(2)      # computed = 20
rig("sprint").scale.speed.to(3)      # computed = 30 (replaced)

# Shift
rig("boost").shift.speed.to(5)       # computed = 10 + 5 = 15
rig("boost").shift.speed.by(5)       # computed = 10 + 5 + 5 = 20 (stacked)

# Combined
rig("combo").scale.speed.to(2)       # ×2
rig("combo").shift.speed.to(5)       # +5
# computed = (10 × 2) + 5 = 25
```

**Sign-off required before proceeding to Step 3**

---

### **STEP 3: Implement `.to()` vs `.by()` Stacking Semantics**

**Goal:** Ensure `.to()` is idempotent (set/replace) and `.by()` accumulates (stack).

**Changes:**
- Modify effect tracking to distinguish between `.to()` and `.by()` operations
- For `.to()`: Replace existing value for that entity
- For `.by()`: Accumulate values across multiple calls
- Track per-entity stack count for `.max.stack()` (Step 6)

**Implementation Details:**

**Data Structure:**
```python
# Per named entity, track:
{
  "boost": {
    "scale_speed": {
      "mode": "by",              # "to" or "by"
      "values": [2, 1],          # List for .by(), single value for .to()
      "total": 3                 # Sum (for .by()) or value (for .to())
    },
    "shift_speed": {
      "mode": "to",
      "values": [10],
      "total": 10
    }
  }
}
```

**Behavior:**
```python
# .to() - idempotent
rig("a").scale.speed.to(2)           # total = 2
rig("a").scale.speed.to(3)           # total = 3 (replaced)

# .by() - accumulates
rig("b").scale.speed.by(2)           # total = 2
rig("b").scale.speed.by(1)           # total = 3 (2+1)
rig("b").scale.speed.by(-1)          # total = 2 (3-1)
```

**Edge Cases:**
- Calling `.to()` after `.by()` on same entity → Replace entire stack with single value
- Calling `.by()` after `.to()` → Start accumulating from `.to()` value

**Testing:**
```python
rig.speed(10)

# Scenario 1: .to() only
rig("test").scale.speed.to(2)        # computed = 20
rig("test").scale.speed.to(3)        # computed = 30

# Scenario 2: .by() only
rig("test2").shift.speed.by(5)       # computed = 15
rig("test2").shift.speed.by(5)       # computed = 20

# Scenario 3: .by() then .to()
rig("test3").shift.speed.by(5)       # computed = 15
rig("test3").shift.speed.by(5)       # computed = 20
rig("test3").shift.speed.to(8)       # computed = 18 (replaced stack)

# Scenario 4: .to() then .by()
rig("test4").shift.speed.to(10)      # computed = 20
rig("test4").shift.speed.by(5)       # computed = 25 (10 + 5)
```

**Sign-off required before proceeding to Step 4**

---

### **STEP 4: Implement Force Property Unification**

**Goal:** Allow forces to use either `velocity(x, y)` or `direction().speed()`.

**Changes:**
- Add `.velocity(x, y)` method to force entity builder
- When used, internally converts to direction + speed
- Update existing force system to accept velocity vectors
- Keep backward compatibility with separate setters

**Implementation Details:**

**New API:**
```python
# Method 1: Direct velocity
rig("wind").velocity(5, 3)
# Internally: direction = (5, 3).normalize(), speed = sqrt(5²+3²)

# Method 2: Separate (existing)
rig("wind").direction(1, 0).speed(5)
# Already works
```

**Internal Representation:**
- Store as `_velocity: Vec2` or separate `_direction + _speed`
- Convert between representations as needed
- Normalize direction vectors automatically

**Testing:**
```python
rig.speed(10).direction(1, 0)        # base velocity = (10, 0)

# Velocity method
rig("wind").velocity(0, 5)           # force velocity = (0, 5)
# Final velocity = (10, 0) + (0, 5) = (10, 5)

# Separate method (equivalent)
rig("wind2").direction(0, 1).speed(5)  # force velocity = (0, 5)
# Final velocity = (10, 0) + (0, 5) = (10, 5)
```

**Sign-off required before proceeding to Step 5**

---

### **STEP 5: Implement Type Inference and Validation**

**Goal:** Enforce transform vs force constraints and error on mixing.

**Changes:**
- Add validation in `EntityBuilder` to track entity type
- Throw descriptive errors when mixing operations
- Prevent transforms from setting direction/velocity
- Prevent forces from using scale/shift

**Implementation Details:**

**Type Inference Logic:**
```python
class EntityBuilder:
    def __init__(self, name: str):
        self._name = name
        self._entity_type: Optional[Literal["transform", "force"]] = None
    
    @property
    def scale(self):
        if self._entity_type == "force":
            raise ValueError(f"Entity '{self._name}' is a force, cannot use .scale")
        self._entity_type = "transform"
        return ScaleBuilder(self)
    
    @property
    def shift(self):
        if self._entity_type == "force":
            raise ValueError(f"Entity '{self._name}' is a force, cannot use .shift")
        self._entity_type = "transform"
        return ShiftBuilder(self)
    
    def velocity(self, x, y):
        if self._entity_type == "transform":
            raise ValueError(f"Entity '{self._name}' is a transform, cannot set velocity")
        self._entity_type = "force"
        # ... set velocity
```

**Error Messages:**
```python
# Case 1: Transform trying to set direction
rig("sprint").scale.speed.to(2)
rig("sprint").direction(1, 0)
# Error: Entity 'sprint' is a transform, cannot set direction.
#        Transforms modify base properties using .scale/.shift.
#        Use a separate force entity for independent direction.

# Case 2: Force trying to use scale
rig("wind").velocity(5, 0)
rig("wind").scale.speed.to(2)
# Error: Entity 'wind' is a force, cannot use .scale.
#        Forces are independent entities with absolute values.
#        Use a transform entity to modify base properties.
```

**Testing:**
```python
# Valid transform
rig("sprint").scale.speed.to(2)

# Valid force
rig("gravity").direction(0, 1).accel(9.8)

# Invalid - mixing
try:
    rig("bad").scale.speed.to(2)
    rig("bad").direction(1, 0)
    assert False, "Should have raised error"
except ValueError as e:
    assert "is a transform" in str(e)
```

**Sign-off required before proceeding to Step 6**

---

### **STEP 6: Implement Max Constraints**

**Goal:** Add `.max.speed()`, `.max.accel()`, `.max.stack()` constraint methods.

**Changes:**
- Add `MaxBuilder` class with properties:
  - `.speed(value)` → caps final computed speed
  - `.accel(value)` → caps final computed accel
  - `.stack(count)` → limits number of stacks
- Add `.max` property to transform builders
- Add `.max(value)` shorthand that infers constraint type

**Implementation Details:**

**Max Value Constraints:**
```python
rig("boost").shift.speed.by(10).max.speed(50)
# Even if multiple stacks exceed 50, cap at 50

# Internal tracking:
{
  "boost": {
    "shift_speed": {"values": [10, 10, 10, 10, 10], "total": 50},
    "max_speed": 50  # Constraint
  }
}
```

**Max Stack Constraints:**
```python
rig("boost").shift.speed.by(10).max.stack(3)
# Only first 3 calls stack, 4th+ ignored

# Internal tracking:
{
  "boost": {
    "shift_speed": {
      "values": [10, 10, 10],  # Only 3 values
      "max_stack": 3
    }
  }
}

# On 4th call:
rig("boost").shift.speed.by(10)  # Ignored, max stack reached
```

**Shorthand Inference:**
```python
# Context-aware shorthand
rig("boost").shift.speed.by(10).max(50)
# Infers .max.speed(50) because operating on speed

rig("boost").shift.accel.by(5).max(20)
# Infers .max.accel(20) because operating on accel
```

**Testing:**
```python
rig.speed(10)

# Max speed constraint
rig("boost").shift.speed.by(20).max.speed(25)
rig("boost").shift.speed.by(20).max.speed(25)  # Stack
# computed = min(10 + 20 + 20, 25) = 25 (capped)

# Max stack constraint
rig("boost2").shift.speed.by(5).max.stack(3)
rig("boost2").shift.speed.by(5)
rig("boost2").shift.speed.by(5)
rig("boost2").shift.speed.by(5)  # Ignored
# computed = 10 + 5 + 5 + 5 = 25 (only 3 stacks)
```

**Sign-off required before proceeding to Step 7**

---

### **STEP 7: Implement Anonymous Entities**

**Goal:** Support `rig()` without name for auto-cleanup temporary effects.

**Changes:**
- Make `name` parameter optional in `rig(name?)`
- Auto-generate names like `"_anon_1"`, `"_anon_2"`, etc.
- Auto-remove after lifecycle completes (`.hold()` or `.revert()`)
- Add counter for anonymous entity naming

**Implementation Details:**

**Auto-naming:**
```python
class RigState:
    def __init__(self):
        self._anon_counter = 0
    
    def __call__(self, name: Optional[str] = None):
        if name is None:
            self._anon_counter += 1
            name = f"_anon_{self._anon_counter}"
        return EntityBuilder(self, name, is_anonymous=(name is None))
```

**Auto-cleanup:**
- Anonymous entities MUST have lifecycle (`.hold()` or `.revert()`)
- Automatically remove from tracking after lifecycle completes
- Error if anonymous entity created without lifecycle

**Testing:**
```python
# Anonymous transform
rig().shift.speed.by(10).hold(2000).revert(1000)
# Auto-named as "_anon_1", auto-removed after 3s

# Anonymous force
rig().velocity(5, 0).hold(1000).revert(500)
# Auto-named as "_anon_2", auto-removed after 1.5s

# Error - no lifecycle
try:
    rig().shift.speed.by(10)  # No .hold() or .revert()
    assert False, "Should have raised error"
except ValueError as e:
    assert "anonymous entity" in str(e).lower()
    assert "lifecycle" in str(e).lower()
```

**Sign-off required before proceeding to Step 8**

---

### **STEP 8: Update Transform Composition Pipeline**

**Goal:** Ensure transforms apply in order: scale before shift within entity, entities in creation order.

**Changes:**
- Modify effect application to respect:
  1. Within entity: scale first, then shift
  2. Across entities: creation order (sequential)
- Update calculation logic in state computation
- Ensure transforms recalculate when base changes

**Implementation Details:**

**Within Entity (scale before shift):**
```python
rig.speed(10)
rig("combo").scale.speed.to(2)       # ×2
rig("combo").shift.speed.to(5)       # +5

# Application: (base * scale) + shift
# Computed: (10 * 2) + 5 = 25
```

**Across Entities (creation order):**
```python
rig.speed(10)
rig("first").scale.speed.to(2)       # Created first
rig("second").shift.speed.to(5)      # Created second

# Pipeline:
# base = 10
# → first: 10 * 2 = 20
# → second: 20 + 5 = 25
```

**Transform Recalculation:**
```python
rig.speed(10)
rig("sprint").scale.speed.to(2)
# computed = 20

rig.speed(20)  # Change base
# computed = 40 (transform recalculates automatically)
```

**Testing:**
```python
# Test within-entity order
rig.speed(10)
rig("test").shift.speed.to(5)        # +5
rig("test").scale.speed.to(2)        # ×2 (added later)
# Computed: (10 * 2) + 5 = 25 (scale always first)

# Test cross-entity order
rig.speed(10)
rig("a").scale.speed.to(2)           # Created 1st: ×2
rig("b").shift.speed.to(3)           # Created 2nd: +3
rig("c").scale.speed.to(1.5)         # Created 3rd: ×1.5
# Pipeline: ((10 * 2) + 3) * 1.5 = 34.5

# Test recalculation
rig.speed(10)
rig("sprint").scale.speed.to(2)
assert rig.state.speed == 20
rig.speed(15)
assert rig.state.speed == 30  # Recalculated
```

**Sign-off required before proceeding to Step 9**

---

### **STEP 9: Update Fixed Pipeline Order (Base → Transforms → Forces)**

**Goal:** Ensure forces always apply after all transforms via vector addition.

**Changes:**
- Separate transform computation from force computation
- Compute final state in fixed order:
  1. Base state
  2. Apply all transforms (in creation order)
  3. Apply all forces (vector addition)
  4. Final state
- Update `rig.state` accessors to use correct pipeline

**Implementation Details:**

**Pipeline Steps:**
```python
def _compute_state(self):
    # 1. Start with base
    speed = self._speed
    direction = self._direction
    
    # 2. Apply all transforms (in creation order)
    for transform in self._transforms_ordered:
        if transform.target == "speed":
            speed = (speed * transform.scale) + transform.shift
    
    # 3. Apply all forces (vector addition)
    base_velocity = Vec2(direction.x * speed, direction.y * speed)
    for force in self._forces.values():
        base_velocity += force.velocity
    
    # 4. Final state
    final_speed = base_velocity.magnitude()
    final_direction = base_velocity.normalized()
    
    return final_speed, final_direction
```

**Testing:**
```python
rig.speed(10).direction(1, 0)        # base velocity = (10, 0)

# Transform: double speed
rig("sprint").scale.speed.to(2)      # transform velocity = (20, 0)

# Force: push down
rig("gravity").velocity(0, 5)        # force velocity = (0, 5)

# Final: (20, 0) + (0, 5) = (20, 5)
assert rig.state.velocity == (20, 5)
assert rig.state.speed == math.sqrt(20**2 + 5**2)

# Change base - transform recalculates, force stays constant
rig.speed(20)
# transform velocity = (40, 0)
# force velocity = (0, 5)
# final = (40, 5)
assert rig.state.velocity == (40, 5)
```

**Sign-off required before proceeding to Step 10**

---

### **STEP 10: Update Documentation and Examples**

**Goal:** Update all documentation, docstrings, and examples to PRD 6 API.

**Changes:**
- Update module docstring (lines 1-114 in `mouse_rig.py`)
- Update all class/method docstrings
- Update `examples.py` with PRD 6 patterns
- Update `examples.talon` with PRD 6 commands
- Create new `PRD6_EXAMPLES.md` with comprehensive examples

**Files to Update:**
1. `mouse_rig.py` - module docstring
2. `mouse_rig.py` - all class docstrings
3. `examples.py` - convert PRD 5 → PRD 6 examples
4. `examples.talon` - update voice commands
5. `PRD6_EXAMPLES.md` - new comprehensive examples document

**Documentation Sections:**
- Quick Start
- Transform Examples (scale/shift)
- Force Examples
- Stacking Examples (.to() vs .by())
- Max Constraints
- Anonymous Entities
- Composition Pipeline
- Complete Use Cases (WASD, boost pads, gravity, etc.)

**Sign-off required before proceeding to Step 11**

---

### **STEP 11: Deprecate Old API (Optional Backward Compatibility)**

**Goal:** Decide on backward compatibility strategy for PRD 5 API.

**Options:**

**Option A: Hard Break (Recommended)**
- Remove `rig.modifier()` and `rig.force()`
- Remove `.mul()` and `.div()` methods
- All users must migrate to PRD 6

**Option B: Deprecation Period**
- Keep `rig.modifier()` and `rig.force()` with deprecation warnings
- Keep `.mul()` as alias for `.scale.*.to()`
- Print warnings but allow old API
- Remove in future version

**Option C: Permanent Compatibility**
- Keep both APIs indefinitely
- Internally map old API to new implementation
- More maintenance burden

**Recommendation:** Option A (hard break) since this is early development.

**If Option B chosen, implementation:**
```python
def modifier(self, name: str):
    print(f"Warning: rig.modifier() is deprecated. Use rig('{name}').scale/shift instead.")
    return self(name)

def force(self, name: str):
    print(f"Warning: rig.force() is deprecated. Use rig('{name}') with direct properties instead.")
    return self(name)
```

**Sign-off required before proceeding to Step 12**

---

### **STEP 12: Testing and Validation**

**Goal:** Comprehensive testing of all PRD 6 features.

**Test Categories:**

**12.1: Unit Tests**
- Transform operations (scale/shift with .to()/.by())
- Force operations (velocity/direction/speed)
- Type inference and validation
- Max constraints (value and stack)
- Anonymous entities
- Pipeline order (scale before shift, transforms before forces)
- Stacking semantics (.to() vs .by())

**12.2: Integration Tests**
- Complete workflows (WASD movement with sprint)
- Boost pad stacking with max constraints
- Gravity + wind forces
- Complex compositions (transforms + forces)
- Lifecycle management (hold/revert with auto-cleanup)

**12.3: Edge Cases**
- Mixing .to() and .by() on same entity
- Changing base while transforms active
- Multiple anonymous entities
- Stopping entities during animation
- Max stack limits
- Zero/negative values

**12.4: Performance Tests**
- Many entities (100+ transforms/forces)
- Rapid entity creation/destruction
- Frame rate stability

**Testing Tools:**
- Create `test_prd6.py` with pytest
- Add assertions in `examples.py`
- Manual testing with `examples.talon`

**Sign-off required before declaring PRD 6 complete**

---

## Implementation Timeline

**Estimated Effort per Step:**
- Step 1: 2-3 hours (unified entry point)
- Step 2: 4-6 hours (scale/shift operations)
- Step 3: 2-3 hours (stacking semantics)
- Step 4: 1-2 hours (force velocity unification)
- Step 5: 2-3 hours (type inference/validation)
- Step 6: 3-4 hours (max constraints)
- Step 7: 2-3 hours (anonymous entities)
- Step 8: 2-3 hours (transform composition)
- Step 9: 3-4 hours (pipeline order)
- Step 10: 4-6 hours (documentation)
- Step 11: 1 hour (deprecation strategy decision)
- Step 12: 6-8 hours (comprehensive testing)

**Total Estimated Time:** 32-46 hours

**Recommended Approach:**
1. Implement steps sequentially (each builds on previous)
2. Get sign-off before starting each step
3. Test thoroughly after each step
4. Commit after each successful step
5. Can parallelize Steps 10-12 after Step 9 complete

---

## Risk Mitigation

**Risks:**

1. **Breaking existing code**
   - Mitigation: Keep PRD 5 implementation in separate branch
   - Test migration path thoroughly

2. **Complex state management**
   - Mitigation: Comprehensive unit tests for each step
   - Clear separation of transform vs force logic

3. **Performance degradation**
   - Mitigation: Performance tests in Step 12
   - Profile before/after

4. **API complexity**
   - Mitigation: Extensive documentation and examples
   - User feedback before finalizing

---

## Success Criteria

PRD 6 is complete when:

✓ All 12 steps implemented and signed off
✓ All tests passing (unit + integration + edge cases)
✓ Documentation comprehensive and accurate
✓ Examples demonstrate all major features
✓ Performance meets or exceeds PRD 5
✓ No breaking bugs in common workflows

---

## Next Steps

1. Review this migration plan
2. Sign off on overall approach
3. Sign off on Step 1
4. Implement Step 1
5. Test and validate Step 1
6. Sign off on Step 2
7. Continue through all steps sequentially

---

## Questions for Sign-Off

Before proceeding, please confirm:

1. **Unified API:** Approve `rig(name)` as single entry point?
2. **Scale/Shift:** Approve `.scale.*` and `.shift.*` keywords?
3. **Stacking:** Approve `.to()` (replace) vs `.by()` (accumulate) semantics?
4. **Type Inference:** Approve automatic transform vs force detection?
5. **Max Constraints:** Approve `.max.speed()` / `.max.stack()` API?
6. **Anonymous:** Approve `rig()` without name for temporary effects?
7. **Pipeline:** Approve fixed order (base → transforms → forces)?
8. **Backward Compatibility:** Choose Option A, B, or C from Step 11?
9. **Timeline:** Approve estimated 32-46 hour timeline?
10. **Testing:** Approve comprehensive test plan in Step 12?

---

## Appendix: API Comparison

### PRD 5 vs PRD 6 Side-by-Side

```python
# ============================================================================
# TRANSFORMS (modify base properties)
# ============================================================================

# PRD 5
rig.modifier("sprint").speed.mul(2)
rig.modifier("sprint").speed.by(10)
rig.modifier("sprint").stop()

# PRD 6
rig("sprint").scale.speed.to(2)      # Multiply
rig("sprint").shift.speed.by(10)     # Add/stack
rig("sprint").stop()

# ============================================================================
# FORCES (independent entities)
# ============================================================================

# PRD 5
rig.force("gravity").speed(9.8).direction(0, 1)
rig.force("wind").speed(5).direction(1, 0)
rig.force("wind").stop()

# PRD 6
rig("gravity").direction(0, 1).accel(9.8)
rig("wind").velocity(5, 0)
rig("wind").stop()

# ============================================================================
# TEMPORARY EFFECTS
# ============================================================================

# PRD 5
rig.speed.mul(2).hold(1000).revert(500)

# PRD 6 (anonymous)
rig().scale.speed.to(2).hold(1000).revert(500)

# ============================================================================
# STACKING
# ============================================================================

# PRD 5 (implicit)
rig.modifier("boost").speed.by(10)
rig.modifier("boost").speed.by(10)   # Stacks

# PRD 6 (explicit)
rig("boost").shift.speed.by(10)
rig("boost").shift.speed.by(10)      # Stacks (.by)
rig("boost").shift.speed.to(20)      # Replaces (.to)

# ============================================================================
# MAX CONSTRAINTS
# ============================================================================

# PRD 5 (not available)

# PRD 6
rig("boost").shift.speed.by(10).max.speed(50)
rig("boost").shift.speed.by(10).max.stack(3)

# ============================================================================
# STATE ACCESS
# ============================================================================

# PRD 5 & PRD 6 (same)
rig.state.speed      # Computed
rig.base.speed       # Base only
rig.bake()           # Flatten
```

---

**END OF MIGRATION PLAN**

*This document should be reviewed and approved before implementation begins.*
