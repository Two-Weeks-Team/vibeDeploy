import asyncio
import json
import logging
import os
import re

logger = logging.getLogger(__name__)


async def enrich_card_with_gemini(
    video_title: str,
    transcript_text: str,
    idea_name: str,
    idea_domain: str,
    idea_features: list[str],
    paper_titles: list[str],
    market_gaps: list[str],
    competitors_count: int,
) -> dict:
    api_key = (
        os.environ.get("GOOGLE_API_KEY", "")
        or os.environ.get("GOOGLE_GENAI_API_KEY", "")
        or os.environ.get("GEMINI_API_KEY", "")
    )
    if not api_key:
        return _rule_based_enrichment(video_title, transcript_text, idea_name, idea_domain, idea_features, market_gaps)

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        context = f"Video: {video_title}\n"
        if transcript_text:
            context += f"Transcript (first 500 chars): {transcript_text[:500]}\n"
        context += f"Idea: {idea_name} (domain: {idea_domain})\n"
        if idea_features:
            context += f"Features: {', '.join(idea_features[:5])}\n"
        if paper_titles:
            context += f"Related papers: {', '.join(paper_titles[:3])}\n"
        if market_gaps:
            context += f"Market gaps: {', '.join(market_gaps[:3])}\n"
        context += f"Competitors found: {competitors_count}\n"

        prompt = (
            f"{context}\n"
            "Based on this analysis, return JSON with:\n"
            '1. "video_summary": 2-3 sentence summary of the video/idea (English)\n'
            '2. "insights": array of 3-5 actionable insights (English, each 1 sentence)\n'
            '3. "mvp_proposal": object with:\n'
            '   - "app_name": catchy English app name\n'
            '   - "target_user": one-line primary user definition (English)\n'
            '   - "core_feature": one-line core feature description (English)\n'
            '   - "tech_stack": recommended tech stack\n'
            '   - "key_pages": array of 3-4 main pages/screens (English)\n'
            '   - "estimated_days": number (1-7)\n'
            "Return ONLY valid JSON, no markdown."
        )

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = response.text or ""
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text.strip())

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                return _rule_based_enrichment(
                    video_title, transcript_text, idea_name, idea_domain, idea_features, market_gaps
                )

        return {
            "video_summary": str(data.get("video_summary", "")),
            "insights": [str(i) for i in data.get("insights", [])][:5],
            "mvp_proposal": data.get("mvp_proposal", {}),
        }

    except Exception:
        logger.exception("[CardEnrichment] Gemini enrichment failed, using rule-based")
        return _rule_based_enrichment(video_title, transcript_text, idea_name, idea_domain, idea_features, market_gaps)


def _rule_based_enrichment(
    video_title: str,
    transcript_text: str,
    idea_name: str,
    idea_domain: str,
    idea_features: list[str],
    market_gaps: list[str],
) -> dict:
    summary = transcript_text[:200] if transcript_text else f"{video_title} — app idea in {idea_domain} domain"

    insights = []
    if idea_features:
        insights = [f"{f} is a key differentiating feature" for f in idea_features[:3]]
    if market_gaps:
        insights.extend([f"Market gap: {g}" for g in market_gaps[:2]])
    if not insights:
        insights = [
            f"New opportunity identified in {idea_domain} domain",
            "Rapid MVP launch enables early market validation",
            "Research-backed technology creates differentiation",
        ]

    mvp = {
        "app_name": idea_name or video_title[:30],
        "target_user": f"People looking for simpler {idea_domain} workflows" if idea_domain else "Busy consumers",
        "core_feature": f"Automation solution for {idea_domain} domain",
        "tech_stack": "Next.js + Tailwind CSS + FastAPI",
        "key_pages": ["Dashboard", "Data Input", "Analysis Results", "Settings"],
        "estimated_days": 3,
    }

    return {"video_summary": summary, "insights": insights[:5], "mvp_proposal": mvp}
