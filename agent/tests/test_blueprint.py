import pytest

from agent.nodes import blueprint as blueprint_module


@pytest.mark.asyncio
async def test_blueprint_generator_short_circuits_without_fallback_models(monkeypatch):
    calls = {"ainvoke": 0}

    async def _fake_invoke(*args, **kwargs):
        calls["ainvoke"] += 1
        raise AssertionError("blueprint LLM should not run in strict mode")

    monkeypatch.setattr(blueprint_module, "get_llm", lambda *args, **kwargs: object())
    monkeypatch.setattr(blueprint_module, "ainvoke_with_retry", _fake_invoke)
    monkeypatch.setattr(blueprint_module, "get_rate_limit_fallback_models", lambda model: [])

    result = await blueprint_module.blueprint_generator(
        {
            "idea": {
                "name": "TripCanvas AI",
                "must_have_surfaces": ["hero", "trip planner", "saved plans"],
                "proof_points": ["shareable plans", "recent itineraries"],
                "experience_non_negotiables": ["no blank dashboard"],
            },
            "generated_docs": {},
        }
    )

    blueprint = result["blueprint"]

    assert calls["ainvoke"] == 0
    assert result["phase"] == "blueprint"
    assert blueprint["app_name"] == "tripcanvas-ai"
    assert "src/app/page.tsx" in blueprint["frontend_files"]
    assert "main.py" in blueprint["backend_files"]
    assert len(blueprint["frontend_backend_contract"]) >= 2
