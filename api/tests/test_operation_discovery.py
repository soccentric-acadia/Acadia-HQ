from app.models.enums import UserRole
from tests.factories import login_as, make_tenant, make_user


async def test_operation_discovery_returns_canonical_device_operations(client, db_session):
    tenant = await make_tenant(db_session)
    viewer = await make_user(db_session, tenant, UserRole.viewer)
    login_as(client, viewer)

    response = await client.get("/operations")

    assert response.status_code == 200
    operations = response.json()["items"]
    assert {item["name"] for item in operations} == {
        "backup",
        "restore",
        "factory_reset",
        "apply_update",
        "configuration.read",
        "configuration.write",
        # T-P11 (B05): SSH key provisioning for the operator account.
        "ssh_keys.set",
    }
    for operation in operations:
        assert operation["daemon"] == "configuration"
        assert operation["command_kind"]
        assert operation["description"]
