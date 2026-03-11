import json

NODE_EVENTS = {
    "input_processor": {"phase": "input_processing", "message": "Analyzing your idea..."},
    "run_council_agent": {"phase": "individual_analysis", "message": "Council members analyzing..."},
    "cross_examination": {"phase": "cross_examination", "message": "Council members debating..."},
    "score_axis": {"phase": "scoring", "message": "Scoring axes..."},
    "strategist_verdict": {"phase": "verdict", "message": "Strategist delivering verdict..."},
    "decision_gate": {"phase": "decision", "message": "Making decision..."},
    "doc_generator": {"phase": "doc_generation", "message": "Generating documentation..."},
    "blueprint_generator": {"phase": "blueprint", "message": "Creating file manifest..."},
    "prompt_strategist": {"phase": "prompt_strategy", "message": "Assembling model-aware prompt kit..."},
    "code_generator": {"phase": "code_generation", "message": "Generating code..."},
    "code_evaluator": {"phase": "code_evaluation", "message": "Evaluating code quality..."},
    "deployer": {"phase": "deployment", "message": "Deploying to DigitalOcean..."},
    "feedback_generator": {"phase": "feedback", "message": "Generating feedback..."},
    "conditional_review": {"phase": "conditional_review", "message": "Waiting for your decision..."},
    "run_brainstorm_agent": {"phase": "brainstorming", "message": "Agents brainstorming ideas..."},
    "synthesize_brainstorm": {"phase": "synthesis", "message": "Synthesizing insights..."},
}


def format_sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
