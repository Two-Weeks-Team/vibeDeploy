from ..state import VibeDeployState


async def decision_gate(state: VibeDeployState) -> dict:
    scoring = state.get("scoring", {})
    decision = scoring.get("decision", "NO_GO")
    return {"phase": f"decision_{decision.lower()}"}


def route_decision(state: VibeDeployState) -> str:
    scoring = state.get("scoring", {})
    decision = scoring.get("decision", "NO_GO")
    iteration = state.get("eval_iteration", 0)
    final_score = float(scoring.get("final_score", 0) or 0)

    if decision == "GO":
        return "doc_generator"

    if decision == "CONDITIONAL" and final_score >= 60:
        return "doc_generator"

    if iteration >= 1:
        return "scope_down"

    return "fix_storm"
