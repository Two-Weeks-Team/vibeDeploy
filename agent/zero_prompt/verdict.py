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


def _is_generic_core_feature(core_feature: str) -> bool:
    lowered = core_feature.lower()
    return any(phrase in lowered for phrase in _GENERIC_CORE_FEATURE_PHRASES)


def _proposal_clarity_score(
    *,
    app_name: str,
    target_user: str,
    core_feature: str,
    tech_stack: str,
    key_pages: list[str],
) -> int:
    score = 0
    if app_name:
        score += 10 if _word_count(app_name) <= 4 else 6
    if core_feature:
        score += 12
        if _word_count(core_feature) >= 6 and not _is_generic_core_feature(core_feature):
            score += 18
        elif not _is_generic_core_feature(core_feature):
            score += 10
    if tech_stack:
        score += 15
    if target_user:
        score += 15

    non_generic_pages = [page for page in key_pages if page.lower() not in _GENERIC_PAGE_NAMES]
    if 3 <= len(key_pages) <= 5:
        score += 10
    elif key_pages:
        score += 5
    if len(non_generic_pages) >= 2:
        score += 20
    elif len(non_generic_pages) == 1:
        score += 10

    return _clamp(score)


def _execution_feasibility_score(
    *,
    estimated_days: int,
    tech_stack: str,
    key_pages: list[str],
    feature_count: int,
) -> int:
    score = 25
    if tech_stack:
        score += 20

    if 2 <= estimated_days <= 5:
        score += 25
    elif 1 <= estimated_days <= 7:
        score += 16
    elif estimated_days > 7:
        score += 8

    if 3 <= len(key_pages) <= 5:
        score += 15
    elif 1 <= len(key_pages) <= 6:
        score += 8

    if feature_count <= 4:
        score += 15
    elif feature_count <= 6:
        score += 8

    return _clamp(score)


def _market_viability_score(*, market_opportunity: int, target_audience: str, core_feature: str) -> int:
    audience_bonus = 15 if target_audience else 0
    feature_bonus = 10 if core_feature and not _is_generic_core_feature(core_feature) else 4 if core_feature else 0
    return _clamp(market_opportunity * 0.7 + audience_bonus + feature_bonus)


def _mvp_differentiation_score(
    *,
    novelty_boost: float,
    market_gap_count: int,
    app_name: str,
    target_user: str,
    core_feature: str,
    key_pages: list[str],
) -> int:
    proposal_distinctiveness = 20
    if app_name and _word_count(app_name) <= 4:
        proposal_distinctiveness += 8
    if target_user:
        proposal_distinctiveness += 12
    if core_feature and not _is_generic_core_feature(core_feature):
        proposal_distinctiveness += 20
    if _word_count(core_feature) >= 8:
        proposal_distinctiveness += 10
    proposal_distinctiveness += min(market_gap_count, 3) * 8
    proposal_distinctiveness += (
        10 if sum(1 for page in key_pages if page.lower() not in _GENERIC_PAGE_NAMES) >= 2 else 0
    )
    proposal_distinctiveness += round(min(novelty_boost / 0.3, 1.0) * 20)
    return _clamp(proposal_distinctiveness)


def _evidence_strength_score(*, papers_found: int, novelty_boost: float, core_feature: str, tech_stack: str) -> int:
    paper_score = min(papers_found, 3) / 3 * 25
    novelty_score = min(novelty_boost / 0.3, 1.0) * 20
    proposal_specificity = (
        30 if core_feature and not _is_generic_core_feature(core_feature) else 10 if core_feature else 0
    )
    stack_score = 25 if tech_stack else 10
    return _clamp(paper_score + novelty_score + proposal_specificity + stack_score)


def build_mvp_score_breakdown(
    *,
    mvp_proposal: dict[str, Any],
    market_opportunity: int,
    novelty_boost: float,
    papers_found: int,
    market_gap_count: int,
) -> dict[str, float | int]:
    app_name = _normalize_text(mvp_proposal.get("app_name"))
    target_user = _normalize_text(mvp_proposal.get("target_user"))
    core_feature = _normalize_text(mvp_proposal.get("core_feature"))
    tech_stack = _normalize_text(mvp_proposal.get("tech_stack"))
    key_pages = _normalize_pages(mvp_proposal.get("key_pages"))
    estimated_days = int(mvp_proposal.get("estimated_days") or 0)

    proposal_clarity = _proposal_clarity_score(
        app_name=app_name,
        target_user=target_user,
        core_feature=core_feature,
        tech_stack=tech_stack,
        key_pages=key_pages,
    )
    execution_feasibility = _execution_feasibility_score(
        estimated_days=estimated_days,
        tech_stack=tech_stack,
        key_pages=key_pages,
        feature_count=max(1, len(key_pages)),
    )
    market_viability = _market_viability_score(
        market_opportunity=market_opportunity,
        target_audience=target_user,
        core_feature=core_feature,
    )
    mvp_differentiation = _mvp_differentiation_score(
        novelty_boost=novelty_boost,
        market_gap_count=market_gap_count,
        app_name=app_name,
        target_user=target_user,
        core_feature=core_feature,
        key_pages=key_pages,
    )
    evidence_strength = _evidence_strength_score(
        papers_found=papers_found,
        novelty_boost=novelty_boost,
        core_feature=core_feature,
        tech_stack=tech_stack,
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
        "proposal_clarity_points": proposal_points,
        "execution_feasibility_points": execution_points,
        "market_viability_points": market_points,
        "mvp_differentiation_points": differentiation_points,
        "evidence_strength_points": evidence_points,
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
) -> str:
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
) -> Verdict:
    if score >= 70:
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
    )
    reason_messages = {
        "market_saturated": f"The proposed MVP still lands in a crowded market (score {score}) — market pull is not yet strong enough.",
        "weak_differentiation": f"The proposed MVP is still not differentiated enough (score {score}) — it needs a sharper wedge or clearer edge.",
        "technical_risk": f"The proposed MVP is too broad or execution-risky (score {score}) — scope and implementation path need tightening.",
        "weak_paper_backing": f"The proposed MVP lacks enough supporting evidence (score {score}) — validation and research backing are still thin.",
        "low_confidence": f"The proposed MVP is not yet convincing across clarity, execution, and evidence (score {score}).",
    }
    return Verdict(score=score, decision="NO_GO", reason=reason_messages[reason_code], reason_code=reason_code)
