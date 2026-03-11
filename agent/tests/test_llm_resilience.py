import pytest


class _TimeoutLLM:
    async def ainvoke(self, messages):
        raise TimeoutError("simulated timeout")


class _TimeoutAgent:
    async def analyze(self, idea):
        raise TimeoutError("simulated timeout")


@pytest.mark.asyncio
async def test_run_council_agent_uses_fallback_on_timeout(monkeypatch):
    from agent.nodes import vibe_council

    monkeypatch.setitem(vibe_council.COUNCIL_MEMBERS, "architect", _TimeoutAgent())

    result = await vibe_council.run_council_agent({"agent_name": "architect", "idea": {"name": "Test App"}})

    analysis = result["council_analysis"]["architect"]
    assert analysis["fallback"] is True
    assert analysis["score"] == 68
    assert "timed out" in analysis["reasoning"]


@pytest.mark.asyncio
async def test_cross_examination_uses_deterministic_fallback():
    from agent.nodes.vibe_council import cross_examination

    result = await cross_examination({"idea": {"name": "Test App"}, "council_analysis": {}})

    debates = result["cross_examination"]
    assert result["phase"] == "cross_examination_complete"
    assert debates["architect_vs_guardian"]["score_adjustments"] == {}
    assert debates["scout_vs_catalyst"]["score_adjustments"] == {}
    assert debates["advocate_challenges"]["score_adjustments"] == {}
    assert "Deterministic" in debates["architect_vs_guardian"]["note"]


@pytest.mark.asyncio
async def test_fix_storm_increments_iteration_on_timeout(monkeypatch):
    import agent.llm as llm_mod
    from agent.nodes.fix_storm import fix_storm

    monkeypatch.setattr(llm_mod, "get_llm", lambda *args, **kwargs: _TimeoutLLM())

    state = {
        "idea": {"name": "Test App"},
        "idea_summary": "Test App summary",
        "eval_iteration": 1,
        "scoring": {
            "technical_feasibility": {"score": 55, "reasoning": "too broad"},
            "final_score": 61,
        },
    }
    result = await fix_storm(state)

    assert result["eval_iteration"] == 2
    assert result["phase"] == "fix_storm_round_2"
    assert result["idea"] == {"name": "Test App"}
    assert result["fix_storm_result"]["fallback"] is True


@pytest.mark.asyncio
async def test_scope_down_uses_fallback_mvp_on_timeout(monkeypatch):
    import agent.llm as llm_mod
    from agent.nodes.fix_storm import scope_down

    monkeypatch.setattr(llm_mod, "get_llm", lambda *args, **kwargs: _TimeoutLLM())

    result = await scope_down(
        {
            "idea": {"name": "Bookmark MVP", "key_features": ["Save links", "Tag links", "Search links"]},
            "idea_summary": "Bookmark MVP summary",
            "scoring": {"final_score": 42, "decision": "NO_GO"},
        }
    )

    assert result["phase"] == "scope_down_forced_go"
    assert result["scoring"]["decision"] == "GO"
    assert result["idea"]["name"] == "Bookmark MVP"
    assert result["idea"]["key_features"] == ["Save links", "Tag links", "Search links"]


def test_route_decision_scopes_down_after_second_conditional_failure():
    from agent.nodes.decision_gate import route_decision

    route = route_decision({"scoring": {"decision": "CONDITIONAL"}, "eval_iteration": 1})

    assert route == "scope_down"


def test_route_decision_fast_tracks_borderline_conditional_scores():
    from agent.nodes.decision_gate import route_decision

    route = route_decision({"scoring": {"decision": "CONDITIONAL", "final_score": 63.45}, "eval_iteration": 0})

    assert route == "doc_generator"
