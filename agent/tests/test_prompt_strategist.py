import pytest

from agent.nodes.prompt_strategist import infer_model_family, prompt_strategist


def test_infer_model_family_classifies_supported_codegen_families():
    assert infer_model_family("openai-gpt-oss-120b") == "openai_gpt_oss"
    assert infer_model_family("alibaba-qwen3-32b") == "qwen3"
    assert infer_model_family("deepseek-r1-distill-llama-70b") == "deepseek_r1"
    assert infer_model_family("mistral-nemo-instruct-2407") == "generic"


@pytest.mark.asyncio
async def test_prompt_strategist_builds_layered_prompt_strategy(monkeypatch):
    async def _fake_collect(families: set[str]) -> dict[str, dict]:
        return {
            family: {
                "family": family,
                "notes": [f"{family} note"],
                "sources": [{"label": f"{family} source", "url": f"https://example.com/{family}", "status": "fetched"}],
            }
            for family in families
        }

    monkeypatch.setattr("agent.nodes.prompt_strategist._collect_family_guidance", _fake_collect)

    result = await prompt_strategist(
        {
            "idea": {"name": "DemoPilot"},
            "blueprint": {
                "design_system": {"visual_direction": "stage-like rehearsal console"},
                "experience_contract": {
                    "required_surfaces": ["hero", "workspace", "saved takes"],
                    "required_states": ["loading", "empty", "error", "success"],
                    "proof_points": ["scorecard on first run", "recent rehearsals"],
                },
                "frontend_files": {
                    "src/app/page.tsx": {},
                    "src/components/Hero.tsx": {},
                },
                "backend_files": {
                    "main.py": {},
                    "routes.py": {},
                },
                "frontend_backend_contract": [
                    {
                        "frontend_file": "src/lib/api.ts",
                        "calls": "POST /api/rehearse",
                        "backend_file": "routes.py",
                        "request_fields": ["transcript"],
                        "response_fields": ["scores"],
                    }
                ],
            },
            "generated_docs": {
                "tech_spec": "- Use Next.js App Router with live scorecards",
                "api_spec": "- POST /rehearse returns scores and feedback",
            },
        }
    )

    strategy = result["prompt_strategy"]

    assert result["phase"] == "prompt_strategy"
    assert strategy["strategy_version"] == "prompt-strategy-v1"
    assert strategy["context_priority"]
    assert strategy["quality_gates"]
    assert "CTO Lead" in strategy["frontend_prompt_appendix"]
    assert "Frontend Architect" in strategy["frontend_prompt_appendix"]
    assert "Backend Expert" in strategy["backend_prompt_appendix"]
    assert "Prompt Engineer" in strategy["shared_prompt_appendix"]
    assert "Runtime Quality Gates" in strategy["shared_prompt_appendix"]
    assert "Cross-Model Output Contract" in strategy["cross_model_user_contract"]
    assert strategy["source_index"]
