from ..state import VibeDeployState

MAX_FIX_STORM_ROUNDS = 3


async def decision_gate(state: VibeDeployState) -> dict:
    scoring = state.get("scoring", {})
    decision = scoring.get("decision", "NO_GO")
    return {"phase": f"decision_{decision.lower()}"}


def route_decision(state: VibeDeployState) -> str:
    scoring = state.get("scoring", {})
    decision = scoring.get("decision", "NO_GO")
    iteration = state.get("eval_iteration", 0)
    final_score = float(scoring.get("final_score", 0) or 0)
    repair_tasks = state.get("repair_tasks") or []

    if decision == "GO":
        return "doc_generator"

    if decision == "CONDITIONAL" and final_score >= 70:
        return "doc_generator"

    if iteration < MAX_FIX_STORM_ROUNDS:
        return "fix_storm"

    if decision == "CONDITIONAL" and final_score >= 45 and repair_tasks and iteration < MAX_FIX_STORM_ROUNDS + 1:
        return "fix_storm"

    if iteration >= MAX_FIX_STORM_ROUNDS:
        return "scope_down"

    return "fix_storm"
