# Task 007 (leaf: Acadia-HQ) — Validation record

Parent: [`tasks/007-fix-tailscale-login/validation.md`](../../../../tasks/007-fix-tailscale-login/validation.md)
Repository: Acadia-HQ, working tree at `develop` @ `d2519a4` + task-007 changes
(Makefile, README.md; **no application code changed**).

## Checks

| # | Check | Command / procedure | Result |
|---|---|---|---|
| 1 | Issuer selection default | `make -n run` → expansion; `/proc/$(cat .run/api.pid)/environ` after `make run` | ✅ `ACADIAHQ_OIDC_ISSUER=http://100.89.99.106:8081/realms/acadiahq` (Tailscale IPv4) |
| 2 | Env override honored | `ACADIAHQ_OIDC_ISSUER=http://1.2.3.4:8081/realms/acadiahq make -n run` | ✅ passed verbatim to the API process |
| 3 | Issuer echo consistency | `curl http://100.89.99.106:8081/realms/acadiahq/.well-known/openid-configuration` | ✅ discovery `issuer` == configured issuer (token `iss` validation will pass) |
| 4 | Login URL contract (remote origin `pabi:5173`) | `curl -H 'X-Forwarded-Host: pabi:5173' -H 'X-Forwarded-Proto: http' http://localhost:8000/auth/login` | ✅ Keycloak host `100.89.99.106:8081` (tailnet-reachable), `redirect_uri=http://pabi:5173/auth/callback` |
| 5 | Login URL contract (origin `100.89.99.106:5173`) | same with that `X-Forwarded-Host` | ✅ same Keycloak host; matching `redirect_uri` |
| 6 | Run preflight guard | `make run` while old orphans held 8000/5173/50051 | ✅ new code verified by dry-run expansion + port probe (`ss -tlnH`); orphans were cleaned manually, then `make run` started clean |
| 7 | Listener hygiene | `ss -tlnp` after restart; pid files vs `ps` | ✅ exactly one listener each on 8000 (api pid 4042420), 5173 (vite pid 4042436), 50051 (gateway pid 4042422); `.run/*.pid` match live PIDs |
| 8 | Web on canonical origin | `curl -o /dev/null -w %http_code http://100.89.99.106:5173/` | ✅ 200 |
| 9 | `test-web` | `make test-web` | ✅ 8 passed |
| 10 | `lint` (ruff api + gateway, eslint, vue-tsc) | `make lint` | ✅ exit 0; no unintended file modifications |
| 11 | `test-api` | `make test-api` | ⚠️ 40 passed, **3 failed** — see below |
| 12 | Manual end-to-end login from `blade14` over Tailscale | user: open `http://pabi:5173` (or `http://100.89.99.106:5173`), sign in `admin@example.com` | ⏳ **pending — user verification** |

## test-api: 3 pre-existing failures (not caused by task 007)

- Failing: `tests/test_phase3.py::test_device_health_explains_offline_state`
  (assert `'degraded' == 'offline'` — device-health logic vs test expectation),
  `test_configuration_read_is_durable_signed_and_explicitly_blocked`,
  `test_configuration_write_requires_operator_and_queues_signed_values`.
- Evidence of pre-existence: with the task-007 changes stashed
  (`git stash push Makefile README.md`), the same 3 tests fail identically at
  `develop` @ `d2519a4`; restored after (`git stash pop`).
- Classification: **unrelated to auth/login and to this task** (Makefile +
  README only; device health / signed-configuration assertions). Root cause
  appears to be an app-behavior vs test-expectation drift introduced by
  commit `e779f51` (signed durable configuration control surface).
- Required-check status: **reported as failed, with owner** — decision needed
  whether to fix in a follow-up task or fold into task 007 (scope change).
- Environment note: the suite expects a Postgres at `localhost:55432`
  (`api/tests/conftest.py`); CI provides it as a service. Started locally as
  throwaway container `acadiahq-testdb` (postgres:16-alpine, db
  `acadiahq_test`) for this validation. Wiring a test DB into
  `make test-api`/`db-up` is an open improvement candidate.

## Skipped checks

- Real-browser login from `blade14`: cannot be executed from the host; assigned
  to the user (acceptance criterion 5). All server-side preconditions for it
  are verified above (checks 1–8).

## Known limitations / follow-ups

- With the Tailscale-IP issuer, LAN-only (non-tailnet) clients must use
  `ACADIAHQ_OIDC_ISSUER=http://<lan-ip>:8081/realms/acadiahq make run`
  (documented in README).
- Browsing origins remain per-device single-origin (cookie scoping) — the
  `make run` output now says this explicitly.
- `make stop` still relies on pid files; orphan listeners outside them must be
  killed manually (the new `run` guard detects and explains this).