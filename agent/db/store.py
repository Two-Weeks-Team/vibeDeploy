import json
from typing import Optional

import aiosqlite

_SCHEMA = """
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


class ResultStore:
    def __init__(self, db_path: str = "vibedeploy.db"):
        self._db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def init(self):
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.executescript(_SCHEMA)
        if self._db_path != ":memory:":
            await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def save_meeting(self, thread_id: str, result: dict):
        await self._db.execute(
            "INSERT OR REPLACE INTO meeting_results (thread_id, result) VALUES (?, ?)",
            (thread_id, json.dumps(result, ensure_ascii=False)),
        )
        await self._db.commit()

    async def get_meeting(self, thread_id: str) -> Optional[dict]:
        cursor = await self._db.execute(
            "SELECT result FROM meeting_results WHERE thread_id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else None

    async def save_brainstorm(self, thread_id: str, result: dict):
        await self._db.execute(
            "INSERT OR REPLACE INTO brainstorm_results (thread_id, result) VALUES (?, ?)",
            (thread_id, json.dumps(result, ensure_ascii=False)),
        )
        await self._db.commit()

    async def get_brainstorm(self, thread_id: str) -> Optional[dict]:
        cursor = await self._db.execute(
            "SELECT result FROM brainstorm_results WHERE thread_id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else None

    async def list_meetings(self, limit: int = 50) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT thread_id, result, created_at FROM meeting_results ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [{"thread_id": r[0], **json.loads(r[1]), "created_at": r[2]} for r in rows]

    async def list_brainstorms(self, limit: int = 50) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT thread_id, result, created_at FROM brainstorm_results ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [{"thread_id": r[0], **json.loads(r[1]), "created_at": r[2]} for r in rows]

    async def get_stats(self) -> dict:
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
