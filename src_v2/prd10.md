# Mouse Rig V2 - PRD10

## Core Philosophy

**Unity above all else.** The system should have:
- 1 unified builder type (RigBuilder)
- 1 state manager
- 1 queue system
- 1 execution model
- No special cases between "effects" vs "base rig" vs "forces"

All builders follow the same rules. Named builders execute after anonymous builders.

---

## Architecture Overview

### The Universal Builder: RigBuilder

Every fluent chain returns a `RigBuilder`. There are no separate builder types.

```python
# All of these return RigBuilder
rig.pos.by(10, 10)                    # RigBuilder (anonymous)
rig.speed.add(5)                      # RigBuilder (anonymous)
rig.tag("sprint").speed.mul(2)        # RigBuilder (tagged)
rig.stack().speed.add(5)              # RigBuilder (anonymous with behavior)
```

**Execution model:** Builders execute on `__del__` (when Python garbage collects the builder object).

---

## Builder Requirements

Every builder must satisfy:

```
1 Property × 1 Operator × 1 Lifecycle (optional) × (optional) 1 Behavior × (optional) 1 Tag
```

### 1. Property (exactly 1)

Choose one:
- `pos` - Position (x, y)
- `speed` - Speed magnitude
- `direction` - Direction vector/angle
- `accel` - Acceleration magnitude

**Special cases:**
- `rig.reverse()` - shorthand for 180° direction change
- `rig.stop()` - shorthand for speed to 0
- `rig.bake()` - commit all temporary modifications to base

### 2. Operator (exactly 1)

How we're changing the property:

- `.to(value)` - Set absolute value
- `.by(value)` / `.add(value)` - Add delta (aliases)
- `.sub(value)` - Subtract delta
- `.mul(value)` - Multiply by factor
- `.div(value)` - Divide by divisor

**Shorthand:** For anonymous (untagged) builders only, you can use:
```python
rig.speed(5)           # Shorthand for rig.speed.to(5)
rig.direction(1, 0)    # Shorthand for rig.direction.to(1, 0)
```

Tagged builders **must** use explicit operators:
```python
rig.tag("x").speed.to(5)     # ✅ Explicit required
rig.tag("x").speed(5)        # ❌ Error - no shorthand for tagged
```

### 3. Lifecycle (optional timing)

Control how the change happens over time:

- `.over(ms, easing?)` - Transition/fade in over duration (optional, default instant)
- `.over(rate=X)` - Transition at a specific rate (alternative to time-based)
- `.hold(ms)` - Sustain the effect for duration (optional)
- `.revert(ms?, easing?)` - Fade out/restore (optional)
- `.revert(rate=X)` - Fade out at a specific rate (alternative to time-based)
- `.then(callback)` - Execute callback after current stage (can be used multiple times between each stage, and at the end)

**Lifecycle order:** `over` → `then`* → `hold` → `then`* → `revert` → `then`*

**Rules:**
- Maximum 1 `.over()` per statement
- Maximum 1 `.hold()` per statement
- Maximum 1 `.revert()` per statement
- Unlimited `.then()` callbacks (execute at current lifecycle stage)
- Order is enforced: must call in sequence

**Time-based vs Rate-based:**

**Time-based** (duration in milliseconds):
```python
rig.speed.to(10).over(500)              # Transition over 500ms
rig.speed.add(5).over(300).revert(500)  # Different in/out durations
```

**Rate-based** (units per second):
```python
# Speed/Accel: rate = units/second
rig.speed.to(10).over(rate=5)           # Ramp speed at 5 units/sec
                                         # Duration auto-calculated from delta

# Direction: rate = degrees/second
rig.direction.by(90).over(rate=45)      # Rotate at 45°/sec
                                         # Takes 2 seconds to rotate 90°

# Position: rate = pixels/second
rig.pos.to(100, 100).over(rate=50)      # Move at 50 pixels/sec
                                         # Duration calculated from distance
```

**Rate calculations:**
- Speed/Accel: `duration = |target - current| / rate`
- Direction: `duration = |angle_delta| / rate`
- Position: `duration = distance(current, target) / rate`

**Examples:**
```python
# Instant (no lifecycle)
rig.speed.to(10)

# Time-based transition
rig.speed.to(10).over(500)

# Rate-based transition
rig.speed.to(10).over(rate=5)           # Ramp at 5 units/sec

# Temporary effect (time-based)
rig.speed.add(5).hold(2000)

# Full lifecycle (time-based)
rig.speed.add(5).over(300).hold(2000).revert(500)

# Full lifecycle (rate-based)
rig.speed.add(5).over(rate=10).hold(2000).revert(rate=5)

# Mixed (time in, rate out)
rig.speed.to(20).over(500).hold(1000).revert(rate=10)

# Direction with rate
rig.direction.by(180).over(rate=90)     # Turn 180° at 90°/sec (2 seconds)
rig.direction.by(90).over(rate=45)      # Turn 90° at 45°/sec (2 seconds)

# Position with rate
rig.pos.to(960, 540).over(rate=200)     # Move at 200 pixels/sec

# With callbacks
rig.speed.add(5)\
    .over(300).then(lambda: print("ramped up"))\
    .hold(2000).then(lambda: print("holding"))\
    .revert(500).then(lambda: print("done"))
```

### 4. Behavior (optional, 0-1)

What happens if the same statement is triggered again while active?

- `.replace()` - Cancel previous, start new (default for tagged)
- `.stack(max?)` - Stack effects (unlimited or with max count)
- `.queue()` - Queue for execution after current completes
- `.extend()` - Extend hold duration
- `.throttle(ms)` - Ignore if active, or rate limit if ms specified
All can be called as a attribute or a call:
```python
rig.stack()          # Call
rig.stack.pos.add(5)  # Attribute
```

**Default behaviors:**
- Anonymous (untagged): `.stack()` with unlimited stacks
- Tagged: `.stack()`  with unlimited stacks

**Examples:**
```python
# Stack unlimited
rig.tag("boost").speed.add(5).stack()

# Stack max 3
rig.tag("boost").speed.add(5).stack(3)

# Replace (cancel previous)
rig.tag("sprint").speed.mul(2).replace()
rig.tag("sprint").replace.speed.mul(2)
rig.replace.speed(4)

# Queue (wait for current to finish)
rig.tag("combo").speed.add(10).queue()
rig.tag("combo").queue.speed.add(10)

rig.queue.pos.to(100, 100).over(500) # probably doesn't actually queue anywhere because the tag is anonymous and/or a uid, so just executes immediately
rig.queue.pos.to(200, 200).over(500) # probably doesn't actually queue anywhere because the tag is anonymous and/or a uid, so just executes immediately

# Throttle (ignore rapid calls)
rig.tag("dash").speed.add(20).throttle(500)
rig.tag("dash").throttle.speed.add(20)
```

### 5. Tag (optional, 0-1)

Name the statement for:
- Identity (to stop/revert later)
- Controlling repeat behavior
- Execution ordering (tagged runs after anonymous)

```python
# Anonymous - no tag
rig.speed.add(5)

# Tagged
rig.tag("sprint").speed.mul(2)
```

**Tag operations:**
```python
# Revert a tag (fade out)
rig.tag("sprint").revert(500)

# Stop immediately
rig.tag("sprint").revert()
```

### 6. Bake (optional, 0-1)

Controls whether changes persist into base rig state or remain reversible.

**Defaults:**
- Anonymous builders: `bake=true` (changes become permanent)
- Tagged builders: `bake=false` (changes are reversible)

**Explicit control:**
```python
# Anonymous but don't bake (keep reversible)
rig.speed.to(10).bake(false)

# Tagged but bake (make permanent)
rig.tag("boost").speed.add(5).bake(true)
```

**Baking semantics:**
- `bake=true`: After lifecycle completes, values merge into base state
- `bake=false`: Values remain in a layer, can be reverted with `.tag("name").revert()`

---

## Order-Agnostic Fluent API

All builder methods can be called in any order (with some logical constraints):

```python
# All equivalent
rig.speed.add(5).over(300)
rig.speed.add(5).tag("boost").over(300)
rig.tag("boost").speed.add(5).over(300)
rig.over(300).speed.add(5).tag("boost")  # ✅ Works!
rig.stack().speed.add(5).tag("boost").over(300)

# Lifecycle must be ordered
rig.speed.add(5).over(300).hold(1000).revert(500)  # ✅
rig.speed.add(5).revert(500).over(300)             # ❌ Error
```

**Implementation strategy:** Builder collects all calls, validates and executes on `__del__`.

---

## Execution Model

### When Statements Execute

Statements execute when the Python object is garbage collected (`__del__`).

```python
def my_action():
    rig = actions.user.mouse_rig()
    rig.speed.add(5).over(300)
    # Statement executes here when rig.speed.add(5).over(300) goes out of scope
```

### Execution Order

1. **Anonymous statements** execute first (in order of `__del__` calls)
2. **Tagged statements** execute after all anonymous statements

This ensures base modifications happen before named effects apply.

---

## State Management

### Single Unified State

```python
class RigState:
    # Base state (baked values)
    _base_pos: Vec2
    _base_speed: float
    _base_direction: Vec2
    _base_accel: float

    # Active statements (layers)
    _statements: dict[str, Statement]  # tag_name -> Statement
    _anonymous_statements: list[Statement]  # Order matters

    # Queue system (unified)
    _queues: dict[str, list[Statement]]  # tag_name -> queued statements

    # Frame loop
    _cron_job: Optional[CronJob]
    _last_frame_time: float
```

### State Access

```python
# Read current computed state
rig.state.speed        # Computed: base + all active modifications
rig.state.direction    # Computed direction
rig.state.pos          # Current position
rig.state.accel        # Computed acceleration

# Read base state only
rig.base.speed         # Base speed (baked values only)
rig.base.direction     # Base direction
```

---

## Property-Specific Behaviors

### Position

```python
# Absolute positioning
rig.pos.to(960, 540).over(1000)

# Relative positioning (offset from current)
rig.pos.by(100, 50).over(500)

# Temporary offset (returns to original)
rig.pos.by(10, 10).over(300).hold(2000).revert(300)
```

### Speed

```python
# Set speed
rig.speed.to(10)
rig.speed(10)  # Shorthand (anonymous only)

# Modify speed
rig.speed.add(5)
rig.speed.mul(2)
rig.speed.div(2)

# Temporary boost
rig.speed.add(10).hold(2000)
```

### Direction

Direction can be set as:
- Vector: `(x, y)`
- Angle delta: `.by(degrees)`

```python
# Absolute direction (vector)
rig.direction.to(1, 0)        # Right
rig.direction(1, 0)           # Shorthand

# Relative rotation (degrees)
rig.direction.by(90)          # Turn 90° clockwise
rig.direction.by(-90)         # Turn 90° counter-clockwise

# Smooth turn
rig.direction.by(90).over(500, "ease_in_out")

# Reverse (special case - 180° turn)
rig.reverse()
rig.reverse().over(1000)      # Smooth reverse
```

### Acceleration

```python
# Set acceleration
rig.accel.to(5)
rig.accel(5)  # Shorthand

# Temporary acceleration burst
rig.accel.add(10).hold(1000)
```

---

## Examples

### Basic Movement

```python
# Start moving right
rig.direction(1, 0)
rig.speed(5)

# Stop
rig.stop()
rig.stop(1000)  # Smooth stop over 1 second
```

### Temporary Effects

```python
# Speed boost (anonymous - auto-stacks)
rig.speed.add(10).hold(2000)

# Named sprint (replaces on repeat)
rig.tag("sprint").speed.mul(2).over(500).hold(3000).revert(500)
```

### Stacking

```python
# Unlimited stacking (default for anonymous)
rig.speed.add(5)
rig.speed.add(5)  # Now +10 total

# Limited stacking
rig.tag("rage").speed.mul(1.2).stack(5)
```

### Queuing

```python
# Queue operations
rig.tag("combo").speed.to(10).over(500).queue()
rig.tag("combo").speed.to(20).over(500).queue()
# Second waits for first to complete
```

### Complex Lifecycle

```python
rig.pos.by(10, 10).over(400)\
    .then(lambda: print("moved"))\
    .hold(2000)\
    .then(lambda: print("holding"))\
    .then(lambda: print("hello"))\
    .revert(400)\
    .then(lambda: print("reverted"))
```

### Baking Control

```python
# Permanent speed increase
rig.speed.add(5).bake(true)

# Temporary named effect (can revert later)
rig.tag("boost").speed.add(10).bake(false)
rig.tag("boost").revert(500)  # Remove it
```

---

## API Reference

### Rig Entry Points

```python
rig = actions.user.mouse_rig()

# Property accessors (return RigStatement)
rig.pos          # Position builder
rig.speed        # Speed builder
rig.direction    # Direction builder
rig.accel        # Accel builder

# Tag accessor
rig.tag(name)    # Tagged statement builder

# Behavior sugar (sets default behavior)
rig.stack(max?)       # Stack behavior
rig.replace()         # Replace behavior
rig.queue()           # Queue behavior
rig.throttle(ms)      # Throttle behavior
rig.extend()          # Extend behavior
rig.ignore()          # Ignore behavior

# Special operations
rig.reverse()         # 180° turn
rig.stop(ms?)         # Stop (speed to 0)
rig.bake()            # Commit all temporary to base
rig.state             # Read computed state
rig.base              # Read base state only
```

### RigBuilder Methods

**Operators:**
- `.to(value)` - Set absolute
- `.by(value)` / `.add(value)` - Add delta
- `.sub(value)` - Subtract
- `.mul(value)` - Multiply
- `.div(value)` - Divide

**Lifecycle:**
- `.over(ms, easing?)` - Transition duration
- `.hold(ms)` - Hold duration
- `.revert(ms?, easing?)` - Revert duration
- `.then(callback)` - Callback after current stage

**Behavior:**
- `.stack(max?)` - Stack (unlimited or max)
- `.replace()` - Replace previous
- `.queue()` - Queue after current
- `.extend()` - Extend hold duration
- `.throttle(ms)` - Rate limit
- `.ignore()` - Ignore while active

**Identity:**
- `.tag(name)` - Name the statement
- `.bake(bool)` - Control persistence

---

## Implementation Notes

### Builder Pattern

```python
class RigBuilder:
    """Universal builder - all methods return self for chaining"""

    def __init__(self, rig_state: RigState):
        self.rig_state = rig_state

        # Builder configuration (collected via fluent calls)
        self.property: Optional[str] = None  # pos, speed, direction, accel
        self.operator: Optional[str] = None  # to, by, add, sub, mul, div
        self.value: Any = None

        self.tag_name: Optional[str] = None
        self.behavior: Optional[str] = None
        self.behavior_args: tuple = ()

        self.over_ms: Optional[float] = None
        self.over_easing: str = "linear"
        self.hold_ms: Optional[float] = None
        self.revert_ms: Optional[float] = None
        self.revert_easing: str = "linear"

        self.then_callbacks: list[tuple[str, Callable]] = []  # (stage, callback)
        self.bake_value: Optional[bool] = None

    def __del__(self):
        """Execute on garbage collection"""
        self._validate()
        self._execute()

    def _validate(self):
        """Ensure builder is valid before execution"""
        # Must have property and operator
        # Lifecycle order must be correct
        # etc.
        pass

    def _execute(self):
        """Submit builder to RigState for execution"""
        # Determine if anonymous or tagged
        # Apply default bake behavior
        # Queue or execute immediately
        pass
```### Property Builders

Internally, property builders can be thin wrappers that configure the statement:

```python
class PropertyBuilder:
    def __init__(self, rig_state: RigState, property_name: str):
        self.rig_state = rig_state
        self.property_name = property_name

    def to(self, *args) -> RigBuilder:
        builder = RigBuilder(self.rig_state)
        builder.property = self.property_name
        builder.operator = "to"
        builder.value = args
        return builder

    def add(self, *args) -> RigBuilder:
        builder = RigBuilder(self.rig_state)
        builder.property = self.property_name
        builder.operator = "add"
        builder.value = args
        return builder

    # ... etc
```### Execution Flow

```
1. User writes: rig.speed.add(5).over(300)
2. Python creates: PropertyBuilder("speed").add(5) -> RigBuilder
3. Call: RigBuilder.over(300) -> returns self
4. Builder goes out of scope
5. __del__ called
6. Builder validates and executes
7. RigState processes:
   - Is it tagged? No -> execute as anonymous
   - Default bake? Yes (anonymous) -> will merge to base after
   - Create animation/lifecycle
   - Start frame loop if needed
```

---

## Implementation Strategy: Learn from V1, Rebuild Core

**Core principle:** V2 redesigns both API *and* core architecture. Unity and simplicity over backward compatibility.

### Reuse from V1 (Low-level utilities only)

The following low-level components are proven and should be reused as-is:

1. **Mouse Movement Primitives** (`src/core.py`):
   - Mouse movement API with platform detection (Talon vs Windows raw input)
   - **SubpixelAdjuster** - critical for smooth small movements
   - EPSILON constant for float comparisons

2. **Math Utilities** (`src/core.py`):
   - Vec2 class with operations (normalized, magnitude, dot product, etc.)
   - Easing functions: linear, ease_in, ease_out, ease_in_out, smoothstep
   - Lerp function

3. **Rate Calculation Logic** (`src/builders/rate_utils.py`):
   - Duration calculation from rate (speed, accel, rotation, position)
   - Rate parameter validation

### Completely Redesign (Core Architecture)

These must be rebuilt from scratch with V2's unified philosophy:

1. **State Management** (`src/state.py` → `src_v2/state.py`):
   - **Old:** Multiple lists (`_effects`, `_effect_stacks`, `_effect_lifecycles`, `_direction_effects`, `_position_effects`, `_named_forces`)
   - **New:** Single unified structure: `base` + `active_builders` + `queues`
   - Simplified composition: iterate active builders, apply to base

2. **Builder System** (`src/builders/` → `src_v2/builder.py`):
   - **Old:** Hierarchy of EffectBuilder, SpeedBuilder, DirectionBuilder, multiple mixins
   - **New:** Single `RigBuilder` class with property-specific logic inside
   - No inheritance complexity, just one class handling all cases

3. **Lifecycle/Animation** (`src/effects.py` + `src/core.py` transitions → `src_v2/lifecycle.py`):
   - **Old:** Separate Effect, EffectLifecycle, EffectStack, Transition classes
   - **New:** Single Lifecycle manager per builder
   - Unified progress tracking (over/hold/revert phases)

4. **Queue System** (`src/state.py` segments → `src_v2/queue.py`):
   - **Old:** Split between `_segment_queues` and effect lifecycle queuing
   - **New:** Single queue implementation used by all behaviors

5. **Frame Loop** (`src/state.py` → `src_v2/state.py`):
   - **Old:** Complex update cycle checking multiple effect lists and transitions
   - **New:** Simple loop: update all active builders, compute final values, move mouse
   - Single `_update_frame()` method, not scattered logic

### Critical: SubpixelAdjuster

The SubpixelAdjuster from V1 **must** be used in V2:

```python
class SubpixelAdjuster:
    """
    Accumulates fractional pixel movements to prevent rounding errors.

    When moving the mouse in small increments (e.g., 0.3 pixels per frame),
    naive int() conversion would lose the fractional part each frame,
    causing the mouse to drift from its intended path.
    """
```

Without this, slow movements or rate-based animations will drift off course.

### File Structure

```
src_v2/
  __init__.py
  contracts.py       # Single file with all interfaces/protocols
  builder.py         # RigBuilder (the universal builder)
  state.py           # RigState (unified state management)
  lifecycle.py       # Lifecycle management (over/hold/revert)
  queue.py           # Queue system (for behavior modes)
  core.py            # Math/easing/Vec2/SubpixelAdjuster (copied from V1)
  rate_utils.py      # Rate calculations (copied from V1)
```

**Key principle:** `contracts.py` defines all interfaces. Other files implement them.

### contracts.py - Single Source of Truth

All protocols and interfaces in one place:

```python
"""Type contracts and protocols for mouse rig V2"""

from typing import Protocol, Optional, Any
from abc import ABC, abstractmethod

class PropertyOperations(Protocol):
    """Contract for property operations (to, add, sub, mul, div)"""
    def to(self, value: Any) -> 'RigBuilder': ...
    def add(self, value: Any) -> 'RigBuilder': ...
    def by(self, value: Any) -> 'RigBuilder': ...  # alias for add
    def sub(self, value: Any) -> 'RigBuilder': ...
    def mul(self, value: float) -> 'RigBuilder': ...
    def div(self, value: float) -> 'RigBuilder': ...

class LifecycleMethods(Protocol):
    """Contract for lifecycle methods (over, hold, revert, then)"""
    def over(self, ms: Optional[float] = None, easing: str = "linear", *, rate: Optional[float] = None) -> 'RigBuilder': ...
    def hold(self, ms: float) -> 'RigBuilder': ...
    def revert(self, ms: Optional[float] = None, easing: str = "linear", *, rate: Optional[float] = None) -> 'RigBuilder': ...
    def then(self, callback: Callable) -> 'RigBuilder': ...

class BehaviorMethods(Protocol):
    """Contract for behavior modes (stack, replace, queue, etc.)"""
    def stack(self, max_count: Optional[int] = None) -> 'RigBuilder': ...
    def replace(self) -> 'RigBuilder': ...
    def queue(self) -> 'RigBuilder': ...
    def extend(self) -> 'RigBuilder': ...
    def throttle(self, ms: float) -> 'RigBuilder': ...
    def ignore(self) -> 'RigBuilder': ...

class Updatable(ABC):
    """Interface for objects that update each frame"""
    @abstractmethod
    def update(self, dt: float) -> bool:
        """Update state. Returns True if still active, False if complete."""
        pass

# ... etc
```

### Migration Philosophy

- **Don't port complexity:** If V1 code is complex due to the split architecture, simplify in V2
- **Question everything:** Just because V1 does it doesn't mean V2 should
- **Favor composition over inheritance:** V1 used mixins heavily, V2 uses simple composition
- **Single responsibility:** Each file/class has one clear job

---

## Open Questions / Future Considerations

1. **Force system**: Do we keep the separate force concept, or unify it?
   - Current thinking: Forces are just tagged builders with vector addition

2. **Layer system**: Do we need explicit layers, or is tag + bake enough?
   - Current thinking: Tag + bake is sufficient for v2

3. **Multi-segment chaining**: Should we support chaining multiple operations?
   ```python
   rig.speed.to(10).over(500).to(20).over(500)  # Two sequential changes?
   ```
   - Current thinking: Defer to later if needed

---

## Success Criteria

✅ Single unified builder type (RigBuilder)
✅ No distinction between "effects" and "base rig" in API
✅ Order-agnostic fluent API (except lifecycle order)
✅ Clean execution model (del-based)
✅ Simple state management (base + active builders)
✅ Behavior system works for all builders
✅ Bake system provides control over persistence
✅ All examples from current system work in new system
✅ Leverage V1's proven movement implementation (frame loop, transitions, subpixel adjuster)
