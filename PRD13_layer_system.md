# PRD13: Layer System with Incoming/Outgoing

## Overview
A unified layer-based system where everything is a layer (base, user layers, final). All layers follow the same contract with incoming/outgoing phases for explicit operation ordering.

## Core Concepts

### 1. Everything is a Layer
Three types of layers, all following the same contract:

- **`base`** - Initial layer (rig.speed operations)
- **`user layers`** - Named layers (rig.layer("name") operations)
- **`final`** - Final layer (rig.final operations)

### 2. Layer Contract (Universal)
Every layer processes values through the same flow:

```
input → incoming phase → layer operations → outgoing phase → output
```

**Phases:**
- **`incoming`** - Pre-process: operations on the input before the layer's work
- **`(default)`** - Layer's main operations (add, sub, to, scale)
- **`outgoing`** - Post-process: operations on the output after the layer's work

### 3. Override Scope
Layers can override accumulated values:

- **`override`** - Ignore previous accumulated value, replace with new value

## Processing Chain

```
base.incoming (no-op, nothing before base)
  ↓
base operations
  ↓
base.outgoing
  ↓
layer[order=1].incoming
  ↓
layer[order=1] operations
  ↓
layer[order=1].outgoing
  ↓
layer[order=2].incoming
  ↓
layer[order=2] operations
  ↓
layer[order=2].outgoing
  ↓
final.incoming
  ↓
final operations
  ↓
final.outgoing (THE ABSOLUTE LAST THING)
  ↓
result
```

## API Examples

### Base Layer

```python
# Base layer operations (rig.speed = rig.layer("__base__"))
rig.speed.to(10)                    # Set initial value
rig.speed.add(5).over(1000)         # Anonymous operation in base
rig.incoming.speed.mul(2)           # No-op (nothing before base)
rig.outgoing.speed.mul(1.5)         # Post-process base before user layers
```

### User Layers

```python
# Simple layer
rig.layer("boost").speed.add(10)

# With incoming/outgoing
rig.layer("boost").incoming.speed.mul(2)    # Pre-process input
rig.layer("boost").speed.add(10)            # Layer's work
rig.layer("boost").speed.add(5)             # More work
rig.layer("boost").outgoing.speed.mul(1.5)  # Post-process output

# With ordering
rig.layer("first", order=1).speed.add(5)
rig.layer("second", order=2).speed.add(3)
```

### Final Layer

```python
# Final layer operations
rig.final.speed.add(5)              # Final adjustments
rig.final.incoming.speed.mul(2)     # Pre-process accumulated result
rig.final.outgoing.speed.mul(0.5)   # THE FINAL FINAL OPERATION
```

### Override Scope

```python
# Override ignores previous accumulated value at this layer's position
rig.layer("boost").speed.add(10)           # Contribute +10
rig.layer("more").speed.add(5)             # Contribute +5 (total: +15)
rig.layer("cap").override.speed.to(100)    # Ignore previous, set to 100
rig.layer("after").speed.add(10)           # Add to 100 (result: 110)
```

### Mixing Operations (No Mode Locking!)

```python
# Layers can freely mix all operation types
rig.layer("complex").incoming.speed.mul(2)   # Pre-multiply
rig.layer("complex").speed.add(10)           # Add
rig.layer("complex").speed.add(5)            # Add more
rig.layer("complex").speed.scale(2)          # Scale: +30 total
rig.layer("complex").outgoing.speed.mul(1.5) # Post-multiply

# Processing: input → ×2 → +30 → ×1.5 → output
```

### Scale (Retroactive Multiplier)

```python
# Scale accumulated operations within a layer
rig.layer("boost").speed.add(5)
rig.layer("boost").speed.add(3)       # Total: +8
rig.layer("boost").speed.scale(2)     # Scale to +16

# Scale with phases
rig.layer("x").incoming.speed.mul(2)  # Pre: ×2
rig.layer("x").speed.add(10)          # Add: +10
rig.layer("x").speed.scale(3)         # Scale the add: +30
rig.layer("x").outgoing.speed.mul(1.5) # Post: ×1.5
# Result: input → ×2 → +30 → ×1.5
```

### Different Properties

```python
# Different properties can have different behaviors
rig.layer("gravity").direction.add(0, 1)      # Directional influence
rig.layer("gravity").speed.to(9.8)            # Set speed
rig.layer("gravity").override.pos.to(0, 500)  # Override position
```

## Complete Examples

### Example 1: Simple Layering

```python
# Base
rig.speed.to(10)

# User layers
rig.layer("boost").speed.add(20)       # 10 + 20 = 30
rig.layer("more").speed.add(10)        # 30 + 10 = 40

# Final
rig.final.speed.add(5)                 # 40 + 5 = 45
rig.final.outgoing.speed.mul(2)        # 45 × 2 = 90

# Result: 90
```

### Example 2: Incoming/Outgoing Processing

```python
# Base
rig.speed.to(10)
rig.outgoing.speed.mul(2)              # 10 × 2 = 20

# Layer 1
rig.layer("boost", order=1).incoming.speed.mul(1.5)  # 20 × 1.5 = 30
rig.layer("boost").speed.add(10)                     # 30 + 10 = 40
rig.layer("boost").outgoing.speed.mul(2)             # 40 × 2 = 80

# Layer 2
rig.layer("cap", order=2).incoming.speed.mul(0.5)    # 80 × 0.5 = 40
rig.layer("cap").override.speed.to(50)               # Ignore 40, set to 50

# Final
rig.final.speed.add(10)                # 50 + 10 = 60

# Result: 60
```

### Example 3: Practical Use - The Final Final

```python
# Movement setup
rig.speed.to(100)
rig.direction(1, 0)

# Boost effects
rig.layer("sprint").incoming.speed.mul(2)      # Double input
rig.layer("sprint").speed.add(50)              # Add boost

# Final adjustments
rig.final.speed.add(10)                        # Fine-tune
rig.final.outgoing.speed.mul(0.8)              # Global speed limiter (THE FINAL THING)
```

### Example 4: Complex Multi-Layer

```python
# Base
rig.speed.to(10)
rig.direction(1, 0)

# Layer 1 - Boost
rig.layer("boost", order=1).incoming.speed.mul(2)   # 10 × 2 = 20
rig.layer("boost").speed.add(5)                     # 20 + 5 = 25
rig.layer("boost").speed.add(3)                     # 25 + 3 = 28
rig.layer("boost").speed.scale(2)                   # (5+3)×2 = 16, total: 20 + 16 = 36
rig.layer("boost").outgoing.speed.mul(1.5)          # 36 × 1.5 = 54

# Layer 2 - Sprint
rig.layer("sprint", order=2).incoming.speed.mul(0.5) # 54 × 0.5 = 27
rig.layer("sprint").speed.add(10)                    # 27 + 10 = 37

# Final
rig.final.speed.add(5)                               # 37 + 5 = 42
rig.final.outgoing.speed.mul(2)                      # 42 × 2 = 84

# Result: speed = 84
```

## Rules

### Layer Rules
1. Three layer types: base, user layers, final
2. Base layer always executes first
3. User layers execute in order (first instance timing OR explicit `order` parameter)
4. Final layer always executes last
5. All layers follow the same contract: incoming → operations → outgoing

### Operation Rules
1. **`incoming`/`outgoing`** - For phase-specific operations (typically `mul`)
2. **`add`, `sub`, `by`, `to`** - Can be used directly in layer (no phase needed)
3. **`mul`** - MUST use `incoming` or `outgoing` on user layers for clarity
4. **`scale`** - Retroactive multiplier applied to accumulated layer operations
5. **No operation mode locking** - Layers can freely mix all operation types

### Override Rules
1. `override` scope ignores previous accumulated value
2. Override happens at the layer's position in the processing order
3. Layers after the override still process normally
4. Override primarily used with `.to()` for replacement behavior

### Ordering Rules
1. Base layer: order = -infinity (always first)
2. User layers without explicit order: use first instance timing
3. User layers with explicit order: `rig.layer("name", order=N)`
4. Final layer: order = +infinity (always last)
5. Subsequent operations on same layer append to that layer

### Edge Cases
1. `base.incoming` - No-op (nothing before base)
2. `final.outgoing` - THE absolute final operation before result
3. `rig.speed.add(5)` - Shorthand for base layer operation
4. Anonymous operations in base layer stack normally

## Implementation Notes

### Internal Representation
```python
# Internally, all use the same layer system:
rig.speed.to(10)              # layer_name = "__base__"
rig.layer("boost").speed.add(5)  # layer_name = "boost"
rig.final.speed.add(10)       # layer_name = "__final__"
```

### Layer Contract
```python
class Layer:
    incoming_operations: list  # Phase 1: Pre-process
    operations: list           # Phase 2: Main work
    outgoing_operations: list  # Phase 3: Post-process
    override_mode: bool        # Ignore previous accumulated value
    order: int                 # Processing order
    
    def process(input_value):
        # Phase 1: Incoming
        value = apply_operations(input_value, incoming_operations)
        
        # Phase 2: Main operations (with potential override)
        if override_mode:
            value = apply_operations(0, operations)  # Ignore input
        else:
            value = apply_operations(value, operations)
        
        # Phase 3: Outgoing
        value = apply_operations(value, outgoing_operations)
        
        return value
```

### Processing Order
```python
# Pseudo-code for computation
def compute_property(property_name):
    value = base_value
    
    # Get all layers sorted by order
    layers = [base_layer] + sorted(user_layers, by=order) + [final_layer]
    
    for layer in layers:
        value = layer.process(value)
    
    return value
```

## Key Improvements Over PRD12

### 1. Unified Layer Model
**Before (PRD12):**
- `local` vs `world` scopes (different behaviors)
- Base rig vs tags vs world operations (three separate concepts)

**After (PRD13):**
- Everything is a layer (one unified concept)
- All layers follow the same contract

### 2. Cleaner API
**Before (PRD12):**
```python
rig.tag("boost").local.incoming.speed.mul(2)  # Redundant "local"
rig.tag("boost").local.speed.add(10)          # Redundant "local"
rig.world.speed.add(5)                        # Different concept
```

**After (PRD13):**
```python
rig.layer("boost").incoming.speed.mul(2)      # No redundant scope
rig.layer("boost").speed.add(10)              # Implicit layer context
rig.final.speed.add(5)                        # Consistent layer model
```

### 3. Better Semantics
- `layer` naturally implies local scope (no need to say "local")
- `override` is clearer than `world` for replacement behavior
- `final` is explicit about timing vs implicit "world runs last"

### 4. More Powerful Final Operations
**PRD12:** `world` was primarily for override/replacement

**PRD13:** `final` supports full layer contract:
```python
rig.final.incoming.speed.mul(2)     # Pre-process result
rig.final.speed.add(5)               # Final adjustments
rig.final.outgoing.speed.mul(0.5)   # THE FINAL FINAL THING
```

### 5. Consistent Mental Model
**One rule:** Everything flows through layers, each layer has incoming → operations → outgoing

## Migration from PRD12

### Terminology Changes
| PRD12 | PRD13 |
|-------|-------|
| `tag()` | `layer()` |
| `.local` | (removed, implicit) |
| `.world` | `.final` or `.override` |
| `rig.tag("x").local.speed.add(5)` | `rig.layer("x").speed.add(5)` |
| `rig.world.speed.add(5)` | `rig.final.speed.add(5)` |
| `rig.tag("x").world.speed.to(10)` | `rig.layer("x").override.speed.to(10)` |

### Key Changes
1. **Remove `local` scope** - Implicit in layer concept
2. **Split `world` into two concepts:**
   - `final` - Operations at the end of the processing chain
   - `override` - Replacement behavior at a layer's position
3. **Rename `tag()` to `layer()`** - Better semantic fit
4. **Add `final.outgoing`** - The absolute final operation

## Summary

PRD13 provides a beautifully consistent layer-based system:

- **One concept:** Everything is a layer
- **One contract:** incoming → operations → outgoing
- **One flow:** base → user layers → final
- **Cleaner API:** No redundant scope keywords
- **More powerful:** Final layer with full phase support

The key insight: "Layer" naturally implies scope/context, eliminating the need for explicit "local" keyword while providing a clearer mental model of the processing chain.
