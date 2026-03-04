from typing import Annotated

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes.code_generator import code_generator
from .nodes.decision_gate import (
    conditional_review,
    decision_gate,
    feedback_generator,
    route_conditional,
    route_decision,
)
from .nodes.deployer import deployer
from .nodes.doc_generator import doc_generator
from .nodes.input_processor import input_processor
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
    workflow.add_node("run_council_agent", run_council_agent)
    workflow.add_node("cross_examination", cross_examination)
    workflow.add_node("score_axis", score_axis)
    workflow.add_node("strategist_verdict", strategist_verdict)
    workflow.add_node("decision_gate", decision_gate)
    workflow.add_node("conditional_review", conditional_review)
    workflow.add_node("feedback_generator", feedback_generator)
    workflow.add_node("doc_generator", doc_generator)
    workflow.add_node("code_generator", code_generator)
    workflow.add_node("deployer", deployer)
    workflow.set_entry_point("input_processor")
    workflow.add_conditional_edges(
        "input_processor",
        fan_out_analysis,
        ["run_council_agent"],
    )
    workflow.add_edge("run_council_agent", "cross_examination")
    workflow.add_conditional_edges(
        "cross_examination",
        fan_out_scoring,
        ["score_axis"],
    )
    workflow.add_edge("score_axis", "strategist_verdict")
    workflow.add_edge("strategist_verdict", "decision_gate")
    workflow.add_conditional_edges(
        "decision_gate",
        route_decision,
        {
            "doc_generator": "doc_generator",
            "conditional_review": "conditional_review",
            "feedback_generator": "feedback_generator",
        },
    )
    workflow.add_conditional_edges(
        "conditional_review",
        route_conditional,
        {
            "doc_generator": "doc_generator",
            "feedback_generator": "feedback_generator",
        },
    )
    workflow.add_edge("doc_generator", "code_generator")
    workflow.add_edge("code_generator", "deployer")
    workflow.add_edge("deployer", END)
    workflow.add_edge("feedback_generator", END)

    return workflow.compile(checkpointer=MemorySaver())


app = create_graph()
