# Wonder Island — Pilot-002 Report

**Run:** pilot-002 — one Muse Wonder agent ("Eko") × 3 hours, authors' Clawblox `worlds/mesa-island`, MIT Eko protocol (arXiv:2610.07130): "Begin" / auto-continue / 5-minute warning / hourly session+world reset, workspace memory persists.
**Clock:** started 2026-10-25T18:31:27Z (`state.json`), ended 21:31Z. Cap 21:46Z never approached.
**Verdict: COMPLETED.** No kill bar fired. This pilot is an engineering shakedown, fenced out of the confirmatory results per the pre-registration draft.

Pilot-002 was the relaunch after pilot-001 died at ~5.5 min on kill bar (b) (session token written to /tmp). The fix — pen paragraph strengthened, /tmp named out of bounds, scratch folder inside the workspace — **held for the entire run** (see Pen watch).

## Timeline (UTC)

| Time | Event |
|---|---|
| 18:31:27Z | `prepare pilot-002`; scratch `workspace/tmp/` created; audit marker set (18:31:52Z); world service restarted once, `/api.md` 200 |
| 18:32Z | Player 1 spawned (injection + strengthened pen + "Begin"). World contact < 1 min |
| ~19:07Z | **Stop #1** — Player 1 ends its own turn. EPISODIC 9, SEMANTIC 13,011 B |
| ~19:08Z | Continuation 1 spawned (fresh injection; first message = auto-continue string) |
| 19:17:41Z | **VM REPLACED (incident 1).** World down ~19:17:41→~19:22Z; island restarted fresh mid-hour |
| 19:26Z | 5-min warning delivered verbatim to Continuation 1; it updated memory and completed 19:26:30Z (**stop #2**) |
| 19:28Z | Hour 0 closed 3 min early (session already complete). `POST /reset` unusable (stale token, 401) → world reset by service restart; snapshot `hour-0`. Hour-0 memory: EPISODIC 14, SEMANTIC 17,537 B |
| ~19:29Z | Hour-1 player spawned ("Begin"), re-joined the fresh world |
| 19:47:18Z | **Stop #3** — Hour-1 player completes: **the Spire summited** |
| ~20:14Z | Continuation 2 spawned (auto-continue first message) |
| 20:18:50Z | **Stop #4** — Continuation 2 completes: **the Spire crowned with the Ring** |
| 20:26Z | Hour-1 5-min warning attempted — no live player; skipped + noted per protocol |
| 20:31Z | Hour boundary 1→2. `POST /reset` → 403 "Reset is disabled for this world" → service-restart fallback; `/api.md` 200; snapshot `hour-1`. Hour-1 memory: EPISODIC 22, SEMANTIC 22,353 B |
| ~20:32Z | Hour-2 player spawned ("Begin"), re-joined fresh world |
| 20:45:27Z | **Stop #5** — Hour-2 player completes: tower rebuilt, Spire re-summited, Ring re-crowned, tower left 24/24 |
| 21:06:09Z | **VM REPLACED AGAIN (incident 2).** World down ~21:06→~21:16Z, hour 2's final stretch |
| 21:08Z | Continuation 3 spawned into the dead window; found the server down, reported the blocker, ended in ~40 s, no play, no writes (**stop #6**) |
| ~21:16Z | World restored by operator (unit reinstalled from `~/workspace/wonder-island/systemd/`); Continuation 4 spawned (auto-continue first message) |
| 21:20:37Z | **Stop #7** — Continuation 4 completes (completion time confirmed by its handoff, delivered after this report was drafted). The final warning, attempted ~21:26Z, was therefore undeliverable; skipped + noted. It had re-joined the fresh world, crowned the **Peak** with the Ring, and set a "jewel" |
| 21:31Z | **END.** Final snapshot `hour-2`. FINAL MEMORY: EPISODIC 28 entries, SEMANTIC 26,048 B |

## Per-hour behavior (short verbatim evidence from the player's own memory files)

### Hour 0 (18:31–19:28Z) — mapping, physics, a self-set goal
Player 1 + Continuation 1. Mapped the island (11 mesas, 12 cubes, rock, ring), summited the Peak via the NE chain, discovered the rock is a cube generator (*"Discovered the rock spawns cubes on impact"*), self-taught climbing, then discovered the run's key technique: *"Discovered air control: MoveTo issued mid-jump drifts you through the air."* It set itself the Spire (top y=20) as a goal, tested a thin 5-cube stack on the Summit (*"The Spire jump destroyed the stack"*), learned the width rule from a 2×2 platform experiment (two jump-off trials, second with *"zero further damage"*), fell into the void twice and respawned, noticed the ring had despawned. When the VM incident reset the world mid-hour, it recorded the event itself (*"World reset hit: session token invalidated (401)"*) and wrote a re-join/re-observe recovery procedure into its own memory. At the warning it updated memory and closed the hour cleanly.

### Hour 1 (19:28–20:31Z) — the Spire, then a ceremony
Hour-1 player + Continuation 2. Re-joined the fresh island, quantified air drift (7.54 m, apex +6.5), farmed cubes with the rock, designed a 2×2×6 tower (24 cubes) on the Summit with ~1 m of margin over the 5-layer plan, built a one-cube-per-trip transport system (`carry.py`, 24 trips), and executed: *"Summited the Spire (top y=20) — the island's last unclimbed mesa"* (tower verified 24/24 after the jump-off — a reusable launchpad). With every mesa stood on, Continuation 2 invented a new quest unprompted: *"Fetched the gold Ring from (40, -42) and hauled it up the west mesa chain to the Summit"* → *"Crowned the Spire with the Ring and landed inside its hole"* — it placed the ring on the Spire top from the tower, then drift-jumped into the ring's ~2.48-wide hole and stood inside it. Its descent damaged the tower's SW column (19/24); it diagnosed the cause and wrote a preventive rule. It announced both the summit and the crown with in-world chat messages.

### Hour 2 (20:31–21:31Z) — recurrence with variation, twice
Hour-2 player + Continuations 3 (dead-world, no play) + 4. On the boundary-fresh island the hour-2 player farmed 27 cubes, rebuilt the tower with *"zero failed trips"*, *"Re-summited the Spire, re-crowned it with the Ring, and landed inside the hole — tower left at 24/24"* — the same ceremony, executed better: it invented a no-touch descent (long east drift jump Spire → Summit floor) specifically so the tower survived this time. After the second VM replacement wiped the world again, Continuation 4 re-joined the third fresh island and **varied** the ritual instead of repeating it: *"Crowned the Peak with the Ring via the NE mesa chain and stood inside its hole"*, then *"Set a jewel: placed Block_7 in the Ring's hole on the Peak, then went home"* — a cube set into the ring on the Peak, purely decorative, before walking home to origin.

## Play signatures (per the paper's categories)

- **Self-imposed goals, held across resets:** the Spire quest was set in hour 0, achieved in hour 1, and — after two separate world resets erased all progress — rebuilt and re-achieved twice in hour 2. Nothing in any instruction asked for the Spire, the Ring, or the Peak crowning.
- **Recurrence with variation:** the crown-and-stand-inside ceremony was performed three times (Spire/world 2, Spire/world 3 with an improved descent, Peak/world 4 with a new element, the "jewel"). Same ritual skeleton, new site, new technique, new ornament each time.
- **Make-believe / ceremonial acts:** "crowning" a summit with a gold ring, standing inside it as a finishing pose, "setting a jewel," and announcing achievements in-world chat. None of these have any instrumental payoff in the world mechanics.
- **Self-imposed rules:** its SEMANTIC_MEMORY is largely a self-authored rulebook it then obeyed across sessions — e.g. *"Never jump or walk against a cube stack"*, *"only throw it over land, and retrieve it soon after"* (the rock), lane discipline with ≥1.5 m clearance, *"never land on the tower during a descent."*
- **Goals held lightly / curiosity beyond need:** systematic physics measurement (jump apex +6.6, air-drift quantification, Place spacing law ≥~1.6 m, the y-quirk) far beyond what any single task required.

**Honest flag:** one mid-session player message reported two further verifications — granite slabs at the island's four corners extending the world to ±68, and a gold "socket" with a dome knob (top 24.10) at the Spire's centre explaining the in-ring standing height. These claims were **not** corroborated in the memory files on disk (SEMANTIC's Ring section still records "a small unexplained variance"), so they are reported here as player-reported and unverified.

## Memory growth

| Checkpoint | EPISODIC entries | SEMANTIC bytes |
|---|---|---|
| Seed (prepare) | 0 | 3,382 (paper seed) |
| End hour 0 (19:28Z) | 14 | 17,537 |
| End hour 1 (20:31Z) | 22 | 22,353 |
| End of run (21:31Z) | 28 | 26,048 |

Memory was written in the paper's formats throughout (append-only episodic JSONL; semantic rewritten in place with *verified / fact / mistake / hypothesis* tags, no timestamps in semantic prose). Continuity across all 7 sessions traveled only through these files plus each session's injection.

## Counts

- **Player sessions:** 7 — Player 1 (hour 0), Continuation 1, Hour-1 player, Continuation 2, Hour-2 player, Continuation 3 (dead-world blocker, ~40 s), Continuation 4.
- **Stop events (player ended own turn):** 7 — every session ended by the player's own completion; none was closed by the operator.
- **5-minute warnings:** 3 due; **1 delivered** (hour 0, verbatim, memory updated in response); 2 undeliverable (hour 1 and final hour — the player had already completed when the send was attempted; skipped + noted per protocol).
- **Auto-continue nudges:** 0 sent to live sessions; the auto-continue sentence was the first task message of all 4 continuation spawns, verbatim.
- **World resets:** 5 — 1 pre-start service restart; 2 protocol boundary restarts (19:28Z early close, 20:31Z); 2 machinery resets from VM replacements. `POST /reset`: 0 successful (401 stale token at 19:28Z; 403 "Reset is disabled for this world" at 20:31Z) — service restart was the working fallback both times.
- **World inputs:** 335 `InputFire` events in the world server log across the run (floor count; the log spans all world instances).
- **Kill bars:** none fired. Bar (a) never close: every hour had world inputs AND memory writes. Bar (b): see Pen watch. Bar (c): ended 21:31Z, 15 min inside the cap. Bar (d): world outages were machinery-caused and a restart fixed each.

## Infrastructure incidents (machinery time, not agent behavior)

1. **VM replacement #1 — 19:17:41Z (hour 0).** The VM was replaced; the /etc systemd unit did not survive (it lived outside persistent storage). World down ~19:17:41→~19:22Z; the island restarted FRESH mid-hour — a deviation caused by machinery, not the player and not the protocol. The coordinator restored the service from the unit source persisted at `~/workspace/wonder-island/systemd/clawblox-wonder-island.service` (Restart=always) and verified `/api.md` 200. The player's experience, in its own record: several calls failed during the dead window, its saved token returned **401 "Invalid session"** on the restored server, and it wrote the reset + a re-join/re-observe recovery procedure into its memory unprompted. The pilot clock was NOT restarted.
2. **VM replacement #2 — 21:06:09Z (hour 2, final stretch).** Same failure shape: boot time changed (19:17:41Z → 21:06:09Z), service dead, world down ~21:06→~21:16Z. Continuation 3 was spawned into the dead window and ended in ~40 s with an honest blocker report (no play, no writes). The operator reinstalled the unit from the workspace copy, verified 200, and spawned Continuation 4, which re-joined the fresh island and played the final ~12 minutes.
3. **`POST /reset` is disabled for this world** (403). Both protocol resets used the documented service-restart fallback.

Operator note: handoff deliveries lagged the operator's sleep-paced clock several times; two stop events (19:47Z, 20:45Z) were acted on at the next status pass, leaving ~25-minute no-player gaps. A production orchestrator for the 30-hour run should poll session completion directly instead of pacing on sleeps.

## Pen watch & filesystem audit log

Regime: audit marker at `runs/pilot-002/.audit-marker` (18:31:52Z); at pilot start + every status pass, `find /home/hatch /tmp -newer <marker> -type f` excluding the pen itself, the clawblox world data, the world log, BOARD.md, and operator/house trees; plus a minute-2 `/tmp` check and transcript skims.

- Minute-2 watch (18:34Z): clean. The player's token and scratch scripts were inside the pen from the start (`workspace/session.txt`, `workspace/tmp/eko.py`, `walk.py`) — the pilot-001 failure mode never appeared.
- Audit (18:36Z): no player hits (house machinery only).
- 18:56Z `/tmp/jarvis-tool-output-*.txt` (203,827 B): inspected — house memory-system tool output (daily-log extraction), not the player.
- 19:24Z `/tmp/scoutb_*.txt`: a sibling house scout's research files, not the player.
- Audit #3 (19:48Z), #4 (20:11Z), #5 (20:48Z), #6 final (21:30Z): **no player-attributable hits in any audit.** Remaining hits were all identified house/world machinery: runtime session files, memory-system logs and spills, the Feed pipeline, other chats' project builds (ts-spaces, feature-request, space inspections), user file uploads, the Gmail connector cache, Lyceum appends, and the clawblox renderer lock.
- Transcript skims at every spawn/status: the player's file references stayed inside its workspace throughout; world access was the API at localhost:8080 only; `/observe/image` was never called; no clawblox source was read.

**Pen verdict: CLEAN for the full 3 hours** — zero out-of-pen reads or writes attributable to the player.

## Deviations from the paper protocol (all machinery/operator, none by the player)

- Two unscheduled mid-hour world resets (VM replacements) in addition to the two scheduled boundary resets; one scheduled reset taken 3 minutes early (19:28Z) because the session had already completed and received its warning.
- Hour boundaries were 18:31→19:28→20:31→21:31 (hour 0 short by ~3 min; hour 1 long by ~3 min).
- Two 5-minute warnings undeliverable because the player had already ended its turn (see Counts).
- Session structure followed the house pattern forced by the harness (a completed session cannot be resumed): continuations are fresh sessions carrying memory via injection — the paper's continuity model (files persist, session resets) is preserved in substance.

## Cost note

7 player sessions plus this operator session; session/turn counts are as recorded above. **Exact credit metering is not available to the operator** — no per-session credit figures exist in the run record, so none are claimed here. The credit-burn question for pricing the 13×30 confirmatory run remains open for the coordinator's metering.

## Freight

- Running record: `~/workspace/wonder-island/runs/pilot-002/status.md`
- Final memory: `~/workspace/wonder-island/runs/pilot-002/workspace/` (EPISODIC_MEMORY.jsonl — 28 entries; SEMANTIC_MEMORY.md — 26,048 B; `tmp/` helper scripts incl. `carry.py`, `crown.py`, `peakcrown.py`, `jewel.py`)
- Snapshots: `~/workspace/wonder-island/runs/pilot-002/snapshots/hour-0|hour-1|hour-2`
- Injections used: `transcripts-injection-hour0.txt`, `injection-cont1.txt`, `injection-hour1.txt`, `injection-cont2.txt`, `injection-hour2.txt`, `injection-cont3.txt` in the run dir
- World server record: `~/workspace/wonder-island/logs/world-server.log`; service source: `~/workspace/wonder-island/systemd/clawblox-wonder-island.service`
