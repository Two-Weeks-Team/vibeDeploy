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
