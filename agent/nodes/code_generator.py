import asyncio
import json
import logging
import re

from ..llm import MODEL_CONFIG, get_llm
from ..prompts.code_templates import (
    BACKEND_SYSTEM_PROMPT,
    CODE_GENERATION_BASE_SYSTEM_PROMPT,
    FRONTEND_SYSTEM_PROMPT,
)
from ..state import VibeDeployState

logger = logging.getLogger(__name__)

# Minimum expected file counts for validation
_MIN_FRONTEND_FILES = 3  # At least package.json + 2 source files
_MIN_BACKEND_FILES = 2  # At least main.py + requirements.txt


async def code_generator(state: VibeDeployState) -> dict:
    generated_docs = state.get("generated_docs", {})
    idea = state.get("idea", {})

    llm = get_llm(
        model=MODEL_CONFIG["code_gen"],
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

    generation_warnings = []

    if len(frontend_code) < _MIN_FRONTEND_FILES:
        warning = (
            f"Frontend generation produced {len(frontend_code)} files "
            f"(expected >= {_MIN_FRONTEND_FILES}). "
            f"Files: {list(frontend_code.keys()) if frontend_code else '(none)'}"
        )
        logger.warning("[CODE_GEN] %s", warning)
        generation_warnings.append(warning)

        logger.info("[CODE_GEN] Retrying frontend generation (attempt 2)...")
        frontend_code = await _generate_frontend_files(llm, context, retry=True)

        if len(frontend_code) < _MIN_FRONTEND_FILES:
            retry_warning = (
                f"Frontend retry also produced {len(frontend_code)} files. "
                "Frontend will be omitted — backend-only deployment."
            )
            logger.warning("[CODE_GEN] %s", retry_warning)
            generation_warnings.append(retry_warning)

    if len(backend_code) < _MIN_BACKEND_FILES:
        warning = (
            f"Backend generation produced {len(backend_code)} files "
            f"(expected >= {_MIN_BACKEND_FILES}). "
            f"Files: {list(backend_code.keys()) if backend_code else '(none)'}"
        )
        logger.warning("[CODE_GEN] %s", warning)
        generation_warnings.append(warning)

    logger.info(
        "[CODE_GEN] Result: frontend=%d files, backend=%d files, warnings=%d",
        len(frontend_code),
        len(backend_code),
        len(generation_warnings),
    )

    return {
        "frontend_code": frontend_code,
        "backend_code": backend_code,
        "phase": "code_generated",
        "code_gen_warnings": generation_warnings,
    }


async def _generate_frontend_files(llm, context: str, retry: bool = False) -> dict[str, str]:
    extra_instruction = ""
    if retry:
        extra_instruction = (
            "\n\nCRITICAL: Your previous response could not be parsed as valid JSON. "
            'You MUST return ONLY a valid JSON object like: {"files": {"path": "content", ...}}. '
            "No markdown, no explanation — ONLY the JSON object."
        )

    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": (
                    f"{CODE_GENERATION_BASE_SYSTEM_PROMPT}\n\n"
                    f"{FRONTEND_SYSTEM_PROMPT}\n\n"
                    "Return JSON object with exactly one top-level key: 'files'."
                    f"{extra_instruction}"
                ),
            },
            {
                "role": "user",
                "content": f"Generate frontend files from this product context:\n\n{context}",
            },
        ]
    )

    parsed = _parse_json_response(response.content, {"files": {}}, label="frontend")
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

    parsed = _parse_json_response(response.content, {"files": {}}, label="backend")
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


def _parse_json_response(content, default: dict, label: str = "unknown") -> dict:
    from ..llm import content_to_str

    raw_content = content_to_str(content).strip()
    cleaned = raw_content
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(
            "[CODE_GEN] %s: Direct JSON parse failed (response length: %d chars)",
            label,
            len(raw_content),
        )

    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning(
                "[CODE_GEN] %s: Regex JSON extraction also failed",
                label,
            )

    logger.error(
        "[CODE_GEN] %s: All JSON parse attempts failed. Returning default. Response preview: %.200s",
        label,
        raw_content,
    )
    result = dict(default)
    result["raw_response"] = raw_content[:500]
    return result
