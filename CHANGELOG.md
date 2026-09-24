# Changelog

## 2026-09-24 — Integration-production pass (T-P20…T-P35, backlog)

- T-P20: device command API for power, updates, services, users and log bundles, with a SPOKE_OPERATIONS allowlist. Also fixes the command dispatcher (HQ-019) and the offline health status.
- T-P21: OTA artifact store with HQ-side SHA-256 verification, and staged rollouts (canary, halt, resume, auto-activate) with a Remote updates UI.
- T-P22…T-P25:
  - upload rows are finalised by UploadComplete;
  - SigV4 presigning;
  - alarm ack/clear propagates to the device;
  - DeviceStatus snapshot and health factors;
  - operation catalog taken from vendored contracts.
- T-P34:
  - server-side sessions;
  - OIDC nonce and email_verified checks;
  - rate limiting and WebSocket origin check;
  - user lifecycle management;
  - production is the default environment;
  - the gateway refuses plaintext in production;
  - compose images pinned by digest.
- HQ-018: API and gateway tests start an ephemeral Postgres when none is reachable.
- Validation: api 81, gateway 38, web 37, lint clean, E2E 15/15.

## 2026-09-21 — Cross-repo API surface audit: API gap closure (task 009)

### Added

- New updates command router with regression tests; log-bundle fetch
  via istate bulk socket; command ack result-payload propagation
  in configuration/device services.
- Mounted the previously missing backups router (regression-tested).

## 2026-09-21 — Device detail: 1:1 WebConfig (Acadia-Configuration) UI (task 008)

- Selecting a device in HQ now presents the WebConfig experience 1:1: design
  tokens (zinc + sky-blue accent) ported app-wide, a categorized device
  sidebar (36 sections mirroring the WebConfig registry: Dashboard, System,
  Time & Sync, Connectivity, Maintenance, Security, Hardware), topbar with
  device identity/status/health, Ctrl+K command palette, `g <key>` chords,
  toasts, skeletons, confirm dialogs, and admin-only gating.
- Live sections are backed by existing HQ APIs (overview/health, monitoring,
  telemetry, faults, alarms with ack/resolve/clear, log bundles, backups,
  factory reset/disable, update operation catalog).
- Configuration-backed sections (system, clock/NTP/PTP/GPS, wired, wireless,
  5G, services, cloud, security, SSH, firewall, secure boot, users, display,
  LEDs, GPIO, serial, CAN, USB, PCI, MCU, camera, telemetry policy) render
  schema-driven forms via the existing 202-queued configuration command
  channel and show explicit pending-contract states until the device reports
  its configuration; they need no further UI change when the contract lands.
- Web-only change: no API, gateway, or migration changes; API client gained
  additive methods (device health, command status, operations catalog,
  configuration read/write). Superseded device tab panels removed.
- Validation: web tests 25/25, lint 0, build ok, section registry 36/36 vs
  Acadia-Configuration, token values identical; API/gateway suites unchanged
  (pre-existing failures documented in the task records).

## 2026-09-21 — Fix login over Tailscale (task 007)

- `make run` no longer bakes the OIDC issuer (Keycloak) URL to the first LAN
  address, which broke login from Tailscale clients: the browser was
  redirected to a Keycloak host it could not route to. The issuer host is now
  selected as: pre-set `ACADIAHQ_OIDC_ISSUER` (verbatim) > first Tailscale
  IPv4 > first `hostname -I` address; the `run` output prints the canonical
  URLs. Documented in README (Tailscale/LAN access section).
- `make run` now refuses to start when ports 8000/5173/50051 are already in
  use (previously it half-started, orphaning old processes and leaving stale
  pid files that `make stop` could not clean).
- No application code changes (`api/app/**`, `agent-gateway/**`, `web/src/**`
  untouched); no migrations; no API contract change.

## 2026-09-21 — Root-agent feature workflow guard (task 006)

- Added a canonical instruction requiring leaf-started agents to refuse feature
  changes and direct the user to the Acadia parent root.

## 2026-09-18 — Agent documentation and task workflow standardization

- Replaced the detailed root `CLAUDE.md` with a canonical pointer and added
  `AGENTS.md`.
- Added a concise canonical document with installation, Docker build, and test
  instructions.
- Added ignored local `Plan.md` and `Task.md` workflow artifacts.
- Verified the required document shape and the declared `make install`,
  `make build`, and `make test` targets.

Maintained by the Loop Engine. One entry per loop that touched this repo,
newest first, appended on loop close (pass or fail) and committed on the loop's
own feature branch. See the master repo's `Acadia-Loop-Orchestration-Spec-v2.md` §11.1.

Entries written by hand are fine; the engine inserts directly under this header.

## 2026-07-30 — [20260730-app-telemetry-daemon] Telemetry daemon streams configurable key-value metrics and Acadia-HQ can ingest a sample
- Status: SUCCESS (try 1 of 4)- Verdict: auditor: UPHOLD; orchestrator: ACCEPT-WITH-FINDINGS
