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


CONTENT_MODERATION_PATTERNS = [
    re.compile(r"(?i)\b(?:hack|exploit|attack)\s+(?:a|the|this)\s+(?:website|server|system|database)\b"),
    re.compile(r"(?i)\b(?:create|build|make)\s+(?:a\s+)?(?:malware|virus|ransomware|trojan|keylogger)\b"),
    re.compile(r"(?i)\b(?:ddos|sql\s*injection|xss|cross-site)\b"),
    re.compile(r"(?i)\b(?:phishing|credential\s*harvest|social\s*engineer)\b"),
    re.compile(r"(?i)\b(?:steal|scrape)\s+(?:personal|user|customer)\s+(?:data|info|information)\b"),
]

JAILBREAK_PATTERNS = [
    re.compile(r"(?i)pretend\s+(?:you\s+are|to\s+be)\s+(?:an?\s+)?(?:unrestricted|unfiltered|evil)"),
    re.compile(r"(?i)(?:DAN|do\s+anything\s+now)\s+mode"),
    re.compile(r"(?i)roleplay\s+as\s+(?:an?\s+)?(?:hacker|attacker|malicious)"),
    re.compile(r"(?i)bypass\s+(?:your|all|any)\s+(?:safety|content|ethical)\s+(?:filter|guardrail|restriction)"),
    re.compile(r"(?i)respond\s+without\s+(?:any\s+)?(?:filter|restriction|limitation|safety)"),
]


def _check_patterns(prompt: str, patterns: list[re.Pattern], message: str) -> tuple[bool, str]:
    for pattern in patterns:
        if pattern.search(prompt):
            return False, message
    return True, ""


def check_content_moderation(prompt: str) -> tuple[bool, str]:
    return _check_patterns(
        prompt, CONTENT_MODERATION_PATTERNS, "Content blocked: request involves harmful or malicious activity"
    )


def check_jailbreak(prompt: str) -> tuple[bool, str]:
    return _check_patterns(prompt, JAILBREAK_PATTERNS, "Content blocked: jailbreak attempt detected")


def sanitize_input(prompt: str) -> tuple[str, bool, str, list[str]]:
    valid, error = validate_prompt(prompt)
    if not valid:
        return prompt, False, error, []

    safe, moderation_error = check_content_moderation(prompt)
    if not safe:
        return prompt, False, moderation_error, []

    safe, jailbreak_error = check_jailbreak(prompt)
    if not safe:
        return prompt, False, jailbreak_error, []

    sanitized, pii_found = redact_pii(prompt)
    return sanitized, True, "", pii_found
