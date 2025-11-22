"""PRD12 Quick Reference Card

A concise reference for the new local/world scope system.
"""

# ==============================================================================
# SCOPE SYSTEM
# ==============================================================================

# LOCAL SCOPE (default for tags)
rig.tag("name").local.speed.add(5)       # Tag's own contribution
rig.tag("name").speed.add(5)             # Defaults to local

# WORLD SCOPE
rig.world.speed.add(5)                   # Accumulated global value
rig.tag("name").world.speed.to(10)       # Operate on world

# ==============================================================================
# PHASE SYSTEM (for mul operations)
# ==============================================================================

# INCOMING (pre-process)
rig.tag("name").local.incoming.speed.mul(2)     # Multiply input before tag's work

# OUTGOING (post-process)
rig.tag("name").local.outgoing.speed.mul(1.5)   # Multiply output after tag's work

# WORLD MUL (no phase needed)
rig.world.speed.mul(2)                          # World mul doesn't need phase

# ==============================================================================
# OPERATIONS
# ==============================================================================

# ADDITIVE (can stack freely)
.add(value)      # Add delta
.by(value)       # Alias for add
.sub(value)      # Subtract delta
.to(value)       # Set absolute value

# MULTIPLICATIVE (requires incoming/outgoing on tags)
.mul(value)      # Multiply (needs incoming/outgoing for tags)
.div(value)      # Divide

# RETROACTIVE
.scale(value)    # Retroactive multiplier (last one wins)

# ==============================================================================
# TAG ORDERING
# ==============================================================================

rig.tag("first", order=1).speed.add(5)   # Execute first
rig.tag("second", order=2).speed.add(3)  # Execute second
rig.tag("third").speed.add(1)            # No order = executes last

# ==============================================================================
# MIXING OPERATIONS (New in PRD12!)
# ==============================================================================

# Tags can now freely mix additive and multiplicative operations
rig.tag("complex").local.incoming.speed.mul(2)    # Pre-multiply
rig.tag("complex").local.speed.add(10)            # Add
rig.tag("complex").local.speed.add(5)             # Add more
rig.tag("complex").speed.scale(2)                 # Scale the adds
rig.tag("complex").local.outgoing.speed.mul(1.5)  # Post-multiply

# Processing: input → *2 → +30 (10+5 scaled by 2) → *1.5

# ==============================================================================
# COMPUTATION ORDER
# ==============================================================================

# 1. Base values
# 2. Local tags (in order):
#    - incoming muls
#    - local operations (add/sub/by/to)
#    - scale
#    - outgoing muls
# 3. World operations
# 4. World scale (if no tag world scales)

# ==============================================================================
# COMMON PATTERNS
# ==============================================================================

# Simple boost
rig.tag("boost").speed.add(10)

# Multiplicative boost
rig.tag("boost").local.incoming.speed.mul(2)

# Complex effect
rig.tag("effect").local.incoming.speed.mul(0.5)
rig.tag("effect").local.speed.add(20)
rig.tag("effect").local.outgoing.speed.mul(2)

# Scaled effect
rig.tag("effect").speed.add(5)
rig.tag("effect").speed.add(3)
rig.tag("effect").speed.scale(2)  # Total: +16 instead of +8

# World override
rig.world.speed.to(50)  # Override to absolute value

# Multi-property tag
rig.tag("gravity").local.direction.add(0, 1)
rig.tag("gravity").local.speed.to(9.8)

# Ordered tags
rig.tag("base", order=1).speed.add(10)
rig.tag("boost", order=2).local.incoming.speed.mul(2)
rig.tag("cap", order=3).world.speed.to(100)  # Cap at 100

# ==============================================================================
# VALIDATION RULES
# ==============================================================================

# ✓ Valid: mul with incoming/outgoing on tag
rig.tag("x").local.incoming.speed.mul(2)
rig.tag("x").local.outgoing.speed.mul(2)

# ✓ Valid: mul without phase on world
rig.world.speed.mul(2)

# ✗ Invalid: mul without phase on tag
# rig.tag("x").local.speed.mul(2)  # ERROR: requires incoming/outgoing

# ✓ Valid: mix operations
rig.tag("x").local.incoming.speed.mul(2)
rig.tag("x").local.speed.add(10)

# ✓ Valid: different scopes per property
rig.tag("x").local.speed.add(5)
rig.tag("x").world.pos.to(100, 100)

# ✗ Invalid: different scopes for same property
# rig.tag("x").local.speed.add(5)
# rig.tag("x").world.speed.add(10)  # ERROR: scope mismatch

# ==============================================================================
# MIGRATION FROM PRD11
# ==============================================================================

# PRD11 → PRD12

# .relative → .local
# Before: rig.tag("x").relative.speed.add(5)
# After:  rig.tag("x").local.speed.add(5)

# .absolute → .world
# Before: rig.tag("x").absolute.speed.to(10)
# After:  rig.tag("x").world.speed.to(10)

# mul now requires phase
# Before: rig.tag("x").relative.speed.mul(2)
# After:  rig.tag("x").local.incoming.speed.mul(2)  # or .outgoing

# No more operation locking!
# Before: Tags could ONLY use mul OR add
# After:  Tags can freely mix mul and add!
