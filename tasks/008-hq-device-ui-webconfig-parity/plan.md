# Task 008 (leaf: Acadia-HQ) — Device detail: 1:1 WebConfig look, feel, and features

Parent: [`tasks/008-hq-device-ui-webconfig-parity/plan.md`](../../../tasks/008-hq-device-ui-webconfig-parity/plan.md)
- **Status:** PROPOSED — awaiting plan approval
- **Role in task:** affected (implementation repository; `web/` only)

## Scope

Rebuild the device-level experience in the HQ web client to match Acadia-Configuration
(WebConfig) 1:1: design tokens, app-shell layout (categorized sidebar + topbar), full section
registry, command palette, keyboard chords, dirty-guard, and role gating. No API changes
planned — the existing endpoints cover the UI:

- `GET /devices` / `GET /devices/{id}` / `GET /devices/{id}/health` / `GET
  /devices/{id}/commands/{command_id}`
- `GET /devices/{id}/telemetry`, `/faults`, `/alarms`, `/logs`, `/backups` (+ take/restore)
- `POST /devices/{id}/factory-reset`, `/devices/{id}/disable`
- `GET /operations` (catalog), `GET/PUT /devices/{id}/configuration` (202-queued contract)

## Affected interfaces

- Web-only: `web/src/assets/main.css` (tokens), `web/src/views/DeviceDetailView.vue`
  (shell), new `web/src/views/device/` sections, new `web/src/components/wc/*` primitives,
  `web/src/router/index.ts` (nested routes), `web/src/lib/` (section registry, palette,
  chords). Existing views keep working under the new token palette.

## Expected files / components

- `src/assets/main.css` — WebConfig token set (zinc + sky accent, radii, shadows, type).
- `src/views/DeviceDetailView.vue` — WebConfig app shell (sidebar, topbar, content).
- `src/lib/sections.ts` — section registry mirroring WebConfig `NAV` (id, label, icon,
  category, adminOnly, chord) with a parity test against the Configuration registry.
- `src/views/device/*.vue` — Overview, Monitoring, Telemetry, Faults, Alerts, Logs, Updates,
  Backup & Restore, System Control, and configuration-backed sections (System, Clock, NTP,
  PTP, GPS, Wired, Wireless, 5G, Services, Cloud, Security, SSH, Firewall, Secure Boot,
  Users, Display, LEDs, GPIO, Serial, CAN, USB, PCI, MCU, Camera) using a shared
  schema-driven form + pending-contract callouts.
- `src/components/wc/*` — parity primitives: ActionRow, Callout, EmptyState, Toggle, Toast,
  CommandPalette, Skeleton.
- `web/src/router/index.ts` — nested section routes.

## Local tests

- Vitest: registry parity vs WebConfig `NAV`, shell composition, schema-form validation,
  dirty-guard, palette navigation, admin gating; update existing specs for the new palette.
- `npm run type-check`, `lint`, `test:unit`, `build-only` via the web Makefile targets.

## Cross-repository validation role

- Diff section registry against `Acadia-Configuration/frontend/pages/registry.js`.
- Verify rendered token values against `Acadia-Configuration/frontend/styles/tokens.css`.
- Run api + web locally and walk Devices → device → every section (live data +
  configuration read/write queued states).

## Constraints

- Do not touch uncommitted task-007 files (`Makefile`, `README.md`, `CHANGELOG.md`,
  `.run/*`); changelog update is an append-only addition at task close.
- No `api/`, gateway, or migration changes without renewed user approval.