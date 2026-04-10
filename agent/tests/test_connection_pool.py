"""Tests for agent/db/connection.py — pool configuration logic without real Postgres."""

from unittest.mock import AsyncMock, patch

import pytest

import agent.db.connection as conn_mod
from agent.db.connection import _float_env, _int_env, close_pool, get_pool


@pytest.fixture(autouse=True)
def _reset_pool_globals():
    """Reset module-level pool state before and after every test."""
    conn_mod._pool = None
    conn_mod._pool_lock = None
    yield
    conn_mod._pool = None
    conn_mod._pool_lock = None


# ---------------------------------------------------------------------------
# get_pool – DATABASE_URL validation
# ---------------------------------------------------------------------------


class TestGetPoolDatabaseUrl:
    @pytest.mark.asyncio
    async def test_raises_when_database_url_not_set(self, monkeypatch):
        """get_pool must raise RuntimeError when DATABASE_URL is empty."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="DATABASE_URL environment variable is required"):
            await get_pool()

    @pytest.mark.asyncio
    async def test_raises_when_database_url_empty_string(self, monkeypatch):
        """get_pool must raise RuntimeError when DATABASE_URL is an empty string."""
        monkeypatch.setenv("DATABASE_URL", "")
        with pytest.raises(RuntimeError, match="DATABASE_URL environment variable is required"):
            await get_pool()


# ---------------------------------------------------------------------------
# _int_env / _float_env helpers
# ---------------------------------------------------------------------------


class TestIntEnv:
    def test_returns_default_when_not_set(self, monkeypatch):
        monkeypatch.delenv("TEST_INT_VAR", raising=False)
        assert _int_env("TEST_INT_VAR", 42) == 42

    def test_returns_parsed_value(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "7")
        assert _int_env("TEST_INT_VAR", 42) == 7

    def test_clamps_to_minimum(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "0")
        assert _int_env("TEST_INT_VAR", 42, minimum=1) == 1

    def test_returns_default_on_non_numeric(self, monkeypatch):
        monkeypatch.setenv("TEST_INT_VAR", "abc")
        assert _int_env("TEST_INT_VAR", 42) == 42


class TestFloatEnv:
    def test_returns_default_when_not_set(self, monkeypatch):
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        assert _float_env("TEST_FLOAT_VAR", 2.5) == 2.5

    def test_returns_parsed_value(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "3.14")
        assert _float_env("TEST_FLOAT_VAR", 2.5) == pytest.approx(3.14)

    def test_clamps_to_minimum(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "-1.0")
        assert _float_env("TEST_FLOAT_VAR", 2.5, minimum=0.0) == 0.0

    def test_returns_default_on_non_numeric(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "nope")
        assert _float_env("TEST_FLOAT_VAR", 2.5) == 2.5


# ---------------------------------------------------------------------------
# Pool size env var overrides
# ---------------------------------------------------------------------------


class TestPoolSizeOverrides:
    @pytest.mark.asyncio
    async def test_custom_pool_sizes_passed_to_create_pool(self, monkeypatch):
        """DB_POOL_MIN_SIZE and DB_POOL_MAX_SIZE should be forwarded to asyncpg.create_pool."""
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/testdb")
        monkeypatch.setenv("DB_POOL_MIN_SIZE", "5")
        monkeypatch.setenv("DB_POOL_MAX_SIZE", "20")

        sentinel_pool = AsyncMock()
        with patch(
            "agent.db.connection.asyncpg.create_pool", new_callable=AsyncMock, return_value=sentinel_pool
        ) as mock_create:
            pool = await get_pool()
            mock_create.assert_awaited_once()
            _, kwargs = mock_create.call_args
            assert kwargs["min_size"] == 5
            assert kwargs["max_size"] == 20
            assert pool is sentinel_pool

    @pytest.mark.asyncio
    async def test_max_size_at_least_min_size(self, monkeypatch):
        """If DB_POOL_MAX_SIZE < DB_POOL_MIN_SIZE, max_size should be clamped to min_size."""
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/testdb")
        monkeypatch.setenv("DB_POOL_MIN_SIZE", "10")
        monkeypatch.setenv("DB_POOL_MAX_SIZE", "3")

        sentinel_pool = AsyncMock()
        with patch(
            "agent.db.connection.asyncpg.create_pool", new_callable=AsyncMock, return_value=sentinel_pool
        ) as mock_create:
            await get_pool()
            _, kwargs = mock_create.call_args
            assert kwargs["max_size"] >= kwargs["min_size"]


# ---------------------------------------------------------------------------
# close_pool
# ---------------------------------------------------------------------------


class TestClosePool:
    @pytest.mark.asyncio
    async def test_close_pool_resets_global(self):
        """close_pool should close the pool and set the global to None."""
        fake_pool = AsyncMock()
        conn_mod._pool = fake_pool

        await close_pool()

        fake_pool.close.assert_awaited_once()
        assert conn_mod._pool is None

    @pytest.mark.asyncio
    async def test_close_pool_noop_when_none(self):
        """close_pool should be safe to call when no pool exists."""
        assert conn_mod._pool is None
        await close_pool()  # should not raise
        assert conn_mod._pool is None

    @pytest.mark.asyncio
    async def test_get_pool_after_close_recreates(self, monkeypatch):
        """After close_pool, a subsequent get_pool should create a fresh pool."""
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/testdb")

        first_pool = AsyncMock()
        second_pool = AsyncMock()

        with patch(
            "agent.db.connection.asyncpg.create_pool",
            new_callable=AsyncMock,
            side_effect=[first_pool, second_pool],
        ):
            pool1 = await get_pool()
            assert pool1 is first_pool

            await close_pool()
            assert conn_mod._pool is None

            pool2 = await get_pool()
            assert pool2 is second_pool
            assert pool2 is not pool1
