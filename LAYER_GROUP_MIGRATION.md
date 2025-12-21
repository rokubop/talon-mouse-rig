# LayerGroup Architecture Migration

## Overview
Migrating from parent/children ActiveBuilder model to LayerGroup container model.

## Key Changes

### Before
```python
# RigState holds individual builders
_active_builders: dict[str, ActiveBuilder] = {}

# ActiveBuilder has children
class ActiveBuilder:
    children: list[ActiveBuilder] = []
    # First builder becomes "parent", rest are children
```

### After
```python
# RigState holds layer groups
_layer_groups: dict[str, LayerGroup] = {}

# LayerGroup contains multiple builders as siblings
class LayerGroup:
    builders: list[ActiveBuilder] = []  # All are siblings
    accumulated_value: Any  # Baked state for modifiers
    pending_queue: deque[Callable]  # Queue within group
```

## Layer Scoping

| Layer Type | Key Format | Persistence |
|-----------|------------|-------------|
| Base | `base.{property}` | Transient - removed when empty |
| Auto-modifier | `{property}.{mode}` | Persistent if non-zero |
| User-named | `{name}` | Persistent if non-zero |

## Builder Lifecycle

1. **Builder created** → Added to group
2. **Builder animates** → Contributes to group value
3. **Builder completes** → Bakes to group, removed from builders list
4. **Group accumulates** → Holds baked value (for modifiers only)
5. **Group cleanup** → Removed if empty + zero accumulated (except for active operations)

## Baking Flow

```
Builder completes
  ↓
If base layer:
  builder value → base state (via RigState.bake_group)
  group removed (transient)
  ↓
If modifier layer:
  builder value → group.accumulated_value
  builder removed from group.builders
  group persists with accumulated value
```

## Behavior Semantics

### Replace
```python
rig.speed.offset.by(10).replace()
# 1. Get group.get_current_value() → current accumulated + active
# 2. new_builder.base_value = current_value
# 3. group.clear_builders()  # Remove old active builders
# 4. group.add_builder(new_builder)
```

### Stack
```python
rig.speed.offset.by(5).stack()
rig.speed.offset.by(5).stack()
# Both builders coexist in group.builders
# group.get_current_value() = accumulated + builder1 + builder2
```

### Queue
```python
rig.pos.by(50, 0).queue()
rig.pos.by(0, 50).queue()
# First executes immediately
# Second added to group.pending_queue
# When first completes → bakes → second starts
```

### Throttle
```python
rig.speed.to(10).throttle(500)
rig.speed.to(15).throttle(500)  # Within 500ms → ignored
# Throttle tracking stays global (spans group recreation)
# Check in add_builder before adding to group
```

## Migration Steps

1. ✅ Create LayerGroup class
2. ⏳ Update RigState._layer_groups
3. ⏳ Remove ActiveBuilder.children
4. ⏳ Rewrite add_builder() to use groups
5. ⏳ Update frame loop to iterate groups → builders
6. ⏳ Move queue into LayerGroup
7. ⏳ Update behavior handlers
8. ⏳ Update baking logic

## API Compatibility

No breaking changes to public API:
```python
# All of these still work the same
rig.speed.to(10)
rig.layer("boost").speed.offset.by(5)
rig.speed.offset.by(5).stack().over(300)
```

Internal implementation changes are transparent to users.
