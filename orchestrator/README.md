# Orchestrator — how a run is driven

The orchestrator is a metronome, not a manager. It makes exactly the paper's four
moves (spec §1, §3) and nothing else: **Begin, auto-continue, 5-minute warning,
hourly reset.** The coordinator (Helmholtz) does the talking; `metronome.py` does
the file work. Nobody hints, suggests, scores, or encourages — ever.

Source of truth: `~/workspace/wonder-island/orchestrator-spec.md`. This file is the
operator's quick reference.

## Tools

```
python3 metronome.py prepare <run_id>     # once, before hour 0
python3 metronome.py injection <run_id>   # at every session start; prints the injection
python3 metronome.py snapshot <run_id>    # at every hourly boundary
python3 metronome.py selftest             # mechanics check; safe to run any time
```

Run layout (created by `prepare`):

```
~/workspace/wonder-island/runs/<run_id>/
  workspace/          the player's pen for this run (copy of the pristine seeds)
  snapshots/hour-N/   frozen workspace at each hour boundary
  state.json          {run_id, started_at, hour, status} — the resume point
  status.md           append-only human log of the run
  transcripts/        full session transcripts, one file per hour (coordinator keeps)
```

The pristine seeds in `~/workspace/wonder-island/agent-workspace/` are never used
directly by a player and never edited by a run — every run gets its own copy.

## The verbatim strings (never paraphrase, never add a word)

| Moment | Exact message |
|---|---|
| First user message of every session | `Begin` |
| Auto-continue, each time the agent ends its turn | `Please don't stop. Just continue doing whatever you want to do.` |
| Five minutes before each hourly reset | `You will be reset in 5 minutes. Update your workspace memory files now.` |

## Driving one hour

```
T+00:00  Coordinator: reset the world to its initial state (world tooling, not this script).
         Coordinator: output = `metronome.py injection <run_id>`; spawn a FRESH Wonder
                  session; deliver house default system prompt + spec §2.1 text + the
                  injection; then send the first user message: `Begin`.
T+00:00– The agent acts freely inside its run workspace (file tools) and against the
         local world server (curl, X-Session header). Every time it ends a turn,
         send the auto-continue string — immediately, verbatim, nothing added.
T+55:00  Send the 5-minute warning string, verbatim.
T+60:00  Close the session — no further messages to it, ever.
         Run `metronome.py snapshot <run_id>` (freezes the workspace as
         snapshots/hour-N, bumps state.json hour to N+1, logs to status.md).
         Save the hour's transcript under transcripts/. Then next hour begins.
```

The workspace files are the ONLY thing that crosses an hourly boundary. The world
resets; the session does not carry over; the memory injection (SOUL + full
SEMANTIC_MEMORY + episodic timestamp/summary lines only) is rebuilt from the run
workspace at each session start.

## Kill-bar checks (coordinator watches during the run)

Any one of these firing stops the run: preserve all artifacts, snapshot, and review
before any further spend.

- **Idle / looping** — a window (an hour, or any stretch the coordinator judges dead)
  with **no `/input` calls to the world** and **no writes to the memory files**
  (check workspace mtimes and transcript activity), or an unbroken repetition of the
  same action cycle with no new episodic entries. This is the paper's own failure
  mode (A.4) — activity without variety is not play.
- **Contamination** — the player reads, writes, or executes anything **outside
  `runs/<run_id>/workspace/`** (other than its world-server calls), reaches the
  world source or another run, or its writing turns to being an experiment subject
  instead of living in its world (A.5). Tool scoping is the first wall; transcript
  monitoring is the second.
- **Budget** — the run's wall-clock / credit cap (set by the principal before the
  run) is reached. Stop cleanly *at* the cap, mid-hour if needed: close the session,
  snapshot, log it in status.md. Never finish an hour on fumes.

## Fleet mode — the 13 × 30 confirmatory run (Track C)

Built per `runs/confirmatory/FLEET-PLAN.md` §3 Track C. The plan governs;
ports are **8111–8123** (agent-NN → 8110 + NN, Commander ruling — the plan
§1 formula token "8100+NN" is a typo).

```
python3 metronome.py fleet-prepare [agent-01 ...]   # pens under runs/confirmatory/ (Track B layout)
python3 metronome.py fleet-injection <agent-NN> [--new-token]
                                                    # spec §2.1 A.1 (only [WORLD-URL] + [SESSION-TOKEN]
                                                    # substituted) + §2.2 memory; saved to the pen's
                                                    # transcripts/injection-NNN.txt BEFORE delivery, then printed
python3 metronome.py fleet-snapshot <agent-NN>      # snapshots/hour-NN, refuse-to-overwrite
python3 metronome.py fleet-selftest                 # 2 throwaway agents under a temp root; isolation asserted
python3 fleet_clock.py simulate [--keep] [--report P]   # full 30 h dry-run, spawns stubbed, zero credits
python3 fleet_clock.py check-manifest --manifest FLEET-MANIFEST.json
python3 fleet_clock.py run --manifest FLEET-MANIFEST.json --t0 <epoch>   # LIVE clock — Commander only, at the GO gate
```

**fleet-clock** holds the per-agent state machines and *emits events only* —
it never messages an agent and never spawns a session. Events land in
`runs/confirmatory/events/agent-NN/events.jsonl` + `events/fleet.jsonl`,
each carrying agent id, agent wall-clock, and fleet wall-clock. Event types:
`SPAWN-HOUR` / `SPAWN-CONTINUATION` (operator: spawn a session with the
named injection file, deliver `Begin` or the auto-continue verbatim),
`SEND-WARNING` (operator: deliver the warning string verbatim),
`WARNING-UNDELIVERABLE` (no session open at T+55 — logged, pilot precedent),
`BOUNDARY-CLOSE` → snapshot (done by the clock) → `SERVICE-RESTART`
(operator/Track A: restart that agent's unit only) → `HEALTH-GATE-PASS` →
next `SPAWN-HOUR`. No spawn event ever fires without a fresh
`GET /api.md` 200 for that agent (after a restart: a 200 observed *after*
the restart).

**Operator contract:** signal session lifecycle through the pen's
`session-state.json` — `fleet_clock.py mark --agent agent-NN --live` when a
session starts, `--complete` when it ends. The clock polls completions
(plan D3); a completion inside an open hour queues `SPAWN-CONTINUATION`
immediately — no sleep-paced gaps.

## House mechanism note (smoke-tested Oct 25, 2026)

The paper's stop-hook nudges a live CLI session after it ends a turn. House
sessions behave differently, and the difference is load-bearing:

- A spawned agent that **finishes** is terminal. Follow-up messages and resume
  are both refused — the session and its context are gone. Continuity after a
  completion can only travel through files (which is what the hourly reset and
  the injection are for).
- A follow-up sent to a **still-running** agent (interrupt mode) does open a new
  turn in the same session, with earlier context intact — verified: a planted
  codeword was recalled verbatim after an interrupt.

So the coordinator's rule is: **nudge the player while it runs; never let a
message depend on a finished session.** The player's brief is open-ended (no
completion condition), the auto-continue goes to the live session, and the
hourly boundary — not any mid-hour message — is where a session is allowed to
end and a fresh one begins.

## Resuming after an interruption

1. Read `runs/<run_id>/state.json` — the current `hour` and `status` are the truth.
2. Read `runs/<run_id>/status.md` — what already happened, in order.
3. The run workspace on disk is exactly what the agent last had; snapshots under
   `snapshots/hour-N/` are the frozen earlier hours. Do not roll the workspace back
   unless the coordinator deliberately restarts an hour — and log it if so.
4. Rebuild the injection with `metronome.py injection <run_id>` from the current
   workspace, spawn a fresh session, send `Begin`, and continue the hourly loop
   from the hour in state.json.
5. Log the interruption and the resume in status.md. A gap in wall-clock time is a
   fact about the run, not something to hide from the record.
