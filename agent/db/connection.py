import asyncio
import os

import asyncpg

_pool: asyncpg.Pool | None = None
_DEFAULT_POOL_MIN_SIZE = 1
_DEFAULT_POOL_MAX_SIZE = 1
_DEFAULT_POOL_RETRIES = 5
_DEFAULT_POOL_RETRY_DELAY = 2.0


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _float_env(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return max(minimum, float(raw))
    except ValueError:
        return default


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        database_url = os.environ.get("DATABASE_URL", "")
        if not database_url:
            raise RuntimeError("DATABASE_URL environment variable is required")
        min_size = _int_env("DB_POOL_MIN_SIZE", _DEFAULT_POOL_MIN_SIZE)
        max_size = max(min_size, _int_env("DB_POOL_MAX_SIZE", _DEFAULT_POOL_MAX_SIZE))
        retries = _int_env("DB_POOL_CONNECT_RETRIES", _DEFAULT_POOL_RETRIES)
        retry_delay = _float_env("DB_POOL_CONNECT_RETRY_DELAY", _DEFAULT_POOL_RETRY_DELAY, minimum=0.25)

        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                _pool = await asyncpg.create_pool(
                    database_url,
                    min_size=min_size,
                    max_size=max_size,
                    command_timeout=60,
                )
                break
            except asyncpg.TooManyConnectionsError as exc:
                last_error = exc
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (attempt + 1))
        if _pool is None and last_error is not None:
            raise last_error
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
