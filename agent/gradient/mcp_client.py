import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0


class MCPClient:
    def __init__(self) -> None:
        self._url: str = os.environ.get("DO_MCP_SERVER_URL", "").rstrip("/")
        self._token: str = os.environ.get("DIGITALOCEAN_API_TOKEN", "")

    def is_available(self) -> bool:
        return bool(self._url)

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {"name": tool_name, "arguments": arguments or {}}
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            response = await client.post(
                f"{self._url}/v1/tools/call",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            return body.get("result", body)

    async def list_apps(self) -> list[dict]:
        if not self.is_available():
            return []

        try:
            result = await self._call_tool("apps_list")
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("apps", [])
            return []
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("list_apps failed: %s", exc)
            return []

    async def get_app(self, app_id: str) -> dict | None:
        if not self.is_available():
            return None

        try:
            result = await self._call_tool("apps_get", {"app_id": app_id})
            if isinstance(result, dict):
                return result.get("app", result) or None
            return None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.warning("get_app(%s) failed: %s", app_id, exc)
            return None
        except httpx.RequestError as exc:
            logger.warning("get_app(%s) failed: %s", app_id, exc)
            return None

    async def create_app(self, spec: dict) -> dict:
        if not self.is_available():
            return {}

        try:
            result = await self._call_tool("apps_create", {"spec": spec})
            if isinstance(result, dict):
                return result.get("app", result)
            return {}
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("create_app failed: %s", exc)
            return {}
