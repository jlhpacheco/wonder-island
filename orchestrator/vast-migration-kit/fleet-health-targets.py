#!/usr/bin/env python3
"""fleet-health-targets.py — STAGED targets-aware variant of fleet-health.py.

Wonder Island → Vast cutover kit; NOT LIVE. Drop-in replacement for the
clerk's step-7 health call once the kit is released: identical board-line
format, sentinel note, and ledger line as fleet-health.py, except each
agent is probed at its CURRENT target from ops/world-targets.json:

  - target "local": GET http://localhost:<unit port>/api.md + systemctl
    is-active of the agent's unit (byte-identical to fleet-health.py);
  - target "vast": GET <vast public URL>/api.md; there is no local unit to
    interrogate, so svc is reported as "remote-supervisord" and the agent
    is UP iff the public probe answers 200.

Usage: fleet-health-targets.py [--targets PATH] [--board PATH]
Defaults are the live ops/world-targets.json and the live run BOARD.md,
so at cutover the clerk's step 7 changes only the script name. The
staging tests in vast-migration/staging/proofs/ ran it with both paths
pointed into staging.

The monitor reports; it never restarts, spawns, or throttles anything.

Python 3 standard library only.
"""

import argparse
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
DEFAULT_BOARD = RUN_ROOT / "BOARD.md"
DEFAULT_TARGETS = RUN_ROOT / "ops" / "world-targets.json"
STATE = RUN_ROOT / "fleet-state.json"
EVENTS = RUN_ROOT / "events"
LEDGER = ROOT / "orchestrator" / "fleet-ledger.py"
AGENTS = [f"agent-{n:02d}" for n in range(1, 14)]
PT = ZoneInfo("America/Los_Angeles")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def pt_stamp(dt: datetime) -> str:
    return dt.astimezone(PT).strftime("%Y-%m-%d %H:%M PT")


def load_targets(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    agents = data.get("agents")
    return agents if isinstance(agents, dict) else {}


def unit_port(aid: str) -> int:
    text = (UNITS / f"clawblox-wonder-island-{aid}.service").read_text(encoding="utf-8")
    m = re.search(r"--port\s+(\d+)", text)
    if not m:
        raise SystemExit(f"error: no --port in unit for {aid}")
    return int(m.group(1))


def probe_api(url: str) -> bool:
    try:
        req = urllib.request.Request(url + "/api.md", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
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
    parser = argparse.ArgumentParser(
        description="Targets-aware fleet health monitor (staged variant).")
    parser.add_argument("--targets", default=str(DEFAULT_TARGETS))
    parser.add_argument("--board", default=str(DEFAULT_BOARD))
    args = parser.parse_args()

    board = Path(args.board)
    targets = load_targets(Path(args.targets))
    board.parent.mkdir(parents=True, exist_ok=True)
    if not board.exists():
        board.write_text(
            "# Confirmatory run board — 13×30 (folded lines; format per FLEET-PLAN §4)\n\n",
            encoding="utf-8")
    stamp = pt_stamp(now_utc())
    lines = []
    bad = []
    for aid in AGENTS:
        entry = targets.get(aid) or {}
        ev = last_event(aid)
        if entry.get("target") == "vast":
            url = (entry.get("vast") or {}).get("url", "")
            port = (entry.get("vast") or {}).get("public_port", "?")
            api = probe_api(url) if url else False
            svc = "remote-supervisord"
            state = "UP" if api else "DOWN"
            where = f"target=vast url={url}"
        else:
            port = unit_port(aid)
            api = probe_api(f"http://localhost:{port}")
            svc = service_state(aid)
            state = "UP" if (api and svc == "active") else "DOWN"
            where = "target=local"
        if state == "DOWN":
            bad.append(aid)
        line = (f"[{stamp}] FROM: Track E/health-targets | {aid} | {state} "
                f"svc={svc} api.md={'200' if api else 'FAIL'} port={port} {where} "
                f"last-event={ev} | freight → ~/workspace/wonder-island/logs/world-{aid}.log")
        lines.append(line)
    fleet_line = (f"[{stamp}] FROM: Track E/health-targets | fleet | "
                  f"{'ALL-UP' if not bad else 'DOWN: ' + ','.join(bad)} · "
                  f"{sentinel_note()} · ledger: {ledger_oneline()} | "
                  f"freight → ~/workspace/wonder-island/runs/confirmatory/credit-ledger.md")
    with board.open("a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line + "\n")
        fh.write(fleet_line + "\n")
    for line in lines:
        print(line)
    print(fleet_line)
    return 0 if not bad else 4


if __name__ == "__main__":
    raise SystemExit(main())
