# Vendored operation-catalog contracts (T-P25, N04)

* `configuration-operations.json` — from Acadia-Configuration
  `contracts/configuration-operations.json` (owner: the device handler).
* `instrumentation-operation-catalog.json` — from Acadia-Configuration
  `contracts/instrumentation-operation-catalog.json`, itself vendored from
  Acadia-Instrumentation `contracts/operation-catalog.json` (generated from
  the spokes' command tables).

Refresh by copying both files. `tests/test_operation_discovery.py` fails if
`SPOKE_OPERATIONS` names a verb the catalog no longer has, or if a catalog
verb has no gateway mapping.
