import asyncio
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

_YOUTUBE_URL_RE = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})")

_SEARCH_QUERIES = [
    "trending app development project ideas YouTube 2025 2026",
    "best SaaS side project ideas tutorial YouTube",
    "AI powered app ideas build deploy YouTube trending",
    "mobile app startup ideas coding tutorial YouTube viral",
    "web app project ideas for developers YouTube popular",
]


async def discover_videos_via_grounding(max_results: int = 15) -> list[tuple[str, str, str]]:
    api_key = (
        os.environ.get("GOOGLE_API_KEY", "")
        or os.environ.get("GOOGLE_GENAI_API_KEY", "")
        or os.environ.get("GEMINI_API_KEY", "")
    )
    if not api_key:
        return []

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        prompt = (
            "Find 15 trending YouTube videos about app development ideas, side projects, "
            "and SaaS startup concepts from the last 6 months. For each video, provide:\n"
            "1. YouTube video ID (the 11-character ID from the URL)\n"
            "2. Video title\n"
            "3. A one-sentence description of the app idea discussed\n\n"
            "Return ONLY a JSON array of objects with keys: video_id, title, description\n"
            'Example: [{"video_id": "dQw4w9WgXcQ", "title": "...", "description": "..."}]'
        )

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.7,
            ),
        )

        text = response.text or ""
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text.strip())
        json_match = re.search(r"\[.*\]", text, re.DOTALL)
        if not json_match:
            logger.warning("[GroundingDiscovery] No JSON array in response")
            return _parse_freeform(text, max_results)

        items = json.loads(json_match.group())
        results = []
        for item in items[:max_results]:
            vid = str(item.get("video_id", "")).strip()
            title = str(item.get("title", "")).strip()
            desc = str(item.get("description", "")).strip()
            if vid and title:
                results.append((vid, title, desc))

        logger.info("[GroundingDiscovery] Found %d videos via Gemini grounding", len(results))
        return results

    except Exception:
        logger.exception("[GroundingDiscovery] Gemini grounding failed")
        return []


def _parse_freeform(text: str, max_results: int) -> list[tuple[str, str, str]]:
    results = []
    video_ids = _YOUTUBE_URL_RE.findall(text)
    lines = text.split("\n")
    for vid in video_ids[:max_results]:
        title = ""
        for line in lines:
            if vid in line:
                clean = re.sub(r"https?://\S+", "", line).strip(" -•*[]():")
                if clean:
                    title = clean[:100]
                    break
        results.append((vid, title or f"YouTube video {vid}", ""))
    return results
