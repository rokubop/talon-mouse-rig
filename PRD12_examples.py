"""PRD12 Examples - Local/World Scope System with Incoming/Outgoing

This file demonstrates the new PRD12 API with local/world scopes and
incoming/outgoing phases for mul operations.
"""

# These examples show the API - they won't run outside of Talon
# Copy them into your Talon voice commands

# ==============================================================================
# BASIC LOCAL layer USAGE
# ==============================================================================

def example_local_additive():
    """Local scope with additive operations (default for layers)"""
    rig = actions.user.mouse_rig()

    # These all default to local scope
    rig.layer("boost").speed.add(5)           # Local additive
    rig.layer("boost").speed.add(3)           # Stacks: total +8

    # Explicit local scope (same as above)
    rig.layer("boost").local.speed.add(5)

def example_local_multiplicative():
    """Local scope with multiplicative operations using incoming/outgoing"""
    rig = actions.user.mouse_rig()

    # mul REQUIRES incoming or outgoing on layers
    rig.layer("boost").local.incoming.speed.mul(2)   # Multiply input before layer's work
    rig.layer("boost").local.outgoing.speed.mul(1.5) # Multiply output after layer's work

def example_mixed_operations():
    """layers can freely mix additive and multiplicative operations!"""
    rig = actions.user.mouse_rig()

    # No more operation mode locking!
    rig.layer("complex").local.incoming.speed.mul(2)   # Pre-multiply
    rig.layer("complex").local.speed.add(5)            # Add
    rig.layer("complex").local.speed.add(3)            # Add more
    rig.layer("complex").local.outgoing.speed.mul(1.5) # Post-multiply

    # Processing: input → *2 → +5 → +3 → *1.5 → output

# ==============================================================================
# SCALE (RETROACTIVE MULTIPLIER)
# ==============================================================================

def example_scale():
    """Scale operations retroactively multiply accumulated values"""
    rig = actions.user.mouse_rig()

    # Scale an additive layer
    rig.layer("boost").speed.add(5)
    rig.layer("boost").speed.add(3)              # Total: +8
    rig.layer("boost").speed.scale(2).over(1000) # Scale to +16

    # Scale with incoming/outgoing
    rig.layer("x").local.incoming.speed.mul(2)   # Pre: *2
    rig.layer("x").local.speed.add(10)           # Add: +10
    rig.layer("x").speed.scale(3)                # Scale the add: +30
    rig.layer("x").local.outgoing.speed.mul(1.5) # Post: *1.5
    # Result: input → *2 → +30 → *1.5

def example_scale_precedence():
    """Last scale wins; layer scales override rig scales"""
    rig = actions.user.mouse_rig()

    # World scale
    rig.world.speed.scale(2)                       # 2x

    # layer world scale overrides
    rig.layer("override").world.speed.scale(3)       # layer wins: 3x not 2x

# ==============================================================================
# WORLD SCOPE
# ==============================================================================

def example_world_operations():
    """World operations work on accumulated global value"""
    rig = actions.user.mouse_rig()

    # Base
    rig.speed(10)

    # Local layers
    rig.layer("boost").local.speed.add(5)    # 10 + 5 = 15
    rig.layer("more").local.speed.add(3)     # 15 + 3 = 18

    # World operations (after all local layers)
    rig.world.speed.add(2)                 # 18 + 2 = 20
    rig.world.speed.scale(2)               # 20 * 2 = 40

    # Final speed: 40

def example_world_position():
    """World position sets absolute coordinates"""
    rig = actions.user.mouse_rig()

    # Local offset
    rig.layer("offset").local.pos.add(50, 0)     # Offset from current

    # World position
    rig.layer("jump").world.pos.to(500, 300)     # Absolute coordinates

# ==============================================================================
# layer ORDERING
# ==============================================================================

def example_explicit_order():
    """Control layer execution order"""
    rig = actions.user.mouse_rig()

    # Explicit order
    rig.layer("first", order=1).local.speed.add(5)
    rig.layer("second", order=2).local.speed.add(3)

    # Subsequent builders on same layer append in original order
    rig.layer("first").local.speed.add(2)  # Appends to "first", keeps order=1

def example_ordered_processing():
    """Multiple ordered layers with incoming/outgoing"""
    rig = actions.user.mouse_rig()

    # Base
    rig.speed(10)

    # layer 1 (order=1)
    rig.layer("first", order=1).local.incoming.speed.mul(2)   # 10 * 2 = 20
    rig.layer("first").local.speed.add(10)                    # 20 + 10 = 30

    # layer 2 (order=2)
    rig.layer("second", order=2).local.speed.add(5)           # 30 + 5 = 35
    rig.layer("second").local.outgoing.speed.mul(0.5)         # 35 * 0.5 = 17.5

    # Final speed: 17.5

# ==============================================================================
# DIFFERENT SCOPES PER PROPERTY
# ==============================================================================

def example_mixed_scopes():
    """Different properties can have different scopes on same layer"""
    rig = actions.user.mouse_rig()

    # One layer affecting multiple properties with different scopes
    rig.layer("gravity").local.direction.add(0, 1)     # Local directional influence
    rig.layer("gravity").local.speed.to(9.8)           # Local speed
    rig.layer("gravity").world.pos.to(0, 500)          # World position (different scope!)

# ==============================================================================
# COMPLEX EXAMPLE
# ==============================================================================

def example_complex_flow():
    """Complex example showing full processing chain"""
    rig = actions.user.mouse_rig()

    # Base movement
    rig.speed(10)
    rig.direction(1, 0)

    # Local layer 1 (order=1)
    rig.layer("boost", order=1).local.incoming.speed.mul(2)   # 10 * 2 = 20
    rig.layer("boost").local.speed.add(5)                     # 20 + 5 = 25
    rig.layer("boost").local.speed.add(3)                     # 25 + 3 = 28
    rig.layer("boost").local.outgoing.speed.mul(1.5)          # 28 * 1.5 = 42

    # Local layer 2 (order=2)
    rig.layer("sprint", order=2).local.incoming.speed.mul(0.5) # 42 * 0.5 = 21
    rig.layer("sprint").local.speed.add(10)                    # 21 + 10 = 31

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
    # rig.layer("boost").relative.speed.add(5)

    # NEW (PRD12):
    rig.layer("boost").local.speed.add(5)      # local replaces relative

    # OLD (PRD11):
    # rig.layer("set").absolute.speed.to(10)

    # NEW (PRD12):
    rig.layer("set").world.speed.to(10)        # world replaces absolute

    # OLD (PRD11):
    # rig.layer("boost").relative.speed.mul(2)  # Required explicit scope

    # NEW (PRD12):
    rig.layer("boost").local.incoming.speed.mul(2)   # Requires incoming/outgoing
    # or
    rig.layer("boost").local.outgoing.speed.mul(2)

    # OLD (PRD11):
    # layers were locked to either mul OR add mode

    # NEW (PRD12):
    # layers can freely mix operations!
    rig.layer("x").local.incoming.speed.mul(2)
    rig.layer("x").local.speed.add(10)
    rig.layer("x").local.outgoing.speed.mul(1.5)
