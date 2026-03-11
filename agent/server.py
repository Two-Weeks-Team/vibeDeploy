"""Local FastAPI server — replaces gradient_adk @entrypoint for local testing.

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
import json
import os
import re
import shutil
import time
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from .cost import estimate_pipeline_cost
from .db.store import ResultStore
from .llm import get_runtime_model_config
from .sse import NODE_EVENTS, format_sse
from .tools.digitalocean import list_apps as list_digitalocean_apps

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env.test")

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
                for family in {_project_family(candidate) for candidate in repo_candidates | ({name} if name else set())}
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

        reconciled.append({**meeting, "deployment": deployment})

    return reconciled


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
    scoring = state.get("scoring", {})
    decision_raw = scoring.get("decision", "NO_GO")
    verdict_map = {"GO": "GO", "CONDITIONAL": "CONDITIONAL", "NO_GO": "NO-GO"}

    analyses = state.get("council_analysis", {})
    analyses_list = [{"agent": k, **v} for k, v in analyses.items()] if isinstance(analyses, dict) else []

    cross_exam = state.get("cross_examination", {})
    debates_list = [{"topic": k, **v} for k, v in cross_exam.items()] if isinstance(cross_exam, dict) else []

    _DOC_TYPE_MAP = {
        "prd": "prd",
        "tech_spec": "tech-spec",
        "api_spec": "api-spec",
        "db_schema": "db-schema",
        "app_spec_yaml": "app-spec",
    }
    _DOC_TITLE_MAP = {
        "prd": "Product Requirements",
        "tech-spec": "Technical Specification",
        "api-spec": "API Specification",
        "db-schema": "Database Schema",
        "app-spec": "App Platform Spec",
    }
    docs = state.get("generated_docs", {})
    documents_list = []
    if isinstance(docs, dict):
        for k, v in docs.items():
            doc_type = _DOC_TYPE_MAP.get(k, k)
            documents_list.append(
                {
                    "type": doc_type,
                    "title": _DOC_TITLE_MAP.get(doc_type, doc_type),
                    "content": v,
                }
            )

    _EXT_LANG = {
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "jsx",
        ".py": "python",
        ".css": "css",
        ".html": "html",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sql": "sql",
        ".sh": "bash",
        ".toml": "toml",
        ".txt": "text",
    }
    code_files = []
    for label, code_dict in [("backend", state.get("backend_code", {})), ("frontend", state.get("frontend_code", {}))]:
        if isinstance(code_dict, dict):
            for path, content in code_dict.items():
                ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
                code_files.append(
                    {
                        "path": path,
                        "content": content,
                        "language": _EXT_LANG.get(ext, "text"),
                        "source": label,
                    }
                )

    deploy = state.get("deploy_result", {})
    deployment = None
    if deploy and (deploy.get("github_repo") or deploy.get("live_url") or deploy.get("local_url")):
        deployment = {
            "repoUrl": deploy.get("github_repo", ""),
            "liveUrl": deploy.get("live_url", ""),
            "status": deploy.get("status", ""),
        }
        if deploy.get("ci_status"):
            deployment["ciStatus"] = deploy["ci_status"]
        if deploy.get("ci_url"):
            deployment["ciUrl"] = deploy["ci_url"]
        if deploy.get("ci_repair_attempts"):
            deployment["ciRepairAttempts"] = deploy["ci_repair_attempts"]
        if deploy.get("local_url"):
            deployment["localUrl"] = deploy["local_url"]
        if deploy.get("local_backend_url"):
            deployment["localBackendUrl"] = deploy["local_backend_url"]
        if deploy.get("local_frontend_url"):
            deployment["localFrontendUrl"] = deploy["local_frontend_url"]

    result = {
        "score": scoring.get("final_score", 0),
        "verdict": verdict_map.get(decision_raw, "NO-GO"),
        "analyses": analyses_list,
        "debates": debates_list,
        "documents": documents_list,
        "code_files": code_files,
        "scoring": scoring,
        "deployment": deployment,
        "cost_estimate": state.get("cost_estimate"),
        "input_prompt": state.get("raw_input", ""),
        "idea_summary": state.get("idea_summary", ""),
    }
    await _store.save_meeting(thread_id, result)
    _invalidate_dashboard_snapshot_cache()


class RunRequest(BaseModel):
    prompt: str = ""
    config: dict | None = None


async def _stream_pipeline(prompt: str, thread_id: str) -> AsyncGenerator[str, None]:
    from .graph import app as graph_app

    yield _sse(
        "council.phase.start",
        {
            "type": "council.phase.start",
            "phase": "input_processing",
            "message": "Processing your idea...",
        },
    )

    final_state = {}

    try:
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 80}
        async for event in graph_app.astream_events(
            {"raw_input": prompt},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            if kind == "on_custom_event":
                payload = dict(data or {})
                payload.setdefault("type", name)
                yield _sse(name, payload)
                continue

            if kind == "on_chain_start" and name in _NODE_EVENTS:
                node_event = _NODE_EVENTS[name]
                yield _sse(
                    "council.node.start",
                    {
                        "type": "council.node.start",
                        "node": name,
                        "phase": node_event["phase"],
                        "message": node_event["message"],
                    },
                )

                input_data = data.get("input", {}) or {}
                if name == "run_council_agent":
                    agent_name = str(input_data.get("agent_name", "")).strip()
                    agent_node = _AGENT_NODE_IDS.get(agent_name)
                    if agent_node:
                        yield _sse(
                            "council.agent.start",
                            {
                                "type": "council.agent.start",
                                "agent": agent_name,
                                "node": agent_node,
                                "phase": "individual_analysis",
                                "message": f"{agent_name.title()} analysis started",
                            },
                        )
                elif name == "score_axis":
                    agent_name = str(input_data.get("agent_name", "")).strip()
                    axis_name = _AGENT_SCORE_AXES.get(agent_name, "")
                    axis_node = _SCORE_AXIS_NODE_IDS.get(axis_name)
                    if axis_node:
                        yield _sse(
                            "scoring.axis.start",
                            {
                                "type": "scoring.axis.start",
                                "agent": agent_name,
                                "axis": axis_name,
                                "node": axis_node,
                                "phase": "scoring",
                                "message": f"{_SCORE_AXIS_LABELS.get(axis_name, axis_name)} scoring started",
                            },
                        )
                continue

            if kind != "on_chain_end" or name not in _NODE_EVENTS:
                continue

            output = data.get("output", {})
            phase = output.get("phase", _NODE_EVENTS[name]["phase"])
            yield _sse(
                "council.node.complete",
                {
                    "type": "council.node.complete",
                    "node": name,
                    "phase": phase,
                    "message": f"{name} complete",
                },
            )

            if name == "run_council_agent":
                analyses = output.get("council_analysis", {}) or {}
                for agent_name, analysis in analyses.items():
                    agent_node = _AGENT_NODE_IDS.get(agent_name)
                    yield _sse(
                        "council.agent.analysis",
                        {
                            "type": "council.agent.analysis",
                            "agent": agent_name,
                            "node": agent_node,
                            "score": analysis.get("score", 0),
                            "findings_count": len(analysis.get("findings", [])),
                            "message": f"{agent_name.title()} analysis complete",
                        },
                    )
            elif name == "score_axis":
                scoring = output.get("scoring", {}) or {}
                for axis_name, axis_data in scoring.items():
                    if axis_name in {"final_score", "decision"} or not isinstance(axis_data, dict):
                        continue
                    axis_node = _SCORE_AXIS_NODE_IDS.get(axis_name)
                    yield _sse(
                        "scoring.axis.complete",
                        {
                            "type": "scoring.axis.complete",
                            "axis": axis_name,
                            "node": axis_node,
                            "phase": "scoring",
                            "score": axis_data.get("score", 0),
                            "message": f"{_SCORE_AXIS_LABELS.get(axis_name, axis_name)} scoring complete",
                        },
                    )
            elif name == "strategist_verdict":
                scoring = output.get("scoring", {}) or {}
                final_state["scoring"] = scoring
                yield _sse(
                    "council.verdict",
                    {
                        "type": "council.verdict",
                        "final_score": scoring.get("final_score", 0),
                        "decision": scoring.get("decision", "NO_GO"),
                    },
                )
            elif name == "blueprint_generator":
                bp = output.get("blueprint", {}) or {}
                yield _sse(
                    "blueprint.complete",
                    {
                        "type": "blueprint.complete",
                        "node": "blueprint",
                        "frontend_files": len(bp.get("frontend_files", {})),
                        "backend_files": len(bp.get("backend_files", {})),
                        "app_name": bp.get("app_name", ""),
                    },
                )
            elif name == "prompt_strategist":
                strategy = output.get("prompt_strategy", {}) or {}
                source_index = strategy.get("source_index", []) or []
                yield _sse(
                    "prompt_strategy.complete",
                    {
                        "type": "prompt_strategy.complete",
                        "node": "prompt_strategy",
                        "sources": len(source_index),
                        "frontend_model": strategy.get("model_plan", {}).get("frontend", {}).get("model", ""),
                        "backend_model": strategy.get("model_plan", {}).get("backend", {}).get("model", ""),
                    },
                )
            elif name == "code_evaluator":
                eval_res = output.get("code_eval_result", {}) or {}
                yield _sse(
                    "code_eval.result",
                    {
                        "type": "code_eval.result",
                        "node": "code_eval",
                        "match_rate": eval_res.get("match_rate", 0),
                        "completeness": eval_res.get("completeness", 0),
                        "consistency": eval_res.get("consistency", 0),
                        "runnability": eval_res.get("runnability", 0),
                        "iteration": eval_res.get("iteration", 0),
                        "passed": eval_res.get("passed", False),
                    },
                )
            elif name == "code_generator":
                frontend = output.get("frontend_code", {}) or {}
                backend = output.get("backend_code", {}) or {}
                warnings = output.get("code_gen_warnings", [])
                yield _sse(
                    "code_gen.complete",
                    {
                        "type": "code_gen.complete",
                        "node": "code_gen",
                        "frontend_files": len(frontend),
                        "backend_files": len(backend),
                        "has_frontend": len(frontend) >= 3,
                        "warnings": warnings,
                    },
                )
                if warnings:
                    yield _sse(
                        "code_gen.warning",
                        {
                            "type": "code_gen.warning",
                            "message": "; ".join(warnings),
                        },
                    )
            elif name == "deployer":
                deploy = output.get("deploy_result", {}) or {}
                final_state["deploy_result"] = deploy
                yield _sse(
                    "deploy.complete",
                    {
                        "type": "deploy.complete",
                        "node": "do_deploy",
                        "live_url": deploy.get("live_url", ""),
                        "github_repo": deploy.get("github_repo", ""),
                        "status": deploy.get("status", ""),
                        "frontend_files": deploy.get("frontend_files", 0),
                        "backend_files": deploy.get("backend_files", 0),
                        "url_verification": deploy.get("url_verification", {}),
                    },
                )

            final_state.update(output)

        cost = estimate_pipeline_cost()
        final_state["cost_estimate"] = cost

        await _store_result(thread_id, final_state)

        yield _sse(
            "council.phase.complete",
            {
                "type": "council.phase.complete",
                "phase": "complete",
                "message": "Pipeline complete",
                "cost_estimate": cost,
            },
        )

    except Exception as exc:
        yield _sse(
            "council.error",
            {
                "type": "council.error",
                "error": str(exc)[:500],
                "traceback": traceback.format_exc()[:1000],
            },
        )


@app.post("/api/run")
@app.post("/run")
async def run_pipeline(request: RunRequest):
    from .guardrails import sanitize_input

    sanitized, valid, error, pii_found = sanitize_input(request.prompt)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    config = request.config or {}
    thread_id = config.get("configurable", {}).get("thread_id", "default")

    return StreamingResponse(
        _with_tracking(thread_id, "evaluation", sanitized, _stream_pipeline(sanitized, thread_id)),
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
    from langgraph.types import Command

    from .graph import app as graph_app

    yield _sse(
        "council.phase.start",
        {
            "type": "council.phase.start",
            "phase": "resuming",
            "message": f"Resuming pipeline ({action})...",
        },
    )

    final_state = {}

    try:
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 80}
        async for event in graph_app.astream_events(
            Command(resume=action),
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            if kind == "on_chain_start" and name in _NODE_EVENTS:
                node_event = _NODE_EVENTS[name]
                yield _sse(
                    "council.node.start",
                    {
                        "type": "council.node.start",
                        "node": name,
                        "phase": node_event["phase"],
                        "message": node_event["message"],
                    },
                )
                continue

            if kind != "on_chain_end" or name not in _NODE_EVENTS:
                continue

            output = data.get("output", {})
            phase = output.get("phase", _NODE_EVENTS[name]["phase"])
            yield _sse(
                "council.node.complete",
                {
                    "type": "council.node.complete",
                    "node": name,
                    "phase": phase,
                    "message": f"{name} complete",
                },
            )

            if name == "deployer":
                deploy = output.get("deploy_result", {}) or {}
                final_state["deploy_result"] = deploy
                yield _sse(
                    "deploy.complete",
                    {
                        "type": "deploy.complete",
                        "live_url": deploy.get("live_url", ""),
                        "github_repo": deploy.get("github_repo", ""),
                        "status": deploy.get("status", ""),
                    },
                )

            final_state.update(output)

        full_state = graph_app.get_state(config)
        if full_state and full_state.values:
            merged = {**full_state.values, **final_state}
        else:
            merged = final_state

        await _store_result(thread_id, merged)

        yield _sse(
            "council.phase.complete",
            {
                "type": "council.phase.complete",
                "phase": "complete",
                "message": "Pipeline complete",
            },
        )

    except Exception as exc:
        yield _sse(
            "council.error",
            {
                "type": "council.error",
                "error": str(exc)[:500],
                "traceback": traceback.format_exc()[:1000],
            },
        )


@app.post("/api/resume")
@app.post("/resume")
async def resume_pipeline(request: ResumeRequest):
    return StreamingResponse(
        _with_tracking(
            request.thread_id,
            "evaluation",
            f"resume:{request.action}",
            _stream_resume(request.thread_id, request.action),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_brainstorm(prompt: str, thread_id: str) -> AsyncGenerator[str, None]:
    from .graph_brainstorm import brainstorm_app

    yield _sse(
        "brainstorm.phase.start",
        {
            "type": "brainstorm.phase.start",
            "phase": "input_processing",
            "message": "Processing your idea for brainstorming...",
        },
    )

    final_state = {}

    try:
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 80}
        async for event in brainstorm_app.astream_events(
            {"raw_input": prompt},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            if kind == "on_chain_start" and name in _NODE_EVENTS:
                node_event = _NODE_EVENTS[name]
                yield _sse(
                    "brainstorm.node.start",
                    {
                        "type": "brainstorm.node.start",
                        "node": name,
                        "phase": node_event["phase"],
                        "message": node_event["message"],
                    },
                )
                continue

            if kind != "on_chain_end" or name not in _NODE_EVENTS:
                continue

            output = data.get("output", {})
            phase = output.get("phase", _NODE_EVENTS[name]["phase"])
            yield _sse(
                "brainstorm.node.complete",
                {
                    "type": "brainstorm.node.complete",
                    "node": name,
                    "phase": phase,
                    "message": f"{name} complete",
                },
            )

            if name == "run_brainstorm_agent":
                insights = output.get("brainstorm_insights", {}) or {}
                for agent_name, insight in insights.items():
                    yield _sse(
                        "brainstorm.agent.insight",
                        {
                            "type": "brainstorm.agent.insight",
                            "agent": agent_name,
                            "ideas": insight.get("ideas", []),
                            "opportunities": insight.get("opportunities", []),
                            "wild_card": insight.get("wild_card", ""),
                            "action_items": insight.get("action_items", []),
                        },
                    )

            for key, val in output.items():
                if key == "brainstorm_insights" and isinstance(val, dict):
                    existing = final_state.get("brainstorm_insights", {}) or {}
                    existing.update(val)
                    final_state["brainstorm_insights"] = existing
                else:
                    final_state[key] = val

        cost = estimate_pipeline_cost()
        final_state["cost_estimate"] = cost

        await _store_brainstorm_result(thread_id, final_state)

        yield _sse(
            "brainstorm.phase.complete",
            {
                "type": "brainstorm.phase.complete",
                "phase": "complete",
                "message": "Brainstorming complete",
                "cost_estimate": cost,
            },
        )

    except Exception as exc:
        yield _sse(
            "brainstorm.error",
            {
                "type": "brainstorm.error",
                "error": str(exc)[:500],
                "traceback": traceback.format_exc()[:1000],
            },
        )


async def _store_brainstorm_result(thread_id: str, state: dict):
    insights = state.get("brainstorm_insights", {})
    synthesis = state.get("synthesis", {})

    insights_list = []
    for agent_name, insight in insights.items():
        insights_list.append({"agent": agent_name, **insight})

    result = {
        "insights": insights_list,
        "synthesis": synthesis,
        "idea": state.get("idea", {}),
        "idea_summary": state.get("idea_summary", ""),
        "cost_estimate": state.get("cost_estimate"),
    }
    await _store.save_brainstorm(thread_id, result)
    _invalidate_dashboard_snapshot_cache()


@app.post("/api/brainstorm")
@app.post("/brainstorm")
async def brainstorm_pipeline(request: RunRequest):
    from .guardrails import sanitize_input

    sanitized, valid, error, pii_found = sanitize_input(request.prompt)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    config = request.config or {}
    thread_id = config.get("configurable", {}).get("thread_id", "default")

    return StreamingResponse(
        _with_tracking(thread_id, "brainstorm", sanitized, _stream_brainstorm(sanitized, thread_id)),
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


@app.put("/test/result/{meeting_id}")
async def put_test_result(meeting_id: str, body: dict):
    await _store.save_meeting(meeting_id, body)
    _invalidate_dashboard_snapshot_cache()
    return {"stored": meeting_id}


@app.put("/test/brainstorm/{brainstorm_id}")
async def put_test_brainstorm(brainstorm_id: str, body: dict):
    await _store.save_brainstorm(brainstorm_id, body)
    _invalidate_dashboard_snapshot_cache()
    return {"stored": brainstorm_id}


@app.get("/health")
@app.get("/")
async def health():
    return {"status": "ok", "provider": "do-app-platform"}


@app.get("/api/cost-estimate")
@app.get("/cost-estimate")
async def cost_estimate():
    return estimate_pipeline_cost()


@app.get("/api/models")
@app.get("/models")
async def models():
    runtime_models = get_runtime_model_config()
    return {
        "models": runtime_models,
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
        if dep and (dep.get("liveUrl") or dep.get("repoUrl")):
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


if __name__ == "__main__":
    uvicorn.run(
        "agent.server:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info",
    )
