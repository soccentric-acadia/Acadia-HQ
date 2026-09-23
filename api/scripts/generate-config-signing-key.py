#!/usr/bin/env python3
"""Generate the HQ Ed25519 configuration-signing keypair (T-P13, F09).

Writes the private key PEM to the path given as argv[1] (the value for
ACADIAHQ_CONFIGURATION_SIGNING_KEY_PATH) and prints the public key PEM to
provision onto devices at /etc/acadia/hq-config-pub.pem.
"""
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: generate-config-signing-key.py <private-key-out.pem>", file=sys.stderr)
        return 2
    out = sys.argv[1]
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(out, "wb") as f:
        f.write(pem)
    import os

    os.chmod(out, 0o600)
    sys.stdout.write(pub.decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
