import os
from typing import Annotated

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes.api_contract_generator import api_contract_generator_node
from .nodes.blueprint import blueprint_generator
from .nodes.build_validator import build_validator
from .nodes.code_evaluator import code_evaluator, route_code_eval
from .nodes.code_generator import code_generator
from .nodes.contract_validator import contract_validator_node
from .nodes.decision_gate import decision_gate, route_decision
from .nodes.deploy_gate import deploy_gate, route_after_deploy_gate
from .nodes.deployer import deployer
from .nodes.design_system_generator import design_system_generator
from .nodes.doc_generator import doc_generator
from .nodes.enrich import enrich_idea
from .nodes.experience_agent import experience_agent
from .nodes.fix_storm import fix_storm, scope_down
from .nodes.input_processor import input_processor
from .nodes.inspiration_agent import inspiration_agent
from .nodes.local_runtime_validator import local_runtime_validator
from .nodes.per_file_code_generator import backend_generator_node, frontend_generator_node
from .nodes.prompt_strategist import prompt_strategist
from .nodes.pydantic_generator import pydantic_generator_node
from .nodes.scaffold_generator import scaffold_generator_node
from .nodes.spec_freeze_gate import spec_freeze_gate
from .nodes.type_generator import type_generator_node
from .nodes.vibe_council import (
    cross_examination,
    fan_out_analysis,
    fan_out_scoring,
    run_council_agent,
    score_axis,
    strategist_verdict,
)
from .state import VibeDeployState


def route_after_enrich(state):
    if state.get("skip_council"):
        return "doc_generator"
    return fan_out_analysis(state)


def route_after_build(state):
    if state.get("build_validation", {}).get("passed"):
        return "deployer"
    if state.get("build_attempt_count", 0) >= 3:
        return "__end__"
    return "code_generator"


def route_after_spec_freeze(state):
    if state.get("spec_frozen"):
        return "scaffold_generator"
    if int(state.get("spec_freeze_attempt_count") or 0) >= 2:
        return "__end__"
    return "blueprint_generator"


def route_after_contract(state):
    validation = state.get("wiring_validation") or {}
    return "code_evaluator" if validation.get("passed") else "code_generator"


def route_after_local_runtime(state):
    runtime_validation = state.get("local_runtime_validation") or {}
    if runtime_validation.get("passed"):
        return "deploy_gate"
    attempts = int(state.get("build_attempt_count") or 0)
    if attempts >= 3:
        return "__end__"
    return "code_generator"


def route_code_eval_staged(state):
    result = route_code_eval(state)
    if result == "code_generator":
        return "backend_generator"
    if result == "deployer":
        return "build_validator"
    return result


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class PipelineState(VibeDeployState, total=False):
    council_analysis: Annotated[dict | None, merge_dicts]
    scoring: Annotated[dict | None, merge_dicts]


def create_graph():
    if os.getenv("VIBEDEPLOY_USE_STAGED_PIPELINE", "false").lower() in {"1", "true", "yes", "on"}:
        return create_staged_graph()

    workflow = StateGraph(PipelineState)

    workflow.add_node("input_processor", input_processor)
    workflow.add_node("inspiration_agent", inspiration_agent)
    workflow.add_node("experience_agent", experience_agent)
    workflow.add_node("enrich_idea", enrich_idea)
    workflow.add_node("run_council_agent", run_council_agent)
    workflow.add_node("cross_examination", cross_examination)
    workflow.add_node("score_axis", score_axis)
    workflow.add_node("strategist_verdict", strategist_verdict)
    workflow.add_node("decision_gate", decision_gate)
    workflow.add_node("fix_storm", fix_storm)
    workflow.add_node("scope_down", scope_down)
    workflow.add_node("doc_generator", doc_generator)
    workflow.add_node("blueprint_generator", blueprint_generator)
    workflow.add_node("prompt_strategist", prompt_strategist)
    workflow.add_node("code_generator", code_generator)
    workflow.add_node("code_evaluator", code_evaluator)
    workflow.add_node("build_validator", build_validator)
    workflow.add_node("deployer", deployer)

    workflow.set_entry_point("input_processor")

    workflow.add_edge("input_processor", "inspiration_agent")
    workflow.add_edge("inspiration_agent", "experience_agent")
    workflow.add_edge("experience_agent", "enrich_idea")
    workflow.add_conditional_edges(
        "enrich_idea",
        route_after_enrich,
        ["doc_generator", "run_council_agent"],
    )

    workflow.add_edge("run_council_agent", "cross_examination")
    workflow.add_conditional_edges("cross_examination", fan_out_scoring, ["score_axis"])
    workflow.add_edge("score_axis", "strategist_verdict")
    workflow.add_edge("strategist_verdict", "decision_gate")

    workflow.add_conditional_edges(
        "decision_gate",
        route_decision,
        {
            "doc_generator": "doc_generator",
            "fix_storm": "fix_storm",
            "scope_down": "scope_down",
        },
    )

    workflow.add_conditional_edges("fix_storm", fan_out_analysis, ["run_council_agent"])

    workflow.add_edge("scope_down", "doc_generator")

    workflow.add_edge("doc_generator", "blueprint_generator")
    workflow.add_edge("blueprint_generator", "prompt_strategist")
    workflow.add_edge("prompt_strategist", "code_generator")
    workflow.add_edge("code_generator", "code_evaluator")

    workflow.add_conditional_edges(
        "code_evaluator",
        route_code_eval,
        {
            "deployer": "build_validator",
            "code_generator": "code_generator",
        },
    )

    workflow.add_conditional_edges(
        "build_validator",
        route_after_build,
        {
            "deployer": "deployer",
            "code_generator": "code_generator",
            "__end__": END,
        },
    )
    workflow.add_edge("deployer", END)

    return workflow.compile(checkpointer=MemorySaver())


def create_staged_graph():
    workflow = StateGraph(PipelineState)

    workflow.add_node("input_processor", input_processor)
    workflow.add_node("inspiration_agent", inspiration_agent)
    workflow.add_node("experience_agent", experience_agent)
    workflow.add_node("enrich_idea", enrich_idea)
    workflow.add_node("run_council_agent", run_council_agent)
    workflow.add_node("cross_examination", cross_examination)
    workflow.add_node("score_axis", score_axis)
    workflow.add_node("strategist_verdict", strategist_verdict)
    workflow.add_node("decision_gate", decision_gate)
    workflow.add_node("fix_storm", fix_storm)
    workflow.add_node("scope_down", scope_down)
    workflow.add_node("doc_generator", doc_generator)
    workflow.add_node("blueprint_generator", blueprint_generator)
    workflow.add_node("api_contract_generator", api_contract_generator_node)
    workflow.add_node("spec_freeze_gate", spec_freeze_gate)
    workflow.add_node("scaffold_generator", scaffold_generator_node)
    workflow.add_node("type_generator", type_generator_node)
    workflow.add_node("pydantic_generator", pydantic_generator_node)
    workflow.add_node("design_system_generator", design_system_generator)
    workflow.add_node("prompt_strategist", prompt_strategist)
    workflow.add_node("backend_generator", backend_generator_node)
    workflow.add_node("frontend_generator", frontend_generator_node)
    workflow.add_node("code_generator", code_generator)
    workflow.add_node("contract_validator", contract_validator_node)
    workflow.add_node("code_evaluator", code_evaluator)
    workflow.add_node("build_validator", build_validator)
    workflow.add_node("local_runtime_validator", local_runtime_validator)
    workflow.add_node("deploy_gate", deploy_gate)
    workflow.add_node("deployer", deployer)

    workflow.set_entry_point("input_processor")

    workflow.add_edge("input_processor", "inspiration_agent")
    workflow.add_edge("inspiration_agent", "experience_agent")
    workflow.add_edge("experience_agent", "enrich_idea")
    workflow.add_conditional_edges(
        "enrich_idea",
        route_after_enrich,
        ["doc_generator", "run_council_agent"],
    )
    workflow.add_edge("run_council_agent", "cross_examination")
    workflow.add_conditional_edges("cross_examination", fan_out_scoring, ["score_axis"])
    workflow.add_edge("score_axis", "strategist_verdict")
    workflow.add_edge("strategist_verdict", "decision_gate")
    workflow.add_conditional_edges(
        "decision_gate",
        route_decision,
        {
            "doc_generator": "doc_generator",
            "fix_storm": "fix_storm",
            "scope_down": "scope_down",
        },
    )
    workflow.add_conditional_edges("fix_storm", fan_out_analysis, ["run_council_agent"])
    workflow.add_edge("scope_down", "doc_generator")

    workflow.add_edge("doc_generator", "blueprint_generator")
    workflow.add_edge("blueprint_generator", "api_contract_generator")
    workflow.add_edge("api_contract_generator", "spec_freeze_gate")
    workflow.add_conditional_edges(
        "spec_freeze_gate",
        route_after_spec_freeze,
        {
            "scaffold_generator": "scaffold_generator",
            "blueprint_generator": "blueprint_generator",
            "__end__": END,
        },
    )
    workflow.add_edge("scaffold_generator", "type_generator")
    workflow.add_edge("type_generator", "pydantic_generator")
    workflow.add_edge("pydantic_generator", "design_system_generator")
    workflow.add_edge("design_system_generator", "prompt_strategist")
    workflow.add_edge("prompt_strategist", "backend_generator")
    workflow.add_edge("backend_generator", "frontend_generator")
    workflow.add_edge("frontend_generator", "contract_validator")
    # Staged pipeline remaps logical "code_generator" → actual "backend_generator" for per-file generation
    workflow.add_conditional_edges(
        "contract_validator",
        route_after_contract,
        {
            "code_evaluator": "code_evaluator",
            "code_generator": "backend_generator",
        },
    )
    # Staged pipeline remaps logical "code_generator" → actual "backend_generator" for per-file generation
    workflow.add_conditional_edges(
        "code_evaluator",
        route_code_eval_staged,
        {
            "build_validator": "build_validator",
            "backend_generator": "backend_generator",
        },
    )
    # Staged pipeline remaps logical "code_generator" → actual "backend_generator" for per-file generation
    workflow.add_conditional_edges(
        "build_validator",
        route_after_build,
        {
            "deployer": "local_runtime_validator",
            "code_generator": "code_generator",
            "__end__": END,
        },
    )
    workflow.add_conditional_edges(
        "local_runtime_validator",
        route_after_local_runtime,
        {
            "deploy_gate": "deploy_gate",
            "code_generator": "backend_generator",
            "__end__": END,
        },
    )
    workflow.add_conditional_edges(
        "deploy_gate",
        route_after_deploy_gate,
        {
            "deployer": "deployer",
            "__end__": END,
        },
    )
    workflow.add_edge("deployer", END)

    return workflow.compile(checkpointer=MemorySaver())


app = create_graph()
