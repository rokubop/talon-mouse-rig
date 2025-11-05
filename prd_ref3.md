Talon Mouse Rig — PRD (Tiered)
Scope for Use Case 1 (MVP)

Goal: Continuous motion with simple controls.

Set direction

Set speed

Change speed (instant or over time)

Change direction instantly

Stop (halt)

Brake (rate-based decel to 0)

Public API (MVP)
rig = actions.user.mouse_rig()

# Direction
rig.direction(vec2)                  # snap heading immediately

# Speed (cruise)
rig.speed(value)                     # instant set
rig.speed(value).over(ms)            # ramp to target over time (linear by default)

# Speed adjustments
rig.speed.add(dv)                    # instant delta
rig.speed.add(dv).over(ms)           # ramp by delta over time

# Braking & stop
rig.speed.brake(decel)               # reduce current speed → 0 at rate (units/s²)
rig.halt()                           # immediate speed = 0

State (MVP)

direction: (x, y) (unit vec)

speed: float (cruise magnitude)

limits.max_speed: float (default clamp, can be None/∞)

Engine Rules (MVP)

Frame loop at ~16ms; position integrates direction * speed * dt.

speed(v).over(ms) is linear (no easing until later tiers).

speed.brake(decel) wins over any in-flight speed(...).over(...) (brake replaces).

halt() zeroes speed immediately (position still integrates, but with 0 velocity).

Examples (MVP)
# Set direction + speed
rig.direction((1,0))
rig.speed(5)

# Increase speed immediately
rig.speed(7)

# Increase speed over time
rig.speed(10).over(300)

# Turn up instantly (preserve speed)
rig.direction((0,-1))

# Gentle stop
rig.speed.brake(decel=2.0)

# Emergency stop
rig.halt()

Edge Cases (MVP)

If speed.add(dv).over(ms) goes past limits.max_speed, clamp at limit.

If brake(decel) is called while already at (or below ε), snap to zero.

direction(vec) requires non-zero vec; normalize internally.

Tier 2 (Comfort)

Add the minimal niceties, still no thrust required.

direction(vec).over(ms) (shortest-arc turn; linear by default)

pos.by(dx, dy).over(ms) and pos.to(x, y).over(ms) (basic glides; linear)

Optional: speed.min, speed.max helpers (aliases for limits)

Read-only: rig.state.position, rig.state.velocity (derived)

Examples

rig.direction((-1,0)).over(180)    # smooth turn
rig.pos.by(0, 10).over(150)        # nudge down while cruising

Tier 3 (Expression)

Introduce easing (opt-in) and polish.

.ease("ease_in"|"ease_out"|"ease_in_out"|"smoothstep")

speed(v).over(ms).ease(...), direction(...).over(ms).ease(...), pos.*.over(ms).ease(...)

Events (optional): on_speed_change, on_turn_start/end

Tier 4 (Advanced Motion — optional, later)

Bring back advanced overlays once the basics feel perfect.

Thrust (acceleration): rig.thrust(a).hold() / .over(ms) (+ optional .bake() later)

Boost (instant velocity offset + decay): rig.boost(f).over(ms)

Direction rate limits: direction(vec).rate(rad_per_s)[.accel(rad_per_s2)]

Defaults & Precedence

Linear by default for all .over(ms) until Tier 3.

Command precedence within a frame: halt > brake > speed.set/add (replaces active ramps).

New direction(...) (snap) replaces any turning in progress.