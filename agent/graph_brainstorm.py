from typing import Annotated, Dict, List, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes.brainstorm import (
    fan_out_brainstorm,
    run_brainstorm_agent,
    synthesize_brainstorm,
)
from .nodes.input_processor import input_processor


def merge_dicts(left: dict | None, right: dict | None) -> dict:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class BrainstormState(TypedDict):
    raw_input: str
    input_type: str
    transcript: Optional[str]
    key_frames: Optional[List[Dict]]
    visual_context: Optional[str]
    idea: Dict
    idea_summary: str
    brainstorm_insights: Annotated[dict | None, merge_dicts]
    synthesis: Optional[Dict]
    phase: str
    error: Optional[str]


def create_brainstorm_graph():
    workflow = StateGraph(BrainstormState)
    workflow.add_node("input_processor", input_processor)
    workflow.add_node("run_brainstorm_agent", run_brainstorm_agent)
    workflow.add_node("synthesize_brainstorm", synthesize_brainstorm)

    workflow.set_entry_point("input_processor")
    workflow.add_conditional_edges(
        "input_processor",
        fan_out_brainstorm,
        ["run_brainstorm_agent"],
    )
    workflow.add_edge("run_brainstorm_agent", "synthesize_brainstorm")
    workflow.add_edge("synthesize_brainstorm", END)

    return workflow.compile(checkpointer=MemorySaver())


brainstorm_app = create_brainstorm_graph()
