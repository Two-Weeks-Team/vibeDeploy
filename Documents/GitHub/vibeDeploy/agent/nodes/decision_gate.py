from ..state import VibeDeployState


def decision_gate(state: VibeDeployState) -> str:
    decision = ((state.get("scoring") or {}).get("decision") or "NO_GO").upper()

    if decision == "GO":
        return "doc_generator"
    if decision == "CONDITIONAL":
        return "conditional_review"
    return "feedback_generator"


async def conditional_review(state: VibeDeployState) -> dict:
    _ = state
    return {
        "scope_adjustment": "",
        "user_feedback": "",
        "phase": "conditional_accepted",
    }


async def feedback_generator(state: VibeDeployState) -> dict:
    _ = state
    return {
        "phase": "feedback_delivered",
        "error": None,
    }
