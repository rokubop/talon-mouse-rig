Ref 1: Talon Mouse Rig — Product Requirements Document (PRD)

Repo Name: talon-mouse-rig
Primary Entry: rig = actions.user.mouse_rig()
Goal: Provide a fluent, stateful, motion-based mouse control system supporting continuous movement, smooth turning, controlled speed shaping, and temporary acceleration overlays.

Core Design Principles

State-based movement, not discrete deltas.

Direction (unit vector) and Speed (scalar magnitude) are persistent.

Thrust is a temporary acceleration overlay that never rewrites speed.

.over() means time-based transition; absence means instant.

Movements and transitions auto-commit unless inside a sequence.

Fluent chaining must always read like a sentence.

Example:

rig.direction((-1,0))             # go left continuously
rig.speed(0.8)                    # constant cruise speed
rig.thrust(0.6).over(200)         # temporary acceleration push

Public API
Initialize
rig = actions.user.mouse_rig()

1) Direction (unit vector)
Operation	Meaning
rig.direction(vec)	Snap direction immediately
rig.direction(vec).over(ms)	Rotate to direction over time (shortest angular path)
rig.direction(vec).over(ms).ease(shape)	Smooth turning curve (default ease_in_out)
rig.direction(vec).rate(rad_per_sec)	Limit max turn speed (duration emerges naturally)
rig.direction(vec).rate(r).accel(a)	Limit angular velocity and angular acceleration

Alias:

rig.dir(vec)  # identical to rig.direction(vec)

2) Speed (cruise magnitude)
Operation	Meaning
rig.speed(v)	Set cruise speed instantly
rig.speed(v).over(ms)	Ease cruise to new speed
rig.speed.add(dv)	Add to current speed instantly
rig.speed.add(dv).over(ms)	Ease the adjustment over time
rig.speed.brake(decel)	Decelerate until speed = 0
rig.speed.brake_to(target, decel)	Decelerate to a specific cruise speed
rig.speed.ramp(rate) → handle	Indefinite acceleration until .stop()
3) Thrust (temporary acceleration overlay)
Operation	Meaning
rig.thrust(a).over(ms)	Apply acceleration envelope in current direction
rig.thrust(a).over(ms).ease(shape)	Smooth temporary acceleration profile
rig.thrust(a).dir(vec).over(ms)	Thrust in explicit direction
rig.thrust(a).hold() → handle	Apply constant acceleration until stopped

Key Rule:
Thrust never changes cruise speed.
When thrust ends, we return to direction * speed.

4) Position Control
Operation	Meaning
rig.pos.to(x,y)	Snap move
rig.pos.to(x,y).over(ms)	Smooth glide to coordinate
rig.pos.by(dx,dy)	Relative move
rig.pos.by(dx,dy).over(ms)	Smooth relative move