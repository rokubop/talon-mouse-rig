from talon import Module, actions

mod = Module()

@mod.action_class
class Actions:
    # =========================================================================
    # 1. BASIC MOVEMENT & DIRECTION
    # =========================================================================

    def test_move_right():
        """Basic right movement - base layer"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5).over(1000)
        # rig.layer("hello").direction(1, 0)
        # rig.layer("hello").speed(5)

    def test_move_left():
        """Basic left movement"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        rig.speed(rig.state.speed or 3)

    def test_move_up():
        """Basic up movement`!"""
        rig = actions.user.mouse_rig()
        rig.direction(0, -1)
        rig.speed(5)

    def test_move_down():
        """Basic down movement"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)
        rig.speed(5)

    def test_move_diagonal():
        """Diagonal movement (up-right)"""
        rig = actions.user.mouse_rig()
        rig.direction(1, -1)
        rig.speed(5)

    def test_direction_rotate():
        """Rotate by degrees (add)"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0)  # Start right
        # rig.speed(5)
        rig.direction.by(90).over(1000)  # Rotate 90° clockwise

    def test_reverse():
        """Reverse direction (180° turn)"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.reverse()

    # =========================================================================
    # 2. SPEED & ACCELERATION
    # =========================================================================

    def test_speed_set():
        """Set absolute speed"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0)
        rig.speed(6)

    def test_speed_add():
        """Add to speed (accelerate)"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0)
        # rig.speed(3)
        rig.speed.add(2)  # Accelerate to 5

    def test_speed_add_negative():
        """Decelerate by adding negative"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0)
        # rig.speed(5)
        rig.speed.add(-2)  # Slow to 3

    def test_speed_mul():
        """Multiply speed (double)"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0)
        # rig.speed(3)
        rig.speed.mul(2)  # Double to 6

    def test_speed_slow():
        """Multiply speed (double)"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0) *
        # rig.speed(3)
        rig.speed.div(2)  # Double to 6

    def test_speed_over():
        """Gradual speed change over time"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed.add(10).over(1000)  # Accelerate to +10 over 1 second

    def test_stop():
        """Stop completely (immediate)"""
        rig = actions.user.mouse_rig()
        rig.stop()

    def test_stop_gradual():
        """Gradual stop over time with easing"""
        rig = actions.user.mouse_rig()
        rig.stop(1000, easing="ease_out")  # Stop over 1 second with ease_out

    # =========================================================================
    # 3. LAYER SYSTEM - BASE, USER LAYERS, FINAL
    # =========================================================================

    def test_layer_basic():
        """Basic layer creation"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0)
        # rig.speed(5)
        rig.layer("modifier").speed.to(0)  # User layer sets speed

    def test_layer_basic_stop():
        """Basic layer creation"""
        rig = actions.user.mouse_rig()
        rig.layer("modifier").revert()

    def test_layer_stacking():
        """Multiple layers stack"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("layer1").speed.add(2)  # +2
        rig.layer("layer2").speed.mul(1.5)  # ×1.5

    def test_layer_ordering():
        """Layer execution order"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("first", order=1).speed.add(5)  # Runs first
        rig.layer("second", order=2).speed.mul(2)  # Runs second

    def test_layer_lifecycle_reset():
        """Layer lifecycle - reset"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").speed(10)  # Reset speed

    def test_layer_lifecycle_stack():
        """Layer lifecycle - stack"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").speed.stack(3)  # Add to existing

    # =========================================================================
    # 4. LAYER OPERATIONS
    # =========================================================================

    def test_layer_multiply():
        """Layer with multiply operation"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("boost").speed.mul(2)  # Double speed

    def test_layer_add():
        """Layer with add operation"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("boost").speed.add(3)  # Add 3 to speed

    def test_layer_combined():
        """Multiple operations on same layer"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        layer = rig.layer("combined")
        layer.speed.mul(2)  # Double speed
        layer.speed.add(1)  # Then add 1

    def test_layer_sequence():
        """Multiple layers in sequence"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("first").speed.add(2)
        rig.layer("second").speed.mul(1.5)

    # =========================================================================
    # 5. FINAL LAYER
    # =========================================================================

    def test_final_speed():
        """Final layer speed override"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").speed.mul(3)
        rig.final.speed(10)  # Final override

    def test_final_direction():
        """Final layer direction override"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.final.direction(0, 1)  # Force down

    # =========================================================================
    # 6. OVERRIDE BLEND_MODE
    # =========================================================================

    def test_override_speed():
        """Override blend_mode - reset without stacking"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").override.speed(15)  # Reset completely

    def test_override_direction():
        """Override direction"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").override.direction(-1, 0)  # Force left

    # =========================================================================
    # 7. BEHAVIOR TYPES - STACK, RESET, QUEUE, EXTEND, THROTTLE, IGNORE
    # =========================================================================

    def test_behavior_stack():
        """Stack behavior - add operations together (default for add/mul/div)"""
        rig = actions.user.mouse_rig()
        rig.layer("boost").speed.add(5)
        rig.layer("boost").speed.stack.add(3)  # Stacks to +8 total

    def test_behavior_reset():
        """Reset behavior - replace operation (default for .to())"""
        rig = actions.user.mouse_rig()
        rig.layer("move").speed.to(10)
        rig.layer("move").speed.reset.to(5)  # Replaces with 5

    def test_behavior_queue():
        """Queue behavior - wait for current operation to finish"""
        rig = actions.user.mouse_rig()
        rig.layer("move").speed.to(10).over(1000)
        rig.layer("move").speed.queue.to(5).over(500)  # Waits for first to finish

    def test_behavior_extend():
        """Extend behavior - extend hold duration"""
        rig = actions.user.mouse_rig()
        rig.layer("boost").speed.add(5).hold(1000)
        rig.layer("boost").speed.extend.hold(500)  # Adds 500ms to hold

    def test_behavior_throttle():
        """Throttle behavior - rate limit updates (with ms) or ignore (no ms)"""
        rig = actions.user.mouse_rig()
        rig.layer("smooth").direction.by(10)
        rig.layer("smooth").direction.throttle(200).by(10)  # Max every 200ms

    def test_behavior_throttle_ignore():
        """Throttle behavior - ignore new operations while active (no ms arg)"""
        rig = actions.user.mouse_rig()
        rig.layer("lock").speed.to(10).over(1000)
        rig.layer("lock").speed.throttle.to(5)  # Ignored while first operation active

    # =========================================================================
    # 8. HOLD - SUSTAIN VALUE AFTER TRANSITION
    # =========================================================================

    def test_hold():
        """Hold value for duration after transition"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed.add(5).over(1000).hold(2000)  # Transition for 1s, hold for 2s

    # =========================================================================
    # 9. SCALE - RETROACTIVE MULTIPLIER ON PROPERTIES
    # =========================================================================

    def test_scale():
        """Scale a property operation"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed.add(5).scale(2)  # Adds 10 instead of 5

    def test_scale_layer():
        """Scale in layer"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("zoom").speed.add(10).scale(1.5)  # Adds 15 instead of 10

    def test_scale_final():
        """Scale final layer"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("boost").speed.add(5)
        rig.final.speed.add(0).scale(2)  # Scale all accumulated speed by 2

    # =========================================================================
    # 10. POSITION CONTROL
    # =========================================================================

    def test_position_to():
        """Move to absolute position"""
        rig = actions.user.mouse_rig()
        rig.pos.to(500, 300).over(1000)  # 1 second transition

    def test_position_by():
        """Move by relative amount"""
        rig = actions.user.mouse_rig()
        rig.pos.by(100, -50).over(500)  # Relative movement

    # =========================================================================
    # 11. EASING & INTERPOLATION
    # =========================================================================

    def test_easing():
        """Use easing function"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed.add(10).over(1000, easing="ease_in_out")

    def test_easing_revert():
        """Easing on revert"""
        rig = actions.user.mouse_rig()
        rig.layer("boost").speed.add(10).over(500, easing="ease_out").hold(1000).revert(500, easing="ease_in")

    # =========================================================================
    # 12. STATE ACCESS & BAKING
    # =========================================================================

    def test_state_read():
        """Read current state"""
        rig = actions.user.mouse_rig()
        print(vars(rig.state))

    def test_bake():
        """Bake current values"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.bake()  # Lock current computed state

    # =========================================================================
    # 13. REAL-WORLD SCENARIOS
    # =========================================================================

    def test_scenario_sprint():
        """Sprint: hold shift to go faster"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        rig.layer("sprint").speed.mul(3)  # 3x speed while active

    def test_scenario_precision():
        """Precision mode: hold for slower, finer control"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("precision").speed.mul(0.3)  # 30% speed

    def test_scenario_acceleration_ramp():
        """Gradual acceleration ramp up"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(1)
        rig.speed.add(10).over(2000)  # 0→10 over 2 seconds

    def test_scenario_drift():
        """Drift: turn while maintaining speed"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(8)
        rig.direction.by(45).over(500)  # Smooth 45° turn

    def test_scenario_rubber_band():
        """Rubber band: snap back to center"""
        rig = actions.user.mouse_rig()
        rig.pos.to(960, 540).over(800, easing="ease_out")  # Snap to center

    def test_scenario_orbit():
        """Orbit: rotate around point"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.direction.by(2)  # Constant rotation

    def test_scenario_multi_layer_combo():
        """Complex: base + sprint + precision + final"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("sprint", order=1).speed.mul(2)
        rig.layer("precision", order=2).speed.mul(0.5)
        rig.final.speed.add(0).scale(1.2)  # Final 20% boost via scale

    def mouse_rig_pos_center():
        """Legacy: Move to center of screen"""
        rig = actions.user.mouse_rig()
        rig.pos.to(960, 540).over(500)  # Move to center over 1 second