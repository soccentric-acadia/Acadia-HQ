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


@lru_cache
def get_gateway_settings() -> GatewaySettings:
    return GatewaySettings()
