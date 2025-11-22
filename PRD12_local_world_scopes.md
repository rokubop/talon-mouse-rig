# PRD12: Local/World Scope System with Incoming/Outgoing

## Overview
A clear scope system that uses `local`/`world` to define processing context, with `incoming`/`outgoing` to position `mul` operations explicitly in the processing chain.

## Core Concepts

### 1. Scopes
Defines **where** an operation is applied:

- **`local`** - The tag's own contribution/work (default for tags)
- **`world`** - Operations on the accumulated global value (after all local tags)

### 2. Incoming/Outgoing (For Mul Only)
Defines **when** a `mul` operation happens relative to the tag's work:

- **`incoming`** - Pre-process: multiply the input **before** the tag's local work
- **`outgoing`** - Post-process: multiply the output **after** the tag's local work

### 3. Operation Rules
- **`mul`** operations **MUST** use `incoming` or `outgoing` on tags (never standalone)
- **`add`, `sub`, `by`, `to`** operations work directly in `local` scope (can stack freely)
- **No operation mode locking** - tags can freely mix additive and multiplicative operations
- Different properties on the same tag can have different scopes

## Computation Chain

```
Base Rig
  ↓
Local Tags (by order)
  For each tag:
    incoming → local operations → outgoing
  ↓
World Operations
```

**Detailed Example:**
```python
# Base
rig.speed(10)                                      # base = 10

# Local Tag 1 (order=1)
rig.tag("boost", order=1).local.incoming.speed.mul(2)   # 10 * 2 = 20
rig.tag("boost").local.speed.add(5)                     # 20 + 5 = 25
rig.tag("boost").local.speed.add(3)                     # 25 + 3 = 28
rig.tag("boost").local.outgoing.speed.mul(1.5)          # 28 * 1.5 = 42

# Local Tag 2 (order=2)
rig.tag("sprint", order=2).local.incoming.speed.mul(0.5) # 42 * 0.5 = 21
rig.tag("sprint").local.speed.add(10)                    # 21 + 10 = 31

# World operations
rig.world.speed.add(5)                            # 31 + 5 = 36
rig.world.speed.scale(2)                          # 36 * 2 = 72

# Final speed = 72
```

## API Examples

### Basic Local Tag Usage

```python
// Local scope (default for tags)
rig.tag("boost").local.speed.add(5)           # Additive operation
rig.tag("boost").speed.add(5)                 # Equivalent - defaults to local

rig.tag("boost").local.incoming.speed.mul(2)  # Multiply input before tag's work
rig.tag("boost").local.outgoing.speed.mul(1.5) # Multiply output after tag's work
```

### World Scope

```python
# World operations (after all local tags)
rig.world.speed.add(10)                       # Add to accumulated value
rig.world.speed.scale(2)                      # Scale final result
```

### Base Rig Operations

```python
rig.speed.add(10)                             # === rig.local.speed.add(10)
rig.speed.scale(2)                            # === rig.local.speed.scale(2)
```

### Complete Tag Example

```python
# A tag can mix operations freely
rig.tag("effect").local.incoming.speed.mul(2)   # Pre-multiply
rig.tag("effect").local.speed.add(5)            # Add
rig.tag("effect").local.speed.add(3)            # Add more (stacks)
rig.tag("effect").local.speed.sub(1)            # Subtract
rig.tag("effect").local.outgoing.speed.mul(1.5) # Post-multiply

# Processing: input → *2 → +5 → +3 → -1 → *1.5 → output
```

### Scale (Retroactive Multiplier)

```python
# Scale an additive tag
rig.tag("boost").local.speed.add(5)
rig.tag("boost").local.speed.add(3)               # Total: +8
rig.tag("boost").speed.scale(2).over(1000)        # Scale entire tag: +16

# Scale with incoming/outgoing
rig.tag("x").local.incoming.speed.mul(2)          # Pre: *2
rig.tag("x").local.speed.add(10)                  # Add: +10
rig.tag("x").speed.scale(3)                       # Scale the add: +30
rig.tag("x").local.outgoing.speed.mul(1.5)        # Post: *1.5
# Result: input → *2 → +30 → *1.5

# Scale world
rig.world.speed.scale(1.5)                        # Scale accumulated total

# Scale base
rig.speed.scale(2).over(1000)                     # Scale base speed

# Scale precedence: Last one wins (tag scales override rig scales)
rig.world.speed.scale(2)
rig.tag("override").world.speed.scale(3)          # Tag wins: 3x not 2x
```

### Tag Ordering

```python
# Explicit order
rig.tag("first", order=1).local.speed.add(5)
rig.tag("second", order=2).local.speed.add(3)

# Subsequent builders on same tag append in original order
rig.tag("first").local.speed.add(2)  # Appends to "first", keeps order=1
```

### Scope for Different Properties

```python
// Position
rig.tag("move").world.pos.to(500, 300)        # World coordinates
rig.tag("offset").local.pos.add(50, 0)        # Local offset

# Direction - mixing scopes on same tag, different properties
rig.tag("gravity").local.direction.add(0, 1)  # Local directional influence
rig.tag("gravity").local.speed.to(9.8)        # Local speed

# With incoming/outgoing
rig.tag("turn").local.incoming.direction.mul(0.5)  # Reduce input direction
rig.tag("turn").local.direction.add(1, 0)          # Add rightward influence
```

## Rules

### Scope Rules
1. Tags default to `local` scope if not specified
2. Scope can be `local` or `world`
3. Scope is tracked per property per tag (different properties can have different scopes)
4. First operation on a property sets the scope for that property
5. `rig.world.*` operations always use world scope
6. Base rig operations (`rig.speed.add(5)`) default to local scope

### Mul Operation Rules
1. **`mul` on tags MUST use `incoming` or `outgoing`** - never standalone
2. `incoming` multiplies the input before the tag's local work
3. `outgoing` multiplies the output after the tag's local work
4. Multiple `incoming` or `outgoing` muls on same property chain together
5. Exception: `rig.world.speed.mul(2)` allowed (no incoming/outgoing needed for world)

### Additive Operation Rules (add/sub/by/to)
1. Can be used directly in `local` scope without incoming/outgoing
2. Stack together in the order they're added
3. `to` operations overwrite previous values

### Scale Rules
1. `scale()` is a retroactive multiplier applied to the accumulated value
2. Can be used on any scope: local, world
3. Last scale wins (overrides previous scales)
4. Tag scales override rig scales
5. Syntax: `rig.tag("x").speed.scale(2)` (no scope prefix needed)

### Tag Ordering
1. Tags execute in ascending order (order=1, then order=2, etc.)
2. Subsequent operations on same tag append to that tag
3. Tags without explicit order execute in creation order

## Implementation Notes

### BuilderConfig Changes
```python
class BuilderConfig:
    scope: Optional[str] = None  # "local", "world"
    phase: Optional[str] = None  # "incoming", "outgoing", None (for regular local operations)
    order: Optional[int] = None  # explicit ordering for tags
```

### State Tracking
```python
class RigState:
    # Track scope per property per tag
    _tag_scopes: dict[tuple[str, str], str]  # (tag_name, property) -> scope
    _tag_orders: dict[str, int]  # tag_name -> order

    # Track operations per tag per property for processing
    _tag_operations: dict[tuple[str, str], dict]  # (tag_name, property) -> {
    #   "incoming": [],  # incoming mul operations
    #   "local": [],     # add/sub/by/to operations
    #   "outgoing": [],  # outgoing mul operations
    #   "scale": None    # scale value (last one wins)
    # }
```

### Validation
- Validate that `mul` on tags uses `incoming` or `outgoing`
- Validate scope consistency per property per tag
- Track and enforce tag ordering
- Validate scale precedence (tag overrides rig)

### Computation Order
1. Start with base values
2. For each local tag (in ascending order):
   a. Apply incoming muls (chain)
   b. Apply local operations (add/sub/by/to stack)
   c. Apply scale (if present)
   d. Apply outgoing muls (chain)
3. Apply world operations
4. Apply world scale (if present, and no tag world scales)
5. Return final computed values

## Migration from PRD11

### Changes
- `absolute` → `world`
- `relative` → `local`
- Remove `operation_mode` concept (mul/add distinction)
- Add `incoming`/`outgoing` phase for `mul` operations
- `mul` on tags requires `incoming` or `outgoing`
- Tags can freely mix additive and multiplicative operations
- Add `order` parameter for tags
- Add retroactive `scale()` operation with precedence rules

### Rationale
- "local/world" better describes processing context than "absolute/relative"
- `incoming`/`outgoing` makes `mul` positioning explicit and unambiguous
- Removing operation_mode locking allows more flexible tag design
- Explicit ordering removes ambiguity in execution sequence
- Scale with precedence provides clean retroactive adjustment

### Key Improvement
**No more mul/add mode locking** - the biggest win! Tags can now do:
```python
rig.tag("complex").local.incoming.speed.mul(2)   # Multiply input
rig.tag("complex").local.speed.add(5)            # Add value
rig.tag("complex").local.speed.add(3)            # Add more
rig.tag("complex").local.outgoing.speed.mul(1.5) # Multiply output
```
This wasn't possible in PRD11 where tags were locked to either mul OR add mode.

## Edge Cases

### Multiple `.to()` on same tag
```python
rig.tag("set").local.speed.to(10)
rig.tag("set").local.speed.to(15)  # Overwrites, final value = 15
```

### Scale without other operations
```python
rig.tag("scale_only").local.speed.scale(2)
# Scales the entire tag. no-op if no other operations exist
```

### World scope on base rig
```python
rig.world.speed.add(5)  # Applied after all local tags
```

### Anonymous builders
```python
rig.speed.add(5)  # Anonymous, defaults to local
# Still follows operation mode rules within that builder
```

## Examples

### Example 1: Complex Tag with Incoming/Outgoing
```python
# Base movement
rig.speed(10)
rig.direction(1, 0)

# Complex boost effect
rig.tag("boost").local.incoming.speed.mul(2)     # Double the input: 10 → 20
rig.tag("boost").local.speed.add(5)              # Add boost: 20 + 5 = 25
rig.tag("boost").local.speed.add(3)              # Add more: 25 + 3 = 28
rig.tag("boost").local.outgoing.speed.mul(1.5)   # Amplify output: 28 * 1.5 = 42

# Final speed: 42
```

### Example 2: Multiple Ordered Tags
```python
# Base
rig.speed(10)

# Tag 1 (order=1)
rig.tag("first", order=1).local.incoming.speed.mul(2)   # 10 * 2 = 20
rig.tag("first").local.speed.add(10)                    # 20 + 10 = 30

# Tag 2 (order=2)
rig.tag("second", order=2).local.speed.add(5)           # 30 + 5 = 35
rig.tag("second").local.outgoing.speed.mul(0.5)         # 35 * 0.5 = 17.5

# Final speed: 17.5
```

### Example 3: World Operations
```python
# Base
rig.speed(10)

// Local tags
rig.tag("boost").local.speed.add(5)              # 10 + 5 = 15
rig.tag("more").local.speed.add(3)               # 15 + 3 = 18

# World operations (after all local tags)
rig.world.speed.add(2)                           # 18 + 2 = 20
rig.world.speed.scale(2)                         # 20 * 2 = 40

# Final speed: 40
```

### Example 4: Scale Precedence
```python
# Base
rig.speed(10)

# Tag with scale
rig.tag("boost").local.speed.add(10)             # 10 + 10 = 20
rig.tag("boost").speed.scale(2)                  # Scale to +20 (10 + 20 = 30)

# World scale
rig.world.speed.scale(3)                         # 30 * 3 = 90

# Tag world scale (overrides rig world scale)
rig.tag("override").world.speed.scale(2)         # Tag wins: 30 * 2 = 60

# Final speed: 60 (tag scale overrode world scale)
```

### Example 5: Different Scopes Per Property
```python
# One tag affecting multiple properties with different scopes
rig.tag("gravity").local.direction.add(0, 1)     # Local directional influence
rig.tag("gravity").local.speed.to(9.8)           # Local speed
rig.tag("gravity").world.pos.to(0, 500)          # World position (different scope!)

# This is allowed - different properties can have different scopes
```

## Edge Cases

### Multiple `.to()` on same tag
```python
rig.tag("set").local.speed.to(10)
rig.tag("set").local.speed.to(15)     # Overwrites, final value = 15
```

### Multiple incoming or outgoing muls
```python
rig.tag("x").local.incoming.speed.mul(2)
rig.tag("x").local.incoming.speed.mul(1.5)  # Chain: input * 2 * 1.5
```

### Scale without other operations
```python
rig.tag("scale_only").speed.scale(2)
# Scales the tag's accumulated operations (if any)
# If tag has no other operations, this effectively does nothing
```

### World scale precedence
```python
rig.world.speed.scale(5)
rig.tag("a").world.speed.scale(3)
rig.tag("b").world.speed.scale(2)     # Last tag wins: 2x
```

### Mixing incoming/outgoing with regular operations
```python
rig.tag("x").local.incoming.speed.mul(2)   # Pre-multiply
rig.tag("x").local.speed.add(10)           # Regular local add
rig.tag("x").speed.scale(3)                # Scales the add: +30
rig.tag("x").local.outgoing.speed.mul(1.5) # Post-multiply
# Flow: input → *2 → +30 → *1.5 → output
```

## Summary

PRD12 provides a clear, unambiguous system for mouse rig operations:

- **local/world** scopes define processing context
- **incoming/outgoing** phases make `mul` positioning explicit
- **No operation mode locking** - tags can freely mix operations
- **Scale** provides retroactive adjustment with clear precedence
- **Order** parameter ensures predictable execution

The key insight: requiring `mul` to use `incoming`/`outgoing` eliminates all ambiguity about where multiplication happens in the processing chain.
