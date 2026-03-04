from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, Send, StateGraph

from .nodes.code_generator import code_generator
from .nodes.decision_gate import conditional_review, decision_gate, feedback_generator
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


def create_graph():
    workflow = StateGraph(VibeDeployState)
    # Add nodes (stubs imported from nodes/)
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

    # Entry
    workflow.set_entry_point("input_processor")
    # TODO: Wire edges (will be completed in issue #15)
    workflow.add_edge("input_processor", "run_council_agent")  # Simplified for now
    workflow.add_edge("run_council_agent", END)

    _ = (Send, fan_out_analysis, fan_out_scoring, decision_gate)
    return workflow.compile(checkpointer=MemorySaver())


app = create_graph()
