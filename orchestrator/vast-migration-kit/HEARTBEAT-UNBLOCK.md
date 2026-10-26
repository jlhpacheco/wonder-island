# Wonder Island → Vast — Heartbeat Unblock (STAGED)

> **Redaction note (for the public repo):** the rented standby server's live IP address, public port numbers, and cloud account/instance identifiers are redacted in this copy — the box is a live standby until the confirmatory run ends. The structure of the port map (internal 8111–8123, one public port per agent) and every method detail are preserved.

**State: STAGED ONLY.** Built and verified Oct 25–26, 2026. No live file,
job body, service, or pen has been changed. This document **supersedes
the fix prescribed in CUTOVER-CHECKLIST §3** (the blocker measurement
there stands as the record; the §3 prescription is marked superseded in
place). Jose Luis's order for this work: "Buy insurance" — make the
already-rented standby (instance [REDACTED-INSTANCE-ID]) actually usable.

## The fix in one line

The clock never probes the box. An agent-context prober probes it
instead and writes a heartbeat file; the clock's health gate for a vast
agent reads the heartbeat and passes only while it is **fresh
(< 600 s) and ok**.

## Why the §3 fix cannot work (proven, not re-litigated)

§3 prescribed capturing the operator shell's proxy URL into a static
`proxy.env` for the clock unit. The pilot attempt showed the runtime
**rotates its egress-proxy credentials per session**: the captured
credential is dead in the clock's long-lived context (HTTP 407 Proxy
Authentication Required), while any short-lived agent-context process
receives fresh credentials and reaches the box (200). No static file
can fix a rotating credential. The heartbeat design moves the probe to
the context that receives fresh credentials, and ships the *result* —
not the credential — across the boundary as a file. Nothing secret is
written anywhere by this kit.

## What was built (all under `vast-migration/staging/`)

| File | Role |
|---|---|
| `fleet-heartbeat-prober.py` (new) | Run by an agent-context process (the clerk, each tick). For every vast-targeted agent: GET `<vast url>/api.md` and write `ops/heartbeats/<agent>.json` (agent, target, url, ts, iso, status, http_status, entity_count, slot, census, error), atomically. Reads proxy credentials from its own environment via urllib; never stores or prints them. |
| `fleet_clock.py` (patched again) | `LiveHealth.ok()`: local targets → the original direct localhost probe, unchanged. Vast targets → `_heartbeat_ok()`: heartbeat file must name this agent + target `vast`, record status `ok`, and be younger than `HEARTBEAT_FRESH_S = 600` s (a 60 s future-skew is tolerated). Missing / malformed / stale / not-ok → gate closed (fail-closed, same shape as a failed probe). |
| `proofs/heartbeat-demo/` + `proofs/heartbeat-demo.log` | The end-to-end gate demonstration (below). |
| `proofs/fleet-clock.diff` | Regenerated: the complete live→staged clock patch, heartbeat change included (86 lines). |

Prober safety — the single player slot: a join holds a world's only
player slot until restart, and there is no leave endpoint. The gate's
criterion is /api.md 200, so **tick mode never joins** (`slot:
"not-probed"`, `entity_count: null`). The `--census` mode (join +
observe → entity count) is pre-flight / dark-box only; it records
`slot: "held-by-prober"` in the heartbeat and prints a warning naming
the clearing tool (`remote-restart.py`). A census join refused because
a player is in the world records `slot: "occupied"` — healthy world,
census merely unavailable.

## Verification (cold, in staging — `proofs/heartbeat-demo.log`)

Regressions on the patched staged kit:
- `python3 metronome.py fleet-selftest` → **OK** (all checks PASS).
- `python3 fleet_clock.py simulate` → **16/16 PASS, 3,564 events**,
  event counts identical to the original Track C proof. (The simulation
  exercises `SimWorld`, not `LiveHealth`, exactly as before — the patch
  surface is live-mode only, and the sim proves it changed nothing
  else.)

Gate demonstration — demo root with agent-13 flipped to `vast`, all
others local; gate harness run under the clock unit's own environment
(`env -i HOME=/home/hatch`, **no proxy variables at all**, so a vast
True can only come from the heartbeat file):

| Step | Setup | agent-13 (vast) | agent-01 (local) |
|---|---|---|---|
| A | no heartbeat on disk | **False** | True |
| B | prober run from an agent context, `--census`, against the dark box | heartbeat written: `status=ok, http=200, entity_count=36` | — |
| C | census session cleared via `remote-restart.py agent-13` (box world re-verified 36 entities, left fresh + unoccupied) | — | — |
| D | fresh heartbeat (from B) | **True** | True |
| E | heartbeat aged (ts − 900 s, past the 600 s window) | **False** | True |
| F | prober re-run in tick mode (no census, slot untouched) → fresh heartbeat | **True** | True |

## Release deltas vs CUTOVER-CHECKLIST §4

Follow §4 with these substitutions:

- **Step 2** also installs `fleet-heartbeat-prober.py` into
  `orchestrator/`.
- **Step 3 is REPLACED.** Do NOT create `proxy.env`; do NOT add an
  `EnvironmentFile` to the clock unit. The only clock restart is the
  one that loads the patched `fleet_clock.py` (same T0; expect a
  ≤ 60 s gate re-warm — the Oct 25 systemd move is the precedent).
- **Step 4** adds one clerk-body step (§5 replacements stand as
  written), inserted after step 1:

> 1B. HEARTBEATS (vast agents only). Run python3 ~/workspace/wonder-island/orchestrator/fleet-heartbeat-prober.py once (no arguments). It probes every vast-targeted agent's box world and refreshes ops/heartbeats/<agent>.json, which the fleet-clock's health gate reads for vast agents. Never pass --census on a tick (a census join holds the world's single player slot). A nonzero exit means a vast world did not answer: note it on the run board; if it persists to a second consecutive tick, treat it as an ALERT (step 8). With no vast-targeted agents the prober writes nothing and exits 0.

- **New pre-flight (before step 5's observation hour):** replicate the
  demo against a scratch root — live targets + agent-13 flipped —
  run the prober from an agent context, then the gate harness under
  `env -i HOME=/home/hatch`: require **True** for agent-13 (vast, from
  the heartbeat) AND **True** for one local agent. Any False → stop;
  nothing has been flipped yet. (`proofs/heartbeat-demo/gate_check.py`
  is the harness; it takes the root as its only argument.)

## Commander steps — agent-13 pilot flip

Preconditions: Jose Luis's go on the flip itself (unchanged gate);
§4-as-amended installed; the all-local observation hour (§4 step 5)
clean; agent-13 not frozen; its box world confirmed healthy within the
last hour (a `remote-restart.py agent-13` run counts, and leaves it
fresh). Then CUTOVER-CHECKLIST §6 steps 1–7 verbatim, with these
heartbeat-specific notes:

1. From the flip onward, agent-13's gate is the heartbeat: the clerk's
   step 1B refreshes it every 5 min tick; the gate tolerates one missed
   tick (600 s window), then closes — spawns hold in HEALTH-GATE-WAIT,
   visible in the events, no silent stall.
2. §6 step 3's failure branch is unchanged (HEALTH-GATE-WAIT past
   ~2 min after a boundary → §7 fallback, no live debugging). Add one
   first look: is `ops/heartbeats/agent-13.json` fresh and `ok`? A
   stale heartbeat with a healthy box means the prober/clerk stalled —
   still fall back first (§7), diagnose after.
3. §6 step 4's injection check is the positive proof the flip took:
   newest `transcripts/injection-*.txt` carries
   `http://[REDACTED-IP]:[REDACTED-PORT]` ×2 and no `localhost:8123`.

Fallback: CUTOVER-CHECKLIST §7 verbatim (target → `local`, start the
local unit, ≤ 2 min). The heartbeat file may stay on disk — once the
target is local the gate takes the direct-probe path and never reads
it.

## Residual risks, stated plainly

- The heartbeat proves the box world answered /api.md 200 from an
  agent context within the last 10 minutes — the same evidence the
  original gate design used, one hop removed. The census (36 entities)
  remains a boundary-time proof via `remote-restart.py` at every
  SERVICE-RESTART, exactly as the checklist already routes it.
- If the clerk stops ticking entirely, vast agents stall at their next
  boundary (fail-closed) while local agents continue — a partial-fleet
  stall, alertable through the existing watchdog's world-down and
  rate conditions, recoverable by §7 fallback per agent.
- Nothing in this kit changes the box, the worlds, the starter, or
  fleet-recover semantics; §8's cosmetics stand.
