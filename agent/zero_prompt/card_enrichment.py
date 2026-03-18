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
            '1. "video_summary": 2-3 sentence summary of the video/idea (Korean)\n'
            '2. "insights": array of 3-5 actionable insights (Korean, each 1 sentence)\n'
            '3. "mvp_proposal": object with:\n'
            '   - "app_name": catchy app name\n'
            '   - "core_feature": one-line core feature description (Korean)\n'
            '   - "tech_stack": recommended tech stack\n'
            '   - "key_pages": array of 3-4 main pages/screens\n'
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
    summary = transcript_text[:200] if transcript_text else f"{video_title} — {idea_domain} 도메인의 앱 아이디어"

    insights = []
    if idea_features:
        insights = [f"{f} 기능이 핵심 차별화 포인트" for f in idea_features[:3]]
    if market_gaps:
        insights.extend([f"시장 갭: {g}" for g in market_gaps[:2]])
    if not insights:
        insights = [
            f"{idea_domain} 도메인에서 새로운 기회 발견",
            "빠른 MVP 출시로 시장 검증 가능",
            "논문 기반 기술 적용으로 차별화 가능",
        ]

    mvp = {
        "app_name": idea_name or video_title[:30],
        "core_feature": f"{idea_domain} 도메인 자동화 솔루션",
        "tech_stack": "Next.js + Tailwind CSS + FastAPI",
        "key_pages": ["대시보드", "데이터 입력", "분석 결과", "설정"],
        "estimated_days": 3,
    }

    return {"video_summary": summary, "insights": insights[:5], "mvp_proposal": mvp}
