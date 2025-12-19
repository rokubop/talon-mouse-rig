# Max/Min Constraints Implementation

## Changes Made

### 1. Core Configuration ([contracts.py](src/contracts.py))
- Added `max_value` and `min_value` fields to `BuilderConfig` class

### 2. Builder API ([builder.py](src/builder.py))
Added chainable constraint methods:
- `.max(value)` - Set maximum constraint on operation result
- `.min(value)` - Set minimum constraint on operation result

Operations no longer accept inline `max`/`min` parameters:
- `to(*args)` - no max/min params
- `add(*args)` - no max/min params
- `by(*args)` - no max/min params
- `sub(*args)` - no max/min params
- `mul(value)` - no max/min params
- `div(value)` - no max/min params

### 3. Constraint Application ([state.py](src/state.py))

Added `apply_constraints()` utility function that:
- Handles both scalar values (speed, direction) and Vec2 tuples (pos, vector)
- Supports scalar constraints (single value) or tuple constraints `(x, y)`
- Clamps contributions to prevent cumulative value from exceeding limits

Constraint application occurs in TWO places:

#### A. Frame Loop (`_apply_layer()`)
For animated operations with `.over()`, constraints are applied during each frame tick before mode operations.

#### B. Instant Operations
- **Synchronous position** (`execute_synchronous()`): Applied before mouse_move
- **Non-synchronous** (`_bake_builder()`): Applied during baking to base state

### 4. Constraint Semantics

- **Mode-aware**: Only applies to "offset" mode (additive operations)
  - Ignored for "override" mode (absolute values)
  - Ignored for "scale" mode (multipliers)

- **Per-builder evaluation**: Each builder checks its own constraints

- **Cumulative checking**: Constraints evaluated against accumulated value from all previous layers

## Usage Examples

```python
# Scalar constraint - cap result at 150
rig.speed.add(100).max(150)

# Tuple constraint for Vec2 - clamp x and y separately
rig.pos.by(200, 150).max((1000, 800))

# Min constraint - floor result at 20
rig.speed.sub(80).min(20)

# Chaining is flexible - constraints can be anywhere in the chain
rig.speed.add(10).max(15).over(500)
rig.speed.mul(2).over(300).max(20)

# Layered constraints - each layer respects cumulative limit
rig.speed.to(10)
rig.layer("boost1").speed.add(50).max(100)  # 10 + 50 = 60
rig.layer("boost2").speed.add(60).max(100)  # 60 + 60 = 120 -> capped at 100

# Vector constraints with tuple bounds
rig.vector.add(50, 50).max((30, 30))  # Clamps each component

# Both min and max
rig.speed.add(-10).min(1).max(20)
```

## Test Coverage

18 new tests added across all property types:
- **speed.py** (5 tests): Scalar constraints with add/sub/mul and layers
- **position.py** (4 tests): Vec2 tuple/scalar constraints, layered positions
- **vector.py** (3 tests): Velocity vector constraints
- **direction.py** (2 tests): Direction vector constraints
- **behaviors.py** (2 tests): Constraints with stack/queue behaviors
- **validation.py** (3 tests): Edge cases and type mixing

## Implementation Notes

1. **Circular import handling**: The `execute_synchronous()` method imports `apply_constraints` locally to avoid circular dependencies

2. **Position special cases**:
   - For `pos.by()` with absolute tracking (after `pos.to()`), constraints are checked against screen coordinates
   - For pure relative movement, constraints are checked against current mouse position

3. **Type flexibility**: Constraints can be:
   - Scalar for any property (applied to both x/y for Vec2)
   - Tuple `(x, y)` for Vec2 properties

4. **Performance**: Constraint checks only occur when max/min are explicitly provided, no overhead otherwise
