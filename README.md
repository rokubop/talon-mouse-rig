![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)
![License](https://img.shields.io/badge/license-MIT-green)

# Talon Mouse Rig

<table width="600"><tr>
<td width="150"><img src="preview.svg"></td>
<td>All purpose mouse rig for Talon with movement and scrolling. Prefers OS-specific relative movement to be compatible with games.</td>
</tr></table>

## What can it do?

- Continuous mouse movement with speed, direction, turns
- Discrete mouse movement by direction or x,y offset
- Absolute position movement with easing
- Speed adjustments, boosts, braking
- Smooth curves and natural easing transitions
- Scroll ticks and continuous scroll movement
- Native platform APIs compatible with games
- [Ready-to-use voice commands](mouse_rig_user.talon)

## Installation

Clone this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# mac and linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

# This repo
git clone https://github.com/rokubop/talon-mouse-rig
```

🎉 Done!

Go to **[mouse_rig_user.talon](mouse_rig_user.talon)** to start trying out commands.

This is your file to customize.

## Talon Actions

**At a Glance**

```
Movement:
  mouse_rig_move              one-shot move (direction, amount)
  mouse_rig_move_natural      one-shot smooth move (direction, amount)
  mouse_rig_move_xy           one-shot move (dx, dy)
  mouse_rig_move_xy_natural   one-shot smooth move (dx, dy)
  mouse_rig_move_value        one-shot move in current direction
  mouse_rig_go                continuous move (direction, speed)
  mouse_rig_go_natural        continuous smooth move (direction, speed)
  mouse_rig_go_xy             continuous move (x, y, speed)
  mouse_rig_go_xy_natural     continuous smooth move (x, y, speed)
  mouse_rig_speed_*           speed control (to, add, mul)
  mouse_rig_direction_*       direction control (to, by degrees)
  mouse_rig_pos_to            move to absolute position
  mouse_rig_boost*            one-shot or sustained speed boost

Scroll:
  mouse_rig_scroll            one-shot scroll (direction, amount)
  mouse_rig_scroll_natural    one-shot smooth scroll (direction, amount)
  mouse_rig_scroll_xy         one-shot scroll (dx, dy)
  mouse_rig_scroll_xy_natural one-shot smooth scroll (dx, dy)
  mouse_rig_scroll_go         continuous scroll (direction, speed)
  mouse_rig_scroll_go_natural continuous smooth scroll (direction, speed)
  mouse_rig_scroll_go_xy      continuous scroll (x, y, speed)
  mouse_rig_scroll_go_xy_natural continuous smooth scroll (x, y, speed)
  mouse_rig_scroll_speed_*    scroll speed control (to, add, mul)
  mouse_rig_scroll_direction_* scroll direction control (to, by)
  mouse_rig_scroll_boost*     one-shot or sustained scroll boost

Control:
  mouse_rig_stop            stop movement
  mouse_rig_scroll_stop     stop scrolling
  mouse_rig_sequence        chain actions with waits
```

**Naming patterns:**
- `_to` = set absolute value
- `_by` = relative delta
- `_natural` = smooth transitions with easing
- `_xy` = raw x,y values instead of direction string

See [mouse_rig.py](mouse_rig.py) for full parameters.

### Native Scroll API

Scroll uses native platform APIs (SendInput on Windows, CGEvent on macOS, XTest on Linux) for sub-line precision. This enables smooth direction transitions at low scroll speeds - e.g., turning from down to right produces a smooth arc instead of "stop Y, start X".

- `mouse_rig_scroll("down", 1)` = 1 physical scroll tick (matches your mouse wheel)
- `mouse_rig_scroll_natural("down", 8)` = smooth 8-tick scroll with easing (400ms default)
- Continuous scroll (`scroll_go_natural`) uses native API for smooth velocity scrolling

Controlled by `mouse_rig_scroll_api` setting (defaults to following `mouse_rig_api`).

## Transitions and Easings

All operations can transition through three phases: **over** → **hold** → **revert**, with callbacks at each stage.

<img src="assets/speed_curve.svg">

Mix and match any combination:

<img src="assets/speed_curve_combos.svg">

Transitions also accept an easing function. Solid = base, faded = 2→4 (sharper).

<img src="assets/easing_curves.svg">

When Talon actions support transitions, you'll see parameters like `over_ms`, `hold_ms`, `revert_ms`, and `easing`.

Not all actions expose every parameter. For full control, use the [fluent API](#fluent-api).

## Fluent API

`rig = actions.user.mouse_rig()` - full control over every operation.

```python
rig.pos.to(960, 540).over(400, "ease_in_out")
rig.speed(8)
rig.direction.to(1, 0)
rig.direction.by(90).over(500)              # rotate
rig.scroll.by(0, 3)                        # scroll down 3 ticks
rig.scroll.by_pixels.by(0, 5).over(400)    # smooth scroll via native API
rig.scroll.speed.to(5)
rig.scroll.direction.to(0, 1)              # scroll down
rig.stop()
rig.stop(1000)                             # smooth stop
```

### Callbacks

Chain `.then()` at each phase:

```python
rig.speed.add(10).over(300) \
    .then(lambda: print("ramped up")) \
    .hold(2000) \
    .then(lambda: print("held")) \
    .revert(300) \
    .then(lambda: print("reverted"))
```

### Offset and Override

Use an offset layer for a separate, revertible effect.
Available on all properties pos, speed, direction, etc

```python
# start (can do up to 3 stacks)
rig.speed.offset.stack(3).add(10).over(200)

# later
rig.speed.offset.revert(200)
```

Built in layers are `offset` or `override`.

### Layers

Instead of using built-in `offset`, use named layers when you want to invoke a start and stop at different times, and be able to reference it in `state.layers` for introspection.

```python
rig.layer("boost").speed.add(10).over(1000)
rig.layer("boost").revert(1000)  # remove effect
rig.layer("boost").bake()        # flatten into base
rig.layer("boost").emit(1000)    # convert to anonymous layer that fades out
```

**Repeat behaviors** control what happens when a layer fires again while active:

```python
rig.layer("boost").stack.speed.add(10)        # stack (default)
rig.layer("boost").stack(3).speed.add(10)     # max 3 stacks
rig.layer("boost").queue.speed.add(10)        # queue until finished
rig.layer("boost").throttle(500).speed.add(10) # rate-limit
rig.layer("boost").reset.speed.add(10)        # restart from scratch
```

### Quick Reference

**Properties:** `pos`, `speed`, `direction`, `scroll.speed`, `scroll.direction`, `scroll.vector`

**Operators:** `.to()`, `.add()` / `.by()`, `.sub()`, `.mul()`, `.div()` - additive and multiplicative cannot be mixed on the same layer

**Lifecycle:** `.over(ms, easing?)`, `.over(rate=X)`, `.hold(ms)`, `.revert(ms?, easing?)`, `.then(callback)`

**Behaviors:** `.stack(max?)`, `.queue()`, `.throttle(ms?)`, `.reset()`

**Easing:** `linear`, `ease_in`, `ease_out`, `ease_in_out`, `ease_in2` … `ease_in_out4`

**Shortcuts:** `rig.stop(ms?)`, `rig.reverse(ms?)`, `rig.bake()`

**State:**

```python
rig.state.pos          # computed (base + all effects)
rig.state.base.speed   # base only
rig.state.layers["sprint"]  # LayerState or None
```

### Execution Note

Fluent chains execute on garbage collection. If you hold a reference to the builder, it may not run until the variable goes out of scope. Call `.run()` to execute immediately:

```python
builder = rig.speed.add(10).over(300)
builder.run()  # execute now instead of waiting for GC
```

## Tests

200+ tests across 13 groups run live inside Talon and serve as working examples. See the [test files](tests/) for usage patterns.

Uncomment [mouse_rig_dev.talon](mouse_rig_dev.talon) to enable.

Requires [talon-ui-elements](https://github.com/rokubop/talon-ui-elements) (v0.14.0+).

![Tests](assets/tests.png)
