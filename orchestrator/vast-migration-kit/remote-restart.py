#!/usr/bin/env python3
"""remote-restart.py — STAGED Wonder Island → Vast cutover tool. NOT LIVE.

Restarts ONE agent's world server ON THE RENTED BOX and verifies it, the
target-aware replacement for the clerk's local SERVICE-RESTART step once
an agent's target in ops/world-targets.json is "vast":

  1. supervisorctl restart world-agent-NN on the box, reached by SSH over
     the HTTP CONNECT tunnel documented in vast-migration/MAPPING.md
     (ProxyCommand = the sibling connect-tunnel.py; proxy and credentials
     come from the https_proxy environment variable at runtime — nothing
     secret is stored in this kit);
  2. poll the agent's public URL until GET /api.md answers 200 (<= 90 s);
  3. join as a verification player and GET /observe — the world must hold
     exactly 36 entities (the pristine mesa-island census);
  4. restart once more so no verification session occupies the world's
     single player slot — the world is left fresh, exactly as a local
     boundary restart leaves it — and confirm /api.md 200 again.

Usage: python3 remote-restart.py agent-NN [--targets PATH] [--keep-session]

Exit codes: 0 verified; 2 bad arguments / unknown target; 3 SSH or
supervisor failure; 4 /api.md never answered 200; 5 entity census wrong.
Every step is echoed with a UTC timestamp so the output can be filed as
evidence verbatim.

Python 3 standard library only.
"""

import argparse
import json
import sys
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_TARGETS = (Path.home() / "workspace" / "wonder-island" / "runs"
                   / "confirmatory" / "ops" / "world-targets.json")
EXPECTED_ENTITIES = 36


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    print(f"[{stamp()}] {msg}", flush=True)


def http(method: str, url: str, headers=None, timeout=15):
    req = urllib.request.Request(url, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def wait_api(url: str, timeout_s: int = 90) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            status, _ = http("GET", url + "/api.md", timeout=10)
            if status == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def ssh_supervisor(box: dict, command: str) -> subprocess.CompletedProcess:
    ssh_cfg = box["ssh"]
    proxy_cmd = (f"{sys.executable} {HERE / 'connect-tunnel.py'} %h %p")
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=20",
        "-o", f"ProxyCommand={proxy_cmd}",
    ]
    key = ssh_cfg.get("key")
    if key:
        # Explicit -i is load-bearing: this process runs as root while the
        # house key lives under $HOME (/home/hatch), and ssh resolves its
        # DEFAULT identity paths against the passwd home (/root), where no
        # key exists — without -i no key is offered at all (proven in the
        # staging test, proofs/remote-restart-agent-13-test.log).
        cmd += ["-i", str(Path(key).expanduser()), "-o", "IdentitiesOnly=yes"]
    cmd += [
        "-p", str(ssh_cfg["port"]),
        f"{ssh_cfg['user']}@{box['host']}",
        command,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Restart one agent's world ON THE BOX and verify it (staged).")
    parser.add_argument("agent_id")
    parser.add_argument("--targets", default=str(DEFAULT_TARGETS),
                        help="world-targets.json (default: the live ops path)")
    parser.add_argument("--keep-session", action="store_true",
                        help="skip the final clearing restart (leaves the "
                             "verification session joined — NOT for cutover use)")
    args = parser.parse_args(argv)

    targets = json.loads(Path(args.targets).read_text(encoding="utf-8"))
    entry = (targets.get("agents") or {}).get(args.agent_id)
    if not entry:
        log(f"FAIL: {args.agent_id} not in {args.targets}")
        return 2
    if entry.get("target") != "vast":
        log(f"FAIL: {args.agent_id} target is {entry.get('target')!r}, not 'vast' "
            f"— this tool only restarts box worlds")
        return 2
    box = targets["vast_box"]
    vast = entry["vast"]
    program = vast["supervisor_program"]
    url = vast["url"]
    log(f"remote-restart {args.agent_id}: box {box['host']} "
        f"(instance {box.get('instance_id')}), program {program}, url {url}")

    log(f"step 1/4: supervisorctl restart {program} (via SSH CONNECT tunnel)")
    res = ssh_supervisor(box, f"supervisorctl restart {program}")
    log(f"  ssh exit={res.returncode} stdout={res.stdout.strip()!r} "
        f"stderr={res.stderr.strip()!r}")
    if res.returncode != 0:
        log("FAIL: supervisor restart failed")
        return 3

    log("step 2/4: waiting for GET /api.md 200 on the public URL")
    if not wait_api(url):
        log("FAIL: /api.md never answered 200")
        return 4
    log("  /api.md 200 OK")

    log("step 3/4: join + observe — entity census must be 36")
    _, body = http("POST", f"{url}/join?name=cutover-verify")
    token = json.loads(body)["session"]
    _, body = http("GET", url + "/observe", headers={"X-Session": token})
    entities = json.loads(body)["world"]["entities"]
    names = sorted(e.get("name") for e in entities)
    log(f"  entities={len(entities)} names={names}")
    if len(entities) != EXPECTED_ENTITIES:
        log(f"FAIL: expected {EXPECTED_ENTITIES} entities, got {len(entities)}")
        return 5

    if args.keep_session:
        log("step 4/4: SKIPPED (--keep-session) — verification session left joined")
    else:
        log("step 4/4: clearing restart (verification session must not hold "
            "the single player slot) + final /api.md check")
        res = ssh_supervisor(box, f"supervisorctl restart {program}")
        log(f"  ssh exit={res.returncode} stdout={res.stdout.strip()!r} "
            f"stderr={res.stderr.strip()!r}")
        if res.returncode != 0:
            log("FAIL: clearing restart failed")
            return 3
        if not wait_api(url):
            log("FAIL: /api.md not 200 after the clearing restart")
            return 4
        log("  /api.md 200 OK — world fresh and unoccupied")
    log(f"PASS: {args.agent_id} world restarted on the box and verified "
        f"(api.md 200, {EXPECTED_ENTITIES} entities)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
