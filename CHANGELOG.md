# Changelog

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
