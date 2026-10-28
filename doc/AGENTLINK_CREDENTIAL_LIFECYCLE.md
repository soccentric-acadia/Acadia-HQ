# AgentLink credential lifecycle

AgentLink device credentials are opaque, randomly generated bearer tokens.
HQ stores only their SHA-256 hashes in `device_credentials`; the target stores
the active token, its HQ-issued expiry, device ID, and endpoint in
`/pst/acadia/webconfig/pairing.json` (mode `0600`, parent directory `0700`).
The record is atomically replaced and is removed by factory reset.

## Expiry and renewal

`PairingResult.credential_expires_at_unix_ms` authenticates the initial
credential lifetime.  During an authenticated heartbeat, HQ renews a
credential in the configured seven-day renewal window (default credential
TTL: 30 days).  HQ returns the replacement and authoritative expiry in
`HeartbeatAck`; the device atomically stores them before subsequent
heartbeats.  The old hash is revoked in the same HQ transaction that creates
the replacement.

No renewal is attempted while offline.  The device may use its locally stored
credential for at most five minutes past its recorded expiry to tolerate a
fast local clock, but HQ is authoritative and rejects an expired credential
on every authentication check.  A target without an expiry is accepted only
for legacy compatibility until its next authenticated renewal.

## Revocation

Disabling, revoking, or rotating a device revokes every active credential in
HQ immediately.  The next heartbeat or reconnect is rejected, and the target
marks itself revoked rather than retrying the credential.  Recovery requires
an operator-issued, single-use pairing token and a new enrollment.

Fields added to AgentLink are backward compatible: legacy clients ignore
unknown expiry/renewal fields, while current clients preserve an existing
expiry when a legacy server sends zero.
