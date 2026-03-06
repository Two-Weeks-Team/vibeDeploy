import traceback

from gradient_adk import RequestContext, entrypoint

from .graph import app
from .graph_brainstorm import brainstorm_app
from .sse import NODE_EVENTS, format_sse


@entrypoint
async def main(input: dict, context: RequestContext):
    prompt = input.get("prompt", "")
    action = input.get("action", "evaluate")
    config_data = input.get("config", {})
    thread_id = config_data.get("configurable", {}).get("thread_id", "default")
    config = {"configurable": {"thread_id": thread_id}}
    _ = context

    if action == "brainstorm":
        return _stream_brainstorm(prompt, config)
    return _stream_evaluate(prompt, config)


def _stream_evaluate(prompt: str, config: dict):
    async def stream():
        yield format_sse(
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

                if kind == "on_chain_start" and name in NODE_EVENTS:
                    node_event = NODE_EVENTS[name]
                    yield format_sse(
                        "council.node.start",
                        {
                            "type": "council.node.start",
                            "node": name,
                            "phase": node_event["phase"],
                            "message": node_event["message"],
                        },
                    )
                    continue

                if kind != "on_chain_end" or name not in NODE_EVENTS:
                    continue

                output = data.get("output", {})
                phase = output.get("phase", NODE_EVENTS[name]["phase"])
                yield format_sse(
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
                        yield format_sse(
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
                    yield format_sse(
                        "council.verdict",
                        {
                            "type": "council.verdict",
                            "final_score": scoring.get("final_score", 0),
                            "decision": scoring.get("decision", "NO_GO"),
                        },
                    )
                elif name == "deployer":
                    deploy = output.get("deploy_result", {}) or {}
                    yield format_sse(
                        "deploy.complete",
                        {
                            "type": "deploy.complete",
                            "live_url": deploy.get("live_url", ""),
                            "github_repo": deploy.get("github_repo", ""),
                            "status": deploy.get("status", ""),
                        },
                    )

            yield format_sse(
                "council.phase.complete",
                {
                    "type": "council.phase.complete",
                    "phase": "complete",
                    "message": "Pipeline complete",
                },
            )
        except Exception as exc:
            yield format_sse(
                "council.error",
                {
                    "type": "council.error",
                    "error": str(exc)[:500],
                    "traceback": traceback.format_exc()[:1000],
                },
            )

    return stream()


def _stream_brainstorm(prompt: str, config: dict):
    async def stream():
        yield format_sse(
            "brainstorm.phase.start",
            {
                "type": "brainstorm.phase.start",
                "phase": "input_processing",
                "message": "Starting brainstorm session...",
            },
        )

        try:
            async for event in brainstorm_app.astream_events(
                {"raw_input": prompt},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")
                name = event.get("name", "")
                data = event.get("data", {})

                if kind == "on_chain_end" and name == "synthesize_brainstorm":
                    output = data.get("output", {})
                    yield format_sse(
                        "brainstorm.synthesis",
                        {
                            "type": "brainstorm.synthesis",
                            "synthesis": output.get("synthesis", {}),
                        },
                    )
                elif kind == "on_chain_end" and name == "run_brainstorm_agent":
                    output = data.get("output", {})
                    insights = output.get("brainstorm_insights", {})
                    for agent_name in insights:
                        yield format_sse(
                            "brainstorm.agent.complete",
                            {
                                "type": "brainstorm.agent.complete",
                                "agent": agent_name,
                            },
                        )

            yield format_sse(
                "brainstorm.phase.complete",
                {
                    "type": "brainstorm.phase.complete",
                    "phase": "complete",
                    "message": "Brainstorm complete",
                },
            )
        except Exception as exc:
            yield format_sse(
                "brainstorm.error",
                {
                    "type": "brainstorm.error",
                    "error": str(exc)[:500],
                    "traceback": traceback.format_exc()[:1000],
                },
            )

    return stream()
