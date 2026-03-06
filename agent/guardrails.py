import re

MAX_PROMPT_LENGTH = 5000
MIN_PROMPT_LENGTH = 10

PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

BLOCKED_PATTERNS = [
    re.compile(r"(?i)ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions"),
    re.compile(r"(?i)you\s+are\s+now\s+(?:a\s+)?(?:different|new)\s+(?:ai|assistant|bot)"),
    re.compile(r"(?i)(?:system|admin)\s*:\s*override"),
    re.compile(r"(?i)disregard\s+(?:your|all)\s+(?:rules|guidelines|instructions)"),
]


def validate_prompt(prompt: str) -> tuple[bool, str]:
    if not prompt or len(prompt.strip()) < MIN_PROMPT_LENGTH:
        return False, f"Prompt too short (min {MIN_PROMPT_LENGTH} chars)"

    if len(prompt) > MAX_PROMPT_LENGTH:
        return False, f"Prompt too long (max {MAX_PROMPT_LENGTH} chars)"

    for pattern in BLOCKED_PATTERNS:
        if pattern.search(prompt):
            return False, "Prompt contains disallowed content"

    return True, ""


def redact_pii(text: str) -> tuple[str, list[str]]:
    redacted = text
    found_types: list[str] = []

    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(redacted):
            found_types.append(pii_type)
            redacted = pattern.sub(f"[REDACTED_{pii_type.upper()}]", redacted)

    return redacted, found_types


def sanitize_input(prompt: str) -> tuple[str, bool, str, list[str]]:
    valid, error = validate_prompt(prompt)
    if not valid:
        return prompt, False, error, []

    sanitized, pii_found = redact_pii(prompt)
    return sanitized, True, "", pii_found
