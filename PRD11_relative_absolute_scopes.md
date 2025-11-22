# PRD11: Relative/Absolute Scope Disambiguation

## Problem
is_named_layer operations with `.to()`, `.mul()`, and `.div()` are ambiguous:
- `rig.layer("boost").speed.mul(2)` - unclear what this multiplies
- `rig.layer("boost").speed.to(10)` - unclear what this means
- Currently these are disabled for layers

## Solution
Introduce `.relative` and `.absolute` scopes to disambiguate operations.

## Scope Semantics

### `.relative` - layer's Own Contribution
Operates on the layer's accumulated value:

```python
# Base speed = 10
rig.layer("boost").speed.add(5)      # boost = +5, total = 15
rig.layer("boost").speed.add(3)      # boost = +8, total = 18

rig.layer("boost").relative.speed.mul(2)
# boost's +8 becomes +16
# Total: 10 + 16 = 26

rig.layer("boost").relative.speed.to(20)
# boost's contribution becomes 20 (absolute contribution, not delta)
# Total: 10 + 20 = 30
```

### `.absolute` on layers - Modify Base Value
layer modifies the base value (stored as delta):

```python
# Base speed = 10
rig.layer("boost").absolute.speed.mul(2)
# boost contributes: (base * 2) - base = +10
# Total: 10 + 10 = 20

rig.layer("boost").absolute.speed.to(20)
# boost contributes: 20 - base = +10
# Total: 10 + 10 = 20
```

Multiple `.absolute` operations from different layers compose:
```python
# Base speed = 10
rig.layer("a").absolute.speed.mul(2)    # 10 * 2 = 20
rig.layer("b").absolute.speed.mul(3)    # 20 * 3 = 60
rig.layer("c").absolute.speed.to(100)   # overrides to 100 (last .to() wins)
# Final base after .absolute ops: 100
```

### `rig.absolute` - Final Override (Temporal or Permanent)

Behavior depends on whether `.revert()` is specified:

**WITH revert - Temporal override (no baking):**
```python
# Base speed = 10
rig.layer("boost").speed.add(5)      # +5
rig.layer("sprint").speed.add(10)    # +10
# Current: 10 + 5 + 10 = 25

rig.absolute.speed.to(100).over(1000).revert(1000)
# Over: ramps from current (25) → 100 over 1000ms
# Hold: stays at 100
# Revert: ramps from 100 → 25 over 1000ms
# After revert: back to 25 (base + effects still active)
# No baking, no clearing - temporary override

rig.absolute.speed.mul(2).over(500).hold(2000).revert(500)
# Temporarily multiplies current value by 2, then reverts
# Effects preserved throughout
```

**WITHOUT revert - Permanent baking:**
```python
# Base speed = 10
rig.layer("boost").speed.add(5)      # boost contributes +5 (relative)
rig.layer("sprint").speed.add(10)    # sprint contributes +10 (relative)
# Current computed: base(10) + boost(+5) + sprint(+10) = 25

rig.absolute.speed.to(100)
# 1. Computes current value (25)
# 2. Removes all speed-related builders (boost, sprint, and this absolute builder itself)
# 3. Sets base to 100
# Result: base = 100 (clean slate)
# Can now add new effects/layers on top of 100

# After baking, can continue:
rig.layer("new_boost").speed.add(5)  # base(100) + 5 = 105

rig.absolute.speed.mul(2)
# 1. Computes current value (25)
# 2. Multiplies: 25 * 2 = 50
# 3. Removes all speed-related builders (including itself)
# 4. Sets base to 50
# Result: base = 50 (permanent)
```

Multiple `rig.absolute` calls - last wins (for permanent):
```python
rig.absolute.speed.to(100)   # Sets to 100
rig.absolute.speed.mul(2)    # Sets to 100 * 2 = 200 (wins)
# Result: 200
```

Per-property (only affects specified property):
```python
rig.absolute.speed.to(100)              # Only bakes/clears speed
rig.layer("drift").direction.add(0.1, 0)  # Direction effects still active
```

## Rules

### Scope Applies to layers Only
The `.relative` / `.absolute` distinction only applies to **is_named_layer builders**:

```python
# Anonymous (base rig) - operates directly on base, no scope needed
rig.speed.to(10)      # Sets base to 10
rig.speed.mul(2)      # Multiplies base by 2
rig.speed.add(5)      # Adds to base

# layers - must specify scope for ambiguous operations
rig.layer("boost").relative.speed.to(10)   # layer's contribution is 10
rig.layer("boost").absolute.speed.to(10)   # Base becomes 10 (via layer)

# rig.absolute - global override/baking operation
rig.absolute.speed.to(100)  # Special case: collapses everything
```

**Why the distinction?**
- **Anonymous builders ARE the base** - they directly modify base values, no ambiguity
- **layers modify FROM a reference** - they need to specify: modify my own value (.relative) or modify base (.absolute)?
- **`rig.absolute`** - special global operation that sits at end of chain

### Ambiguous Operations (require scope for layers)
layers MUST use `.relative` or `.absolute` for these operations:
- `.to()` - MUST have scope
- `.mul()` - MUST have scope
- `.div()` - MUST have scope

```python
# ✗ Error - ambiguous operations without scope
rig.layer("boost").speed.to(10)    # Error: requires .relative or .absolute
rig.layer("boost").speed.mul(2)    # Error: requires .relative or .absolute
rig.layer("boost").speed.div(2)    # Error: requires .relative or .absolute

# ✓ Correct - explicit scope
rig.layer("boost").relative.speed.to(10)   # OK
rig.layer("boost").absolute.speed.mul(2)   # OK
rig.layer("boost").relative.speed.div(2)   # OK
```

### Unambiguous Operations (default to relative)
- `.add()` - defaults to relative (layer's delta), can use `.absolute.add()` to add to base
- `.sub()` - defaults to relative (layer's delta), can use `.absolute.sub()` to subtract from base
- `.by()` - alias for `.add()`, defaults to relative

```python
rig.layer("boost").speed.add(5)              # Relative (implicit)
rig.layer("boost").relative.speed.add(5)     # Relative (explicit)
rig.layer("boost").absolute.speed.add(5)     # Add to base instead
```

### Scope Locking (no mixing)
Once a layer uses a scope (relative or absolute), it's locked to that scope:

```python
# ✓ Allowed - all relative
rig.layer("boost").speed.add(10)              # Starts in relative mode
rig.layer("boost").speed.mul(2)               # Stays relative (implicit)
rig.layer("boost").relative.speed.div(3)      # Still relative (explicit)

# ✓ Allowed - all absolute
rig.layer("slow").absolute.speed.div(2)       # Starts in absolute mode
rig.layer("slow").absolute.speed.mul(0.8)     # Stays absolute

# ✗ Error - mixing scopes
rig.layer("boost").speed.add(10)              # Relative (implicit)
rig.layer("boost").absolute.speed.mul(2)      # Error: can't mix scopes on same layer

# ✗ Error - mixing scopes
rig.layer("slow").absolute.speed.div(2)       # Absolute (explicit)
rig.layer("slow").speed.add(5)                # Error: layer is in absolute mode
```

### Anonymous (base rig)
Anonymous builders don't need scope (unambiguous):
```python
rig.speed.to(10)   # ✓ Sets base to 10
rig.speed.mul(2)   # ✓ Multiplies base by 2
rig.speed.div(2)   # ✓ Divides base by 2
```

Optional: allow `rig.absolute` for consistency:
```python
rig.absolute.speed.to(10)   # Same as rig.speed.to(10)
```

## Implementation Notes

### Builder Changes
1. Add `.relative` and `.absolute` properties to `RigBuilder`
2. These return a `ScopeProxy` that exposes property accessors
3. `PropertyBuilder` needs to know the scope to validate operations
4. `BuilderConfig` needs a `scope` field: `None | "relative" | "absolute"`

### Scope Tracking
- Track scope per layer name (not per builder instance)
- First scoped operation on a layer locks it to that mode
- Unscoped operations (`.add()`, `.sub()`) default to relative
- Mixing scopes on same layer name → error

Example state structure:
```python
{
  "layer_scopes": {
    "boost": "relative",
    "slow": "absolute",
  },
  "relative_effects": {
    "boost": [ActiveBuilder(...), ActiveBuilder(...)],
  },
  "absolute_effects": {
    "slow": [ActiveBuilder(...)],
  }
}
```

### Validation
- layers using `.to()`, `.mul()`, `.div()` without scope → error with helpful message
- layers mixing scopes → error: "layer 'boost' is in relative mode, cannot use absolute"
- Anonymous builders using `.relative` or `.absolute` → allowed but optional
- State reading (`rig.state`) → no scope needed, different context

### Computation Order
1. Start with base value
2. Apply all layer `.absolute` operations (in stack order, last `.to()` wins)
3. Add all layer `.relative` contributions and deltas
4. Apply `rig.absolute` operations (if temporal - with revert)

**Execution flow:**
- `rig.absolute` **with revert**: Acts as temporary override layer (after all layers)
- `rig.absolute` **without revert**: Immediately bakes, clears all builders for that property (including itself), sets new base, then is removed from active builders

**Chain visualization:**
```
Normal: base → layer.absolute → layer.relative → rig.absolute (temporal)
Baking: base → [rig.absolute executes, bakes to base, removes self and all property builders] → new base
```

### Revert Semantics
- **Relative effects**: Revert removes the layer's contribution (back to 0 delta)
- **Absolute effects**: Revert restores base to original value before modification
- **`rig.absolute` with revert**: Temporary override, preserves all effects
- **`rig.absolute` without revert**: Immediately bakes to base, clears ALL builders for that property (layers + itself), allows fresh start

### Baking Behavior
When `rig.absolute` executes without revert:
1. It's a one-time operation, not an ongoing effect
2. Computes current value from all sources
3. Removes ALL active builders for that property (layers and the absolute builder itself)
4. Sets base to final computed value
5. System is now clean - can add new layers/effects on top of new base

This ensures `rig.absolute` is truly a "reset point" - not a persistent layer.

## Examples

### Basic Usage
```python
# Boost effect with relative scaling
rig.layer("boost").speed.add(10)
rig.layer("boost").relative.speed.mul(2)  # Double the boost

# Override base speed via layer
rig.layer("slow").absolute.speed.div(2)  # Half the base speed

# Final override (collapse everything)
rig.absolute.speed.to(100)  # Force speed to 100
```

### Complex Scenario
```python
# Base speed = 10
rig.layer("boost").speed.add(5).over(1000)       # +5 over time
rig.layer("sprint").absolute.speed.mul(1.5)      # base becomes 15
# Current: 15 + 5 = 20

rig.layer("boost").relative.speed.mul(2)         # boost's +5 becomes +10
# Current: 15 + 10 = 25

rig.absolute.speed.to(100)                     # Collapse, bake, reset
# All speed-related builders removed (boost, sprint), base = 100
```

## Contract Changes

### BuilderConfig
Add scope field:
```python
class BuilderConfig:
    scope: Optional[Literal["relative", "absolute"]] = None
    # ... existing fields
```

### VALID_OPERATORS
Update to reflect scope requirements:
```python
VALID_OPERATORS = {
    'speed': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'direction': ['to', 'add', 'by', 'sub', 'mul', 'div', 'bake'],
    'pos': ['to', 'add', 'by', 'sub', 'bake']
}

# Operators that require scope for is_named_layer builders
SCOPE_REQUIRED_OPERATORS = ['to', 'mul', 'div']

# Operators that default to relative
RELATIVE_DEFAULT_OPERATORS = ['add', 'sub', 'by']
```

### VALID_RIG_PROPERTIES
Add scope accessors:
```python
VALID_RIG_PROPERTIES = [
    'pos', 'speed', 'direction',
    'state', 'base',
    'relative', 'absolute',  # New scope accessors
    'stack', 'replace', 'queue', 'extend', 'throttle', 'ignore',
]
```

### Error Messages
Add new validation errors:
```python
# When layer uses ambiguous operator without scope
"layer operations with .{operator}() require explicit scope. Use:\n"
"  rig.layer('{layer}').relative.{property}.{operator}({value})  # Operate on layer's contribution\n"
"  rig.layer('{layer}').absolute.{property}.{operator}({value})  # Operate on base value"

# When layer mixes scopes
"layer '{layer}' is in {current_scope} mode, cannot use {attempted_scope}.\n"
"All operations on a layer must use the same scope."
```

## Migration
- Keep existing `.add()`, `.sub()`, `.by()` working as-is (default to relative for layers)
- Re-enable `.to()`, `.mul()`, `.div()` but require explicit scope for layers
- Add helpful error messages pointing to `.relative` or `.absolute`
- Anonymous builders continue to work without scope changes
