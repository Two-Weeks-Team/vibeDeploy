from __future__ import annotations

import re
from typing import Any

from agent.zero_prompt.schemas import Verdict

_GENERIC_PAGE_NAMES = {
    "dashboard",
    "home",
    "landing",
    "settings",
    "profile",
    "results",
    "analysis results",
    "data input",
}

_GENERIC_CORE_FEATURE_PHRASES = (
    "automation solution",
    "app for",
    "platform for",
    "tool for",
    "dashboard for",
    "solution for",
)

_GENERIC_AUDIENCE_PHRASES = (
    "busy professionals",
    "busy consumers",
    "people looking for",
    "everyone",
    "anyone",
    "users",
    "individuals",
)

_COMMODITY_MVP_MARKERS = (
    "directory",
    "business ideas",
    "idea platform",
    "idea generator",
    "discover ideas",
    "idea finder",
    "inspiration",
    "resource library",
    "tools directory",
    "free tools",
    "success stories",
    "featured ideas",
)

_VALIDATION_WEAK_MARKERS = (
    "no concrete validation signal",
    "generic demand",
    "could help",
    "might help",
)


def _clamp(value: float, lower: int = 0, upper: int = 100) -> int:
    return int(round(max(lower, min(upper, value))))


def _normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _normalize_pages(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _word_count(text: str) -> int:
    return len([part for part in re.split(r"[^a-zA-Z0-9]+", text) if part])


def _tokenize_text(text: str) -> set[str]:
    return {part for part in re.split(r"[^a-zA-Z0-9]+", text.lower()) if len(part) >= 3}


def _is_generic_core_feature(core_feature: str) -> bool:
    lowered = core_feature.lower()
    return any(phrase in lowered for phrase in _GENERIC_CORE_FEATURE_PHRASES)


def _is_generic_target_user(target_user: str) -> bool:
    lowered = target_user.lower()
    return any(phrase in lowered for phrase in _GENERIC_AUDIENCE_PHRASES)


def _is_weak_validation_signal(validation_signal: str) -> bool:
    if not validation_signal:
        return True
    lowered = validation_signal.lower()
    return any(marker in lowered for marker in _VALIDATION_WEAK_MARKERS)


def _commodity_marker_count(core_feature: str, key_pages: list[str]) -> int:
    lowered = " ".join([core_feature, *key_pages]).lower()
    return sum(1 for marker in _COMMODITY_MVP_MARKERS if marker in lowered)


def _originality_score(
    *,
    target_user: str,
    problem_statement: str,
    core_feature: str,
    differentiation: str,
    validation_signal: str,
    key_pages: list[str],
    market_gap_count: int,
    novelty_boost: float,
) -> int:
    score = 45
    score += _specificity_score(problem_statement) * 0.14
    score += _specificity_score(differentiation) * 0.18
    score += 10 if validation_signal and not _is_weak_validation_signal(validation_signal) else -12
    score += 8 if target_user and not _is_generic_target_user(target_user) else -10
    score += min(market_gap_count, 3) * 6
    score += min(novelty_boost / 0.3, 1.0) * 12

    commodity_count = _commodity_marker_count(f"{problem_statement} {core_feature} {differentiation}", key_pages)
    score -= commodity_count * 14

    if _is_generic_core_feature(core_feature):
        score -= 14
    if len([page for page in key_pages if page.lower() not in _GENERIC_PAGE_NAMES]) < 2:
        score -= 8

    lowered = " ".join([problem_statement, core_feature, differentiation, validation_signal]).lower()
    if "business ideas" in lowered or "free tools" in lowered:
        score -= 12

    return _clamp(score)


def _specificity_score(text: str) -> int:
    if not text:
        return 0
    words = _word_count(text)
    if words >= 12:
        return 100
    if words >= 8:
        return 80
    if words >= 5:
        return 60
    if words >= 3:
        return 40
    return 20


def measure_paper_support(query: str, papers: list[Any]) -> tuple[int, float]:
    query_tokens = _tokenize_text(query)
    if not query_tokens or not papers:
        return 0, 0.0

    relevant = 0
    relevance_sum = 0.0
    for paper in papers:
        title = _normalize_text(getattr(paper, "title", ""))
        abstract = _normalize_text(getattr(paper, "abstract", ""))
        text_tokens = _tokenize_text(f"{title} {abstract}")
        if not text_tokens:
            continue
        overlap_ratio = len(query_tokens & text_tokens) / max(len(query_tokens), 1)
        if overlap_ratio >= 0.18 or len(query_tokens & text_tokens) >= 3:
            relevant += 1
            relevance_sum += overlap_ratio

    avg_relevance = relevance_sum / relevant if relevant else 0.0
    return relevant, round(avg_relevance, 4)


def _proposal_clarity_score(
    *,
    app_name: str,
    target_user: str,
    problem_statement: str,
    core_feature: str,
    differentiation: str,
    tech_stack: str,
    key_pages: list[str],
) -> int:
    score = 0
    if app_name:
        score += 8 if _word_count(app_name) <= 4 else 4
    score += _specificity_score(problem_statement) * 0.18
    if core_feature and not _is_generic_core_feature(core_feature):
        score += 12
        score += _specificity_score(core_feature) * 0.2
    if tech_stack:
        score += 8
    if target_user and not _is_generic_target_user(target_user):
        score += _specificity_score(target_user) * 0.16
    if differentiation:
        score += _specificity_score(differentiation) * 0.16

    non_generic_pages = [page for page in key_pages if page.lower() not in _GENERIC_PAGE_NAMES]
    if 2 <= len(key_pages) <= 4:
        score += 8
    elif key_pages:
        score += 2
    if len(non_generic_pages) >= 2:
        score += 18
    elif len(non_generic_pages) == 1:
        score += 6

    if _is_generic_target_user(target_user):
        score -= 12
    if _commodity_marker_count(core_feature, key_pages) >= 2:
        score -= 10

    return _clamp(score)


def _execution_feasibility_score(
    *,
    estimated_days: int,
    tech_stack: str,
    key_pages: list[str],
    not_in_scope: list[str],
) -> int:
    score = 0
    if tech_stack:
        score += 15

    if 3 <= estimated_days <= 6:
        score += 25
    elif 1 <= estimated_days <= 7:
        score += 12
    elif estimated_days > 7:
        score += 4

    if 2 <= len(key_pages) <= 4:
        score += 15
    elif 1 <= len(key_pages) <= 5:
        score += 8

    if len(not_in_scope) >= 2:
        score += 20
    elif len(not_in_scope) == 1:
        score += 8

    if _commodity_marker_count("", key_pages) >= 2:
        score -= 8

    return _clamp(score)


def _market_viability_score(*, market_opportunity: int, target_user: str, validation_signal: str) -> int:
    audience_bonus = 15 if target_user and not _is_generic_target_user(target_user) else 5 if target_user else 0
    validation_bonus = 15 if validation_signal and not _is_weak_validation_signal(validation_signal) else 0
    return _clamp(market_opportunity * 0.55 + audience_bonus + validation_bonus)


def _mvp_differentiation_score(
    *,
    novelty_boost: float,
    market_gap_count: int,
    app_name: str,
    target_user: str,
    core_feature: str,
    differentiation: str,
    key_pages: list[str],
) -> int:
    proposal_distinctiveness = 0
    if app_name and _word_count(app_name) <= 4:
        proposal_distinctiveness += 8
    if target_user and not _is_generic_target_user(target_user):
        proposal_distinctiveness += 12
    if core_feature and not _is_generic_core_feature(core_feature):
        proposal_distinctiveness += 20
    if _word_count(core_feature) >= 8:
        proposal_distinctiveness += 10
    if differentiation:
        proposal_distinctiveness += _specificity_score(differentiation) * 0.18
    proposal_distinctiveness += min(market_gap_count, 3) * 8
    proposal_distinctiveness += (
        10 if sum(1 for page in key_pages if page.lower() not in _GENERIC_PAGE_NAMES) >= 2 else 0
    )
    proposal_distinctiveness += round(min(novelty_boost / 0.3, 1.0) * 20)
    proposal_distinctiveness -= _commodity_marker_count(core_feature, key_pages) * 10
    return _clamp(proposal_distinctiveness)


def _evidence_strength_score(
    *,
    relevant_papers: int,
    avg_paper_relevance: float,
    novelty_boost: float,
    validation_signal: str,
    market_search_confidence: str,
) -> int:
    paper_score = min(relevant_papers, 3) / 3 * 35
    relevance_score = min(avg_paper_relevance / 0.35, 1.0) * 20
    novelty_score = min(novelty_boost / 0.3, 1.0) * 20
    validation_score = 15 if validation_signal and not _is_weak_validation_signal(validation_signal) else 0
    market_confidence_score = (
        10 if market_search_confidence == "high" else 4 if market_search_confidence == "normal" else 0
    )
    return _clamp(paper_score + relevance_score + novelty_score + validation_score + market_confidence_score)


def build_mvp_score_breakdown(
    *,
    mvp_proposal: dict[str, Any],
    market_opportunity: int,
    novelty_boost: float,
    relevant_papers: int,
    avg_paper_relevance: float,
    market_gap_count: int,
    market_search_confidence: str,
) -> dict[str, float | int]:
    app_name = _normalize_text(mvp_proposal.get("app_name"))
    target_user = _normalize_text(mvp_proposal.get("target_user"))
    problem_statement = _normalize_text(mvp_proposal.get("problem_statement"))
    core_feature = _normalize_text(mvp_proposal.get("core_feature"))
    differentiation = _normalize_text(mvp_proposal.get("differentiation"))
    validation_signal = _normalize_text(mvp_proposal.get("validation_signal"))
    tech_stack = _normalize_text(mvp_proposal.get("tech_stack"))
    key_pages = _normalize_pages(mvp_proposal.get("key_pages"))
    not_in_scope = _normalize_pages(mvp_proposal.get("not_in_scope"))
    estimated_days = int(mvp_proposal.get("estimated_days") or 0)

    proposal_clarity = _proposal_clarity_score(
        app_name=app_name,
        target_user=target_user,
        problem_statement=problem_statement,
        core_feature=core_feature,
        differentiation=differentiation,
        tech_stack=tech_stack,
        key_pages=key_pages,
    )
    execution_feasibility = _execution_feasibility_score(
        estimated_days=estimated_days,
        tech_stack=tech_stack,
        key_pages=key_pages,
        not_in_scope=not_in_scope,
    )
    market_viability = _market_viability_score(
        market_opportunity=market_opportunity,
        target_user=target_user,
        validation_signal=validation_signal,
    )
    mvp_differentiation = _mvp_differentiation_score(
        novelty_boost=novelty_boost,
        market_gap_count=market_gap_count,
        app_name=app_name,
        target_user=target_user,
        core_feature=core_feature,
        differentiation=differentiation,
        key_pages=key_pages,
    )
    evidence_strength = _evidence_strength_score(
        relevant_papers=relevant_papers,
        avg_paper_relevance=avg_paper_relevance,
        novelty_boost=novelty_boost,
        validation_signal=validation_signal,
        market_search_confidence=market_search_confidence,
    )
    originality = _originality_score(
        target_user=target_user,
        problem_statement=problem_statement,
        core_feature=core_feature,
        differentiation=differentiation,
        validation_signal=validation_signal,
        key_pages=key_pages,
        market_gap_count=market_gap_count,
        novelty_boost=novelty_boost,
    )

    proposal_points = round((proposal_clarity / 100) * 25, 1)
    execution_points = round((execution_feasibility / 100) * 20, 1)
    market_points = round((market_viability / 100) * 25, 1)
    differentiation_points = round((mvp_differentiation / 100) * 20, 1)
    evidence_points = round((evidence_strength / 100) * 10, 1)

    score = compute_verdict_score(
        proposal_clarity=proposal_clarity,
        execution_feasibility=execution_feasibility,
        market_viability=market_viability,
        mvp_differentiation=mvp_differentiation,
        evidence_strength=evidence_strength,
    )

    return {
        "proposal_clarity_weight": 25,
        "execution_feasibility_weight": 20,
        "market_viability_weight": 25,
        "mvp_differentiation_weight": 20,
        "evidence_strength_weight": 10,
        "proposal_clarity_signal": proposal_clarity,
        "execution_feasibility_signal": execution_feasibility,
        "market_viability_signal": market_viability,
        "mvp_differentiation_signal": mvp_differentiation,
        "evidence_strength_signal": evidence_strength,
        "originality_signal": originality,
        "originality_threshold": 55,
        "proposal_clarity_points": proposal_points,
        "execution_feasibility_points": execution_points,
        "market_viability_points": market_points,
        "mvp_differentiation_points": differentiation_points,
        "evidence_strength_points": evidence_points,
        "relevant_papers_signal": relevant_papers,
        "avg_paper_relevance_signal": round(avg_paper_relevance * 100, 1),
        "final_score": score,
    }


def compute_verdict_score(
    *,
    proposal_clarity: int,
    execution_feasibility: int,
    market_viability: int,
    mvp_differentiation: int,
    evidence_strength: int,
) -> int:
    score = (
        (proposal_clarity / 100) * 25
        + (execution_feasibility / 100) * 20
        + (market_viability / 100) * 25
        + (mvp_differentiation / 100) * 20
        + (evidence_strength / 100) * 10
    )
    return int(round(score))


def _no_go_reason_code(
    *,
    market_viability: int,
    mvp_differentiation: int,
    execution_feasibility: int,
    evidence_strength: int,
    novelty_boost: float,
    originality: int,
) -> str:
    if originality < 55:
        return "weak_differentiation"
    if execution_feasibility < 55:
        return "technical_risk"
    if market_viability < 55:
        return "market_saturated"
    if mvp_differentiation < 60:
        return "weak_differentiation"
    if evidence_strength < 45 and novelty_boost < 0.08:
        return "weak_paper_backing"
    if market_viability < 45:
        return "market_saturated"
    if mvp_differentiation < 45:
        return "weak_differentiation"
    if execution_feasibility < 45:
        return "technical_risk"
    if evidence_strength < 40 and novelty_boost < 0.05:
        return "weak_paper_backing"
    return "low_confidence"


def determine_verdict(
    *,
    score: int,
    market_viability: int,
    mvp_differentiation: int,
    execution_feasibility: int,
    evidence_strength: int,
    novelty_boost: float,
    originality: int,
) -> Verdict:
    if (
        score >= 70
        and market_viability >= 55
        and mvp_differentiation >= 60
        and execution_feasibility >= 55
        and evidence_strength >= 45
        and originality >= 55
    ):
        reason = (
            f"The proposed MVP is concrete, scoped, and differentiated enough to build (score {score})."
            if score >= 80
            else f"The proposed MVP is viable and execution-ready with manageable risk (score {score})."
        )
        return Verdict(score=score, decision="GO", reason=reason, reason_code="high_potential")

    reason_code = _no_go_reason_code(
        market_viability=market_viability,
        mvp_differentiation=mvp_differentiation,
        execution_feasibility=execution_feasibility,
        evidence_strength=evidence_strength,
        novelty_boost=novelty_boost,
        originality=originality,
    )
    reason_messages = {
        "market_saturated": f"The proposed MVP still lands in a crowded market (score {score}) — market pull is not yet strong enough.",
        "weak_differentiation": f"The proposed MVP is still not differentiated enough (score {score}) — it needs a sharper wedge or clearer edge.",
        "technical_risk": f"The proposed MVP is too broad or execution-risky (score {score}) — scope and implementation path need tightening.",
        "weak_paper_backing": f"The proposed MVP lacks enough supporting evidence (score {score}) — validation and research backing are still thin.",
        "low_confidence": f"The proposed MVP is not yet convincing across clarity, execution, and evidence (score {score}).",
    }
    return Verdict(score=score, decision="NO_GO", reason=reason_messages[reason_code], reason_code=reason_code)
