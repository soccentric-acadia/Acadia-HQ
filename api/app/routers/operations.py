from fastapi import APIRouter, Depends

from app.auth.deps import require_role
from app.models.enums import UserRole
from app.services.operation_catalog import OPERATIONS, SPOKE_OPERATIONS, spoke_catalog
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("")
async def list_operations(
    _ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    """Return the HQ operation catalog used by the durable command gateway:
    the device-local configuration verbs plus the Instrumentation spoke verbs
    HQ allows through ``operation.run`` (with their minimum role)."""
    spokes = [
        {**op, "daemon": daemon, "min_role": SPOKE_OPERATIONS[(daemon, op["name"])]}
        for daemon, ops in spoke_catalog().items()
        for op in ops
        if (daemon, op["name"]) in SPOKE_OPERATIONS
    ]
    return {"items": list(OPERATIONS), "spoke_operations": spokes}
