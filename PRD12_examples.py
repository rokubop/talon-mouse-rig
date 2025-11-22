"""PRD12 Examples - Local/World Scope System with Incoming/Outgoing

This file demonstrates the new PRD12 API with local/world scopes and
incoming/outgoing phases for mul operations.
"""

# These examples show the API - they won't run outside of Talon
# Copy them into your Talon voice commands

# ==============================================================================
# BASIC LOCAL TAG USAGE
# ==============================================================================

def example_local_additive():
    """Local scope with additive operations (default for tags)"""
    rig = actions.user.mouse_rig()

    # These all default to local scope
    rig.tag("boost").speed.add(5)           # Local additive
    rig.tag("boost").speed.add(3)           # Stacks: total +8

    # Explicit local scope (same as above)
    rig.tag("boost").local.speed.add(5)

def example_local_multiplicative():
    """Local scope with multiplicative operations using incoming/outgoing"""
    rig = actions.user.mouse_rig()

    # mul REQUIRES incoming or outgoing on tags
    rig.tag("boost").local.incoming.speed.mul(2)   # Multiply input before tag's work
    rig.tag("boost").local.outgoing.speed.mul(1.5) # Multiply output after tag's work

def example_mixed_operations():
    """Tags can freely mix additive and multiplicative operations!"""
    rig = actions.user.mouse_rig()

    # No more operation mode locking!
    rig.tag("complex").local.incoming.speed.mul(2)   # Pre-multiply
    rig.tag("complex").local.speed.add(5)            # Add
    rig.tag("complex").local.speed.add(3)            # Add more
    rig.tag("complex").local.outgoing.speed.mul(1.5) # Post-multiply

    # Processing: input → *2 → +5 → +3 → *1.5 → output

# ==============================================================================
# SCALE (RETROACTIVE MULTIPLIER)
# ==============================================================================

def example_scale():
    """Scale operations retroactively multiply accumulated values"""
    rig = actions.user.mouse_rig()

    # Scale an additive tag
    rig.tag("boost").speed.add(5)
    rig.tag("boost").speed.add(3)              # Total: +8
    rig.tag("boost").speed.scale(2).over(1000) # Scale to +16

    # Scale with incoming/outgoing
    rig.tag("x").local.incoming.speed.mul(2)   # Pre: *2
    rig.tag("x").local.speed.add(10)           # Add: +10
    rig.tag("x").speed.scale(3)                # Scale the add: +30
    rig.tag("x").local.outgoing.speed.mul(1.5) # Post: *1.5
    # Result: input → *2 → +30 → *1.5

def example_scale_precedence():
    """Last scale wins; tag scales override rig scales"""
    rig = actions.user.mouse_rig()

    # World scale
    rig.world.speed.scale(2)                       # 2x

    # Tag world scale overrides
    rig.tag("override").world.speed.scale(3)       # Tag wins: 3x not 2x

# ==============================================================================
# WORLD SCOPE
# ==============================================================================

def example_world_operations():
    """World operations work on accumulated global value"""
    rig = actions.user.mouse_rig()

    # Base
    rig.speed(10)

    # Local tags
    rig.tag("boost").local.speed.add(5)    # 10 + 5 = 15
    rig.tag("more").local.speed.add(3)     # 15 + 3 = 18

    # World operations (after all local tags)
    rig.world.speed.add(2)                 # 18 + 2 = 20
    rig.world.speed.scale(2)               # 20 * 2 = 40

    # Final speed: 40

def example_world_position():
    """World position sets absolute coordinates"""
    rig = actions.user.mouse_rig()

    # Local offset
    rig.tag("offset").local.pos.add(50, 0)     # Offset from current

    # World position
    rig.tag("jump").world.pos.to(500, 300)     # Absolute coordinates

# ==============================================================================
# TAG ORDERING
# ==============================================================================

def example_explicit_order():
    """Control tag execution order"""
    rig = actions.user.mouse_rig()

    # Explicit order
    rig.tag("first", order=1).local.speed.add(5)
    rig.tag("second", order=2).local.speed.add(3)

    # Subsequent builders on same tag append in original order
    rig.tag("first").local.speed.add(2)  # Appends to "first", keeps order=1

def example_ordered_processing():
    """Multiple ordered tags with incoming/outgoing"""
    rig = actions.user.mouse_rig()

    # Base
    rig.speed(10)

    # Tag 1 (order=1)
    rig.tag("first", order=1).local.incoming.speed.mul(2)   # 10 * 2 = 20
    rig.tag("first").local.speed.add(10)                    # 20 + 10 = 30

    # Tag 2 (order=2)
    rig.tag("second", order=2).local.speed.add(5)           # 30 + 5 = 35
    rig.tag("second").local.outgoing.speed.mul(0.5)         # 35 * 0.5 = 17.5

    # Final speed: 17.5

# ==============================================================================
# DIFFERENT SCOPES PER PROPERTY
# ==============================================================================

def example_mixed_scopes():
    """Different properties can have different scopes on same tag"""
    rig = actions.user.mouse_rig()

    # One tag affecting multiple properties with different scopes
    rig.tag("gravity").local.direction.add(0, 1)     # Local directional influence
    rig.tag("gravity").local.speed.to(9.8)           # Local speed
    rig.tag("gravity").world.pos.to(0, 500)          # World position (different scope!)

# ==============================================================================
# COMPLEX EXAMPLE
# ==============================================================================

def example_complex_flow():
    """Complex example showing full processing chain"""
    rig = actions.user.mouse_rig()

    # Base movement
    rig.speed(10)
    rig.direction(1, 0)

    # Local Tag 1 (order=1)
    rig.tag("boost", order=1).local.incoming.speed.mul(2)   # 10 * 2 = 20
    rig.tag("boost").local.speed.add(5)                     # 20 + 5 = 25
    rig.tag("boost").local.speed.add(3)                     # 25 + 3 = 28
    rig.tag("boost").local.outgoing.speed.mul(1.5)          # 28 * 1.5 = 42

    # Local Tag 2 (order=2)
    rig.tag("sprint", order=2).local.incoming.speed.mul(0.5) # 42 * 0.5 = 21
    rig.tag("sprint").local.speed.add(10)                    # 21 + 10 = 31

    # World operations
    rig.world.speed.add(5)                            # 31 + 5 = 36
    rig.world.speed.scale(2)                          # 36 * 2 = 72

    # Final speed = 72

# ==============================================================================
# MIGRATION FROM OLD API
# ==============================================================================

def migration_examples():
    """How to migrate from relative/absolute to local/world"""
    rig = actions.user.mouse_rig()

    # OLD (PRD11):
    # rig.tag("boost").relative.speed.add(5)

    # NEW (PRD12):
    rig.tag("boost").local.speed.add(5)      # local replaces relative

    # OLD (PRD11):
    # rig.tag("set").absolute.speed.to(10)

    # NEW (PRD12):
    rig.tag("set").world.speed.to(10)        # world replaces absolute

    # OLD (PRD11):
    # rig.tag("boost").relative.speed.mul(2)  # Required explicit scope

    # NEW (PRD12):
    rig.tag("boost").local.incoming.speed.mul(2)   # Requires incoming/outgoing
    # or
    rig.tag("boost").local.outgoing.speed.mul(2)

    # OLD (PRD11):
    # Tags were locked to either mul OR add mode

    # NEW (PRD12):
    # Tags can freely mix operations!
    rig.tag("x").local.incoming.speed.mul(2)
    rig.tag("x").local.speed.add(10)
    rig.tag("x").local.outgoing.speed.mul(1.5)
