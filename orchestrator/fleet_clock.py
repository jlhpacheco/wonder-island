#!/usr/bin/env python3
"""fleet_clock.py — the fleet clock for the Wonder Island confirmatory run.

FLEET-PLAN §3, Track C. A dumb clock with per-agent state machines. It NEVER
messages an agent and NEVER spawns a session: it emits *events* (files under
runs/confirmatory/events/) that operator sessions — Helmholtz — consume.
Spawning and all verbatim-string delivery (Begin / auto-continue / the
5-minute warning) stay with the Commander, per orchestrator-spec §7.

What the clock does:
  * holds per-agent hourly state machines off the manifest's T0 offsets
    (agent-NN starts at fleet T0 + (NN-1)*60 s, port 8110 + NN);
  * POLLS session completion (plan D3) instead of pacing on sleeps — when the
    operator's session-state file reports a completion inside an open hour, a
    SPAWN-CONTINUATION event is queued immediately;
  * at T+55 queues SEND-WARNING (or resolves WARNING-UNDELIVERABLE when no
    session is open, per pilot precedent);
  * at T+60 runs the boundary job in order: BOUNDARY-CLOSE -> snapshot
    (metronome, refuse-to-overwrite) -> SERVICE-RESTART event -> health-gate
    -> SPAWN-HOUR with a fresh injection (fresh token) saved to the pen's
    transcripts/ before the event fires;
  * health-gates EVERY spawn: no spawn event fires unless that agent's server
    answered GET /api.md 200 within the last 60 s — and after a restart, only
    on a 200 observed *after* the restart (dead-window spawns are forbidden,
    pilot-002 Continuation 3).

Operator contract (live mode): the operator signals session lifecycle by
writing the pen's session-state.json — use the mark subcommand:
  fleet_clock.py mark --agent agent-01 --live       # a session is running
  fleet_clock.py mark --agent agent-01 --complete   # it finished (count + 1)

Modes:
  run       live clock (detached, workspace-resident; logs to
            ~/workspace/wonder-island/logs/fleet-clock.log). Started by the
            Commander at the GO gate — never during the build.
  simulate  the whole 30-hour schedule dry-runs in fast-forward under a temp
            root with spawns stubbed (plan §3C.4): proves boundary ordering,
            the 60 s stagger, and event formats without spending a credit.
  mark      operator session-state signalling (above).

Python 3 standard library only.
"""

import argparse
import io
import json
import random
import shutil
import sys
import tempfile
import time
import urllib.request
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metronome  # noqa: E402  (house tooling, same directory)

HOUR_S = 3600
WARNING_AT_S = 3300  # T+55:00
HEALTH_FRESH_S = 60
HEALTH_FAIL_ALERT_S = 600
EPOCH_2026_10_26 = datetime(2026, 10, 26, tzinfo=timezone.utc).timestamp()


def iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------- manifest

def _pick(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def load_manifest(path: Path):
    """Normalize FLEET-MANIFEST.json (Track B) into agent dicts:
    {id, port, unit, pen, t0_offset_s}. Key spellings are tolerated per the
    plan's field list; ports and offsets fall back to the plan's scheme."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "agents" in raw:
        entries = raw["agents"]
        fleet_t0 = _pick(raw, "t0_epoch", "t0")
    elif isinstance(raw, dict):
        entries = [dict(v, id=k) for k, v in raw.items() if isinstance(v, dict)]
        fleet_t0 = None
    else:
        entries = raw
        fleet_t0 = None
    conf = Path(path).resolve().parent
    agents = []
    for e in entries:
        aid = _pick(e, "id", "agent_id", "name")
        nn = metronome.agent_number(aid)
        pen = _pick(e, "pen", "pen_path", "pen_dir")
        if pen:
            pen = Path(pen)
            if not pen.is_absolute():
                pen = conf / pen
        else:
            pen = conf / aid
        agents.append({
            "id": aid,
            "port": int(_pick(e, "port", default=8110 + nn)),
            "unit": _pick(e, "unit", "unit_name", default=f"clawblox-wonder-island-{aid}.service"),
            "pen": pen,
            "t0_offset_s": int(_pick(e, "t0_offset_s", "t0_offset_seconds",
                                     "offset_seconds", "t0_offset", default=(nn - 1) * 60)),
        })
    agents.sort(key=lambda a: a["id"])
    return agents, fleet_t0


# ---------------------------------------------------------------- sink

class EventSink:
    """Append-only JSONL: one file per agent + one fleet log. Every event
    carries agent id, agent wall-clock, and fleet wall-clock."""

    def __init__(self, conf: Path):
        self.conf = conf
        self.events_dir = conf / "events"
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.seq = 0
        fleet_log = self.events_dir / "fleet.jsonl"
        if fleet_log.exists():  # resume numbering after a clock restart
            self.seq = sum(1 for _ in fleet_log.open(encoding="utf-8"))

    def emit(self, agent_id, etype, fleet_now, agent_t0, hour=None, data=None):
        self.seq += 1
        evt = {
            "seq": self.seq,
            "type": etype,
            "agent": agent_id,
            "fleet_time": iso(fleet_now),
            "fleet_elapsed_s": round(fleet_now - self.fleet_t0, 3) if self.fleet_t0 else None,
            "agent_elapsed_s": round(fleet_now - agent_t0, 3) if agent_t0 else None,
            "hour": hour,
            "data": data or {},
        }
        line = json.dumps(evt, ensure_ascii=False) + "\n"
        adir = self.events_dir / agent_id
        adir.mkdir(exist_ok=True)
        with (adir / "events.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(line)
        with (self.events_dir / "fleet.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(line)
        return evt

    fleet_t0 = None


# ------------------------------------------------------------ providers

class LiveHealth:
    def ok(self, agent_id, port):
        try:
            req = urllib.request.Request(f"http://localhost:{port}/api.md", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False


class LiveSessions:
    """Reads the operator-maintained session-state.json in each pen."""

    def __init__(self, agents):
        self.pens = {a["id"]: a["pen"] for a in agents}

    def obs(self, agent_id):
        f = self.pens[agent_id] / "session-state.json"
        if not f.exists():
            return {"live": False, "completions": 0}
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            return {"live": bool(d.get("live")), "completions": int(d.get("completions", 0))}
        except Exception:
            return {"live": False, "completions": 0}


# ---------------------------------------------------------------- engine

class AgentState:
    def __init__(self, spec, t0):
        self.spec = spec
        self.id = spec["id"]
        self.t0 = t0
        self.phase = "PRE"          # PRE | OPEN | WAIT_HEALTH | DONE
        self.started = False
        self.open_hour = None       # hour index currently open
        self.opened_hours = set()
        self.boundaries_done = 0    # boundaries processed (closing hour b-1)
        self.warning_hour = -1      # last hour a warning resolution fired for
        self.completions_seen = 0
        self.pending_hour = None    # hour awaiting a post-restart spawn
        self.restart_time = None
        self.fail_alerted = False
        self.gate_wait_noted = False
        self.pending_continuation = False
        self.last_health_ok = False
        self.last_health_time = 0.0


class Engine:
    def __init__(self, root, agents, fleet_t0, sink, health, sessions, on_event=None):
        self.root = Path(root)
        self.fleet_t0 = fleet_t0
        self.sink = sink
        self.sink.fleet_t0 = fleet_t0
        self.health = health
        self.sessions = sessions
        self.on_event = on_event
        self.states = {a["id"]: AgentState(a, fleet_t0 + a["t0_offset_s"]) for a in agents}
        self.log_lines = []

    # -- helpers ------------------------------------------------------
    def emit(self, st, etype, now, hour=None, data=None):
        evt = self.sink.emit(st.id, etype, now, st.t0, hour=hour, data=data)
        self.log_lines.append(f"{evt['fleet_time']} {st.id} {etype} hour={hour} {data or ''}")
        if self.on_event:
            self.on_event(evt)
        return evt

    def gate_recent(self, st, now):
        return st.last_health_ok and (now - st.last_health_time) <= HEALTH_FRESH_S

    def gate_after(self, st, ts):
        return st.last_health_ok and st.last_health_time > ts

    def spawn(self, st, now, hour, kind):
        """Build the injection (saved to transcripts/ first), then emit the
        spawn event. Hour spawns get a fresh token; continuations reuse the
        hour's token (metronome default)."""
        if kind == "SPAWN-HOUR":
            dest, _ = metronome.fleet_injection(self.root, st.id, new_token=True)
        else:
            dest, _ = metronome.fleet_injection(self.root, st.id)
        state = metronome.load_state(st.spec["pen"])
        self.emit(st, "HEALTH-GATE-PASS", now, hour=hour, data={"for": kind})
        evt = self.emit(st, kind, now, hour=hour, data={
            "session_seq": state["session_seq"],
            "injection": str(dest),
            "token": state["current_token"],
            "port": st.spec["port"],
        })
        st.opened_hours.add(hour)
        return evt

    # -- per-agent step ------------------------------------------------
    def step(self, st, now):
        if st.phase == "DONE" or now < st.t0:
            return
        elapsed = now - st.t0
        sched_hour = int(elapsed // HOUR_S)

        for _ in range(4):  # bounded catch-up loop (clock lag, sim ticks)
            progressed = False

            # (a) boundary due?
            b = st.boundaries_done + 1
            if b <= 30 and elapsed >= b * HOUR_S and st.phase != "WAIT_HEALTH":
                self.process_boundary(st, now, b)
                progressed = True
                if st.phase == "DONE":
                    return
            # (b) initial spawn
            if not st.started:
                if self.gate_recent(st, now):
                    hour = min(sched_hour, 29)
                    for skipped in range(hour):
                        self.emit(st, "HOUR-SKIPPED", now, hour=skipped,
                                  data={"reason": "clock started after this hour's T0"})
                    self.spawn(st, now, hour, "SPAWN-HOUR")
                    st.started = True
                    st.open_hour = hour
                    st.phase = "OPEN"
                    obs = self.sessions.obs(st.id)
                    st.completions_seen = obs["completions"]
                    progressed = True
                elif not st.gate_wait_noted:
                    self.emit(st, "HEALTH-GATE-WAIT", now, hour=0,
                              data={"reason": "no /api.md 200 within the last 60 s"})
                    st.gate_wait_noted = True
            # (c) post-restart spawn
            elif st.phase == "WAIT_HEALTH":
                if sched_hour > st.pending_hour and sched_hour < 30:
                    self.emit(st, "HOUR-SKIPPED", now, hour=st.pending_hour,
                              data={"reason": "server down across the boundary (D6)"})
                    st.pending_hour = sched_hour
                    st.restart_time = now
                    st.fail_alerted = False
                if sched_hour >= 30:
                    st.phase = "DONE"
                    self.emit(st, "AGENT-DONE", now, hour=st.pending_hour,
                              data={"reason": "run window ended while server down"})
                    return
                if self.gate_after(st, st.restart_time):
                    # spawn() itself emits HEALTH-GATE-PASS (after-restart
                    # freshness is what gate_after just proved).
                    self.spawn(st, now, st.pending_hour, "SPAWN-HOUR")
                    st.open_hour = st.pending_hour
                    st.pending_hour = None
                    st.phase = "OPEN"
                    obs = self.sessions.obs(st.id)
                    st.completions_seen = obs["completions"]
                    progressed = True
                elif (now - st.restart_time) > HEALTH_FAIL_ALERT_S and not st.fail_alerted:
                    self.emit(st, "HEALTH-GATE-FAIL", now, hour=st.pending_hour,
                              data={"reason": "no /api.md 200 within 600 s of restart"})
                    st.fail_alerted = True
            if not progressed:
                break

        if st.phase != "OPEN" or st.open_hour is None:
            return
        # (d) completion polling -> continuation (D3)
        obs = self.sessions.obs(st.id)
        if obs["completions"] > st.completions_seen:
            st.completions_seen = obs["completions"]
            if (not obs["live"] and sched_hour == st.open_hour
                    and elapsed < (st.open_hour + 1) * HOUR_S):
                st.pending_continuation = True
        if st.pending_continuation:
            if obs["live"] or sched_hour != st.open_hour:
                st.pending_continuation = False
            elif self.gate_recent(st, now):
                self.spawn(st, now, st.open_hour, "SPAWN-CONTINUATION")
                st.pending_continuation = False
        # (e) T+55 warning resolution
        if (st.warning_hour != st.open_hour
                and elapsed >= st.open_hour * HOUR_S + WARNING_AT_S):
            st.warning_hour = st.open_hour
            obs = self.sessions.obs(st.id)
            if obs["live"]:
                self.emit(st, "SEND-WARNING", now, hour=st.open_hour,
                          data={"string": "verbatim warning (Commander delivers)"})
            else:
                self.emit(st, "WARNING-UNDELIVERABLE", now, hour=st.open_hour,
                          data={"reason": "no session open — session complete (pilot precedent)"})

    def process_boundary(self, st, now, b):
        closing = b - 1
        self.emit(st, "BOUNDARY-CLOSE", now, hour=closing, data={"closing_hour": closing})
        if closing in st.opened_hours:
            with redirect_stdout(io.StringIO()):
                dest = metronome.fleet_snapshot(self.root, st.id)
            self.emit(st, "SNAPSHOT-DONE", now, hour=closing,
                      data={"snapshot": str(dest)})
        st.boundaries_done = b
        st.open_hour = None
        st.pending_continuation = False
        if b == 30:
            st.phase = "DONE"
            self.emit(st, "AGENT-DONE", now, hour=closing, data={"hours_completed": 30})
            return
        self.emit(st, "SERVICE-RESTART", now, hour=b,
                  data={"unit": st.spec["unit"], "for_hour": b})
        st.phase = "WAIT_HEALTH"
        st.pending_hour = b
        st.restart_time = now
        st.fail_alerted = False

    # -- driver ---------------------------------------------------------
    def tick(self, now):
        for st in self.states.values():
            st.last_health_ok = bool(self.health.ok(st.id, st.spec["port"]))
            if st.last_health_ok:
                st.last_health_time = now
        for st in self.states.values():
            self.step(st, now)

    def all_done(self):
        return all(st.phase == "DONE" for st in self.states.values())


# ------------------------------------------------------------ simulation

class SimWorld:
    """Stubbed sessions + health for the fast-forward dry run. Deterministic
    (seeded). Scripted cases, named so the proof covers the ugly paths:
      * agent-01, hour 0: the continuation pickup never lands -> the T+55
        warning resolves WARNING-UNDELIVERABLE (pilot precedent);
      * agent-05, boundary closing hour 2: /api.md stays down 100 s after the
        restart -> SPAWN-HOUR for hour 3 must wait for a fresh 200."""

    def __init__(self, agents, seed=13):
        self.rng = {a["id"]: random.Random(seed * 100 + metronome.agent_number(a["id"]))
                    for a in agents}
        self.now = 0.0
        self.live = {}          # agent -> (start, end)
        self.completions = {a["id"]: 0 for a in agents}
        self.restart_at = {}
        self.restart_count = {a["id"]: 0 for a in agents}
        self.first_session = {a["id"]: True for a in agents}

    # engine hook
    def on_event(self, evt):
        aid, etype = evt["agent"], evt["type"]
        if etype in ("SPAWN-HOUR", "SPAWN-CONTINUATION"):
            if aid == "agent-01" and evt["hour"] == 0 and etype == "SPAWN-CONTINUATION":
                return  # scripted: pickup never lands
            dur = self.rng[aid].uniform(240, 3500)
            if aid == "agent-01" and etype == "SPAWN-HOUR" and evt["hour"] == 0:
                dur = 1200.0  # scripted: completes at T+20:00
            self.live[aid] = (self.now, self.now + dur)
            if aid == "agent-01" and etype == "SPAWN-HOUR" and evt["hour"] == 1:
                self._plant_episodic(aid)
        elif etype == "SERVICE-RESTART":
            self.restart_at[aid] = self.now
            self.restart_count[aid] += 1
            self.live.pop(aid, None)  # boundary closes any live session

    def _plant_episodic(self, aid):
        pen = self.pen_of(aid)
        entry = {"timestamp": "2026-10-26T01:00:00Z",
                 "summary": "SIM-SUMMARY-MARKER planted in hour 1.",
                 "detail": "SIM-DETAIL-MARKER must never cross into an injection."}
        with (pen / "workspace" / "EPISODIC_MEMORY.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    pen_of = None  # set by simulate()

    def update(self, now):
        self.now = now
        for aid, (start, end) in list(self.live.items()):
            if now >= end:
                self.completions[aid] += 1
                del self.live[aid]

    def ok(self, agent_id, port):
        if agent_id == "agent-05" and self.restart_count.get(agent_id) == 3:
            if self.now - self.restart_at.get(agent_id, 0) < 100:
                return False
        return True

    def obs(self, agent_id):
        return {"live": agent_id in self.live,
                "completions": self.completions[agent_id]}


def simulate(seed=13, base=None, keep=False):
    base = Path(base) if base else Path(tempfile.mkdtemp(prefix="wonder-fleet-sim-"))
    root = base
    shutil.copytree(metronome.SEEDS, root / "agent-workspace")
    agents_spec = [{"id": aid, "port": metronome.agent_port(aid),
                    "unit": f"clawblox-wonder-island-{aid}.service",
                    "pen": str(metronome.conf_root(root) / aid),
                    "t0_offset_s": (metronome.agent_number(aid) - 1) * 60}
                   for aid in metronome.ALL_AGENTS]
    manifest = {"t0_epoch": EPOCH_2026_10_26, "agents": agents_spec}
    conf = metronome.conf_root(root)
    conf.mkdir(parents=True, exist_ok=True)
    (conf / "FLEET-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                              encoding="utf-8")
    with redirect_stdout(io.StringIO()):
        metronome.fleet_prepare(root, metronome.ALL_AGENTS)
    agents, fleet_t0 = load_manifest(conf / "FLEET-MANIFEST.json")

    world = SimWorld(agents, seed=seed)
    world.pen_of = lambda aid: metronome.fleet_pen(root, aid)
    sink = EventSink(conf)
    engine = Engine(root, agents, fleet_t0, sink, world, world, on_event=world.on_event)

    tick_s = 5.0
    now = fleet_t0
    end_limit = fleet_t0 + 31 * HOUR_S
    while not engine.all_done() and now <= end_limit:
        world.update(now)
        engine.tick(now)
        now += tick_s
    sim_seconds = now - fleet_t0

    events = [json.loads(l) for l in (conf / "events" / "fleet.jsonl")
              .read_text(encoding="utf-8").splitlines() if l.strip()]
    checks = verify_simulation(root, agents, events, world)
    if not keep:
        shutil.rmtree(root, ignore_errors=True)
    return checks, events, sim_seconds, root


def verify_simulation(root, agents, events, world):
    checks = []

    def check(name, ok):
        checks.append((name, bool(ok)))

    by_agent = {a["id"]: [e for e in events if e["agent"] == a["id"]] for a in agents}

    # 1. 30 hour-spawns per agent, hours 0..29 in order; 60 s stagger intact.
    ok_stagger, ok_hours = True, True
    for a in agents:
        spawns = [e for e in by_agent[a["id"]] if e["type"] == "SPAWN-HOUR"]
        if [e["hour"] for e in spawns] != list(range(30)):
            ok_hours = False
        nn = metronome.agent_number(a["id"])
        if not spawns or abs(spawns[0]["fleet_elapsed_s"] - (nn - 1) * 60) > 5:
            ok_stagger = False
    check("13 x 30 SPAWN-HOUR events, hours 0-29 in order per agent", ok_hours)
    check("60 s stagger intact (agent-NN first spawn at fleet_elapsed (NN-1)*60)", ok_stagger)

    # 2. Boundary ordering per agent.
    order_ok = True
    for a in agents:
        evs = by_agent[a["id"]]
        closes = [e for e in evs if e["type"] == "BOUNDARY-CLOSE"]
        if len(closes) != 30:
            order_ok = False
            break
        for h in range(30):
            seq = [e["type"] for e in evs]
            ic = next(i for i, e in enumerate(evs)
                      if e["type"] == "BOUNDARY-CLOSE" and e["hour"] == h)
            want = ["BOUNDARY-CLOSE", "SNAPSHOT-DONE"] + (
                ["AGENT-DONE"] if h == 29 else
                ["SERVICE-RESTART", "HEALTH-GATE-PASS", "SPAWN-HOUR"])
            if seq[ic:ic + len(want)] != want:
                order_ok = False
                break
            if h == 29 and any(e["type"] == "SERVICE-RESTART" and e["hour"] == 30 for e in evs):
                order_ok = False
    check("boundary order per agent: CLOSE -> SNAPSHOT -> RESTART -> GATE -> SPAWN (DONE at 30)", order_ok)

    # 3. Every spawn immediately gated.
    gate_ok = True
    for a in agents:
        evs = by_agent[a["id"]]
        for i, e in enumerate(evs):
            if e["type"] in ("SPAWN-HOUR", "SPAWN-CONTINUATION"):
                if i == 0 or evs[i - 1]["type"] != "HEALTH-GATE-PASS":
                    gate_ok = False
    check("every SPAWN-* immediately preceded by HEALTH-GATE-PASS", gate_ok)

    # 4. Continuations happened (polling path exercised) and respect completions.
    conts = [e for e in events if e["type"] == "SPAWN-CONTINUATION"]
    check(f"continuation polling exercised ({len(conts)} SPAWN-CONTINUATION events)", len(conts) > 100)
    over = False
    for a in agents:
        for h in range(30):
            n_cont = sum(1 for e in by_agent[a["id"]]
                         if e["type"] == "SPAWN-CONTINUATION" and e["hour"] == h)
            if n_cont > world.completions[a["id"]]:
                over = True
    check("continuations never exceed observed completions", not over)

    # 5. Warning resolution: exactly one per agent-hour; scripted case correct.
    warn_ok = all(
        sum(1 for e in by_agent[a["id"]] if e["type"] in ("SEND-WARNING", "WARNING-UNDELIVERABLE")
            and e["hour"] == h) == 1
        for a in agents for h in range(30))
    check("exactly one warning resolution per agent-hour (390 total)", warn_ok)
    a1 = by_agent["agent-01"]
    check("agent-01 hour 0 resolves WARNING-UNDELIVERABLE (scripted dead pickup)",
          any(e["type"] == "WARNING-UNDELIVERABLE" and e["hour"] == 0 for e in a1)
          and not any(e["type"] == "SEND-WARNING" and e["hour"] == 0 for e in a1))

    # 6. Health-gate delay: agent-05 hour-3 spawn waited out the 100 s outage.
    a5 = by_agent["agent-05"]
    rst = next(e for e in a5 if e["type"] == "SERVICE-RESTART" and e["hour"] == 3)
    spn = next(e for e in a5 if e["type"] == "SPAWN-HOUR" and e["hour"] == 3)
    check("agent-05 hour-3 spawn delayed >=100 s past restart (health-gate held)",
          spn["fleet_elapsed_s"] - rst["fleet_elapsed_s"] >= 100)

    # 7. Injection proofs (files survive in pens only if sim root kept; here
    #    read from the still-live temp root via transcripts).
    conf = metronome.conf_root(root)
    inj_ok, port_ok, detail_ok, token_ok = True, True, True, True
    for a in agents:
        pen = metronome.fleet_pen(root, a["id"])
        first = pen / "transcripts" / "injection-001.txt"
        if not first.exists():
            inj_ok = False
            break
        text = first.read_text(encoding="utf-8")
        if not text.startswith("You are a being living in your world."):
            inj_ok = False
        if f"http://localhost:{a['port']}" not in text:
            port_ok = False
    check("every agent's first injection saved under transcripts/ and opens with A.1", inj_ok)
    check("every first injection carries its own port (8111-8123)", port_ok)
    pen1 = metronome.fleet_pen(root, "agent-01")
    later = sorted((pen1 / "transcripts").glob("injection-*.txt"))[-1].read_text(encoding="utf-8")
    check("agent-01 later injection carries the planted episodic summary",
          "SIM-SUMMARY-MARKER" in later)
    check("agent-01 later injection never carries the episodic detail",
          "SIM-DETAIL-MARKER" not in later and "detail" not in later)
    evs1 = by_agent["agent-01"]
    h0 = [e for e in evs1 if e["type"] in ("SPAWN-HOUR", "SPAWN-CONTINUATION") and e["hour"] == 0]
    h1 = next(e for e in evs1 if e["type"] == "SPAWN-HOUR" and e["hour"] == 1)
    check("token constant within an hour, fresh across hours",
          len({e["data"]["token"] for e in h0}) == 1
          and h0[0]["data"]["token"] != h1["data"]["token"])

    # 8. Snapshots: 30 zero-padded hours per pen.
    snap_ok = all(
        len(list((metronome.fleet_pen(root, a["id"]) / "snapshots").glob("hour-*"))) == 30
        for a in agents)
    check("30 snapshots per pen (hour-00 .. hour-29)", snap_ok)

    # 9. Event format: required clocks on every event.
    fmt_ok = all(
        e.get("agent") and e.get("fleet_time") and e.get("fleet_elapsed_s") is not None
        and e.get("agent_elapsed_s") is not None and "type" in e
        for e in events)
    check("every event carries agent id + fleet wall-clock + agent wall-clock", fmt_ok)
    return checks


# ------------------------------------------------------------------ mark

def cmd_mark(root, agent_id, live):
    pen = metronome.fleet_pen(root, agent_id)
    f = pen / "session-state.json"
    cur = {"live": False, "completions": 0, "session": 0}
    if f.exists():
        try:
            cur.update(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    if live:
        cur["live"] = True
        cur["session"] = int(cur.get("completions", 0)) + 1
    else:
        cur["live"] = False
        cur["completions"] = int(cur.get("completions", 0)) + 1
    cur["updated_at"] = iso(time.time())
    tmp = f.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
    tmp.replace(f)
    print(f"{agent_id}: session-state -> {cur}")


# ------------------------------------------------------------------- cli

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Wonder Island fleet clock (Track C).")
    parser.add_argument("--root", default=str(metronome.ROOT))
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run")
    p.add_argument("--manifest", default=None)
    p.add_argument("--t0", type=float, default=None, help="fleet T0, epoch seconds")

    p = sub.add_parser("simulate")
    p.add_argument("--seed", type=int, default=13)
    p.add_argument("--base", default=None)
    p.add_argument("--keep", action="store_true")
    p.add_argument("--report", default=None)

    p = sub.add_parser("mark")
    p.add_argument("--agent", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--live", action="store_true")
    g.add_argument("--complete", action="store_true")

    p = sub.add_parser("check-manifest")
    p.add_argument("--manifest", required=True)

    args = parser.parse_args(argv)
    root = Path(args.root)

    if args.cmd == "mark":
        cmd_mark(root, args.agent, live=args.live)
        return 0

    if args.cmd == "check-manifest":
        agents, fleet_t0 = load_manifest(Path(args.manifest))
        for a in agents:
            print(f"{a['id']}  port={a['port']}  offset={a['t0_offset_s']}s  "
                  f"unit={a['unit']}  pen={a['pen']}")
        print(f"agents={len(agents)}  manifest_t0={fleet_t0}")
        return 0

    if args.cmd == "simulate":
        checks, events, sim_seconds, sim_root = simulate(
            seed=args.seed, base=args.base, keep=args.keep)
        failed = [n for n, ok in checks if not ok]
        for name, ok in checks:
            print(f"{'PASS' if ok else 'FAIL'}  {name}")
        counts = {}
        for e in events:
            counts[e["type"]] = counts.get(e["type"], 0) + 1
        print(f"simulation: {len(events)} events over {sim_seconds / 3600:.2f} fleet-hours "
              f"(virtual), counts={counts}")
        if args.report:
            lines = ["# Track C — fleet simulation report",
                     f"\nSeed 13 · virtual span {sim_seconds / 3600:.2f} fleet-hours · "
                     f"{len(events)} events · sim root {'kept at ' + str(sim_root) if args.keep else 'removed after verification'}",
                     "\n## Checks"]
            lines += [f"- {'PASS' if ok else 'FAIL'}  {n}" for n, ok in checks]
            lines.append("\n## Event counts")
            lines += [f"- {k}: {v}" for k, v in sorted(counts.items())]
            Path(args.report).write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"report written: {args.report}")
        if failed:
            print(f"simulation FAILED ({len(failed)} check(s))", file=sys.stderr)
            return 1
        print("simulation OK")
        return 0

    if args.cmd == "run":
        manifest = Path(args.manifest) if args.manifest else (
            metronome.conf_root(root) / "FLEET-MANIFEST.json")
        agents, manifest_t0 = load_manifest(manifest)
        fleet_t0 = args.t0 or manifest_t0
        if not fleet_t0:
            raise SystemExit("error: no fleet T0 (pass --t0 or set t0_epoch in the manifest)")
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        sink = EventSink(metronome.conf_root(root))
        engine = Engine(root, agents, float(fleet_t0), sink,
                        LiveHealth(), LiveSessions(agents))
        print(f"fleet-clock live: {len(agents)} agents, T0={iso(float(fleet_t0))}; "
              f"events -> {sink.events_dir}", flush=True)
        while not engine.all_done():
            engine.tick(time.time())
            if engine.log_lines:
                with (log_dir / "fleet-clock.log").open("a", encoding="utf-8") as fh:
                    fh.write("\n".join(engine.log_lines) + "\n")
                engine.log_lines.clear()
            time.sleep(2)
        print("fleet-clock: all agents DONE", flush=True)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
