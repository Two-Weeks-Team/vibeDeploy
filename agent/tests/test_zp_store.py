"""Tests for agent/db/zp_store.py — update_card validation, JSONB serialisation, and column allow-list."""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from agent.db.zp_store import (
    _ALLOWED_CARD_COLUMNS,
    _JSONB_COLUMNS,
    _card_row_to_dict,
    update_card,
)


def _make_fake_pool():
    """Return (fake_pool, fake_conn) where pool.acquire() is a proper async context manager."""
    fake_conn = AsyncMock()

    @asynccontextmanager
    async def _acquire():
        yield fake_conn

    fake_pool = AsyncMock()
    fake_pool.acquire = _acquire
    return fake_pool, fake_conn


# ---------------------------------------------------------------------------
# update_card – allowed / disallowed columns
# ---------------------------------------------------------------------------


class TestUpdateCardValidation:
    @pytest.mark.asyncio
    async def test_empty_fields_returns_immediately(self):
        """update_card with no keyword args should be a no-op (no DB call)."""
        with patch("agent.db.zp_store.get_pool") as mock_gp:
            await update_card("card-1")
            mock_gp.assert_not_called()

    @pytest.mark.asyncio
    async def test_allowed_column_succeeds(self):
        """update_card with a valid column should build a query and execute."""
        fake_pool, fake_conn = _make_fake_pool()

        async def _get_pool():
            return fake_pool

        with patch("agent.db.zp_store.get_pool", side_effect=_get_pool):
            await update_card("card-1", status="go_ready")

        fake_conn.execute.assert_awaited_once()
        sql = fake_conn.execute.call_args[0][0]
        assert "status = $1" in sql
        assert fake_conn.execute.call_args[0][1] == "go_ready"
        assert fake_conn.execute.call_args[0][2] == "card-1"

    @pytest.mark.asyncio
    async def test_disallowed_column_raises_valueerror(self):
        """update_card with an unknown column name must raise ValueError."""
        with pytest.raises(ValueError, match="Disallowed column names"):
            await update_card("card-1", evil_column="drop table")

    @pytest.mark.asyncio
    async def test_multiple_disallowed_columns_listed(self):
        """ValueError message should mention every disallowed column."""
        with pytest.raises(ValueError) as exc_info:
            await update_card("card-1", bad1="x", bad2="y")
        msg = str(exc_info.value)
        assert "bad1" in msg
        assert "bad2" in msg

    @pytest.mark.asyncio
    async def test_mixed_allowed_and_disallowed_raises(self):
        """If any column is disallowed, the entire call should fail."""
        with pytest.raises(ValueError, match="Disallowed column names"):
            await update_card("card-1", status="ok", sql_injection="bad")


# ---------------------------------------------------------------------------
# update_card – JSONB serialisation
# ---------------------------------------------------------------------------


class TestUpdateCardJsonb:
    @pytest.mark.asyncio
    async def test_jsonb_dict_is_serialised(self):
        """A dict value for a JSONB column should be JSON-serialised."""
        fake_pool, fake_conn = _make_fake_pool()

        async def _get_pool():
            return fake_pool

        payload = {"tech": 80, "market": 70}
        with patch("agent.db.zp_store.get_pool", side_effect=_get_pool):
            await update_card("card-1", score_breakdown=payload)

        sql = fake_conn.execute.call_args[0][0]
        assert "::jsonb" in sql
        serialised_value = fake_conn.execute.call_args[0][1]
        assert json.loads(serialised_value) == payload

    @pytest.mark.asyncio
    async def test_jsonb_list_is_serialised(self):
        """A list value for a JSONB column should be JSON-serialised."""
        fake_pool, fake_conn = _make_fake_pool()

        async def _get_pool():
            return fake_pool

        items = [{"event": "start"}, {"event": "end"}]
        with patch("agent.db.zp_store.get_pool", side_effect=_get_pool):
            await update_card("card-1", build_events=items)

        serialised_value = fake_conn.execute.call_args[0][1]
        assert json.loads(serialised_value) == items

    @pytest.mark.asyncio
    async def test_jsonb_string_passed_through(self):
        """A string value for a JSONB column should be passed as-is (already serialised)."""
        fake_pool, fake_conn = _make_fake_pool()

        async def _get_pool():
            return fake_pool

        raw_json = '{"already": "serialised"}'
        with patch("agent.db.zp_store.get_pool", side_effect=_get_pool):
            await update_card("card-1", insights=raw_json)

        passed_value = fake_conn.execute.call_args[0][1]
        assert passed_value == raw_json

    @pytest.mark.asyncio
    async def test_non_jsonb_column_not_serialised(self):
        """A plain column value should not be JSON-serialised."""
        fake_pool, fake_conn = _make_fake_pool()

        async def _get_pool():
            return fake_pool

        with patch("agent.db.zp_store.get_pool", side_effect=_get_pool):
            await update_card("card-1", domain="health")

        sql = fake_conn.execute.call_args[0][0]
        assert "::jsonb" not in sql
        passed_value = fake_conn.execute.call_args[0][1]
        assert passed_value == "health"


# ---------------------------------------------------------------------------
# _ALLOWED_CARD_COLUMNS coverage
# ---------------------------------------------------------------------------


class TestAllowedCardColumns:
    """Verify the allow-list matches every column name used via update_card in the codebase."""

    def test_jsonb_columns_are_subset_of_allowed(self):
        """Every JSONB column must also be in the allowed set."""
        assert _JSONB_COLUMNS.issubset(_ALLOWED_CARD_COLUMNS)

    def test_known_used_columns_are_allowed(self):
        """Columns referenced in server.py and orchestrator.py must be in the allow-list."""
        used_columns = {
            "status",
            "score",
            "domain",
            "reason",
            "reason_code",
            "score_breakdown",
            "build_step",
            "analysis_step",
            "repo_url",
            "live_url",
            "thread_id",
            "title",
            "video_id",
            "build_events",
            "build_phase",
            "build_node",
            "papers_found",
            "competitors_found",
            "saturation",
            "novelty_boost",
            "video_summary",
            "insights",
            "mvp_proposal",
        }
        missing = used_columns - _ALLOWED_CARD_COLUMNS
        assert missing == set(), f"Columns used in code but missing from allow-list: {missing}"

    def test_id_not_allowed(self):
        """Primary key 'id' must never be updatable."""
        assert "id" not in _ALLOWED_CARD_COLUMNS

    def test_session_id_not_allowed(self):
        """Foreign key 'session_id' must never be updatable via update_card."""
        assert "session_id" not in _ALLOWED_CARD_COLUMNS

    def test_created_at_not_allowed(self):
        """Timestamp 'created_at' must never be updatable via update_card."""
        assert "created_at" not in _ALLOWED_CARD_COLUMNS


# ---------------------------------------------------------------------------
# _card_row_to_dict
# ---------------------------------------------------------------------------


class TestCardRowToDict:
    def _make_row(self, **overrides) -> dict:
        """Build a minimal row dict mimicking an asyncpg Record."""
        base = {
            "id": "card-1",
            "session_id": "sess-1",
            "created_at": "2025-01-01T00:00:00Z",
            "video_id": "yt-abc",
            "title": "Test",
            "status": "analyzing",
            "score": 0,
            "domain": "",
            "reason": "",
            "reason_code": "",
            "score_breakdown": {},
            "papers_found": 0,
            "competitors_found": "",
            "saturation": "",
            "novelty_boost": 0.0,
            "video_summary": "",
            "insights": [],
            "mvp_proposal": {},
            "build_step": "",
            "analysis_step": "",
            "repo_url": "",
            "live_url": "",
            "thread_id": None,
        }
        base.update(overrides)
        return base

    def test_id_renamed_to_card_id(self):
        row = self._make_row()
        result = _card_row_to_dict(row)
        assert "card_id" in result
        assert result["card_id"] == "card-1"
        assert "id" not in result

    def test_session_id_stripped(self):
        row = self._make_row()
        result = _card_row_to_dict(row)
        assert "session_id" not in result

    def test_created_at_stripped(self):
        row = self._make_row()
        result = _card_row_to_dict(row)
        assert "created_at" not in result

    def test_insights_string_parsed_as_json(self):
        row = self._make_row(insights='[{"key": "value"}]')
        result = _card_row_to_dict(row)
        assert result["insights"] == [{"key": "value"}]

    def test_mvp_proposal_string_parsed_as_json(self):
        row = self._make_row(mvp_proposal='{"name": "app"}')
        result = _card_row_to_dict(row)
        assert result["mvp_proposal"] == {"name": "app"}

    def test_score_breakdown_string_parsed_as_json(self):
        row = self._make_row(score_breakdown='{"tech": 80}')
        result = _card_row_to_dict(row)
        assert result["score_breakdown"] == {"tech": 80}

    def test_already_parsed_dict_unchanged(self):
        original = {"tech": 90}
        row = self._make_row(score_breakdown=original)
        result = _card_row_to_dict(row)
        assert result["score_breakdown"] == {"tech": 90}

    def test_already_parsed_list_unchanged(self):
        original = [{"idea": "x"}]
        row = self._make_row(insights=original)
        result = _card_row_to_dict(row)
        assert result["insights"] == [{"idea": "x"}]

    def test_invalid_json_string_raises(self):
        """If a JSONB column contains invalid JSON as a string, json.loads should raise."""
        row = self._make_row(insights="not valid json {{{")
        with pytest.raises(json.JSONDecodeError):
            _card_row_to_dict(row)
