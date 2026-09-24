"""Operations that HQ can durably deliver through the device gateway.

T-P25 (N04): the catalog is built from two contract files instead of a hand
copy:

* ``contracts/configuration-operations.json`` — vendored from
  Acadia-Configuration (owner): the device-local ``configuration`` verbs;
* ``contracts/instrumentation-operation-catalog.json`` — vendored from
  Acadia-Instrumentation (generated from the spokes' command tables).

``SPOKE_OPERATIONS`` below is HQ *policy* (which spoke verbs HQ may run and
the minimum role); tests assert every entry exists in the vendored catalog.
"""

import json
from pathlib import Path

_CONTRACTS = Path(__file__).resolve().parent.parent / "contracts"


def _load(name: str) -> dict:
    return json.loads((_CONTRACTS / name).read_text(encoding="utf-8"))


CONFIGURATION_CATALOG = _load("configuration-operations.json")
INSTRUMENTATION_CATALOG = _load("instrumentation-operation-catalog.json")

OPERATIONS = tuple(
    {**op, "integration_status": "device_integrated"}
    for op in CONFIGURATION_CATALOG["operations"]
) + (
    {
        "name": "operation.run",
        "daemon": "configuration",
        "command_kind": "operation_run",
        "description": "Allowlisted Instrumentation spoke operation (SPOKE_OPERATIONS, T-P20).",
        "integration_status": "device_integrated",
    },
)


def spoke_catalog() -> dict[str, list[dict]]:
    """Instrumentation spoke verbs, from the generated catalog."""
    return INSTRUMENTATION_CATALOG["spokes"]


# T-P20 (N05): the Instrumentation spoke operations HQ may run through the
# generic ``operation.run`` command, with the minimum role for each. Anything
# absent is refused before a command row exists. Deliberately excluded: OTA
# (single owner is SWUpdate via Configuration, T-P00c), reset/factory-reset
# (dedicated confirmed commands), config-set/apply-plan (B-01 — Configuration
# owns operator config), raw gpio-set/can-send/usb-reset, relay, drain,
# backup restore.
SPOKE_OPERATIONS: dict[tuple[str, str], str] = {
    **{("istate", op): "operator" for op in (
        "status", "spokes", "health", "timeline", "budgets", "spool-stats", "system-info",
    )},
    **{("monitord", op): "operator" for op in ("status", "sample-once", "wear")},
    **{("networkd", op): "operator" for op in (
        "status", "ifaces", "firewall-get", "ssh-list", "tunnel-status",
    )},
    ("networkd", "ssh-open"): "admin",   # F03: temporary SSH access window
    ("networkd", "ssh-close"): "admin",
    **{("hardware", op): "operator" for op in (
        "list-devices", "check", "check-all", "gpio-get",
    )},
    ("hardware", "led-set"): "admin",
    ("hardware", "led-blink"): "operator",
    **{("faults", op): "operator" for op in ("stats", "rules-list")},
    **{("alarms", op): "operator" for op in ("list", "ack", "clear")},
    **{("logmanager", op): "operator" for op in ("sources", "stats", "bundle-list")},
    ("logmanager", "level-set"): "admin",  # G07: per-source log level
    **{("telemetry", op): "operator" for op in ("list-metrics", "buffer-stats", "health-score")},
    **{("backup", op): "operator" for op in ("list", "verify", "schedule-get")},
    ("backup", "create"): "admin",
    ("backup", "schedule-set"): "admin",
}
