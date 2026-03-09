import json
import os
from typing import Optional

import aiosqlite

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS meeting_results (
    thread_id TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS brainstorm_results (
    thread_id TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS meeting_results (
    thread_id TEXT PRIMARY KEY,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS brainstorm_results (
    thread_id TEXT PRIMARY KEY,
    result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


class ResultStore:
    """Dual-backend store: PostgreSQL (production) or SQLite (tests).

    - No args or db_url=<postgres url> → PostgreSQL via asyncpg
    - db_path=":memory:" → SQLite in-memory (for tests)
    """

    def __init__(self, db_path: str | None = None, db_url: str | None = None):
        self._use_pg = False
        self._db_path = db_path
        self._db_url = db_url
        self._db: Optional[aiosqlite.Connection] = None
        self._pool = None

        if db_path == ":memory:":
            self._use_pg = False
        elif db_url or os.environ.get("DATABASE_URL"):
            self._use_pg = True
            self._db_url = db_url or os.environ.get("DATABASE_URL", "")
        elif db_path:
            self._use_pg = False
        else:
            db_env = os.environ.get("DATABASE_URL", "")
            if db_env:
                self._use_pg = True
                self._db_url = db_env
            else:
                self._use_pg = False
                self._db_path = "vibedeploy.db"

    async def init(self):
        if self._use_pg:
            from .connection import get_pool

            self._pool = await get_pool()
            async with self._pool.acquire() as conn:
                for stmt in _PG_SCHEMA.strip().split(";"):
                    stmt = stmt.strip()
                    if stmt:
                        await conn.execute(stmt)
        else:
            self._db = await aiosqlite.connect(self._db_path or ":memory:")
            await self._db.executescript(_SQLITE_SCHEMA)
            if self._db_path and self._db_path != ":memory:":
                await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.commit()

    async def close(self):
        if self._use_pg:
            from .connection import close_pool

            await close_pool()
            self._pool = None
        else:
            if self._db:
                await self._db.close()
                self._db = None

    async def save_meeting(self, thread_id: str, result: dict):
        if self._use_pg:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO meeting_results (thread_id, result)
                       VALUES ($1, $2::jsonb)
                       ON CONFLICT (thread_id)
                       DO UPDATE SET result = $2::jsonb, created_at = NOW()""",
                    thread_id,
                    json.dumps(result, ensure_ascii=False),
                )
        else:
            await self._db.execute(
                "INSERT OR REPLACE INTO meeting_results (thread_id, result) VALUES (?, ?)",
                (thread_id, json.dumps(result, ensure_ascii=False)),
            )
            await self._db.commit()

    async def get_meeting(self, thread_id: str) -> Optional[dict]:
        if self._use_pg:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT result FROM meeting_results WHERE thread_id = $1",
                    thread_id,
                )
                if row is None:
                    return None
                r = row["result"]
                return json.loads(r) if isinstance(r, str) else r
        else:
            cursor = await self._db.execute(
                "SELECT result FROM meeting_results WHERE thread_id = ?",
                (thread_id,),
            )
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else None

    async def save_brainstorm(self, thread_id: str, result: dict):
        if self._use_pg:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO brainstorm_results (thread_id, result)
                       VALUES ($1, $2::jsonb)
                       ON CONFLICT (thread_id)
                       DO UPDATE SET result = $2::jsonb, created_at = NOW()""",
                    thread_id,
                    json.dumps(result, ensure_ascii=False),
                )
        else:
            await self._db.execute(
                "INSERT OR REPLACE INTO brainstorm_results (thread_id, result) VALUES (?, ?)",
                (thread_id, json.dumps(result, ensure_ascii=False)),
            )
            await self._db.commit()

    async def get_brainstorm(self, thread_id: str) -> Optional[dict]:
        if self._use_pg:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT result FROM brainstorm_results WHERE thread_id = $1",
                    thread_id,
                )
                if row is None:
                    return None
                r = row["result"]
                return json.loads(r) if isinstance(r, str) else r
        else:
            cursor = await self._db.execute(
                "SELECT result FROM brainstorm_results WHERE thread_id = ?",
                (thread_id,),
            )
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else None

    async def list_meetings(self, limit: int = 50) -> list[dict]:
        if self._use_pg:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT thread_id, result, created_at FROM meeting_results ORDER BY created_at DESC LIMIT $1",
                    limit,
                )
                results = []
                for r in rows:
                    res = json.loads(r["result"]) if isinstance(r["result"], str) else r["result"]
                    results.append(
                        {
                            "thread_id": r["thread_id"],
                            **res,
                            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                        }
                    )
                return results
        else:
            cursor = await self._db.execute(
                "SELECT thread_id, result, created_at FROM meeting_results ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [{"thread_id": r[0], **json.loads(r[1]), "created_at": r[2]} for r in rows]

    async def list_brainstorms(self, limit: int = 50) -> list[dict]:
        if self._use_pg:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT thread_id, result, created_at FROM brainstorm_results ORDER BY created_at DESC LIMIT $1",
                    limit,
                )
                results = []
                for r in rows:
                    res = json.loads(r["result"]) if isinstance(r["result"], str) else r["result"]
                    results.append(
                        {
                            "thread_id": r["thread_id"],
                            **res,
                            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                        }
                    )
                return results
        else:
            cursor = await self._db.execute(
                "SELECT thread_id, result, created_at FROM brainstorm_results ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = await cursor.fetchall()
            return [{"thread_id": r[0], **json.loads(r[1]), "created_at": r[2]} for r in rows]

    async def get_stats(self) -> dict:
        if self._use_pg:
            async with self._pool.acquire() as conn:
                m_count = await conn.fetchval("SELECT COUNT(*) FROM meeting_results")
                b_count = await conn.fetchval("SELECT COUNT(*) FROM brainstorm_results")
                avg_score_raw = await conn.fetchval("SELECT AVG((result->>'score')::float) FROM meeting_results")
                avg_score = round(avg_score_raw, 1) if avg_score_raw else 0
                go_count = await conn.fetchval("SELECT COUNT(*) FROM meeting_results WHERE result->>'verdict' = 'GO'")
                return {
                    "total_meetings": m_count,
                    "total_brainstorms": b_count,
                    "avg_score": avg_score,
                    "go_count": go_count,
                    "nogo_count": m_count - go_count,
                }
        else:
            m_cursor = await self._db.execute("SELECT COUNT(*) FROM meeting_results")
            m_count = (await m_cursor.fetchone())[0]

            b_cursor = await self._db.execute("SELECT COUNT(*) FROM brainstorm_results")
            b_count = (await b_cursor.fetchone())[0]

            avg_cursor = await self._db.execute("SELECT AVG(json_extract(result, '$.score')) FROM meeting_results")
            avg_row = await avg_cursor.fetchone()
            avg_score = round(avg_row[0], 1) if avg_row[0] else 0

            go_cursor = await self._db.execute(
                "SELECT COUNT(*) FROM meeting_results WHERE json_extract(result, '$.verdict') = 'GO'"
            )
            go_count = (await go_cursor.fetchone())[0]

            return {
                "total_meetings": m_count,
                "total_brainstorms": b_count,
                "avg_score": avg_score,
                "go_count": go_count,
                "nogo_count": m_count - go_count,
            }
