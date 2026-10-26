#!/usr/bin/env python3
"""fleet-sentinel.py — boot-time sentinel + machinery accounting (Track E).

FLEET-PLAN.md §3, Track E output 3. Pilot day saw THREE VM replacements
(boot times 12:17:41Z, 19:17:41Z, 21:06:09Z on 2026-10-25); a replacement
wipes /etc, so every systemd unit must be reinstalled from the workspace
copies (orchestrator/fleet-recover.sh) and the downtime accounted per agent.

Behavior of `check`:
  - Reads the machine boot time (`uptime -s`, local time as reported).
  - Compares with the boot time recorded in fleet state
    (runs/confirmatory/fleet-state.json).
  - First ever check: records the baseline silently, exit 0.
  - Same boot time: exit 0 (state's last_check updated).
  - CHANGED boot time = VM replaced:
      * appends a RECOVERY banner to logs/fleet-recovery.log,
      * writes `DOWN <fleet-time>` to every existing pen's machinery.log
        (runs/confirmatory/agent-NN/machinery.log) — once per incident,
      * marks those agents down in fleet state,
      * with --recover, runs orchestrator/fleet-recover.sh, which appends
        the matching `UP <fleet-time>` per verified agent and clears the
        down marks via `fleet-recover.sh` calling back into this tool's
        `mark-up` — or, run standalone, the operator clears marks with
        `mark-up --agent NN` after manual verification,
      * exit code 2 (RECOVERY REQUIRED) so callers can chain on it.
  - Per the registration's missing-data rule + plan D6, down agents resume
    at their next scheduled hour boundary; machinery intervals in
    machinery.log are excluded from behavioral coding. The sentinel only
    detects and accounts — it never spawns or restarts anything itself
    (recovery is fleet-recover.sh's job).

Test hook: env FLEET_BOOT_TIME overrides the detected boot time;
--state / --pens-root / --log allow fully isolated selftest runs.

Python 3 standard library only.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / "workspace" / "wonder-island"
RUN_ROOT = ROOT / "runs" / "confirmatory"
DEFAULT_STATE = RUN_ROOT / "fleet-state.json"
DEFAULT_LOG = ROOT / "logs" / "fleet-recovery.log"
RECOVER_SH = ROOT / "orchestrator" / "fleet-recover.sh"
AGENTS = [f"agent-{n:02d}" for n in range(1, 14)]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def detect_boot_time() -> str:
    override = os.environ.get("FLEET_BOOT_TIME")
    if override:
        return override
    out = subprocess.run(["uptime", "-s"], capture_output=True, text=True)
    return out.stdout.strip()


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"boot_time": None, "down_agents": [], "incidents": [],
            "created_at": now_iso()}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def cmd_check(args) -> int:
    state_path = Path(args.state)
    pens_root = Path(args.pens_root)
    log_path = Path(args.log)
    state = load_state(state_path)
    boot = detect_boot_time()
    fleet_time = now_iso()
    state["last_check"] = fleet_time

    if state.get("boot_time") is None:
        state["boot_time"] = boot
        save_state(state_path, state)
        print(f"sentinel baseline recorded: boot_time={boot}")
        return 0

    if boot == state["boot_time"]:
        save_state(state_path, state)
        print(f"boot unchanged: {boot}")
        return 0

    # ---- VM REPLACED ----
    old_boot = state["boot_time"]
    state["boot_time"] = boot
    incident = {"detected_at": fleet_time, "old_boot": old_boot,
                "new_boot": boot, "down_agents": []}
    banner = (f"[{fleet_time}] RECOVERY REQUIRED — VM REPLACED: "
              f"boot time changed {old_boot} -> {boot}. All /etc state "
              f"assumed gone. Run orchestrator/fleet-recover.sh.")
    append_line(log_path, banner)
    print(banner)
    for aid in AGENTS:
        pen = pens_root / aid
        if pen.is_dir():
            append_line(pen / "machinery.log", f"DOWN {fleet_time}")
            incident["down_agents"].append(aid)
    state["down_agents"] = sorted(set(state.get("down_agents", []))
                                  | set(incident["down_agents"]))
    state.setdefault("incidents", []).append(incident)
    save_state(state_path, state)
    print(f"machinery DOWN written for {len(incident['down_agents'])} agent(s): "
          f"{', '.join(incident['down_agents']) or 'none (no pens)'}")

    if args.recover:
        print("invoking fleet-recover.sh ...")
        rc = subprocess.run(["bash", str(RECOVER_SH)]).returncode
        print(f"fleet-recover.sh exit {rc}")
        return 0 if rc == 0 else rc
    return 2


def cmd_mark_up(args) -> int:
    """Clear down marks after an agent's server has been verified back up.
    fleet-recover.sh calls this per verified agent; the matching UP line is
    appended to machinery.log by fleet-recover.sh itself."""
    state_path = Path(args.state)
    state = load_state(state_path)
    aid = f"agent-{int(args.agent):02d}"
    down = state.get("down_agents", [])
    if aid in down:
        down.remove(aid)
        state["down_agents"] = down
        state["last_up"] = {"agent": aid, "at": now_iso()}
        save_state(state_path, state)
        print(f"{aid} marked up; still down: {down or 'none'}")
    else:
        print(f"{aid} was not marked down; nothing to clear")
    return 0


def cmd_selftest(args) -> int:
    checks = []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        state = td / "fleet-state.json"
        log = td / "fleet-recovery.log"
        pens = td / "pens"
        for aid in ("agent-01", "agent-02"):
            (pens / aid).mkdir(parents=True)
        base = ["--state", str(state), "--pens-root", str(pens),
                "--log", str(log)]

        def run_check(boot):
            env = dict(os.environ, FLEET_BOOT_TIME=boot)
            return subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "check", *base],
                capture_output=True, text=True, env=env)

        r1 = run_check("2026-01-01 00:00:00")
        checks.append(("first check records baseline, exit 0",
                       r1.returncode == 0 and "baseline" in r1.stdout))
        r2 = run_check("2026-01-01 00:00:00")
        checks.append(("same boot time: exit 0, no banner",
                       r2.returncode == 0 and not log.exists()))
        r3 = run_check("2026-01-02 00:00:00")
        checks.append(("changed boot time: exit 2 (recovery required)",
                       r3.returncode == 2))
        checks.append(("banner written to recovery log",
                       log.exists() and "VM REPLACED" in log.read_text()))
        m1 = (pens / "agent-01" / "machinery.log").read_text()
        m2 = (pens / "agent-02" / "machinery.log").read_text()
        checks.append(("DOWN written once to each existing pen",
                       m1.count("DOWN ") == 1 and m2.count("DOWN ") == 1))
        st = json.loads(state.read_text())
        checks.append(("state records both agents down + one incident",
                       sorted(st["down_agents"]) == ["agent-01", "agent-02"]
                       and len(st["incidents"]) == 1))
        r4 = run_check("2026-01-02 00:00:00")
        checks.append(("repeat check same boot: exit 0, no duplicate DOWN",
                       r4.returncode == 0
                       and (pens / "agent-01" / "machinery.log")
                       .read_text().count("DOWN ") == 1))
        r5 = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "mark-up",
             "--agent", "1", "--state", str(state)],
            capture_output=True, text=True)
        st = json.loads(state.read_text())
        checks.append(("mark-up clears one agent's down mark",
                       r5.returncode == 0 and st["down_agents"] == ["agent-02"]))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if failed:
        print(f"selftest FAILED ({len(failed)})", file=sys.stderr)
        return 1
    print("selftest OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Wonder Island boot-time sentinel (Track E).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--state", default=str(DEFAULT_STATE))
    p.add_argument("--pens-root", default=str(RUN_ROOT))
    p.add_argument("--log", default=str(DEFAULT_LOG))
    p.add_argument("--recover", action="store_true",
                   help="on VM replacement, invoke fleet-recover.sh")
    p = sub.add_parser("mark-up")
    p.add_argument("--agent", required=True, help="agent number 1..13")
    p.add_argument("--state", default=str(DEFAULT_STATE))
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "mark-up":
        return cmd_mark_up(args)
    if args.cmd == "selftest":
        return cmd_selftest(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
