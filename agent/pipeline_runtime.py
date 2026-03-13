import traceback
from collections.abc import AsyncGenerator

from .cost import estimate_pipeline_cost
from .sse import NODE_EVENTS, format_sse

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


def normalize_action_payload(body: dict | None) -> dict:
    payload = dict(body or {})
    action = str(payload.get("action") or "evaluate").strip().lower()

    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    configurable = config.get("configurable") if isinstance(config.get("configurable"), dict) else {}
    thread_id = str(payload.get("thread_id") or configurable.get("thread_id") or "default").strip() or "default"

    reference_urls = payload.get("reference_urls")
    if not isinstance(reference_urls, list):
        reference_urls = []
    flagship_contract = payload.get("flagship_contract") if isinstance(payload.get("flagship_contract"), dict) else {}

    return {
        "action": action,
        "thread_id": thread_id,
        "prompt": str(payload.get("prompt") or "").strip(),
        "youtube_url": str(payload.get("youtube_url") or "").strip(),
        "reference_urls": [str(item).strip() for item in reference_urls if str(item).strip()],
        "constraints": str(payload.get("constraints") or "").strip(),
        "selected_flagship": str(payload.get("selected_flagship") or "").strip(),
        "flagship_contract": flagship_contract,
    }


def compose_raw_input(payload: dict) -> str:
    parts: list[str] = []
    prompt = str(payload.get("prompt") or "").strip()
    youtube_url = str(payload.get("youtube_url") or "").strip()
    reference_urls = payload.get("reference_urls") if isinstance(payload.get("reference_urls"), list) else []
    constraints = str(payload.get("constraints") or "").strip()
    selected_flagship = str(payload.get("selected_flagship") or "").strip()

    if prompt:
        parts.append(prompt)
    if selected_flagship:
        parts.append(f"Flagship lane: {selected_flagship}")
    if youtube_url:
        parts.append(f"Use this YouTube as inspiration: {youtube_url}")
    if reference_urls:
        formatted = "\n".join(f"- {str(item).strip()}" for item in reference_urls if str(item).strip())
        if formatted:
            parts.append(f"Reference URLs:\n{formatted}")
    if constraints:
        parts.append(f"Constraints and acceptance criteria:\n{constraints}")

    return "\n\n".join(part for part in parts if part).strip()


def build_meeting_result(state: dict) -> dict:
    scoring = state.get("scoring", {})
    decision_raw = scoring.get("decision", "NO_GO")
    verdict_map = {"GO": "GO", "CONDITIONAL": "CONDITIONAL", "NO_GO": "NO-GO"}

    analyses = state.get("council_analysis", {})
    analyses_list = [{"agent": k, **v} for k, v in analyses.items()] if isinstance(analyses, dict) else []

    cross_exam = state.get("cross_examination", {})
    debates_list = [{"topic": k, **v} for k, v in cross_exam.items()] if isinstance(cross_exam, dict) else []

    docs = state.get("generated_docs", {})
    documents_list = []
    if isinstance(docs, dict):
        for key, value in docs.items():
            doc_type = _DOC_TYPE_MAP.get(key, key)
            documents_list.append(
                {
                    "type": doc_type,
                    "title": _DOC_TITLE_MAP.get(doc_type, doc_type),
                    "content": value,
                }
            )

    code_files = []
    for label, code_dict in [("backend", state.get("backend_code", {})), ("frontend", state.get("frontend_code", {}))]:
        if not isinstance(code_dict, dict):
            continue
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

    deploy = state.get("deploy_result", {}) if isinstance(state.get("deploy_result"), dict) else {}
    deployment = {
        "repoUrl": deploy.get("github_repo", ""),
        "liveUrl": deploy.get("live_url", ""),
        "status": deploy.get("status", ""),
        "ciStatus": deploy.get("ci_status", ""),
        "ciUrl": deploy.get("ci_url", ""),
        "ciRepairAttempts": deploy.get("ci_repair_attempts", 0),
        "localUrl": deploy.get("local_url", ""),
        "localAppDir": deploy.get("local_app_dir", ""),
        "localBackendUrl": deploy.get("local_backend_url", ""),
        "localFrontendUrl": deploy.get("local_frontend_url", ""),
    }

    return {
        "score": scoring.get("final_score", 0),
        "verdict": verdict_map.get(decision_raw, "NO-GO"),
        "selected_flagship": state.get("selected_flagship", ""),
        "analyses": analyses_list,
        "debates": debates_list,
        "documents": documents_list,
        "code_files": code_files,
        "deployment": deployment,
        "idea_summary": state.get("idea_summary", ""),
        "input_prompt": state.get("raw_input", ""),
        "cost_estimate": state.get("cost_estimate"),
    }


def build_brainstorm_result(state: dict) -> dict:
    insights = state.get("brainstorm_insights", {})
    synthesis = state.get("synthesis", {})

    insights_list = []
    if isinstance(insights, dict):
        for agent_name, insight in insights.items():
            if isinstance(insight, dict):
                insights_list.append({"agent": agent_name, **insight})

    return {
        "selected_flagship": state.get("selected_flagship", ""),
        "insights": insights_list,
        "synthesis": synthesis,
        "idea": state.get("idea", {}),
        "idea_summary": state.get("idea_summary", ""),
        "cost_estimate": state.get("cost_estimate"),
    }


def _phase_event(event_name: str, phase: str, message: str, **extra) -> str:
    return format_sse(
        event_name,
        {
            "type": event_name,
            "phase": phase,
            "message": message,
            **extra,
        },
    )


async def _stream_evaluation(
    prompt: str, thread_id: str, initial_state: dict | None = None
) -> AsyncGenerator[str, None]:
    from .graph import app as graph_app

    yield format_sse(
        "session.started",
        {
            "type": "session.started",
            "action": "evaluate",
            "thread_id": thread_id,
            "phase": "input_processing",
            "message": "Evaluation session started",
        },
    )
    yield format_sse(
        "council.phase.start",
        {
            "type": "council.phase.start",
            "phase": "input_processing",
            "message": "Processing your idea...",
        },
    )

    final_state: dict = {"raw_input": prompt, **dict(initial_state or {})}

    try:
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 80}
        async for event in graph_app.astream_events(final_state, config=config, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            if kind == "on_custom_event":
                payload = dict(data or {})
                payload.setdefault("type", name)
                yield format_sse(name, payload)
                continue

            if kind == "on_chain_start" and name in NODE_EVENTS:
                node_event = NODE_EVENTS[name]
                phase = node_event["phase"]
                yield _phase_event("phase.started", phase, node_event["message"], node=name, thread_id=thread_id)
                yield format_sse(
                    "council.node.start",
                    {
                        "type": "council.node.start",
                        "node": name,
                        "phase": phase,
                        "message": node_event["message"],
                    },
                )

                input_data = data.get("input", {}) or {}
                if name == "run_council_agent":
                    agent_name = str(input_data.get("agent_name", "")).strip()
                    agent_node = _AGENT_NODE_IDS.get(agent_name)
                    if agent_node:
                        yield format_sse(
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
                        yield format_sse(
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

            if kind != "on_chain_end" or name not in NODE_EVENTS:
                continue

            output = data.get("output", {}) or {}
            phase = output.get("phase", NODE_EVENTS[name]["phase"])
            final_state.update(output)

            yield _phase_event("phase.completed", phase, f"{name} complete", node=name, thread_id=thread_id)
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
                    agent_node = _AGENT_NODE_IDS.get(agent_name)
                    yield format_sse(
                        "council.agent.completed",
                        {
                            "type": "council.agent.completed",
                            "agent": agent_name,
                            "node": agent_node,
                            "score": analysis.get("score", 0),
                            "findings_count": len(analysis.get("findings", [])),
                        },
                    )
                    yield format_sse(
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
                    yield format_sse(
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
                yield format_sse(
                    "council.verdict",
                    {
                        "type": "council.verdict",
                        "final_score": scoring.get("final_score", 0),
                        "decision": scoring.get("decision", "NO_GO"),
                    },
                )
            elif name == "blueprint_generator":
                bp = output.get("blueprint", {}) or {}
                yield format_sse(
                    "artifact.generated",
                    {
                        "type": "artifact.generated",
                        "artifact_type": "blueprint",
                        "node": "blueprint",
                        "frontend_files": len(bp.get("frontend_files", {})),
                        "backend_files": len(bp.get("backend_files", {})),
                        "app_name": bp.get("app_name", ""),
                    },
                )
                yield format_sse(
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
                yield format_sse(
                    "artifact.generated",
                    {
                        "type": "artifact.generated",
                        "artifact_type": "prompt_strategy",
                        "node": "prompt_strategy",
                        "sources": len(source_index),
                    },
                )
                yield format_sse(
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
                yield format_sse(
                    "code_eval.result",
                    {
                        "type": "code_eval.result",
                        "node": "code_eval",
                        "match_rate": eval_res.get("match_rate", 0),
                        "completeness": eval_res.get("completeness", 0),
                        "consistency": eval_res.get("consistency", 0),
                        "runnability": eval_res.get("runnability", 0),
                        "artifact_fidelity": eval_res.get("artifact_fidelity"),
                        "iteration": eval_res.get("iteration", 0),
                        "passed": eval_res.get("passed", False),
                        "blockers": eval_res.get("blockers", []),
                    },
                )
            elif name == "code_generator":
                frontend = output.get("frontend_code", {}) or {}
                backend = output.get("backend_code", {}) or {}
                warnings = output.get("code_gen_warnings", [])
                yield format_sse(
                    "artifact.generated",
                    {
                        "type": "artifact.generated",
                        "artifact_type": "code_bundle",
                        "node": "code_gen",
                        "frontend_files": len(frontend),
                        "backend_files": len(backend),
                    },
                )
                yield format_sse(
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
                    yield format_sse(
                        "code_gen.warning",
                        {
                            "type": "code_gen.warning",
                            "message": "; ".join(warnings),
                        },
                    )
            elif name == "deployer":
                deploy = output.get("deploy_result", {}) or {}
                yield format_sse(
                    "artifact.generated",
                    {
                        "type": "artifact.generated",
                        "artifact_type": "deployment",
                        "node": "do_deploy",
                        "live_url": deploy.get("live_url", ""),
                        "github_repo": deploy.get("github_repo", ""),
                        "status": deploy.get("status", ""),
                    },
                )
                yield format_sse(
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

        final_state["cost_estimate"] = estimate_pipeline_cost()
        result = build_meeting_result(final_state)
        yield format_sse(
            "artifact.generated",
            {
                "type": "artifact.generated",
                "artifact_type": "meeting_result",
                "thread_id": thread_id,
                "result": result,
            },
        )
        yield format_sse(
            "session.completed",
            {
                "type": "session.completed",
                "action": "evaluate",
                "thread_id": thread_id,
                "phase": "complete",
                "result_type": "meeting",
                "result": result,
            },
        )
        yield format_sse(
            "council.phase.complete",
            {
                "type": "council.phase.complete",
                "phase": "complete",
                "message": "Pipeline complete",
                "cost_estimate": final_state["cost_estimate"],
            },
        )
    except Exception as exc:
        error_payload = {
            "type": "session.error",
            "action": "evaluate",
            "thread_id": thread_id,
            "error": str(exc)[:500],
            "traceback": traceback.format_exc()[:1000],
        }
        yield format_sse("session.error", error_payload)
        yield format_sse(
            "council.error",
            {
                "type": "council.error",
                "error": error_payload["error"],
                "traceback": error_payload["traceback"],
            },
        )


async def _stream_resume(thread_id: str, action: str) -> AsyncGenerator[str, None]:
    from langgraph.types import Command

    from .graph import app as graph_app

    yield format_sse(
        "session.started",
        {
            "type": "session.started",
            "action": "resume",
            "thread_id": thread_id,
            "phase": "resuming",
            "message": "Resume session started",
        },
    )
    yield format_sse(
        "council.phase.start",
        {
            "type": "council.phase.start",
            "phase": "resuming",
            "message": f"Resuming pipeline ({action})...",
        },
    )

    final_state: dict = {}

    try:
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 80}
        async for event in graph_app.astream_events(Command(resume=action), config=config, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            if kind == "on_custom_event":
                payload = dict(data or {})
                payload.setdefault("type", name)
                yield format_sse(name, payload)
                continue

            if kind == "on_chain_start" and name in NODE_EVENTS:
                node_event = NODE_EVENTS[name]
                phase = node_event["phase"]
                yield _phase_event("phase.started", phase, node_event["message"], node=name, thread_id=thread_id)
                yield format_sse(
                    "council.node.start",
                    {
                        "type": "council.node.start",
                        "node": name,
                        "phase": phase,
                        "message": node_event["message"],
                    },
                )
                continue

            if kind != "on_chain_end" or name not in NODE_EVENTS:
                continue

            output = data.get("output", {}) or {}
            phase = output.get("phase", NODE_EVENTS[name]["phase"])
            final_state.update(output)
            yield _phase_event("phase.completed", phase, f"{name} complete", node=name, thread_id=thread_id)
            yield format_sse(
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
                yield format_sse(
                    "deploy.complete",
                    {
                        "type": "deploy.complete",
                        "live_url": deploy.get("live_url", ""),
                        "github_repo": deploy.get("github_repo", ""),
                        "status": deploy.get("status", ""),
                    },
                )

        full_state = graph_app.get_state(config)
        if full_state and full_state.values:
            final_state = {**full_state.values, **final_state}

        final_state["cost_estimate"] = estimate_pipeline_cost()
        result = build_meeting_result(final_state)
        yield format_sse(
            "session.completed",
            {
                "type": "session.completed",
                "action": "resume",
                "thread_id": thread_id,
                "phase": "complete",
                "result_type": "meeting",
                "result": result,
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
        error_payload = {
            "type": "session.error",
            "action": "resume",
            "thread_id": thread_id,
            "error": str(exc)[:500],
            "traceback": traceback.format_exc()[:1000],
        }
        yield format_sse("session.error", error_payload)
        yield format_sse(
            "council.error",
            {
                "type": "council.error",
                "error": error_payload["error"],
                "traceback": error_payload["traceback"],
            },
        )


async def _stream_brainstorm(
    prompt: str, thread_id: str, initial_state: dict | None = None
) -> AsyncGenerator[str, None]:
    from .graph_brainstorm import brainstorm_app

    yield format_sse(
        "session.started",
        {
            "type": "session.started",
            "action": "brainstorm",
            "thread_id": thread_id,
            "phase": "input_processing",
            "message": "Brainstorm session started",
        },
    )
    yield format_sse(
        "brainstorm.phase.start",
        {
            "type": "brainstorm.phase.start",
            "phase": "input_processing",
            "message": "Processing your idea for brainstorming...",
        },
    )

    final_state: dict = {"raw_input": prompt, **dict(initial_state or {})}

    try:
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 80}
        async for event in brainstorm_app.astream_events(final_state, config=config, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")
            data = event.get("data", {})

            if kind == "on_chain_start" and name in NODE_EVENTS:
                node_event = NODE_EVENTS[name]
                phase = node_event["phase"]
                yield _phase_event("phase.started", phase, node_event["message"], node=name, thread_id=thread_id)
                yield format_sse(
                    "brainstorm.node.start",
                    {
                        "type": "brainstorm.node.start",
                        "node": name,
                        "phase": phase,
                        "message": node_event["message"],
                    },
                )
                continue

            if kind != "on_chain_end" or name not in NODE_EVENTS:
                continue

            output = data.get("output", {}) or {}
            phase = output.get("phase", NODE_EVENTS[name]["phase"])
            yield _phase_event("phase.completed", phase, f"{name} complete", node=name, thread_id=thread_id)
            yield format_sse(
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
                    yield format_sse(
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

            for key, value in output.items():
                if key == "brainstorm_insights" and isinstance(value, dict):
                    existing = final_state.get("brainstorm_insights", {}) or {}
                    existing.update(value)
                    final_state["brainstorm_insights"] = existing
                else:
                    final_state[key] = value

        final_state["cost_estimate"] = estimate_pipeline_cost()
        result = build_brainstorm_result(final_state)
        yield format_sse(
            "artifact.generated",
            {
                "type": "artifact.generated",
                "artifact_type": "brainstorm_result",
                "thread_id": thread_id,
                "result": result,
            },
        )
        yield format_sse(
            "session.completed",
            {
                "type": "session.completed",
                "action": "brainstorm",
                "thread_id": thread_id,
                "phase": "complete",
                "result_type": "brainstorm",
                "result": result,
            },
        )
        yield format_sse(
            "brainstorm.phase.complete",
            {
                "type": "brainstorm.phase.complete",
                "phase": "complete",
                "message": "Brainstorming complete",
                "cost_estimate": final_state["cost_estimate"],
            },
        )
    except Exception as exc:
        error_payload = {
            "type": "session.error",
            "action": "brainstorm",
            "thread_id": thread_id,
            "error": str(exc)[:500],
            "traceback": traceback.format_exc()[:1000],
        }
        yield format_sse("session.error", error_payload)
        yield format_sse(
            "brainstorm.error",
            {
                "type": "brainstorm.error",
                "error": error_payload["error"],
                "traceback": error_payload["traceback"],
            },
        )


async def stream_action_session(payload: dict) -> AsyncGenerator[str, None]:
    action_payload = normalize_action_payload(payload)
    action = action_payload["action"]
    raw_input = compose_raw_input(action_payload)
    initial_state = {
        "selected_flagship": action_payload.get("selected_flagship") or None,
        "flagship_contract": action_payload.get("flagship_contract") or None,
    }
    if action == "brainstorm":
        async for chunk in _stream_brainstorm(
            raw_input or action_payload["prompt"],
            action_payload["thread_id"],
            initial_state=initial_state,
        ):
            yield chunk
        return
    if action == "resume":
        resume_action = action_payload["constraints"] or "proceed"
        async for chunk in _stream_resume(action_payload["thread_id"], resume_action):
            yield chunk
        return

    async for chunk in _stream_evaluation(
        raw_input or action_payload["prompt"],
        action_payload["thread_id"],
        initial_state=initial_state,
    ):
        yield chunk
