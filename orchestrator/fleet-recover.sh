#!/usr/bin/env bash
# fleet-recover.sh — Wonder Island 13x30 fleet recovery (Track E).
#
# FLEET-PLAN.md §3, Track E output 3. After a VM replacement, /etc is gone;
# the workspace copies under ~/workspace/wonder-island/systemd/ are the
# source of truth. This script:
#   1. asserts the clawblox binary exists (~/.local/bin/clawblox) — fails
#      LOUD and stops if it is gone (it lives under home storage and
#      survived all three pilot-day replacements);
#   2. copies the target units -> /etc/systemd/system/, daemon-reload,
#      enables them, and STARTS any that are not active (never restarts a
#      healthy, active server — Track E fence);
#   3. verifies /api.md 200 per agent SEQUENTIALLY, in agent order; a port
#      that will not serve is NAMED in the output and the exit code, never
#      averaged away;
#   4. per verified agent: appends `UP <fleet-time>` to that agent's
#      machinery.log (pen dir runs/confirmatory/agent-NN/) and clears its
#      down mark via fleet-sentinel.py mark-up. Servers return with FRESH
#      islands — that is machinery, logged as such; per plan D6 each agent
#      resumes at its next scheduled hour boundary.
#
# Ports are parsed from each unit's ExecStart (source of truth = the unit
# file). Commander ruling 2026-10-25: the fleet block is 8111-8123
# (agent-NN -> 8110+NN); a unit whose port falls outside the block draws a
# loud WARNING (the script still recovers it — recovery is not the gate).
#
# Usage:
#   fleet-recover.sh                recover all 13 agents
#   fleet-recover.sh --only 13      recover agent-13 only (drill path)
#   fleet-recover.sh --dry-run      print every action; touch nothing
#
# Exit: 0 all targets verified 200; 1 binary missing / unit missing;
#       3 one or more named agents failed verification.

set -u

WI="$HOME/workspace/wonder-island"
UNIT_SRC="$WI/systemd"
UNIT_DST="/etc/systemd/system"
RUN_ROOT="$WI/runs/confirmatory"
LOG="$WI/logs/fleet-recovery.log"
BINARY="$HOME/.local/bin/clawblox"
SENTINEL="$WI/orchestrator/fleet-sentinel.py"
VERIFY_TIMEOUT_S=45

ONLY=""
DRYRUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --only) ONLY="$2"; shift 2 ;;
    --dry-run) DRYRUN=1; shift ;;
    *) echo "fleet-recover: unknown argument: $1" >&2; exit 1 ;;
  esac
done

fleet_time() { date -u +%Y-%m-%dT%H:%M:%SZ; }

log_line() {
  local line="[$(fleet_time)] $*"
  echo "$line"
  if [ "$DRYRUN" -eq 0 ]; then
    mkdir -p "$(dirname "$LOG")"
    echo "$line" >> "$LOG"
  fi
}

run() {
  # run a command, or just print it in dry-run mode
  if [ "$DRYRUN" -eq 1 ]; then
    echo "DRY-RUN would run: $*"
  else
    "$@"
  fi
}

# ---- 1. binary assertion: fail loud -------------------------------------
if [ ! -x "$BINARY" ]; then
  echo "fleet-recover: FATAL — clawblox binary missing or not executable: $BINARY" >&2
  echo "fleet-recover: recovery impossible; escalate to the Commander." >&2
  exit 1
fi
log_line "binary OK: $BINARY"

# ---- target list ---------------------------------------------------------
targets=""
if [ -n "$ONLY" ]; then
  targets=$(printf '%02d' "$ONLY")
else
  targets=$(seq -w 1 13)
fi

# ---- 2. install + enable + start ----------------------------------------
for nn in $targets; do
  unit="clawblox-wonder-island-agent-${nn}.service"
  src="$UNIT_SRC/$unit"
  if [ ! -f "$src" ]; then
    echo "fleet-recover: FATAL — workspace unit missing: $src" >&2
    exit 1
  fi
  port=$(grep -o -- '--port [0-9]*' "$src" | head -1 | awk '{print $2}')
  if [ -z "$port" ]; then
    echo "fleet-recover: FATAL — no --port in $src" >&2
    exit 1
  fi
  if [ "$port" -lt 8111 ] || [ "$port" -gt 8123 ]; then
    log_line "WARNING agent-${nn}: unit port ${port} is OUTSIDE the ruled block 8111-8123"
  fi
  run cp "$src" "$UNIT_DST/$unit"
done
run systemctl daemon-reload
for nn in $targets; do
  unit="clawblox-wonder-island-agent-${nn}.service"
  run systemctl enable "$unit"
  if [ "$DRYRUN" -eq 1 ]; then
    echo "DRY-RUN would run: systemctl start $unit (only if not already active)"
  else
    if systemctl is-active --quiet "$unit"; then
      log_line "agent-${nn}: already active — left untouched (healthy servers are never restarted)"
    else
      systemctl start "$unit"
      log_line "agent-${nn}: started"
    fi
  fi
done

# ---- 2b. fleet-clock unit (full recoveries only; added 2026-10-25 21:38 PT) --
# The clock died in the 21:23 PT VM replacement because it ran as a plain
# detached process while the world servers (systemd, Restart=always) all
# returned. The clock now lives under systemd too; recover it the same way.
if [ -z "$ONLY" ]; then
  clock_unit="clawblox-fleet-clock.service"
  clock_src="$UNIT_SRC/$clock_unit"
  if [ -f "$clock_src" ]; then
    run cp "$clock_src" "$UNIT_DST/$clock_unit"
    run systemctl daemon-reload
    run systemctl enable "$clock_unit"
    if [ "$DRYRUN" -eq 1 ]; then
      echo "DRY-RUN would run: systemctl start $clock_unit (only if not already active)"
    else
      if systemctl is-active --quiet "$clock_unit"; then
        log_line "fleet-clock: already active — left untouched"
      else
        systemctl start "$clock_unit"
        log_line "fleet-clock: started"
      fi
    fi
  else
    log_line "WARNING: fleet-clock unit missing from workspace copies: $clock_src"
  fi
fi

# ---- 3. sequential verification ------------------------------------------
failed=""
for nn in $targets; do
  unit="clawblox-wonder-island-agent-${nn}.service"
  src="$UNIT_SRC/$unit"
  port=$(grep -o -- '--port [0-9]*' "$src" | head -1 | awk '{print $2}')
  if [ "$DRYRUN" -eq 1 ]; then
    echo "DRY-RUN would verify: GET http://localhost:${port}/api.md (agent-${nn}, up to ${VERIFY_TIMEOUT_S}s)"
    continue
  fi
  ok=0
  waited=0
  while [ $waited -lt $VERIFY_TIMEOUT_S ]; do
    if curl -sf -m 3 "http://localhost:${port}/api.md" >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 2
    waited=$((waited + 2))
  done
  if [ $ok -eq 1 ]; then
    log_line "agent-${nn}: VERIFIED /api.md 200 on port ${port} (after ~${waited}s)"
    # ---- 4. machinery accounting: UP + clear down mark ----
    pen="$RUN_ROOT/agent-${nn}"
    if [ -d "$pen" ]; then
      echo "UP $(fleet_time)" >> "$pen/machinery.log"
      python3 "$SENTINEL" mark-up --agent "$nn" >/dev/null 2>&1 || true
    else
      log_line "agent-${nn}: pen dir absent — UP recorded in recovery log only"
    fi
  else
    log_line "agent-${nn}: FAILED — /api.md did not answer 200 on port ${port} within ${VERIFY_TIMEOUT_S}s"
    failed="$failed agent-${nn}(port ${port})"
  fi
done

if [ -n "$failed" ]; then
  echo "fleet-recover: FAILED agents (named, not averaged):$failed" >&2
  exit 3
fi
log_line "recovery complete: all target agents verified"
exit 0
