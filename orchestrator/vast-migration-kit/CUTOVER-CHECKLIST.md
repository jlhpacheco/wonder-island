# Wonder Island → Vast — Cutover Checklist (STAGED KIT)

> **Redaction note (for the public repo):** the rented standby server's live IP address, public port numbers, and cloud account/instance identifiers are redacted in this copy — the box is a live standby until the confirmatory run ends. The structure of the port map (internal 8111–8123, one public port per agent) and every method detail are preserved.

**State: STAGED ONLY.** Built and tested Oct 25–26, 2026 against the dark
rented box (instance [REDACTED-INSTANCE-ID]). **No live file, job body, service, or pen
has been changed.** Releasing any part of this kit is the Commander's
separate decision; the recommended first release is a one-agent pilot (§7).

The design in one line: `ops/world-targets.json` is the single source of
truth for where each agent's world lives (`local` | `vast`). Every
consumer reads it — nothing else needs per-agent configuration, and a
missing file/entry means **local**, the pre-migration behavior.

---

## 0. Sequencing constraint — checked before building

The kit was not to go live until the operator-split changeover
(clerk/starter) was confirmed complete. Findings at build time:

- Both split jobs exist and are enabled: `wonder-island-fleet-ops`
  (clerk body, 900 s timeout) and `wonder-island-fleet-starter`
  (enabled, every 5 min, first run Oct 25 22:05:40 PT).
- `ops/spawn-pending.json` was seeded with **18** handoffs at the
  changeover (05:00 UTC) and is **draining**: 17 at 05:09 UTC, **3** at
  ~05:16 UTC, with hour-1 player spawns landing in the ledger in step
  (agent-02 05:07:07, agent-03 05:07:47, agent-04 05:08:52, …,
  agent-13 05:15:45 UTC). Duplicate seed entries from the clock's
  re-emissions are being dropped by the starter's ledger re-check, as
  designed.
- **Verdict: the split changeover is complete and functioning.** The
  constraint on *building* is satisfied. The constraint on *releasing
  this kit* is unchanged: Commander release, per agent, at boundaries.

## 1. Kit inventory (all under `vast-migration/staging/`)

| Staged file | Installs to (at release) | What it does |
|---|---|---|
| `ops/world-targets.json` | `runs/confirmatory/ops/world-targets.json` | Per-agent target + both endpoints' coordinates. Ships with **all 13 targets `local`** — installing it changes nothing. |
| `ops/world-targets.schema.json` | `runs/confirmatory/ops/world-targets.schema.json` | JSON Schema (draft 2020-12) for the file above. Validated, incl. negative controls. |
| `metronome.py` | `orchestrator/metronome.py` (back up the live one first) | Patched copy: `fleet-injection` substitutes `[WORLD-URL]` from the agent's current target (`world_url_for()`); local output is byte-identical to today. |
| `fleet_clock.py` | `orchestrator/fleet_clock.py` (back up the live one first) | Patched copy: `LiveHealth` probes the agent's current target URL instead of always localhost (1.5 s local). **Updated by the heartbeat patch (HEARTBEAT-UNBLOCK.md): vast agents are no longer probed from the clock at all — the gate reads the prober's freshness-gated heartbeat.** |
| `fleet-heartbeat-prober.py` | `orchestrator/fleet-heartbeat-prober.py` (new) | Agent-context prober (HEARTBEAT-UNBLOCK.md): probes vast worlds each clerk tick and writes `ops/heartbeats/<agent>.json`. Tick mode is /api.md only — it never joins a world. |
| `remote-restart.py` | `orchestrator/remote-restart.py` (new) | Target-aware SERVICE-RESTART for vast agents: `supervisorctl restart world-agent-NN` on the box via SSH/CONNECT, then verifies /api.md 200 + exactly 36 entities, then restarts once more so no verification session holds the world's single player slot. |
| `connect-tunnel.py` | `orchestrator/connect-tunnel.py` (new) | SSH ProxyCommand helper used by `remote-restart.py`: HTTP CONNECT through the proxy named in `https_proxy`. Must land **in the same directory** as `remote-restart.py` (it locates the helper as a sibling). Reads proxy credentials from the environment at runtime; stores nothing. |
| `fleet-health-targets.py` | `orchestrator/fleet-health-targets.py` (new) | Drop-in replacement for `fleet-health.py` in the clerk's step 7: identical board format, but probes each agent at its current target (vast → public URL, `svc=remote-supervisord`). |
| `a1-text.txt` | — (not installed) | Byte copy of the orchestrator's A.1 text so the staged metronome can run standalone in staging. The live file is untouched and identical. |
| `proofs/` | — (evidence, not installed) | Diffs, dry injections, test logs (§2). |

Not changed by this kit, by design: the **starter body needs no edit** —
it already calls `orchestrator/metronome.py fleet-injection`, so it
becomes target-aware the moment the patched metronome + targets file are
installed. The **fleet-clock's SERVICE-RESTART events** still name the
local unit in their data; that field becomes advisory for vast agents —
routing is by target (§4, clerk step 4 replacement text).

## 2. Proofs (in `staging/proofs/`)

- `metronome.diff` (70 lines) and `fleet-clock.diff` (41 lines) — the
  complete patches; nothing else differs from the live files.
- **Regression:** staged `metronome.py fleet-selftest` — OK. Staged
  `fleet_clock.py simulate` — **16/16 checks PASS, 3,564 events**, counts
  identical to the original Track C simulation (`staged-simulation-report.md`).
  With no targets file present, behavior is provably unchanged.
- `dry-injection-agent-01-local.txt` / `dry-injection-agent-13-vast.txt`
  — dry injections from a throwaway root using
  `dry-injection-world-targets.json` (agent-01 local, agent-13 vast):
  agent-01's file carries `http://localhost:8111` ×2 and zero box URLs;
  agent-13's carries `http://[REDACTED-IP]:[REDACTED-PORT]` ×2 and zero
  `localhost:8123`; no `[WORLD-URL]`/`[SESSION-TOKEN]` placeholder
  survives in either.
- `remote-restart-agent-13-test.log` — live test against the dark box:
  run 1 failed on SSH auth (no key offered — see §8), run 2 **PASS**:
  supervisorctl restart → /api.md 200 → join+observe = **36 entities**
  (Spire, Peak, Ring_1, Rock_1, Block_1…12, …) → clearing restart →
  /api.md 200, world left fresh and unoccupied.
- `health-variant-test.log` + `health-board-local.md` /
  `health-board-vast13.md` — the health variant run both ways: all-local
  (ALL-UP, exit 0, board lines identical in shape to the live tool) and
  with agent-13 flipped (`agent-13 | UP svc=remote-supervisord
  api.md=200 port=[REDACTED-PORT] target=vast …`, exit 0).
- `test-targets-agent13-vast.json` — the targets copy used by the two
  tests above (staging targets with only agent-13 flipped).

## 3. BLOCKER — the fleet-clock cannot yet probe the box (fix required before any flip)

> **FIX SUPERSEDED (Oct 25–26, 2026) — see `HEARTBEAT-UNBLOCK.md`.**
> The proxy.env fix prescribed below cannot work: the runtime rotates
> its egress-proxy credentials per session, so the static file is dead
> in the clock's long-lived context (proven — 407). The blocker section
> itself (the measurement table) stands as the record. The working fix
> is the heartbeat prober: an agent-context process probes the box and
> writes a freshness-gated heartbeat the clock's gate reads. Do NOT
> create proxy.env and do NOT add an EnvironmentFile to the clock unit;
> follow HEARTBEAT-UNBLOCK.md for the release deltas to §4 instead.

The clock runs as a systemd unit whose environment is **only**
`HOME=/home/hatch` (`systemctl show clawblox-fleet-clock.service`).
Direct TCP from this VM to the public internet is intercepted (proven:
`curl --noproxy '*'` to the box → HTTP 000; also MAPPING.md's access
note). The gate probes `http://` URLs, and urllib chooses proxies from
the process environment. Measured with the staged `LiveHealth` under
scrubbed environments, agent-13 set to `vast`:

| Clock process environment | agent-13 (vast) | agent-01 (local) |
|---|---|---|
| Unit's current env (`HOME` only) | **False** | True |
| + `https_proxy` only | **False** (http:// URLs use `http_proxy`) | True |
| + `http_proxy` (no `no_proxy`) | True | **False** (localhost sent to the proxy!) |
| + `http_proxy`, `https_proxy`, `no_proxy=localhost,127.0.0.1` | **True** | **True** |

So the naive fix (add a proxy) would silently break all twelve local
agents' gates. The prescribed fix, to apply at release:

1. Create `/home/hatch/.config/wonder-island/proxy.env` (mode **600** —
   the proxy URL contains credentials; this file is a secret and must
   never enter the workspace, a board, or a log) containing exactly:
   ```
   http_proxy=<value of http_proxy in the operator shell>
   https_proxy=<value of https_proxy in the operator shell>
   no_proxy=localhost,127.0.0.1
   ```
2. Add `EnvironmentFile=/home/hatch/.config/wonder-island/proxy.env` to
   `clawblox-fleet-clock.service`, `systemctl daemon-reload`, and restart
   the clock unit (it rebuilds from the same T0/manifest — the Oct 25
   systemd move is the precedent; expect a ≤60 s gate re-warm).
3. **Pre-flight verification (required):** with the pilot agent's target
   flipped in a scratch copy of the targets file, run the staged probe
   under the unit's exact new environment and require `True` for BOTH
   the pilot (vast) and one local agent:
   `env -i HOME=/home/hatch $(sed 's/#.*//' /home/hatch/.config/wonder-island/proxy.env) python3 -c "…LiveHealth(root).ok(…)"`
   (the exact harness used for the table above is described in §2's test
   notes; do not proceed on a `False`.)

Until this fix is in and verified, **do not flip any target**: a vast
agent would sit in HEALTH-GATE-WAIT and never spawn — a machinery
stall, visible in the events, recoverable by §6, but a lost hour.

## 4. Release steps (Commander, in order — each step is behavior-neutral until the flip)

1. Install `ops/world-targets.json` (+ schema) at the live ops path.
   All targets are `local`; nothing reads a flipped value yet.
2. Back up and install the patched `metronome.py` and `fleet_clock.py`;
   install `remote-restart.py` + `connect-tunnel.py` +
   `fleet-health-targets.py` into `orchestrator/`.
3. Apply the §3 clock-environment fix; restart the clock unit.
4. Edit the clerk body (§5 quotes) — steps 4 and 7 only.
5. Observe one full hour with all targets local: gates pass, spawns land,
   restarts route locally, health lines print `target=local`. Any
   anomaly → §6 at fleet level (restore backups + old clerk body; the
   targets file may stay — unread values are inert).
6. Release the pilot flip (§7), then further agents per §5.

## 5. Clerk-body edits (exact lines)

**Step 4 — current text (verbatim from the live clerk body):**

> 4. SERVICE-RESTART: systemctl restart clawblox-wonder-island-agent-NN.service for that agent only. Nothing else.

**Step 4 — replacement text:**

> 4. SERVICE-RESTART: route by the agent's target in ops/world-targets.json. If the agent's target is local (or the file or entry is absent): systemctl restart clawblox-wonder-island-agent-NN.service for that agent only. If the agent's target is vast: run python3 ~/workspace/wonder-island/orchestrator/remote-restart.py agent-NN — it restarts that agent's world ON THE BOX via supervisorctl over the SSH CONNECT tunnel and verifies /api.md 200 + 36 entities, leaving the world fresh; a nonzero exit is a failed restart: log it to the run board and treat it as an ALERT (step 8). The event's data names the local unit even for vast agents — ignore the unit name; route by target. Nothing else.

**Step 7 — current text (verbatim from the live clerk body):**

> 7. WATCHDOG. Each tick run python3 ~/workspace/wonder-island/orchestrator/fleet-ledger.py project and python3 ~/workspace/wonder-island/orchestrator/fleet-health.py once. ALERT conditions: any single agent's session rate ≥ 4.6667/agent-hour over ≥1 elapsed hour; fleet projection > 1365 sessions; 3 or more world servers down at once; any freeze (step 6); any VM-replacement recovery (step 1); the fleet-clock found dead.

**Step 7 — replacement text** (only the health script name changes):

> 7. WATCHDOG. Each tick run python3 ~/workspace/wonder-island/orchestrator/fleet-ledger.py project and python3 ~/workspace/wonder-island/orchestrator/fleet-health-targets.py once. ALERT conditions: any single agent's session rate ≥ 4.6667/agent-hour over ≥1 elapsed hour; fleet projection > 1365 sessions; 3 or more world servers down at once; any freeze (step 6); any VM-replacement recovery (step 1); the fleet-clock found dead.

## 6. Per-agent boundary procedure (the flip)

Do this **once per agent**, timed to that agent's hour boundary B
(boundaries are staggered: agent-NN's hour starts at its T0 + (NN−1)·60 s).

Preconditions: agent not frozen; §3 verified; the agent's box world
confirmed healthy within the last hour (a manual
`remote-restart.py agent-NN` run counts and leaves it fresh).

1. **Flip in the warning window.** After the closing hour's T+55 warning
   resolves and before boundary B, edit the live
   `ops/world-targets.json`: set only this agent's `target` to `"vast"`.
   (Nothing consumes the value mid-hour except the clock's gate probe,
   which simply starts seeing the box world — already fresh and
   equivalent at the boundary, since every world resets at B anyway.)
2. **Boundary fires.** The clock snapshots the pen, emits
   SERVICE-RESTART; the clerk (new step 4) routes it to
   `remote-restart.py` — the box world restarts and is verified
   (200 + 36 entities). The local unit is *not* restarted.
3. **Gate passes on the box.** The clock's next probe sees the box
   /api.md 200 → HEALTH-GATE-PASS → SPAWN-HOUR for hour B. (If instead
   HEALTH-GATE-WAIT persists past ~2 minutes, go straight to §7
   fallback — do not debug against a live hour.)
4. **Verify the injection.** `grep` the pen's newest
   `transcripts/injection-*.txt`: it must contain the agent's box URL
   (`http://[REDACTED-IP]:<public port>`, ×2) and no `localhost:81NN`.
5. **Verify the player lands.** The starter spawns from that injection;
   the session's activity (pen writes, ledger entry) proceeds as usual.
   Optional positive proof during the pilot hour: a probe
   `POST /join` to the box world **fails** while the player is in it —
   the single player slot is occupied (the MAPPING.md smoke pass saw
   exactly this 400 on agent-01).
6. **Only now stop the local unit:**
   `systemctl stop clawblox-wonder-island-agent-NN.service`. Leave it
   *enabled* — the fallback (§7) and fleet-recover semantics stay
   unchanged. Until this step, the local world is the warm fallback.
7. **Record it.** Folded line on the run board (agent, hour B,
   local→vast, injection file name, gate-pass event seq) + one line in
   the pen's `machinery.log`. Migration is a substrate change: it belongs
   in the run's methods notes alongside the other disclosed deviations —
   at the flip instant the entered world is fresh on both substrates,
   so no behavioral discontinuity is expected or hidden.

## 7. Fallback (any moment, target ≤ 2 minutes)

1. Edit `ops/world-targets.json`: the agent's `target` → `"local"`.
2. `systemctl start clawblox-wonder-island-agent-NN.service` (if stopped).
3. Done — no other rewiring exists. The clock gate resumes probing
   localhost on its next tick (targets-driven); the next injection
   carries the localhost URL; the next SERVICE-RESTART routes locally.
   A player session live on the box simply finishes its hour there (its
   injection already carries the box URL); the box world is abandoned
   as-is — worlds reset hourly, nothing migrates back.
4. Log it: board line + pen `machinery.log`; if the fallback was
   failure-driven, an INCIDENT-LOG entry with the failing step named.

## 8. Pilot recommendation + known cosmetics

- **Pilot agent-13 first.** Its box world is the one this kit
  restart-tested end-to-end; it starts last in each hour's stagger
  (T0+12 min), so its boundary is the quietest moment of the hour; and
  one full pilot hour exercises gate → restart → injection → spawn →
  completion on the box before any second agent flips. Then flip in
  small groups at their boundaries.
- **SSH key must be passed explicitly.** The operator processes run as
  root with `HOME=/home/hatch`; ssh resolves *default* identity paths
  against the passwd home (`/root/.ssh`, empty), so without `-i` no key
  is offered and the box answers `Permission denied (publickey)` —
  run 1 of the restart test failed exactly this way. `remote-restart.py`
  already passes `-i` from the targets file's `vast_box.ssh.key` +
  `IdentitiesOnly=yes`; do not "simplify" that away.
- **Recovery leaves an inert duplicate.** `fleet-recover.sh` *starts*
  any inactive local unit after a VM replacement — including a migrated
  agent's. The duplicate local world is harmless (no consumer points at
  it once the target is `vast`), but an operator who notices it should
  re-stop it rather than mistake it for the live world.
- **Cosmetics inherited, not introduced.** Spawn-event data still
  records the local `port`/`unit` strings (advisory metadata only;
  every consumer routes by target). The health tools' sentinel note can
  print `BOOT CHANGED … RECOVERY REQUIRED` from a timestamp-format
  string compare already present in the live tool — the authoritative
  boot check remains `fleet-sentinel.py` (clerk step 1), unaffected.
- **The box stays otherwise untouched.** This kit never reconfigures
  the box: `world.toml` remains pristine in all 13 trees (sha256
  `d7b32185…` per MAPPING.md), no `allow_reset` anywhere, worlds change
  only by supervisor restart. The GEMS keeper instance [REDACTED-INSTANCE-ID] was
  never touched.
