"""Authentication and rate-limiting middleware for vibeDeploy gateway."""

import hmac
import logging
import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_PUBLIC_PATHS: frozenset[str] = frozenset(
    {
        "/",
        "/health",
        "/cost-estimate",
        "/api/cost-estimate",
        "/models",
        "/api/models",
    }
)

_PUBLIC_PREFIXES: tuple[str, ...] = ("/test/",)


def _get_api_key() -> str:
    for key in ("VIBEDEPLOY_API_KEY", "VIBEDEPLOY_OPS_TOKEN", "DASHBOARD_ADMIN_TOKEN"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _is_public_path(path: str) -> bool:
    if path in _PUBLIC_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


async def verify_api_key(
    request: Request,
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    path = request.url.path

    if _is_public_path(path):
        return None

    expected = _get_api_key()

    # Auth disabled when no key is configured (dev mode)
    if not expected:
        return None

    # SSE endpoints: fall back to query param (EventSource can't send headers)
    if not api_key and "/events" in path:
        api_key = request.query_params.get("api_key")

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="missing_api_key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not hmac.compare_digest(api_key, expected):
        logger.warning("Invalid API key from %s for %s", request.client.host if request.client else "unknown", path)
        raise HTTPException(status_code=403, detail="invalid_api_key")

    return api_key


class _RateLimitBucket:
    __slots__ = ("_requests",)

    def __init__(self) -> None:
        self._requests: list[float] = []

    def hit(self, now: float, window_seconds: int, max_requests: int) -> bool:
        cutoff = now - window_seconds
        self._requests = [t for t in self._requests if t > cutoff]
        if len(self._requests) >= max_requests:
            return False
        self._requests.append(now)
        return True

    def is_empty(self) -> bool:
        return len(self._requests) == 0


_rate_buckets: dict[str, _RateLimitBucket] = {}
_BUCKET_CLEANUP_INTERVAL = 300  # seconds
_last_bucket_cleanup = 0.0

_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "write": (10, 60),
    "read": (120, 60),
    "sse": (20, 60),
}

_WRITE_PATHS: frozenset[str] = frozenset(
    {
        "/run",
        "/api/run",
        "/resume",
        "/api/resume",
        "/brainstorm",
        "/api/brainstorm",
        "/zero-prompt/start",
        "/api/zero-prompt/start",
        "/zero-prompt/reset",
        "/api/zero-prompt/reset",
    }
)

_SSE_FRAGMENTS: tuple[str, ...] = ("/events", "/build/")


def _classify_rate_tier(path: str, method: str) -> str:
    if path in _WRITE_PATHS:
        return "write"
    for fragment in _SSE_FRAGMENTS:
        if fragment in path:
            return "sse"
    if method == "POST" and "/actions" in path:
        return "write"
    return "read"


def _cleanup_stale_buckets(now: float) -> None:
    global _last_bucket_cleanup
    if now - _last_bucket_cleanup < _BUCKET_CLEANUP_INTERVAL:
        return
    _last_bucket_cleanup = now
    stale = [k for k, b in _rate_buckets.items() if b.is_empty()]
    for k in stale:
        _rate_buckets.pop(k, None)


async def rate_limit_check(request: Request) -> None:
    path = request.url.path

    if _is_public_path(path):
        return

    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    tier = _classify_rate_tier(path, method)
    max_requests, window_seconds = _RATE_LIMITS[tier]
    bucket_key = f"{client_ip}:{tier}"
    now = time.monotonic()

    _cleanup_stale_buckets(now)

    if bucket_key not in _rate_buckets:
        _rate_buckets[bucket_key] = _RateLimitBucket()

    if not _rate_buckets[bucket_key].hit(now, window_seconds, max_requests):
        logger.warning("Rate limit exceeded: %s %s from %s (tier=%s)", method, path, client_ip, tier)
        raise HTTPException(
            status_code=429,
            detail="rate_limit_exceeded",
            headers={
                "Retry-After": str(window_seconds),
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Window": str(window_seconds),
            },
        )
