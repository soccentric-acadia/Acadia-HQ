import hashlib
import hmac
import json
from typing import Any
from uuid import UUID

from app.config import get_settings


def canonical_document(
    *, device_id: UUID, command_id: str, operation: str, values: dict[str, Any] | None = None
) -> bytes:
    envelope = {
        "command_id": command_id,
        "device_id": str(device_id),
        "operation": operation,
        "values": values or {},
        "version": 1,
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sign_document(document: bytes) -> str:
    key = get_settings().configuration_signing_key.encode()
    return hmac.new(key, document, hashlib.sha256).hexdigest()
