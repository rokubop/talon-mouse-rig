# Property Chaining Implementation

## Summary

Implemented property chaining functionality that allows setting multiple properties in a single fluent statement:

```python
rig.speed(10).accel(2).direction(1, 0)
rig.speed(5).accel(3).direction(1, 1).pos.to(500, 500)
```

## Key Rule

**Timing and chaining are mutually exclusive** - you cannot use timing methods (`.over()`, `.hold()`, `.revert()`, `.rate()`, `.wait()`) when chaining properties.

### ✅ Valid Patterns

```python
# Chaining without timing (all execute immediately)
rig.speed(4).accel(3)
rig.speed(5).accel(2).direction(1, 0)

# Timing without chaining (separate statements)
rig.speed(4).over(100)
rig.accel(3).over(200)

# Relative changes while chaining
rig.speed.by(5).accel.by(2).direction.by(45)
```

### ❌ Invalid Patterns

```python
# Timing before chain
rig.speed(4).over(100).accel(3)
# Error: Cannot chain .accel after using timing methods (.over, .in_out, .hold, .revert).
#
# Use separate statements:
#   rig.speed(...).over(...)
#   rig.accel(...)

# Timing after chain
rig.speed(4).accel(3).over(100)
# Error: Cannot chain .over after using timing methods (.over, .in_out, .hold, .revert).
#
# Use separate statements:
#   rig.speed(...).over(...)
#   rig.accel(...)
```

## Implementation Details

### Modified Classes

All builder classes now enable property chaining via `__getattr__`:

1. **PropertyEffectBuilder** - handles `speed.to()`, `speed.by()`, `accel.to()`, `accel.by()`
2. **DirectionBuilder** - handles `direction(x, y)`
3. **DirectionByBuilder** - handles `direction.by(degrees)`
4. **PositionToBuilder** - handles `pos.to(x, y)`
5. **PositionByBuilder** - handles `pos.by(dx, dy)`

### Chaining Logic

Each builder's `__getattr__` method:

1. **Checks for timing configuration** - looks for any timing-related flags:
   - `_duration_ms`, `_in_duration_ms`, `_hold_duration_ms`, `_out_duration_ms`
   - `_use_rate`, `_wait_duration_ms`

2. **Raises helpful error if timing found**:
   ```
   Cannot chain .{property} after using timing methods (.over, .hold, .revert).
   
   Use separate statements:
     rig.speed(...).over(...)
     rig.accel(...)
   ```

3. **Executes immediately if no timing** - calls `_execute()` or `__del__()`

4. **Returns appropriate controller** for the chained property:
   - `speed` → `SpeedController`
   - `accel` → `AccelController`
   - `pos` → `PositionController`
   - `direction` → `DirectionController`

### Error Message Format

All error messages explicitly list:
- The timing methods that are incompatible: `.over, .rate, .wait, .hold, .revert`
- The chainable properties: `speed`, `accel`, `pos`, `direction`
- Example of correct usage with separate statements

## Examples Added

Added comprehensive examples in `examples.py`:

- `mouse_rig_chain_basic()` - basic speed + accel + direction chain
- `mouse_rig_chain_all_properties()` - all four properties in one chain
- `mouse_rig_chain_with_modifiers()` - using `.by()` while chaining
- `mouse_rig_no_timing_in_chains()` - documentation of invalid patterns

## Testing

Created `test_chaining.py` with test cases for:
- Basic chaining (should work)
- Timing before chain (should fail with clear error)
- Timing after chain (should fail with clear error)
- Direction timing + chain (should fail)
- Position timing + chain (should fail)
- Separate statements (should work)

## Benefits

1. **Cleaner initialization code**:
   ```python
   # Before
   rig.direction(1, 0)
   rig.speed(10)
   rig.accel(2)
   
   # After
   rig.direction(1, 0).speed(10).accel(2)
   ```

2. **Clear error messages** - users immediately understand why timing + chaining doesn't work

3. **Type safety maintained** - proper controller types returned for each property

4. **No ambiguity** - simple rule: "no timing when chaining"
