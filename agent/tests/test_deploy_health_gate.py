from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent.nodes.deployer import _check_deploy_health, get_deploy_gate_status


def test_gate_blocks_when_build_not_passed():
    state = {"build_validation": {"passed": False}}
    assert get_deploy_gate_status(state) == "blocked"


def test_gate_allows_when_build_passed():
    state = {"build_validation": {"passed": True}}
    assert get_deploy_gate_status(state) == "allowed"


def test_gate_blocks_when_build_validation_missing():
    assert get_deploy_gate_status({}) == "blocked"


def test_gate_blocks_with_empty_build_validation():
    assert get_deploy_gate_status({"build_validation": {}}) == "blocked"


def test_gate_blocks_with_partial_build_validation_no_passed():
    state = {"build_validation": {"errors": ["some error"], "skipped": False}}
    assert get_deploy_gate_status(state) == "blocked"


def test_gate_allows_with_extra_fields():
    state = {"build_validation": {"passed": True, "errors": [], "skipped": False}}
    assert get_deploy_gate_status(state) == "allowed"


def test_gate_with_none_build_validation():
    state = {"build_validation": None}
    assert get_deploy_gate_status(state) == "blocked"


@pytest.mark.asyncio
async def test_check_deploy_health_returns_healthy_on_200():
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    mock_async_context = AsyncMock()
    mock_async_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_async_context):
        result = await _check_deploy_health("https://example.ondigitalocean.app")

    assert result["status"] == "healthy"
    assert result["status_code"] == 200
    assert result["url"] == "https://example.ondigitalocean.app/health"


@pytest.mark.asyncio
async def test_check_deploy_health_returns_unhealthy_on_non_200():
    mock_response = MagicMock()
    mock_response.status_code = 503

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    mock_async_context = AsyncMock()
    mock_async_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_async_context):
        result = await _check_deploy_health("https://example.ondigitalocean.app")

    assert result["status"] == "unhealthy"
    assert result["status_code"] == 503


@pytest.mark.asyncio
async def test_check_deploy_health_returns_unreachable_on_connection_error():
    mock_async_context = AsyncMock()
    mock_async_context.__aenter__ = AsyncMock(side_effect=ConnectionError("Connection refused"))
    mock_async_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_async_context):
        result = await _check_deploy_health("https://example.ondigitalocean.app")

    assert result["status"] == "unreachable"
    assert "error" in result
    assert "Connection refused" in result["error"]


@pytest.mark.asyncio
async def test_check_deploy_health_strips_trailing_slash():
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    mock_async_context = AsyncMock()
    mock_async_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_async_context):
        result = await _check_deploy_health("https://example.ondigitalocean.app/")

    assert result["url"] == "https://example.ondigitalocean.app/health"


@pytest.mark.asyncio
async def test_check_deploy_health_404_returns_unhealthy():
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    mock_async_context = AsyncMock()
    mock_async_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_async_context):
        result = await _check_deploy_health("https://example.ondigitalocean.app")

    assert result["status"] == "unhealthy"
    assert result["status_code"] == 404


@pytest.mark.asyncio
async def test_check_deploy_health_error_message_truncated_at_200():
    long_error = "x" * 500

    mock_async_context = AsyncMock()
    mock_async_context.__aenter__ = AsyncMock(side_effect=RuntimeError(long_error))
    mock_async_context.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_async_context):
        result = await _check_deploy_health("https://example.ondigitalocean.app")

    assert result["status"] == "unreachable"
    assert len(result["error"]) <= 200
