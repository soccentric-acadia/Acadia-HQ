"""HQ-018: a Postgres for the API and gateway test suites, wherever they run.

The suites need a real Postgres (JSONB, enums, advisory locks — SQLite is not
a stand-in). ``resolve_test_database_url`` returns the configured
``ACADIAHQ_TEST_DATABASE_URL`` when something is listening there (the dev
compose database locally, the ``postgres`` service in CI). Otherwise — or
when ``ACADIAHQ_TEST_EPHEMERAL_PG=1`` — it starts a throwaway container from
the same pinned image the compose stack uses, on a random loopback port,
and removes it when the test process exits. Only the standard library and
the ``docker`` CLI are needed.
"""

from __future__ import annotations

import atexit
import os
import shutil
import socket
import subprocess
import time
from urllib.parse import urlsplit

# Same digest as infra/docker-compose.yml's postgres service.
PG_IMAGE = (
    "postgres:16-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777"
)
_USER = "acadiahq"
_PASSWORD = "acadiahq"
_DB = "acadiahq_test"

_started_url: str | None = None


def _reachable(url: str, timeout: float = 1.0) -> bool:
    parts = urlsplit(url.replace("+asyncpg", ""))
    try:
        with socket.create_connection((parts.hostname or "localhost", parts.port or 5432), timeout):
            return True
    except OSError:
        return False


def _start_container() -> str:
    if shutil.which("docker") is None:
        raise RuntimeError(
            "HQ tests need Postgres: nothing listens at ACADIAHQ_TEST_DATABASE_URL and the "
            "docker CLI is not available to start an ephemeral one (HQ-018)."
        )
    container = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "-e",
            f"POSTGRES_USER={_USER}",
            "-e",
            f"POSTGRES_PASSWORD={_PASSWORD}",
            "-e",
            f"POSTGRES_DB={_DB}",
            "-p",
            "127.0.0.1::5432",
            "--tmpfs",
            "/var/lib/postgresql/data",
            PG_IMAGE,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    atexit.register(
        subprocess.run, ["docker", "rm", "-f", container], capture_output=True, check=False
    )
    mapped = subprocess.run(
        ["docker", "port", container, "5432/tcp"], check=True, capture_output=True, text=True
    ).stdout.split()[0]
    port = int(mapped.rsplit(":", 1)[1])
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        ready = subprocess.run(
            ["docker", "exec", container, "pg_isready", "-h", "127.0.0.1", "-U", _USER, "-d", _DB],
            capture_output=True,
            check=False,
        )
        if ready.returncode == 0:
            return f"postgresql+asyncpg://{_USER}:{_PASSWORD}@127.0.0.1:{port}/{_DB}"
        time.sleep(0.5)
    raise RuntimeError(f"ephemeral Postgres container {container[:12]} never became ready")


def resolve_test_database_url(default: str) -> str:
    """The database URL the test session should use (see module docstring)."""
    global _started_url
    if _started_url:
        return _started_url
    configured = os.environ.get("ACADIAHQ_TEST_DATABASE_URL", default)
    force = os.environ.get("ACADIAHQ_TEST_EPHEMERAL_PG") == "1"
    if not force and _reachable(configured):
        return configured
    _started_url = _start_container()
    return _started_url
