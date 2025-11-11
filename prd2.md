Talon Mouse Rig — PRD (v1 → v3 roadmap)
Core Philosophy

The rig is a continuous-motion model, where:

speed is baseline cruise velocity magnitude

direction is persistent heading

thrust applies acceleration (force) while active

boost applies instant velocity offset that decays

pos.by(...) applies temporary spatial offsets independent of cruise

No snapping unless explicitly requested.
Cursor motion emerges naturally from velocity over time.

STATE MODEL
Persistent
Field	Type	Meaning
direction	unit vec2	heading of baseline movement
speed	float	baseline speed magnitude
limits.max_speed	float	clamp on cruise speed
Overlays (Temporary)
Name	Origin	Affects	Auto-stop?	Notes
thrust	thrust(a)	acceleration	only if .over(t)	.hold() is continuous
boost	boost(f)	velocity offset	always decays to 0 over .over(t)	instant effect
pos glide	pos.by() / pos.to()	position, not velocity	ends at target	stackable for by
Derived Each Frame
cruise_velocity = direction * speed
velocity = cruise_velocity + sum(thrust_overlays) + sum(boost_overlays)
cursor_position += velocity * dt + pos_glide_offset

PUBLIC API (final structure)
Persistent motion
rig.direction(vec2)
rig.speed(value)

Acceleration (force)
h = rig.thrust(a).hold()            # continuous push
rig.thrust(a).over(ms)              # timed push
h.stop()                            # stop the push

# destructive mode (accel permanently changes cruise speed)
rig.thrust(a).hold().bake()

Instant velocity burst (dash/pop)
rig.boost(f).over(ms)               # instant velocity offset → decays

One-off spatial offsets
rig.pos.by(dx, dy).over(ms)
rig.pos.to(x, y).over(ms)

Halt
rig.halt()   # sets speed = 0 (does not cancel overlays)

TIERED IMPLEMENTATION PLAN
Phase 1 (MVP — can ship in a day)

Focus: Continuous motion + thrust hold + brake

Implement:

direction(vec)

speed(v)

frame loop stepping position += (direction*speed) * dt

thrust hold (constant thrust acceleration)

.bake() (thrust modifies cruise speed)

idle speed.brake(decel) for drift-to-zero

halt()

Use Case Enabled:

2-pedal analog movement (left/right accel)

Smooth reversals (no snapping)

Natural cruise retention

Drift to rest when idle

This alone gives you the pedal behavior we locked in.
And it feels great immediately.

Phase 2 (Comfort / Movement Expression)

Add overlays, but no easing yet.

Implement:

thrust(a).over(ms) (flat push impulse)

boost(f).over(ms) (instant velocity bump + linear fade)

pos.by(dx,dy).over(ms) (basic linear glide)

Use Case Enabled:

dash pops

correction flicks while cruising

downward nudges while moving left/right

camera smoothing

Still no easing, no curve math required.

Phase 3 (Refinement, Polish, Aesthetic Motion)

Add optional curvature, only when requested:

Implement:

.ease("ease_in_out")

.ease("ease_out")

.ease("smoothstep")

Defaults remain flat unless .ease() is used.

Use Case Enabled:

cinematic feel

recoil easing

soft UI glides

Phase 4 (Advanced Steering and Turning)

Later — only when needed.

Add:

direction(vec).over(ms)

direction(vec).rate(max_turn_speed)

This allows arc turns and smooth heading corrections.

Do not implement now.
Not needed for pedal-based control.

SUCCESS CRITERIA
Stage	You must be able to do this	Without…
Phase 1	Pedal left/right produces acceleration and retains momentum	easing, boost, pos glides
Phase 2	You can add pops/dashes & positional offsets	curves
Phase 3	Movement feels aesthetic & expressive	rewriting architecture
Phase 4	Smooth directional steering	touching the core loop
THE FIRST BUILD YOU SHOULD IMPLEMENT

The Phase 1 loop:

velocity = direction * speed
speed += thrust_accel * dt
speed = clamp(speed, -max_speed, max_speed)
position += velocity * dt


And foot pedal bindings:

_left = rig.thrust(ACCEL).dir((-1,0)).hold().bake()
_right = rig.thrust(ACCEL).dir((1,0)).hold().bake()
release → .stop(); rig.speed.brake(decel)

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