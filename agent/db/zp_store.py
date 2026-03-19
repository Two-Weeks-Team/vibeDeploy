import json
import uuid

from agent.db.connection import get_pool


async def ensure_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS zp_sessions (
                id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'exploring',
                goal_go_cards INT DEFAULT 10,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS zp_cards (
                id TEXT PRIMARY KEY,
                session_id TEXT REFERENCES zp_sessions(id),
                video_id TEXT DEFAULT '',
                title TEXT DEFAULT '',
                status TEXT DEFAULT 'analyzing',
                score INT DEFAULT 0,
                domain TEXT DEFAULT '',
                reason TEXT DEFAULT '',
                reason_code TEXT DEFAULT '',
                score_breakdown JSONB DEFAULT '{}'::jsonb,
                papers_found INT DEFAULT 0,
                competitors_found TEXT DEFAULT '',
                saturation TEXT DEFAULT '',
                novelty_boost REAL DEFAULT 0,
                video_summary TEXT DEFAULT '',
                insights JSONB DEFAULT '[]'::jsonb,
                mvp_proposal JSONB DEFAULT '{}'::jsonb,
                build_step TEXT DEFAULT '',
                analysis_step TEXT DEFAULT '',
                repo_url TEXT DEFAULT '',
                live_url TEXT DEFAULT '',
                thread_id TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )

        migrations = [
            "ALTER TABLE zp_cards ADD COLUMN IF NOT EXISTS analysis_step TEXT DEFAULT ''",
            "ALTER TABLE zp_cards ADD COLUMN IF NOT EXISTS repo_url TEXT DEFAULT ''",
            "ALTER TABLE zp_cards ADD COLUMN IF NOT EXISTS live_url TEXT DEFAULT ''",
            "ALTER TABLE zp_cards ADD COLUMN IF NOT EXISTS build_events JSONB DEFAULT '[]'::jsonb",
            "ALTER TABLE zp_cards ADD COLUMN IF NOT EXISTS build_phase TEXT DEFAULT ''",
            "ALTER TABLE zp_cards ADD COLUMN IF NOT EXISTS build_node TEXT DEFAULT ''",
            "ALTER TABLE zp_cards ADD COLUMN IF NOT EXISTS score_breakdown JSONB DEFAULT '{}'::jsonb",
        ]
        for migration in migrations:
            try:
                await conn.execute(migration)
            except Exception:
                pass


async def create_session(goal: int = 10) -> dict:
    session_id = str(uuid.uuid4())
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO zp_sessions (id, status, goal_go_cards) VALUES ($1, $2, $3)",
            session_id,
            "exploring",
            goal,
        )
    return {"session_id": session_id, "status": "exploring", "goal_go_cards": goal, "cards": []}


async def ensure_session(session_id: str, goal: int = 10) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO zp_sessions (id, status, goal_go_cards) VALUES ($1, $2, $3) ON CONFLICT (id) DO NOTHING",
            session_id,
            "exploring",
            goal,
        )


async def get_session(session_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM zp_sessions WHERE id = $1", session_id)
        if not row:
            return None
        cards = await conn.fetch(
            "SELECT * FROM zp_cards WHERE session_id = $1 AND status != 'deleted' ORDER BY created_at",
            session_id,
        )
        return {
            "session_id": row["id"],
            "status": row["status"],
            "goal_go_cards": row["goal_go_cards"],
            "cards": [_card_row_to_dict(c) for c in cards],
        }


async def get_dashboard() -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM zp_sessions ORDER BY created_at DESC LIMIT 1")
        if not row:
            return {"session_id": None, "status": "idle", "cards": []}
        cards = await conn.fetch(
            "SELECT * FROM zp_cards WHERE session_id = $1 AND status != 'deleted' ORDER BY created_at",
            row["id"],
        )
        return {
            "session_id": row["id"],
            "status": row["status"],
            "goal_go_cards": row["goal_go_cards"],
            "cards": [_card_row_to_dict(c) for c in cards],
        }


async def reset_session(session_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM zp_cards WHERE session_id = $1", session_id)
        await conn.execute("DELETE FROM zp_sessions WHERE id = $1", session_id)


async def reset_all_sessions() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM zp_cards")
        await conn.execute("DELETE FROM zp_sessions")


async def add_card(session_id: str, card_id: str, video_id: str, title: str = "") -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO zp_cards (id, session_id, video_id, title) VALUES ($1, $2, $3, $4)",
            card_id,
            session_id,
            video_id,
            title,
        )
    return {"card_id": card_id, "video_id": video_id, "title": title, "status": "analyzing"}


async def update_card(card_id: str, **fields: object) -> None:
    if not fields:
        return
    pool = await get_pool()
    sets = []
    values = []
    for i, (k, v) in enumerate(fields.items(), 1):
        if k in ("insights", "mvp_proposal", "score_breakdown"):
            sets.append(f"{k} = ${i}::jsonb")
            values.append(json.dumps(v) if not isinstance(v, str) else v)
        else:
            sets.append(f"{k} = ${i}")
            values.append(v)
    values.append(card_id)
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE zp_cards SET {', '.join(sets)} WHERE id = ${len(values)}",  # noqa: S608
            *values,
        )


async def update_session_status(session_id: str, status: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE zp_sessions SET status = $1 WHERE id = $2",
            status,
            session_id,
        )


async def count_go_ready(session_id: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) as cnt FROM zp_cards WHERE session_id = $1 AND status = 'go_ready'",
            session_id,
        )
        return row["cnt"] if row else 0


async def get_session_goal(session_id: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT goal_go_cards FROM zp_sessions WHERE id = $1",
            session_id,
        )
        return row["goal_go_cards"] if row else 10


def _card_row_to_dict(row: object) -> dict:
    d = dict(row)  # type: ignore[call-overload]
    d["card_id"] = d.pop("id")
    d.pop("session_id", None)
    d.pop("created_at", None)
    if isinstance(d.get("insights"), str):
        d["insights"] = json.loads(d["insights"])
    if isinstance(d.get("mvp_proposal"), str):
        d["mvp_proposal"] = json.loads(d["mvp_proposal"])
    if isinstance(d.get("score_breakdown"), str):
        d["score_breakdown"] = json.loads(d["score_breakdown"])
    return d
