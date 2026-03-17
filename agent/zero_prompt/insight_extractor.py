import logging
import os
import re

from agent.zero_prompt.schemas import AppIdea

logger = logging.getLogger(__name__)

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "healthcare": ["healthcare", "medical", "health", "patient", "doctor", "clinic", "hospital", "medicine", "therapy"],
    "finance": [
        "finance",
        "payment",
        "banking",
        "money",
        "investment",
        "budget",
        "expense",
        "wallet",
        "loan",
        "crypto",
    ],
    "education": ["education", "learning", "student", "course", "teaching", "school", "university", "quiz", "lesson"],
    "ecommerce": ["ecommerce", "shopping", "store", "product", "cart", "checkout", "order", "marketplace", "buy"],
    "social": ["social", "community", "network", "connect", "friends", "chat", "message", "feed", "profile"],
    "productivity": [
        "productivity",
        "task",
        "project",
        "workflow",
        "management",
        "schedule",
        "calendar",
        "todo",
        "kanban",
    ],
    "entertainment": ["entertainment", "game", "gaming", "music", "video", "media", "stream", "playlist", "podcast"],
    "travel": ["travel", "booking", "hotel", "flight", "tourism", "trip", "vacation", "itinerary", "destination"],
    "food": ["food", "restaurant", "recipe", "delivery", "menu", "cooking", "meal", "nutrition", "ingredient"],
    "fitness": ["fitness", "exercise", "workout", "gym", "sport", "training", "run", "yoga", "calories"],
}

# Regex patterns that identify feature-describing phrases in transcript lines
_FEATURE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bfeature[s]?\b[:\-–]?\s*(.+)", re.IGNORECASE),
    re.compile(r"\bfunction[s]?\b[:\-–]?\s*(.+)", re.IGNORECASE),
    re.compile(r"\bcapabilit(?:y|ies)\b[:\-–]?\s*(.+)", re.IGNORECASE),
    re.compile(r"\babilit(?:y|ies) to\s+(.+)", re.IGNORECASE),
    re.compile(r"\ballow[s]? (?:users? to|you to)\s+(.+)", re.IGNORECASE),
    re.compile(r"\bcan (?:also )?(.+)", re.IGNORECASE),
    re.compile(r"\bsupport[s]?\s+(.+)", re.IGNORECASE),
    re.compile(r"\binclude[s]?\s+(.+)", re.IGNORECASE),
]

# Confidence: length contributes up to 0.6 (scaled against _CONF_MAX_WORDS)
# and keyword density contributes up to 0.4
_CONF_MAX_WORDS = 500


def _detect_domain(text: str) -> str:
    lower = text.lower()
    scores: dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in lower)
        if count:
            scores[domain] = count
    if not scores:
        return "general"
    return max(scores, key=lambda d: scores[d])


def _extract_features(text: str) -> list[str]:
    features: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for pattern in _FEATURE_PATTERNS:
            m = pattern.search(line)
            if m:
                phrase = m.group(1).strip().rstrip(".,;:")
                if 3 <= len(phrase) <= 80 and phrase.lower() not in seen:
                    seen.add(phrase.lower())
                    features.append(phrase)
                break
    return features[:10]


def _compute_confidence(text: str, domain: str) -> float:
    word_count = len(text.split())
    if word_count == 0:
        return 0.0
    length_score = min(word_count, _CONF_MAX_WORDS) / _CONF_MAX_WORDS * 0.6
    if domain != "general":
        domain_kws = _DOMAIN_KEYWORDS.get(domain, [])
        lower = text.lower()
        hits = sum(1 for kw in domain_kws if kw in lower)
        density_score = min(hits / max(len(domain_kws), 1), 1.0) * 0.4
    else:
        density_score = 0.0
    return round(min(length_score + density_score, 1.0), 4)


def _derive_name(video_title: str, domain: str) -> str:
    if video_title:
        return " ".join(video_title.split()[:4])
    return f"{domain.title()} App"


def _derive_description(text: str, video_title: str) -> str:
    for sent in re.split(r"(?<=[.!?])\s+", text.strip()):
        sent = sent.strip()
        if 10 <= len(sent) <= 200:
            return sent
    if video_title:
        return f"App idea derived from: {video_title}"
    return "App idea extracted from transcript."


def _derive_audience(text: str, domain: str) -> str:
    lower = text.lower()
    for cue, label in [
        ("small business", "Small business owners"),
        ("enterprise", "Enterprise teams"),
        ("student", "Students"),
        ("developer", "Developers"),
        ("consumer", "General consumers"),
        ("professional", "Professionals"),
        ("team", "Teams and organizations"),
        ("user", "General users"),
    ]:
        if cue in lower:
            return label
    return {
        "healthcare": "Patients and healthcare providers",
        "finance": "Individuals and businesses managing finances",
        "education": "Students and educators",
        "ecommerce": "Online shoppers and merchants",
        "social": "Social media users",
        "productivity": "Professionals and teams",
        "entertainment": "General consumers",
        "travel": "Travelers and tourists",
        "food": "Food enthusiasts and restaurants",
        "fitness": "Fitness enthusiasts",
    }.get(domain, "General users")


def extract_insight_from_transcript(transcript_text: str, video_title: str = "") -> AppIdea:
    text = (transcript_text or "").strip()
    domain = _detect_domain(text or video_title)
    return AppIdea(
        name=_derive_name(video_title, domain),
        domain=domain,
        description=_derive_description(text, video_title),
        key_features=_extract_features(text),
        target_audience=_derive_audience(text, domain),
        confidence_score=_compute_confidence(text, domain),
    )


async def extract_with_gemini(transcript_text: str) -> AppIdea | None:
    api_key = os.environ.get("GOOGLE_GENAI_API_KEY", "").strip()
    if not api_key:
        logger.debug("GOOGLE_GENAI_API_KEY not set — skipping Gemini extraction")
        return None
    # TODO: wire real Gemini call — import google.generativeai, configure with api_key,
    #       call model.generate_content(transcript_text[:4000]), parse response into AppIdea.
    logger.info("GOOGLE_GENAI_API_KEY present — Gemini stub reached (not yet implemented)")
    return None
