from app.models.enums import UserRole
from tests.factories import login_as, make_tenant, make_user


async def test_operation_discovery_returns_canonical_device_operations(client, db_session):
    tenant = await make_tenant(db_session)
    viewer = await make_user(db_session, tenant, UserRole.viewer)
    await db_session.commit()
    await login_as(client, viewer)

    response = await client.get("/operations")

    assert response.status_code == 200
    operations = response.json()["items"]
    names = {item["name"] for item in operations}
    # T-P25: the catalog is the vendored Acadia-Configuration contract (+ the
    # HQ-only generic operation.run), not a hand list.
    assert {"backup", "configuration.write", "ssh_keys.set", "system.reboot",
            "users.create", "update.rollback", "operation.run"} <= names
    spokes = response.json()["spoke_operations"]
    assert {(s["daemon"], s["name"]) for s in spokes} >= {("networkd", "status")}
    assert all(s["min_role"] in ("operator", "admin") for s in spokes)
    for operation in operations:
        assert operation["daemon"] == "configuration"
        assert operation["command_kind"]
        assert operation["description"]


def test_spoke_allowlist_only_names_real_instrumentation_verbs():
    """Every SPOKE_OPERATIONS entry exists in the generated Instrumentation
    catalog — a renamed spoke verb breaks this test, not production."""
    from app.services.operation_catalog import SPOKE_OPERATIONS, spoke_catalog

    real = {(d, op["name"]) for d, ops in spoke_catalog().items() for op in ops}
    assert set(SPOKE_OPERATIONS) <= real, set(SPOKE_OPERATIONS) - real


def test_every_catalog_command_kind_is_deliverable():
    """Every configuration verb maps to a CommandKind the gateway can build."""
    import sys
    from pathlib import Path

    from app.models.enums import CommandKind
    from app.services.operation_catalog import OPERATIONS

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent-gateway"))
    from gateway.command_map import OPERATIONS as GATEWAY_MAP

    for op in OPERATIONS:
        kind = CommandKind(op["command_kind"])
        assert kind in GATEWAY_MAP, op["name"]
