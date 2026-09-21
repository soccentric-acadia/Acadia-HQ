# Task 007 (leaf: Acadia-HQ) — Execution record

Parent: [`tasks/007-fix-tailscale-login/execution.md`](../../../../tasks/007-fix-tailscale-login/execution.md)
- **Approval:** 2026-09-21 ("ok") — scope as in this leaf's `plan.md`.

## Checklist

- [x] `Makefile`: issuer host selection (env override > Tailscale IPv4 > LAN).
- [x] `Makefile`: `run` preflight guard for ports 8000/5173/50051.
- [x] `Makefile`: `run` echo block reflects the canonical host.
- [x] Runtime cleanup + clean restart on `pabi` (orphans killed; one listener
      per port; pid files accurate).
- [x] `README.md`: Tailscale/remote access note.
- [x] Validation per plan; `validation.md` (server-side contracts green;
      `test-web` 8/8; `lint` 0; `test-api` 40/43 — 3 pre-existing failures
      reported; manual `blade14` login pending user).

## Files changed (actual)

- `Makefile` — issuer selection, preflight guard, echo block (approved phases
  1–2; no application code touched).
- `README.md` — new "Accessing HQ from other devices (Tailscale / LAN)" section.
- `CHANGELOG.md` — task 007 entry.
- `tasks/007-fix-tailscale-login/` — plan/execution/validation records.
- Runtime side effects only: `.run/*.log` (service logs), `.run/*.pid`
  (untracked), throwaway docker container `acadiahq-testdb` on 55432 used for
  the test suite.

## Deviations

- None in scope. Validation environment note: started throwaway
  `acadiahq-testdb` Postgres on 55432 (suite prerequisite, CI-provided in CI);
  no repo change.

## Commands and decisions

- `make -n run` (expansion checks, default + override) before runtime changes.
- `make stop`; `kill 4013548 4013563 4013553` (orphans not in pid files);
  `make run`; verified `/proc/<api>/environ`, discovery issuer echo,
  `/auth/login` authorization_url for two remote origins, `ss -tlnp`.
- `make test-web`, `make lint`, `make test-api` (failures proven pre-existing
  via `git stash push Makefile README.md` → same 3 failures at `d2519a4` →
  `git stash pop`).