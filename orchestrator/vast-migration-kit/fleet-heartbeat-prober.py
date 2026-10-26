#!/usr/bin/env python3
"""fleet-heartbeat-prober.py — STAGED (vast-migration kit, NOT LIVE).

Why this exists (CUTOVER-CHECKLIST §3, superseded fix — see
HEARTBEAT-UNBLOCK.md): the fleet-clock runs as a long-lived systemd unit
whose environment cannot reach the rented box, because this runtime
ROTATES its egress-proxy credentials per session — any credential
captured into a static file is dead by the time the clock uses it
(407 Proxy Authentication Required, proven Oct 25–26, 2026).

So the probe moves to where fresh credentials exist: an agent-context
process (a clerk tick, an operator shell). This prober probes each
vast-targeted agent's world and writes the result as a small heartbeat
JSON. The patched fleet-clock never probes a remote URL itself; for a
vast agent its health gate reads the heartbeat and passes only if the
heartbeat is FRESH (< 10 min old — the clerk ticks every 5 min) and
records status ok. Local agents are never probed by this tool and never
read heartbeats; their gate probe stays the direct localhost GET.

Safety — the single player slot: a world's slot (max_players = 1) is
held by ANY join until the world restarts; there is no leave endpoint.
The gate's own criterion is GET /api.md 200, so the default tick probe
is /api.md only and NEVER joins. The entity census (--census) joins and
therefore HOLDS the slot: use it only pre-flight / on a dark box, and
clear the held session afterwards with remote-restart.py (the join is
recorded in the heartbeat as slot="held-by-prober" so it is never
silent). A census join that fails because a player is in the world is
recorded as slot="occupied" with entity_count null — the world is
still healthy; the census is simply unavailable that tick.

Usage:
  fleet-heartbeat-prober.py [--targets PATH] [--out-dir PATH]
                            [--agent agent-NN ...] [--census]

Defaults: --targets is the confirmatory ops world-targets.json under
~/workspace/wonder-island/runs/confirmatory/ops (the install path);
--out-dir defaults to a heartbeats/ directory beside the targets file.
At cutover the clerk runs this once per tick with no arguments.

Heartbeat JSON (one file per agent, written atomically):
  {agent, target, url, ts, iso, status ("ok"|"down"), http_status,
   entity_count (int|null), slot, census (bool), error (str|null)}

Exit status: 0 if every probed vast agent is ok (or no agent is
vast-targeted), 4 otherwise. The prober reports; it never restarts,
spawns, throttles, or writes anywhere except its heartbeat files.

Python 3 standard library only. Proxy credentials are taken from the
process environment by urllib at runtime and are never read, printed,
or stored by this script.
"""

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TARGETS = (Path.home() / "workspace" / "wonder-island" / "runs"
                   / "confirmatory" / "ops" / "world-targets.json")
PROBE_TIMEOUT_S = 5.0
JOIN_NAME = "heartbeat-prober"


def http(method, url, headers=None, timeout=PROBE_TIMEOUT_S):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


def probe_agent(agent_id, entry, census):
    url = (entry.get("vast") or {}).get("url", "")
    hb = {"agent": agent_id, "target": "vast", "url": url,
          "ts": time.time(), "iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
          "status": "down", "http_status": None, "entity_count": None,
          "slot": "not-probed", "census": bool(census), "error": None}
    if not url:
        hb["error"] = "target is 'vast' but world-targets gives no vast.url"
        return hb
    try:
        status, _ = http("GET", url + "/api.md")
        hb["http_status"] = status
    except Exception as exc:  # transport error or non-200 (HTTPError)
        hb["http_status"] = getattr(exc, "code", None)
        hb["error"] = f"api.md probe failed: {exc}"
        return hb
    if hb["http_status"] == 200:
        hb["status"] = "ok"
    if census:
        try:
            _, body = http("POST", f"{url}/join?name={JOIN_NAME}")
            token = json.loads(body)["session"]
        except Exception as exc:
            hb["slot"] = "occupied"  # a player (or stale session) holds it
            hb["error"] = f"census join unavailable: {exc}"
            return hb
        hb["slot"] = "held-by-prober"
        try:
            _, body = http("GET", url + "/observe", headers={"X-Session": token})
            entities = json.loads(body)["world"]["entities"]
            hb["entity_count"] = len(entities)
        except Exception as exc:
            hb["error"] = f"census observe failed: {exc}"
    return hb


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Vast-world heartbeat prober (staged; see HEARTBEAT-UNBLOCK.md).")
    parser.add_argument("--targets", default=str(DEFAULT_TARGETS))
    parser.add_argument("--out-dir", default=None,
                        help="default: heartbeats/ beside the targets file")
    parser.add_argument("--agent", action="append", default=None,
                        help="probe only this agent (repeatable); default: all vast-targeted agents")
    parser.add_argument("--census", action="store_true",
                        help="also join + observe for the entity count (HOLDS the world slot "
                             "until a restart — pre-flight / dark-box use only)")
    args = parser.parse_args(argv)

    targets_path = Path(args.targets)
    if not targets_path.exists():
        print(f"no targets file at {targets_path} — nothing is vast-targeted; no heartbeats written")
        return 0
    data = json.loads(targets_path.read_text(encoding="utf-8"))
    agents = data.get("agents") or {}
    wanted = [aid for aid, e in sorted(agents.items())
              if (e or {}).get("target") == "vast"
              and (args.agent is None or aid in args.agent)]
    if not wanted:
        print("no vast-targeted agents in the targets file; no heartbeats written")
        return 0

    out_dir = Path(args.out_dir) if args.out_dir else targets_path.parent / "heartbeats"
    out_dir.mkdir(parents=True, exist_ok=True)

    worst = 0
    for aid in wanted:
        hb = probe_agent(aid, agents[aid], args.census)
        dest = out_dir / f"{aid}.json"
        tmp = out_dir / f".{aid}.json.tmp"
        tmp.write_text(json.dumps(hb, indent=2) + "\n", encoding="utf-8")
        tmp.replace(dest)
        print(f"{aid}: status={hb['status']} http={hb['http_status']} "
              f"entities={hb['entity_count']} slot={hb['slot']} -> {dest}")
        if hb["slot"] == "held-by-prober":
            print(f"  WARNING: census session HELD on {aid}'s world — clear it with "
                  f"remote-restart.py {aid} before any player joins")
        if hb["error"]:
            print(f"  note: {hb['error']}")
        if hb["status"] != "ok":
            worst = 4
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
