# Mouse Rig - Comprehensive Test Guide

## Overview
The `examples.py` and `examples.talon` files have been completely rewritten to provide comprehensive manual testing coverage for the entire mouse rig system, including the new PRD13 layer system.

## Test Organization (14 Categories)

### 1. **Basic Movement & Direction** (7 tests)
- Basic directional movement (right, left, up, down, diagonal)
- Direction rotation by degrees
- Reverse direction

**Voice Commands:**
- "test move right/left/up/down"
- "test move diagonal"
- "test rotate"
- "test reverse"

### 2. **Speed & Acceleration** (7 tests)
- Set absolute speed
- Add to speed (positive/negative)
- Multiply speed
- Gradual speed changes with `over()`
- Stop (instant and gradual)

**Voice Commands:**
- "test speed set/add/multiply/over"
- "test stop" / "test stop gradual"

### 3. **Layer System - PRD13** (5 tests)
- Basic layer creation
- Layer stacking (multiple layers)
- Layer ordering (execution order)
- Layer lifecycle methods (replace, stack)

**Voice Commands:**
- "test layer basic/stacking/ordering"
- "test layer replace/stack"

### 4. **Phases - Incoming vs Outgoing** (4 tests)
- Incoming phase (modifies input to operations)
- Outgoing phase (modifies output of operations)
- Both phases in same layer
- Multiple layers with different phases

**Voice Commands:**
- "test phase incoming/outgoing/both/sequence"

### 5. **Final Layer** (3 tests)
- Final speed override
- Final direction override
- Final force override

**Voice Commands:**
- "test final speed/direction/force"

### 6. **Override Scope** (2 tests)
- Override speed (replace without stacking)
- Override direction

**Voice Commands:**
- "test override speed/direction"

### 7. **Lifecycle Methods** (4 tests)
- Queue operations
- Extend operation duration
- Throttle rapid changes
- Ignore new operations

**Voice Commands:**
- "test lifecycle queue/extend/throttle/ignore"

### 8. **Behavior Modes** (2 tests)
- Hold value for duration
- Release after duration

**Voice Commands:**
- "test hold" / "test release"

### 9. **Scale - Global Multiplier** (3 tests)
- Set scale
- Add to scale
- Scale in layer

**Voice Commands:**
- "test scale" / "test scale add/layer"

### 10. **Position Control** (2 tests)
- Move to absolute position
- Move by relative amount

**Voice Commands:**
- "test position to/by"

### 11. **Easing & Interpolation** (1 test)
- Easing functions (ease_in_out, etc.)

**Voice Commands:**
- "test easing"

### 12. **State Access & Baking** (2 tests)
- Read current state
- Bake current values

**Voice Commands:**
- "test state read" / "test bake"

### 13. **Error Cases** (3 tests - commented out)
- Base layer with incoming (should error)
- Final layer with incoming (should error)
- User layer mul without phase (should error)

**Note:** These are intentionally commented out as they test error conditions.

### 14. **Real-World Scenarios** (7 tests)
- Sprint mode (3x speed boost)
- Precision mode (30% speed for fine control)
- Acceleration ramp (gradual speedup)
- Drift (smooth turning)
- Rubber band (snap to center)
- Orbit (constant rotation)
- Multi-layer combo (complex layering)

**Voice Commands:**
- "test sprint/precision/acceleration ramp"
- "test drift/rubber band/orbit"
- "test multi layer"

## Legacy Commands

The file also preserves legacy commands for backward compatibility testing:
- "mouse rig turn right/left"
- "mouse rig position center"
- "mouse rig nudge right/down"
- "mouse rig stop smooth"
- "mouse rig bake"
- "mouse rig show state"

## Total Test Coverage

- **49 test functions** covering all major features
- **7 legacy commands** for backward compatibility
- **14 distinct feature categories**
- Tests both **PRD13 features** (layer system) and **existing system** features

## Usage

1. Say any voice command from the categories above
2. Observe the mouse rig behavior
3. Each test is self-contained and demonstrates specific functionality
4. Tests are designed to be run independently

## PRD13 Specific Tests

Tests specifically demonstrating the new layer system:
- Category 3: Layer creation, stacking, ordering
- Category 4: Incoming/outgoing phases
- Category 5: Final layer operations
- Category 6: Override scope
- Category 14: Real-world multi-layer scenarios

## Notes

- All tests use the new `layer()` API (not the old `tag()` API)
- User layers must use `incoming`/`outgoing` for multiplicative operations
- Base and final layers use ordered operations (no phase)
- Layer execution order: base → user layers (by order) → final
