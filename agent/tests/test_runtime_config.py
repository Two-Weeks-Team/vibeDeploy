import asyncpg
import pytest

from agent.db import connection
from agent.run_server import _read_worker_count


@pytest.mark.asyncio
async def test_get_pool_uses_conservative_defaults(monkeypatch):
    created = {}
    pool = object()

    async def fake_create_pool(database_url: str, **kwargs):
        created["database_url"] = database_url
        created["kwargs"] = kwargs
        return pool

    monkeypatch.setenv("DATABASE_URL", "postgres://example")
    monkeypatch.setattr(connection.asyncpg, "create_pool", fake_create_pool)
    monkeypatch.setattr(connection, "_pool", None)

    result = await connection.get_pool()

    assert result is pool
    assert created["database_url"] == "postgres://example"
    assert created["kwargs"]["min_size"] == 1
    assert created["kwargs"]["max_size"] == 4
    assert created["kwargs"]["command_timeout"] == 60


@pytest.mark.asyncio
async def test_get_pool_retries_when_postgres_slots_are_exhausted(monkeypatch):
    attempts = {"count": 0}
    sleeps: list[float] = []
    pool = object()

    async def fake_create_pool(_database_url: str, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise asyncpg.TooManyConnectionsError("busy")
        return pool

    async def fake_sleep(seconds: float):
        sleeps.append(seconds)

    monkeypatch.setenv("DATABASE_URL", "postgres://example")
    monkeypatch.setattr(connection.asyncpg, "create_pool", fake_create_pool)
    monkeypatch.setattr(connection.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(connection, "_pool", None)

    result = await connection.get_pool()

    assert result is pool
    assert attempts["count"] == 3
    assert sleeps == [2.0, 4.0]


def test_read_worker_count_defaults_to_one(monkeypatch):
    monkeypatch.delenv("UVICORN_WORKERS", raising=False)
    monkeypatch.delenv("WEB_CONCURRENCY", raising=False)

    assert _read_worker_count() == 1


def test_read_worker_count_prefers_explicit_env(monkeypatch):
    monkeypatch.setenv("WEB_CONCURRENCY", "3")

    assert _read_worker_count() == 3
