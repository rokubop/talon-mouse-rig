# Mouse Rig V2 - Development Guide

## Architecture Overview

```
Rig (__init__.py)           - Entry point, fluent API facade
    ↓
RigBuilder (builder.py)     - Configuration chain, deferred execution
    ↓
ActiveBuilder (builder.py)  - Executes via __del__, manages Lifecycle
    ↓
RigState (state.py)         - Frame loop, layer groups, state computation
    ↓
Lifecycle (lifecycle.py)    - OVER → HOLD → REVERT phase management
```

## Key Files

| File | Responsibility |
|------|----------------|
| `src/__init__.py` | Rig factory, StopHandle, global state |
| `src/builder.py` | RigBuilder, PropertyBuilder, ScrollPropertyProxy, ActiveBuilder |
| `src/state.py` | RigState, frame loop, layer management, computed state |
| `src/lifecycle.py` | Animation phases, PropertyAnimator, interpolation |
| `src/layer_group.py` | LayerGroup container, queue system |
| `src/mode_operations.py` | Offset/override/scale transformations |
| `src/mouse_api.py` | Platform-specific mouse movement |
| `mouse_rig.py` | Talon action wrappers (thin layer only) |

## Execution Model

1. **Configuration** - Fluent chain builds BuilderConfig
2. **Deferred Execution** - `__del__` triggers when RigBuilder garbage collected
3. **ActiveBuilder Created** - Captures config, creates Lifecycle
4. **Frame Loop** - RigState advances builders, computes state, executes movement

```python
# This chain configures, doesn't execute yet
builder = rig.speed.to(10).over(500).hold(1000).revert(500)
# Execution happens when builder goes out of scope (GC triggers __del__)
```

## Layer System

```
Base State (baked values)
├── _base_speed, _base_direction
├── _base_scroll_speed, _base_scroll_direction
└── _internal_pos

Layer Groups (modifier contributions)
├── "base.speed" → base layer builders
├── "speed.offset" → anonymous offset modifiers
├── "boost" → user-named layer
└── "scroll:base.speed" → scroll layers use "scroll:" prefix
```

## Modes

| Mode | Behavior | Example |
|------|----------|---------|
| `offset` | Add to accumulated | `rig.speed.offset.add(10)` |
| `override` | Replace value | `rig.speed.override.to(50)` |
| `scale` | Multiply value | `rig.speed.scale.mul(2.0)` |

## Scroll vs Mouse

Parallel systems differentiated by `input_type`:

```python
# Mouse movement (input_type = "move")
rig.speed.to(10)
rig.direction.to(1, 0)
rig.pos.by(100, 0)

# Scroll (input_type = "scroll")
rig.scroll.speed.to(5)
rig.scroll.direction.to(0, 1)
rig.scroll.by(0, 10)  # One-time scroll
```

Scroll layers prefixed with `scroll:` (e.g., `scroll:base.speed`)

## Animation Lifecycle

```
[OVER] ──→ [HOLD] ──→ [REVERT]
 0→1        1         1→0

over(ms, easing)   - Animate to target
hold(ms)           - Sustain target
revert(ms, easing) - Return to base/zero
then(callback)     - Fire at phase end
```

## Patterns to Follow

### 1. Actions are Thin Wrappers

Actions in `mouse_rig.py` should only configure builders, never contain animation logic:

```python
# ✓ Correct - thin wrapper
def mouse_rig_speed_to(value, over_ms, hold_ms, revert_ms):
    rig = actions.user.mouse_rig()
    builder = rig.speed.to(value)
    if over_ms: builder = builder.over(over_ms)
    if hold_ms: builder = builder.hold(hold_ms)
    if revert_ms: builder = builder.revert(revert_ms)

# ✗ Wrong - animation logic in action
def mouse_rig_scroll_by(dy, dx, over_ms):
    # DON'T use cron here, DON'T manually animate
    # Let the builder system handle it
```

### 2. Single Property Per Chain

```python
# ✓ Correct
rig.speed.to(10)
rig.direction.to(1, 0)

# ✗ Wrong - can't chain different properties
rig.speed.to(10).direction.to(1, 0)
```

### 3. Single Operator Per Chain

```python
# ✓ Correct
rig.speed.to(10)

# ✗ Wrong - multiple operators
rig.speed.to(10).add(5)
```

### 4. Single Mode Per Chain

```python
# ✓ Correct
rig.speed.offset.add(10)

# ✗ Wrong - multiple modes
rig.speed.offset.add(10).override.to(50)
```

### 5. State Access

```python
# Computed state (base + layers)
rig.state.speed
rig.state.direction
rig.state.scroll_speed

# Base state only
rig.base.speed
rig.base.direction
```

### 6. Adding New Properties

When adding a new property:
1. Add base state field in `RigState.__init__`
2. Add property handling in `_compute_current_state`
3. Add state accessor in `RigState.StateAccessor`
4. Add PropertyBuilder support if needed
5. Add frame loop execution if needed

### 7. Adding Scroll Features

Follow existing scroll patterns:
1. Use `input_type = "scroll"` in config
2. Prefix layer names with `scroll:`
3. Add to `ScrollPropertyProxy` in builder.py
4. Handle in state.py alongside existing scroll logic

## Behaviors

| Behavior | Description |
|----------|-------------|
| `stack` (default) | Builders run in parallel, values combine |
| `replace` | Cancel existing, apply new |
| `queue` | Sequential execution |
| `throttle` | Rate-limit operations |
| `debounce` | Delay + cancel previous |

## Error Handling

- Invalid configs raise `ConfigError` or `RigAttributeError`
- Validation happens at execution time (in `__del__`)
- Use `find_closest_match` for suggestions in error messages
- Mark builder invalid with `_mark_invalid` before raising

## Testing

Tests are in `tests/` directory:
- `actions.py` - Mouse movement action tests
- `actions_scroll.py` - Scroll action tests
- `main.py` - Test UI toggle

Run via: `actions.user.mouse_rig_test_toggle_ui()`
