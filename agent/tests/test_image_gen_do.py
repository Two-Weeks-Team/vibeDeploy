import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from agent.tools.image_gen_do import IMAGE_MODEL, DOImageGenerator


def _make_b64_response(raw: bytes) -> dict:
    return {"data": [{"b64_json": base64.b64encode(raw).decode()}]}


@pytest.fixture()
def generator(monkeypatch):
    monkeypatch.setenv("DIGITALOCEAN_INFERENCE_KEY", "test-key-123")
    return DOImageGenerator()


@pytest.fixture()
def generator_no_key(monkeypatch):
    monkeypatch.delenv("DIGITALOCEAN_INFERENCE_KEY", raising=False)
    return DOImageGenerator()


@pytest.fixture()
def mock_async_client():
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client
        yield mock_client


@pytest.mark.asyncio
async def test_generate_og_image_success(generator, mock_async_client):
    fake_bytes = b"fake-png-data"
    mock_response = MagicMock()
    mock_response.json.return_value = _make_b64_response(fake_bytes)
    mock_response.raise_for_status = MagicMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)

    result = await generator.generate_og_image("MyApp", "A task manager")
    assert result == fake_bytes


@pytest.mark.asyncio
async def test_generate_logo_success(generator, mock_async_client):
    fake_bytes = b"logo-png-data"
    mock_response = MagicMock()
    mock_response.json.return_value = _make_b64_response(fake_bytes)
    mock_response.raise_for_status = MagicMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)

    result = await generator.generate_logo("MyApp")
    assert result == fake_bytes


@pytest.mark.asyncio
async def test_generate_og_image_missing_key_returns_none(generator_no_key):
    result = await generator_no_key.generate_og_image("MyApp", "desc")
    assert result is None


@pytest.mark.asyncio
async def test_generate_logo_missing_key_returns_none(generator_no_key):
    result = await generator_no_key.generate_logo("MyApp")
    assert result is None


@pytest.mark.asyncio
async def test_generate_og_image_http_error_returns_none(generator, mock_async_client):
    mock_response = MagicMock()
    mock_response.status_code = 503
    http_error = httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_response)
    mock_async_client.post = AsyncMock(side_effect=http_error)

    result = await generator.generate_og_image("MyApp", "desc")
    assert result is None


@pytest.mark.asyncio
async def test_generate_logo_timeout_returns_none(generator, mock_async_client):
    mock_async_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

    result = await generator.generate_logo("MyApp")
    assert result is None


@pytest.mark.asyncio
async def test_generate_unexpected_exception_returns_none(generator, mock_async_client):
    mock_async_client.post = AsyncMock(side_effect=RuntimeError("unexpected"))

    result = await generator.generate_og_image("MyApp", "desc")
    assert result is None


@pytest.mark.asyncio
async def test_og_image_prompt_contains_app_name_and_description(generator, mock_async_client):
    fake_bytes = b"img"
    mock_response = MagicMock()
    mock_response.json.return_value = _make_b64_response(fake_bytes)
    mock_response.raise_for_status = MagicMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)

    await generator.generate_og_image("VibeApp", "A vibe coding tool")

    call_kwargs = mock_async_client.post.call_args.kwargs
    payload = call_kwargs["json"]
    assert "VibeApp" in payload["prompt"]
    assert "A vibe coding tool" in payload["prompt"]
    assert payload["model"] == IMAGE_MODEL


@pytest.mark.asyncio
async def test_logo_prompt_contains_app_name(generator, mock_async_client):
    fake_bytes = b"logo"
    mock_response = MagicMock()
    mock_response.json.return_value = _make_b64_response(fake_bytes)
    mock_response.raise_for_status = MagicMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)

    await generator.generate_logo("CoolBrand")

    call_kwargs = mock_async_client.post.call_args.kwargs
    payload = call_kwargs["json"]
    assert "CoolBrand" in payload["prompt"]
    assert payload["model"] == IMAGE_MODEL


@pytest.mark.asyncio
async def test_request_uses_bearer_auth(generator, mock_async_client):
    fake_bytes = b"auth-check"
    mock_response = MagicMock()
    mock_response.json.return_value = _make_b64_response(fake_bytes)
    mock_response.raise_for_status = MagicMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)

    await generator.generate_og_image("App", "desc")

    call_kwargs = mock_async_client.post.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-key-123"
