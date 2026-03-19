from agent.zero_prompt.verdict import build_mvp_score_breakdown, compute_verdict_score, determine_verdict


def test_score_above_70_returns_go():
    score = compute_verdict_score(
        proposal_clarity=85,
        execution_feasibility=80,
        market_viability=70,
        mvp_differentiation=75,
        evidence_strength=65,
    )
    result = determine_verdict(
        score=score,
        market_viability=70,
        mvp_differentiation=75,
        execution_feasibility=80,
        evidence_strength=65,
        novelty_boost=0.12,
    )
    assert result.decision == "GO"


def test_score_below_70_returns_no_go():
    score = compute_verdict_score(
        proposal_clarity=40,
        execution_feasibility=35,
        market_viability=30,
        mvp_differentiation=25,
        evidence_strength=20,
    )
    result = determine_verdict(
        score=score,
        market_viability=30,
        mvp_differentiation=25,
        execution_feasibility=35,
        evidence_strength=20,
        novelty_boost=0.0,
    )
    assert result.decision == "NO_GO"


def test_mvp_score_formula_basic():
    score = compute_verdict_score(
        proposal_clarity=100,
        execution_feasibility=100,
        market_viability=100,
        mvp_differentiation=100,
        evidence_strength=100,
    )
    assert score == 100


def test_mvp_score_formula_partial():
    score = compute_verdict_score(
        proposal_clarity=50,
        execution_feasibility=50,
        market_viability=50,
        mvp_differentiation=50,
        evidence_strength=50,
    )
    assert score == 50


def test_reason_code_market_saturated():
    result = determine_verdict(
        score=50,
        market_viability=20,
        mvp_differentiation=60,
        execution_feasibility=60,
        evidence_strength=60,
        novelty_boost=0.2,
    )
    assert result.reason_code == "market_saturated"
    assert result.decision == "NO_GO"


def test_reason_code_weak_differentiation():
    result = determine_verdict(
        score=50,
        market_viability=60,
        mvp_differentiation=20,
        execution_feasibility=60,
        evidence_strength=60,
        novelty_boost=0.2,
    )
    assert result.reason_code == "weak_differentiation"
    assert result.decision == "NO_GO"


def test_reason_code_technical_risk():
    result = determine_verdict(
        score=50,
        market_viability=60,
        mvp_differentiation=55,
        execution_feasibility=30,
        evidence_strength=60,
        novelty_boost=0.2,
    )
    assert result.reason_code == "technical_risk"
    assert result.decision == "NO_GO"


def test_reason_code_weak_paper_backing():
    result = determine_verdict(
        score=50,
        market_viability=60,
        mvp_differentiation=55,
        execution_feasibility=60,
        evidence_strength=30,
        novelty_boost=0.01,
    )
    assert result.reason_code == "weak_paper_backing"
    assert result.decision == "NO_GO"


def test_reason_code_low_confidence():
    result = determine_verdict(
        score=50,
        market_viability=60,
        mvp_differentiation=55,
        execution_feasibility=60,
        evidence_strength=35,
        novelty_boost=0.2,
    )
    assert result.reason_code == "low_confidence"
    assert result.decision == "NO_GO"


def test_reason_code_high_potential_on_high_score():
    result = determine_verdict(
        score=85,
        market_viability=80,
        mvp_differentiation=80,
        execution_feasibility=85,
        evidence_strength=75,
        novelty_boost=0.2,
    )
    assert result.reason_code == "high_potential"
    assert result.decision == "GO"


def test_boundary_score_70_is_go():
    result = determine_verdict(
        score=70,
        market_viability=55,
        mvp_differentiation=60,
        execution_feasibility=70,
        evidence_strength=55,
        novelty_boost=0.15,
    )
    assert result.decision == "GO"


def test_boundary_score_69_is_no_go():
    result = determine_verdict(
        score=69,
        market_viability=55,
        mvp_differentiation=60,
        execution_feasibility=70,
        evidence_strength=55,
        novelty_boost=0.15,
    )
    assert result.decision == "NO_GO"


def test_nutrition_mvp_can_clear_go_threshold():
    breakdown = build_mvp_score_breakdown(
        mvp_proposal={
            "app_name": "NutriPlan",
            "target_user": "Busy adults who want simpler meal planning",
            "core_feature": "Create a weekly nutrition plan from health goals, pantry items, and budget in one guided flow.",
            "tech_stack": "Next.js + FastAPI + PostgreSQL + Gemini",
            "key_pages": ["Onboarding", "Weekly Meal Plan", "Grocery List", "Nutrition Insights"],
            "estimated_days": 5,
        },
        market_opportunity=52,
        novelty_boost=0.08,
        papers_found=3,
        market_gap_count=2,
    )
    assert breakdown["final_score"] >= 70
    assert breakdown["proposal_clarity_signal"] >= 70
    assert breakdown["execution_feasibility_signal"] >= 70


def test_generic_mvp_stays_below_go_threshold():
    breakdown = build_mvp_score_breakdown(
        mvp_proposal={
            "app_name": "Nutrition App",
            "target_user": "",
            "core_feature": "Automation solution for nutrition domain",
            "tech_stack": "Next.js + FastAPI",
            "key_pages": ["Dashboard", "Settings", "Results"],
            "estimated_days": 3,
        },
        market_opportunity=52,
        novelty_boost=0.01,
        papers_found=0,
        market_gap_count=0,
    )
    assert breakdown["final_score"] < 70


def test_verdict_model_structure():
    result = determine_verdict(
        score=70,
        market_viability=60,
        mvp_differentiation=60,
        execution_feasibility=75,
        evidence_strength=55,
        novelty_boost=0.12,
    )
    assert type(result).__name__ == "Verdict"
    assert isinstance(result.score, int)
    assert result.decision in ("GO", "NO_GO")
    assert isinstance(result.reason, str)
    assert len(result.reason) > 0
    assert result.reason_code in (
        "high_potential",
        "market_saturated",
        "weak_differentiation",
        "low_confidence",
        "weak_paper_backing",
        "technical_risk",
    )
