from fastapi import APIRouter, Depends

from app.auth.deps import require_role
from app.models.enums import UserRole
from app.services.operation_catalog import OPERATIONS
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("")
async def list_operations(
    _ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    """Return the HQ operation catalog used by the durable command gateway."""
    return {"items": list(OPERATIONS)}
