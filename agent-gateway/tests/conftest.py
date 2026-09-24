import os

os.environ.setdefault("ACADIAHQ_ENV", "test")  # T-P34: production is the default

import grpc
import pytest_asyncio

from app.db.base import Base, configure_for_tests, get_engine, get_session_factory
from app.db.test_database import resolve_test_database_url
from acadiahq.agent_pb2_grpc import AgentLinkStub, add_AgentLinkServicer_to_server
from gateway.servicer import AgentLinkServicer

# HQ-018: the configured database when reachable, else an ephemeral
# container (app/db/test_database.py). Exported so every consumer in the
# session (alembic parity test included) sees the same URL.
TEST_DB_URL = resolve_test_database_url(
    "postgresql+asyncpg://acadiahq:acadiahq@localhost:5432/acadiahq_test"
)
os.environ["ACADIAHQ_TEST_DATABASE_URL"] = TEST_DB_URL


@pytest_asyncio.fixture(autouse=True)
async def _db():
    configure_for_tests(TEST_DB_URL)
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    async with get_session_factory()() as session:
        yield session


@pytest_asyncio.fixture
async def gateway_stub():
    server = grpc.aio.server()
    add_AgentLinkServicer_to_server(AgentLinkServicer(), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    try:
        yield AgentLinkStub(channel)
    finally:
        await channel.close()
        await server.stop(None)
