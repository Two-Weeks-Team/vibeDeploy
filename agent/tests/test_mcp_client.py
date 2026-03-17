from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from gradient.mcp_client import MCPClient  # noqa: E402


@pytest.fixture()
def client_no_url(monkeypatch):
    monkeypatch.delenv("DO_MCP_SERVER_URL", raising=False)
    monkeypatch.delenv("DIGITALOCEAN_API_TOKEN", raising=False)
    return MCPClient()


@pytest.fixture()
def client_with_url(monkeypatch):
    monkeypatch.setenv("DO_MCP_SERVER_URL", "http://mcp.example.com")
    monkeypatch.setenv("DIGITALOCEAN_API_TOKEN", "test-token")
    return MCPClient()


def test_is_available_false_when_url_missing(client_no_url):
    assert client_no_url.is_available() is False


def test_is_available_true_when_url_set(client_with_url):
    assert client_with_url.is_available() is True


@pytest.mark.asyncio
async def test_list_apps_returns_empty_when_not_configured(client_no_url):
    result = await client_no_url.list_apps()
    assert result == []


@pytest.mark.asyncio
async def test_get_app_returns_none_when_not_configured(client_no_url):
    result = await client_no_url.get_app("app-123")
    assert result is None


@pytest.mark.asyncio
async def test_create_app_returns_empty_dict_when_not_configured(client_no_url):
    result = await client_no_url.create_app({"name": "my-app"})
    assert result == {}


@pytest.mark.asyncio
async def test_list_apps_returns_apps_from_mcp(client_with_url):
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"result": {"apps": [{"id": "app-1", "name": "my-app"}]}}

    mock_post = AsyncMock(return_value=fake_response)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.post = mock_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client_with_url.list_apps()

    assert result == [{"id": "app-1", "name": "my-app"}]


@pytest.mark.asyncio
async def test_list_apps_returns_list_result_directly(client_with_url):
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"result": [{"id": "app-2"}]}

    mock_post = AsyncMock(return_value=fake_response)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.post = mock_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client_with_url.list_apps()

    assert result == [{"id": "app-2"}]


@pytest.mark.asyncio
async def test_get_app_returns_app_dict(client_with_url):
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"result": {"app": {"id": "app-123", "name": "found-app"}}}

    mock_post = AsyncMock(return_value=fake_response)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.post = mock_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client_with_url.get_app("app-123")

    assert result == {"id": "app-123", "name": "found-app"}


@pytest.mark.asyncio
async def test_get_app_returns_none_on_404(client_with_url):
    mock_response = MagicMock()
    mock_response.status_code = 404

    http_error = httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_response)

    mock_post = AsyncMock(side_effect=http_error)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.post = mock_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client_with_url.get_app("nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_create_app_returns_app_dict(client_with_url):
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"result": {"app": {"id": "new-app-id", "name": "created-app"}}}

    mock_post = AsyncMock(return_value=fake_response)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.post = mock_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client_with_url.create_app({"name": "created-app", "region": "nyc"})

    assert result == {"id": "new-app-id", "name": "created-app"}


@pytest.mark.asyncio
async def test_list_apps_returns_empty_on_request_error(client_with_url):
    mock_post = AsyncMock(side_effect=httpx.RequestError("connection refused"))

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.post = mock_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client_with_url.list_apps()

    assert result == []


@pytest.mark.asyncio
async def test_create_app_returns_empty_on_http_error(client_with_url):
    mock_response = MagicMock()
    mock_response.status_code = 500

    http_error = httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_response)
    mock_post = AsyncMock(side_effect=http_error)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_async_client = AsyncMock()
        mock_async_client.post = mock_post
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await client_with_url.create_app({"name": "bad-app"})

    assert result == {}


@pytest.mark.asyncio
async def test_headers_include_bearer_token(client_with_url):
    headers = client_with_url._headers()
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Content-Type"] == "application/json"


def test_headers_no_auth_when_token_missing(client_no_url):
    headers = client_no_url._headers()
    assert "Authorization" not in headers
