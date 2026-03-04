import json
import traceback

from gradient_adk import RequestContext, entrypoint

from .graph import app


@entrypoint
async def main(input: dict, context: RequestContext):
    prompt = input.get("prompt", "")
    config_data = input.get("config", {})
    thread_id = config_data.get("configurable", {}).get("thread_id", "default")
    config = {"configurable": {"thread_id": thread_id}}
    _ = context

    async def stream():
        yield _sse(
            "council.phase.start",
            {
                "type": "council.phase.start",
                "phase": "input_processing",
                "message": "Processing your idea...",
            },
        )

        try:
            async for event in app.astream_events(
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
                    yield _sse(
                        "deploy.complete",
                        {
                            "type": "deploy.complete",
                            "live_url": deploy.get("live_url", ""),
                            "github_repo": deploy.get("github_repo", ""),
                            "status": deploy.get("status", ""),
                        },
                    )

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

    return stream()


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


_NODE_EVENTS = {
    "input_processor": {
        "phase": "input_processing",
        "message": "Analyzing your idea...",
    },
    "run_council_agent": {
        "phase": "individual_analysis",
        "message": "Council members analyzing...",
    },
    "cross_examination": {
        "phase": "cross_examination",
        "message": "Council members debating...",
    },
    "score_axis": {
        "phase": "scoring",
        "message": "Scoring axes...",
    },
    "strategist_verdict": {
        "phase": "verdict",
        "message": "Strategist delivering verdict...",
    },
    "decision_gate": {
        "phase": "decision",
        "message": "Making decision...",
    },
    "doc_generator": {
        "phase": "doc_generation",
        "message": "Generating documentation...",
    },
    "code_generator": {
        "phase": "code_generation",
        "message": "Generating code...",
    },
    "deployer": {
        "phase": "deployment",
        "message": "Deploying to DigitalOcean...",
    },
    "feedback_generator": {
        "phase": "feedback",
        "message": "Generating feedback...",
    },
    "conditional_review": {
        "phase": "conditional_review",
        "message": "Waiting for your decision...",
    },
}
