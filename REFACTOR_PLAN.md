# Mouse Rig Refactoring Plan

## Current State
- **File size**: 5385 lines in a single `mouse_rig.py` file
- **Status**: Monolithic architecture with all code in one file
- **Complexity**: Hard to navigate, test, and maintain

## Goal
Split the monolithic file into a modular structure while maintaining Talon's action-based export pattern.

---

## Directory Structure (Target)

```
/
├── mouse_rig.py                   # Talon module interface (~100 lines)
│   └── actions.user.mouse_rig()  # Main entry point
│
├── examples.py                    # Keep as-is
├── examples.talon                 # Keep as-is
├── prd*.md                        # Keep as-is
│
└── src/                           # Implementation (hidden from users)
    ├── core.py                    # Core utilities (~200 lines)
    │   - Vec2, normalize_vector, lerp, clamp
    │   - SubpixelAdjuster
    │   - Easing functions (ease_linear, ease_in, etc.)
    │   - Mouse movement API (_make_talon_mouse_move, etc.)
    │
    ├── effects.py                 # Effect systems (~800 lines)
    │   - EffectStack (PRD 8)
    │   - EffectLifecycle (PRD 8)
    │   - Effect (PRD 5 - anonymous effects)
    │   - DirectionEffect (PRD 5)
    │   - Force
    │
    ├── builders/
    │   ├── base.py                # Base rig builders (~1200 lines)
    │   │   - PropertyEffectBuilder (anonymous effects - PRD 5)
    │   │   - PropertyRateNamespace
    │   │   - DirectionBuilder, DirectionByBuilder
    │   │   - PositionController, PositionToBuilder, PositionByBuilder
    │   │
    │   ├── effect.py              # PRD 8 effect builders (~800 lines)
    │   │   - EffectBuilder
    │   │   - EffectSpeedBuilder
    │   │   - EffectAccelBuilder
    │   │   - EffectDirectionBuilder
    │   │   - EffectPosBuilder
    │   │   - MaxBuilder
    │   │
    │   └── named.py               # Named entities (~700 lines)
    │       - NamedModifierBuilder (PRD 5 named modifiers)
    │       - NamedForceBuilder (PRD 8 forces)
    │       - NamedSpeedController, NamedAccelController, etc.
    │       - NamedForceSpeedController, etc.
    │
    ├── state.py                   # Main RigState class (~900 lines)
    │   - RigState (main state machine)
    │   - StateAccessor
    │   - BaseAccessor
    │   - get_rig() (singleton)
    │
    └── settings.py                # Talon settings (~50 lines)
        - Module & setting definitions
```

---

## Migration Steps

### Phase 1: Create Directory Structure
```bash
mkdir src
mkdir src/builders
```

### Phase 2: Extract Core Utilities (`src/core.py`)
**Lines to extract**: ~227-355 (utilities and easing functions)

**Contents**:
- `Vec2` class
- `normalize_vector()`, `lerp()`, `clamp()`
- `SubpixelAdjuster` class
- Easing functions: `ease_linear()`, `ease_in()`, `ease_out()`, `ease_in_out()`, `ease_smoothstep()`
- `EASING_FUNCTIONS` dict
- `DEFAULT_EASING` constant
- Mouse movement API: `_make_talon_mouse_move()`, `_make_windows_raw_mouse_move()`, `_initialize_mouse_move()`

**Imports needed**:
```python
import math
from typing import Tuple
from dataclasses import dataclass
```

### Phase 3: Extract Settings (`src/settings.py`)
**Lines to extract**: ~145-183 (Module and settings)

**Contents**:
- `mod = Module()`
- All `mod.setting()` definitions

**Imports needed**:
```python
from talon import Module
```

### Phase 4: Extract Effect Systems (`src/effects.py`)
**Lines to extract**: ~549-1176 (EffectStack, EffectLifecycle, Effect, DirectionEffect, Force)

**Contents**:
- `EffectStack` (PRD 8 - stacking container)
- `EffectLifecycle` (PRD 8 - lifecycle wrapper)
- `Effect` (PRD 5 - anonymous scalar effects)
- `DirectionEffect` (PRD 5 - anonymous direction effects)
- `Force` (PRD 8 - independent entities)

**Imports needed**:
```python
from typing import Optional, Union, Literal
from dataclasses import dataclass
import time
import math
from .core import Vec2, EASING_FUNCTIONS, ease_linear, lerp
```

### Phase 5: Extract Base Builders (`src/builders/base.py`)
**Lines to extract**: ~1835-2761 (PropertyEffectBuilder, PropertyRateNamespace, DirectionBuilder, DirectionByBuilder, PositionController, PositionToBuilder, PositionByBuilder)

**Contents**:
- `PropertyEffectBuilder` - Universal builder for anonymous effects
- `PropertyRateNamespace` - Rate-based transitions
- `DirectionBuilder` - Direction setting with transitions
- `DirectionByBuilder` - Relative direction changes
- `PositionController` - Position operations
- `PositionToBuilder` - Absolute position movements
- `PositionByBuilder` - Relative position movements

**Imports needed**:
```python
from typing import Optional, Callable, Union
import time
import math
from ..core import Vec2, EASING_FUNCTIONS, ease_linear, lerp, clamp
from ..effects import Effect, DirectionEffect
```

### Phase 6: Extract Effect Builders (`src/builders/effect.py`)
**Lines to extract**: ~3007-3826 (EffectBuilder, EffectSpeedBuilder, EffectAccelBuilder, EffectDirectionBuilder, EffectPosBuilder, MaxBuilder)

**Contents**:
- `EffectBuilder` - Main PRD 8 effect builder
- `EffectSpeedBuilder` - Speed effect operations
- `EffectAccelBuilder` - Acceleration effect operations
- `EffectDirectionBuilder` - Direction effect operations
- `EffectPosBuilder` - Position effect operations
- `MaxBuilder` - Max constraints builder

**Imports needed**:
```python
from typing import Optional
from ..core import Vec2
from ..effects import EffectStack, EffectLifecycle
```

### Phase 7: Extract Named Entity Builders (`src/builders/named.py`)
**Lines to extract**: ~3827-4347 (NamedModifierBuilder, NamedForceBuilder, and all their controllers)

**Contents**:
- `NamedModifierBuilder` - PRD 5 named modifiers (deprecated)
- `NamedSpeedController`, `NamedAccelController`, `NamedDirectionController`
- `NamedDirectionByBuilder`
- `NamedForceBuilder` - PRD 8 force entities
- `NamedForceSpeedController`, `NamedForceAccelController`, `NamedForceDirectionBuilder`
- `NamedModifierNamespace`, `NamedForceNamespace`

**Imports needed**:
```python
from typing import Optional, Callable
import time
from ..core import Vec2
from ..effects import Effect, DirectionEffect, Force
```

### Phase 8: Extract State Management (`src/state.py`)
**Lines to extract**: ~4355-5313 (RigState, StateAccessor, BaseAccessor, get_rig)

**Contents**:
- `RigState` - Main state machine class
- `StateAccessor` - Computed state access (`rig.state.*`)
- `BaseAccessor` - Base values access (`rig.base.*`)
- `get_rig()` - Singleton accessor

**Imports needed**:
```python
from typing import Optional, Callable, Literal, Union
from dataclasses import dataclass
import time
import math
from talon import cron, settings
from .core import Vec2, SubpixelAdjuster, _mouse_move, lerp, clamp
from .effects import EffectStack, EffectLifecycle, Effect, DirectionEffect, Force
from .builders.base import PropertyEffectBuilder, DirectionBuilder, PositionController
from .builders.effect import EffectBuilder
from .builders.named import NamedModifierNamespace, NamedForceNamespace
```

### Phase 9: Create New Root `mouse_rig.py`
**Replace entire file** with clean interface:

```python
"""Talon Mouse Rig - Entry point"""
from talon import Module, actions
from .src.state import get_rig
from .src.settings import mod  # Re-export module for settings

class Actions:
    def mouse_rig():
        """Get the mouse rig instance"""
        return get_rig()
```

---

## Legacy Code to Consider Removing

### Obsolete Transition Classes (Lines 447-542)
**Status**: Replaced by effect system in PRD 8
- `Transition` (base class)
- `SpeedTransition`
- `DirectionTransition`
- `PositionTransition`

**Used by**:
- `SpeedBuilder` (lines ~1351-1442)
- `SpeedAdjustBuilder` (lines ~1443-1543)
- `SpeedMultiplyBuilder` (lines ~1544-1644)
- `SpeedDivideBuilder` (lines ~1645-1752)
- `DirectionBuilder` (line 2151)
- `PropertyEffectBuilder` (line 1882)

**Impact**: Breaking change for legacy syntax
- ❌ `rig.speed(10).over(500)` - would be removed
- ✅ `rig.speed.to(10).over(500)` - still works (uses PropertyEffectBuilder)
- ✅ `rig.effect("boost").speed.to(10).over(500)` - still works

**Decision**: Mark for future removal, but keep for now to maintain backward compatibility.

### Legacy Builder Classes
These could be simplified/removed:
- `SpeedBuilder` - Replaced by `PropertyEffectBuilder`
- `SpeedAdjustBuilder` - Replaced by `PropertyEffectBuilder`
- `SpeedMultiplyBuilder` - Replaced by `PropertyEffectBuilder`
- `SpeedDivideBuilder` - Replaced by `PropertyEffectBuilder`
- `SpeedController` - Could be simplified to only return `PropertyEffectBuilder`
- `AccelController` - Could be simplified to only return `PropertyEffectBuilder`

**Estimated line reduction**: ~1400 lines if removed

---

## Testing Strategy

### 1. Unit Tests
Create test files in `src/tests/`:
- `test_core.py` - Test Vec2, utilities, easing
- `test_effects.py` - Test EffectStack, EffectLifecycle, Effect classes
- `test_builders.py` - Test builder fluent API
- `test_state.py` - Test RigState integration

### 2. Integration Tests
- Test complete workflows (WASD movement, sprint, boost pads, etc.)
- Test effect stacking
- Test force composition
- Test lifecycle transitions

### 3. Regression Tests
- Ensure existing examples still work
- Test both old API (if keeping) and new API

---

## Migration Checklist

- [ ] Phase 1: Create directory structure
- [ ] Phase 2: Extract `src/core.py`
- [ ] Phase 3: Extract `src/settings.py`
- [ ] Phase 4: Extract `src/effects.py`
- [ ] Phase 5: Extract `src/builders/base.py`
- [ ] Phase 6: Extract `src/builders/effect.py`
- [ ] Phase 7: Extract `src/builders/named.py`
- [ ] Phase 8: Extract `src/state.py`
- [ ] Phase 9: Create new root `mouse_rig.py`
- [ ] Update `examples.py` imports if needed
- [ ] Test all examples
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Remove obsolete code (optional, breaking change)

---

## Notes

### Import Patterns
Since Talon doesn't use standard Python `__init__.py` patterns, use relative imports:
```python
# In src/state.py
from .core import Vec2
from .effects import EffectStack
from .builders.effect import EffectBuilder
```

### Circular Dependencies
Watch for circular imports between:
- `state.py` ↔ `builders/*.py` (RigState referenced in builders)
- Solution: Use forward references with string quotes: `'RigState'`

### Error Messages
Keep error message helpers in their own section or in `core.py`:
- `_get_speed_operations_help()`
- `_get_accel_operations_help()`
- `_get_pos_operations_help()`
- `_get_direction_operations_help()`
- `_error_cannot_chain_property()`
- `_error_unknown_builder_attribute()`

---

## Benefits After Refactoring

1. **Easier Navigation**: Find code quickly in focused files
2. **Better Testing**: Test systems independently
3. **Clearer Architecture**: See dependencies and relationships
4. **Easier Collaboration**: Work on different files without conflicts
5. **Maintainability**: Smaller files are easier to understand
6. **Incremental Loading**: Could optimize imports if needed
7. **Documentation**: Each module can have clear purpose

---

## Risks & Mitigation

### Risk 1: Breaking Existing Code
**Mitigation**: Keep backward compatibility during migration, deprecate gracefully

### Risk 2: Import Errors
**Mitigation**: Test incrementally, use type hints to catch issues early

### Risk 3: Talon-Specific Import Issues
**Mitigation**: Test in Talon environment after each phase, not just in editor

### Risk 4: Circular Dependencies
**Mitigation**: Use forward references, design clean dependency hierarchy

---

## Future Enhancements (Post-Refactor)

1. **Remove Legacy Code**: Clean up Transition classes and old builders
2. **Add Type Stubs**: Create `.pyi` files for better IDE support
3. **Add Logging**: Structured logging for debugging
4. **Performance Profiling**: Identify and optimize hot paths
5. **Documentation**: Auto-generate API docs from docstrings
6. **Plugin System**: Allow extending with custom effects/forces

---

Last Updated: November 12, 2025
