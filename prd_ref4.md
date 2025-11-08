Mouse Rig API Summary PRD 4

We will change some behavior.

Old: uses thrust, boost, resist, ease primitives.
New: Instead we want to just use speed and accel primitives, intuitive temporary effects system based on .in/.hold/.out, and the addition of named effects, and easing becomes part of second param to .over()/.in()/.out().

New Behavior (some parts similar to old):

Core Concepts
Base rig properties are permanent changes to the mouse movement state.
Temporary effects (anonymous or named) auto-remove after their lifecycle completes.

Property Access
rig.pos       # position (x, y)
rig.speed     # speed scalar
rig.accel     # acceleration scalar
rig.direction # direction vector (x, y)

Immediate Changes
rig.speed(10)           # set speed immediately
rig.direction(-1, 0)    # set direction immediately
rig.pos(100, 200)       # set position immediately

Value Modifiers
.to(value)    # set to absolute value
.by(delta)    # add/subtract relative value
.mul(factor)  # multiply by factor
.div(divisor) # divide by divisor

Timing & Lifecycle
Permanent Changes
.over(duration, easing?)  # animate change over duration, stays forever
Temporary Effects (Envelope System)
.in(duration, easing?)    # fade in over duration
.hold(duration)           # maintain value for duration
.out(duration, easing?)   # fade out over duration
.in_out(duration)          # symmetric: half duration in, half duration out

Rules:

Presence of .hold() or .out() = temporary (auto-removes)
.over() alone = permanent
.in() must be paired with .hold() or .out() (can't be used alone)
.in_out(duration) splits total duration evenly (no easing control - use .in().out() for that)

Examples
Permanent Changes
rig.speed(10)                          # immediate
rig.speed.to(15).over(500)             # animated
rig.speed.by(5).over(300, "ease_out")  # relative with easing
rig.direction(1, 0)                    # immediate direction
Temporary Anonymous Effects
rig.speed.mul(2).hold(1000)                           # instant boost, hold 1s, instant revert
rig.speed.mul(1.5).hold(2000).out(500)                # instant boost, hold 2s, fade out
rig.speed.mul(2).in(300).hold(1000).out(500)          # fade in, hold, fade out
rig.accel.to(5).in(300, "ease_out").out(1000, "ease_in")  # full control
Temporary Named Effects
# Can be stopped early
rig("boost").speed.mul(2).hold(1000)
rig("boost").stop()                    # immediate cancel
rig("boost").stop().over(500)          # graceful cancel

# Imperative control (no auto-revert until stopped)
rig("thrust").accel.to(5)              # stays active
rig("thrust").stop().over(2000, "ease_in_out")  # remove when ready
Global Rig Control
rig.stop()              # stop entire rig immediately
rig.stop().over(1000)   # gradually stop over 1s

Easing
Easing strings use naming: "ease_in", "ease_out", "ease_in_out", "linear"
rig.speed.to(10).over(500, "ease_in_out")
rig("boost").speed.by(5).in(300, "ease_out").out(1000, "ease_in")

Use Cases
Speed Boost Pads
rig.speed.mul(1.5).hold(2000)           # pad 1: instant +50% for 2s
rig.speed.mul(1.33).hold(1500)          # pad 2: instant +33% for 1.5s
rig.speed.mul(2).hold(1000).out(3000)   # pad 3: instant 2x, hold 1s, fade 3s
Thrust/Acceleration Control
# Key down
rig("thrust").accel.to(5)

# Key up
rig("thrust").stop().over(2000, "ease_in")
Gravity Effect
gravity = rig("gravity")
gravity.direction(0, 1)
gravity.accel(9.8)

Key Distinctions

.over() = permanent animation timing
.in()/.hold()/.out() = temporary envelope system
rig.property = base state (permanent)
rig("name") = named effect (can be stopped early)
Anonymous effects = fire-and-forget temporary changes