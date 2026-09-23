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
        "description": "Apply signed device configuration (device configuration contract v1, transitional HMAC).",
        "integration_status": "contract_v1_device_integrated",
    },
)
