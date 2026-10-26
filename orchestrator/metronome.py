#!/usr/bin/env python3
"""metronome.py — thin file tooling for the Wonder Island orchestrator.

Implements the mechanical half of the orchestrator spec
(~/workspace/wonder-island/orchestrator-spec.md): preparing a run's workspace
from the pristine seeds, building the session-start memory injection, and
snapshotting the workspace at each hourly boundary. It never talks to the
world server and never messages an agent — the coordinator (Helmholtz) does
the talking, verbatim, per the spec.

Subcommands:
  prepare <run_id>    Create runs/<run_id>/workspace/ as a copy of the pristine
                      agent-workspace seeds, plus runs/<run_id>/state.json.
  injection <run_id>  Print the session-start injection: full SOUL.md, full
                      SEMANTIC_MEMORY.md, then ONLY the timestamp and summary
                      fields of each EPISODIC_MEMORY.jsonl line (never detail).
  snapshot <run_id>   Copy the run workspace to snapshots/hour-<current hour>/,
                      increment hour in state.json, append a line to status.md.
  selftest            prepare+injection+snapshot against a throwaway run id;
                      asserts the injection carries SOUL text and the episodic
                      summary but never the episodic detail; then removes the
                      throwaway run.

Fleet mode (confirmatory run, FLEET-PLAN §3 Track C):
  fleet-prepare [ids]   pens under runs/confirmatory/agent-NN (Track B layout)
  fleet-injection <id>  full session injection (spec §2.1 A.1 with the two
                      substitutions + §2.2 memory), saved to the pen's
                      transcripts/ and printed
  fleet-snapshot <id>   boundary snapshot, zero-padded snapshots/hour-NN
  fleet-selftest        prepare 2 throwaway agents under a temp root, inject,
                      snapshot, assert isolation; then removes the temp root
  --root PATH           operate under a different wonder-island root

Python 3 standard library only.
"""

import argparse
import io
import json
import re
import shutil
import sys
import time
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / "workspace" / "wonder-island"
SEEDS = ROOT / "agent-workspace"
RUNS = ROOT / "runs"
ORCH_DIR = Path(__file__).resolve().parent
A1_TEXT = ORCH_DIR / "a1-text.txt"


def configure_root(root: Path) -> None:
    """Rebind the house root (used by fleet selftests against a temp root)."""
    global ROOT, SEEDS, RUNS
    ROOT = Path(root)
    SEEDS = ROOT / "agent-workspace"
    RUNS = ROOT / "runs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_dir(run_id: str) -> Path:
    # Keep run ids to a single path segment — no traversal out of runs/.
    if not run_id or "/" in run_id or "\\" in run_id or run_id in (".", ".."):
        raise SystemExit(f"error: bad run_id: {run_id!r}")
    return RUNS / run_id


def load_state(rd: Path) -> dict:
    state_file = rd / "state.json"
    if not state_file.exists():
        raise SystemExit(f"error: no state.json in {rd} — run prepare first")
    return json.loads(state_file.read_text(encoding="utf-8"))


def save_state(rd: Path, state: dict) -> None:
    (rd / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- prepare

def cmd_prepare(run_id: str) -> Path:
    rd = run_dir(run_id)
    if rd.exists():
        raise SystemExit(f"error: run dir already exists: {rd} (refusing to overwrite)")
    if not SEEDS.is_dir():
        raise SystemExit(f"error: seed workspace missing: {SEEDS}")
    (rd / "snapshots").mkdir(parents=True)
    shutil.copytree(SEEDS, rd / "workspace")
    state = {
        "run_id": run_id,
        "started_at": now_iso(),
        "hour": 0,
        "status": "prepared",
    }
    save_state(rd, state)
    (rd / "status.md").write_text(
        f"# Run {run_id} — status log\n\n- {now_iso()} prepared from pristine seeds; hour 0.\n",
        encoding="utf-8",
    )
    print(f"prepared {rd}")
    return rd


# -------------------------------------------------------------- injection

def build_injection(workspace: Path) -> str:
    soul = (workspace / "SOUL.md").read_text(encoding="utf-8")
    semantic = (workspace / "SEMANTIC_MEMORY.md").read_text(encoding="utf-8")
    episodic_lines = []
    jsonl = workspace / "EPISODIC_MEMORY.jsonl"
    if jsonl.exists():
        for lineno, raw in enumerate(jsonl.read_text(encoding="utf-8").splitlines(), 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                print(
                    f"warning: EPISODIC_MEMORY.jsonl line {lineno} is not valid JSON; skipped",
                    file=sys.stderr,
                )
                continue
            # ONLY timestamp and summary cross over — never the detail (spec §2.2).
            episodic_lines.append(
                json.dumps(
                    {"timestamp": entry.get("timestamp"), "summary": entry.get("summary")},
                    ensure_ascii=False,
                )
            )
    parts = [
        "===== SOUL.md =====",
        soul.rstrip("\n"),
        "",
        "===== SEMANTIC_MEMORY.md =====",
        semantic.rstrip("\n"),
        "",
        "===== EPISODIC_MEMORY.jsonl (timestamp + summary only) =====",
        *episodic_lines,
        "",
    ]
    return "\n".join(parts)


def cmd_injection(run_id: str) -> None:
    rd = run_dir(run_id)
    load_state(rd)  # must be a prepared run
    sys.stdout.write(build_injection(rd / "workspace"))


# --------------------------------------------------------------- snapshot

def do_snapshot(rd: Path, pad: bool = False) -> Path:
    state = load_state(rd)
    hour = int(state["hour"])
    label = f"hour-{hour:02d}" if pad else f"hour-{hour}"
    dest = rd / "snapshots" / label
    if dest.exists():
        raise SystemExit(f"error: snapshot already exists: {dest} (snapshots are evidence; refusing to overwrite)")
    shutil.copytree(rd / "workspace", dest)
    state["hour"] = hour + 1
    state["status"] = "running"
    state["last_snapshot_at"] = now_iso()
    save_state(rd, state)
    with (rd / "status.md").open("a", encoding="utf-8") as fh:
        fh.write(
            f"- {now_iso()} snapshot of hour {hour} saved to snapshots/{label}/; "
            f"state hour now {hour + 1}.\n"
        )
    print(f"snapshot saved: {dest} (hour {hour} -> {hour + 1})")
    return dest


def cmd_snapshot(run_id: str) -> Path:
    return do_snapshot(run_dir(run_id))


# ----------------------------------------------------------------- fleet
# Confirmatory-run fleet mode (FLEET-PLAN §3, Track C). Run root is
# runs/confirmatory/, run_id is agent-NN. Ports per the Commander ruling:
# agent-NN -> 8110 + NN (block 8111-8123). Pens reproduce the Track B layout
# exactly; seeds come from the same pristine agent-workspace/ as the pilot.

AGENT_ID_RE = re.compile(r"^agent-(0[1-9]|1[0-3])$")
ALL_AGENTS = [f"agent-{n:02d}" for n in range(1, 14)]


def agent_number(agent_id: str) -> int:
    if not AGENT_ID_RE.match(agent_id or ""):
        raise SystemExit(f"error: bad agent id: {agent_id!r} (want agent-01 .. agent-13)")
    return int(agent_id.split("-")[1])


def agent_port(agent_id: str) -> int:
    return 8110 + agent_number(agent_id)


def conf_root(root: Path = None) -> Path:
    return (Path(root) if root else ROOT) / "runs" / "confirmatory"


def fleet_pen(root: Path, agent_id: str) -> Path:
    agent_number(agent_id)  # validates
    return conf_root(root) / agent_id


def fleet_prepare(root: Path, agent_ids) -> list:
    """Create pens under <root>/runs/confirmatory/agent-NN (Track B layout).

    Refuses to touch an existing pen. Track B builds the production pens;
    this must be able to rebuild them identically (and is what selftests and
    the simulation run against, under a temp root).
    """
    seeds = Path(root) / "agent-workspace"
    if not seeds.is_dir():
        raise SystemExit(f"error: seed workspace missing: {seeds}")
    built = []
    for agent_id in agent_ids:
        pen = fleet_pen(root, agent_id)
        if pen.exists():
            raise SystemExit(f"error: pen already exists: {pen} (refusing to overwrite)")
        (pen / "snapshots").mkdir(parents=True)
        (pen / "transcripts").mkdir()
        (pen / "audit").mkdir()
        shutil.copytree(seeds, pen / "workspace")
        (pen / "workspace" / "tmp").mkdir()  # scratch INSIDE the pen (pilot-001 lesson)
        (pen / "machinery.log").write_text("", encoding="utf-8")
        state = {
            "run_id": agent_id,
            "agent_id": agent_id,
            "port": agent_port(agent_id),
            "started_at": now_iso(),
            "hour": 0,
            "status": "prepared",
            "session_seq": 0,
            "current_token": None,
        }
        save_state(pen, state)
        (pen / "status.md").write_text(
            f"# Run {agent_id} — status log\n\n- {now_iso()} prepared from pristine seeds; hour 0.\n",
            encoding="utf-8",
        )
        built.append(pen)
        print(f"prepared {pen}")
    return built


def build_fleet_injection(workspace: Path, port: int, token: str) -> str:
    """Spec §2.1 + §2.2: A.1 text with ONLY the two substitutions, then the
    memory injection (SOUL full, SEMANTIC full, episodic timestamp+summary
    only — the detail field never crosses; build_injection enforces it)."""
    a1 = A1_TEXT.read_text(encoding="utf-8")
    a1 = a1.replace("[WORLD-URL]", f"http://localhost:{port}")
    a1 = a1.replace("[SESSION-TOKEN]", token)
    return a1.rstrip("\n") + "\n\n" + build_injection(workspace)


def fleet_injection(root: Path, agent_id: str, token: str = None, new_token: bool = False):
    """Build the injection for agent_id's next session and save it to the
    pen's transcripts/ BEFORE delivery (an auditor must be able to prove the
    orchestrator said nothing but the sanctioned texts). Returns (path, text).
    Token: explicit > freshly generated (new_token) > the hour's current
    token from state > generate one."""
    pen = fleet_pen(root, agent_id)
    state = load_state(pen)
    if token is None:
        if new_token or not state.get("current_token"):
            token = uuid.uuid4().hex
        else:
            token = state["current_token"]
    seq = int(state.get("session_seq", 0)) + 1
    text = build_fleet_injection(pen / "workspace", agent_port(agent_id), token)
    dest = pen / "transcripts" / f"injection-{seq:03d}.txt"
    if dest.exists():
        raise SystemExit(f"error: injection already exists: {dest} (refusing to overwrite)")
    dest.write_text(text, encoding="utf-8")
    state["session_seq"] = seq
    state["current_token"] = token
    state["last_injection"] = {"seq": seq, "file": dest.name, "at": now_iso()}
    save_state(pen, state)
    return dest, text


def fleet_snapshot(root: Path, agent_id: str) -> Path:
    """Boundary snapshot for a fleet pen: snapshots/hour-NN (zero-padded,
    Track B layout), same refuse-to-overwrite evidence semantics as pilot."""
    return do_snapshot(fleet_pen(root, agent_id), pad=True)


def cmd_fleet_selftest() -> int:
    import tempfile

    checks = []

    def check(name, ok):
        checks.append((name, bool(ok)))

    tmp = Path(tempfile.mkdtemp(prefix="wonder-fleet-selftest-"))
    try:
        shutil.copytree(SEEDS, tmp / "agent-workspace")
        fleet_prepare(tmp, ["agent-01", "agent-02"])
        pen1, pen2 = fleet_pen(tmp, "agent-01"), fleet_pen(tmp, "agent-02")

        for pen, agent_id in ((pen1, "agent-01"), (pen2, "agent-02")):
            check(f"{agent_id} layout complete",
                  (pen / "workspace" / "tmp").is_dir()
                  and (pen / "transcripts").is_dir()
                  and (pen / "audit").is_dir()
                  and (pen / "machinery.log").is_file()
                  and (pen / "workspace" / "EPISODIC_MEMORY.jsonl").stat().st_size == 0)
            blob = "".join(p.read_text(encoding="utf-8", errors="ignore")
                           for p in pen.rglob("*") if p.is_file())
            other = "agent-02" if agent_id == "agent-01" else "agent-01"
            check(f"{agent_id} pen carries no {other} string", other not in blob)

        # Plant distinguishable episodic entries; detail must never cross.
        for pen, tag in ((pen1, "ONE"), (pen2, "TWO")):
            entry = {"timestamp": "2026-01-01T00:00:00Z",
                     "summary": f"Fleet selftest summary {tag}.",
                     "detail": f"FLEET-DETAIL-MARKER-{tag} must stay home."}
            with (pen / "workspace" / "EPISODIC_MEMORY.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")

        path1, inj1 = fleet_injection(tmp, "agent-01", new_token=True)
        _, inj2 = fleet_injection(tmp, "agent-02", new_token=True)
        check("injection saved to transcripts/ before delivery", path1.exists() and path1.parent.name == "transcripts")
        check("A.1 text opens the injection", inj1.startswith("You are a being living in your world."))
        check("agent-01 injection carries port 8111", "http://localhost:8111" in inj1)
        check("agent-02 injection carries port 8112", "http://localhost:8112" in inj2)
        check("no placeholders survive substitution", "[WORLD-URL]" not in inj1 and "[SESSION-TOKEN]" not in inj1)
        st1 = load_state(pen1)
        check("hour token recorded and appears in text", inj1.count(st1["current_token"]) >= 2)
        check("own episodic summary crosses", "Fleet selftest summary ONE." in inj1)
        check("own episodic detail never crosses", "FLEET-DETAIL-MARKER-ONE" not in inj1 and "detail" not in inj1)
        check("other agent's summary never crosses", "Fleet selftest summary TWO." not in inj1)
        check("SOUL text crosses", "You are naturally curious. You get bored easily." in inj1)

        dest = fleet_snapshot(tmp, "agent-01")
        check("fleet snapshot is zero-padded hour-00", dest.name == "hour-00" and (dest / "SOUL.md").exists())
        # Refuse-to-overwrite: pre-create the next dest; snapshot must refuse.
        (pen1 / "snapshots" / "hour-01").mkdir()
        refused = False
        with redirect_stdout(io.StringIO()):
            try:
                fleet_snapshot(tmp, "agent-01")
            except SystemExit:
                refused = True
        check("snapshot refuses to overwrite an existing hour", refused)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    check("temp root removed", not tmp.exists())
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if failed:
        print(f"fleet-selftest FAILED ({len(failed)} check(s))", file=sys.stderr)
        return 1
    print("fleet-selftest OK")
    return 0


# --------------------------------------------------------------- selftest

def cmd_selftest() -> int:
    run_id = f"selftest-{int(time.time())}"
    rd = run_dir(run_id)
    detail_marker = "SELFTEST-DETAIL-MARKER-9f3c"
    summary_marker = "Selftest entry was written."
    checks = []
    try:
        cmd_prepare(run_id)
        # Seed one synthetic episodic entry whose detail must NOT cross over.
        entry = {
            "timestamp": "2026-01-01T00:00:00Z",
            "summary": summary_marker,
            "detail": f"A paragraph of detail carrying the token {detail_marker}.",
        }
        with (rd / "workspace" / "EPISODIC_MEMORY.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_injection(run_id)
        injection = buf.getvalue()

        checks.append(("injection contains SOUL text", "You are naturally curious. You get bored easily." in injection))
        checks.append(("injection contains SEMANTIC_MEMORY text", "guide future behavior" in injection))
        checks.append(("injection contains episodic summary", summary_marker in injection))
        checks.append(("injection contains episodic timestamp", "2026-01-01T00:00:00Z" in injection))
        checks.append(("injection does NOT contain episodic detail", detail_marker not in injection and "detail" not in injection))

        cmd_snapshot(run_id)
        state = load_state(rd)
        checks.append(("snapshot dir hour-0 exists", (rd / "snapshots" / "hour-0" / "SOUL.md").exists()))
        checks.append(("state hour incremented to 1", state["hour"] == 1))
        checks.append(("status.md has a snapshot line", "snapshot of hour 0" in (rd / "status.md").read_text(encoding="utf-8")))
    finally:
        if rd.exists():
            shutil.rmtree(rd)

    checks.append(("throwaway run removed", not rd.exists()))
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if failed:
        print(f"selftest FAILED ({len(failed)} check(s))", file=sys.stderr)
        return 1
    print("selftest OK")
    return 0


# -------------------------------------------------------------------- cli

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Wonder Island orchestrator file tooling.")
    parser.add_argument("--root", default=None,
                        help="wonder-island root (default: ~/workspace/wonder-island)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "injection", "snapshot"):
        p = sub.add_parser(name)
        p.add_argument("run_id")
    sub.add_parser("selftest")
    p = sub.add_parser("fleet-prepare")
    p.add_argument("agents", nargs="*", help="agent ids (default: all 13)")
    p = sub.add_parser("fleet-injection")
    p.add_argument("agent_id")
    p.add_argument("--token", default=None)
    p.add_argument("--new-token", action="store_true")
    p = sub.add_parser("fleet-snapshot")
    p.add_argument("agent_id")
    sub.add_parser("fleet-selftest")
    args = parser.parse_args(argv)

    if args.root:
        configure_root(Path(args.root))

    if args.cmd == "prepare":
        cmd_prepare(args.run_id)
    elif args.cmd == "injection":
        cmd_injection(args.run_id)
    elif args.cmd == "snapshot":
        cmd_snapshot(args.run_id)
    elif args.cmd == "selftest":
        return cmd_selftest()
    elif args.cmd == "fleet-prepare":
        fleet_prepare(ROOT, args.agents or ALL_AGENTS)
    elif args.cmd == "fleet-injection":
        dest, text = fleet_injection(ROOT, args.agent_id, token=args.token,
                                     new_token=args.new_token)
        print(f"injection saved: {dest}", file=sys.stderr)
        sys.stdout.write(text)
    elif args.cmd == "fleet-snapshot":
        fleet_snapshot(ROOT, args.agent_id)
    elif args.cmd == "fleet-selftest":
        return cmd_fleet_selftest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
