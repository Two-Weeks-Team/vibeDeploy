import json
import logging
import re

logger = logging.getLogger(__name__)

# Directories and patterns that LLM-generated files must never target.
_BLOCKED_PATH_PREFIXES = (
    ".github/",
    ".git/",
    ".env",
    ".gradient/",
)

_BLOCKED_EXACT_FILES = {
    ".env",
    ".gitignore",
    "Dockerfile",
}


def parse_json_response(content: str, default: dict) -> dict:
    """Parse an LLM response that should contain JSON.

    Strips markdown fences, attempts ``json.loads``, and falls back to
    extracting the first ``{...}`` block via regex.  On total failure
    the *default* dict is returned with the raw response attached under
    the ``raw_response`` key.
    """
    content = content.strip()
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
                logger.warning(
                    "Failed to parse extracted JSON block (length=%d)",
                    len(json_match.group()),
                )

        logger.warning(
            "Returning default for unparseable LLM response (length=%d)",
            len(content),
        )
        result = dict(default)
        result["raw_response"] = content[:500]
        return result


def slugify(value: object, *, max_length: int = 0, fallback: str = "vibedeploy-app") -> str:
    """Convert *value* to a URL/repo-safe slug.

    * Non-alphanumeric characters (except hyphens) are removed.
    * Whitespace and underscores become single hyphens.
    * Consecutive hyphens are collapsed.
    * If *max_length* > 0 the slug is truncated and trailing hyphens
      are stripped.
    """
    text = str(value) if value else ""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    clean = re.sub(r"[\s_]+", "-", clean)
    clean = re.sub(r"-+", "-", clean)
    if max_length > 0:
        clean = clean[:max_length].strip("-")
    return clean or fallback


def is_safe_file_path(path: str) -> bool:
    """Return ``True`` when *path* is safe to write to a generated repo.

    Blocks sensitive directories (``.github/``, ``.git/``) and files
    (``.env``, ``Dockerfile``) that could be exploited via prompt
    injection.
    """
    normalized = path.lstrip("/")
    if normalized in _BLOCKED_EXACT_FILES:
        return False
    for prefix in _BLOCKED_PATH_PREFIXES:
        if normalized.startswith(prefix):
            return False
    return True
