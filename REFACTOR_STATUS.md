# Mouse Rig API Refactor — Status

## What was done

### 1. Consolidated cardinal direction actions into parameterized actions (`mouse_rig.py`)

**Removed 17 actions** — cardinal variants where direction was baked into the function name:
- `mouse_rig_go_left/right/up/down`, `mouse_rig_go_direction`
- `mouse_rig_direction_left/right/up/down`
- `mouse_rig_scroll_go_left/right/up/down`, `mouse_rig_scroll_go_direction`
- `mouse_rig_scroll_direction_left/right/up/down`

**Added `DIRECTION_MAP`** at module level for string→vector lookup (supports diagonals):
```python
DIRECTION_MAP = {
    "left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1),
    "up_left": (-1, -1), "up_right": (1, -1), "down_left": (-1, 1), "down_right": (1, 1),
}
```

**Added 10 new actions:**

| Action | Description |
|--------|-------------|
| `mouse_rig_go(direction, speed, force)` | Set direction + start moving |
| `mouse_rig_go_natural(direction, speed, force, scale)` | Smooth turns, speed-scaled timing |
| `mouse_rig_go_vector(x, y, speed, force)` | Arbitrary direction vector |
| `mouse_rig_go_vector_natural(x, y, speed, force, scale)` | Smooth turns with vector |
| `mouse_rig_boost(amount, over_ms, hold_ms, release_ms, max_stacks)` | One-shot speed boost via implicit `speed.offset` layer |
| `mouse_rig_boost_start(amount, over_ms)` | Sustained boost start via `speed.offset` |
| `mouse_rig_boost_stop(release_ms)` | Sustained boost stop via `speed.offset.revert()` |
| `mouse_rig_scroll_go(direction, speed, force)` | Scroll direction + start |
| `mouse_rig_scroll_go_natural(direction, speed, force, scale)` | Smooth scroll turns |
| `mouse_rig_scroll_boost(amount, over_ms, hold_ms, release_ms, max_stacks)` | One-shot scroll speed boost via implicit scroll `speed.offset` |

### 2. Natural movement settings (`settings.py`)

Added 4 settings for `go_natural` / `scroll_go_natural`:

| Setting | Default | Description |
|---------|---------|-------------|
| `mouse_rig_natural_turn_ms` | 500 | Base duration for direction changes |
| `mouse_rig_natural_turn_easing` | `ease_out2` | Easing for direction changes |
| `mouse_rig_natural_speed_ms` | 200 | Duration for speed ramp (start from stopped only) |
| `mouse_rig_natural_speed_easing` | `ease_in_out` | Easing for speed ramp |

Turn timing scales dynamically with current speed:
```python
speed_factor = max(1.0, rig.state.speed / 3.0)
turn_ms = int(base_turn_ms * scale * speed_factor)
```
At speed 3→500ms, speed 6→1000ms, speed 10→1667ms.

### 3. Updated `mouse_rig_user.talon`

Rewritten to use new parameterized API. User also manually added `rig go left/right/up/down` commands using `go_natural`.

### 4. Updated all callsites

- `talon-grid-mode/grid_mode.py` — `go_direction` → `go_vector`
- `talon-face-tester/face_tester.py` — `go_up/right/left` → `go("up"/"right"/"left")` (wrapped in lambdas for input_map)
- `talon-mouse-rig/tests/actions.py` — Updated all test functions and registry
- `talon-mouse-rig/tests/actions_scroll.py` — Updated all test functions and registry (removed cardinal direction tests that tested removed actions)
- `talon-mouse-rig/tests/sequence.py` — `go_right(5)` → `go("right", 5)`

### 5. Bug fixes

**Race condition in `_sync_to_manual_mouse_movement`** (`src/state.py`):
- `self._expected_mouse_pos` could become `None` between the `is not None` check and the unpack
- Fix: capture to local variable before unpacking

**Revert-only path in builder `_execute`** (`src/builder.py`):
- `rig.speed.offset.revert(ms)` was broken — the `.speed.offset` chain sets `config.property`, so the revert-only check (`property is None and operator is None`) was never hit
- Fix: relaxed check to `operator is None` so implicit layer paths like `rig.speed.offset.revert(ms)` correctly trigger `trigger_revert` on the existing layer

## Currently debugging

**`boost_start` → `boost_stop` sequence crashes.** Steps to reproduce:
1. `rig go left` (start moving)
2. `rig boost start` (sustained boost via `rig.speed.offset.add(amount).over(over_ms)`)
3. `rig boost stop` (calls `rig.speed.offset.revert(release_ms)`)

Error: `TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'` in `lerp(target_value, base_value, progress)` at `src/core.py:193`.

The builder.py `_execute` fix (relaxing the revert-only check) should address this, but **has not been tested yet**. The fix ensures `rig.speed.offset.revert(ms)` hits `trigger_revert` instead of creating a broken `ActiveBuilder` with no operator/base_value.

### Stack trace reference
```
mouse_rig.py:344        | rig.speed(speed)
builder.py:725           | self._execute()
builder.py:745           | self.rig_state.add_builder(active)
state.py:620             | self._finalize_builder_completion(builder...)
  → then on cron tick:
layer_group.py:286       | builder.get_interpolated_value()
builder.py:1590          | PropertyAnimator.animate_scalar(neutral, target, phase, progress, ...)
lifecycle.py:270         | lerp(target_value, base_value, progress)  ← base_value is None
core.py:193              | a + (b - a) * t  ← NoneType error
```

Note: the deferred error from `rig.speed(speed)` at line 344 and the cron error may be two symptoms of the same root cause — a broken builder in the `speed.offset` layer group corrupts the state, then subsequent operations and tick frames both fail.

## Files modified

| File | Changes |
|------|---------|
| `mouse_rig.py` | Removed 17 actions, added 10, added DIRECTION_MAP, added `settings` import |
| `settings.py` | Added 4 natural movement settings |
| `mouse_rig_user.talon` | Rewritten for new API (user also manually edited) |
| `src/state.py` | Race condition fix in `_sync_to_manual_mouse_movement` |
| `src/builder.py` | Revert-only path fix in `_execute` |
| `tests/actions.py` | Updated for new API |
| `tests/actions_scroll.py` | Updated for new API |
| `tests/sequence.py` | Updated `go_right(5)` → `go("right", 5)` |
| `../talon-grid-mode/grid_mode.py` | `go_direction` → `go_vector` |
| `../talon-face-tester/face_tester.py` | Cardinal go actions → parameterized `go()` |
