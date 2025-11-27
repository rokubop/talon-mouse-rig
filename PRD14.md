# Product Requirements Document: Layer Modes

## Overview
Introducing explicit **modes** to the layer API to eliminate ambiguity in how layers combine with the rig's base values.

## The Problem
The current API is ambiguous:
```python
# BEFORE - ambiguous
rig.layer("boost").speed.to(100)
# Does this mean: layer contributes +100, or final speed = 100?
```

## The Solution
Require an explicit **mode** for every layer operation:
```python
# AFTER - unambiguous
rig.layer("boost").speed.offset.to(100)  # layer contributes +100
rig.layer("cap").speed.override.to(100)  # final speed = 100
```

---

## Modes

Three modes define how a layer's value combines with the rig:

### **`offset`** - Additive contribution
Layer's value is added to the rig's value.
```python
# Add 50 to speed
rig.layer("boost").speed.offset.add(50)

# Set layer's speed contribution to 100
rig.layer("cruise").speed.offset.to(100)

# Camera shake
rig.layer("shake").position.offset.by(5, -3)
```

### **`override`** - Replace value
Layer's value completely replaces the rig's value (ignores base and other layers with lower order).
```python
# Lock cursor to center
rig.layer("lock").position.override.to(screen_w/2, screen_h/2)

# Snap to cardinal direction
rig.layer("snap").direction.override.to(90)

# Speed cap
rig.layer("limit").speed.override.to(200)
```

### **`scale`** - Multiplicative factor
Layer's value multiplies the rig's current value.
```python
# Slow motion
rig.layer("slowmo").speed.scale.to(0.3)

# Friction on velocity
rig.layer("friction").vector.scale.to(0.8)
```

---

## Restrictions

### **1. Mode is required**
Every layer operation MUST specify a mode. No defaults.
```python
# ❌ ERROR - no mode specified
rig.layer("boost").speed.to(100)

# ✅ CORRECT
rig.layer("boost").speed.offset.to(100)
```

### **2. One mode per layer**
A layer cannot mix modes. Once a mode is set, all operations on that layer must use the same mode.
```python
# ❌ ERROR - mixing modes
rig.layer("boost").speed.offset.to(100)
rig.layer("boost").speed.override.to(200)

# ✅ CORRECT - use separate layers
rig.layer("boost").speed.offset.to(100)
rig.layer("cap").speed.override.to(200)
```

### **3. Supported properties**
- **speed** - scalar value
- **position** - (x, y) coordinates
- **direction** - angle (scalar) or (x, y) vector
- **vector** - (x, y) velocity (experimental)

---

## Required Parameters

When using layers, you must now specify:

### **Minimum required:**
```python
rig.layer(name).property.mode.operation(value)
rig.layer(name).mode.property.operation(value)
```

### **With optional order:**
```python
rig.layer(name, order=N).property.mode.operation(value)
rig.layer(name, order=N).mode.property.operation(value)
```

### **With timing:**
```python
rig.layer(name).property.mode.operation(value).over(duration)
```

---

## Examples

### Speed Control
```python
# Temporary boost
rig.layer("boost").speed.offset.add(50).over(500).revert(500)

# Speed limiter
rig.layer("cap").speed.override.to(200)

# Slow motion
rig.layer("slowmo").speed.scale.to(0.3)
```

### Position Control
```python
# Lock cursor
rig.layer("lock").position.override.to(960, 540)

# Camera shake
rig.layer("shake").position.offset.by(5, 5)

# Smooth snap
rig.layer("snap").position.override.to(x, y).over(300)
```

### Direction Control
```python
# Snap to north
rig.layer("snap").direction.override.to(0, -1)

# Recoil offset
rig.layer("recoil").direction.offset.by(15).revert(100, "ease_out")

# Aim assist
rig.layer("assist").direction.override.to(1, 0).over(200)
```

### Complex Layering
```python
# Lock position, add shake on top
rig.layer("lock", order=1).position.override.to(center_x, center_y)
rig.layer("shake", order=2).position.offset.by(shake_x, shake_y)

# Base speed + boost + cap
rig.layer("cruise", order=1).speed.offset.to(100)
rig.layer("boost", order=2).speed.offset.add(50).revert(1000)
rig.layer("limit", order=3).speed.override.to(200)
```

---

## Migration Guide

### Before (ambiguous):
```python
rig.layer("boost").speed.to(100)
rig.layer("lock").position.to(x, y)
```

### After (explicit):
```python
rig.layer("boost").speed.offset.to(100)  # additive
rig.layer("lock").position.override.to(x, y)  # replacement
```

## Other notes
- [ ] No more "blend_mode", only "mode" now and it is slightly different.
- [ ] Remove existing 'override' as a separate method; integrate into mode system.

---

## Implementation Checklist

- [ ] Update contracts
- [ ] Enforce mode requirement (error if not specified)
- [ ] Validate single mode per layer (error on mode mixing)
- [ ] Support `offset`, `override`, `scale` modes
- [ ] Apply modes to: speed, position, direction, vector
- [ ] Update builders and state calculations
- [ ] Update error messages to guide users to specify mode
- [ ] Update documentation with examples