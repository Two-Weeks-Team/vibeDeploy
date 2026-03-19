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
        originality=75,
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
        originality=20,
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
        originality=65,
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
        originality=30,
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
        originality=65,
    )
    assert result.reason_code == "technical_risk"
    assert result.decision == "NO_GO"


def test_reason_code_weak_paper_backing():
    result = determine_verdict(
        score=50,
        market_viability=60,
        mvp_differentiation=65,
        execution_feasibility=60,
        evidence_strength=30,
        novelty_boost=0.01,
        originality=65,
    )
    assert result.reason_code == "weak_paper_backing"
    assert result.decision == "NO_GO"


def test_reason_code_low_confidence():
    result = determine_verdict(
        score=50,
        market_viability=60,
        mvp_differentiation=65,
        execution_feasibility=60,
        evidence_strength=35,
        novelty_boost=0.2,
        originality=65,
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
        originality=80,
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
        originality=65,
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
        originality=60,
    )
    assert result.decision == "NO_GO"


def test_gate_blocked_high_score_is_clamped_for_display():
    result = determine_verdict(
        score=78,
        market_viability=65,
        mvp_differentiation=72,
        execution_feasibility=75,
        evidence_strength=55,
        novelty_boost=0.12,
        originality=45,
    )
    assert result.decision == "NO_GO"
    assert result.score == 69


def test_nutrition_mvp_can_clear_go_threshold():
    breakdown = build_mvp_score_breakdown(
        mvp_proposal={
            "app_name": "NutriPlan",
            "target_user": "Busy adults who want simpler meal planning",
            "problem_statement": "People trying to eat better waste time translating fitness goals into actual weekly meals and shopping decisions.",
            "core_feature": "Create a weekly nutrition plan from health goals, pantry items, and budget in one guided flow.",
            "differentiation": "Turns meal planning into one personalized planning workflow instead of a generic calorie tracker or recipe list.",
            "validation_signal": "Users already pay coaches and meal-planning apps to reduce planning time and decision fatigue.",
            "tech_stack": "Next.js + FastAPI + PostgreSQL + Gemini",
            "key_pages": ["Onboarding", "Weekly Meal Plan", "Grocery List", "Nutrition Insights"],
            "not_in_scope": ["Social feed", "Coach marketplace", "Wearable integrations"],
            "estimated_days": 5,
        },
        market_opportunity=52,
        novelty_boost=0.08,
        relevant_papers=2,
        avg_paper_relevance=0.41,
        market_gap_count=2,
        market_search_confidence="high",
    )
    assert breakdown["final_score"] >= 70
    assert breakdown["proposal_clarity_signal"] >= 70
    assert breakdown["execution_feasibility_signal"] >= 70
    assert breakdown["originality_signal"] >= 65


def test_generic_mvp_stays_below_go_threshold():
    breakdown = build_mvp_score_breakdown(
        mvp_proposal={
            "app_name": "Nutrition App",
            "target_user": "",
            "problem_statement": "People want better nutrition.",
            "core_feature": "Automation solution for nutrition domain",
            "differentiation": "A better experience than existing tools.",
            "validation_signal": "No concrete validation signal available from fallback enrichment.",
            "tech_stack": "Next.js + FastAPI",
            "key_pages": ["Dashboard", "Settings", "Results"],
            "not_in_scope": [],
            "estimated_days": 3,
        },
        market_opportunity=52,
        novelty_boost=0.01,
        relevant_papers=0,
        avg_paper_relevance=0.0,
        market_gap_count=0,
        market_search_confidence="normal",
    )
    assert breakdown["final_score"] < 70
    assert breakdown["originality_signal"] < 65


def test_generic_business_idea_directory_stays_below_go_threshold():
    breakdown = build_mvp_score_breakdown(
        mvp_proposal={
            "app_name": "AI Income Catalyst",
            "target_user": "Busy professionals",
            "problem_statement": "People want to earn money with AI.",
            "core_feature": "Discover AI business ideas and free tools in one place.",
            "differentiation": "Combines ideas, tools, and success stories in one platform.",
            "validation_signal": "Creators often talk about earning money with AI.",
            "tech_stack": "Next.js + Firebase + Tailwind CSS",
            "key_pages": ["Home", "Explore Business Ideas", "Free AI Tools Directory", "Success Stories"],
            "not_in_scope": ["Community forum"],
            "estimated_days": 6,
        },
        market_opportunity=64,
        novelty_boost=0.12,
        relevant_papers=0,
        avg_paper_relevance=0.05,
        market_gap_count=0,
        market_search_confidence="normal",
    )
    assert breakdown["final_score"] < 70
    assert breakdown["mvp_differentiation_signal"] < 60
    assert breakdown["originality_signal"] < 65


def test_verdict_model_structure():
    result = determine_verdict(
        score=70,
        market_viability=60,
        mvp_differentiation=60,
        execution_feasibility=75,
        evidence_strength=55,
        novelty_boost=0.12,
        originality=60,
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
