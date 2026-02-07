![Version](https://img.shields.io/badge/version-0.7.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)
![License](https://img.shields.io/badge/license-MIT-green)

# Talon Mouse Rig

<table width="600"><tr>
<td width="150"><img src="preview.svg"></td>
<td>All purpose mouse rig for Talon with movement and scrolling. Prefers OS-specific relative movement to be compatible with games.</td>
</tr></table>

![Demo](assets/demo.webp)

## Overview

Mouse rig gives you

- ~50 actions for controlling mouse position, speed, direction, and scroll
- Transitions and easing
- Works with games by using relative movement when possible
- Ready to use voice commands in [mouse_rig_user.talon](mouse_rig_user.talon)
- Sequencing actions
- Offset and override layers for temporary effects

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
mouse_rig_go_*          direction + speed (continuous)
mouse_rig_speed_*       speed (continuous)
mouse_rig_direction_*   absolute or by degrees
mouse_rig_pos_*         absolute or delta

mouse_rig_scroll_by_*     delta
mouse_rig_scroll_go_*     direction + speed (continuous)
mouse_rig_scroll_speed_*  speed (continuous)
mouse_rig_scroll_direction_* absolute or by degrees

mouse_rig_stop
mouse_rig_sequence
```

**Naming convention:**
- `_to` = set absolute,
- `_by` = relative delta,


See [mouse_rig.py](mouse_rig.py) for full parameters.

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

Already moving right and want a temporary speed boost on hiss?

```python
# Offset adds to the base value and auto-reverts - base state is untouched
rig.speed.offset.add(10).over(200).hold(500).revert(200)

# Override replaces the base value instead of adding
rig.speed.override.to(5).over(200).hold(500).revert(200)
```

Scroll works the same way: `rig.scroll.speed.offset.add(10).over(1000)`

### Layers

Named layers provide isolated, revertible effects calculated after base values.

```python
rig.layer("boost").speed.add(10).over(1000)
rig.layer("slowmo").speed.mul(0.5).over(1000)
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

**Operators:** `.to()`, `.add()` / `.by()`, `.sub()`, `.mul()`, `.div()` — additive and multiplicative cannot be mixed on the same layer

**Lifecycle:** `.over(ms, easing?)`, `.over(rate=X)`, `.hold(ms)`, `.revert(ms?, easing?)`, `.then(callback)`

**Behaviors:** `.stack(max?)`, `.queue()`, `.throttle(ms?)`, `.reset()`

**Easing:** `linear`, `ease_in`, `ease_out`, `ease_in_out`, `ease_in2` … `ease_in_out4`

**Shortcuts:** `rig.stop(ms?)`, `rig.reverse(ms?)`, `rig.bake()`

**State:**

```python
rig.state.pos          # computed (base + all effects)
rig.state.base.speed   # base only
rig.state.layers       # ["sprint", "drift"]
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
