import asyncio
import json
import re

from ..llm import get_llm
from ..prompts.code_templates import (
    BACKEND_SYSTEM_PROMPT,
    CODE_GENERATION_BASE_SYSTEM_PROMPT,
    FRONTEND_SYSTEM_PROMPT,
)
from ..state import VibeDeployState


async def code_generator(state: VibeDeployState) -> dict:
    generated_docs = state.get("generated_docs", {})
    idea = state.get("idea", {})

    llm = get_llm(
        model="openai-gpt-5.3-codex",
        temperature=0.3,
        max_tokens=8000,
    )

    context = json.dumps(
        {
            "idea": idea,
            "generated_docs": generated_docs,
        },
        indent=2,
        ensure_ascii=False,
    )

    # Generate frontend and backend in parallel for 2x speed
    frontend_code, backend_code = await asyncio.gather(
        _generate_frontend_files(llm, context),
        _generate_backend_files(llm, context),
    )

    return {
        "frontend_code": frontend_code,
        "backend_code": backend_code,
        "phase": "code_generated",
    }


async def _generate_frontend_files(llm, context: str) -> dict[str, str]:
    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": (
                    f"{CODE_GENERATION_BASE_SYSTEM_PROMPT}\n\n"
                    f"{FRONTEND_SYSTEM_PROMPT}\n\n"
                    "Return JSON object with exactly one top-level key: 'files'."
                ),
            },
            {
                "role": "user",
                "content": f"Generate frontend files from this product context:\n\n{context}",
            },
        ]
    )

    parsed = _parse_json_response(response.content, {"files": {}})
    files = parsed.get("files", {})
    return _normalize_files_dict(files)


async def _generate_backend_files(llm, context: str) -> dict[str, str]:
    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": (
                    f"{CODE_GENERATION_BASE_SYSTEM_PROMPT}\n\n"
                    f"{BACKEND_SYSTEM_PROMPT}\n\n"
                    "Return JSON object with exactly one top-level key: 'files'."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Generate backend files from this product context. "
                    "AI features must be integral to business endpoints:\n\n"
                    f"{context}"
                ),
            },
        ]
    )

    parsed = _parse_json_response(response.content, {"files": {}})
    files = parsed.get("files", {})
    return _normalize_files_dict(files)


def _normalize_files_dict(files: object) -> dict[str, str]:
    if not isinstance(files, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in files.items():
        if isinstance(key, str) and isinstance(value, str):
            normalized[key] = value
    return normalized


def _parse_json_response(content, default: dict) -> dict:
    from ..llm import content_to_str

    content = content_to_str(content).strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        result = dict(default)
        result["raw_response"] = content[:500]
        return result
