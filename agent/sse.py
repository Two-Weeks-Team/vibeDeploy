import json

NODE_EVENTS = {
    "input_processor": {"phase": "input_processing", "message": "Analyzing your idea..."},
    "inspiration_agent": {"phase": "reference_mapping", "message": "Extracting reference and YouTube inspiration..."},
    "experience_agent": {"phase": "experience_specialization", "message": "Specializing the product experience..."},
    "run_council_agent": {"phase": "individual_analysis", "message": "Running named council analysis..."},
    "cross_examination": {"phase": "cross_examination", "message": "Council members debating..."},
    "score_axis": {"phase": "scoring", "message": "Scoring named evaluation axes..."},
    "strategist_verdict": {"phase": "verdict", "message": "Strategist delivering verdict..."},
    "decision_gate": {"phase": "decision", "message": "Making decision..."},
    "doc_generator": {"phase": "doc_generation", "message": "Generating documentation..."},
    "blueprint_generator": {"phase": "blueprint", "message": "Creating file manifest..."},
    "prompt_strategist": {"phase": "prompt_strategy", "message": "Building model-aware prompt strategy..."},
    "code_generator": {"phase": "code_generation", "message": "Generating code..."},
    "code_evaluator": {"phase": "code_evaluation", "message": "Evaluating code quality..."},
    "build_validator": {"phase": "build_validation", "message": "Validating build in Docker..."},
    "deployer": {"phase": "deployment", "message": "Deploying to DigitalOcean..."},
    "feedback_generator": {
        "phase": "feedback",
        "message": "Generating feedback...",
    },  # COMPAT: remove after 2026-06-01 — no graph node emits this; kept for tests/conftest.py mock fixture
    "run_brainstorm_agent": {"phase": "brainstorming", "message": "Agents brainstorming ideas..."},
    "synthesize_brainstorm": {"phase": "synthesis", "message": "Synthesizing insights..."},
    "api_contract_generator": {"phase": "api_contract", "message": "Generating OpenAPI contract..."},
    "spec_freeze_gate": {"phase": "spec_freeze", "message": "Freezing API specification..."},
    "scaffold_generator": {"phase": "scaffold", "message": "Scaffolding project structure..."},
    "type_generator": {"phase": "type_generation", "message": "Generating TypeScript types..."},
    "pydantic_generator": {"phase": "pydantic_generation", "message": "Generating Pydantic models..."},
    "design_system_generator": {"phase": "design_system", "message": "Generating design system tokens..."},
    "backend_generator": {"phase": "backend_generation", "message": "Generating backend files..."},
    "frontend_generator": {"phase": "frontend_generation", "message": "Generating frontend files..."},
    "contract_validator": {"phase": "contract_validation", "message": "Validating API contract compliance..."},
    "local_runtime_validator": {"phase": "runtime_validation", "message": "Validating local runtime..."},
    "deploy_gate": {"phase": "deploy_gate", "message": "Checking deploy readiness..."},
    "frontend_file_repairer": {"phase": "frontend_repair", "message": "Repairing failing frontend files..."},
}


def format_sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
