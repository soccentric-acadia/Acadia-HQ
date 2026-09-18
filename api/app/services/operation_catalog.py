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
)
