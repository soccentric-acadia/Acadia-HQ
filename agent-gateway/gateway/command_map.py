"""PendingCommand kind → AgentLink ``Command`` fields.

Pulled out of the dispatcher (T-P20) so every mapping is unit-testable. Each
entry returns the keyword fields for ``Command(...)``; three keys are
special and consumed by the dispatcher rather than passed through:

* ``operation`` — the device operation name (defaults to the entry's name);
* ``daemon`` — the target daemon (defaults to the ``configuration``
  pseudo-daemon that webconfigd executes locally; generic spoke operations
  override it with the Instrumentation spoke name).

New kinds ride the generic ``operation``/``json_args`` fields, so no proto
bump is needed for them.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from acadiahq.agent_pb2 import ApplyUpdate, FactoryReset, Restore, TakeBackupNow

from app.models.enums import CommandKind

# Confirmation strings the device demands for destructive verbs (mirrored in
# Acadia-Configuration hq_bridge.rs REQUIRED_*_CONFIRMATION).
FACTORY_RESET_CONFIRMATION = "FACTORY-RESET"
SHUTDOWN_CONFIRMATION = "SHUTDOWN"
ROLLBACK_CONFIRMATION = "ROLLBACK"

# Payload keys that must never outlive delivery in the HQ database (T-P20:
# users.create carries the initial password to the device).
SENSITIVE_PAYLOAD_KEYS = ("password",)


def _json_args(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _plain(payload: dict[str, Any]) -> dict[str, Any]:
    return {"json_args": _json_args(payload)}


def _users(payload: dict[str, Any]) -> dict[str, Any]:
    args = {k: v for k, v in payload.items() if k != "operation"}
    return {"operation": payload["operation"], "json_args": _json_args(args)}


def _operation_run(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "daemon": payload["daemon"],
        "operation": payload["operation"],
        "json_args": _json_args(payload.get("args") or {}),
    }


OPERATIONS: dict[CommandKind, tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]] = {
    CommandKind.take_backup_now: ("backup", lambda p: {"take_backup_now": TakeBackupNow()}),
    CommandKind.restore: (
        "restore",
        lambda p: {"restore": Restore(backup_download_url=p.get("backup_download_url", ""))},
    ),
    # The device gate (hq_bridge REQUIRED_FACTORY_RESET_CONFIRMATION): an HQ
    # factory reset without this confirmation is refused on-device (task 009).
    CommandKind.factory_reset: (
        "factory_reset",
        lambda p: {
            "factory_reset": FactoryReset(),
            "required_confirmation": FACTORY_RESET_CONFIRMATION,
        },
    ),
    CommandKind.apply_update: (
        "apply_update",
        lambda p: {
            "apply_update": ApplyUpdate(
                artifact_id=p.get("artifact_id", ""),
                artifact_download_url=p.get("artifact_download_url", ""),
                checksum_sha256=p.get("checksum_sha256", ""),
            )
        },
    ),
    CommandKind.configuration_read: ("configuration.read", _plain),
    CommandKind.configuration_write: ("configuration.write", _plain),
    # T-P11 (B05)
    CommandKind.ssh_keys_set: ("ssh_keys.set", _plain),
    # T-P20 (C04/C05)
    CommandKind.reboot: ("system.reboot", _plain),
    CommandKind.shutdown: (
        "system.shutdown",
        lambda p: {**_plain(p), "required_confirmation": SHUTDOWN_CONFIRMATION},
    ),
    # T-P20 (K10)
    CommandKind.reboot_to_apply: ("update.reboot_to_apply", _plain),
    CommandKind.confirm_update: ("update.confirm", _plain),
    CommandKind.rollback_update: (
        "update.rollback",
        lambda p: {**_plain(p), "required_confirmation": ROLLBACK_CONFIRMATION},
    ),
    # T-P20 (G02, J04, B02, N05)
    CommandKind.service_control: ("service.control", _plain),
    CommandKind.log_bundle_request: ("log_bundle.request", _plain),
    CommandKind.users_command: ("users", _users),
    CommandKind.operation_run: ("operation.run", _operation_run),
}


def build_command_fields(
    kind: CommandKind, payload: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Fields for ``Command(...)`` (incl. ``operation``/``daemon``), or None
    when the kind has no device mapping."""
    entry = OPERATIONS.get(kind)
    if entry is None:
        return None
    name, build = entry
    fields = build(payload or {})
    fields.setdefault("operation", name)
    fields.setdefault("daemon", "configuration")
    return fields


def scrub_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop credentials from a delivered command's stored payload."""
    if not payload:
        return payload
    if not any(k in payload for k in SENSITIVE_PAYLOAD_KEYS):
        return payload
    return {k: ("[scrubbed]" if k in SENSITIVE_PAYLOAD_KEYS else v) for k, v in payload.items()}
