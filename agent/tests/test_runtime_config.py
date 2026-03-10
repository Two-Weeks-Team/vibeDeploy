import asyncpg
import pytest

from agent.db.store import ResultStore
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


@pytest.mark.asyncio
async def test_result_store_initializes_on_first_use():
    store = ResultStore(":memory:")

    assert store._initialized is False
    assert store._db is None

    await store.save_meeting("thread-1", {"score": 91, "verdict": "GO"})

    assert store._initialized is True
    assert await store.get_meeting("thread-1") == {"score": 91, "verdict": "GO"}

    await store.close()


@pytest.mark.asyncio
async def test_server_lifespan_defers_store_init(monkeypatch):
    import agent.server as srv

    created: dict[str, object] = {}

    class FakeStore:
        def __init__(self, *args, **kwargs):
            created["args"] = args
            created["kwargs"] = kwargs
            created["instance"] = self
            self.init_called = False
            self.close_called = False

        async def init(self):
            self.init_called = True

        async def close(self):
            self.close_called = True

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_PATH", "/tmp/vibedeploy-test.db")
    monkeypatch.setattr(srv, "ResultStore", FakeStore)

    async with srv.lifespan(srv.app):
        instance = created["instance"]
        assert created["kwargs"] == {"db_path": "/tmp/vibedeploy-test.db"}
        assert srv._store is instance
        assert instance.init_called is False

    instance = created["instance"]
    assert instance.close_called is True
    assert srv._store is None
