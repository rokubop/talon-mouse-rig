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
        """Stop completely"""
        rig = actions.user.mouse_rig()
        rig.stop()

    def test_stop_gradual():
        """Gradual stop over time"""
        rig = actions.user.mouse_rig()
        rig.stop(1000)  # Stop over 0.5 seconds

    # =========================================================================
    # 3. LAYER SYSTEM - BASE, USER LAYERS, FINAL
    # =========================================================================

    def test_layer_basic():
        """Basic layer creation"""
        rig = actions.user.mouse_rig()
        # rig.direction(1, 0)
        # rig.speed(5)
        rig.layer("modifier").speed.to(0)  # User layer doubles speed
        # rig.layer("modifier").incoming.speed.add(2)  # User layer doubles speed

    def test_layer_basic_stop():
        """Basic layer creation"""
        rig = actions.user.mouse_rig()
        rig.layer("modifier").revert()

    def test_layer_stacking():
        """Multiple layers stack"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("layer1").incoming.speed.add(2)  # +2
        rig.layer("layer2").incoming.speed.mul(1.5)  # ×1.5

    def test_layer_ordering():
        """Layer execution order"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("first", order=1).incoming.speed.add(5)  # Runs first
        rig.layer("second", order=2).incoming.speed.mul(2)  # Runs second

    def test_layer_lifecycle_reset():
        """Layer lifecycle - reset"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").incoming.speed(10)  # Reset speed

    def test_layer_lifecycle_stack():
        """Layer lifecycle - stack"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").incoming.speed.stack(3)  # Add to existing

    # =========================================================================
    # 4. PHASES - INCOMING VS OUTGOING
    # =========================================================================

    def test_phase_incoming():
        """Incoming phase - modify input to operations"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("input_mod").incoming.speed.mul(2)  # Affects operations

    def test_phase_outgoing():
        """Outgoing phase - modify output of operations"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("output_mod").outgoing.speed.add(3)  # Affects final result

    def test_phase_both():
        """Both phases in same layer"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        layer = rig.layer("both")
        layer.incoming.speed.mul(2)  # Double input
        layer.outgoing.speed.add(1)  # Add 1 to output

    def test_phase_sequence():
        """Multiple layers with phases"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("first").incoming.speed.add(2)
        rig.layer("second").outgoing.speed.mul(1.5)

    # =========================================================================
    # 5. FINAL LAYER
    # =========================================================================

    def test_final_speed():
        """Final layer speed override"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").incoming.speed.mul(3)
        rig.final.speed(10)  # Final override

    def test_final_direction():
        """Final layer direction override"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.final.direction(0, 1)  # Force down

    def test_final_force():
        """Final layer force"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.final.force(100, 100)  # Final force override

    # =========================================================================
    # 6. OVERRIDE BLEND_MODE
    # =========================================================================

    def test_override_speed():
        """Override blend_mode - reset without stacking"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").incoming.override.speed(15)  # Reset completely

    def test_override_direction():
        """Override direction"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("test").incoming.override.direction(-1, 0)  # Force left

    # =========================================================================
    # 7. LIFECYCLE METHODS - QUEUE, EXTEND, THROTTLE, IGNORE
    # =========================================================================

    def test_lifecycle_queue():
        """Queue operations"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("queued").incoming.speed.queue(8)  # Queue next

    def test_lifecycle_extend():
        """Extend operation duration"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5).over(1000)
        rig.layer("ext").incoming.speed.extend(500)  # Add 500ms

    def test_lifecycle_throttle():
        """Throttle rapid changes"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.layer("throttled").incoming.speed.throttle(200)  # Max every 200ms

    def test_lifecycle_ignore():
        """Ignore new operations"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5).over(1000)
        rig.layer("lock").incoming.speed.ignore()  # Lock speed

    # =========================================================================
    # 8. BEHAVIOR MODES - HOLD, RELEASE
    # =========================================================================

    def test_hold():
        """Hold value for duration"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed.add(5).over(1000).hold(2000)  # Hold for 2 seconds

    def test_release():
        """Release after duration"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(10).release(1000)  # Release after 1 second

    # =========================================================================
    # 9. SCALE - GLOBAL MULTIPLIER
    # =========================================================================

    def test_scale():
        """Scale all operations"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.scale(2)  # Double everything

    def test_scale_add():
        """Add to scale"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.scale.add(0.5)  # Increase scale

    def test_scale_layer():
        """Scale in layer"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("zoom").incoming.scale.mul(1.5)

    # =========================================================================
    # 10. POSITION CONTROL
    # =========================================================================

    def test_position_to():
        """Move to absolute position"""
        rig = actions.user.mouse_rig()
        rig.position.to(500, 300).over(1000)  # 1 second transition

    def test_position_by():
        """Move by relative amount"""
        rig = actions.user.mouse_rig()
        rig.position.by(100, -50).over(500)  # Relative movement

    # =========================================================================
    # 11. EASING & INTERPOLATION
    # =========================================================================

    def test_easing():
        """Use easing function"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed.add(10).over(1000).ease("ease_in_out")

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
    # 13. ERROR CASES & EDGE CONDITIONS
    # =========================================================================

    def test_error_base_incoming():
        """Base layer should not use incoming (error)"""
        rig = actions.user.mouse_rig()
        # This should raise error:
        # rig.incoming.speed(5)

    def test_error_final_incoming():
        """Final layer should not use incoming (error)"""
        rig = actions.user.mouse_rig()
        # This should raise error:
        # rig.final.incoming.speed(5)

    def test_error_layer_mul_without_phase():
        """User layer mul without phase (error)"""
        rig = actions.user.mouse_rig()
        # This should raise error:
        # rig.layer("test").speed.mul(2)

    # =========================================================================
    # 14. REAL-WORLD SCENARIOS
    # =========================================================================

    def test_scenario_sprint():
        """Sprint: hold shift to go faster"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(3)
        rig.layer("sprint").incoming.speed.mul(3)  # 3x speed while active

    def test_scenario_precision():
        """Precision mode: hold for slower, finer control"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(5)
        rig.layer("precision").incoming.speed.mul(0.3)  # 30% speed

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
        rig.position.to(960, 540).over(800).ease("ease_out")  # Snap to center

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
        rig.layer("sprint", order=1).incoming.speed.mul(2)
        rig.layer("precision", order=2).incoming.speed.mul(0.5)
        rig.final.scale(1.2)  # Final 20% boost

    def mouse_rig_pos_center():
        """Legacy: Move to center of screen"""
        rig = actions.user.mouse_rig()
        rig.pos.to(960, 540).over(300)