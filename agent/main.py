"""vibeDeploy ADK Agent — Vibe Council evaluator.

Standalone entrypoint for Gradient ADK deployment.
Uses DO Serverless Inference directly (no relative imports).
The full LangGraph pipeline runs on App Platform via server.py.
"""

import json
import os
import traceback

import httpx
from gradient_adk import RequestContext, entrypoint

_INFERENCE_URL = "https://inference.do-ai.run/v1/chat/completions"
_MODEL = "openai-gpt-oss-120b"
_REASONING_MODEL = "openai-gpt-oss-120b"

_COUNCIL_AGENTS = {
    "architect": "You are the Architect — technical lead analyzing feasibility, complexity, tech stack, and whether the primary workflow can be shipped as a polished DigitalOcean app. Score technical_feasibility 0-100.",
    "scout": "You are the Scout — market analyst evaluating competition, trends, TAM, product-market fit, and whether the concept feels differentiated enough for the market. Score market_viability 0-100.",
    "guardian": "You are the Guardian — risk assessor identifying security, legal, scalability, trust, and failure risks. Score risk_profile 0-100 (higher = more risk).",
    "catalyst": "You are the Catalyst — innovation officer evaluating uniqueness, disruption potential, creative differentiation, and demo wow-factor. Score innovation_score 0-100.",
    "advocate": "You are the Advocate — UX champion assessing user experience, accessibility, onboarding, retention, and whether the product avoids generic dashboard patterns. Score user_impact 0-100.",
}


def _get_api_key() -> str:
    return os.environ.get("GRADIENT_MODEL_ACCESS_KEY", os.environ.get("DIGITALOCEAN_INFERENCE_KEY", ""))


async def _call_model(system: str, user: str, model: str = _MODEL) -> str:
    api_key = _get_api_key()
    if not api_key:
        return '{"error": "No API key configured"}'

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            _INFERENCE_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_completion_tokens": 1024,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content


async def _evaluate_idea(prompt: str) -> dict:
    analyses = {}
    for agent_name, system_prompt in _COUNCIL_AGENTS.items():
        try:
            raw = await _call_model(
                system=f'{system_prompt}\n\nRespond in JSON: {{"score": <0-100>, "reasoning": "...", "key_findings": ["..."]}}',
                user=f"Evaluate this app idea:\n\n{prompt}",
            )
            try:
                analyses[agent_name] = json.loads(raw)
            except json.JSONDecodeError:
                analyses[agent_name] = {"score": 50, "reasoning": raw[:500], "key_findings": []}
        except Exception as exc:
            analyses[agent_name] = {"score": 0, "reasoning": f"Error: {exc}", "key_findings": []}

    scores = {name: a.get("score", 50) for name, a in analyses.items()}
    risk = scores.get("guardian", 50)
    vibe_score = round(
        scores.get("architect", 50) * 0.25
        + scores.get("scout", 50) * 0.20
        + scores.get("catalyst", 50) * 0.20
        + (100 - risk) * 0.20
        + scores.get("advocate", 50) * 0.15,
        1,
    )

    if vibe_score >= 70:
        decision = "GO"
    elif vibe_score >= 50:
        decision = "CONDITIONAL"
    else:
        decision = "NO_GO"

    try:
        synthesis = await _call_model(
            system=(
                "You are the Strategist — synthesize the Vibe Council's analyses into a final verdict. "
                "Provide a concise summary, key strengths, key risks, recommendation, and whether the concept has a compelling first-use story."
            ),
            user=f"Idea: {prompt}\n\nCouncil analyses: {json.dumps(analyses, ensure_ascii=False)}\n\nVibe Score: {vibe_score} -> {decision}",
            model=_REASONING_MODEL,
        )
    except Exception:
        synthesis = f"Vibe Score: {vibe_score} -> {decision}"

    return {
        "vibe_score": vibe_score,
        "decision": decision,
        "analyses": analyses,
        "synthesis": synthesis,
    }


async def _brainstorm_idea(prompt: str) -> dict:
    try:
        raw = await _call_model(
            system=(
                "You are a creative brainstorming AI. Generate 5 innovative variations "
                "of the given app idea. For each, provide: name, tagline, key differentiator, "
                "signature experience or visual hook, and estimated technical complexity "
                "(low/medium/high). Respond in JSON array format."
            ),
            user=f"Brainstorm variations of this app idea:\n\n{prompt}",
        )
        try:
            ideas = json.loads(raw)
        except json.JSONDecodeError:
            ideas = raw
        return {"ideas": ideas}
    except Exception as exc:
        return {"error": str(exc)}


@entrypoint
async def main(input: dict, context: RequestContext):
    prompt = input.get("prompt", "")
    action = input.get("action", "evaluate")
    _ = context

    if not prompt:
        return {"error": 'No prompt provided. Send {"prompt": "your app idea"}'}

    try:
        if action == "brainstorm":
            result = await _brainstorm_idea(prompt)
        else:
            result = await _evaluate_idea(prompt)
        return {"response": result}
    except Exception as exc:
        return {"error": str(exc), "traceback": traceback.format_exc()[:1000]}
