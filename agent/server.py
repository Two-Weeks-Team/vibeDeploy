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
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import JSONResponse, StreamingResponse

from .cost import estimate_pipeline_cost
from .db.store import ResultStore
from .llm import get_runtime_model_config
from .model_capabilities import load_model_capability_report, selected_runtime_model
from .pipeline_runtime import build_brainstorm_result, build_meeting_result, stream_action_session
from .sse import NODE_EVENTS, format_sse
from .tools.digitalocean import list_apps as list_digitalocean_apps
from .zero_prompt.event_bus import push_zp_event, register_zp_client, unregister_zp_client

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env.test")

logger = logging.getLogger(__name__)

_store: ResultStore | None = None

# ── Dashboard live tracking ──────────────────────────────────────────
_active_pipelines: dict[str, dict] = {}
_zp_build_subscribers: dict[str, list[asyncio.Queue]] = {}
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
            deployment = dict(meeting.get("deployment") or {})
            status = str(deployment.get("status") or "").strip().lower()
            local_url = str(deployment.get("localUrl") or deployment.get("local_url") or "").strip()
            if status in {"local_running", "local_error"} or local_url:
                reconciled.append(meeting)
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
        try:
            from .db.zp_store import ensure_tables

            await ensure_tables()
        except Exception:
            logger.warning("[ZP] Could not create ZP tables — DB may not be ready yet")
        try:
            orch = _get_zp_orchestrator()
            loaded = await orch.load_sessions_from_db()
            if loaded:
                logger.info("[ZP] Restored %d session(s) from DB on startup", loaded)
        except Exception:
            logger.warning("[ZP] Could not restore ZP sessions from DB on startup")
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
async def dashboard_results(limit: int = 50):
    meetings, _brainstorms, _filtered = await _get_dashboard_snapshot()
    safe_limit = max(1, min(limit, 200))
    return meetings[:safe_limit]


@app.get("/dashboard/brainstorms")
@app.get("/brainstorms")
async def dashboard_brainstorms(limit: int = 50):
    _meetings, brainstorms, _filtered = await _get_dashboard_snapshot()
    safe_limit = max(1, min(limit, 200))
    return brainstorms[:safe_limit]


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


@app.get("/api/zero-prompt/dashboard")
@app.get("/zero-prompt/dashboard")
async def zp_dashboard():
    try:
        from .db.zp_store import get_dashboard

        return await get_dashboard()
    except Exception:
        return {"session_id": None, "status": "idle", "cards": []}


@app.get("/api/zero-prompt/events")
@app.get("/zero-prompt/events")
async def zp_events(request: Request):
    client_id = str(uuid.uuid4())
    session_id = request.query_params.get("session_id")
    q: asyncio.Queue = register_zp_client(client_id, session_id)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            try:
                from .db import zp_store as _zps

                if session_id:
                    snapshot = await _zps.get_session(session_id)
                    if snapshot:
                        yield f"data: {json.dumps({'type': 'snapshot', **snapshot})}\n\n"
                else:
                    dashboard = await _zps.get_dashboard()
                    yield f"data: {json.dumps({'type': 'snapshot', **dashboard})}\n\n"
            except Exception:
                pass

            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            unregister_zp_client(client_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


_zp_orchestrator = None
_zp_pipeline_tasks: dict[str, asyncio.Task[None]] = {}


def _get_zp_orchestrator():
    global _zp_orchestrator
    if _zp_orchestrator is None:
        from .zero_prompt.orchestrator import StreamingOrchestrator as _SO

        _zp_orchestrator = _SO()
    return _zp_orchestrator


class ZPStartRequest(BaseModel):
    goal: int = 5


class ZPActionRequest(BaseModel):
    action: str
    card_id: str = ""
    video_id: str = ""
    title: str = ""
    success: bool | None = None
    thread_id: str | None = None


_ZP_FALLBACK_TOPICS = [
    "AI fitness tracker app",
    "Recipe sharing with AI recommendations",
    "Smart budget expense tracker",
    "Language learning spaced repetition",
    "Pet health monitoring symptom checker",
    "Project management for remote teams",
    "AI resume builder with job matching",
    "Meditation and sleep tracker",
    "Restaurant queue management AI",
    "Sustainable grocery delivery optimizer",
    "AI flashcard study assistant",
    "Social media sentiment dashboard",
    "AR interior design visualizer",
    "Code review automation tool",
    "Handmade crafts marketplace",
]

_ZP_EXPLORING_LIMIT = 5
_ZP_GO_READY_LIMIT = 5
_ZP_REJECTED_LIMIT = 5
_ZP_MAX_ROUNDS = 5


def _should_launch_zp_pipeline_background_task() -> bool:
    if not _test_api_enabled():
        return True
    return not bool(os.getenv("PYTEST_CURRENT_TEST"))


def _launch_zp_pipeline(orch, session_id: str, goal: int) -> None:
    existing = _zp_pipeline_tasks.get(session_id)
    if existing and not existing.done():
        return

    task = asyncio.create_task(_run_zp_pipeline(orch, session_id, goal))
    _zp_pipeline_tasks[session_id] = task

    def _cleanup(done_task: asyncio.Task[None]) -> None:
        if _zp_pipeline_tasks.get(session_id) is done_task:
            _zp_pipeline_tasks.pop(session_id, None)

    task.add_done_callback(_cleanup)


async def _discover_videos(session_id: str) -> list[tuple[str, str, str]]:
    try:
        from .zero_prompt.discovery import YouTubeDiscovery

        discovery = YouTubeDiscovery()
        candidates = await discovery.fetch_candidate_pool(
            max_results=30, min_views=5000, min_likes=100, min_engagement_rate=0.01
        )
        videos = [(c.video_id, c.title, c.description) for c in candidates]
        if videos:
            logger.info("[ZP] YouTube API discovery: %d videos", len(videos))
            return videos
    except Exception as exc:
        logger.warning("[ZP] YouTube API failed: %s", str(exc)[:200])

    push_zp_event(
        {
            "type": "zp.discovery.grounding",
            "message": "Using Gemini AI to discover trending videos...",
            "session_id": session_id,
        }
    )
    try:
        from .zero_prompt.grounding_discovery import discover_videos_via_grounding

        videos = await discover_videos_via_grounding(max_results=20)
        if videos:
            logger.info("[ZP] Gemini grounding discovery: %d videos", len(videos))
            return videos
    except Exception as exc:
        logger.warning("[ZP] Gemini grounding failed: %s", str(exc)[:200])

    logger.info("[ZP] Using hardcoded fallback topics")
    return [(f"fallback-{i}", topic, topic) for i, topic in enumerate(_ZP_FALLBACK_TOPICS)]


def _count_go_cards(session) -> int:
    return sum(1 for c in session.cards if c.status == "go_ready")


def _count_exploring_cards(session) -> int:
    return sum(1 for c in session.cards if c.status == "analyzing")


def _count_rejected_cards(session) -> int:
    rejected = {"nogo", "passed", "build_failed"}
    return sum(1 for c in session.cards if c.status in rejected)


async def _set_zp_session_status(orch, session_id: str, status: str) -> None:
    session = await orch.ensure_session(session_id)
    if session is not None:
        session.status = status
    try:
        from .db import zp_store as _zps

        await _zps.update_session_status(session_id, status=status)
    except Exception:
        logger.exception("[ZP] Failed to persist status=%s for session %s", status, session_id)


async def _maybe_resume_zp_pipeline(orch, session_id: str) -> None:
    if not _should_launch_zp_pipeline_background_task():
        return

    session = await orch.ensure_session(session_id)
    if session is None or session.status == "completed":
        return

    if _count_go_cards(session) >= session.goal_go_cards:
        return
    if _count_rejected_cards(session) >= _ZP_REJECTED_LIMIT:
        return
    if _count_exploring_cards(session) >= _ZP_EXPLORING_LIMIT:
        return

    if session.status != "exploring":
        await _set_zp_session_status(orch, session_id, "exploring")
        push_zp_event({"type": "zp.session.resume", "session_id": session_id})

    _launch_zp_pipeline(orch, session_id, session.goal_go_cards)


async def _run_zp_pipeline(orch, session_id: str, goal: int) -> None:
    final_status = "completed"
    final_event = {"type": "zp.session.complete", "session_id": session_id, "reason": "max_rounds_reached"}
    try:
        session = await orch.ensure_session(session_id)
        seen_video_ids: set[str] = {card.video_id for card in session.cards} if session else set()
        round_num = 0

        while round_num < _ZP_MAX_ROUNDS:
            session = await orch.ensure_session(session_id)
            if session and _count_go_cards(session) >= goal:
                logger.info("[ZP] Goal reached (%d GO cards) for session %s", goal, session_id)
                final_status = "paused"
                final_event = {
                    "type": "zp.session.pause",
                    "reason": "goal_reached",
                    "go_ready_cards": _count_go_cards(session),
                    "session_id": session_id,
                }
                break
            if session and _count_rejected_cards(session) >= _ZP_REJECTED_LIMIT:
                logger.info("[ZP] Rejected cap reached (%d cards) for session %s", _ZP_REJECTED_LIMIT, session_id)
                final_status = "paused"
                final_event = {
                    "type": "zp.session.pause",
                    "reason": "rejected_cap_reached",
                    "rejected_cards": _count_rejected_cards(session),
                    "session_id": session_id,
                }
                break

            available_slots = _ZP_EXPLORING_LIMIT
            if session:
                available_slots = max(0, _ZP_EXPLORING_LIMIT - _count_exploring_cards(session))
            if available_slots <= 0:
                logger.info(
                    "[ZP] Pending card limit reached (%d), stopping registration for session %s",
                    _ZP_EXPLORING_LIMIT,
                    session_id,
                )
                final_status = "paused"
                final_event = {
                    "type": "zp.session.pause",
                    "reason": "exploring_cap_reached",
                    "exploring_cards": _count_exploring_cards(session) if session else 0,
                    "session_id": session_id,
                }
                break

            round_num += 1
            push_zp_event(
                {
                    "type": "zp.discovery.start",
                    "message": f"Searching for trending videos (round {round_num})...",
                    "session_id": session_id,
                }
            )
            videos = await _discover_videos(session_id)

            new_videos = [(vid_id, title, desc) for vid_id, title, desc in videos if vid_id not in seen_video_ids]
            if not new_videos:
                logger.info("[ZP] No new videos found in round %d, stopping", round_num)
                final_status = "completed"
                final_event = {
                    "type": "zp.session.complete",
                    "reason": "no_new_videos",
                    "rounds": round_num,
                    "session_id": session_id,
                }
                break

            batch = new_videos[:available_slots]
            for vid_id, title, desc in batch:
                seen_video_ids.add(vid_id)
                await orch.register_card(session_id, vid_id, title)
                push_zp_event(
                    {"type": "zp.card.registered", "video_id": vid_id, "title": title, "session_id": session_id}
                )

            push_zp_event({"type": "zp.exploration.started", "total_videos": len(batch), "session_id": session_id})
            logger.info("[ZP] Round %d: analyzing %d videos for session %s", round_num, len(batch), session_id)

            for vid_id, title, desc in batch:
                step_events = await orch.exploration_step(session_id, vid_id, video_title=title, video_description=desc)
                for evt in step_events:
                    push_zp_event(evt)
                await _trigger_pending_builds(orch, session_id)

                session = await orch.ensure_session(session_id)
                if session and _count_go_cards(session) >= goal:
                    logger.info("[ZP] Goal reached mid-round (%d GO cards)", goal)
                    final_status = "paused"
                    final_event = {
                        "type": "zp.session.pause",
                        "reason": "goal_reached",
                        "go_ready_cards": _count_go_cards(session),
                        "session_id": session_id,
                    }
                    break
                if session and _count_rejected_cards(session) >= _ZP_REJECTED_LIMIT:
                    logger.info("[ZP] Rejected cap reached mid-round for session %s", session_id)
                    final_status = "paused"
                    final_event = {
                        "type": "zp.session.pause",
                        "reason": "rejected_cap_reached",
                        "rejected_cards": _count_rejected_cards(session),
                        "session_id": session_id,
                    }
                    break

        logger.info("[ZP] Pipeline complete for session %s", session_id)
    except Exception:
        logger.exception("[ZP] Pipeline failed for session %s", session_id)
        final_status = "paused"
        final_event = {"type": "zp.session.pause", "reason": "pipeline_error", "session_id": session_id}
    finally:
        await _set_zp_session_status(orch, session_id, final_status)
        push_zp_event(final_event)


@app.post("/api/zero-prompt/start")
@app.post("/zero-prompt/start")
async def zero_prompt_start(request: ZPStartRequest):
    orch = _get_zp_orchestrator()
    goal = max(1, min(request.goal or _ZP_GO_READY_LIMIT, _ZP_GO_READY_LIMIT))
    session, _start_event = orch.create_session(goal=goal)
    session_id = session.session_id

    if _should_launch_zp_pipeline_background_task():
        _launch_zp_pipeline(orch, session_id, goal)
    push_zp_event(
        {"type": "zp.session.start", "session_id": session_id, "goal_go_cards": goal, "session_status": session.status}
    )
    push_zp_event({"type": "zp.pipeline.started", "session_id": session_id, "goal": goal})

    return JSONResponse(
        {
            "session_id": session_id,
            "status": session.status,
            "goal_go_cards": goal,
            "cards": [],
            "build_queue": [],
            "active_build": None,
        }
    )


@app.post("/api/zero-prompt/reset")
@app.post("/zero-prompt/reset")
async def zero_prompt_reset():
    from .db import zp_store as _zps

    dashboard = await _zps.get_dashboard()
    if dashboard.get("session_id"):
        await _zps.reset_session(dashboard["session_id"])
    orch = _get_zp_orchestrator()
    orch._sessions.clear()
    orch._build_queues.clear()
    return {"type": "zp.reset", "deleted_session": dashboard.get("session_id")}


@app.get("/api/zero-prompt/active")
@app.get("/zero-prompt/active")
async def zero_prompt_active():
    orch = _get_zp_orchestrator()
    if not orch._sessions:
        await orch.load_sessions_from_db()
    sessions = [s.model_dump() for s in orch._sessions.values()]
    return {"sessions": sessions, "count": len(sessions)}


@app.get("/api/zero-prompt/{session_id}")
@app.get("/zero-prompt/{session_id}")
async def zero_prompt_get_session(session_id: str):
    orch = _get_zp_orchestrator()
    session = await orch.ensure_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return session.model_dump()


@app.post("/api/zero-prompt/{session_id}/actions")
@app.post("/zero-prompt/{session_id}/actions")
async def zero_prompt_action(session_id: str, request: ZPActionRequest):
    orch = _get_zp_orchestrator()
    session = await orch.ensure_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    action = request.action
    card_id = request.card_id

    if action == "delete_card":
        result = orch.delete_card(session_id, card_id)
    elif action == "pass_card":
        result = orch.pass_card(session_id, card_id)
    elif action == "add_video":
        video_id = request.video_id or card_id
        title = request.title or video_id
        new_card_id = await orch.register_card(session_id, video_id, title)
        asyncio.create_task(_analyze_single(orch, session_id, video_id, title))
        result = {"type": "zp.action.add_video", "card_id": new_card_id, "video_id": video_id}
    elif action == "force_go":
        from .db import zp_store as _zps

        await _zps.update_card(card_id, status="go_ready", score=75, build_step="")
        session = await orch.ensure_session(session_id)
        if session:
            for card in session.cards:
                if card.card_id == card_id:
                    card.status = "go_ready"
                    card.score = 75
                    card.build_step = ""
                    card.build_queue = []
                    break
            if card_id in session.build_queue:
                session.build_queue.remove(card_id)
        push_zp_event({"type": "card.update", "card_id": card_id, "status": "go_ready", "session_id": session_id})
        result = {"type": "zp.action.force_go", "card_id": card_id}
    elif action == "queue_build":
        result = orch.queue_build(session_id, card_id)
        asyncio.create_task(_trigger_zp_build(orch, session_id, card_id))
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

    if action in {"queue_build", "pass_card", "delete_card", "force_go", "resume"}:
        asyncio.create_task(_maybe_resume_zp_pipeline(orch, session_id))

    return result


def _parse_sse_chunk(chunk: str) -> dict | None:
    """Parse an SSE chunk string into event data dict."""
    if not isinstance(chunk, str):
        return None
    for line in chunk.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except (json.JSONDecodeError, TypeError):
                pass
    return None


async def _trigger_pending_builds(orch, session_id: str) -> None:
    session = orch.get_session(session_id)
    if not session or not session.build_queue:
        return
    if any(c.status == "building" for c in session.cards):
        return
    for card_id in list(session.build_queue):
        card = next((c for c in session.cards if c.card_id == card_id), None)
        if card and card.status == "build_queued":
            asyncio.create_task(_trigger_zp_build(orch, session_id, card_id))
            break


async def _analyze_single(orch, session_id: str, video_id: str, title: str) -> None:
    try:
        step_events = await orch.exploration_step(session_id, video_id, video_title=title, video_description=title)
        for evt in step_events:
            push_zp_event(evt)
        await _trigger_pending_builds(orch, session_id)
    except Exception:
        logger.exception("[ZP] Analysis failed for video %s", video_id)


async def _trigger_zp_build(orch, session_id: str, card_id: str) -> None:
    from .db import zp_store as _zp_store

    try:
        session = await orch.ensure_session(session_id)
        if session is None:
            return
        card = next((c for c in session.cards if c.card_id == card_id), None)
        if card is None:
            return

        card.status = "building"
        card.build_step = "code_gen"
        card.build_events = []
        idea_title = card.title or card.video_id

        try:
            await _zp_store.update_card(card_id, status="building", build_step="code_gen")
            push_zp_event({"type": "card.update", "card_id": card_id, "status": "building", "session_id": session_id})
        except Exception:
            pass

        captured_live_url = ""
        captured_repo_url = ""

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
        async for chunk in stream_action_session(action_payload):
            event_data = _parse_sse_chunk(chunk)
            if event_data:
                card.build_events.append(event_data)
                if "phase" in event_data:
                    card.build_phase = event_data["phase"]
                if "node" in event_data or "stage" in event_data:
                    card.build_node = event_data.get("node", event_data.get("stage", ""))
                phase_val = event_data.get("phase", "")
                if "code_gen" in phase_val or "code_generator" in phase_val:
                    card.build_step = "code_gen"
                elif "code_eval" in phase_val or "build_valid" in phase_val:
                    card.build_step = "validate"
                elif "deploy" in phase_val:
                    card.build_step = "deploy"
                for url_key in ("liveUrl", "live_url", "default_ingress"):
                    if event_data.get(url_key):
                        captured_live_url = str(event_data[url_key])
                for url_key in ("repoUrl", "repo_url", "github_url", "github_repo", "repo"):
                    if event_data.get(url_key):
                        captured_repo_url = str(event_data[url_key])
                try:
                    await _zp_store.update_card(card_id, build_step=card.build_step)
                    push_zp_event(
                        {
                            "type": "card.build_step",
                            "card_id": card_id,
                            "build_step": card.build_step,
                            "session_id": session_id,
                        }
                    )
                except Exception:
                    pass
                if captured_live_url and card.status != "deployed":
                    card.build_step = "done"
                    card.status = "deployed"
                    card.live_url = captured_live_url
                    card.repo_url = captured_repo_url
                    card.thread_id = f"zp-{card_id}"
                    try:
                        await _zp_store.update_card(
                            card_id,
                            status="deployed",
                            build_step="done",
                            thread_id=card.thread_id,
                            live_url=captured_live_url,
                            repo_url=captured_repo_url,
                        )
                        push_zp_event(
                            {
                                "type": "card.update",
                                "card_id": card_id,
                                "status": "deployed",
                                "title": card.title,
                                "session_id": session_id,
                            }
                        )
                        logger.info(
                            "[ZP] Card %s deployed mid-stream: url=%s repo=%s",
                            card_id,
                            captured_live_url,
                            captured_repo_url,
                        )
                    except Exception:
                        pass
                subscriber_key = f"{session_id}:{card_id}"
                for queue in _zp_build_subscribers.get(subscriber_key, []):
                    try:
                        queue.put_nowait(event_data)
                    except asyncio.QueueFull:
                        pass

        card.build_step = "done"
        card.status = "deployed"
        thread_id = f"zp-{card_id}"
        card.thread_id = thread_id

        live_url = ""
        repo_url = ""
        try:
            result = await _store.get_meeting(thread_id) if _store else None
            if result and isinstance(result, dict):
                deploy = result.get("deployment", {})
                if isinstance(deploy, dict):
                    live_url = deploy.get("liveUrl", "") or deploy.get("live_url", "")
                    repo_url = deploy.get("repoUrl", "") or deploy.get("repo_url", "")
        except Exception:
            pass
        if not live_url:
            live_url = captured_live_url
        if not repo_url:
            repo_url = captured_repo_url

        card.live_url = live_url
        card.repo_url = repo_url

        completion_event = {"type": "zp.build.done", "card_id": card_id, "status": "deployed"}
        subscriber_key = f"{session_id}:{card_id}"
        for queue in _zp_build_subscribers.get(subscriber_key, []):
            try:
                queue.put_nowait(completion_event)
            except asyncio.QueueFull:
                pass

        try:
            await _zp_store.update_card(
                card_id,
                status="deployed",
                build_step="done",
                thread_id=thread_id,
                live_url=live_url,
                repo_url=repo_url,
            )
            push_zp_event(
                {
                    "type": "card.update",
                    "card_id": card_id,
                    "status": "deployed",
                    "title": card.title,
                    "session_id": session_id,
                }
            )
        except Exception:
            pass
        logger.info("[ZP] Build completed for card %s: %s (url=%s)", card_id, idea_title, live_url)
    except Exception:
        logger.exception("[ZP] Build failed for card %s", card_id)
        session = await orch.ensure_session(session_id)
        if session:
            card = next((c for c in session.cards if c.card_id == card_id), None)
            if card:
                card.status = "build_failed"
                try:
                    await _zp_store.update_card(card_id, status="build_failed")
                    push_zp_event(
                        {"type": "card.update", "card_id": card_id, "status": "build_failed", "session_id": session_id}
                    )
                except Exception:
                    pass
                failure_event = {"type": "zp.build.done", "card_id": card_id, "status": "build_failed"}
                subscriber_key = f"{session_id}:{card_id}"
                for queue in _zp_build_subscribers.get(subscriber_key, []):
                    try:
                        queue.put_nowait(failure_event)
                    except asyncio.QueueFull:
                        pass


async def _resume_exploration(orch, session_id: str) -> None:
    try:
        session = await orch.ensure_session(session_id)
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


@app.get("/api/zero-prompt/{session_id}/build/{card_id}/events")
@app.get("/zero-prompt/{session_id}/build/{card_id}/events")
async def zero_prompt_build_events(session_id: str, card_id: str):
    orch = _get_zp_orchestrator()
    session = await orch.ensure_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_not_found")

    card = next((c for c in session.cards if c.card_id == card_id), None)
    if card is None:
        raise HTTPException(status_code=404, detail="card_not_found")

    subscriber_key = f"{session_id}:{card_id}"
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    if subscriber_key not in _zp_build_subscribers:
        _zp_build_subscribers[subscriber_key] = []
    _zp_build_subscribers[subscriber_key].append(queue)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            for evt in list(card.build_events):
                yield f"data: {json.dumps(evt)}\n\n"

            if card.status in ("deployed", "build_failed"):
                yield f"data: {json.dumps({'type': 'zp.build.done', 'card_id': card_id, 'status': card.status})}\n\n"
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "zp.build.done":
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                    if card.status in ("deployed", "build_failed"):
                        yield f"data: {json.dumps({'type': 'zp.build.done', 'card_id': card_id, 'status': card.status})}\n\n"
                        break
        finally:
            subs = _zp_build_subscribers.get(subscriber_key, [])
            if queue in subs:
                subs.remove(queue)
            if not subs and subscriber_key in _zp_build_subscribers:
                del _zp_build_subscribers[subscriber_key]

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/zero-prompt/{session_id}/build/{card_id}")
@app.get("/zero-prompt/{session_id}/build/{card_id}")
async def zero_prompt_build_status(session_id: str, card_id: str):
    orch = _get_zp_orchestrator()
    session = await orch.ensure_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session_not_found")

    card = next((c for c in session.cards if c.card_id == card_id), None)
    if card is None:
        raise HTTPException(status_code=404, detail="card_not_found")

    return {
        "card_id": card_id,
        "status": card.status,
        "build_phase": card.build_phase,
        "build_node": card.build_node,
        "event_count": len(card.build_events),
        "thread_id": card.thread_id,
    }


if __name__ == "__main__":
    uvicorn.run(
        "agent.server:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info",
    )
