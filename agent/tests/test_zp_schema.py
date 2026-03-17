"""Tests for Zero-Prompt PostgreSQL schema tables (ADR-A3)."""

import re
import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"

POSTGRES_TO_SQLITE = [
    (r"CREATE EXTENSION[^;]+;", ""),
    (r"TIMESTAMPTZ", "TEXT"),
    (r"DEFAULT NOW\(\)", "DEFAULT CURRENT_TIMESTAMP"),
    (r"UUID PRIMARY KEY DEFAULT uuid_generate_v4\(\)", "TEXT PRIMARY KEY"),
    (r"UUID NOT NULL", "TEXT NOT NULL"),
    (r"UUID\b", "TEXT"),
    (r"JSONB\b", "TEXT"),
    (r"NUMERIC\(\d+,\s*\d+\)", "REAL"),
    (r"SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    (r"CHECK\s*\((?:[^()]*|\([^()]*\))*\)", ""),
]


def adapt_sql_for_sqlite(sql: str) -> str:
    for pattern, replacement in POSTGRES_TO_SQLITE:
        sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
    return sql


def get_schema_sql() -> str:
    return SCHEMA_PATH.read_text()


def execute_schema_in_sqlite() -> sqlite3.Connection:
    raw_sql = get_schema_sql()
    adapted_sql = adapt_sql_for_sqlite(raw_sql)
    conn = sqlite3.connect(":memory:")
    conn.executescript(adapted_sql)
    return conn


def get_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


class TestSchemaParses:
    def test_schema_file_exists(self):
        assert SCHEMA_PATH.exists(), f"schema.sql not found at {SCHEMA_PATH}"

    def test_schema_executes_without_error(self):
        conn = execute_schema_in_sqlite()
        assert conn is not None

    def test_schema_has_no_unclosed_statements(self):
        sql = get_schema_sql()
        assert "CREATE TABLE" in sql
        assert sql.strip().endswith(";")


class TestZeroPromptTablesExist:
    def setup_method(self):
        self.conn = execute_schema_in_sqlite()
        self.tables = get_tables(self.conn)

    def test_zero_prompt_sessions_table_exists(self):
        assert "zero_prompt_sessions" in self.tables

    def test_zero_prompt_cards_table_exists(self):
        assert "zero_prompt_cards" in self.tables

    def test_zero_prompt_build_queue_table_exists(self):
        assert "zero_prompt_build_queue" in self.tables


class TestZeroPromptSessionsInsertSelect:
    def setup_method(self):
        self.conn = execute_schema_in_sqlite()

    def test_insert_and_select_session(self):
        self.conn.execute(
            "INSERT INTO zero_prompt_sessions (session_id, status, goal_go_cards, total_cost) VALUES (?, ?, ?, ?)",
            ("sess-001", "exploring", 10, 0.0),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT session_id, status, goal_go_cards, total_cost FROM zero_prompt_sessions WHERE session_id = ?",
            ("sess-001",),
        ).fetchone()
        assert row is not None
        assert row[0] == "sess-001"
        assert row[1] == "exploring"
        assert row[2] == 10
        assert row[3] == 0.0

    def test_default_status_is_exploring(self):
        self.conn.execute(
            "INSERT INTO zero_prompt_sessions (session_id) VALUES (?)",
            ("sess-defaults",),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT status, goal_go_cards, total_cost FROM zero_prompt_sessions WHERE session_id = ?",
            ("sess-defaults",),
        ).fetchone()
        assert row[0] == "exploring"
        assert row[1] == 10
        assert row[2] == 0.0


class TestZeroPromptCardsInsertSelect:
    def setup_method(self):
        self.conn = execute_schema_in_sqlite()
        self.conn.execute(
            "INSERT INTO zero_prompt_sessions (session_id) VALUES (?)",
            ("sess-card-test",),
        )
        self.conn.commit()

    def test_insert_and_select_card(self):
        self.conn.execute(
            "INSERT INTO zero_prompt_cards "
            "(card_id, session_id, source_video_id, app_name, tagline, status, verdict, novelty_boost) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("card-001", "sess-card-test", "yt-abc", "TestApp", "A great app", "evaluating", "GO", 0.1),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT card_id, session_id, app_name, verdict, novelty_boost FROM zero_prompt_cards WHERE card_id = ?",
            ("card-001",),
        ).fetchone()
        assert row is not None
        assert row[0] == "card-001"
        assert row[1] == "sess-card-test"
        assert row[2] == "TestApp"
        assert row[3] == "GO"
        assert row[4] == 0.1

    def test_card_null_verdict_allowed(self):
        self.conn.execute(
            "INSERT INTO zero_prompt_cards (card_id, session_id) VALUES (?, ?)",
            ("card-002", "sess-card-test"),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT verdict FROM zero_prompt_cards WHERE card_id = ?",
            ("card-002",),
        ).fetchone()
        assert row[0] is None

    def test_cascade_delete_removes_cards(self):
        self.conn.execute(
            "INSERT INTO zero_prompt_cards (card_id, session_id) VALUES (?, ?)",
            ("card-cascade", "sess-card-test"),
        )
        self.conn.commit()
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute(
            "DELETE FROM zero_prompt_sessions WHERE session_id = ?",
            ("sess-card-test",),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT card_id FROM zero_prompt_cards WHERE session_id = ?",
            ("sess-card-test",),
        ).fetchone()
        assert row is None


class TestZeroPromptBuildQueueInsertSelect:
    def setup_method(self):
        self.conn = execute_schema_in_sqlite()
        self.conn.execute(
            "INSERT INTO zero_prompt_sessions (session_id) VALUES (?)",
            ("sess-queue-test",),
        )
        self.conn.execute(
            "INSERT INTO zero_prompt_cards (card_id, session_id) VALUES (?, ?)",
            ("card-queue", "sess-queue-test"),
        )
        self.conn.commit()

    def test_insert_and_select_queue_entry(self):
        self.conn.execute(
            "INSERT INTO zero_prompt_build_queue (session_id, card_id, status) VALUES (?, ?, ?)",
            ("sess-queue-test", "card-queue", "queued"),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT session_id, card_id, status FROM zero_prompt_build_queue WHERE session_id = ?",
            ("sess-queue-test",),
        ).fetchone()
        assert row is not None
        assert row[0] == "sess-queue-test"
        assert row[1] == "card-queue"
        assert row[2] == "queued"

    def test_default_status_is_queued(self):
        self.conn.execute(
            "INSERT INTO zero_prompt_build_queue (session_id, card_id) VALUES (?, ?)",
            ("sess-queue-test", "card-queue"),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT status FROM zero_prompt_build_queue ORDER BY id DESC LIMIT 1",
        ).fetchone()
        assert row[0] == "queued"

    def test_started_at_and_completed_at_nullable(self):
        self.conn.execute(
            "INSERT INTO zero_prompt_build_queue (session_id, card_id, started_at, completed_at) "
            "VALUES (?, ?, NULL, NULL)",
            ("sess-queue-test", "card-queue"),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT started_at, completed_at FROM zero_prompt_build_queue ORDER BY id DESC LIMIT 1",
        ).fetchone()
        assert row[0] is None
        assert row[1] is None
