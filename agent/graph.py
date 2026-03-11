from typing import Annotated

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes.blueprint import blueprint_generator
from .nodes.code_evaluator import code_evaluator, route_code_eval
from .nodes.code_generator import code_generator
from .nodes.decision_gate import decision_gate, route_decision
from .nodes.deployer import deployer
from .nodes.doc_generator import doc_generator
from .nodes.enrich import enrich_idea
from .nodes.fix_storm import fix_storm, scope_down
from .nodes.input_processor import input_processor
from .nodes.prompt_strategist import prompt_strategist
from .nodes.vibe_council import (
    cross_examination,
    fan_out_analysis,
    fan_out_scoring,
    run_council_agent,
    score_axis,
    strategist_verdict,
)
from .state import VibeDeployState


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class PipelineState(VibeDeployState, total=False):
    council_analysis: Annotated[dict | None, merge_dicts]
    scoring: Annotated[dict | None, merge_dicts]


def create_graph():
    workflow = StateGraph(PipelineState)

    workflow.add_node("input_processor", input_processor)
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
    workflow.add_node("deployer", deployer)

    workflow.set_entry_point("input_processor")

    workflow.add_edge("input_processor", "enrich_idea")
    workflow.add_conditional_edges("enrich_idea", fan_out_analysis, ["run_council_agent"])

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
            "deployer": "deployer",
            "code_generator": "code_generator",
        },
    )

    workflow.add_edge("deployer", END)

    return workflow.compile(checkpointer=MemorySaver())


app = create_graph()
