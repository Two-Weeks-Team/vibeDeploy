"""FastAPI gateway for the vibeDeploy web app.

Exposes the same HTTP interface the frontend expects:
  POST /run          → SSE stream of council events
  POST /brainstorm   → SSE stream of brainstorm events
  POST /resume       → SSE stream of resume events
  GET  /result/{id}  → meeting result JSON
  GET  /brainstorm/result/{id} → brainstorm result JSON
  GET  /health       → liveness check

Run: python -m agent.server
"""

import asyncio
import hmac
import json
import logging
import os
import re
import shutil
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from .cost import estimate_pipeline_cost
from .db.store import ResultStore
from .llm import get_runtime_model_config
from .model_capabilities import load_model_capability_report, selected_runtime_model
from .pipeline_runtime import build_brainstorm_result, build_meeting_result, stream_action_session
from .sse import NODE_EVENTS, format_sse
from .tools.digitalocean import list_apps as list_digitalocean_apps

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env.test")

logger = logging.getLogger(__name__)

_store: ResultStore | None = None

# ── Dashboard live tracking ──────────────────────────────────────────
_active_pipelines: dict[str, dict] = {}
_dashboard_queues: list[asyncio.Queue] = []
_DASHBOARD_SHOWCASE_TTL_SECONDS = 15
_DASHBOARD_SNAPSHOT_TTL_SECONDS = 4
_DASHBOARD_SOURCE_LIMIT = 200
_SHOWCASE_FAMILY_SUFFIXES = {"ai", "app", "api", "lite", "platform", "pro", "service", "site", "web"}
_dashboard_showcase_cache = {"expires_at": 0.0, "apps": []}
_dashboard_snapshot_cache = {"expires_at": 0.0, "meetings": [], "brainstorms": [], "filtered": False}
_dashboard_showcase_lock: asyncio.Lock | None = None
_dashboard_snapshot_lock: asyncio.Lock | None = None


def _register_pipeline(thread_id: str, pipeline_type: str, prompt: str):
    _active_pipelines[thread_id] = {
        "thread_id": thread_id,
        "type": pipeline_type,
        "phase": "starting",
        "started_at": time.time(),
        "prompt_preview": prompt[:120],
    }
    asyncio.ensure_future(_broadcast_active_pipelines())


def _deregister_pipeline(thread_id: str):
    _active_pipelines.pop(thread_id, None)
    asyncio.ensure_future(_broadcast_active_pipelines())


async def _broadcast_active_pipelines():
    await _broadcast_event(
        {
            "type": "active_pipelines",
            "pipelines": list(_active_pipelines.values()),
        }
    )


async def _broadcast_event(event_data: dict):
    dead: list[asyncio.Queue] = []
    for q in _dashboard_queues:
        try:
            q.put_nowait(event_data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _dashboard_queues.remove(q)


def _get_dashboard_showcase_lock() -> asyncio.Lock:
    global _dashboard_showcase_lock
    if _dashboard_showcase_lock is None:
        _dashboard_showcase_lock = asyncio.Lock()
    return _dashboard_showcase_lock


def _get_dashboard_snapshot_lock() -> asyncio.Lock:
    global _dashboard_snapshot_lock
    if _dashboard_snapshot_lock is None:
        _dashboard_snapshot_lock = asyncio.Lock()
    return _dashboard_snapshot_lock


def _normalize_repo_identifier(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized.startswith("https://github.com/"):
        normalized = normalized[len("https://github.com/") :]
    return normalized.removesuffix(".git").strip("/")


def _repo_basename(value: str) -> str:
    normalized = _normalize_repo_identifier(value)
    return normalized.rsplit("/", 1)[-1] if normalized else ""


def _normalize_live_url(value: str) -> str:
    return (value or "").strip().rstrip("/")


def _project_family(value: str) -> str:
    basename = _repo_basename(value)
    if not basename:
        return ""

    tokens = re.findall(r"[a-z0-9]+", basename)
    filtered: list[str] = []
    for token in tokens:
        if token.isdigit() or re.fullmatch(r"[0-9a-f]{6,}", token):
            continue
        filtered.append(token)

    while filtered and filtered[-1] in _SHOWCASE_FAMILY_SUFFIXES:
        filtered.pop()

    return "-".join(filtered)


def _extract_app_repo_candidates(spec: dict) -> set[str]:
    candidates: set[str] = set()
    for key in ("services", "workers", "jobs", "static_sites"):
        for component in spec.get(key, []) or []:
            github = component.get("github", {}) or {}
            repo = _normalize_repo_identifier(str(github.get("repo", "")))
            if repo:
                candidates.add(repo)
                candidates.add(_repo_basename(repo))

    name = _normalize_repo_identifier(str(spec.get("name", "")))
    if name:
        candidates.add(name)
        candidates.add(_repo_basename(name))
    return {candidate for candidate in candidates if candidate}


def _extract_primary_repo_url(spec: dict) -> str:
    for key in ("services", "workers", "jobs", "static_sites"):
        for component in spec.get(key, []) or []:
            github = component.get("github", {}) or {}
            repo = _normalize_repo_identifier(str(github.get("repo", "")))
            if repo and "/" in repo:
                return f"https://github.com/{repo}"
    return ""


def _showcase_app_from_inventory(name: str, live_url: str, repo_url: str) -> dict:
    repo_candidates = _extract_app_repo_candidates({"name": name, "services": [{"github": {"repo": repo_url}}]})
    family_candidates = {
        family
        for family in {_project_family(candidate) for candidate in repo_candidates | ({name} if name else set())}
        if family
    }
    return {
        "name": _repo_basename(name) or name,
        "live_url": _normalize_live_url(live_url),
        "repo_url": repo_url,
        "repo_candidates": repo_candidates,
        "family_candidates": family_candidates,
    }


async def _list_doctl_apps() -> list[dict]:
    if shutil.which("doctl") is None:
        return []

    try:
        proc = await asyncio.create_subprocess_exec(
            "doctl",
            "apps",
            "list",
            "-o",
            "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            return []
        payload = json.loads(stdout.decode("utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


async def _get_showcase_live_apps() -> list[dict]:
    now = time.time()
    if _dashboard_showcase_cache["expires_at"] > now:
        return _dashboard_showcase_cache["apps"]

    async with _get_dashboard_showcase_lock():
        now = time.time()
        if _dashboard_showcase_cache["expires_at"] > now:
            return _dashboard_showcase_cache["apps"]

        raw_apps = await list_digitalocean_apps(per_page=100)
        if not raw_apps:
            raw_apps = await _list_doctl_apps()

        showcase_apps: list[dict] = []
        for app in raw_apps:
            spec = app.get("spec", {}) or {}
            name = _repo_basename(str(spec.get("name", "")))
            live_url = _normalize_live_url(str(app.get("live_url") or app.get("default_ingress") or ""))
            phase = str((app.get("active_deployment") or {}).get("phase") or "").upper()
            repo_candidates = _extract_app_repo_candidates(spec)
            family_candidates = {
                family
                for family in {
                    _project_family(candidate) for candidate in repo_candidates | ({name} if name else set())
                }
                if family
            }

            if not live_url or "vibedeploy" in live_url:
                continue
            if name == "vibedeploy":
                continue
            if phase and phase != "ACTIVE":
                continue

            showcase_apps.append(
                {
                    "name": name,
                    "live_url": live_url,
                    "repo_url": _extract_primary_repo_url(spec),
                    "repo_candidates": repo_candidates,
                    "family_candidates": family_candidates,
                }
            )

        _dashboard_showcase_cache["expires_at"] = time.time() + _DASHBOARD_SHOWCASE_TTL_SECONDS
        _dashboard_showcase_cache["apps"] = showcase_apps
        return showcase_apps


def _meeting_match_score(meeting: dict, showcase_app: dict) -> int:
    deployment = meeting.get("deployment") or {}
    meeting_live_url = _normalize_live_url(str(deployment.get("liveUrl", "")))
    if meeting_live_url and meeting_live_url == showcase_app["live_url"]:
        return 400

    repo_identifier = _normalize_repo_identifier(str(deployment.get("repoUrl", "")))
    repo_basename = _repo_basename(repo_identifier)
    if {candidate for candidate in (repo_identifier, repo_basename) if candidate} & showcase_app["repo_candidates"]:
        return 300

    meeting_family = _project_family(repo_identifier or repo_basename)
    if meeting_family and meeting_family in showcase_app["family_candidates"]:
        return 100

    return 0


def _reconcile_showcase_meetings(meetings: list[dict], showcase_apps: list[dict]) -> list[dict] | None:
    if not showcase_apps:
        return None

    matches: dict[str, dict] = {}
    used_threads: set[str] = set()
    used_live_urls: set[str] = set()

    for min_score in (300, 100):
        for showcase_app in showcase_apps:
            if showcase_app["live_url"] in used_live_urls:
                continue

            best_match: dict | None = None
            best_score = 0
            for meeting in meetings:
                thread_id = str(meeting.get("thread_id", ""))
                if not thread_id or thread_id in used_threads:
                    continue

                score = _meeting_match_score(meeting, showcase_app)
                if score < min_score or score <= best_score:
                    continue

                best_match = meeting
                best_score = score

            if best_match is None:
                continue

            thread_id = str(best_match["thread_id"])
            matches[thread_id] = showcase_app
            used_threads.add(thread_id)
            used_live_urls.add(showcase_app["live_url"])

    if not matches:
        return None

    reconciled: list[dict] = []
    for meeting in meetings:
        showcase_app = matches.get(str(meeting.get("thread_id", "")))
        if not showcase_app:
            continue

        deployment = dict(meeting.get("deployment") or {})
        deployment["liveUrl"] = showcase_app["live_url"]
        if showcase_app["repo_url"]:
            deployment["repoUrl"] = showcase_app["repo_url"]
        deployment["status"] = "deployed"

        reconciled.append({**meeting, "deployment": deployment})

    return reconciled


def _meeting_store_payload(meeting: dict) -> dict:
    return {key: value for key, value in meeting.items() if key not in {"thread_id", "created_at"}}


def _ops_token() -> str:
    for key in ("VIBEDEPLOY_OPS_TOKEN", "DASHBOARD_ADMIN_TOKEN", "DIGITALOCEAN_INFERENCE_KEY"):
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _require_ops_token(token: str | None) -> None:
    expected = _ops_token()
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="forbidden")


def _test_api_enabled() -> bool:
    return os.getenv("VIBEDEPLOY_ENABLE_TEST_API", "").strip() == "1"


async def _get_dashboard_snapshot() -> tuple[list[dict], list[dict], bool]:
    now = time.time()
    if _dashboard_snapshot_cache["expires_at"] > now:
        return (
            _dashboard_snapshot_cache["meetings"],
            _dashboard_snapshot_cache["brainstorms"],
            bool(_dashboard_snapshot_cache["filtered"]),
        )

    async with _get_dashboard_snapshot_lock():
        now = time.time()
        if _dashboard_snapshot_cache["expires_at"] > now:
            return (
                _dashboard_snapshot_cache["meetings"],
                _dashboard_snapshot_cache["brainstorms"],
                bool(_dashboard_snapshot_cache["filtered"]),
            )

        meetings = await _store.list_meetings(limit=_DASHBOARD_SOURCE_LIMIT)
        brainstorms = await _store.list_brainstorms(limit=_DASHBOARD_SOURCE_LIMIT)
        filtered = False

        showcase_apps = await _get_showcase_live_apps()
        reconciled_meetings = _reconcile_showcase_meetings(meetings, showcase_apps)
        if reconciled_meetings is not None:
            meetings = reconciled_meetings
            selected_thread_ids = {str(meeting.get("thread_id", "")) for meeting in meetings}
            brainstorms = [item for item in brainstorms if str(item.get("thread_id", "")) in selected_thread_ids]
            filtered = True

        _dashboard_snapshot_cache["expires_at"] = time.time() + _DASHBOARD_SNAPSHOT_TTL_SECONDS
        _dashboard_snapshot_cache["meetings"] = meetings
        _dashboard_snapshot_cache["brainstorms"] = brainstorms
        _dashboard_snapshot_cache["filtered"] = filtered

        return meetings, brainstorms, filtered


def _invalidate_dashboard_snapshot_cache() -> None:
    _dashboard_snapshot_cache["expires_at"] = 0.0
    _dashboard_snapshot_cache["meetings"] = []
    _dashboard_snapshot_cache["brainstorms"] = []
    _dashboard_snapshot_cache["filtered"] = False


def _compute_dashboard_stats(meetings: list[dict], brainstorms: list[dict]) -> dict:
    total_meetings = len(meetings)
    total_brainstorms = len(brainstorms)
    go_count = sum(1 for item in meetings if item.get("verdict") == "GO")
    avg_score = round(sum(float(item.get("score") or 0) for item in meetings) / total_meetings, 1) if meetings else 0
    return {
        "total_meetings": total_meetings,
        "total_brainstorms": total_brainstorms,
        "avg_score": avg_score,
        "go_count": go_count,
        "nogo_count": total_meetings - go_count,
    }


async def _with_tracking(
    thread_id: str,
    pipeline_type: str,
    prompt: str,
    stream: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    """Wrap pipeline stream — tracks active state + broadcasts events to dashboard."""
    _register_pipeline(thread_id, pipeline_type, prompt)
    try:
        async for chunk in stream:
            for line in chunk.strip().split("\n"):
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if thread_id in _active_pipelines and "phase" in data:
                            _active_pipelines[thread_id]["phase"] = data["phase"]
                        await _broadcast_event({**data, "thread_id": thread_id})
                    except (json.JSONDecodeError, ValueError):
                        pass
            yield chunk
    finally:
        _deregister_pipeline(thread_id)


def _configured_adk_url() -> str:
    return os.getenv("VIBEDEPLOY_ADK_URL", "").strip().rstrip("/")


def _configured_adk_auth_token() -> str:
    return (
        os.getenv("VIBEDEPLOY_ADK_AUTH_TOKEN", "").strip()
        or os.getenv("GRADIENT_AGENT_ACCESS_KEY", "").strip()
        or os.getenv("DIGITALOCEAN_API_TOKEN", "").strip()
    )


def _configured_adk_auth_mode() -> str:
    if os.getenv("VIBEDEPLOY_ADK_AUTH_TOKEN", "").strip():
        return "endpoint_access_key"
    if os.getenv("GRADIENT_AGENT_ACCESS_KEY", "").strip():
        return "agent_access_key_alias"
    if os.getenv("DIGITALOCEAN_API_TOKEN", "").strip():
        return "personal_access_token"
    return "none"


def _legacy_error_event_name(action: str) -> str:
    return "brainstorm.error" if action == "brainstorm" else "council.error"


def _iter_sse_payloads(chunk: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event_name = ""
    data_payload = ""
    for line in chunk.splitlines():
        if line.startswith("event: "):
            event_name = line[7:]
        elif line.startswith("data: "):
            data_payload = line[6:]
        elif line == "" and event_name:
            try:
                events.append((event_name, json.loads(data_payload)))
            except (TypeError, ValueError):
                pass
            event_name = ""
            data_payload = ""
    if event_name and data_payload:
        try:
            events.append((event_name, json.loads(data_payload)))
        except (TypeError, ValueError):
            pass
    return events


async def _stream_remote_action(payload: dict) -> AsyncGenerator[str, None]:
    adk_url = _configured_adk_url()
    if not adk_url:
        raise RuntimeError("VIBEDEPLOY_ADK_URL is not configured")

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=30.0)) as client:
            async with client.stream(
                "POST",
                f"{adk_url}/run",
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                    **(
                        {"Authorization": f"Bearer {_configured_adk_auth_token()}"}
                        if _configured_adk_auth_token()
                        else {}
                    ),
                },
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise RuntimeError(
                        f"ADK returned {response.status_code}: {body.decode('utf-8', errors='replace')[:300]}"
                    )

                buffered_lines: list[str] = []
                async for line in response.aiter_lines():
                    if line == "":
                        if buffered_lines:
                            yield "".join(f"{item}\n" for item in buffered_lines) + "\n"
                            buffered_lines = []
                        continue
                    buffered_lines.append(line)

                if buffered_lines:
                    yield "".join(f"{item}\n" for item in buffered_lines) + "\n"
    except Exception as exc:
        action = str(payload.get("action") or "evaluate")
        error_payload = {
            "type": "session.error",
            "action": action,
            "thread_id": str(payload.get("thread_id") or "default"),
            "error": str(exc)[:500],
        }
        yield format_sse("session.error", error_payload)
        yield format_sse(
            _legacy_error_event_name(action),
            {
                "type": _legacy_error_event_name(action),
                "error": error_payload["error"],
            },
        )


async def _stream_action_gateway(payload: dict) -> AsyncGenerator[str, None]:
    upstream = _stream_remote_action(payload) if _configured_adk_url() else stream_action_session(payload)

    async for chunk in upstream:
        for event_name, data in _iter_sse_payloads(chunk):
            if event_name != "session.completed":
                continue
            thread_id = str(data.get("thread_id") or payload.get("thread_id") or "default")
            result = data.get("result")
            if data.get("result_type") == "brainstorm":
                await _store_brainstorm_result(thread_id, {"__prebuilt_result__": result})
            elif data.get("result_type") == "meeting":
                await _store_result(thread_id, {"__prebuilt_result__": result})
        yield chunk


def _request_to_action_payload(request: "RunRequest", *, action: str) -> dict:
    config = request.config or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    return {
        "action": action,
        "thread_id": str(configurable.get("thread_id") or request.thread_id or "default"),
        "prompt": request.prompt,
        "youtube_url": request.youtube_url,
        "reference_urls": request.reference_urls or [],
        "constraints": request.constraints,
        "selected_flagship": request.selected_flagship,
        "flagship_contract": request.flagship_contract or {},
        "skip_council": request.skip_council,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _store
    if os.environ.get("DATABASE_URL"):
        _store = ResultStore()
    else:
        db_path = os.environ.get("DB_PATH", str(_AGENT_DIR / "vibedeploy.db"))
        _store = ResultStore(db_path=db_path)
    yield
    await _store.close()
    _store = None


app = FastAPI(title="vibeDeploy Agent (local)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_NODE_EVENTS = NODE_EVENTS
_sse = format_sse
_AGENT_NODE_IDS = {
    "architect": "architect",
    "scout": "scout",
    "catalyst": "catalyst",
    "guardian": "guardian",
    "advocate": "advocate",
}
_AGENT_SCORE_AXES = {
    "architect": "technical_feasibility",
    "scout": "market_viability",
    "catalyst": "innovation_score",
    "guardian": "risk_profile",
    "advocate": "user_impact",
}
_SCORE_AXIS_NODE_IDS = {
    "technical_feasibility": "score_tech",
    "market_viability": "score_market",
    "innovation_score": "score_innovation",
    "risk_profile": "score_risk",
    "user_impact": "score_user",
}
_SCORE_AXIS_LABELS = {
    "technical_feasibility": "Tech Feasibility",
    "market_viability": "Market Viability",
    "innovation_score": "Innovation Score",
    "risk_profile": "Risk Profile",
    "user_impact": "User Impact",
}


async def _store_result(thread_id: str, state: dict):
    prebuilt = state.get("__prebuilt_result__")
    result = prebuilt if isinstance(prebuilt, dict) else build_meeting_result(state)
    await _store.save_meeting(thread_id, result)
    _invalidate_dashboard_snapshot_cache()


class RunRequest(BaseModel):
    prompt: str = ""
    config: dict | None = None
    thread_id: str = ""
    youtube_url: str = ""
    reference_urls: list[str] | None = None
    constraints: str = ""
    selected_flagship: str = ""
    flagship_contract: dict | None = None
    skip_council: bool = False


class ShowcaseAppInput(BaseModel):
    name: str
    live_url: str
    repo_url: str


class DashboardReconcileRequest(BaseModel):
    showcase_apps: list[ShowcaseAppInput]


async def _stream_pipeline(prompt: str, thread_id: str) -> AsyncGenerator[str, None]:
    payload = {
        "action": "evaluate",
        "thread_id": thread_id,
        "prompt": prompt,
    }
    async for chunk in _stream_action_gateway(payload):
        yield chunk


@app.post("/api/run")
@app.post("/run")
async def run_pipeline(request: RunRequest):
    from .guardrails import sanitize_input

    sanitized, valid, error, pii_found = sanitize_input(request.prompt)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    action_payload = _request_to_action_payload(request, action="evaluate")
    action_payload["prompt"] = sanitized
    thread_id = action_payload["thread_id"]

    return StreamingResponse(
        _with_tracking(thread_id, "evaluation", sanitized, _stream_action_gateway(action_payload)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class ResumeRequest(BaseModel):
    thread_id: str
    action: str = "proceed"


async def _stream_resume(thread_id: str, action: str) -> AsyncGenerator[str, None]:
    payload = {
        "action": "resume",
        "thread_id": thread_id,
        "constraints": action,
    }
    async for chunk in _stream_action_gateway(payload):
        yield chunk


@app.post("/api/resume")
@app.post("/resume")
async def resume_pipeline(request: ResumeRequest):
    return StreamingResponse(
        _with_tracking(
            request.thread_id,
            "evaluation",
            f"resume:{request.action}",
            _stream_action_gateway(
                {
                    "action": "resume",
                    "thread_id": request.thread_id,
                    "constraints": request.action,
                }
            ),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_brainstorm(prompt: str, thread_id: str) -> AsyncGenerator[str, None]:
    payload = {
        "action": "brainstorm",
        "thread_id": thread_id,
        "prompt": prompt,
    }
    async for chunk in _stream_action_gateway(payload):
        yield chunk


async def _store_brainstorm_result(thread_id: str, state: dict):
    prebuilt = state.get("__prebuilt_result__")
    result = prebuilt if isinstance(prebuilt, dict) else build_brainstorm_result(state)
    await _store.save_brainstorm(thread_id, result)
    _invalidate_dashboard_snapshot_cache()


@app.post("/api/brainstorm")
@app.post("/brainstorm")
async def brainstorm_pipeline(request: RunRequest):
    from .guardrails import sanitize_input

    sanitized, valid, error, pii_found = sanitize_input(request.prompt)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    action_payload = _request_to_action_payload(request, action="brainstorm")
    action_payload["prompt"] = sanitized
    thread_id = action_payload["thread_id"]

    return StreamingResponse(
        _with_tracking(thread_id, "brainstorm", sanitized, _stream_action_gateway(action_payload)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/brainstorm/result/{session_id}")
@app.get("/brainstorm/result/{session_id}")
async def get_brainstorm_result(session_id: str):
    result = await _store.get_brainstorm(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="not_found")
    return result


@app.get("/api/result/{meeting_id}")
@app.get("/result/{meeting_id}")
async def get_result(meeting_id: str):
    result = await _store.get_meeting(meeting_id)
    if result is None:
        raise HTTPException(status_code=404, detail="not_found")
    return result


@app.post("/api/ops/dashboard/reconcile")
async def reconcile_dashboard_results(
    request: DashboardReconcileRequest,
    x_vibedeploy_ops_token: str | None = Header(default=None),
):
    _require_ops_token(x_vibedeploy_ops_token)

    showcase_apps = [
        _showcase_app_from_inventory(item.name, item.live_url, item.repo_url)
        for item in request.showcase_apps
        if item.live_url.strip() and item.repo_url.strip()
    ]
    if not showcase_apps:
        raise HTTPException(status_code=400, detail="showcase_apps_required")

    meetings = await _store.list_meetings(limit=_DASHBOARD_SOURCE_LIMIT)
    reconciled = _reconcile_showcase_meetings(meetings, showcase_apps)
    if not reconciled:
        raise HTTPException(status_code=404, detail="no_matching_results")

    await _store.replace_meetings(
        [(str(meeting["thread_id"]), _meeting_store_payload(meeting)) for meeting in reconciled]
    )
    _invalidate_dashboard_snapshot_cache()

    return {
        "stored": len(reconciled),
        "thread_ids": [str(meeting["thread_id"]) for meeting in reconciled],
    }


@app.put("/test/result/{meeting_id}")
async def put_test_result(meeting_id: str, body: dict):
    if not _test_api_enabled():
        raise HTTPException(status_code=404, detail="not_found")
    await _store.save_meeting(meeting_id, body)
    _invalidate_dashboard_snapshot_cache()
    return {"stored": meeting_id}


@app.put("/test/brainstorm/{brainstorm_id}")
async def put_test_brainstorm(brainstorm_id: str, body: dict):
    if not _test_api_enabled():
        raise HTTPException(status_code=404, detail="not_found")
    await _store.save_brainstorm(brainstorm_id, body)
    _invalidate_dashboard_snapshot_cache()
    return {"stored": brainstorm_id}


@app.get("/health")
@app.get("/")
async def health():
    return {
        "status": "ok",
        "provider": "do-app-platform-gateway",
        "adk_url_configured": bool(_configured_adk_url()),
        "adk_auth_mode": _configured_adk_auth_mode(),
    }


@app.get("/api/cost-estimate")
@app.get("/cost-estimate")
async def cost_estimate():
    return estimate_pipeline_cost()


@app.get("/api/models")
@app.get("/models")
async def models():
    runtime_models = get_runtime_model_config()
    capability_report = load_model_capability_report()
    return {
        "models": runtime_models,
        "selected_runtime_model": selected_runtime_model(),
        "capabilities": capability_report,
        "vendors": {
            "anthropic": [k for k, v in runtime_models.items() if v.startswith("anthropic-")],
            "openai": [k for k, v in runtime_models.items() if v.startswith("openai-")],
        },
    }


@app.get("/dashboard/stats")
@app.get("/stats")
async def dashboard_stats():
    meetings, brainstorms, filtered = await _get_dashboard_snapshot()
    if not filtered:
        return await _store.get_stats()
    return _compute_dashboard_stats(meetings, brainstorms)


@app.get("/dashboard/results")
@app.get("/results")
async def dashboard_results():
    meetings, _brainstorms, _filtered = await _get_dashboard_snapshot()
    return meetings[:50]


@app.get("/dashboard/brainstorms")
@app.get("/brainstorms")
async def dashboard_brainstorms():
    _meetings, brainstorms, _filtered = await _get_dashboard_snapshot()
    return brainstorms[:50]


@app.get("/dashboard/deployments")
@app.get("/deployments")
async def dashboard_deployments():
    meetings, _brainstorms, _filtered = await _get_dashboard_snapshot()
    deployed = []
    for m in meetings[:100]:
        dep = m.get("deployment")
        live_url = _normalize_live_url(str((dep or {}).get("liveUrl", "")))
        if dep and live_url and "vibedeploy" not in live_url:
            deployed.append(
                {
                    "thread_id": m["thread_id"],
                    "score": m.get("score", 0),
                    "verdict": m.get("verdict", ""),
                    "input_prompt": m.get("input_prompt", ""),
                    "idea_summary": m.get("idea_summary", ""),
                    "deployment": dep,
                    "created_at": m.get("created_at", ""),
                }
            )
    return deployed


@app.get("/dashboard/active")
@app.get("/active")
async def dashboard_active():
    return list(_active_pipelines.values())


@app.get("/dashboard/events")
@app.get("/events")
async def dashboard_events():
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _dashboard_queues.append(queue)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            yield _sse(
                "active_pipelines",
                {
                    "type": "active_pipelines",
                    "pipelines": list(_active_pipelines.values()),
                },
            )
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    yield _sse(event.get("type", "update"), event)
                except asyncio.TimeoutError:
                    yield _sse("heartbeat", {"type": "heartbeat"})
        except asyncio.CancelledError:
            pass
        finally:
            if queue in _dashboard_queues:
                _dashboard_queues.remove(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/dashboard/evaluations")
@app.get("/evaluations")
async def dashboard_evaluations():
    from .evaluations.runner import get_latest_summary

    summary = get_latest_summary()
    if summary is None:
        return {"status": "no_evaluation_run", "total": 0}
    return summary.model_dump()


_zp_orchestrator = None


def _get_zp_orchestrator():
    global _zp_orchestrator
    if _zp_orchestrator is None:
        from .zero_prompt.orchestrator import StreamingOrchestrator as _SO

        _zp_orchestrator = _SO()
    return _zp_orchestrator


class ZPStartRequest(BaseModel):
    goal: int = 10


class ZPActionRequest(BaseModel):
    action: str
    card_id: str = ""
    success: bool | None = None
    thread_id: str | None = None


@app.post("/api/zero-prompt/start")
@app.post("/zero-prompt/start")
async def zero_prompt_start(request: ZPStartRequest):
    import asyncio

    from .sse import format_sse as _fmt
    from .zero_prompt.events import ZP_SESSION_START

    orch = _get_zp_orchestrator()
    session, start_event = orch.create_session(goal=request.goal)
    session_id = session.session_id

    async def event_stream() -> AsyncGenerator[str, None]:
        yield _fmt(ZP_SESSION_START, start_event)
        yield _fmt("zp.discovery.start", {"type": "zp.discovery.start", "message": "Searching for trending videos..."})

        videos: list[tuple[str, str, str]] = []

        try:
            from .zero_prompt.discovery import YouTubeDiscovery

            discovery = YouTubeDiscovery()
            candidates = await discovery.fetch_candidate_pool(
                max_results=30, min_views=5000, min_likes=100, min_engagement_rate=0.01
            )
            videos = [(c.video_id, c.title, c.description) for c in candidates]
            logger.info("[ZP] YouTube API discovery: %d videos", len(videos))
        except Exception as exc:
            logger.warning("[ZP] YouTube API failed: %s", str(exc)[:200])

        if not videos:
            yield _fmt(
                "zp.discovery.grounding",
                {"type": "zp.discovery.grounding", "message": "Using Gemini AI to discover trending videos..."},
            )
            try:
                from .zero_prompt.grounding_discovery import discover_videos_via_grounding

                videos = await discover_videos_via_grounding(max_results=20)
                logger.info("[ZP] Gemini grounding discovery: %d videos", len(videos))
            except Exception as exc:
                logger.warning("[ZP] Gemini grounding failed: %s", str(exc)[:200])

        if not videos:
            fallback_topics = [
                "AI fitness tracker app",
                "Recipe sharing with AI recommendations",
                "Smart budget expense tracker",
                "Language learning spaced repetition",
                "Pet health monitoring symptom checker",
                "Project management remote teams",
                "AI resume builder job matching",
                "Meditation guided sessions tracker",
                "Restaurant queue management AI",
                "Sustainable grocery delivery optimizer",
                "AI flashcard study assistant",
                "Social media sentiment dashboard",
                "AR interior design visualizer",
                "Code review automation tool",
                "Handmade crafts marketplace",
            ]
            videos = [(f"fallback-{i}", topic, topic) for i, topic in enumerate(fallback_topics)]
            logger.info("[ZP] Using hardcoded fallback topics")

        video_idx = 0
        while orch.should_continue_exploring(session_id):
            if video_idx >= len(videos):
                break
            vid_id, vid_title, vid_desc = videos[video_idx]
            video_idx += 1

            step_events = await orch.exploration_step(
                session_id, vid_id, video_title=vid_title, video_description=vid_desc
            )
            for evt in step_events:
                yield _fmt(evt.get("type", "zp.step"), evt)
            await asyncio.sleep(0.05)

        session = orch.get_session(session_id)
        if session is not None:
            session.remaining_videos = [[v[0], v[1], v[2]] for v in videos[video_idx:]]

        yield _fmt("zp.session.complete", {"session_id": session_id, "type": "zp.session.complete"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/api/zero-prompt/active")
@app.get("/zero-prompt/active")
async def zero_prompt_active():
    orch = _get_zp_orchestrator()
    sessions = [s.model_dump() for s in orch._sessions.values()]
    return {"sessions": sessions, "count": len(sessions)}


@app.get("/api/zero-prompt/{session_id}")
@app.get("/zero-prompt/{session_id}")
async def zero_prompt_get_session(session_id: str):
    orch = _get_zp_orchestrator()
    session = orch.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return session.model_dump()


@app.post("/api/zero-prompt/{session_id}/actions")
@app.post("/zero-prompt/{session_id}/actions")
async def zero_prompt_action(session_id: str, request: ZPActionRequest):
    orch = _get_zp_orchestrator()
    session = orch.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_not_found")

    action = request.action
    card_id = request.card_id

    if action == "queue_build":
        result = orch.queue_build(session_id, card_id)
        asyncio.create_task(_trigger_zp_build(orch, session_id, card_id))
        if orch.should_continue_exploring(session_id):
            asyncio.create_task(_resume_exploration(orch, session_id))
    elif action == "pass_card":
        result = orch.pass_card(session_id, card_id)
        if orch.should_continue_exploring(session_id):
            asyncio.create_task(_resume_exploration(orch, session_id))
    elif action == "delete_card":
        result = orch.delete_card(session_id, card_id)
    elif action == "pause":
        result = orch.pause(session_id)
    elif action == "resume":
        result = orch.resume(session_id)
    elif action == "start_next_build":
        built_card = orch.start_next_build(session_id)
        result = {"type": "zp.build.started", "card_id": built_card} if built_card else {"type": "zp.build.empty"}
    elif action == "finish_build":
        result = orch.finish_build(session_id, card_id, success=request.success or False, thread_id=request.thread_id)
    else:
        raise HTTPException(status_code=400, detail="unknown_action")

    if result.get("type") == "zp.action.error":
        raise HTTPException(status_code=422, detail=result["error"])

    return result


async def _trigger_zp_build(orch, session_id: str, card_id: str) -> None:
    try:
        session = orch.get_session(session_id)
        if session is None:
            return
        card = next((c for c in session.cards if c.card_id == card_id), None)
        if card is None:
            return

        card.status = "building"
        idea_title = card.title or card.video_id

        build_prompt = f"Build a web app: {idea_title}."
        if card.domain and card.domain != "unknown":
            build_prompt += f" Domain: {card.domain}."
        if card.reason:
            build_prompt += f" Validation: {card.reason}"
        build_prompt += (
            " Create a complete Next.js frontend with Tailwind CSS"
            " and a FastAPI backend with health endpoint."
            " Include realistic seed data and a clean dashboard UI."
        )

        from .pipeline_runtime import stream_action_session

        action_payload = {
            "action": "evaluate",
            "thread_id": f"zp-{card_id}",
            "prompt": build_prompt,
            "skip_council": True,
        }
        async for _chunk in stream_action_session(action_payload):
            pass

        card.status = "deployed"
        card.thread_id = f"zp-{card_id}"
        logger.info("[ZP] Build completed for card %s: %s", card_id, idea_title)
    except Exception:
        logger.exception("[ZP] Build failed for card %s", card_id)
        session = orch.get_session(session_id)
        if session:
            card = next((c for c in session.cards if c.card_id == card_id), None)
            if card:
                card.status = "build_failed"


async def _resume_exploration(orch, session_id: str) -> None:
    try:
        session = orch.get_session(session_id)
        if session is None or not session.remaining_videos:
            return

        while orch.should_continue_exploring(session_id) and session.remaining_videos:
            vid = session.remaining_videos.pop(0)
            vid_id, vid_title, vid_desc = vid[0], vid[1], vid[2] if len(vid) > 2 else ""
            await orch.exploration_step(session_id, vid_id, video_title=vid_title, video_description=vid_desc)
            await asyncio.sleep(0.05)

        logger.info("[ZP] Exploration resumed for session %s", session_id)
    except Exception:
        logger.exception("[ZP] Exploration resume failed for session %s", session_id)


if __name__ == "__main__":
    uvicorn.run(
        "agent.server:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info",
    )
