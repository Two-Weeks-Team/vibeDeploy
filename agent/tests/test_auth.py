"""Tests for the auth module (API key verification and rate limiting)."""

import time
from unittest.mock import MagicMock

import pytest

from agent.auth import (
    _classify_rate_tier,
    _get_api_key,
    _is_public_path,
    _rate_buckets,
    _RateLimitBucket,
    rate_limit_check,
    verify_api_key,
)


class TestPublicPaths:
    def test_health_is_public(self):
        assert _is_public_path("/health") is True

    def test_root_is_public(self):
        assert _is_public_path("/") is True

    def test_cost_estimate_is_public(self):
        assert _is_public_path("/cost-estimate") is True

    def test_models_is_public(self):
        assert _is_public_path("/models") is True

    def test_test_prefix_is_public(self):
        assert _is_public_path("/test/result/abc") is True

    def test_run_is_not_public(self):
        assert _is_public_path("/run") is False

    def test_zero_prompt_start_is_not_public(self):
        assert _is_public_path("/zero-prompt/start") is False

    def test_dashboard_stats_is_not_public(self):
        assert _is_public_path("/dashboard/stats") is False


class TestGetApiKey:
    def test_returns_vibedeploy_api_key(self, monkeypatch):
        monkeypatch.setenv("VIBEDEPLOY_API_KEY", "test-key-123")
        monkeypatch.delenv("VIBEDEPLOY_OPS_TOKEN", raising=False)
        monkeypatch.delenv("DASHBOARD_ADMIN_TOKEN", raising=False)
        assert _get_api_key() == "test-key-123"

    def test_falls_back_to_ops_token(self, monkeypatch):
        monkeypatch.delenv("VIBEDEPLOY_API_KEY", raising=False)
        monkeypatch.setenv("VIBEDEPLOY_OPS_TOKEN", "ops-token")
        monkeypatch.delenv("DASHBOARD_ADMIN_TOKEN", raising=False)
        assert _get_api_key() == "ops-token"

    def test_returns_empty_when_none_set(self, monkeypatch):
        monkeypatch.delenv("VIBEDEPLOY_API_KEY", raising=False)
        monkeypatch.delenv("VIBEDEPLOY_OPS_TOKEN", raising=False)
        monkeypatch.delenv("DASHBOARD_ADMIN_TOKEN", raising=False)
        assert _get_api_key() == ""

    def test_does_not_fall_back_to_inference_key(self, monkeypatch):
        monkeypatch.delenv("VIBEDEPLOY_API_KEY", raising=False)
        monkeypatch.delenv("VIBEDEPLOY_OPS_TOKEN", raising=False)
        monkeypatch.delenv("DASHBOARD_ADMIN_TOKEN", raising=False)
        monkeypatch.setenv("DIGITALOCEAN_INFERENCE_KEY", "should-not-use")
        assert _get_api_key() == ""


class TestRateTierClassification:
    def test_run_is_write(self):
        assert _classify_rate_tier("/run", "POST") == "write"

    def test_api_run_is_write(self):
        assert _classify_rate_tier("/api/run", "POST") == "write"

    def test_zero_prompt_start_is_write(self):
        assert _classify_rate_tier("/zero-prompt/start", "POST") == "write"

    def test_events_is_sse(self):
        assert _classify_rate_tier("/dashboard/events", "GET") == "sse"

    def test_zero_prompt_events_is_sse(self):
        assert _classify_rate_tier("/zero-prompt/events", "GET") == "sse"

    def test_build_events_is_sse(self):
        assert _classify_rate_tier("/zero-prompt/s1/build/c1/events", "GET") == "sse"

    def test_actions_is_write(self):
        assert _classify_rate_tier("/zero-prompt/s1/actions", "POST") == "write"

    def test_dashboard_stats_is_read(self):
        assert _classify_rate_tier("/dashboard/stats", "GET") == "read"

    def test_result_is_read(self):
        assert _classify_rate_tier("/result/abc", "GET") == "read"


class TestRateLimitBucket:
    def test_allows_within_limit(self):
        bucket = _RateLimitBucket()
        now = time.monotonic()
        for _ in range(5):
            assert bucket.hit(now, 60, 5) is True

    def test_blocks_at_limit(self):
        bucket = _RateLimitBucket()
        now = time.monotonic()
        for _ in range(5):
            bucket.hit(now, 60, 5)
        assert bucket.hit(now, 60, 5) is False

    def test_allows_after_window_expires(self):
        bucket = _RateLimitBucket()
        now = time.monotonic()
        for _ in range(5):
            bucket.hit(now, 60, 5)
        # Simulate time passing beyond window
        assert bucket.hit(now + 61, 60, 5) is True


@pytest.mark.asyncio
class TestVerifyApiKey:
    async def test_public_path_skips_auth(self):
        request = MagicMock()
        request.url.path = "/health"
        result = await verify_api_key(request, api_key=None)
        assert result is None

    async def test_no_key_configured_passes(self, monkeypatch):
        monkeypatch.delenv("VIBEDEPLOY_API_KEY", raising=False)
        monkeypatch.delenv("VIBEDEPLOY_OPS_TOKEN", raising=False)
        monkeypatch.delenv("DASHBOARD_ADMIN_TOKEN", raising=False)
        request = MagicMock()
        request.url.path = "/run"
        result = await verify_api_key(request, api_key=None)
        assert result is None

    async def test_valid_key_passes(self, monkeypatch):
        monkeypatch.setenv("VIBEDEPLOY_API_KEY", "valid-key")
        request = MagicMock()
        request.url.path = "/run"
        result = await verify_api_key(request, api_key="valid-key")
        assert result == "valid-key"

    async def test_invalid_key_raises_403(self, monkeypatch):
        from fastapi import HTTPException

        monkeypatch.setenv("VIBEDEPLOY_API_KEY", "valid-key")
        request = MagicMock()
        request.url.path = "/run"
        request.client.host = "127.0.0.1"
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(request, api_key="wrong-key")
        assert exc_info.value.status_code == 403

    async def test_missing_key_raises_401(self, monkeypatch):
        from fastapi import HTTPException

        monkeypatch.setenv("VIBEDEPLOY_API_KEY", "valid-key")
        request = MagicMock()
        request.url.path = "/run"
        request.query_params = {}
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(request, api_key=None)
        assert exc_info.value.status_code == 401

    async def test_sse_path_accepts_query_param(self, monkeypatch):
        monkeypatch.setenv("VIBEDEPLOY_API_KEY", "valid-key")
        request = MagicMock()
        request.url.path = "/zero-prompt/events"
        request.query_params = {"api_key": "valid-key"}
        result = await verify_api_key(request, api_key=None)
        assert result == "valid-key"


@pytest.mark.asyncio
class TestRateLimitCheck:
    async def test_public_path_not_limited(self):
        request = MagicMock()
        request.url.path = "/health"
        # Should not raise
        await rate_limit_check(request)

    async def test_blocks_after_limit(self):
        from fastapi import HTTPException

        _rate_buckets.clear()
        request = MagicMock()
        request.url.path = "/run"
        request.method = "POST"
        request.client.host = "test-ip-block"

        for _ in range(10):
            await rate_limit_check(request)

        with pytest.raises(HTTPException) as exc_info:
            await rate_limit_check(request)
        assert exc_info.value.status_code == 429
