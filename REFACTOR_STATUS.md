# LayerGroup Refactor - Remaining Work

## ✅ Completed
1. Created LayerGroup class with queue, accumulated state, lifecycle
2. Updated RigState.__init__ to use _layer_groups instead of _active_builders
3. Removed ActiveBuilder.children
4. Simplified ActiveBuilder.advance() and get_interpolated_value()
5. Added ActiveBuilder.group back-reference
6. Created new add_builder implementation (in NEW_ADD_BUILDER.py)

## 🔄 In Progress - Need to Integrate

### add_builder and helpers
- Replace old add_builder() with new implementation from NEW_ADD_BUILDER.py
- Add helper methods: `_get_or_create_group()`, `_targets_match()`, `_recalculate_rate_duration()`, `_bake_group_to_base()`
- Remove old behavior handlers: `_handle_user_layer_behavior()`, `_handle_base_layer_behavior()`

### Frame Loop
- Update `_tick_frame()` to iterate groups → builders
- Update `_advance_all_builders()` to work with groups
- Update `_compute_current_state()` to aggregate from groups
- Update `_apply_layer()` to work with groups

### Baking & Cleanup
- Update `remove_builder()` → should be `remove_group()` or handle within group
- Update `_bake_builder()` → groups handle baking now
- Add group cleanup logic (remove empty base groups, keep modifier groups with value)

### References to Update
All places that reference `_active_builders` need to use `_layer_groups`:
- `time_alive()` method
- `_should_frame_loop_be_active()`
- `trigger_revert()`
- `_execute_callbacks()`
- Property state accessors

### Queue System
- Remove old QueueManager class (queue.py)
- Queue is now in LayerGroup
- Update any queue-related methods

### Rate Cache
- `_rate_builder_cache` needs to store group references, not builder references
- Update cache cleanup logic

### Tests
- Allwill probably break initially
- Need to verify behaviors still work:
  - stack, replace, queue, throttle, debounce
  - base vs modifier layer semantics
  - baking logic

## Next Steps (in order)

1. **Integrate new add_builder** - Copy from NEW_ADD_BUILDER.py into state.py, remove old one
2. **Update frame loop** - Make _tick_frame iterate groups
3. **Fix _compute_current_state** - Aggregate from groups
4. **Remove old behavior handlers** - Delete _handle_user_layer_behavior and _handle_base_layer_behavior
5. **Update all _active_builders references** - Search and replace with _layer_groups
6. **Remove QueueManager** - Delete queue.py import and usage
7. **Run tests** - Fix failures one by one
8. **Clean up** - Remove NEW_ADD_BUILDER.py, update documentation

## Key Architecture Changes

### Before
```
_active_builders[layer] = parent_builder
parent_builder.children = [child1, child2]
```

### After
```
_layer_groups[layer] = LayerGroup
LayerGroup.builders = [builder1, builder2, builder3]  # All siblings
LayerGroup.accumulated_value = baked_value
```

### Aggregation
- Old: Parent aggregates children values
- New: Group aggregates all builder values + accumulated value

### Baking
- Base groups: Bake directly to base state, group removed
- Modifier groups: Builders bake to group.accumulated_value, group persists

## Estimated Remaining Work
- ~500 lines of code changes
- ~2-3 hours of refactoring
- ~1-2 hours of testing/debugging

Ready to continue!
