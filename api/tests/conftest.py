import os

os.environ.setdefault("ACADIAHQ_ENV", "test")  # T-P34: production is the default
import tempfile

# T-P13 (F09): the API must sign device configuration with a real Ed25519
# key even in tests — generate one per test session before the app (and its
# cached settings) load.
_KEY_DIR = tempfile.mkdtemp(prefix="acadiahq-signing-")
_KEY_PATH = os.path.join(_KEY_DIR, "config-signing.pem")
os.environ.setdefault("ACADIAHQ_CONFIGURATION_SIGNING_KEY_PATH", _KEY_PATH)

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

if not os.path.exists(_KEY_PATH):
    key = Ed25519PrivateKey.generate()
    with open(_KEY_PATH, "wb") as f:
        f.write(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.base import Base, configure_for_tests, get_engine  # noqa: E402
from app.main import create_app  # noqa: E402

TEST_DB_URL = os.environ.get(
    "ACADIAHQ_TEST_DATABASE_URL",
    "postgresql+asyncpg://acadiahq:acadiahq@localhost:55432/acadiahq_test",
)


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
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    from app.db.base import get_session_factory

    async with get_session_factory()() as session:
        yield session
