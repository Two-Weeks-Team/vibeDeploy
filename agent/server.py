"""Local FastAPI server — replaces gradient_adk @entrypoint for local testing.

Exposes the same HTTP interface the frontend expects:
  POST /run   → SSE stream of council events
  GET  /result/{id} → meeting result JSON
  GET  /health → liveness check

Run: python -m agent.server
"""

import asyncio
import json
import traceback
from collections.abc import AsyncGenerator
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import StreamingResponse

_AGENT_DIR = Path(__file__).resolve().parent
load_dotenv(_AGENT_DIR / ".env.test")

app = FastAPI(title="vibeDeploy Agent (local)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_results: dict[str, dict] = {}

_NODE_EVENTS = {
    "input_processor": {"phase": "input_processing", "message": "Analyzing your idea..."},
    "run_council_agent": {"phase": "individual_analysis", "message": "Council members analyzing..."},
    "cross_examination": {"phase": "cross_examination", "message": "Council members debating..."},
    "score_axis": {"phase": "scoring", "message": "Scoring axes..."},
    "strategist_verdict": {"phase": "verdict", "message": "Strategist delivering verdict..."},
    "decision_gate": {"phase": "decision", "message": "Making decision..."},
    "doc_generator": {"phase": "doc_generation", "message": "Generating documentation..."},
    "code_generator": {"phase": "code_generation", "message": "Generating code..."},
    "deployer": {"phase": "deployment", "message": "Deploying to DigitalOcean..."},
    "feedback_generator": {"phase": "feedback", "message": "Generating feedback..."},
    "conditional_review": {"phase": "conditional_review", "message": "Waiting for your decision..."},
}


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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

        _store_result(thread_id, final_state)

    except Exception as exc:
        yield _sse(
            "council.error",
            {
                "type": "council.error",
                "error": str(exc)[:500],
                "traceback": traceback.format_exc()[:1000],
            },
        )


def _store_result(thread_id: str, state: dict):
    scoring = state.get("scoring", {})
    decision_raw = scoring.get("decision", "NO_GO")
    verdict_map = {"GO": "GO", "CONDITIONAL": "CONDITIONAL", "NO_GO": "NO-GO"}

    analyses = state.get("council_analysis", {})
    analyses_list = [{"agent": k, **v} for k, v in analyses.items()] if isinstance(analyses, dict) else []

    cross_exam = state.get("cross_examination", {})
    debates_list = [{"topic": k, **v} for k, v in cross_exam.items()] if isinstance(cross_exam, dict) else []

    docs = state.get("generated_docs", {})
    documents_list = [{"type": k, "content": v} for k, v in docs.items()] if isinstance(docs, dict) else []

    deploy = state.get("deploy_result", {})
    deployment = None
    if deploy and deploy.get("live_url"):
        deployment = {
            "repoUrl": deploy.get("github_repo", ""),
            "liveUrl": deploy.get("live_url", ""),
        }

    _results[thread_id] = {
        "score": scoring.get("final_score", 0),
        "verdict": verdict_map.get(decision_raw, "NO-GO"),
        "analyses": analyses_list,
        "debates": debates_list,
        "documents": documents_list,
        "scoring": scoring,
        "deployment": deployment,
    }


@app.post("/run")
async def run_pipeline(request: RunRequest):
    config = request.config or {}
    thread_id = config.get("configurable", {}).get("thread_id", "default")

    return StreamingResponse(
        _stream_pipeline(request.prompt, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/result/{meeting_id}")
async def get_result(meeting_id: str):
    result = _results.get(meeting_id)
    if result is None:
        return {"error": "not_found"}, 404
    return result


@app.put("/test/result/{meeting_id}")
async def put_test_result(meeting_id: str, body: dict):
    _results[meeting_id] = body
    return {"stored": meeting_id}


@app.get("/health")
async def health():
    return {"status": "ok", "provider": "local-fastapi"}


if __name__ == "__main__":
    uvicorn.run(
        "agent.server:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level="info",
    )
