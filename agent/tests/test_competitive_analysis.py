import pytest

from agent.zero_prompt.competitive_analysis import (
    _compute_opportunity_score,
    _determine_search_confidence,
    _estimate_saturation,
    _extract_competitors,
    _identify_gaps,
    analyze_competition,
)
from agent.zero_prompt.events import (
    ZP_COMPETE_COMPLETE,
    ZP_COMPETE_START,
    compete_complete_event,
    compete_start_event,
)
from agent.zero_prompt.schemas import MarketAnalysis, SearchResult
from agent.zero_prompt.unified_search import _merge_and_score, _normalize_url


def _make_result(**overrides) -> SearchResult:
    defaults = {"title": "Test App", "url": "https://example.com", "snippet": "A test app", "source": "brave"}
    defaults.update(overrides)
    return SearchResult(**defaults)


def test_normalize_url():
    assert _normalize_url("https://www.example.com/") == "example.com"
    assert _normalize_url("http://example.com") == "example.com"
    assert _normalize_url("https://example.com/path") == "example.com/path"


def test_merge_and_score_deduplicates():
    results = [
        _make_result(title="App A", url="https://example.com", source="brave"),
        _make_result(title="App A", url="https://www.example.com/", source="exa"),
    ]
    merged = _merge_and_score(results)
    assert len(merged) == 1
    assert merged[0].confidence == "high"
    assert "brave" in merged[0].source
    assert "exa" in merged[0].source


def test_merge_and_score_keeps_unique():
    results = [
        _make_result(url="https://a.com", source="brave"),
        _make_result(url="https://b.com", source="exa"),
    ]
    merged = _merge_and_score(results)
    assert len(merged) == 2
    assert all(r.confidence == "normal" for r in merged)


def test_merge_and_score_high_confidence_first():
    results = [
        _make_result(url="https://unique.com", source="brave"),
        _make_result(url="https://both.com", source="brave"),
        _make_result(url="https://both.com", source="exa"),
    ]
    merged = _merge_and_score(results)
    assert merged[0].confidence == "high"


def test_extract_competitors():
    results = [
        _make_result(title="Competitor A"),
        _make_result(title="Competitor B"),
        _make_result(title="Competitor A"),
    ]
    competitors = _extract_competitors(results)
    assert len(competitors) == 2
    assert "Competitor A" in competitors
    assert "Competitor B" in competitors


def test_estimate_saturation_high():
    results = [_make_result() for _ in range(10)]
    assert _estimate_saturation(results) == "high"


def test_estimate_saturation_medium():
    results = [_make_result() for _ in range(5)]
    assert _estimate_saturation(results) == "medium"


def test_estimate_saturation_low():
    results = [_make_result() for _ in range(2)]
    assert _estimate_saturation(results) == "low"


def test_compute_opportunity_score_low_saturation():
    results = [_make_result() for _ in range(2)]
    score = _compute_opportunity_score(results, "low")
    assert score == 80


def test_compute_opportunity_score_high_saturation():
    results = [_make_result() for _ in range(10)]
    score = _compute_opportunity_score(results, "high")
    assert score == 40


def test_determine_search_confidence_no_results():
    assert _determine_search_confidence([]) == "llm_only"


def test_determine_search_confidence_normal():
    results = [_make_result(confidence="normal")]
    assert _determine_search_confidence(results) == "normal"


def test_determine_search_confidence_high():
    results = [_make_result(confidence="high")]
    assert _determine_search_confidence(results) == "high"


def test_identify_gaps_few_players():
    results = [_make_result() for _ in range(3)]
    gaps = _identify_gaps(results)
    assert gaps == ["Market has few established players — early mover advantage possible"]


def test_market_analysis_model():
    analysis = MarketAnalysis(saturation_level="low")
    assert analysis.market_opportunity_score == 0
    assert analysis.competitors == []
    assert analysis.saturation_level == "low"


def test_compete_start_event():
    event = compete_start_event("todo app alternatives")
    assert event["type"] == ZP_COMPETE_START
    assert event["query"] == "todo app alternatives"


def test_compete_complete_event():
    event = compete_complete_event(competitors=5, saturation="medium", confidence="high")
    assert event["type"] == ZP_COMPETE_COMPLETE
    assert event["competitors_found"] == 5
    assert event["saturation_level"] == "medium"


@pytest.mark.asyncio
async def test_analyze_competition_with_mocked_search(monkeypatch):
    from agent.zero_prompt import competitive_analysis as ca_module

    async def fake_unified_search(query, limit=5):
        return [
            SearchResult(title="Rival App", url="https://rival.com", snippet="A rival app", source="brave"),
            SearchResult(title="Another App", url="https://another.com", snippet="Another one", source="exa"),
        ]

    monkeypatch.setattr(ca_module, "unified_search", fake_unified_search)
    result = await analyze_competition("test query")
    assert isinstance(result, MarketAnalysis)
    assert result.saturation_level == "low"
    assert len(result.competitors) == 2
    assert result.search_confidence == "normal"


@pytest.mark.asyncio
async def test_analyze_competition_handles_search_failure(monkeypatch):
    from agent.zero_prompt import competitive_analysis as ca_module

    async def failing_search(query, limit=5):
        raise ConnectionError("All search engines down")

    monkeypatch.setattr(ca_module, "unified_search", failing_search)
    result = await analyze_competition("failing query")
    assert isinstance(result, MarketAnalysis)
    assert result.search_confidence == "llm_only"
    assert result.competitors == []
