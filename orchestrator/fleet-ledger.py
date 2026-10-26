#!/usr/bin/env python3
"""fleet-ledger.py — session-ledger proxy meter for the Wonder Island 13x30 run.

Track E (FLEET-PLAN.md §3, Track E output 1). Exact credit metering does not
exist for house sessions (pilot-002 cost note), so this ledger is the proxy
meter: every session spawn (player, continuation, operator) is recorded, and
the burn is tracked as SESSIONS against the pilot baseline.

Baseline (pilot-002, verified counts): 7 player sessions (hour-open spawns +
continuations) in 3 agent-hours = 2.3333 sessions/agent-hour.
Fleet projection at baseline: 13 agents x 30 h x 2.3333 = 910 player sessions
(+ operator sessions, tallied separately, never in the rate).

The watchdog INFORMS; it never throttles. No skipped auto-continues, no
shortened hours — truncation is Jose Luis's call alone (brief).

Alert thresholds (FLEET-PLAN Track E, output 1), implemented exactly:
  (i)  IMMEDIATE — any single agent's cumulative rate reaches 2x baseline
       (>= 4.6667 sessions/agent-hour over >= 1 elapsed agent-hour): that
       agent's burn rate implies its 30 hours cannot complete inside the
       fleet burn envelope. Alert Jose Luis immediately, exact figures.
  (ii) SUMMARY — fleet projected total exceeds the baseline projection by
       >25% (> 1137.5 player sessions): reported with figures in the next
       08:00 / 17:00 summary.
  (iii) HARD FLOOR — fleet projected total exceeds 1.5x baseline
       (> 1365 player sessions): completion judged threatened; alert the
       same hour, not at the next summary.

Data: runs/confirmatory/credit-ledger.jsonl (append-only spawn events).
View: runs/confirmatory/credit-ledger.md (regenerated on every record).

Python 3 standard library only.
"""

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / "workspace" / "wonder-island"
RUN_ROOT = ROOT / "runs" / "confirmatory"
LEDGER_JSONL = RUN_ROOT / "credit-ledger.jsonl"
LEDGER_MD = RUN_ROOT / "credit-ledger.md"

PILOT_SESSIONS = 7          # pilot-002 verified player-session count
PILOT_AGENT_HOURS = 3.0     # pilot-002 duration
AGENTS = 13
HOURS_PER_AGENT = 30.0
BASELINE_RATE = PILOT_SESSIONS / PILOT_AGENT_HOURS          # 2.3333...
TOTAL_AGENT_HOURS = AGENTS * HOURS_PER_AGENT                # 390
BASELINE_PROJECTION = TOTAL_AGENT_HOURS * BASELINE_RATE     # 910.0

T1_MULT = 2.0    # (i)  per-agent runaway: rate >= 2x baseline
T2_MULT = 1.25   # (ii) fleet projection > baseline x 1.25 -> summary flag
T3_MULT = 1.5    # (iii) fleet projection > baseline x 1.5  -> same-hour alert

PLAYER_KINDS = ("player", "continuation")   # both counted in pilot's 7
ALL_KINDS = PLAYER_KINDS + ("operator",)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def agent_id(n: int) -> str:
    return f"agent-{n:02d}"


# ------------------------------------------------------------------ storage

def load_events(jsonl: Path) -> list:
    if not jsonl.exists():
        return []
    events = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def append_event(jsonl: Path, event: dict) -> None:
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    with jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


# --------------------------------------------------------------- accounting

def compute(events: list, elapsed: dict) -> dict:
    """elapsed: {agent_id: agent-hours elapsed so far (0..30)}.
    Returns per-agent counts/rates, fleet totals, projection, alert states."""
    per_agent = {}
    for n in range(1, AGENTS + 1):
        aid = agent_id(n)
        per_agent[aid] = {"player_sessions": 0, "operator_sessions": 0,
                          "elapsed_h": float(elapsed.get(aid, 0.0))}
    for ev in events:
        aid = ev["agent"]
        if aid not in per_agent:
            continue
        if ev["kind"] in PLAYER_KINDS:
            per_agent[aid]["player_sessions"] += 1
        elif ev["kind"] == "operator":
            per_agent[aid]["operator_sessions"] += 1

    fleet_player = 0
    fleet_operator = 0
    fleet_elapsed = 0.0
    for aid, row in per_agent.items():
        row["rate"] = (row["player_sessions"] / row["elapsed_h"]
                       if row["elapsed_h"] > 0 else None)
        fleet_player += row["player_sessions"]
        fleet_operator += row["operator_sessions"]
        fleet_elapsed += row["elapsed_h"]

    fleet_rate = (fleet_player / fleet_elapsed) if fleet_elapsed > 0 else None
    projected = (fleet_rate * TOTAL_AGENT_HOURS) if fleet_rate is not None else None

    alerts = {"immediate": [], "summary": False, "hard_floor": False}
    for aid, row in per_agent.items():
        if row["elapsed_h"] >= 1.0 and row["rate"] is not None \
                and row["rate"] >= T1_MULT * BASELINE_RATE:
            alerts["immediate"].append(aid)
    if projected is not None:
        if projected > T2_MULT * BASELINE_PROJECTION:
            alerts["summary"] = True
        if projected > T3_MULT * BASELINE_PROJECTION:
            alerts["hard_floor"] = True

    return {"per_agent": per_agent, "fleet_player": fleet_player,
            "fleet_operator": fleet_operator, "fleet_elapsed": fleet_elapsed,
            "fleet_rate": fleet_rate, "projected": projected, "alerts": alerts}


def fmt(x, digits=2):
    return "—" if x is None else f"{x:.{digits}f}"


def render_md(stats: dict, generated_at: str) -> str:
    lines = [
        "# Credit ledger — Wonder Island 13×30 confirmatory run (Track E proxy meter)",
        "",
        "Exact credit metering does not exist for house sessions (pilot-002 cost",
        "note), so burn is tracked as **sessions** against the pilot baseline.",
        "The watchdog informs; it never throttles protocol behavior. Truncation is",
        "Jose Luis's call alone.",
        "",
        f"- Baseline (pilot-002): {PILOT_SESSIONS} player sessions / "
        f"{PILOT_AGENT_HOURS:.0f} agent-hours = **{BASELINE_RATE:.4f} sessions/agent-hour**",
        f"- Baseline fleet projection: 13 × 30 × {BASELINE_RATE:.4f} = "
        f"**{BASELINE_PROJECTION:.0f} player sessions** (+ operator, tallied apart)",
        f"- Threshold (i) IMMEDIATE: any agent rate ≥ {T1_MULT:.0f}× baseline "
        f"({T1_MULT * BASELINE_RATE:.4f}/agent-hour over ≥1 elapsed hour) → alert Jose Luis at once",
        f"- Threshold (ii) SUMMARY: fleet projection > {T2_MULT}× baseline "
        f"({T2_MULT * BASELINE_PROJECTION:.1f}) → figures in next 08:00/17:00 summary",
        f"- Threshold (iii) HARD FLOOR: fleet projection > {T3_MULT}× baseline "
        f"({T3_MULT * BASELINE_PROJECTION:.1f}) → same-hour alert",
        "",
        f"Last regenerated: {generated_at}",
        "",
        "| Agent | Player sessions | Operator | Agent-hours elapsed | Rate /agent-hour |",
        "|---|---|---|---|---|",
    ]
    for n in range(1, AGENTS + 1):
        aid = agent_id(n)
        row = stats["per_agent"][aid]
        lines.append(f"| {aid} | {row['player_sessions']} | {row['operator_sessions']} "
                     f"| {row['elapsed_h']:.2f} | {fmt(row['rate'], 4)} |")
    lines += [
        "",
        f"**Fleet:** {stats['fleet_player']} player sessions, "
        f"{stats['fleet_operator']} operator sessions, "
        f"{stats['fleet_elapsed']:.2f} agent-hours elapsed, "
        f"fleet rate {fmt(stats['fleet_rate'], 4)}/agent-hour, "
        f"**projected fleet total {fmt(stats['projected'], 1)} player sessions** "
        f"(baseline {BASELINE_PROJECTION:.0f}).",
        "",
    ]
    al = stats["alerts"]
    if al["immediate"]:
        lines.append(f"🔴 **ALERT (i) IMMEDIATE — per-agent runaway rate:** "
                     f"{', '.join(al['immediate'])} — alert Jose Luis NOW with exact figures.")
    if al["hard_floor"]:
        lines.append("🔴 **ALERT (iii) HARD FLOOR — completion threatened:** "
                     "alert Jose Luis THIS HOUR with exact figures.")
    elif al["summary"]:
        lines.append("🟠 **FLAG (ii) — projection >25% over baseline:** "
                     "report with figures in the next 08:00/17:00 summary.")
    if not (al["immediate"] or al["summary"] or al["hard_floor"]):
        lines.append("🟢 No alert threshold crossed.")
    lines.append("")
    return "\n".join(lines)


def regenerate(jsonl: Path, md: Path, elapsed: dict) -> dict:
    stats = compute(load_events(jsonl), elapsed)
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(render_md(stats, now_iso()), encoding="utf-8")
    return stats


def load_elapsed(path: Path) -> dict:
    """Elapsed agent-hours per agent, from a JSON file the operator/fleet-clock
    maintains: {"agent-01": 5.0, ...}. Missing agents count as 0."""
    if path and path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {k: float(v) for k, v in raw.items()}
    return {}


# ---------------------------------------------------------------------- cli

def cmd_init(args) -> int:
    if not LEDGER_JSONL.exists():
        LEDGER_JSONL.parent.mkdir(parents=True, exist_ok=True)
        LEDGER_JSONL.write_text("", encoding="utf-8")
        print(f"created empty ledger: {LEDGER_JSONL}")
    stats = regenerate(LEDGER_JSONL, LEDGER_MD, {})
    print(f"ledger view: {LEDGER_MD}")
    print(f"baseline rate {BASELINE_RATE:.4f}/agent-hour; "
          f"baseline projection {BASELINE_PROJECTION:.0f} player sessions")
    return 0


def cmd_record(args) -> int:
    if args.kind not in ALL_KINDS:
        raise SystemExit(f"error: kind must be one of {ALL_KINDS}")
    if not (1 <= int(args.agent) <= AGENTS):
        raise SystemExit("error: --agent must be 1..13")
    event = {"agent": agent_id(int(args.agent)), "kind": args.kind,
             "hour": int(args.hour), "fleet_time": args.at or now_iso(),
             "recorded_by": "fleet-ledger"}
    append_event(LEDGER_JSONL, event)
    elapsed = load_elapsed(Path(args.elapsed) if args.elapsed else None)
    stats = regenerate(LEDGER_JSONL, LEDGER_MD, elapsed)
    print(f"recorded {event['kind']} spawn: {event['agent']} hour {event['hour']} "
          f"at {event['fleet_time']}")
    al = stats["alerts"]
    if al["immediate"]:
        print(f"ALERT(i) IMMEDIATE: {', '.join(al['immediate'])}")
    if al["hard_floor"]:
        print("ALERT(iii) HARD FLOOR: same-hour alert required")
    elif al["summary"]:
        print("FLAG(ii): projection >25% over baseline — next summary")
    return 0


def cmd_project(args) -> int:
    elapsed = load_elapsed(Path(args.elapsed) if args.elapsed else None)
    stats = compute(load_events(LEDGER_JSONL), elapsed)
    if args.oneline:
        print(f"player={stats['fleet_player']} operator={stats['fleet_operator']} "
              f"elapsed_agent_h={stats['fleet_elapsed']:.2f} "
              f"rate={fmt(stats['fleet_rate'], 4)} "
              f"projected={fmt(stats['projected'], 1)} "
              f"baseline={BASELINE_PROJECTION:.0f} "
              f"alerts_i={','.join(stats['alerts']['immediate']) or 'none'} "
              f"flag_ii={stats['alerts']['summary']} "
              f"alert_iii={stats['alerts']['hard_floor']}")
    else:
        print(render_md(stats, now_iso()))
    return 0


def cmd_selftest(args) -> int:
    checks = []
    # 1. Pilot arithmetic reproduces the baseline (plan verification).
    checks.append(("pilot rate 7/3 = 2.3333", abs(BASELINE_RATE - 7 / 3) < 1e-9))
    checks.append(("fleet projection 13x30x7/3 = 910",
                   abs(BASELINE_PROJECTION - 910.0) < 1e-6))
    checks.append(("threshold (ii) figure = 1137.5",
                   abs(T2_MULT * BASELINE_PROJECTION - 1137.5) < 1e-6))
    checks.append(("threshold (iii) figure = 1365",
                   abs(T3_MULT * BASELINE_PROJECTION - 1365.0) < 1e-6))
    checks.append(("threshold (i) rate = 4.6667",
                   abs(T1_MULT * BASELINE_RATE - 14 / 3) < 1e-9))

    with tempfile.TemporaryDirectory() as td:
        jsonl = Path(td) / "ledger.jsonl"
        md = Path(td) / "ledger.md"
        # 2. Recording + projection machinery on synthetic data.
        for i in range(7):  # pilot shape: 7 player sessions, one agent, 3 h
            append_event(jsonl, {"agent": "agent-01",
                                 "kind": "player" if i % 2 == 0 else "continuation",
                                 "hour": i // 3, "fleet_time": now_iso(),
                                 "recorded_by": "selftest"})
        append_event(jsonl, {"agent": "agent-01", "kind": "operator",
                             "hour": 0, "fleet_time": now_iso(),
                             "recorded_by": "selftest"})
        stats = regenerate(jsonl, md, {"agent-01": 3.0})
        checks.append(("pilot-shaped agent rate = baseline",
                       abs(stats["per_agent"]["agent-01"]["rate"] - BASELINE_RATE) < 1e-9))
        checks.append(("operator sessions excluded from rate numerator",
                       stats["fleet_player"] == 7 and stats["fleet_operator"] == 1))
        checks.append(("no alerts at baseline rate",
                       not stats["alerts"]["immediate"]
                       and not stats["alerts"]["summary"]
                       and not stats["alerts"]["hard_floor"]))
        # 3. Threshold (i): one runaway agent at 5.0/h.
        ev = load_events(jsonl)
        for i in range(15):
            append_event(jsonl, {"agent": "agent-02", "kind": "continuation",
                                 "hour": 0, "fleet_time": now_iso(),
                                 "recorded_by": "selftest"})
        stats = compute(load_events(jsonl),
                        {"agent-01": 3.0, "agent-02": 3.0})
        checks.append(("threshold (i) fires for runaway agent-02 (5.0/h)",
                       stats["alerts"]["immediate"] == ["agent-02"]))
        # 4. Threshold (ii) without (iii): fleet at 1.3x baseline rate.
        ev2 = []
        for n in range(1, AGENTS + 1):
            for i in range(91):  # 91 sessions per 30 agent-hours -> 3.0333/h = 1.3x
                ev2.append({"agent": agent_id(n), "kind": "player",
                            "hour": 0, "fleet_time": now_iso(),
                            "recorded_by": "selftest"})
        full = {agent_id(n): 30.0 for n in range(1, AGENTS + 1)}
        stats2 = compute(ev2, full)
        checks.append(("1.3x fleet: flag (ii) set",
                       stats2["alerts"]["summary"] is True))
        checks.append(("1.3x fleet: hard floor (iii) NOT set",
                       stats2["alerts"]["hard_floor"] is False))
        # 5. Threshold (iii): fleet at 1.6x baseline rate.
        ev3 = []
        for n in range(1, AGENTS + 1):
            for i in range(112):  # 112/30 = 3.7333/h = 1.6x
                ev3.append({"agent": agent_id(n), "kind": "player",
                            "hour": 0, "fleet_time": now_iso(),
                            "recorded_by": "selftest"})
        stats3 = compute(ev3, full)
        checks.append(("1.6x fleet: hard floor (iii) set",
                       stats3["alerts"]["hard_floor"] is True))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if failed:
        print(f"selftest FAILED ({len(failed)})", file=sys.stderr)
        return 1
    print("selftest OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Wonder Island fleet burn ledger (Track E).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p = sub.add_parser("record")
    p.add_argument("--agent", required=True, help="agent number 1..13")
    p.add_argument("--kind", required=True, choices=ALL_KINDS)
    p.add_argument("--hour", required=True, help="agent hour index 0..29")
    p.add_argument("--at", help="fleet time ISO (default: now, UTC)")
    p.add_argument("--elapsed", help="JSON file of elapsed agent-hours per agent")
    p = sub.add_parser("project")
    p.add_argument("--elapsed", help="JSON file of elapsed agent-hours per agent")
    p.add_argument("--oneline", action="store_true")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "record":
        return cmd_record(args)
    if args.cmd == "project":
        return cmd_project(args)
    if args.cmd == "selftest":
        return cmd_selftest(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
