import os
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ACADIAHQ_", env_file=".env", extra="ignore")

    env: str = "dev"

    database_url: str = "postgresql+asyncpg://acadiahq:acadiahq@localhost:5432/acadiahq"

    # OIDC (human auth). Dev default points at the self-hosted Keycloak
    # brought up by infra/docker-compose.yml -- see IMPLEMENTATION_PLAN §1.2:
    # "if no IdP is chosen yet, use a self-hosted option... so Phase 1 isn't
    # blocked on an external vendor decision."
    oidc_issuer: str = "http://localhost:8081/realms/acadiahq"
    oidc_client_id: str = "acadiahq-api"
    oidc_client_secret: str = "dev-secret-change-me"
    # No static oidc_redirect_uri: it's derived per-request from the
    # browser's actual origin (X-Forwarded-Host, forwarded by Vite's dev
    # proxy) in app/routers/auth.py -- a fixed value breaks the moment the
    # app is reachable at more than one hostname (localhost, LAN IP, mDNS
    # name), which is exactly what the LAN-access setup needs.
    oidc_redirect_fallback_host: str = "localhost:5173"

    # Session JWT issued by the API after OIDC login, stored in an httpOnly cookie.
    session_secret_key: str = "dev-only-change-me-in-every-real-deployment"
    session_algorithm: str = "HS256"
    session_ttl_seconds: int = 60 * 60 * 8
    # T-P13 (F09): Ed25519 private key (PEM) used to sign the device
    # configuration transport payload; the device verifies MANDATORILY against
    # the matching public key provisioned at /etc/acadia/hq-config-pub.pem.
    # Generate with scripts/generate-config-signing-key.py.
    configuration_signing_key_path: str = ""

    # Object storage (S3-compatible; MinIO in local dev).
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "acadiahq"
    s3_secret_key: str = "acadiahq-dev-secret"
    s3_bucket: str = "acadiahq"
    s3_region: str = "us-east-1"

    # Redis (arq background jobs).
    redis_url: str = "redis://localhost:6379/0"

    # Presence / heartbeat.
    heartbeat_interval_s: int = 30
    heartbeat_missed_threshold: int = 2  # offline after N missed intervals

    # Pairing tokens.
    pairing_token_ttl_seconds: int = 15 * 60
    command_ttl_seconds: int = 60 * 60
    command_lease_seconds: int = 30
    command_max_attempts: int = 3

    cors_allow_origins: list[str] = ["http://localhost:5173"]

    @model_validator(mode="after")
    def _fail_closed_in_production(self):
        """Refuse to start in production unless explicit, non-dev secrets and
        endpoints are supplied. Dev defaults are allowed only in dev/test."""
        if self.env != "production":
            return self

        localhost_refs = ["localhost", "127.0.0.1", "0.0.0.0"]
        problems: list[str] = []

        if any(h in self.database_url for h in localhost_refs):
            problems.append("database_url points at localhost")
        if any(h in self.redis_url for h in localhost_refs):
            problems.append("redis_url points at localhost")
        if self.oidc_issuer.startswith("http://localhost"):
            problems.append("oidc_issuer points at localhost")
        if self.oidc_client_secret in ("dev-secret-change-me", ""):
            problems.append("oidc_client_secret is unset/placeholder")
        if self.session_secret_key in ("dev-only-change-me-in-every-real-deployment", ""):
            problems.append("session_secret_key is unset/placeholder")
        if self.s3_secret_key == "acadiahq-dev-secret":
            problems.append("s3_secret_key is the dev default")
        if len(self.session_secret_key) < 32:
            problems.append("session_secret_key too short (<32 chars)")
        if not self.configuration_signing_key_path:
            problems.append("configuration_signing_key_path is unset (Ed25519 signing key required, F09)")
        elif not os.path.exists(self.configuration_signing_key_path):
            problems.append("configuration_signing_key_path does not exist")

        if problems:
            raise ValueError(
                "ACADIAHQ_ENV=production but config is not fail-closed; "
                "refusing to start. Resolve: " + "; ".join(problems)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
