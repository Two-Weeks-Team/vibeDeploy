import pytest

from agent.nodes import doc_generator as doc_generator_module


@pytest.mark.asyncio
async def test_doc_generator_falls_back_when_llm_errors(monkeypatch):
    async def _fail(*args, **kwargs):
        raise RuntimeError("Error code: 429 - rate limit exceeded")

    monkeypatch.setattr(doc_generator_module, "get_llm", lambda *args, **kwargs: object())
    monkeypatch.setattr(doc_generator_module, "ainvoke_with_retry", _fail)

    result = await doc_generator_module.doc_generator(
        {
            "idea": {
                "name": "TripCanvas AI",
                "tagline": "Plan cinematic journeys",
                "problem": "Travel planning is fragmented",
                "solution": "One guided planner",
                "target_users": "Frequent travelers",
                "key_features": ["Trip brief", "Itinerary board", "Budget planner"],
            },
            "council_analysis": {},
            "scoring": {},
        }
    )

    docs = result["generated_docs"]

    assert result["phase"] == "docs_generated"
    assert "# Product Requirements" in docs["prd"]
    assert "Fallback document generated" in docs["prd"]
    assert "# Technical Specification" in docs["tech_spec"]
    assert "name: tripcanvas-ai" in docs["app_spec_yaml"]


@pytest.mark.asyncio
async def test_doc_generator_short_circuits_to_template_docs_without_fallback_models(monkeypatch):
    calls = {"ainvoke": 0}

    async def _fake_invoke(*args, **kwargs):
        calls["ainvoke"] += 1
        raise AssertionError("doc LLM should not run when template docs are enabled")

    monkeypatch.setattr(doc_generator_module, "get_llm", lambda *args, **kwargs: object())
    monkeypatch.setattr(doc_generator_module, "ainvoke_with_retry", _fake_invoke)
    monkeypatch.setattr(doc_generator_module, "get_rate_limit_fallback_models", lambda model: [])

    result = await doc_generator_module.doc_generator(
        {
            "idea": {
                "name": "EventPilot",
                "tagline": "Run striking live events",
                "problem": "Event planning is fragmented",
                "solution": "One command center",
                "target_users": "Event operators",
                "key_features": ["Run-of-show", "Speaker board", "Check-in dashboard"],
            },
            "council_analysis": {},
            "scoring": {},
        }
    )

    docs = result["generated_docs"]

    assert calls["ainvoke"] == 0
    assert "# Product Requirements" in docs["prd"]
    assert "template_docs_enabled" in docs["prd"]
    assert "name: eventpilot" in docs["app_spec_yaml"]
