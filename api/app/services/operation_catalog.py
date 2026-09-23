"""Operations that HQ can durably deliver through the device gateway."""

OPERATIONS = (
    {
        "name": "backup",
        "daemon": "configuration",
        "command_kind": "take_backup_now",
        "description": "Capture and upload a device backup.",
    },
    {
        "name": "restore",
        "daemon": "configuration",
        "command_kind": "restore",
        "description": "Restore a previously uploaded device backup.",
    },
    {
        "name": "factory_reset",
        "daemon": "configuration",
        "command_kind": "factory_reset",
        "description": "Reset the device to factory configuration.",
    },
    {
        "name": "apply_update",
        "daemon": "configuration",
        "command_kind": "apply_update",
        "description": "Install a signed device update artifact.",
    },
    {
        "name": "configuration.read",
        "daemon": "configuration",
        "command_kind": "configuration_read",
        "description": "Read device configuration (device configuration contract v1).",
        "integration_status": "contract_v1_device_integrated",
    },
    {
        "name": "ssh_keys.set",
        "daemon": "configuration",
        "command_kind": "ssh_keys_set",
        "description": "Provision the device operator account's authorized_keys (T-P11).",
        "integration_status": "device_integrated",
    },
    {
        "name": "configuration.write",
        "daemon": "configuration",
        "command_kind": "configuration_write",
        "description": "Apply signed device configuration (contract v1, Ed25519-signed, T-P13).",
        "integration_status": "contract_v1_device_integrated",
    },
    {
        "name": "system.reboot",
        "daemon": "configuration",
        "command_kind": "reboot",
        "description": "Reboot the device; executed after the outcome is acknowledged (T-P20).",
        "integration_status": "device_integrated",
    },
    {
        "name": "system.shutdown",
        "daemon": "configuration",
        "command_kind": "shutdown",
        "description": "Power the device off; carries required_confirmation SHUTDOWN (T-P20).",
        "integration_status": "device_integrated",
    },
    {
        "name": "update.reboot_to_apply",
        "daemon": "configuration",
        "command_kind": "reboot_to_apply",
        "description": "Tryboot into the freshly installed slot (T-P20).",
        "integration_status": "device_integrated",
    },
    {
        "name": "update.confirm",
        "daemon": "configuration",
        "command_kind": "confirm_update",
        "description": "Mark the running slot good (T-P20).",
        "integration_status": "device_integrated",
    },
    {
        "name": "update.rollback",
        "daemon": "configuration",
        "command_kind": "rollback_update",
        "description": "Re-arm the previous slot and reboot; carries required_confirmation ROLLBACK"
        " (T-P20).",
        "integration_status": "device_integrated",
    },
    {
        "name": "service.control",
        "daemon": "configuration",
        "command_kind": "service_control",
        "description": "Start/stop/restart/enable/disable one allowlisted device unit (T-P20).",
        "integration_status": "device_integrated",
    },
    {
        "name": "log_bundle.request",
        "daemon": "configuration",
        "command_kind": "log_bundle_request",
        "description": "Create a device support bundle and upload it to HQ (T-P20).",
        "integration_status": "device_integrated",
    },
    {
        "name": "users",
        "daemon": "configuration",
        "command_kind": "users_command",
        "description": "Local device web-UI accounts: users.list/create/delete/set_role (T-P20).",
        "integration_status": "device_integrated",
    },
    {
        "name": "operation.run",
        "daemon": "configuration",
        "command_kind": "operation_run",
        "description": "Allowlisted Instrumentation spoke operation (SPOKE_OPERATIONS, T-P20).",
        "integration_status": "device_integrated",
    },
)

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
