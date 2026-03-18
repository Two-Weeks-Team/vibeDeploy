from agent.zero_prompt.verdict import compute_verdict_score, determine_verdict


def test_score_above_70_returns_go():
    score = compute_verdict_score(1.0, 1.0, 80, 0.5, 80)
    result = determine_verdict(score, 80, 0.5, 80)
    assert result.decision == "GO"


def test_score_below_70_returns_no_go():
    score = compute_verdict_score(0.0, 0.0, 10, 0.0, 10)
    result = determine_verdict(score, 10, 0.0, 10)
    assert result.decision == "NO_GO"


def test_score_formula_basic():
    score = compute_verdict_score(
        confidence=1.0,
        engagement=1.0,
        market_opportunity=100,
        novelty_boost=0.3,
        differentiation=100,
    )
    assert score == 100


def test_score_formula_partial():
    score = compute_verdict_score(
        confidence=0.5,
        engagement=0.5,
        market_opportunity=50,
        novelty_boost=0.15,
        differentiation=50,
    )
    assert score == 50


def test_reason_code_market_saturated():
    result = determine_verdict(score=50, market_opportunity=20, novelty_boost=0.5, differentiation=50)
    assert result.reason_code == "market_saturated"
    assert result.decision == "NO_GO"


def test_reason_code_weak_differentiation():
    result = determine_verdict(score=50, market_opportunity=50, novelty_boost=0.5, differentiation=20)
    assert result.reason_code == "weak_differentiation"
    assert result.decision == "NO_GO"


def test_reason_code_weak_paper_backing():
    result = determine_verdict(score=50, market_opportunity=50, novelty_boost=0.01, differentiation=50)
    assert result.reason_code == "weak_paper_backing"
    assert result.decision == "NO_GO"


def test_reason_code_low_confidence():
    result = determine_verdict(score=50, market_opportunity=50, novelty_boost=0.2, differentiation=50)
    assert result.reason_code == "low_confidence"
    assert result.decision == "NO_GO"


def test_reason_code_high_potential_on_high_score():
    result = determine_verdict(score=85, market_opportunity=80, novelty_boost=0.5, differentiation=80)
    assert result.reason_code == "high_potential"
    assert result.decision == "GO"


def test_novelty_boost_capped_at_one():
    score_uncapped = compute_verdict_score(
        confidence=0.0,
        engagement=0.0,
        market_opportunity=0,
        novelty_boost=100.0,
        differentiation=0,
    )
    score_at_cap = compute_verdict_score(
        confidence=0.0,
        engagement=0.0,
        market_opportunity=0,
        novelty_boost=0.3,
        differentiation=0,
    )
    assert score_uncapped == score_at_cap == 15


def test_boundary_score_60_is_go():
    result = determine_verdict(score=60, market_opportunity=50, novelty_boost=0.2, differentiation=50)
    assert result.decision == "GO"


def test_boundary_score_59_is_no_go():
    result = determine_verdict(score=59, market_opportunity=50, novelty_boost=0.2, differentiation=50)
    assert result.decision == "NO_GO"


def test_verdict_model_structure():
    result = determine_verdict(score=70, market_opportunity=60, novelty_boost=0.3, differentiation=60)
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
    )
