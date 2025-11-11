"""
Mouse Rig Examples - PRD 5 API

Basic examples demonstrating the PRD5 API:
- Direction control
- Speed control
- Temporary effects (.over/.hold/.revert)
- Named modifiers and forces
- Rate-based timing
- State management and baking
"""

from talon import Module, actions

mod = Module()

@mod.action_class
class Actions:
    # =========================================================================
    # DIRECTION CONTROL
    # =========================================================================

    def mouse_rig_go_right():
        """Move right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0)
        rig.speed(rig.state.speed or 2)
        # rig

    def mouse_rig_go_left():
        """Move left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 0)
        rig.speed(rig.state.speed or 2)

    def mouse_rig_go_up():
        """Move up"""
        rig = actions.user.mouse_rig()
        rig.direction(0, -1)
        rig.speed(rig.state.speed or 2)

    def mouse_rig_go_down():
        """Move down"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1)
        rig.speed(rig.state.speed or 2)

    def mouse_rig_go_up_right():
        """Move diagonally up-right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, -1)
        rig.speed(rig.state.speed or 2)

    def mouse_rig_go_up_left():
        """Move diagonally up-left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, -1)
        rig.speed(rig.state.speed or 2)

    def mouse_rig_go_down_right():
        """Move diagonally down-right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 1)
        rig.speed(rig.state.speed or 2)

    def mouse_rig_go_down_left():
        """Move diagonally down-left"""
        rig = actions.user.mouse_rig()
        rig.direction(-1, 1)
        rig.speed(rig.state.speed or 2)

    # =========================================================================
    # SPEED CONTROL
    # =========================================================================

    def mouse_rig_speed_slow():
        """Set speed to slow"""
        rig = actions.user.mouse_rig()
        rig.speed(5)

    def mouse_rig_speed_normal():
        """Set speed to normal"""
        rig = actions.user.mouse_rig()
        rig.speed(10)

    def mouse_rig_speed_fast():
        """Set speed to fast"""
        rig = actions.user.mouse_rig()
        rig.speed(20)

    def mouse_rig_speed_up():
        """Increase speed"""
        rig = actions.user.mouse_rig()
        rig.speed.by(5)

    def mouse_rig_speed_down():
        """Decrease speed"""
        rig = actions.user.mouse_rig()
        rig.speed.by(-5)

    def mouse_rig_speed_ramp():
        """Smoothly ramp speed up"""
        rig = actions.user.mouse_rig()
        rig.speed.to(5).over(1000, "ease_out")

    # =========================================================================
    # STOP CONTROL
    # =========================================================================

    def mouse_rig_stop():
        """Stop immediately"""
        rig = actions.user.mouse_rig()
        rig.stop()

    def mouse_rig_stop_soft():
        """Stop gradually over 1 second"""
        rig = actions.user.mouse_rig()
        rig.stop(1000, "ease_out")

    def mouse_rig_stop_gentle():
        """Stop very gradually over 2 seconds"""
        rig = actions.user.mouse_rig()
        rig.stop(2000, "ease_in")

    # =========================================================================
    # TEMPORARY EFFECTS
    # =========================================================================

    def mouse_rig_boost_instant():
        """Speed boost - instant on, hold, instant off"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(2).hold(1000)

    def mouse_rig_boost_fade():
        """Speed boost - instant on, hold, fade off"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(4).hold(1000).revert(1000)

    def mouse_rig_boost_smooth():
        """Speed boost - fade in, hold, fade out"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(4).over(1000).hold(1000).revert(1000, "ease_in")

    def mouse_rig_slowdown():
        """Temporary slowdown"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(0.2).over(1000).revert(500)

    # =========================================================================
    # NAMED MODIFIERS
    # =========================================================================

    def mouse_rig_turbo_on():
        """Start turbo mode (named modifier)"""
        rig = actions.user.mouse_rig()
        rig.modifier("turbo").speed.mul(2)

    def mouse_rig_turbo_off():
        """Stop turbo mode"""
        rig = actions.user.mouse_rig()
        rig.modifier("turbo").stop(500)

    def mouse_rig_thrust_on():
        """Start thrust acceleration (force)"""
        rig = actions.user.mouse_rig()
        rig.force("thrust").accel(10)

    def mouse_rig_thrust_off():
        """Stop thrust"""
        rig = actions.user.mouse_rig()
        rig.force("thrust").stop(2000)

    def mouse_rig_drift_on():
        """Add directional drift modifier (named)"""
        rig = actions.user.mouse_rig()
        rig.modifier("drift").direction.by(15)

    def mouse_rig_drift_temporary():
        """Temporary directional drift (auto-revert)"""
        rig = actions.user.mouse_rig()
        rig.direction.by(15).over(1000).revert(1000)

    def mouse_rig_drift_off():
        """Remove drift"""
        rig = actions.user.mouse_rig()
        rig.modifier("drift").stop()

    # =========================================================================
    # NAMED FORCES
    # =========================================================================

    def mouse_rig_gravity_on():
        """Enable gravity force"""
        rig = actions.user.mouse_rig()
        gravity = rig.force("gravity")
        gravity.accel(2)
        gravity.direction(0, 1)

    def mouse_rig_gravity_off():
        """Disable gravity"""
        rig = actions.user.mouse_rig()
        rig.force("gravity").stop(500)

    def mouse_rig_wind_on():
        """Enable wind force from left"""
        rig = actions.user.mouse_rig()
        wind = rig.force("wind")
        wind.speed(5)
        wind.direction(-1, 0)  # From right to left

    def mouse_rig_wind_off():
        """Disable wind"""
        rig = actions.user.mouse_rig()
        rig.force("wind").stop(500)

    # =========================================================================
    # ACCELERATION CONTROL
    # =========================================================================

    def mouse_rig_accel_on():
        """Start accelerating"""
        rig = actions.user.mouse_rig()
        rig.accel(5)  # Accelerate at 5 units/sec²

    def mouse_rig_accel_off():
        """Stop accelerating"""
        rig = actions.user.mouse_rig()
        rig.accel(0)

    def mouse_rig_accel_boost():
        """Temporary acceleration burst"""
        rig = actions.user.mouse_rig()
        rig.accel.to(10).over(500).revert(1000)

    # =========================================================================
    # RATE-BASED TIMING
    # =========================================================================

    def mouse_rig_ramp_by_rate():
        """Ramp speed at specific rate (10 units/sec)"""
        rig = actions.user.mouse_rig()
        rig.speed.to(50).rate(10)

    def mouse_rig_turn_by_rate():
        """Turn at specific rate (90 degrees/sec)"""
        rig = actions.user.mouse_rig()
        # rig.direction(0, 1).rate(90)
        rig.modifier("asdf").direction.by(90).rate(90)

    def mouse_rig_accel_speed():
        """Increase speed via acceleration"""
        rig = actions.user.mouse_rig()
        rig.speed.to(30).rate.accel(5)

    # =========================================================================
    # SMOOTH TURNS
    # =========================================================================

    def mouse_rig_turn_right():
        """Smooth turn to right"""
        rig = actions.user.mouse_rig()
        rig.direction(1, 0).over(300)

    def mouse_rig_turn_down():
        """Smooth turn to down"""
        rig = actions.user.mouse_rig()
        rig.direction(0, 1).over(300)

    def mouse_rig_reverse():
        """Turn 180 degrees"""
        rig = actions.user.mouse_rig()
        rig.reverse().over(500)

    # =========================================================================
    # POSITION CONTROL
    # =========================================================================

    def mouse_rig_pos_center():
        """Move to screen center"""
        rig = actions.user.mouse_rig()
        rig.pos.to(960, 540).over(350, "ease_in_out")

    def mouse_rig_pos_corner():
        """Move to top-left corner"""
        rig = actions.user.mouse_rig()
        rig.pos.by(100, 100).over(800).revert(800).then(lambda: print("returned"))

    def mouse_rig_nudge_right():
        """Nudge position right"""
        rig = actions.user.mouse_rig()
        rig.pos.by(100, 0).over(200)

    # =========================================================================
    # STATE & BAKING
    # =========================================================================

    def mouse_rig_show_state():
        """Print current state"""
        rig = actions.user.mouse_rig()
        print(f"Speed: {rig.state.speed}")
        print(f"Base Speed: {rig.base.speed}")
        print(f"Position: {rig.state.pos}")
        print(f"Direction: {rig.state.direction}")

    def mouse_rig_bake_state():
        """Bake current state into base"""
        rig = actions.user.mouse_rig()
        rig.bake()
        print("State baked - effects cleared")

    # =========================================================================
    # LAMBDA EXAMPLES
    # =========================================================================

    def mouse_rig_relative_boost():
        """Boost by 50% of current speed"""
        rig = actions.user.mouse_rig()
        rig.speed.by(lambda state: state.speed * 0.5).revert(1000)

    def mouse_rig_double_speed():
        """Double current speed temporarily"""
        rig = actions.user.mouse_rig()
        rig.speed.mul(lambda state: 2).hold(2000).revert(500)

    # =========================================================================
    # PROPERTY CHAINING EXAMPLES
    # =========================================================================

    def mouse_rig_chain_basic():
        """Chain multiple properties in one statement (no timing)"""
        rig = actions.user.mouse_rig()
        # All properties execute immediately, no timing involved
        rig.speed(10).accel(2).direction(1, 0)

    def mouse_rig_chain_all_properties():
        """Chain all four property types"""
        rig = actions.user.mouse_rig()
        # Set speed, accel, direction, and position in one chain
        rig.speed(5).accel(3).direction(1, 1).pos.to(500, 500)

    def mouse_rig_chain_with_modifiers():
        """Chain with relative modifiers"""
        rig = actions.user.mouse_rig()
        # Use .by() for relative changes while chaining
        rig.speed.by(5).accel.by(2).direction.by(45)

    def mouse_rig_no_timing_in_chains():
        """INVALID: Cannot mix timing with chaining

        These would raise errors:
            rig.speed(4).over(100).accel(3)      # timing before chain
            rig.speed(4).accel(3).over(100)      # timing after chain

        Instead, use separate statements:
        """
        rig = actions.user.mouse_rig()
        rig.speed(4).over(100)   # Timing allowed when not chaining
        rig.accel(3).over(200)   # Each property gets its own timing


# =============================================================================
# PRD 6 - TRANSFORM AND FORCE LIFECYCLE EXAMPLES
# =============================================================================

    def mouse_rig_prd6_transform_lifecycle():
        """PRD6: Transform entities with lifecycle (.over/.hold/.revert)
        
        Transform entities support lifecycle timing just like effects:
        - .over(ms, easing) - fade in
        - .hold(ms) - maintain
        - .revert(ms, easing) - fade out
        """
        rig = actions.user.mouse_rig()
        
        # Scale speed by 2x, fade in over 500ms, hold for 2s, then revert over 300ms
        rig("sprint").scale.speed.to(2.0).over(500).hold(2000).revert(300)
        
        # Shift speed by +5, fade in with ease-out, hold indefinitely
        rig("boost").shift.speed.to(5).over(300, "ease-out").hold()
        
        # Stack multiple transforms with different lifecycles
        rig("fast").scale.speed.by(1.5).over(200)  # Quick 1.5x multiplier
        rig("faster").scale.speed.by(2.0).over(500, "ease-in-out")  # Slower 2x on top

    def mouse_rig_prd6_transform_stacking():
        """PRD6: Transform stacking with lifecycle
        
        .to() replaces, .by() stacks - both support lifecycle
        """
        rig = actions.user.mouse_rig()
        
        # Start with base speed
        rig.speed(10)
        
        # Scale it: final = base * scale_total
        rig("double").scale.speed.to(2.0).over(200)  # 2x base, fade in
        rig("bonus").scale.speed.by(0.5).over(100)   # +0.5x more, stacks to 2.5x total
        
        # Then shift: final = (base * scales) + shifts
        rig("speedup").shift.speed.to(15).over(300)  # +15, replaces other shifts
        rig("extra").shift.speed.by(5).over(150)     # +5 more, stacks
        
        # Result: (10 * 2.5) + 15 + 5 = 45 pixels/sec (as multipliers reach full strength)

    def mouse_rig_prd6_named_transforms():
        """PRD6: Named transform entities for control
        
        Transform entities use names for lifecycle management:
        - Same name = modify existing lifecycle
        - Different name = independent transform
        """
        rig = actions.user.mouse_rig()
        
        # Create a named speed boost
        rig("turbo").scale.speed.to(3.0).over(500).hold()
        
        # Later, update the same "turbo" entity to revert
        rig("turbo").revert(400)  # Starts fade-out over 400ms
        
        # Independent transforms run simultaneously
        rig("sprint").scale.speed.to(2.0).over(300)
        rig("nitro").shift.speed.by(10).over(200)

    def mouse_rig_prd6_accel_lifecycle():
        """PRD6: Acceleration transforms with lifecycle"""
        rig = actions.user.mouse_rig()
        
        # Scale acceleration (multiplicative)
        rig("ramp").scale.accel.to(2.0).over(300).hold(1000).revert(200)
        
        # Shift acceleration (additive)
        rig("boost").shift.accel.by(5).over(150).hold(500)
        
        # Combined effect integrates over time
        rig.direction(1, 0).speed(0).accel(10)  # Base accel
        # Result: accel = (10 * 2.0) + 5 = 25 (as effects reach full strength)

    def mouse_rig_prd6_max_with_lifecycle():
        """PRD6: Max constraints work with lifecycle transforms"""
        rig = actions.user.mouse_rig()
        
        # Stack multiple speed scales with max constraints
        rig("fast").scale.speed.by(2.0).max.speed(50).over(200)
        rig("faster").scale.speed.by(1.5).max.speed(30).over(300)
        rig("fastest").scale.speed.by(1.2).max.speed(20).over(100)
        
        # Each has independent lifecycle and clamping
        # As they fade in/out, constraints apply at each phase

    def mouse_rig_prd6_complex_composition():
        """PRD6: Complex transform composition with lifecycle
        
        Pipeline order: base → all scales → all shifts (in entity creation order)
        Each transform can have independent lifecycle timing.
        """
        rig = actions.user.mouse_rig()
        
        # Setup base movement
        rig.direction(1, 0).speed(20)
        
        # Scale transforms (multiplicative) - fade in at different rates
        rig("double").scale.speed.to(2.0).over(500, "ease-out")
        rig("triple").scale.speed.by(1.0).over(300, "linear")  # Stacks to 3x total
        
        # Shift transforms (additive) - different lifecycles
        rig("boost").shift.speed.to(15).over(200, "ease-in")
        rig("extra").shift.speed.by(10).over(400).hold(1000).revert(300)
        
        # Result animates as lifecycle multipliers evolve:
        # - Scales multiply base: 20 * (2.0 + 1.0) = 60 (at full strength)
        # - Shifts add: 60 + 15 + 10 = 85 (at full strength)
        # - Each fade independently per timing settings

    def mouse_rig_prd6_force_lifecycle():
        """PRD6: Force entities with full lifecycle support
        
        Forces now support .over(), .hold(), and .revert() just like transforms.
        """
        rig = actions.user.mouse_rig()
        
        # Setup base movement
        rig.direction(1, 0).speed(10)
        
        # Temporary wind force - fade in, hold, fade out
        rig("wind").velocity(0, 5).over(300).hold(2000).revert(500)
        # Wind pushes down, fades in over 300ms, holds for 2s, fades out over 500ms
        
        # Gravity with instant application and timed removal
        rig("gravity").direction(0, 1).accel(9.8).hold(5000).revert(1000)
        # Instant on, lasts 5s, then fades out over 1s
        
        # Boost pad - instant force, instant removal after duration
        rig("boost_pad").velocity(10, 0).hold(500).revert(0)
        # Instant 10px/s boost for 500ms, then instant removal

    def mouse_rig_prd6_shift_pos():
        """PRD6: Position shifting with .to() and .by()"""
        rig = actions.user.mouse_rig()
        
        # Set position offset (teleport-like)
        rig("warp").shift.pos.to(100, 100)
        # Instantly offset position by (100, 100)
        
        # Stack position offsets
        rig("nudge1").shift.pos.by(10, 0)   # +10 right
        rig("nudge2").shift.pos.by(0, -10)  # +10 up
        # Total offset: (10, -10)
        
        # Replace with new offset
        rig("warp").shift.pos.to(50, 50)
        # Now offset is (50, 50) + nudges

    def mouse_rig_prd6_drift_rotation():
        """PRD6: Direction rotation with shift.direction.by()"""
        rig = actions.user.mouse_rig()
        
        # Moving right
        rig.direction(1, 0).speed(10)
        
        # Add drift rotation
        rig("drift").shift.direction.by(-15).over(200).hold(1000).revert(300)
        # Rotates direction -15° over 200ms, holds for 1s, rotates back over 300ms
        
        # Multiple drift effects stack
        rig("drift2").shift.direction.by(10).over(100)
        # Total rotation: -15° + 10° = -5° (when both at full strength)

