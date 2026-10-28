import base64
import functools
import json
from typing import Any
from uuid import UUID

from app.config import get_settings


# The device configuration contract version webconfigd validates
# (webconfig_engine::CONFIG_SCHEMA_VERSION in Acadia-Configuration). The
# envelope field is `schema_version`, not `config_version` (task 009, H5).
CONFIGURATION_SCHEMA_VERSION = 1

# T-P13 (F09): the signature algorithm is Ed25519, verified MANDATORILY by
# the device against the provisioned HQ verification key
# (/etc/acadia/hq-config-pub.pem or WEBCONFIG_HQ_CONFIG_PUBKEY). The signed
# bytes are the canonical transport payload itself (the envelope minus the
# signature fields), so the device can verify exactly what it received.
SIGNATURE_ALGORITHM = "ed25519"


def signing_key_id() -> str:
    key_id = get_settings().configuration_signing_key_id
    if not key_id or len(key_id) > 128 or not key_id.replace("-", "").replace("_", "").isalnum():
        raise RuntimeError("configuration_signing_key_id must be 1..128 URL-safe characters")
    return key_id


def canonical_document(
    *, device_id: UUID, command_id: str, operation: str, values: dict[str, Any] | None = None
) -> bytes:
    """Kept for audit records (the logical document); NOT the signed bytes —
    the device verifies the transport payload (see sign_payload)."""
    envelope = {
        "command_id": command_id,
        "device_id": str(device_id),
        "operation": operation,
        "values": values or {},
        "version": 1,
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def canonical_payload(payload: dict[str, Any]) -> bytes:
    """Return the versioned configuration-signature field set.

    Only contract fields are signed: ``schema_version``, ``origin``,
    ``config``, and ``signing_key_id`` when present.  Transport metadata is
    deliberately excluded.  This exact subset is mirrored by webconfigd.
    """
    fields = ("schema_version", "origin", "config", "signing_key_id")
    doc = {field: payload[field] for field in fields if field in payload}
    return json.dumps(
        doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


@functools.lru_cache(maxsize=4)
def _load_signing_key(path: str):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    with open(path, "rb") as f:
        return load_pem_private_key(f.read(), password=None)


def signing_public_key_pem() -> str:
    """The Ed25519 public key to provision onto devices
    (/etc/acadia/hq-config-pub.pem), for the deployment runbook."""
    path = get_settings().configuration_signing_key_path
    if not path:
        raise RuntimeError("configuration_signing_key_path is not configured")
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    return _load_signing_key(path).public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    ).decode()


def sign_payload(payload: dict[str, Any]) -> str:
    """Sign the canonical transport payload with the HQ Ed25519 key."""
    path = get_settings().configuration_signing_key_path
    if not path:
        raise RuntimeError(
            "configuration_signing_key_path is not configured — HQ cannot sign "
            "device configuration (T-P13/F09)"
        )
    key = _load_signing_key(path)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    if not isinstance(key, Ed25519PrivateKey):
        raise RuntimeError("configuration_signing_key_path is not an Ed25519 key")
    sig = key.sign(canonical_payload(payload))
    return base64.b64encode(sig).decode()
