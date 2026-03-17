import logging

from .schemas import MarketAnalysis, SearchResult
from .unified_search import unified_search

logger = logging.getLogger(__name__)


def _extract_competitors(results: list[SearchResult]) -> list[str]:
    seen: set[str] = set()
    competitors: list[str] = []
    for r in results:
        name = r.title.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            competitors.append(name)
    return competitors[:10]


def _estimate_saturation(results: list[SearchResult]) -> str:
    if len(results) >= 8:
        return "high"
    if len(results) >= 4:
        return "medium"
    return "low"


def _compute_opportunity_score(results: list[SearchResult], saturation: str) -> int:
    base = 50
    if saturation == "high":
        base = 30
    elif saturation == "low":
        base = 70

    high_confidence_count = sum(1 for r in results if r.confidence == "high")
    if high_confidence_count >= 3:
        base -= 10
    elif high_confidence_count == 0 and len(results) > 0:
        base += 10

    return max(0, min(100, base))


def _determine_search_confidence(results: list[SearchResult]) -> str:
    if not results:
        return "llm_only"
    has_high = any(r.confidence == "high" for r in results)
    return "high" if has_high else "normal"


_GAP_SIGNALS = [
    ("no mobile app", "Mobile app version is missing in current solutions"),
    ("limited api", "API access is limited or unavailable"),
    ("no free tier", "Free tier or freemium model is absent"),
    ("complex setup", "Setup complexity creates opportunity for simpler solutions"),
    ("slow", "Performance issues in existing solutions"),
]


def _identify_gaps(results: list[SearchResult]) -> list[str]:
    gaps: list[str] = []
    snippets = [r.snippet or "" for r in results if r.snippet]
    all_text = " ".join(snippets).lower()

    for signal, gap_description in _GAP_SIGNALS:
        if signal in all_text:
            gaps.append(gap_description)

    if not gaps and len(results) < 5:
        gaps.append("Market has few established players — early mover advantage possible")

    return gaps[:5]


async def analyze_competition(query: str, *, search_limit: int = 10) -> MarketAnalysis:
    try:
        results = await unified_search(query, limit=search_limit)
    except Exception:
        logger.exception("[CompetitiveAnalysis] Search failed entirely")
        results = []

    competitors = _extract_competitors(results)
    saturation = _estimate_saturation(results)
    score = _compute_opportunity_score(results, saturation)
    confidence = _determine_search_confidence(results)
    gaps = _identify_gaps(results)

    differentiation = ""
    if saturation == "high":
        differentiation = "Focus on underserved niches or superior UX to differentiate"
    elif saturation == "medium":
        differentiation = "Opportunity to compete with better execution and modern tech stack"
    else:
        differentiation = "Low competition — first-mover advantage with solid execution"

    return MarketAnalysis(
        market_opportunity_score=score,
        competitors=competitors,
        gaps=gaps,
        differentiation=differentiation,
        saturation_level=saturation,
        search_confidence=confidence,
    )
