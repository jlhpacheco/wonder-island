#!/usr/bin/env python3
"""fleet-health.py — per-agent fleet health monitor (Track E).

FLEET-PLAN.md §3, Track E output 2. One pass:
  - probes each agent's world server (GET /api.md on the port parsed from
    its workspace unit; ruled block 8111-8123, Commander 2026-10-25);
  - reads the agent's systemctl state and last fleet-clock event (if the
    events dir exists) for session state;
  - consults the sentinel state (boot time recorded vs current) and the
    burn ledger's one-line projection;
  - appends ONE folded status line per agent to
    runs/confirmatory/BOARD.md (plan §4 format), plus a fleet line when
    anything is wrong, and prints the same to stdout.

The monitor reports; it never restarts, spawns, or throttles anything.

Python 3 standard library only.
"""

import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path.home() / "workspace" / "wonder-island"
RUN_ROOT = ROOT / "runs" / "confirmatory"
UNITS = ROOT / "systemd"
BOARD = RUN_ROOT / "BOARD.md"
STATE = RUN_ROOT / "fleet-state.json"
EVENTS = RUN_ROOT / "events"
LEDGER = ROOT / "orchestrator" / "fleet-ledger.py"
AGENTS = [f"agent-{n:02d}" for n in range(1, 14)]
PT = ZoneInfo("America/Los_Angeles")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def pt_stamp(dt: datetime) -> str:
    return dt.astimezone(PT).strftime("%Y-%m-%d %H:%M PT")


def unit_port(aid: str) -> int:
    text = (UNITS / f"clawblox-wonder-island-{aid}.service").read_text(encoding="utf-8")
    m = re.search(r"--port\s+(\d+)", text)
    if not m:
        raise SystemExit(f"error: no --port in unit for {aid}")
    return int(m.group(1))


def probe_api(port: int) -> bool:
    try:
        req = urllib.request.Request(f"http://localhost:{port}/api.md",
                                     method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def service_state(aid: str) -> str:
    out = subprocess.run(
        ["systemctl", "is-active", f"clawblox-wonder-island-{aid}.service"],
        capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def last_event(aid: str) -> str:
    edir = EVENTS / aid
    if not edir.is_dir():
        return "no-events-dir"
    files = sorted(edir.glob("*.jsonl"))
    if not files:
        return "no-events"
    try:
        lines = [ln for ln in files[-1].read_text(encoding="utf-8")
                 .splitlines() if ln.strip()]
        if not lines:
            return "no-events"
        ev = json.loads(lines[-1])
        return str(ev.get("type") or ev.get("event") or "event")
    except Exception:
        return "event-unreadable"


def sentinel_note() -> str:
    if not STATE.exists():
        return "sentinel: no state yet"
    st = json.loads(STATE.read_text(encoding="utf-8"))
    out = subprocess.run(["uptime", "-s"], capture_output=True, text=True)
    current = out.stdout.strip()
    if st.get("boot_time") and st["boot_time"] != current:
        return (f"sentinel: BOOT CHANGED recorded={st['boot_time']} "
                f"current={current} — RECOVERY REQUIRED")
    down = st.get("down_agents") or []
    return f"sentinel: boot stable; down={','.join(down) if down else 'none'}"


def ledger_oneline() -> str:
    out = subprocess.run([sys.executable, str(LEDGER), "project", "--oneline"],
                         capture_output=True, text=True)
    return out.stdout.strip()


def main() -> int:
    BOARD.parent.mkdir(parents=True, exist_ok=True)
    if not BOARD.exists():
        BOARD.write_text(
            "# Confirmatory run board — 13×30 (folded lines; format per FLEET-PLAN §4)\n\n",
            encoding="utf-8")
    stamp = pt_stamp(now_utc())
    lines = []
    bad = []
    for aid in AGENTS:
        port = unit_port(aid)
        api = probe_api(port)
        svc = service_state(aid)
        ev = last_event(aid)
        state = "UP" if (api and svc == "active") else "DOWN"
        if state == "DOWN":
            bad.append(aid)
        line = (f"[{stamp}] FROM: Track E/health | {aid} | {state} "
                f"svc={svc} api.md={'200' if api else 'FAIL'} port={port} "
                f"last-event={ev} | freight → ~/workspace/wonder-island/logs/world-{aid}.log")
        lines.append(line)
    fleet_line = (f"[{stamp}] FROM: Track E/health | fleet | "
                  f"{'ALL-UP' if not bad else 'DOWN: ' + ','.join(bad)} · "
                  f"{sentinel_note()} · ledger: {ledger_oneline()} | "
                  f"freight → ~/workspace/wonder-island/runs/confirmatory/credit-ledger.md")
    with BOARD.open("a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")
        fh.write(fleet_line + "\n")
    for line in lines:
        print(line)
    print(fleet_line)
    return 0 if not bad else 4


if __name__ == "__main__":
    raise SystemExit(main())
