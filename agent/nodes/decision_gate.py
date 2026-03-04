from langgraph.types import interrupt

from ..state import VibeDeployState


async def decision_gate(state: VibeDeployState) -> dict:
    scoring = state.get("scoring", {})
    decision = scoring.get("decision", "NO_GO")
    return {"phase": f"decision_{decision.lower()}"}


def route_decision(state: VibeDeployState) -> str:
    scoring = state.get("scoring", {})
    decision = scoring.get("decision", "NO_GO")

    if decision == "GO":
        return "doc_generator"
    if decision == "CONDITIONAL":
        return "conditional_review"
    return "feedback_generator"


async def conditional_review(state: VibeDeployState) -> dict:
    scoring = state.get("scoring", {})
    final_score = scoring.get("final_score", 0)

    user_response = interrupt(
        {
            "type": "conditional_review",
            "message": (
                f"Your idea scored {final_score}/100 (CONDITIONAL). "
                "Would you like to proceed with reduced scope, or cancel?"
            ),
            "score": final_score,
            "options": ["proceed", "cancel"],
        }
    )

    if isinstance(user_response, str) and user_response.lower() in ("proceed", "yes", "go"):
        return {
            "user_feedback": user_response,
            "phase": "conditional_accepted",
        }

    return {
        "user_feedback": user_response if isinstance(user_response, str) else "cancelled",
        "phase": "conditional_rejected",
    }


def route_conditional(state: VibeDeployState) -> str:
    phase = state.get("phase", "")
    if phase == "conditional_accepted":
        return "doc_generator"
    return "feedback_generator"


async def feedback_generator(state: VibeDeployState) -> dict:
    import json
    import re

    from langchain_gradient import ChatGradient

    scoring = state.get("scoring", {})
    idea = state.get("idea", {})
    analyses = state.get("council_analysis", {})
    cross_exam = state.get("cross_examination", {})

    llm = ChatGradient(model="openai-gpt-5-mini", temperature=0.5, max_tokens=3000)
    context = json.dumps(
        {
            "idea": idea,
            "scoring": scoring,
            "council_analyses": analyses,
            "cross_examination": cross_exam,
        },
        indent=2,
        ensure_ascii=False,
    )

    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": (
                    "You are a constructive product advisor. The Vibe Council has decided NOT to proceed "
                    "with building this app idea. Provide helpful, actionable feedback:\n"
                    "1. Key reasons for the NO-GO decision\n"
                    "2. Specific improvements that could change the verdict\n"
                    "3. Alternative directions worth exploring\n"
                    "4. What was strong about the idea\n"
                    "Return as JSON with keys: 'reasons', 'improvements', 'alternatives', 'strengths'"
                ),
            },
            {"role": "user", "content": f"Provide feedback for this idea:\n\n{context}"},
        ]
    )

    content = response.content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        feedback = json.loads(content)
    except (json.JSONDecodeError, TypeError, ValueError):
        feedback = {
            "reasons": [content[:500]],
            "improvements": [],
            "alternatives": [],
            "strengths": [],
        }

    return {
        "generated_docs": {
            "prd": "",
            "tech_spec": "",
            "api_spec": "",
            "db_schema": "",
            "app_spec_yaml": "",
        },
        "user_feedback": json.dumps(feedback, ensure_ascii=False),
        "phase": "feedback_delivered",
        "error": None,
    }
