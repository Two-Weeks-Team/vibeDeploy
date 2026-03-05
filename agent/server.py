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

from .db.store import ResultStore
from .sse import NODE_EVENTS, format_sse

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env.test")

_store: ResultStore | None = None

# ── Dashboard live tracking ──────────────────────────────────────────
_active_pipelines: dict[str, dict] = {}
_dashboard_queues: list[asyncio.Queue] = []


def _register_pipeline(thread_id: str, pipeline_type: str, prompt: str):
    _active_pipelines[thread_id] = {
        "thread_id": thread_id,
        "type": pipeline_type,
        "phase": "starting",
        "started_at": time.time(),
        "prompt_preview": prompt[:120],
    }


def _deregister_pipeline(thread_id: str):
    _active_pipelines.pop(thread_id, None)


async def _broadcast_event(event_data: dict):
    dead: list[asyncio.Queue] = []
    for q in _dashboard_queues:
        try:
            q.put_nowait(event_data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _dashboard_queues.remove(q)


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
    db_path = os.environ.get("DB_PATH", str(_AGENT_DIR / "vibedeploy.db"))
    _store = ResultStore(db_path)
    await _store.init()
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
    }
    await _store.save_meeting(thread_id, result)


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
        config = {"configurable": {"thread_id": thread_id}}
        async for event in graph_app.astream_events(
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

            if name == "run_council_agent":
                analyses = output.get("council_analysis", {}) or {}
                for agent_name, analysis in analyses.items():
                    yield _sse(
                        "council.agent.analysis",
                        {
                            "type": "council.agent.analysis",
                            "agent": agent_name,
                            "score": analysis.get("score", 0),
                            "findings_count": len(analysis.get("findings", [])),
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
            elif name == "deployer":
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

        yield _sse(
            "council.phase.complete",
            {
                "type": "council.phase.complete",
                "phase": "complete",
                "message": "Pipeline complete",
            },
        )

        await _store_result(thread_id, final_state)

    except Exception as exc:
        yield _sse(
            "council.error",
            {
                "type": "council.error",
                "error": str(exc)[:500],
                "traceback": traceback.format_exc()[:1000],
            },
        )


@app.post("/run")
async def run_pipeline(request: RunRequest):
    config = request.config or {}
    thread_id = config.get("configurable", {}).get("thread_id", "default")

    return StreamingResponse(
        _with_tracking(thread_id, "evaluation", request.prompt, _stream_pipeline(request.prompt, thread_id)),
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
        config = {"configurable": {"thread_id": thread_id}}
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

        yield _sse(
            "council.phase.complete",
            {
                "type": "council.phase.complete",
                "phase": "complete",
                "message": "Pipeline complete",
            },
        )

        await _store_result(thread_id, merged)

    except Exception as exc:
        yield _sse(
            "council.error",
            {
                "type": "council.error",
                "error": str(exc)[:500],
                "traceback": traceback.format_exc()[:1000],
            },
        )


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
        config = {"configurable": {"thread_id": thread_id}}
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

        yield _sse(
            "brainstorm.phase.complete",
            {
                "type": "brainstorm.phase.complete",
                "phase": "complete",
                "message": "Brainstorming complete",
            },
        )

        await _store_brainstorm_result(thread_id, final_state)

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
    }
    await _store.save_brainstorm(thread_id, result)


@app.post("/brainstorm")
async def brainstorm_pipeline(request: RunRequest):
    config = request.config or {}
    thread_id = config.get("configurable", {}).get("thread_id", "default")

    return StreamingResponse(
        _with_tracking(thread_id, "brainstorm", request.prompt, _stream_brainstorm(request.prompt, thread_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/brainstorm/result/{session_id}")
async def get_brainstorm_result(session_id: str):
    result = await _store.get_brainstorm(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="not_found")
    return result


@app.get("/result/{meeting_id}")
async def get_result(meeting_id: str):
    result = await _store.get_meeting(meeting_id)
    if result is None:
        raise HTTPException(status_code=404, detail="not_found")
    return result


@app.put("/test/result/{meeting_id}")
async def put_test_result(meeting_id: str, body: dict):
    await _store.save_meeting(meeting_id, body)
    return {"stored": meeting_id}


@app.get("/health")
async def health():
    return {"status": "ok", "provider": "local-fastapi"}


@app.get("/dashboard/stats")
async def dashboard_stats():
    stats = await _store.get_stats()
    return stats


@app.get("/dashboard/results")
async def dashboard_results():
    return await _store.list_meetings(limit=50)


@app.get("/dashboard/brainstorms")
async def dashboard_brainstorms():
    return await _store.list_brainstorms(limit=50)


@app.get("/dashboard/active")
async def dashboard_active():
    return list(_active_pipelines.values())


@app.get("/dashboard/events")
async def dashboard_events():
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    _dashboard_queues.append(queue)

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
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
