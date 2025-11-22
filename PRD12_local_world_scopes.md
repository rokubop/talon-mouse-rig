# PRD12: Local/World Scope System with Incoming/Outgoing

## Overview
A clear scope system that uses `local`/`world` to define processing context, with `incoming`/`outgoing` to position `mul` operations explicitly in the processing chain.

## Core Concepts

### 1. Scopes
Defines **where** an operation is applied:

- **`local`** - The layer's own contribution/work (default for layers)
- **`world`** - Operations on the accumulated global value (after all local layers)

### 2. Incoming/Outgoing (For Mul Only)
Defines **when** a `mul` operation happens relative to the layer's work:

- **`incoming`** - Pre-process: multiply the input **before** the layer's local work
- **`outgoing`** - Post-process: multiply the output **after** the layer's local work

### 3. Operation Rules
- **`mul`** operations **MUST** use `incoming` or `outgoing` on layers (never standalone)
- **`add`, `sub`, `by`, `to`** operations work directly in `local` scope (can stack freely)
- **No operation mode locking** - layers can freely mix additive and multiplicative operations
- Different properties on the same layer can have different scopes

## Computation Chain

```
Base Rig
  ↓
Local layers (by order)
  For each layer:
    incoming → local operations → outgoing
  ↓
World Operations
```

**Detailed Example:**
```python
# Base
rig.speed(10)                                      # base = 10

# Local layer 1 (order=1)
rig.layer("boost", order=1).local.incoming.speed.mul(2)   # 10 * 2 = 20
rig.layer("boost").local.speed.add(5)                     # 20 + 5 = 25
rig.layer("boost").local.speed.add(3)                     # 25 + 3 = 28
rig.layer("boost").local.outgoing.speed.mul(1.5)          # 28 * 1.5 = 42

# Local layer 2 (order=2)
rig.layer("sprint", order=2).local.incoming.speed.mul(0.5) # 42 * 0.5 = 21
rig.layer("sprint").local.speed.add(10)                    # 21 + 10 = 31

# World operations
rig.world.speed.add(5)                            # 31 + 5 = 36
rig.world.speed.scale(2)                          # 36 * 2 = 72

# Final speed = 72
```

## API Examples

### Basic Local layer Usage

```python
// Local scope (default for layers)
rig.layer("boost").local.speed.add(5)           # Additive operation
rig.layer("boost").speed.add(5)                 # Equivalent - defaults to local

rig.layer("boost").local.incoming.speed.mul(2)  # Multiply input before layer's work
rig.layer("boost").local.outgoing.speed.mul(1.5) # Multiply output after layer's work
```

### World Scope

```python
# World operations (after all local layers)
rig.world.speed.add(10)                       # Add to accumulated value
rig.world.speed.scale(2)                      # Scale final result
```

### Base Rig Operations

```python
rig.speed.add(10)                             # === rig.local.speed.add(10)
rig.speed.scale(2)                            # === rig.local.speed.scale(2)
```

### Complete layer Example

```python
# A layer can mix operations freely
rig.layer("effect").local.incoming.speed.mul(2)   # Pre-multiply
rig.layer("effect").local.speed.add(5)            # Add
rig.layer("effect").local.speed.add(3)            # Add more (stacks)
rig.layer("effect").local.speed.sub(1)            # Subtract
rig.layer("effect").local.outgoing.speed.mul(1.5) # Post-multiply

# Processing: input → *2 → +5 → +3 → -1 → *1.5 → output
```

### Scale (Retroactive Multiplier)

```python
# Scale an additive layer
rig.layer("boost").local.speed.add(5)
rig.layer("boost").local.speed.add(3)               # Total: +8
rig.layer("boost").speed.scale(2).over(1000)        # Scale entire layer: +16

# Scale with incoming/outgoing
rig.layer("x").local.incoming.speed.mul(2)          # Pre: *2
rig.layer("x").local.speed.add(10)                  # Add: +10
rig.layer("x").speed.scale(3)                       # Scale the add: +30
rig.layer("x").local.outgoing.speed.mul(1.5)        # Post: *1.5
# Result: input → *2 → +30 → *1.5

# Scale world
rig.world.speed.scale(1.5)                        # Scale accumulated total

# Scale base
rig.speed.scale(2).over(1000)                     # Scale base speed

# Scale precedence: Last one wins (layer scales override rig scales)
rig.world.speed.scale(2)
rig.layer("override").world.speed.scale(3)          # layer wins: 3x not 2x
```

### layer Ordering

```python
# Explicit order
rig.layer("first", order=1).local.speed.add(5)
rig.layer("second", order=2).local.speed.add(3)

# Subsequent builders on same layer append in original order
rig.layer("first").local.speed.add(2)  # Appends to "first", keeps order=1
```

### Scope for Different Properties

```python
// Position
rig.layer("move").world.pos.to(500, 300)        # World coordinates
rig.layer("offset").local.pos.add(50, 0)        # Local offset

# Direction - mixing scopes on same layer, different properties
rig.layer("gravity").local.direction.add(0, 1)  # Local directional influence
rig.layer("gravity").local.speed.to(9.8)        # Local speed

# With incoming/outgoing
rig.layer("turn").local.incoming.direction.mul(0.5)  # Reduce input direction
rig.layer("turn").local.direction.add(1, 0)          # Add rightward influence
```

## Rules

### Scope Rules
1. layers default to `local` scope if not specified
2. Scope can be `local` or `world`
3. Scope is tracked per property per layer (different properties can have different scopes)
4. First operation on a property sets the scope for that property
5. `rig.world.*` operations always use world scope
6. Base rig operations (`rig.speed.add(5)`) default to local scope

### Mul Operation Rules
1. **`mul` on layers MUST use `incoming` or `outgoing`** - never standalone
2. `incoming` multiplies the input before the layer's local work
3. `outgoing` multiplies the output after the layer's local work
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
4. layer scales override rig scales
5. Syntax: `rig.layer("x").speed.scale(2)` (no scope prefix needed)

### layer Ordering
1. layers execute in ascending order (order=1, then order=2, etc.)
2. Subsequent operations on same layer append to that layer
3. layers without explicit order execute in creation order

## Implementation Notes

### BuilderConfig Changes
```python
class BuilderConfig:
    scope: Optional[str] = None  # "local", "world"
    phase: Optional[str] = None  # "incoming", "outgoing", None (for regular local operations)
    order: Optional[int] = None  # explicit ordering for layers
```

### State Tracking
```python
class RigState:
    # Track scope per property per layer
    _layer_scopes: dict[tuple[str, str], str]  # (layer_name, property) -> scope
    _layer_orders: dict[str, int]  # layer_name -> order

    # Track operations per layer per property for processing
    _layer_operations: dict[tuple[str, str], dict]  # (layer_name, property) -> {
    #   "incoming": [],  # incoming mul operations
    #   "local": [],     # add/sub/by/to operations
    #   "outgoing": [],  # outgoing mul operations
    #   "scale": None    # scale value (last one wins)
    # }
```

### Validation
- Validate that `mul` on layers uses `incoming` or `outgoing`
- Validate scope consistency per property per layer
- Track and enforce layer ordering
- Validate scale precedence (layer overrides rig)

### Computation Order
1. Start with base values
2. For each local layer (in ascending order):
   a. Apply incoming muls (chain)
   b. Apply local operations (add/sub/by/to stack)
   c. Apply scale (if present)
   d. Apply outgoing muls (chain)
3. Apply world operations
4. Apply world scale (if present, and no layer world scales)
5. Return final computed values

## Migration from PRD11

### Changes
- `absolute` → `world`
- `relative` → `local`
- Remove `operation_mode` concept (mul/add distinction)
- Add `incoming`/`outgoing` phase for `mul` operations
- `mul` on layers requires `incoming` or `outgoing`
- layers can freely mix additive and multiplicative operations
- Add `order` parameter for layers
- Add retroactive `scale()` operation with precedence rules

### Rationale
- "local/world" better describes processing context than "absolute/relative"
- `incoming`/`outgoing` makes `mul` positioning explicit and unambiguous
- Removing operation_mode locking allows more flexible layer design
- Explicit ordering removes ambiguity in execution sequence
- Scale with precedence provides clean retroactive adjustment

### Key Improvement
**No more mul/add mode locking** - the biggest win! layers can now do:
```python
rig.layer("complex").local.incoming.speed.mul(2)   # Multiply input
rig.layer("complex").local.speed.add(5)            # Add value
rig.layer("complex").local.speed.add(3)            # Add more
rig.layer("complex").local.outgoing.speed.mul(1.5) # Multiply output
```
This wasn't possible in PRD11 where layers were locked to either mul OR add mode.

## Edge Cases

### Multiple `.to()` on same layer
```python
rig.layer("set").local.speed.to(10)
rig.layer("set").local.speed.to(15)  # Overwrites, final value = 15
```

### Scale without other operations
```python
rig.layer("scale_only").local.speed.scale(2)
# Scales the entire layer. no-op if no other operations exist
```

### World scope on base rig
```python
rig.world.speed.add(5)  # Applied after all local layers
```

### Anonymous builders
```python
rig.speed.add(5)  # Anonymous, defaults to local
# Still follows operation mode rules within that builder
```

## Examples

### Example 1: Complex layer with Incoming/Outgoing
```python
# Base movement
rig.speed(10)
rig.direction(1, 0)

# Complex boost effect
rig.layer("boost").local.incoming.speed.mul(2)     # Double the input: 10 → 20
rig.layer("boost").local.speed.add(5)              # Add boost: 20 + 5 = 25
rig.layer("boost").local.speed.add(3)              # Add more: 25 + 3 = 28
rig.layer("boost").local.outgoing.speed.mul(1.5)   # Amplify output: 28 * 1.5 = 42

# Final speed: 42
```

### Example 2: Multiple Ordered layers
```python
# Base
rig.speed(10)

# layer 1 (order=1)
rig.layer("first", order=1).local.incoming.speed.mul(2)   # 10 * 2 = 20
rig.layer("first").local.speed.add(10)                    # 20 + 10 = 30

# layer 2 (order=2)
rig.layer("second", order=2).local.speed.add(5)           # 30 + 5 = 35
rig.layer("second").local.outgoing.speed.mul(0.5)         # 35 * 0.5 = 17.5

# Final speed: 17.5
```

### Example 3: World Operations
```python
# Base
rig.speed(10)

// Local layers
rig.layer("boost").local.speed.add(5)              # 10 + 5 = 15
rig.layer("more").local.speed.add(3)               # 15 + 3 = 18

# World operations (after all local layers)
rig.world.speed.add(2)                           # 18 + 2 = 20
rig.world.speed.scale(2)                         # 20 * 2 = 40

# Final speed: 40
```

### Example 4: Scale Precedence
```python
# Base
rig.speed(10)

# layer with scale
rig.layer("boost").local.speed.add(10)             # 10 + 10 = 20
rig.layer("boost").speed.scale(2)                  # Scale to +20 (10 + 20 = 30)

# World scale
rig.world.speed.scale(3)                         # 30 * 3 = 90

# layer world scale (overrides rig world scale)
rig.layer("override").world.speed.scale(2)         # layer wins: 30 * 2 = 60

# Final speed: 60 (layer scale overrode world scale)
```

### Example 5: Different Scopes Per Property
```python
# One layer affecting multiple properties with different scopes
rig.layer("gravity").local.direction.add(0, 1)     # Local directional influence
rig.layer("gravity").local.speed.to(9.8)           # Local speed
rig.layer("gravity").world.pos.to(0, 500)          # World position (different scope!)

# This is allowed - different properties can have different scopes
```

## Edge Cases

### Multiple `.to()` on same layer
```python
rig.layer("set").local.speed.to(10)
rig.layer("set").local.speed.to(15)     # Overwrites, final value = 15
```

### Multiple incoming or outgoing muls
```python
rig.layer("x").local.incoming.speed.mul(2)
rig.layer("x").local.incoming.speed.mul(1.5)  # Chain: input * 2 * 1.5
```

### Scale without other operations
```python
rig.layer("scale_only").speed.scale(2)
# Scales the layer's accumulated operations (if any)
# If layer has no other operations, this effectively does nothing
```

### World scale precedence
```python
rig.world.speed.scale(5)
rig.layer("a").world.speed.scale(3)
rig.layer("b").world.speed.scale(2)     # Last layer wins: 2x
```

### Mixing incoming/outgoing with regular operations
```python
rig.layer("x").local.incoming.speed.mul(2)   # Pre-multiply
rig.layer("x").local.speed.add(10)           # Regular local add
rig.layer("x").speed.scale(3)                # Scales the add: +30
rig.layer("x").local.outgoing.speed.mul(1.5) # Post-multiply
# Flow: input → *2 → +30 → *1.5 → output
```

## Summary

PRD12 provides a clear, unambiguous system for mouse rig operations:

- **local/world** scopes define processing context
- **incoming/outgoing** phases make `mul` positioning explicit
- **No operation mode locking** - layers can freely mix operations
- **Scale** provides retroactive adjustment with clear precedence
- **Order** parameter ensures predictable execution

The key insight: requiring `mul` to use `incoming`/`outgoing` eliminates all ambiguity about where multiplication happens in the processing chain.
