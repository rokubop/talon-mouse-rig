# Code Cleanup Analysis - Post PRD 8 Refactor

## Executive Summary

After 8 architectural iterations (PRD 1-8), the codebase contains:
1. **Dual effect systems** running in parallel (PRD 5 vs PRD 8)
2. **Legacy builder classes** that are rarely/never used
3. **Deprecated API** (`rig.modifier()` superseded by `rig.effect()`)
4. **Duplicate functionality** in property controllers

---

## Critical Issues Found

### 1. **DUAL EFFECT SYSTEMS (PRD 5 + PRD 8 Running Simultaneously)**

**Problem**: Both old and new effect systems are active, causing redundant processing every frame.

**Location**: `src/state.py`

```python
def _get_effective_speed(self) -> float:
    base_speed = self._speed

    # OLD SYSTEM (PRD 5 - for backward compatibility)
    for effect in self._effects:
        if effect.property_name == "speed":
            base_speed = effect.update(base_speed)

    # NEW SYSTEM (PRD 8)
    for key in self._effect_order:
        stack = self._effect_stacks[key]
        # ...
```

**Files with dual systems**:
- `_get_effective_speed()` - lines 237-289
- `_get_effective_accel()` - lines 292-337
- `_get_effective_direction()` - lines 341-385
- `_update_frame()` - lines 752-818

**State storage duplication**:
```python
# OLD (PRD 5)
self._effects: list[Effect] = []
self._direction_effects: list[DirectionEffect] = []
self._named_modifiers: dict[str, Effect] = {}
self._named_direction_modifiers: dict[str, DirectionEffect] = {}

# NEW (PRD 8)
self._effect_stacks: dict[str, EffectStack] = {}
self._effect_lifecycles: dict[str, EffectLifecycle] = {}
self._effect_order: list[str] = []
```

**Recommendation**:
- ✅ **Remove PRD 5 effect system entirely** (breaking change)
- ❌ OR keep only if you have users with old code (requires migration guide)

---

### 2. **DEPRECATED API: `rig.modifier()` vs `rig.effect()`**

**Problem**: PRD 8 renamed `modifier` to `effect`, but the old API still exists and works.

**Current API (PRD 8)**:
```python
rig.effect("sprint").speed.mul(2)  # ✅ NEW
rig.modifier("sprint").speed.mul(2)  # ⚠️ OLD, still works
```

**Files**:
- `src/state.py`: `modifier` property (lines 115-124)
- `src/builders/named.py`: `NamedModifierBuilder` class (lines 11-60)
- `src/builders/named.py`: `NamedModifierNamespace` class (lines 511-549)

**Usage in examples**: NOT USED - examples.py only uses `.effect()`

**Recommendation**:
- ✅ **Remove `.modifier()` API** - it's fully superseded by `.effect()`
- ✅ **Remove `NamedModifierBuilder`**, `NamedModifierNamespace`, `NamedSpeedController`, `NamedAccelController`, `NamedDirectionController`

---

### 3. **LEGACY BUILDER CLASSES (Rarely/Never Used)**

**Problem**: Old builder classes exist for backward compatibility but add maintenance burden.

#### SpeedAdjustBuilder (lines 1291-1390)
```python
class SpeedAdjustBuilder:  # ❌ LEGACY
    """Builder for speed.add() and speed.subtract()"""
```
**Modern equivalent**: `PropertyEffectBuilder` with `"by"` operation
**Used by**: `SpeedController.add()`, `.subtract()`, `.sub()` (marked as "legacy" in docstrings)

#### SpeedMultiplyBuilder (lines 1393-1492)
```python
class SpeedMultiplyBuilder:  # ❌ LEGACY
    """Builder for speed.multiply()"""
```
**Modern equivalent**: `PropertyEffectBuilder` with `"mul"` operation
**Used by**: `SpeedController.multiply()` (marked as "legacy")

#### SpeedDivideBuilder (lines 1495-1601)
```python
class SpeedDivideBuilder:  # ❌ LEGACY
    """Builder for speed.divide()"""
```
**Modern equivalent**: `PropertyEffectBuilder` with `"div"` operation
**Used by**: `SpeedController.divide()` (marked as "legacy")

**SpeedController methods using them**:
```python
def add(self, delta: float) -> SpeedAdjustBuilder:
    """Add to current speed (legacy - use .by() for new code)"""  # ❌

def subtract(self, delta: float) -> SpeedAdjustBuilder:
    """Subtract from current speed (legacy - use .by() with negative for new code)"""  # ❌

def multiply(self, factor: float) -> SpeedMultiplyBuilder:
    """Multiply current speed by factor (legacy - use .mul() for new code)"""  # ❌

def divide(self, divisor: float) -> SpeedDivideBuilder:
    """Divide current speed by divisor (legacy - use .div() for new code)"""  # ❌
```

**Modern alternatives already exist**:
```python
def mul(self, factor: float) -> PropertyEffectBuilder:  # ✅ CURRENT
def div(self, divisor: float) -> PropertyEffectBuilder:  # ✅ CURRENT
def to(self, value: float) -> PropertyEffectBuilder:    # ✅ CURRENT
def by(self, delta: float) -> PropertyEffectBuilder:    # ✅ CURRENT
```

**Recommendation**:
- ✅ **Remove** `SpeedAdjustBuilder`, `SpeedMultiplyBuilder`, `SpeedDivideBuilder` (~300 lines)
- ✅ **Remove** `.add()`, `.subtract()`, `.sub()`, `.multiply()`, `.divide()` from `SpeedController`
- ✅ **Keep** `.mul()`, `.div()`, `.to()`, `.by()` (they use `PropertyEffectBuilder`)

---

### 4. **UNUSED/INCONSISTENT FEATURES**

#### PropertyRateNamespace (lines 234-300)
**Status**: Incomplete implementation
```python
class PropertyRateNamespace:
    def speed(self, value: float):
        # TODO: Implement position rate logic
        pass
```
**Recommendation**: ✅ Remove or complete the implementation

#### reverse() method
**Issue**: Not found in SpeedController or RigState
**Documentation says**: `rig.reverse()  # 180° turn`
**Recommendation**: ⚠️ Verify if this exists or should be removed from docs

---

### 5. **INCONSISTENT TERMINOLOGY**

**Problem**: "modifier" vs "effect" terminology mixed throughout codebase

**Examples**:
- Comments: "# Apply old effect system (PRD 5 - for backward compatibility)"
- Variables: `self._named_modifiers` (should be `_named_effects`?)
- Properties: `rig.modifier` (deprecated) vs `rig.effect` (current)

**Recommendation**: ✅ Standardize all to "effect" terminology in PRD 8 system

---

## Detailed Cleanup Recommendations

### Phase 1: Remove Deprecated APIs (Breaking Changes)

**Files to modify**: `src/state.py`
```python
# ❌ REMOVE these properties
@property
def modifier(self) -> NamedModifierNamespace:
    ...

# ❌ REMOVE these state variables
self._modifier_namespace = NamedModifierNamespace(self)
```

**Files to DELETE**:
- Sections in `src/builders/named.py`:
  - `NamedModifierBuilder` (lines 11-60)
  - `NamedModifierNamespace` (lines 511-549)
  - `NamedSpeedController` (lines 64-96)
  - `NamedAccelController` (lines 100-132)
  - `NamedDirectionController` (lines 136-151)

**Estimated lines removed**: ~200 lines

---

### Phase 2: Remove PRD 5 Effect System (Breaking Changes)

**Files to modify**: `src/state.py`

**Remove state variables**:
```python
# ❌ REMOVE
self._effects: list[Effect] = []
self._direction_effects: list[DirectionEffect] = []
self._named_modifiers: dict[str, Effect] = {}
self._named_direction_modifiers: dict[str, DirectionEffect] = {}
self._accel_velocities: dict[Effect, float] = {}
```

**Remove from methods**:
- `_get_effective_speed()`: Remove lines 237-240
- `_get_effective_accel()`: Remove lines 292-295
- `_get_effective_direction()`: Remove lines 341-343
- `_update_frame()`: Remove direction effect loop (lines 752-761)
- `_update_frame()`: Remove scalar effect loop (lines 785-817)
- `bake()`: Remove clear calls (lines 508-511)
- `_stop_immediate()`: Remove clear calls (lines 532-533)
- `_is_idle()`: Remove checks (lines 704-708)

**Files to modify**: `src/effects.py`
**Remove classes**:
```python
# ❌ REMOVE (if not used by PRD 8 system)
class Effect:  # Lines ~170-400
class DirectionEffect:  # Lines ~400-600
```

**Estimated lines removed**: ~500 lines

---

### Phase 3: Remove Legacy Builders

**Files to modify**: `src/builders/base.py`

**Remove classes**:
- `SpeedAdjustBuilder` (lines 1291-1390) - ~100 lines
- `SpeedMultiplyBuilder` (lines 1393-1492) - ~100 lines
- `SpeedDivideBuilder` (lines 1495-1601) - ~107 lines

**Remove methods from `SpeedController`**:
```python
# ❌ REMOVE
def add(self, delta: float) -> SpeedAdjustBuilder:
def subtract(self, delta: float) -> SpeedAdjustBuilder:
def sub(self, delta: float) -> SpeedAdjustBuilder:
def multiply(self, factor: float) -> SpeedMultiplyBuilder:
def divide(self, divisor: float) -> SpeedDivideBuilder:
```

**Estimated lines removed**: ~350 lines

---

### Phase 4: Cleanup PropertyEffectBuilder

**Files to modify**: `src/builders/base.py`

**Issue**: `PropertyEffectBuilder` is used for both:
1. Anonymous temporary effects (PRD 5): `rig.speed.by(10).hold(2000).revert()`
2. Base rig property changes: `rig.speed(10)` → `SpeedController.__call__()` → `SpeedBuilder`

**Status**: Actually used! Keep it but verify it's not duplicating logic with EffectBuilder

---

### Phase 5: Remove Unused Imports

After cleanup, check for unused imports:
```python
# In src/state.py - likely unused after cleanup
from .effects import Effect, DirectionEffect  # ❌ If PRD 5 removed
from .builders.named import NamedModifierNamespace  # ❌ If .modifier removed
```

---

## Summary of Removals

| Item | Lines | Impact |
|------|-------|--------|
| PRD 5 Effect System | ~500 | Breaking |
| `.modifier()` API | ~200 | Breaking |
| Legacy Builders | ~350 | Breaking |
| Incomplete Features | ~100 | None |
| **Total** | **~1150 lines** | **25-30% reduction** |

---

## Migration Guide (if keeping backward compatibility)

### From `.modifier()` to `.effect()`
```python
# OLD (PRD 5)
rig.modifier("sprint").speed.mul(2)
rig.modifier("sprint").stop()

# NEW (PRD 8)
rig.effect("sprint").speed.mul(2)
rig.effect("sprint").revert()
```

### From legacy speed methods
```python
# OLD
rig.speed.add(10)
rig.speed.multiply(2)
rig.speed.divide(2)

# NEW
rig.speed.by(10)  # or .add(10) if keeping alias
rig.speed.mul(2)
rig.speed.div(2)
```

---

## Recommendation Priority

### HIGH PRIORITY (Do Now)
1. ✅ **Fix `_mouse_move` bug** (already done)
2. ✅ **Remove duplicate `get_rig()` definition** (already done)
3. ✅ **Remove `PropertyRateNamespace`** (incomplete, ~70 lines)

### MEDIUM PRIORITY (Breaking Changes - Coordinate with Users)
4. ✅ **Remove `.modifier()` API** (~200 lines) - fully replaced by `.effect()`
5. ✅ **Remove legacy builders** (~350 lines) - `.add()`, `.multiply()`, etc.

### LOW PRIORITY (Big Breaking Change - Needs Migration Period)
6. ⚠️ **Remove PRD 5 effect system** (~500 lines) - if no users depend on it
7. ⚠️ **Rename `_named_modifiers` → `_named_effects`** (consistency)

---

## Next Steps

1. **Confirm**: Are there any external users relying on PRD 5 Effect system or `.modifier()` API?
2. **Decision**: Breaking changes acceptable, or need deprecation period?
3. **Execute**: Start with High Priority cleanups (safe, non-breaking)
4. **Test**: After each phase, verify `mouse_rig_go_left` and `mouse_rig_stop` still work
