"""HQ-005 — Alembic migrations ↔ SQLAlchemy models parity.

A schema drift between the migrations and the ORM models is invisible until a
production deploy fails. This test applies the real migrations to a fresh
database, then asserts an `alembic.autogenerate` diff is EMPTY — i.e. the
models and the migrations describe exactly the same schema.

Requires ACADIAHQ_TEST_DATABASE_URL (CI provides a Postgres service; locally
spin one up on 55432).
"""

import os
import subprocess

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
from app.models import *  # noqa: F401,F403 — registers all models on Base.metadata

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.skipif(
    not os.environ.get("ACADIAHQ_TEST_DATABASE_URL"),
    reason="ACADIAHQ_TEST_DATABASE_URL not set",
)
def test_migrations_match_models():
    url = os.environ["ACADIAHQ_TEST_DATABASE_URL"]

    # Reset the schema: the shared conftest seeds the DB with
    # Base.metadata.create_all, but this test must start from an EMPTY
    # database so the migrations alone define the schema.
    import asyncio as _asyncio
    from sqlalchemy import text as _text

    async def _reset() -> None:
        engine = create_async_engine(url)
        try:
            async with engine.begin() as conn:
                # Two separate statements: asyncpg's prepared statements
                # reject multi-command SQL, so this cannot be one string.
                await conn.execute(_text("DROP SCHEMA public CASCADE"))
                await conn.execute(_text("CREATE SCHEMA public"))
        finally:
            await engine.dispose()

    _asyncio.run(_reset())

    # Apply the real migrations through the project's alembic env (async path).
    venv_bin = os.path.join(REPO_ROOT, ".venv", "bin")
    alembic = os.path.join(venv_bin, "alembic") if os.path.exists(
        os.path.join(venv_bin, "alembic")) else "alembic"
    # Point alembic's env (which reads ACADIAHQ_DATABASE_URL) at the test DB
    # so the migrations apply to the database we just reset, not the dev one.
    env = dict(os.environ, ACADIAHQ_DATABASE_URL=url)
    result = subprocess.run(
        [alembic, "-c", os.path.join(REPO_ROOT, "alembic.ini"), "upgrade", "head"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        pytest.fail(
            f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}"
        )

    # Compare the applied schema against the ORM metadata (asyncpg engine).
    async def _diff() -> list:
        engine = create_async_engine(url)
        try:
            async with engine.connect() as conn:
                def _compare(sync_conn):
                    ctx = MigrationContext.configure(sync_conn)
                    return list(compare_metadata(ctx, Base.metadata))

                return await conn.run_sync(_compare)
        finally:
            await engine.dispose()

    import asyncio

    diff = asyncio.run(_diff())

    assert diff == [], (
        "ORM models drifted from the Alembic migrations — fix by regenerating a "
        "migration or updating the models. Diff:\n"
        + "\n".join(f"  {item}" for item in diff)
    )