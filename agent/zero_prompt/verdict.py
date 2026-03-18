"""GO/NO-GO Verdict Engine — deterministic scoring, no LLM calls."""

from agent.zero_prompt.schemas import Verdict


def compute_verdict_score(
    confidence: float,
    engagement: float,
    market_opportunity: int,
    novelty_boost: float,
    differentiation: int,
) -> int:
    """Compute a 0-100 verdict score from signal inputs.

    Formula:
        score = confidence*25
              + engagement*20
              + (market_opportunity/100)*25
              + min(novelty_boost/0.3, 1.0)*15
              + (differentiation/100)*15
    """
    score = (
        confidence * 25
        + engagement * 20
        + (market_opportunity / 100) * 25
        + min(novelty_boost / 0.3, 1.0) * 15
        + (differentiation / 100) * 15
    )
    return int(round(score))


def _no_go_reason_code(market_opportunity: int, differentiation: int, novelty_boost: float) -> str:
    if market_opportunity < 30:
        return "market_saturated"
    if differentiation < 30:
        return "weak_differentiation"
    if novelty_boost < 0.05:
        return "weak_paper_backing"
    return "low_confidence"


def determine_verdict(
    score: int,
    market_opportunity: int,
    novelty_boost: float,
    differentiation: int,
) -> Verdict:
    """Return a Verdict for the given score and signal values.

    Decision boundary:
        score >= 70 → GO
        score <  70 → NO_GO
    """
    if score >= 70:
        reason = (
            f"Strong signals across all axes (score {score}) — high potential opportunity."
            if score >= 80
            else f"Sufficient signals detected (score {score}) — viable opportunity."
        )
        return Verdict(score=score, decision="GO", reason=reason, reason_code="high_potential")

    reason_code = _no_go_reason_code(market_opportunity, differentiation, novelty_boost)
    reason_messages = {
        "market_saturated": f"Market opportunity is too low (score {score}); space appears saturated.",
        "weak_differentiation": f"Differentiation is insufficient (score {score}); idea lacks competitive edge.",
        "weak_paper_backing": f"Novelty boost is negligible (score {score}); weak academic or research backing.",
        "low_confidence": f"Overall confidence is too low to proceed (score {score}).",
    }
    return Verdict(
        score=score,
        decision="NO_GO",
        reason=reason_messages[reason_code],
        reason_code=reason_code,
    )
