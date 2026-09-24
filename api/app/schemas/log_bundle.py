from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Page


class LogBundleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    size_bytes: int
    uploaded_at: datetime
    time_range_start: datetime
    time_range_end: datetime
    upload_state: str
    sha256: str | None = None
    upload_error: str | None = None
    completed_at: datetime | None = None


class LogBundleListOut(BaseModel):
    items: list[LogBundleOut]
    page: Page


class DownloadUrlOut(BaseModel):
    download_url: str
