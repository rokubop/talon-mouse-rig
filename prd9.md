1. tag = the new consumer-facing name for named effects

Effects already exist (anonymous + named).

For consumers, named effects are accessed through rig.tag("name") now instead of rig.effect("name").

Everything else about effects stays the same — this is a rename for clarity.

Examples:

rig.tag("move").pos.to(100,100).over(200)
rig.tag("boost").speed.add(3).over(150)

2. Repeat behavior already handled by effects

Effects already support:

stack (default)

replace

queue

throttle

ignore

Optional (not required):
You may add sugar like:

rig.tag("hover").queue.pos.to(...)
rig.tag("hover").throttle(300).pos.to(...)
rig.tag("hover").stack.pos.to(...)
rig.tag("hover").stack(3).pos.to(...)
rig.tag("hover").replace().pos.to(...)

if we think thats a good idea. make a best judgement call here, if on_repeat is sufficient, or if we would like to add more sugar.

**3. Validation: one operation per segment (new)

A segment = one operation
A locked segment = operation + time declaration (over, hold, revert)
Locked means no further ops can be added to that segment, but we can still do over, hold, revert, then(...), etc.
Is continuation segment + is named tag - important to know if we can revert or not.

over being called twice in a row is disallowed.

Allowed operations:

to, by, add, sub, mul, div


Validation rule:

Only one of these per segment.

Even if it’s the same op (to → to), each op is a separate segment.

Invalid (two ops in one segment):

rig.speed.add(5).add(2).over(300)   # ❌ not allowed


Valid (two segments): (new)

rig.pos.to(10, 10).over(150).to(20, 20).over(150)
rig.pos \
    .to(10, 10).over(150) \
    .then(lambda: print('first over')) \
    .to(20, 20).over(150)

So now we can chain multiple builders if repeating the same operation over time - which creates a new builder and queues it, similar to how named effects queue operations.

1. Queuing: a second operation automatically creates a new segment (new)

First op = new segment

Time declaration (over, hold, revert) locks the segment

Next op on the same builder → always queues a new segment

Example:

rig.pos.to(100,100).over(200)
      .to(300,300).over(200)
      .to(500,200).over(250)


This is 3 queued segments inside the same effect (anonymous or tagged).

IMPORTANT:
Queuing logic should be unified in the code, ideally using the same internal mechanism for both anonymous effects and named effects.

rig.pos.to(100,100).to(200,200).over(200)   # ❌ not allowed (multiple ops before time declaration)
rig.pos.to(100,100).over(200).over(150)   # ❌ not allowed (multiple time declarations)
rig.pos.to(100,100).over(200).hold(150)   # ✅ allowed
rig.pos.to(100,100).over(200).to(200,200).to(150)   # ✅ allowed (new builder queued)

5. Revert rules (unchanged, but restated for clarity)

revert is only allowed if the effect is named (rig.tag(...)).

Anonymous effects cannot use revert IF they have multiple segments.

revert refers to the effect-level baseline, not per-segment.

Example:

rig.tag("boost")
   .speed.mul(2).over(150)
   .speed.add(3).over(150)
   .revert(300)

6. Multiple then calls (new feature)

This is explicitly new.

You can attach multiple then(...) callbacks to the end of:

over

hold

revert

Example:

rig.pos.to(100,100).over(200)
    .then(do_a)
    .then(do_b)
    .then(do_c)
rig.pos.to(100,100).over(200)
    .then(do_a)
    .then(do_b)
    .hold(100)
    .then(do_c)
    .revert(300)
    .then(do_d)

All run in order when that phase completes.

1. One axis per chain (v1 rule)

A single chain must choose one of:

pos

speed

accel

direction

and stay on that axis for the entire chain.

Example (valid):

rig.tag("slide").pos.to(100,100).over(200).to(300,300).over(200)


Example (not allowed):

rig.tag("slide").speed.add(3).over(200).pos.to(100,100)


8. Remove Force from API

users could do rig.force("name"), however I found this not very useful, so we can remove it from the public API for now.

Internally implemented, but no longer part of the public surface.

Not exposed in v1.