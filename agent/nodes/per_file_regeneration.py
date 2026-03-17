import logging
from dataclasses import dataclass, field

from agent.nodes.per_file_code_generator import validate_generated_file

logger = logging.getLogger(__name__)

TEMPERATURE_SCHEDULE: list[float] = [0.1, 0.05, 0.02]

_JS_TS_EXTS = frozenset({"ts", "tsx", "js", "jsx", "mjs", "cjs"})


@dataclass
class RegenerationResult:
    path: str
    content: str
    attempts: int
    used_fallback: bool
    temperatures_used: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def get_temperature_for_attempt(attempt: int) -> float:
    idx = max(0, attempt - 1)
    if idx >= len(TEMPERATURE_SCHEDULE):
        return TEMPERATURE_SCHEDULE[-1]
    return TEMPERATURE_SCHEDULE[idx]


def build_regen_prompt(original_prompt: str, error: str, attempt: int) -> str:
    parts: list[str] = [f"[Attempt {attempt}]"]
    if error:
        parts.append(f"Previous attempt failed with error:\n{error}\n\nPlease fix the error and try again.")
    parts.append(f"Task:\n{original_prompt}")
    return "\n\n".join(parts)


def regenerate_file(
    path: str,
    original_prompt: str,
    content_factory,
    *,
    max_retries: int = 3,
) -> RegenerationResult:
    temperatures_used: list[float] = []
    errors: list[str] = []

    for attempt in range(1, max_retries + 1):
        previous_error = errors[-1] if errors else ""
        prompt = build_regen_prompt(original_prompt, previous_error, attempt)
        temp = get_temperature_for_attempt(attempt)
        temperatures_used.append(temp)

        try:
            content = content_factory(prompt, temp)
        except Exception as exc:
            error_msg = f"content_factory raised: {exc}"
            errors.append(error_msg)
            logger.warning("[REGEN] attempt %d/%d factory error for %s: %s", attempt, max_retries, path, exc)
            continue

        result = validate_generated_file(path, content)
        if result["passed"]:
            logger.info(
                "[REGEN] %s succeeded on attempt %d/%d (success_rate=%.0f%%)",
                path,
                attempt,
                max_retries,
                (1 / attempt) * 100,
            )
            return RegenerationResult(
                path=path,
                content=content,
                attempts=attempt,
                used_fallback=False,
                temperatures_used=temperatures_used,
                errors=errors,
            )

        error_msg = str(result["error"])
        errors.append(error_msg)
        logger.warning(
            "[REGEN] attempt %d/%d validation failed for %s: %s",
            attempt,
            max_retries,
            path,
            error_msg,
        )

    logger.error("[REGEN] %s exhausted %d retries, returning fallback", path, max_retries)
    return RegenerationResult(
        path=path,
        content=_fallback_content(path),
        attempts=max_retries,
        used_fallback=True,
        temperatures_used=temperatures_used,
        errors=errors,
    )


def log_regeneration_stats(results: list[RegenerationResult]) -> dict:
    total = len(results)
    if total == 0:
        return {"total": 0, "succeeded": 0, "failed": 0, "fallback_count": 0, "avg_attempts": 0.0}

    fallback_count = sum(1 for r in results if r.used_fallback)
    return {
        "total": total,
        "succeeded": total - fallback_count,
        "failed": fallback_count,
        "fallback_count": fallback_count,
        "avg_attempts": sum(r.attempts for r in results) / total,
    }


def _fallback_content(path: str) -> str:
    dot = path.rfind(".")
    ext = path[dot + 1 :].lower() if dot != -1 else ""
    tag = "//" if ext in _JS_TS_EXTS else "#"
    return f"{tag} vibedeploy-regen-fallback: validation failed after max retries\n{tag} path: {path}\n"
