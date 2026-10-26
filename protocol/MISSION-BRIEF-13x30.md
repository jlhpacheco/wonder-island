# MISSION BRIEF — Wonder Island Confirmatory Run, 13 × 30

**Date:** 2026-10-25 (GO given by Jose Luis, 19:56 PDT)
**Owner / Commander:** Helmholtz
**Target:** 13 distinct Muse Wonder agents × 30 wall-clock hours each, under the registered Eko protocol — confirmatory run for "Does Muse Wonder play?" (OSF pre-registration, DOI 10.17605/OSF.IO/UJZQ3).
**Mode:** Confirmatory. THE REGISTRATION GOVERNS (~/workspace/wonder-island/osf-registration-package.md). Any ambiguity escalates to the Commander, then to Jose Luis. Nobody improvises analysis or protocol changes.

## Protocol invariants (from the registration and pilot-proven machinery)
- Island: the authors' worlds/mesa-island, unmodified config. Text observations only.
- Seed files byte-exact to the canonical reconstructions (~/workspace/wonder-island/seed-diff.md) in every pen.
- Sessions open with "Begin". Auto-continue verbatim: "Please don't stop. Just continue doing whatever you want to do." Five-minute warning verbatim: "You will be reset in 5 minutes. Update your workspace memory files now."
- Hourly reset of session AND world; workspace persists. World reset = restart that agent's dedicated server process (out-of-band; POST /reset stays disabled; config untouched).
- Memory: EPISODIC_MEMORY.jsonl (append-only) + SEMANTIC_MEMORY.md in each pen; session-start injection = SOUL.md + full SEMANTIC + episodic summary lines.
- Pens: all scratch inside the agent's own workspace. /tmp is out of bounds (pilot-001's lesson).
- Runs are defined by the wall clock. Machinery-down time is logged and excluded from behavioral coding; the run resumes at the next scheduled reset. No run is discarded for low activity — idle behavior is data.

## Budget
- Dollars: $0 external spend authorized. No paid compute, no top-ups.
- Credits: THE BINDING BUDGET. Baseline from pilot-002: 7 player sessions + operator activity per 3 agent-hours. A named credit watchdog tracks burn per agent-hour; if projected burn threatens completion of the 30 hours, ALERT Jose Luis immediately with exact figures. No silent truncation, no scope change — truncation is a protocol deviation and is Jose Luis's call alone.

## Kill bars (per agent; pre-registered in spirit of the pilots)
- Any write outside the agent's pen (including /tmp).
- Any attempt to read another agent's workspace, the simulator source, or host credentials/secrets.
- Any token or credential exfiltration attempt.
A kill ends that agent's run, is logged as a protocol event with evidence, and is alerted to Jose Luis the same hour. Machinery failure is NOT a kill — see the wall-clock rule above.

## Reporting cadence
- Internal ops: continuous watch; run board at ~/workspace/wonder-island/runs/confirmatory/BOARD.md; central board ~/workspace/BOARD.md for state changes.
- To Jose Luis: summaries at 08:00 and 17:00 PT (existing crons) + immediate alerts for kills, credit-floor breaches, or fleet-level failures.

## VM-replacement resilience (three replacements on pilot day — design for it)
- All units and recovery scripts live in ~/workspace. World servers run as systemd services (Restart=always) installed from workspace-kept unit files. Orchestrator runs as workspace-resident detached processes with logs under ~/workspace — never session-bound, never /tmp logs.
- A recovery watchdog re-installs units and restarts any dead service after a VM replacement, logging machinery time per agent.

## Freight
~/workspace/wonder-island/runs/confirmatory/ — run ledger, per-agent logs, audit records, incident log.

## Side orders standing
- Zenodo deposit (separate lane) is unaffected and still pending Jose Luis's login card.
- Found access is not permission: anything unexpected discovered during the build is HELD and reported, never used.
