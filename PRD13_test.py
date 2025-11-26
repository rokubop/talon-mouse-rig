"""PRD13 Test - Verify layer system examples from PRD13_layer_system.md"""

# Example 1: Simple Layering
def test_simple_layering():
    """
    Base: rig.speed.to(10)
    User layer: rig.layer("boost").speed.add(20)  # 10 + 20 = 30
    User layer: rig.layer("more").speed.add(10)   # 30 + 10 = 40
    Final: rig.final.speed.add(5)                 # 40 + 5 = 45
    Final: rig.final.speed.mul(2)                 # 45 × 2 = 90
    Result: 90
    """
    print("Test 1: Simple Layering")
    # Would execute: rig.speed.to(10)
    # rig.layer("boost").speed.add(20)
    # rig.layer("more").speed.add(10)
    # rig.final.speed.add(5)
    # rig.final.speed.mul(2)
    print("Expected: 90")


# Example 2: Incoming/Outgoing Processing
def test_incoming_outgoing():
    """
    Base: rig.speed.to(10), rig.speed.mul(2)  # 10 × 2 = 20
    Layer 1:
      incoming: 20 × 1.5 = 30
      operation: 30 + 10 = 40
      outgoing: 40 × 2 = 80
    Layer 2:
      incoming: 80 × 0.5 = 40
      override: to 50 (ignore 40)
    Final: 50 + 10 = 60
    Result: 60
    """
    print("\nTest 2: Incoming/Outgoing Processing")
    # rig.speed.to(10)
    # rig.speed.mul(2)
    # rig.layer("boost", order=1).incoming.speed.mul(1.5)
    # rig.layer("boost").speed.add(10)
    # rig.layer("boost").outgoing.speed.mul(2)
    # rig.layer("cap", order=2).incoming.speed.mul(0.5)
    # rig.layer("cap").override.speed.to(50)
    # rig.final.speed.add(10)
    print("Expected: 60")


# Example 3: Base and Final Operations
def test_base_and_final():
    """
    Base: to(100), mul(2) = 200
    Layer: incoming(×2)=400, add(50)=450
    Final: add(10)=460, mul(0.8)=368
    """
    print("\nTest 3: Base and Final Operations")
    # rig.speed.to(100)
    # rig.speed.mul(2)  # 200
    # rig.layer("sprint").incoming.speed.mul(2)  # 400
    # rig.layer("sprint").speed.add(50)  # 450
    # rig.final.speed.add(10)  # 460
    # rig.final.speed.mul(0.8)  # 368
    print("Expected: 368")


# Example 4: Complex Multi-Layer
def test_complex_multi_layer():
    """
    Base: to(10), mul(2) = 20
    Layer 1 (boost):
      incoming: 20 × 2 = 40
      add(5): 40 + 5 = 45
      add(3): 45 + 3 = 48
      scale(2): (5+3)×2 = 16, total: 40 + 16 = 56
      outgoing: 56 × 1.5 = 84
    Layer 2 (sprint):
      incoming: 84 × 0.5 = 42
      add(10): 42 + 10 = 52
    Final: add(5)=57, mul(2)=114
    """
    print("\nTest 4: Complex Multi-Layer")
    # rig.speed.to(10)
    # rig.speed.mul(2)
    # rig.layer("boost", order=1).incoming.speed.mul(2)
    # rig.layer("boost").speed.add(5)
    # rig.layer("boost").speed.add(3)
    # rig.layer("boost").speed.scale(2)
    # rig.layer("boost").outgoing.speed.mul(1.5)
    # rig.layer("sprint", order=2).incoming.speed.mul(0.5)
    # rig.layer("sprint").speed.add(10)
    # rig.final.speed.add(5)
    # rig.final.speed.mul(2)
    print("Expected: 114")


# API Examples
def test_api_examples():
    """Test various API patterns from PRD13"""
    print("\nTest 5: API Examples")

    # Base layer operations
    print("Base layer:")
    print("  rig.speed.to(10)")
    print("  rig.speed.add(5)")
    print("  rig.speed.mul(2)  # No phase needed on base!")
    print("  rig.speed.mul(2).over(1000)")

    # User layers
    print("\nUser layers:")
    print("  rig.layer('boost').speed.add(10)  # ✅ no phase")
    print("  rig.layer('boost').incoming.speed.mul(2)  # ✅ with phase")
    print("  rig.layer('boost').outgoing.speed.mul(1.5)  # ✅ with phase")
    # print("  rig.layer('boost').speed.mul(2)  # ❌ ERROR - needs phase")

    # Final layer
    print("\nFinal layer:")
    print("  rig.final.speed.add(5)")
    print("  rig.final.speed.mul(2)  # No phase needed on final!")
    print("  rig.final.speed.mul(2).over(1000)")

    # Override blend_mode
    print("\nOverride blend_mode:")
    print("  rig.layer('boost').speed.add(10)")
    print("  rig.layer('more').speed.add(5)")
    print("  rig.layer('cap').override.speed.to(100)  # Ignore previous, set to 100")
    print("  rig.layer('after').speed.add(10)  # Add to 100 (result: 110)")

    # Errors
    print("\nExpected errors:")
    print("  rig.incoming.speed.mul(2)  # ❌ not allowed on base")
    print("  rig.outgoing.speed.mul(2)  # ❌ not allowed on base")
    print("  rig.final.incoming.speed.mul(2)  # ❌ not allowed on final")
    print("  rig.final.outgoing.speed.mul(2)  # ❌ not allowed on final")
    print("  rig.layer('x').speed.mul(2)  # ❌ must use incoming/outgoing")


if __name__ == "__main__":
    print("=== PRD13 Layer System Tests ===\n")
    test_simple_layering()
    test_incoming_outgoing()
    test_base_and_final()
    test_complex_multi_layer()
    test_api_examples()
    print("\n=== All Tests Documented ===")
    print("\nNote: These are documentation/validation tests.")
    print("Actual execution would require running within Talon environment.")
