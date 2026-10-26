# Vast Migration — Mapping & Provisioning Record

> **Redaction note (for the public repo):** the rented standby server's live IP address, public port numbers, and cloud account/instance identifiers are redacted in this copy — the box is a live standby until the confirmatory run ends. The structure of the port map (internal 8111–8123, one public port per agent) and every method detail are preserved.

**State: DARK.** The box is rented, provisioned, and verified. The live 13×30
confirmatory run has **not** moved — it still runs entirely on the local VM.
Prepared Oct 25, 2026, 22:07 PDT under the principal's approval in chat
("Yes, charge me — rent the powerful New York machine").

## The rental

| Item | Value |
|---|---|
| Instance ID | **[REDACTED-INSTANCE-ID]** |
| Label | wonder-island-worlds |
| Offer / Machine / Host | [REDACTED-OFFER-ID] / [REDACTED-MACHINE-ID] / [REDACTED-HOST-ID] — New York, US |
| Hardware | Xeon E5-2686 v4, 18 vCPU, 32,190 MB RAM, Quadro P4000 ×1 (unused), reliability 0.9972 |
| Image / Disk | ubuntu:22.04 / 20 GB |
| Type | On-demand (not interruptible) |
| Offer rate (compute) | $0.055111/hr — re-verified live immediately before renting |
| **Billed rate as rented** | **$0.061778/hr** (compute + 20 GB storage) ≈ **$1.85 per 30 h** |
| Account | [REDACTED-ACCOUNT-ID] ([REDACTED-EMAIL]) |
| Balance before | [REDACTED-BALANCE]|
| Balance after | [REDACTED-BALANCE]|

**Contract note:** the first create (contract [REDACTED-CONTRACT-ID]) silently dropped the
port mappings — the current Vast API takes the Docker options under the field
`env` with runtype `ssh_direc ssh_proxy`; my first call used a legacy field
name. [REDACTED-CONTRACT-ID] was destroyed after ~13 minutes (minutes billed only) and the
same offer re-rented as [REDACTED-INSTANCE-ID] with the corrected payload. The GEMS keeper
instance [REDACTED-INSTANCE-ID] was never touched (still exited, as found).

## Access

- Public IP: **[REDACTED-IP]**
- SSH (direct): `ssh -p [REDACTED-PORT] root@[REDACTED-IP]` — house default Ed25519 key
  (`~/.ssh/id_ed25519`); the key was also injected into the box's
  `authorized_keys` by the create-time onstart script.
- SSH (Vast proxy fallback): `ssh -p [REDACTED-PORT] root@ssh4.vast.ai`
- From this VM, outbound SSH must ride the runtime egress proxy via HTTP
  CONNECT (direct TCP is intercepted). Working helper used tonight:
  an SSH `ProxyCommand` CONNECT tunnel through the proxy named in the
  `https_proxy` env var. No credential values are recorded in this file.

## Port map (public → internal, all on [REDACTED-IP])

| Agent | Internal | Public | Base URL |
|---|---|---|---|
| agent-01 | 8111 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-02 | 8112 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-03 | 8113 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-04 | 8114 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-05 | 8115 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-06 | 8116 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-07 | 8117 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-08 | 8118 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-09 | 8119 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-10 | 8120 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-11 | 8121 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-12 | 8122 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |
| agent-13 | 8123 | [REDACTED-PORT] | http://[REDACTED-IP]:[REDACTED-PORT] |

(SSH: internal 22 → public [REDACTED-PORT].)

## On the box

- Binary: `/opt/wonder-island/bin/clawblox` — Clawblox 0.1.5, sha256
  `cca5d7d7feb251371cd5e10c53879ad621086a61cde3741e28c2ff21cbbdc14f`,
  byte-identical to the local `~/.local/bin/clawblox`.
- Worlds: `/opt/wonder-island/agents/agent-NN/mesa-island` — pristine trees
  copied from the local fleet copies; datastores were **excluded** from the
  copy and each server created its own fresh `local-81NN.db` on first start.
  `world.toml` sha256 on the box: `d7b321853c1b39fef69ccadf05d8400a0e90457f34869740229fd98d091e1d36`
  (== pristine). `grep -r allow_reset` over all 13 trees: **0 files**.
- Supervisor: **supervisord** (the container has no systemd — PID 1 is `sh`).
  Config: `/etc/supervisor/conf.d/clawblox-worlds.conf` — 13 programs
  `world-agent-01…13`, each
  `clawblox run /opt/wonder-island/agents/agent-NN/mesa-island --port 81NN`,
  `autostart=true`, `autorestart=true`. Logs:
  `/opt/wonder-island/logs/world-agent-NN.log`.
- After any container restart, relaunch with `/opt/wonder-island/start-worlds.sh`.
- Python 3.10.12 is present on the box.

## Verification record (from this VM, over the public internet)

1. **Smoke pass 1** (initial worlds): 11/13 full PASS. agent-01 join returned
   400 — its single player slot (world.toml `max_players = 1`) was still held
   by the calibration join; agent-05's first /api.md hit a transport error,
   its join+observe immediately after passed. Calibration join on agent-01
   itself: /api.md 200, join 200, observe 200.
2. **Restart-all** via supervisorctl (clears smoke sessions → fresh worlds).
3. **Smoke pass 2**: **13/13 PASS** — GET /api.md 200, POST /join 200,
   GET /observe = **36 entities** each, with Spire, Peak, Rock_1, Ring_1 and
   Block_1…Block_12 all present, none missing.
4. **Restart-all again** so no smoke session occupies a player slot, then a
   final **GET /api.md pass: 13/13 → 200**. supervisorctl: 13/13 RUNNING.
   The box is left dark, fresh, and unoccupied.
