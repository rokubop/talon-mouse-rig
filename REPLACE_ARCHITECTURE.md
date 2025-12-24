# Replace Behavior Architecture

## Core Concepts

### Committed vs Accumulated State

**Committed State** (pos.offset only):
- Represents physical mouse movement that has **already happened**
- Cannot be undone - it's "baked into reality"
- Only applies to `pos` property (the only property with observable physical state)
- Accumulates across replaced builders

**Accumulated State** (all properties):
- Represents the **current animation value** from active builders
- Can be reset, replaced, or modified
- Gets clamped when replace_target is set

### Property Types

**Committed Property:** `pos`
- Changes are physical transactions that execute and complete
- Need to track total committed movement separately
- Example: Moving mouse 5px is observable and irreversible

**Stateful Properties:** `speed`, `direction`, `vector`
- Changes are value updates with no physical side effects
- Current value = base + accumulated modifiers
- No committed tracking needed

## Data Ownership

### LayerGroup Owns:
- `committed_value` - Total baked physical movement (Vec2(0,0) for pos, None for others)
  - Only updated when: replace bakes existing progress, or replace builder completes
  - Never changes during builder animation
- `accumulated_value` - Current sum from completed builders (unclamped)
  - Updated when: builder completes via `on_builder_complete()`
  - Never modified during builder animation (builders contribute via `get_current_value()`)
- `final_target` - What accumulated will be when all builders complete (cached)
- `replace_target` - Absolute user target for replace operations
  - Set when: replace behavior triggers
  - Used by: `get_current_value()` to clamp output
  - Cleared when: replace builder completes (see Challenge 5)
  - **Purpose:** Preserves natural animation timing while clamping physical output
  - Only applies to: `pos.offset` with replace behavior

### Builder Owns:
- `base_value` - Where this builder starts animating from (always 0 for fresh builders)
- `target_value` - Where this builder ends (its own animation target, e.g., 10)
- `config.value` - User's input value (e.g., 10 from `.add(10, 0)`)
- Builder animates independently: 0 → target_value
- **Builder is unaware of:**
  - committed_value
  - replace_target clamping
  - LayerGroup's accumulated_value

## Replace Behavior Flow

### Example: Builder 1 at 50% when Builder 2 replaces

**Initial State (B1 at 500ms of 1000ms):**
```
committed_value = (0, 0)
accumulated_value = (5, 0)  # B1 halfway through 0→10
Physical position = (5, 0)
```

**Replace Triggers (B2: add(10, 0).over(1000)):**
1. **Bake B1's progress:**
   - `committed_value += accumulated_value`  → (5, 0)
   - `accumulated_value = (0, 0)`  (reset)
   - Remove B1 from builders

2. **Setup B2:**
   - `replace_target = (10, 0)`  (user's absolute target)
   - B2 animates: (0, 0) → (10, 0) internally over 1000ms
   - LayerGroup will clamp output

**During B2 Animation:**
```python
def get_current_value(self):
    total = committed_value + accumulated_value
    
    if replace_target is not None:
        # Dynamic clamping based on approach direction
        if committed_value < replace_target:
            total = min(total, replace_target)  # upper clamp
        elif committed_value > replace_target:
            total = max(total, replace_target)  # lower clamp
    
    return total
```

**Timeline:**
- 0ms: physical = (5, 0) + (0, 0) = (5, 0)
- 500ms: physical = (5, 0) + (5, 0) = **(10, 0)** ← clamped! B2 internally at (5, 0)
- 1000ms: B2 internally at (10, 0), but accumulated clamped at (5, 0)

**Final State:**
- committed_value = (5, 0)
- accumulated_value = (5, 0) (clamped during animation)
- B2's internal value = (10, 0) (unclamped)
- Physical = (10, 0) ✓

## Replace with Revert

### Example: B1 at 50%, then B2 replaces with revert

**B2 Over Phase (0-1000ms):**
- Same as above, reaches physical (10, 0)
- B2 internal: (10, 0)
- accumulated: (5, 0) (clamped)

**B2 Revert Phase (1000-2000ms):**
- B2 reverts based on **its own internal target (10, 0)**
- Animates internally: (10, 0) → (0, 0)
- This drives accumulated: (5, 0) → (-5, 0)
- Physical = committed + accumulated = (5, 0) + (-5, 0) = **(0, 0)** ✓

**Key Insight:**
- Builder tracks its own animation state independently
- LayerGroup clamps what actually gets applied
- Revert uses builder's internal value, no special logic needed
- The negative accumulated cancels out the committed value

## Non-pos Properties (speed, direction, vector)

For properties without physical state:
- `committed_value` = None or unused
- Replace simply snapshots accumulated_value and resets it
- No clamping needed - just direct value replacement
- Revert works normally since there's no committed offset

## Key Invariants

1. **Physical = committed + clamped(accumulated + active_builders)**
2. **Builder animates independently, unaware of clamping**
3. **Committed only accumulates for pos.offset** (all other properties use None)
4. **Replace always clears existing builders** (only one builder animates)
5. **Replace clamps dynamically** based on committed vs target relationship
6. **Revert uses builder's internal state**, letting negative accumulated cancel committed
7. **accumulated_value never changes during animation** (only on completion via `on_builder_complete()`)
8. **replace_target must be cleared** when builder completes (with consolidation to committed)

## Implementation Challenges

### Challenge 1: accumulated_value Dual Role
**Current behavior:**
- `accumulated_value` is both:
  - Sum of completed builders (persistent state)
  - Combined with active builders via `get_current_value()`

**During animation:**
```python
# get_current_value() combines accumulated + active builders
def get_current_value(self):
    result = self.accumulated_value  # Start with completed builders
    for builder in self.builders:
        result = self._apply_mode(result, builder.get_interpolated_value(), mode)
    return result
```

**Challenge:**
- With clamping, `get_current_value()` returns clamped output
- But `accumulated_value` itself never changes during animation
- Only updates when `on_builder_complete()` is called
- **Solution:** Clamping must happen in `get_current_value()` without affecting `accumulated_value`

### Challenge 2: Builder Independence
**Current behavior:**
- Builders call `builder.get_interpolated_value()` to get their current animated value
- This is **independent** of the group's accumulated_value
- Group combines them: `accumulated + builder1 + builder2 + ...`

**For replace with clamping:**
- Builder animates: 0 → 10 internally (unclamped)
- But group clamps the **total**: `committed(5) + accumulated(0) + builder(5) = 10 max`
- **The builder never knows it's being clamped**
- When builder completes at target=10, accumulated gets incremented by 10
- But the **effective accumulated** should only be 5 (because of clamping)

**Solution:**
- Option A: Track "virtual accumulated" that can exceed replace_target, but clamp on output
- Option B: When builder completes, don't just add target_value, but add `min(target_value, remaining_space)`

### Challenge 3: Multiple Active Builders ✓ NON-ISSUE
**Potential scenario:**
```python
# B1 and B2 both active, both contributing to accumulated
committed = 5
accumulated = 0
B1: animating 0 → 10 (currently at 3)
B2: animating 0 → 10 (currently at 2)
replace_target = 10

Total = 5 + 3 + 2 = 10 ✓ (at limit)
```

**Why this doesn't happen:**
- **Replace behavior ALWAYS clears all existing builders** before adding new one
- Only ONE builder ever animates during a replace operation
- No need to handle multiple builder interactions with clamping

**Code reference:**
```python
def _apply_replace_behavior(self, builder, group):
    # ... bake progress to committed ...
    group.clear_builders()  # ← Removes all existing builders
    # Then the new builder gets added
```

### Challenge 4: Baking on Completion
**Current behavior:**
```python
def on_builder_complete(self, builder):
    value = builder.get_interpolated_value()  # Builder's final value (10)
    self.accumulated_value = self._apply_mode(self.accumulated_value, value, mode)
```

**For replace:**
- Builder internal value: 10
- But it was clamped during animation
- Should accumulated become:
  - `0 + 10 = 10`? (builder's full value)
  - `0 + 5 = 5`? (clamped contribution)

**Answer from architecture:**
- Let accumulated become 10 (builder's internal value)
- But clamp in `get_current_value()`: `min(committed + accumulated, replace_target)`
- So: committed(5) + accumulated(10) = 15, clamped to 10 ✓

**Challenge:** 
- After builder completes, replace_target should be cleared
- Then accumulated(10) + committed(5) = 15 (wrong!)
- **We need to transfer accumulated to committed when replace completes**

### Challenge 5: When to Clear replace_target ⚠️ CRITICAL
**Lifecycle:**
1. Replace triggers: bake to committed, set replace_target
2. Builder animates: clamped by replace_target
3. Builder completes: bakes to accumulated (accumulated = 10)
4. **Now what?** Without cleanup: committed(5) + accumulated(10) = 15 ❌

**Problem:**
- Builder completes with internal value = 10
- Gets added to accumulated_value = 10
- But physical was clamped: should be 10 total, not 15

**Solution:**
When replace builder completes in `on_builder_complete()`:
```python
# After normal baking: accumulated_value = 10, committed_value = 5
if self.replace_target is not None:
    # Consolidate everything into committed
    total = self.committed_value + self.accumulated_value
    
    # Apply the clamp based on direction
    if self.committed_value < self.replace_target:
        self.committed_value = min(total, self.replace_target)
    elif self.committed_value > self.replace_target:
        self.committed_value = max(total, self.replace_target)
    else:
        self.committed_value = self.replace_target
    
    # Reset for next operation
    self.accumulated_value = self._zero_value()
    self.replace_target = None
```

This ensures:
- Final state: committed = 10, accumulated = 0 ✓
- Next operation starts from clean state
- Revert of the layer will revert the full committed value (10)

### Challenge 6: Non-pos Properties
**Good news:** 
- speed/direction/vector never have committed_value
- They don't need clamping logic
- Replace just snapshots and resets accumulated_value (current behavior)
- No changes needed for non-pos properties

**Decision:**
- Only implement committed_value and replace_target for `property == "pos"`
- Keep existing replace behavior for other properties
