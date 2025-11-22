# PRD12 Implementation Summary

## Overview
Successfully implemented PRD12: Local/World Scope System with Incoming/Outgoing phases for the mouse rig.

## Key Changes

### 1. Scope System: `relative/absolute` → `local/world`
- **`local`** - The tag's own contribution/work (default for tags)
- **`world`** - Operations on the accumulated global value (after all local tags)

**API Changes:**
```python
# Before (PRD11):
rig.tag("boost").relative.speed.add(5)
rig.tag("boost").absolute.speed.to(10)

# After (PRD12):
rig.tag("boost").local.speed.add(5)
rig.tag("boost").world.speed.to(10)
```

### 2. Phase System: `incoming/outgoing` for `mul` Operations
- **`incoming`** - Pre-process: multiply the input **before** the tag's local work
- **`outgoing`** - Post-process: multiply the output **after** the tag's local work
- **`mul` on tags MUST use `incoming` or `outgoing`** (not standalone)

**API Changes:**
```python
# Before (PRD11):
rig.tag("boost").relative.speed.mul(2)  # Required explicit scope

# After (PRD12):
rig.tag("boost").local.incoming.speed.mul(2)   # Pre-multiply
rig.tag("boost").local.outgoing.speed.mul(1.5) # Post-multiply
```

### 3. No More Operation Mode Locking
**The biggest win!** Tags can now freely mix additive and multiplicative operations.

```python
# This was IMPOSSIBLE in PRD11:
rig.tag("complex").local.incoming.speed.mul(2)   # Multiply input
rig.tag("complex").local.speed.add(5)            # Add value
rig.tag("complex").local.speed.add(3)            # Add more
rig.tag("complex").local.outgoing.speed.mul(1.5) # Multiply output

# Processing: input → *2 → +5 → +3 → *1.5 → output
```

### 4. New `scale()` Operation
Retroactive multiplier applied to accumulated values. Last scale wins; tag scales override rig scales.

```python
rig.tag("boost").speed.add(5)
rig.tag("boost").speed.add(3)           # Total: +8
rig.tag("boost").speed.scale(2)         # Scale to +16

rig.world.speed.scale(2)                # 2x
rig.tag("override").world.speed.scale(3) # Tag wins: 3x
```

### 5. Explicit Tag Ordering
Tags can now have explicit order parameter for predictable execution sequence.

```python
rig.tag("first", order=1).local.speed.add(5)
rig.tag("second", order=2).local.speed.add(3)

# Subsequent operations on same tag append in original order
rig.tag("first").local.speed.add(2)  # Appends to "first", keeps order=1
```

### 6. Per-Property Scopes
Different properties on the same tag can have different scopes.

```python
rig.tag("gravity").local.direction.add(0, 1)   # Local directional influence
rig.tag("gravity").local.speed.to(9.8)         # Local speed
rig.tag("gravity").world.pos.to(0, 500)        # World position
```

## Computation Chain

```
Base Rig
  ↓
Local Tags (by order)
  For each tag:
    incoming → local operations → scale → outgoing
  ↓
World Operations
```

**Detailed Example:**
```python
# Base
rig.speed(10)                                              # base = 10

# Local Tag 1 (order=1)
rig.tag("boost", order=1).local.incoming.speed.mul(2)      # 10 * 2 = 20
rig.tag("boost").local.speed.add(5)                        # 20 + 5 = 25
rig.tag("boost").local.speed.add(3)                        # 25 + 3 = 28
rig.tag("boost").local.outgoing.speed.mul(1.5)             # 28 * 1.5 = 42

# Local Tag 2 (order=2)
rig.tag("sprint", order=2).local.incoming.speed.mul(0.5)   # 42 * 0.5 = 21
rig.tag("sprint").local.speed.add(10)                      # 21 + 10 = 31

# World operations
rig.world.speed.add(5)                                     # 31 + 5 = 36
rig.world.speed.scale(2)                                   # 36 * 2 = 72

# Final speed = 72
```

## Files Modified

### Core Implementation
1. **`src/contracts.py`**
   - Updated `VALID_SCOPES` to `['local', 'world']`
   - Added `VALID_PHASES` for `['incoming', 'outgoing']`
   - Updated `BuilderConfig` with `scope`, `phase`, and `order` fields
   - Added `validate_phase_requirement()` for mul operations
   - Removed operation mode validation

2. **`src/builder.py`**
   - Renamed `ScopeProxy` to use `local`/`world` instead of `relative`/`absolute`
   - Added `PhaseProxy` class for `incoming`/`outgoing` accessors
   - Updated `RigBuilder` with `local` and `world` properties
   - Added `order` parameter to `__init__`
   - Updated `PropertyBuilder` to support phase and remove scope requirement for mul
   - Added `scale()` method to `PropertyBuilder`

3. **`src/state.py`**
   - Removed `_tag_operation_categories` and operation mode locking
   - Added `_tag_property_scopes` for per-property scope tracking
   - Added `_tag_orders` for explicit tag ordering
   - Rewrote `_compute_current_state()` for PRD12 computation model
   - Added `_apply_local_builder()` and `_apply_world_builder()` methods
   - Updated validation to be per-property

4. **`src/__init__.py`**
   - Added `order` parameter to `Rig.tag()` method
   - Added `local` and `world` properties to `Rig` class
   - Updated `VALID_RIG_PROPERTIES` in contracts

## Smart Defaults

The implementation uses smart defaults to minimize verbosity:

1. **Tagged builders default to `local` scope** for add/sub/by/to operations
   ```python
   rig.tag("boost").speed.add(5)  # Defaults to local
   ```

2. **Anonymous builders don't require scope**
   ```python
   rig.speed.add(5)  # No scope needed
   ```

3. **`mul` defaults to local scope** (but requires phase)
   ```python
   # Only need to specify incoming/outgoing, scope inferred
   rig.tag("x").local.incoming.speed.mul(2)
   ```

4. **Tags without explicit order execute in creation order**
   ```python
   rig.tag("first").speed.add(5)   # order inferred
   rig.tag("second").speed.add(3)  # order inferred
   ```

## Generic Code Patterns

The implementation uses common generic patterns:

1. **Unified builder system** - Single `RigBuilder` class for all operations
2. **Proxy pattern** - `ScopeProxy` and `PhaseProxy` for fluent API
3. **Config-based validation** - Centralized validation in `BuilderConfig`
4. **Per-property tracking** - Generic `(tag, property)` tuple keys
5. **Phase-based processing** - Generic incoming/local/scale/outgoing chain

## Migration Guide

See `PRD12_examples.py` for comprehensive examples of the new API.

### Quick Reference

| PRD11 (Old) | PRD12 (New) |
|-------------|-------------|
| `.relative` | `.local` |
| `.absolute` | `.world` |
| `.relative.speed.mul(2)` | `.local.incoming.speed.mul(2)` or `.local.outgoing.speed.mul(2)` |
| Tags locked to mul OR add | Tags can freely mix operations |
| No explicit ordering | `tag("name", order=1)` |
| No scale operation | `.scale(2)` for retroactive multiplier |

## Testing

Examples file created: `PRD12_examples.py`

Contains examples for:
- Basic local/world usage
- Incoming/outgoing phases
- Mixed operations (the new capability!)
- Scale operations
- Tag ordering
- Complex multi-tag scenarios
- Migration from PRD11
