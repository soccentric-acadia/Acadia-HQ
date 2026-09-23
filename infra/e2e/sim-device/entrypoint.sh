#!/bin/bash
# T-P16 sim-device entrypoint: run the real webconfigd binary as the image's
# non-root `webconfig` user with a sandbox APPROXIMATION (see README.md for
# the honest scope table vs. the systemd unit).
#
# Boot sequence mirrors a device:
#   1. first-boot admin claim — no factory claim code in the sim → the
#      open-with-audit path (T-P10) applies; the admin is created with the
#      E2E password.
#   2. pairing — the harness POSTs the HQ pairing token to
#      /api/v1/pairing/provision (hq_endpoint = ACADIAHQ_GATEWAY_ADDR,
#      explicit scheme http:// for the plaintext dev gateway; production
#      dials https:// per T-P12).
#   3. webconfigd's AgentLink client (hq-agent) dials the gateway, redeems
#      the token, receives the credential, and starts heartbeating.
set -euo pipefail

API_URL="${ACADIAHQ_API_URL:-http://api:8000}"
GW="${ACADIAHQ_GATEWAY_ADDR:-gateway:50051}"
ADMIN_PASS="${E2E_ADMIN_PASSWORD:-e2e-password-1}"

mkdir -p /data/webconfig

# First boot: create the admin (no claim code provisioned in the sim —
# the daemon audits the open first-boot loudly).
python3 - <<EOF
import json, urllib.request

def call(method, path, body=None):
    req = urllib.request.Request(f"${API_URL}/api/v1{path}", method=method)
    req.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode() if body else None
    return urllib.request.urlopen(req, data=data)

try:
    call("POST", "/auth/first-boot", {"username": "admin", "password": "${ADMIN_PASS}"})
    print("sim-device: admin created")
except Exception as e:
    print(f"sim-device: first-boot skipped ({e})")
EOF

# Run as the webconfig user (uid fixed by the Dockerfile).
exec setpriv --reuid webconfig --regid webconfig --init-groups \
    env WEBCONFIG_DATA_DIR=/data \
        WEBCONFIG_STATIC_DIR=/usr/share/webconfig/static \
        WEBCONFIG_PLAIN_PORT=8080 \
        WEBCONFIG_PORT=8443 \
    /usr/bin/webconfigd