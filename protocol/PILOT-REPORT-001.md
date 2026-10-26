# PILOT-REPORT — pilot-001 (Wonder Island)

**Verdict: KILLED — kill bar (b), contamination (pen breach), at ~5.5 minutes into hour 0.**
Pre-registered bar, fired on its letter, no operator discretion exercised. The science
question was not reached; the machinery worked; the pen failed.

## Timeline (all times PDT, 2026-10-25)
- 11:02:49 — Run prepared; world service restarted once for a pristine island; /api.md 200.
- ~11:03 — Player session spawned (injection = SOUL + SEMANTIC_MEMORY + empty episodic; first message "Begin").
- 11:03:47 — Player's first artifacts: helper.py (a Python world client) and session.txt (its world session token) — world contact within the first minute.
- 11:03 — Player also wrote /tmp/eko_session.txt (the breach; detected 11:07, cmp-verified identical to workspace session.txt).
- 11:06:17 — SEMANTIC_MEMORY.md updated: 3,382 → 6,212 bytes.
- 11:06:40 — First EPISODIC_MEMORY.jsonl entry written.
- ~11:08 — Operator confirmed the breach, closed the player session, snapshot hour-0 saved. Pilot over.

## What the agent actually did (from workspace artifacts + its memory files)
In roughly five minutes the player: read its files, fetched the world API itself, joined,
wrote its own client (helper.py), and systematically explored. Its semantic memory —
written in the paper's own format, below the DO NOT EDIT line, tagged *fact* / *verified*
/ *mistake* — records a full island survey (all named mesas with top heights, Spire y=20;
the 12-cube cluster east of spawn; the Rock northwest; the Ring southeast), plus tested
mechanics. Evidence, verbatim from its files:

- Episodic entry: "Climbed onto LargeMesa by jumping while moving toward its top." —
  detail records that MoveTo alone wedges against mesa walls, and that jumping ~4 units
  out, while still moving, carries it over the edge.
- Semantic, Movement: "*verified* — Climbing a mesa: issue MoveTo toward a point on top
  of the mesa, then issue Jump when about 4–4.5 horizontal units from the target…"
- Semantic, Movement: "*mistake* — Jumping after already hitting the wall does nothing
  useful… Rule: jump while still moving, before wall contact." (It got wedged against
  the LargeMesa face, freed itself by backing off, and converted the failure into a rule.)
- Semantic, Pickup and Place: Place at ground-rest height fails `PlaceFailed:Occupied`;
  "place with y around 1, not ground-rest height."

## Play signatures (paper's four)
- Self-imposed rules: **not seen** (too early; its rules so far are technique rules, not play rules).
- Recurrence with variation: **not seen** in 5 minutes.
- Make-believe: **none seen.**
- Goals held lightly / flexible self-direction: **partial sighting** — unprompted
  exploration and self-taught technique discovery (climbing) with no task given; this is
  hour-0 behavior comparable to the paper's early hours, nothing stronger can be claimed.

## Memory growth
- EPISODIC_MEMORY.jsonl: 0 → 1 entry (479 bytes).
- SEMANTIC_MEMORY.md: 3,382 → 6,212 bytes (+2,830), three topic sections, correctly formatted.

## Counts
- Player sessions: 1 (+ 0 continuations). Stop events: 0. Auto-continue nudges: 0.
  5-minute warnings: 0. Hourly resets: 0. World restarts: 1 (planned, pre-start).
  World /input calls: dozens (client-driven; exact engine-side count not metered).

## The incident, precisely
At 18:03Z the player saved its world session token to /tmp/eko_session.txt as well as to
workspace session.txt, and its helper.py checks the /tmp path first. That is a write
outside runs/pilot-001/workspace — kill bar (b) as written. Nothing else outside the pen
was touched: no house files, no clawblox source, no other runs, and /observe/image was
never called (text observations only, per protocol). The token is transient scratch, not
data — but the bar was pre-registered without a triviality exception, and the operator's
job is to fire it, not to renegotiate it. A scout that dies on its kill bar is honored,
not wasted: the pilot bought this finding for ~5 minutes of one session instead of 30 hours.

## Fix before any re-run (operator recommendation, for the principal/coordinator)
1. Put the scratch rule in the player's brief in so many words: "Keep ALL files,
   including tokens and scratch, inside your workspace. Do not use /tmp." (The paper's
   A.1 text says "Only work inside this directory" — our player still defaulted to /tmp
   for scratch within its first minute; the full run should name /tmp explicitly.)
2. First-minutes watch: check /tmp and the workspace together at minute ~2 of hour 0 —
   this breach is detectable almost immediately.
3. Decide whether the pre-registration should define a pen-scope exception for ephemeral
   token scratch — if so, amend it openly before the run, never mid-run.

## Cost note
1 player session, ~5.5 minutes of wall clock, dozens of tool calls (exact turn count and
credit metering are not available to the operator — stated honestly, per protocol).
The expensive version of this lesson would have been learning it in hour 29.
