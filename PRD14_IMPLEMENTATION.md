# PRD14 Implementation Summary

## Changes Made

### 1. Contracts (contracts.py)
- **Removed**: `VALID_BLEND_MODES`
- **Added**: `VALID_MODES = ['offset', 'override', 'scale']`
- **Updated**: `BuilderConfig.blend_mode` → `BuilderConfig.mode`
- **Added**: `validate_mode()` method to enforce mode requirement for user layers
- **Removed**: 'scale' operator from VALID_OPERATORS (now a mode instead)

### 2. Builder (builder.py)
- **Removed**: `OverrideProxy` class
- **Added**: `ModeProxy` class for mode-based property access
- **Added**: Mode accessors to `RigBuilder`: `.offset`, `.override`, `.scale`
- **Added**: Mode accessors to `PropertyBuilder`: `.offset`, `.override`, `.scale`
- **Updated**: `_execute()` to call `config.validate_mode()` before execution

### 3. State (state.py)
- **Updated**: `_apply_layer()` to use `mode` instead of `blend_mode`
- **Implemented**: Three distinct mode behaviors:
  - **offset**: Additive (layer contributes to accumulated value)
  - **override**: Replacement (layer replaces accumulated value)
  - **scale**: Multiplicative (layer multiplies accumulated value)
- **Added**: Mode mixing validation in `add_builder()` to prevent mixing modes on same layer

### 4. Main Entry Point (__init__.py)
- **Removed**: `Rig.override` property accessor (old blend_mode system)

## New API Usage

### Syntax Options
Both syntaxes are supported:
```python
# Option 1: layer.property.mode.operation
rig.layer("boost").speed.offset.to(100)

# Option 2: layer.mode.property.operation
rig.layer("boost").offset.speed.to(100)
```

### Mode Examples

#### Offset Mode (Additive)
```python
# Add 50 to accumulated speed
rig.layer("boost").speed.offset.add(50)

# Set layer's speed contribution to 100
rig.layer("cruise").speed.offset.to(100)

# Camera shake (position offset)
rig.layer("shake").position.offset.by(5, -3)
```

#### Override Mode (Replacement)
```python
# Lock cursor to center (ignores other layers)
rig.layer("lock").position.override.to(960, 540)

# Snap to cardinal direction
rig.layer("snap").direction.override.to(0, -1)

# Speed cap (max speed limit)
rig.layer("limit").speed.override.to(200)
```

#### Scale Mode (Multiplicative)
```python
# Slow motion (50% speed)
rig.layer("slowmo").speed.scale.to(0.5)

# Friction on velocity
rig.layer("friction").vector.scale.to(0.8)
```

### Complex Layering
```python
# Combine modes with explicit ordering
rig.layer("boost", order=1).speed.offset.to(100)    # Base: 50 + 100 = 150
rig.layer("slowmo", order=2).speed.scale.to(0.5)    # 150 * 0.5 = 75
rig.layer("cap", order=3).speed.override.to(200)    # Final: 200
```

## Validation

### Mode Required
User layers must specify a mode:
```python
# ❌ ERROR - no mode specified
rig.layer("boost").speed.to(100)

# ✅ CORRECT
rig.layer("boost").speed.offset.to(100)
```

### No Mode Mixing
Each layer must use a single mode:
```python
# ❌ ERROR - mixing modes on same layer
rig.layer("boost").speed.offset.to(100)
rig.layer("boost").speed.override.to(200)

# ✅ CORRECT - use separate layers
rig.layer("boost").speed.offset.to(100)
rig.layer("cap").speed.override.to(200)
```

### Anonymous Layers
Base and final layers (anonymous) default to offset mode behavior and don't require explicit mode:
```python
# ✅ CORRECT - base layer doesn't require mode
rig.speed.to(50)
rig.direction.to(1, 0)
```

## Migration from Old API

### Before (Ambiguous)
```python
rig.layer("boost").speed.to(100)  # Unclear: contribute or override?
rig.layer("lock").position.to(x, y)
```

### After (Explicit)
```python
rig.layer("boost").speed.offset.to(100)  # Clear: contributes +100
rig.layer("lock").position.override.to(x, y)  # Clear: replaces position
```

## Implementation Notes

### Mode Calculation Logic

#### Offset Mode
- Adds layer's value to accumulated value
- For all operators (to, add, by, sub, mul, div)

#### Override Mode
- Replaces accumulated value with absolute value
- Converts relative operations to absolute:
  - `override.to(100)` → speed = 100
  - `override.add(50)` → speed = base + 50 (animated)

#### Scale Mode
- Multiplies accumulated value by layer's factor
- Typically used with `.to()` to set scale factor:
  - `scale.to(0.5)` → speed *= 0.5

### Anonymous Layer Behavior
- Base layers (rig.speed, rig.direction, etc.) default to offset mode
- Don't require explicit mode specification
- Maintain backward compatibility with existing code
