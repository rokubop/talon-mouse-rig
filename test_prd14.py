"""Test PRD14 mode system implementation"""
from talon import Module, actions

mod = Module()

@mod.action_class
class Actions:
    def test_mode_offset():
        """Test offset mode - additive contribution"""
        rig = actions.user.mouse_rig()
        # Base speed
        rig.speed.to(50)
        # Layer adds to speed
        rig.layer("boost").speed.offset.to(100)
        print(f"Speed with offset: {rig.state.speed}")  # Should be 150

    def test_mode_override():
        """Test override mode - replace value"""
        rig = actions.user.mouse_rig()
        # Base speed
        rig.speed.to(50)
        # Layer overrides speed completely
        rig.layer("cap").speed.override.to(200)
        print(f"Speed with override: {rig.state.speed}")  # Should be 200

    def test_mode_scale():
        """Test scale mode - multiplicative factor"""
        rig = actions.user.mouse_rig()
        # Base speed
        rig.speed.to(100)
        # Layer scales speed
        rig.layer("slowmo").speed.scale.to(0.5)
        print(f"Speed with scale: {rig.state.speed}")  # Should be 50

    def test_mode_combined():
        """Test combining multiple modes in order"""
        rig = actions.user.mouse_rig()
        # Base speed
        rig.speed.to(50)
        # Add boost (offset)
        rig.layer("boost", order=1).speed.offset.to(50)  # 50 + 50 = 100
        # Apply slowmo (scale)
        rig.layer("slowmo", order=2).speed.scale.to(0.5)  # 100 * 0.5 = 50
        # Cap maximum (override)
        rig.layer("cap", order=3).speed.override.to(200)  # Final = 200
        print(f"Speed with combined modes: {rig.state.speed}")

    def test_position_offset():
        """Test position with offset mode"""
        rig = actions.user.mouse_rig()
        # Lock position
        rig.layer("lock", order=1).position.override.to(960, 540)
        # Add shake offset
        rig.layer("shake", order=2).position.offset.by(5, 5)
        print(f"Position: {rig.state.pos}")

    def test_direction_override():
        """Test direction with override mode"""
        rig = actions.user.mouse_rig()
        # Set base direction
        rig.direction.to(1, 0)  # Right
        # Override to north
        rig.layer("snap").direction.override.to(0, -1)
        print(f"Direction: {rig.state.direction}")

    def test_animation():
        """Test mode with animation"""
        rig = actions.user.mouse_rig()
        rig.speed.to(50)
        # Animate offset boost
        rig.layer("boost").speed.offset.add(50).over(500).revert(500)
        print("Animated boost started")

    def test_property_mode_syntax():
        """Test property.mode.operation syntax"""
        rig = actions.user.mouse_rig()
        rig.speed.to(100)
        # Both syntaxes should work:
        # 1. layer.property.mode.operation
        rig.layer("test1").speed.offset.to(50)
        # 2. layer.mode.property.operation
        rig.layer("test2").offset.speed.to(30)
        print(f"Total speed: {rig.state.speed}")  # Should be 180
