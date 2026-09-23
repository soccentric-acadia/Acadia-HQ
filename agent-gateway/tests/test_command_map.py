"""T-P20: PendingCommand kind → AgentLink Command field mapping."""

import json

import pytest

from app.models.enums import CommandKind
from gateway.command_map import OPERATIONS, build_command_fields, scrub_payload


def test_every_command_kind_has_a_device_mapping():
    assert set(OPERATIONS) == set(CommandKind)


@pytest.mark.parametrize(
    "kind,operation,confirmation",
    [
        (CommandKind.reboot, "system.reboot", None),
        (CommandKind.shutdown, "system.shutdown", "SHUTDOWN"),
        (CommandKind.reboot_to_apply, "update.reboot_to_apply", None),
        (CommandKind.confirm_update, "update.confirm", None),
        (CommandKind.rollback_update, "update.rollback", "ROLLBACK"),
        (CommandKind.log_bundle_request, "log_bundle.request", None),
        (CommandKind.factory_reset, "factory_reset", "FACTORY-RESET"),
    ],
)
def test_configuration_verbs(kind, operation, confirmation):
    fields = build_command_fields(kind, {})
    assert fields["operation"] == operation
    assert fields["daemon"] == "configuration"
    assert fields.get("required_confirmation") == confirmation


def test_service_control_carries_json_args():
    fields = build_command_fields(
        CommandKind.service_control, {"unit": "sshd.service", "action": "restart"}
    )
    assert json.loads(fields["json_args"]) == {"action": "restart", "unit": "sshd.service"}


def test_users_command_uses_the_payload_operation():
    fields = build_command_fields(
        CommandKind.users_command,
        {"operation": "users.set_role", "username": "ops1", "role": "viewer"},
    )
    assert fields["operation"] == "users.set_role"
    assert json.loads(fields["json_args"]) == {"role": "viewer", "username": "ops1"}


def test_operation_run_targets_the_spoke():
    fields = build_command_fields(
        CommandKind.operation_run,
        {"daemon": "networkd", "operation": "status", "args": {"verbose": True}},
    )
    assert fields["daemon"] == "networkd"
    assert fields["operation"] == "status"
    assert json.loads(fields["json_args"]) == {"verbose": True}


def test_scrub_payload_removes_passwords_only():
    assert scrub_payload({"operation": "users.create", "password": "p"}) == {
        "operation": "users.create",
        "password": "[scrubbed]",
    }
    unchanged = {"unit": "sshd.service"}
    assert scrub_payload(unchanged) is unchanged
    assert scrub_payload(None) is None
