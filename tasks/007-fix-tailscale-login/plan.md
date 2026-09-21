# Task 007 (leaf: Acadia-HQ) — Fix Tailscale login (OIDC issuer bound to LAN IP)

Parent task: [`tasks/007-fix-tailscale-login/plan.md`](../../../../tasks/007-fix-tailscale-login/plan.md)
(Acadia parent repository). This leaf plan covers only the Acadia-HQ scope.

## Problem (observed evidence on this host, `pabi`)

- Remote client `blade14` reaches the SPA/API over Tailscale
  (`.run/api.log`: requests from 100.92.53.119, `GET /auth/login` → 200),
  but login dead-ends at the Keycloak redirect.
- `make run` sets `ACADIAHQ_OIDC_ISSUER=http://$(hostname -I | awk '{print $1}'):8081/...`
  → `192.168.86.49` (LAN IP) on this host. Live curl of `/auth/login` returns
  `authorization_url: http://192.168.86.49:8081/...` — unreachable from
  tailnet-only clients.
- Orphaned/stale processes: API pid 4013548 holds :8000 (the 15:45 restart
  failed with "address already in use"), vite pid 4013563 holds :5173 (new
  vite fell back to :5174), two gateway processes on :50051; `.run/*.pid`
  point at dead/wrong PIDs so `make stop` cannot clean them.

## Scope (Acadia-HQ only)

1. **`Makefile` — `run` target issuer selection:**
   - Honor a pre-set `ACADIAHQ_OIDC_ISSUER` from the environment.
   - Else use the first `tailscale ip -4` address when the `tailscale` CLI is
     available and returns one.
   - Else fall back to `hostname -I` first address (current behavior).
   - Update the echo block to print the actual issuer/web/keycloak URLs for
     the chosen host.
2. **`Makefile` — `run` preflight guard:** abort with "ports occupied — run
   `make stop` first" when 8000/5173/50051 are already listening, instead of
   half-starting (root cause of today's orphan/port confusion).
3. **Runtime cleanup + restart** on this host: kill orphans, `make stop`,
   `make run`, verify single listeners and pid-file accuracy.
4. **`README.md`:** brief remote/Tailscale access note + `ACADIAHQ_OIDC_ISSUER`
   override documentation.

## Affected interfaces / files

- `Makefile` (run, echo output) — dev tooling only.
- `README.md` — docs only.
- **No application code changes:** `api/app/**`, `agent-gateway/**`,
  `web/src/**` untouched. No migrations, no schema, no API contract change.

## Local validation

- `/proc/<api-pid>/environ` shows issuer host == Tailscale IP;
  `curl` discovery at that URL echoes the same `issuer`.
- `curl -H 'X-Forwarded-Host: pabi:5173' http://localhost:8000/auth/login`
  → `authorization_url` host == issuer host, `redirect_uri` == browsing origin.
- `ss -tlnp`: exactly one listener each on 8000/5173/50051; `.run/*.pid` match.
- `make test-api`, `make test-web`, `make lint` pass.
- Manual (with user, from `blade14`): sign in at `http://pabi:5173` or
  `http://100.89.99.106:5173` with seeded `admin@example.com`; session survives
  reload (`/auth/me` → 200).

## Role in cross-repository validation

None required beyond the parent: all ten other leaves are unaffected (no
shared interface, schema, config, packaging, or platform assumption changes).
Parent records the consolidated validation in its `validation.md`.