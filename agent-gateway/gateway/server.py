import asyncio
import logging

import grpc

from acadiahq.agent_pb2_grpc import add_AgentLinkServicer_to_server

from app.config import get_settings
from gateway.config import get_gateway_settings
from gateway.servicer import AgentLinkServicer
from gateway.stale_sweep import run_forever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway.server")



def plaintext_refused(env: str, settings) -> str | None:
    """Why a plaintext AgentLink listener is refused, or None when allowed
    (T-P34, HQ-030): device credentials and commands must not cross the
    network in cleartext in production."""
    if settings.tls_cert_path and settings.tls_key_path:
        return None
    if env in ("dev", "test"):
        return None
    if settings.allow_insecure_behind_tls_terminator:
        return None
    return (
        "agent-gateway: refusing to serve PLAINTEXT gRPC with ACADIAHQ_ENV="
        f"{env!r}. Set ACADIAHQ_GATEWAY_TLS_CERT_PATH/TLS_KEY_PATH, or — only if TLS "
        "is terminated in front of the gateway — "
        "ACADIAHQ_GATEWAY_ALLOW_INSECURE_BEHIND_TLS_TERMINATOR=true."
    )

async def serve() -> None:
    settings = get_gateway_settings()
    server = grpc.aio.server()
    add_AgentLinkServicer_to_server(AgentLinkServicer(), server)

    # T-P12 (F10): TLS on the AgentLink listener. Devices dial https:// with
    # the pinned HQ CA; optional mTLS additionally pins device certificates.
    if settings.tls_cert_path and settings.tls_key_path:
        with open(settings.tls_cert_path, "rb") as f:
            cert = f.read()
        with open(settings.tls_key_path, "rb") as f:
            key = f.read()
        if settings.tls_client_ca_path:
            with open(settings.tls_client_ca_path, "rb") as f:
                client_ca = f.read()
            server.add_secure_port(
                f"[::]:{settings.grpc_port}",
                grpc.ssl_server_credentials(
                    [(cert, key)],
                    root_certificates=client_ca,
                    require_client_auth=True,
                ),
            )
            logger.info(
                "agent-gateway listening on TLS :%d (mTLS: client certificates required)",
                settings.grpc_port,
            )
        else:
            server.add_secure_port(
                f"[::]:{settings.grpc_port}",
                grpc.ssl_server_credentials([(cert, key)]),
            )
            logger.info("agent-gateway listening on TLS :%d", settings.grpc_port)
    else:
        # T-P34 (HQ-030): fail closed in production.
        refuse = plaintext_refused(get_settings().env, settings)
        if refuse:
            raise SystemExit(refuse)
        # Insecure for local dev only. Production must set
        # ACADIAHQ_GATEWAY_TLS_CERT_PATH/TLS_KEY_PATH (or terminate TLS at a
        # reverse proxy) -- the proto's own security notes (ARCHITECTURE.md §3)
        # assume devices dial in over TLS.
        logger.warning(
            "agent-gateway listening PLAINTEXT on :%d — set tls_cert_path/"
            "tls_key_path for production (T-P12/F10)",
            settings.grpc_port,
        )
        server.add_insecure_port(f"[::]:{settings.grpc_port}")

    stop_event = asyncio.Event()
    sweep_task = asyncio.ensure_future(run_forever(stop_event))

    await server.start()
    try:
        await server.wait_for_termination()
    finally:
        stop_event.set()
        sweep_task.cancel()


if __name__ == "__main__":
    asyncio.run(serve())
