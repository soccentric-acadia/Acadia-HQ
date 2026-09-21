# Task 008 (leaf: Acadia-HQ) — Validation record

Parent: [`tasks/008-hq-device-ui-webconfig-parity/validation.md`](../../../tasks/008-hq-device-ui-webconfig-parity/validation.md)

| # | Check | Command | Result |
|---|---|---|---|
| 1 | `test-web` | `npx vitest run` | ✅ 24/24 (6 files) |
| 2 | Registry parity vs Acadia-Configuration | `node scripts/check-section-parity.mjs` | ✅ 36/36 |
| 3 | Token parity vs Acadia-Configuration | token value diff | ✅ identical |
| 4 | `lint-web` | `make lint-web` (oxlint + eslint + vue-tsc) | ✅ exit 0 |
| 5 | `build` (web) | `npm run build` | ✅ |
| 6 | `test-api` (regression, no api changes) | `make test-api` | ✅ 40/43; 3 failures pre-existing (task 007 record; clean-tree repro) |
| 7 | `test-gateway` (regression) | `make test-gateway` | ✅ 15/17; 2 failures pre-existing (clean-tree stash repro) |
| 8 | Dev-server integration | running stack on :8000/:5173/:50051 | ✅ modules compile/served; UI API paths route (401 pre-auth) |
| 9 | Manual browser walkthrough | OIDC login → device → sections | ⏳ pending user (interactive login) |

Task 007's uncommitted work (Makefile/README/CHANGELOG/.run, task records, stash@{0}) untouched and preserved.
## Audit (2026-09-21)

Score 92/100 — criteria, deductions, and evidence in the parent
`validation.md`. Audit-caught gaps (palette admin filtering, refresh action)
fixed and re-validated: `make lint` 0, vitest 25/25, build ok, parity 36/36.
