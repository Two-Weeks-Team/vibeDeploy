import asyncio
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

_YT_ID_RE = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]{11})")
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


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
            "Search YouTube for 15 recent trending videos about:\n"
            "- SaaS startup ideas\n"
            "- App development project ideas\n"
            "- Side project tutorials\n"
            "- AI-powered app concepts\n\n"
            "For each video return the YouTube video ID (11 characters from the URL), "
            "the video title, and a short description of the app idea.\n\n"
            "Format as JSON array: "
            '[{"video_id":"XXXXXXXXXXX","title":"...","description":"..."}]'
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

        results = _extract_from_response(response, max_results)
        if results:
            logger.info("[GroundingDiscovery] Found %d videos", len(results))
            return results

        logger.warning("[GroundingDiscovery] Primary extraction returned 0, trying grounding metadata")
        return _extract_from_grounding_metadata(response, max_results)

    except Exception:
        logger.exception("[GroundingDiscovery] Gemini grounding failed")
        return []


def _extract_from_response(response, max_results: int) -> list[tuple[str, str, str]]:
    text = response.text or ""

    code_blocks = _JSON_BLOCK_RE.findall(text)
    for block in code_blocks:
        try:
            items = json.loads(block.strip())
            if isinstance(items, list):
                return _items_to_tuples(items, max_results)
        except json.JSONDecodeError:
            continue

    json_match = re.search(r"\[[\s\S]*?\]", text)
    if json_match:
        try:
            items = json.loads(json_match.group())
            if isinstance(items, list):
                return _items_to_tuples(items, max_results)
        except json.JSONDecodeError:
            pass

    return _parse_video_ids_from_text(text, max_results)


def _extract_from_grounding_metadata(response, max_results: int) -> list[tuple[str, str, str]]:
    results = []
    if not hasattr(response, "candidates") or not response.candidates:
        return results

    text = response.text or ""
    lines = text.split("\n")

    for candidate in response.candidates:
        metadata = getattr(candidate, "grounding_metadata", None)
        if not metadata:
            continue
        chunks = getattr(metadata, "grounding_chunks", []) or []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if not web:
                continue
            uri = getattr(web, "uri", "") or ""
            title = getattr(web, "title", "") or ""
            vid_ids = _YT_ID_RE.findall(uri)
            if not vid_ids:
                continue
            vid = vid_ids[0]
            display_title = title
            for line in lines:
                if vid in line or (title and title.lower() in line.lower()):
                    clean = re.sub(r"https?://\S+", "", line).strip(' -•*[]():\n"')
                    if len(clean) > 10:
                        display_title = clean[:120]
                        break
            results.append((vid, display_title or f"YouTube {vid}", ""))
            if len(results) >= max_results:
                break

    logger.info("[GroundingDiscovery] Extracted %d videos from grounding metadata", len(results))
    return results


def _parse_video_ids_from_text(text: str, max_results: int) -> list[tuple[str, str, str]]:
    results = []
    seen = set()
    lines = text.split("\n")
    for vid in _YT_ID_RE.findall(text):
        if vid in seen:
            continue
        seen.add(vid)
        title = ""
        for line in lines:
            if vid in line:
                clean = re.sub(r"https?://\S+", "", line).strip(' -•*[]():\n"')
                if len(clean) > 5:
                    title = clean[:120]
                    break
        results.append((vid, title or f"YouTube video {vid}", ""))
        if len(results) >= max_results:
            break
    return results


def _items_to_tuples(items: list, max_results: int) -> list[tuple[str, str, str]]:
    results = []
    for item in items[:max_results]:
        if not isinstance(item, dict):
            continue
        vid = str(item.get("video_id", "")).strip()
        title = str(item.get("title", "")).strip()
        desc = str(item.get("description", "")).strip()
        if vid and len(vid) >= 8 and title:
            results.append((vid, title, desc))
    return results
