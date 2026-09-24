from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ACADIAHQ_GATEWAY_", extra="ignore")

    grpc_port: int = 50051
    # Stale-connection sweep cadence -- independent of the heartbeat interval
    # itself (app.config.Settings.heartbeat_interval_s), which devices use to
    # decide how often to send heartbeats.
    sweep_interval_s: int = 10
    # Device heartbeat cadence advertised in HeartbeatAck (task 009, H8: this
    # used to advertise the stale-sweep interval, a semantically different
    # knob that devices obediently re-armed their heartbeat to).
    device_heartbeat_interval_s: int = 30
    # Per-command device execution deadline advertised on dispatched commands
    # (task 009, H9). Must be <= command lease so a device still working is
    # not redelivered mid-run.
    command_deadline_ms: int = 60_000
    # T-P12 (F10): AgentLink TLS. When cert+key are configured the gateway
    # serves gRPC over TLS on grpc_port; the device (hq-agent) dials
    # https://<host>:<port> with the HQ CA pinned at
    # /etc/acadia/hq-ca.pem (provisioned with the HQ endpoint, P-A10).
    # Without TLS settings the gateway stays plaintext for local dev and
    # logs a loud warning — production deployments must set both.
    tls_cert_path: str | None = None
    tls_key_path: str | None = None
    # Optional mTLS (T-P12): when set, devices must present a client
    # certificate signed by this CA on every connection.
    tls_client_ca_path: str | None = None
    # T-P34 (HQ-030): production refuses a plaintext listener unless TLS is
    # terminated in front of the gateway and the operator says so explicitly.
    allow_insecure_behind_tls_terminator: bool = False


@lru_cache
def get_gateway_settings() -> GatewaySettings:
    return GatewaySettings()
