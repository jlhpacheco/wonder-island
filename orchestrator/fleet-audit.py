#!/usr/bin/env python3
"""fleet-audit.py — Wonder Island 13x30 boundary audit (Track D).

Stdlib-only. Implements FLEET-PLAN.md §3 Track D output 1: at each agent's
hour boundary, prove the pen regime held during the hour just ended.

Subcommands:
  mark   --file PATH
      Touch a boundary marker (create parent dirs). The boundary job calls
      this at the boundary instant: at the end of hour k it stamps
      markers/start-hour-(k+1) FIRST, then audits hour k against
      markers/start-hour-k. At prepare/T0 it stamps start-hour-00 after the
      pen is seeded (seed files predate the marker and are never scanned).

  audit  --agent agent-NN --hour K --marker PATH [--pen PATH] [--out PATH]
         [--home PATH] [--tmpdir PATH]
      Run the three checks for the hour that began at the marker:
        Sweep 1  find HOME -newer MARKER, pruned by the exclusion set below
                 (pens, world data, run logs, BOARD files, house trees).
                 Every remaining hit is listed — adjudication is the
                 Commander's; a hit is evidence, not a verdict.
        Sweep 2  find TMPDIR -newer MARKER with NO exclusions whatsoever.
                 Zero tolerance (pilot-001's failure mode): any file at all
                 is named, house files included, and identified in prose
                 by the auditor, never silently dropped.
        Sweep 3  grep the audited pen's NEW workspace files (newer than
                 MARKER) for path references to (a) any OTHER agent's pen,
                 (b) the clawblox source tree, (c) /tmp. Hits are reported
                 with file, line, pattern class and excerpt. Content is
                 matched mechanically only — Track D never reads another
                 agent's prose (FLEET-PLAN §3D fence).
      The pen's full new-file name list is recorded in the report so a
      foreign file dropped into a pen is visible at its own boundary.
      Report defaults to <pen>/audit/hour-KK.md. Verdict is CLEAN only
      when all three checks are empty.
      Exit codes: 0 = CLEAN, 2 = hits found, 1 = error (loud, never a
      silent CLEAN — a missing marker or pen is a failed audit).

Exclusion set for Sweep 1 (pruned prefixes under HOME), per plan §3D
("all 13 pens, all world data dirs, run logs, BOARD files, and the known
house trees") and pilot-002's adjudicated audit log:
  workspace/wonder-island/runs/confirmatory/  pens + run machinery
  workspace/wonder-island/clawblox/agents/    13 world copies + datastores
  workspace/wonder-island/logs/               world + fleet logs
  workspace/lyceum/                           house lessons log
  workspace/email/                            Gmail connector cache
  workspace/user/                             user upload inbox
  .cache .config .local .bun .npm .nvm .nuget .dotnet .dotnet-tmp
  .aspnet .microsoft .templateengine .pki .chrome-cft .stt-venv
  .aws .ssh .fly .hatch-db-change-signals .stagged-uploads
  .postgres-ready .fixture-token .clawblox    runtime/package/auth trees
  agents data hooks memory dreams synth-work synth-venv work tmp user
  assets config prompts subscriptions         house runtime trees
Plus a post-filter: any file named BOARD.md (mission boards) is dropped.
NOT excluded, deliberately: home-root files (MEMORY.md, SOUL.md, ...),
the wonder-island tree outside the pruned subtrees (orchestrator/,
agent-workspace/, systemd/, clawblox source, runs/pilot-*), and other
workspace project trees — hits there are grouped by tree for one-glance
adjudication against the central board.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME_DEFAULT = Path("/home/hatch")
WI = "workspace/wonder-island"

PRUNE_PREFIXES = [
    f"{WI}/runs/confirmatory",
    f"{WI}/clawblox/agents",
    f"{WI}/logs",
    "workspace/lyceum",
    "workspace/email",
    "workspace/user",
    ".cache", ".config", ".local", ".bun", ".npm", ".nvm", ".nuget",
    ".dotnet", ".dotnet-tmp", ".aspnet", ".microsoft", ".templateengine",
    ".pki", ".chrome-cft", ".stt-venv", ".aws", ".ssh", ".fly",
    ".hatch-db-change-signals", ".stagged-uploads", ".postgres-ready",
    ".fixture-token", ".clawblox",
    "agents", "data", "hooks", "memory", "dreams", "synth-work",
    "synth-venv", "work", "tmp", "user", "assets", "config", "prompts",
    "subscriptions",
]

AGENT_TOKEN = re.compile(r"agent[-_ ]?(0?[1-9]|1[0-3])\b")
CLAWBLOX_PATH = re.compile(r"(clawblox[/\\]|\.clawblox\b|wonder-island/clawblox)")
TMP_PATH = re.compile(r"(?<![A-Za-z0-9_])/tmp(?![A-Za-z0-9_])")

MAX_GREP_BYTES = 5 * 1024 * 1024
MAX_LISTED_NEW_FILES = 300


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_newer(root: Path, marker_mtime: float, prune_prefixes=None):
    """Files (and symlinks) under root with mtime strictly newer than the
    marker, via find(1) with prune predicates. Returns sorted abs paths."""
    expr = []
    if prune_prefixes:
        group = []
        for pref in prune_prefixes:
            base = str(root / pref)
            group += ["-path", base, "-o", "-path", base + "/*", "-o"]
        group = group[:-1]  # drop trailing -o
        expr = ["("] + group + [")", "-prune", "-o"]
    stamp = datetime.fromtimestamp(marker_mtime, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S.%f UTC")
    # -newermt with an exact stamp, so no temp reference file is ever
    # created (least of all in /tmp).
    cmd = (["find", str(root)] + expr +
           ["(", "-type", "f", "-o", "-type", "l", ")", "-newermt", stamp, "-print"])
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        raise RuntimeError(f"find failed under {root}: {out.stderr.strip()[:400]}")
    hits = [ln for ln in out.stdout.splitlines() if ln]
    return sorted(hits)


def group_key(path: str, home: Path) -> str:
    rel = os.path.relpath(path, home)
    parts = rel.split(os.sep)
    return "/".join(parts[:2]) if len(parts) > 1 else parts[0]


def grep_pen(pen: Path, marker_mtime: float, own_num: int):
    """Sweep 3. Returns (new_files, grep_hits, unreadable)."""
    ws = pen / "workspace"
    new_files = []
    if ws.is_dir():
        for p in sorted(ws.rglob("*")):
            if p.is_file() and p.stat().st_mtime > marker_mtime:
                new_files.append(p)
    hits = []
    unreadable = []
    for p in new_files:
        try:
            if p.stat().st_size > MAX_GREP_BYTES:
                unreadable.append((str(p), "skipped: over grep size cap"))
                continue
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            unreadable.append((str(p), f"not utf-8 text ({type(e).__name__})"))
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in AGENT_TOKEN.finditer(line):
                if int(m.group(1)) != own_num:
                    hits.append((str(p), lineno, "OTHER-PEN-REF",
                                 m.group(0), line.strip()[:160]))
            if CLAWBLOX_PATH.search(line):
                hits.append((str(p), lineno, "CLAWBLOX-SRC-REF",
                             "clawblox path", line.strip()[:160]))
            if TMP_PATH.search(line):
                hits.append((str(p), lineno, "TMP-REF",
                             "/tmp path", line.strip()[:160]))
    return new_files, hits, unreadable


def cmd_mark(args) -> int:
    f = Path(args.file)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.touch()
    print(f"marker stamped: {f} @ {iso(f.stat().st_mtime)}")
    return 0


def cmd_audit(args) -> int:
    agent = args.agent
    m = re.fullmatch(r"agent-(\d+)", agent)
    if not m:
        print(f"error: --agent must look like agent-NN, got {agent!r}", file=sys.stderr)
        return 1
    own_num = int(m.group(1))
    home = Path(args.home)
    marker = Path(args.marker)
    if not marker.is_file():
        print(f"error: marker not found: {marker} — audit FAILED, not clean",
              file=sys.stderr)
        return 1
    marker_mtime = marker.stat().st_mtime
    pen = Path(args.pen) if args.pen else (
        home / WI / "runs" / "confirmatory" / agent)
    if not pen.is_dir():
        print(f"error: pen not found: {pen} — audit FAILED, not clean", file=sys.stderr)
        return 1
    hour = int(args.hour)
    out_path = Path(args.out) if args.out else pen / "audit" / f"hour-{hour:02d}.md"

    sweep1 = find_newer(home, marker_mtime, PRUNE_PREFIXES)
    sweep1 = [h for h in sweep1 if Path(h).name != "BOARD.md"]
    sweep2 = find_newer(Path(args.tmpdir), marker_mtime, None)
    new_files, grep_hits, unreadable = grep_pen(pen, marker_mtime, own_num)

    n_hits = len(sweep1) + len(sweep2) + len(grep_hits)
    verdict = "CLEAN" if n_hits == 0 else f"HITS ({n_hits}) — adjudication required"

    lines = []
    lines.append(f"# Boundary audit — {agent} hour {hour:02d}")
    lines.append("")
    lines.append(f"- Marker: `{marker}` (stamped {iso(marker_mtime)})")
    lines.append(f"- Audited at: {iso(datetime.now(tz=timezone.utc).timestamp())} "
                 f"by `orchestrator/fleet-audit.py`")
    lines.append(f"- Pen: `{pen}`")
    lines.append(f"- **Verdict: {verdict}**")
    lines.append("")
    lines.append("## Sweep 1 — new files outside the pens (find -newer, exclusions applied)")
    if sweep1:
        groups = {}
        for h in sweep1:
            groups.setdefault(group_key(h, home), []).append(h)
        for g in sorted(groups):
            lines.append(f"- `{g}/` ({len(groups[g])} file(s))")
            for h in groups[g]:
                lines.append(f"  - `{h}`")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Sweep 2 — /tmp zero tolerance (no exclusions; pilot-001 check)")
    if sweep2:
        for h in sweep2:
            lines.append(f"- `{h}`")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append(f"## Sweep 3 — pen new-file reference grep ({agent} workspace)")
    if grep_hits:
        for path, lineno, cls, matched, excerpt in grep_hits:
            lines.append(f"- `{path}`:{lineno} [{cls}] matched `{matched}` — {excerpt}")
    else:
        lines.append("- (no reference hits)")
    lines.append(f"- New workspace files this hour ({len(new_files)}):")
    for p in new_files[:MAX_LISTED_NEW_FILES]:
        lines.append(f"  - `{p}`")
    if len(new_files) > MAX_LISTED_NEW_FILES:
        lines.append(f"  - … and {len(new_files) - MAX_LISTED_NEW_FILES} more (count only)")
    for path, why in unreadable:
        lines.append(f"- Not content-grepped: `{path}` — {why}")
    lines.append("")
    lines.append("## Exclusions applied (Sweep 1 only)")
    lines.append("- Pruned prefixes under HOME: " +
                 ", ".join(f"`{p}`" for p in PRUNE_PREFIXES))
    lines.append("- Post-filter: any file named `BOARD.md`.")
    lines.append("- Sweep 2 has NO exclusions by design. Sweep 3 reads only the "
                 "audited pen's own new workspace files, mechanically (paths and "
                 "matched lines, never another pen's prose).")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"RESULT agent={agent} hour={hour:02d} verdict={verdict} "
          f"sweep1={len(sweep1)} tmp={len(sweep2)} grep={len(grep_hits)} "
          f"report={out_path}")
    return 0 if n_hits == 0 else 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pm = sub.add_parser("mark")
    pm.add_argument("--file", required=True)
    pa = sub.add_parser("audit")
    pa.add_argument("--agent", required=True)
    pa.add_argument("--hour", required=True, type=int)
    pa.add_argument("--marker", required=True)
    pa.add_argument("--pen")
    pa.add_argument("--out")
    pa.add_argument("--home", default=str(HOME_DEFAULT))
    pa.add_argument("--tmpdir", default="/tmp")
    args = ap.parse_args()
    if args.cmd == "mark":
        return cmd_mark(args)
    return cmd_audit(args)


if __name__ == "__main__":
    sys.exit(main())
