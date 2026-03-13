"""Tests verifying pipeline quality hardening changes (Phase 1-3)."""

import pytest

from agent.nodes.code_evaluator import (
    _MIN_UNIQUE_API_ENDPOINTS,
    MAX_CODE_EVAL_ITERATIONS,
    _build_fix_instructions,
    _check_content_depth,
    _check_experience,
    _check_flagship_artifact_fidelity,
    _check_structural_presence,
    _collect_quality_blockers,
)
from agent.nodes.decision_gate import MAX_FIX_STORM_ROUNDS, route_decision
from agent.nodes.fix_storm import scope_down

# --- Phase 1: Decision Gate Hardening ---


def test_max_fix_storm_rounds_is_three():
    """Verify constant was updated from 2 to 3."""
    assert MAX_FIX_STORM_ROUNDS == 3


def test_max_code_eval_iterations_is_five():
    """Verify constant was updated from 3 to 5."""
    assert MAX_CODE_EVAL_ITERATIONS == 5


def test_conditional_score_65_routes_to_fix_storm():
    """Score 65 (between old 60 threshold and new 70) must go to fix_storm, not doc_generator."""
    state = {
        "scoring": {"decision": "CONDITIONAL", "final_score": 65.0},
        "eval_iteration": 0,
    }
    assert route_decision(state) == "fix_storm"


def test_conditional_score_70_routes_to_doc_generator():
    """Score exactly 70 meets new threshold, routes to doc_generator."""
    state = {
        "scoring": {"decision": "CONDITIONAL", "final_score": 70.0},
        "eval_iteration": 0,
    }
    assert route_decision(state) == "doc_generator"


def test_fix_storm_round_3_available():
    """With eval_iteration=2, should still have budget for fix_storm (round 3)."""
    state = {
        "scoring": {"decision": "CONDITIONAL", "final_score": 50.0},
        "eval_iteration": 2,
    }
    assert route_decision(state) == "fix_storm"


def test_scope_down_after_round_3():
    """With eval_iteration=3 (exhausted 3 rounds), should scope_down."""
    state = {
        "scoring": {"decision": "CONDITIONAL", "final_score": 50.0},
        "eval_iteration": 3,
    }
    assert route_decision(state) == "scope_down"


# --- Phase 1: Escalating Feedback ---


def test_escalating_feedback_triggers_at_iteration_3():
    """_build_fix_instructions should include CRITICAL prefix at iteration >= 3."""
    eval_result = {
        "iteration": 3,
        "consistency": 90,
        "runnability": 90,
        "experience": 90,
        "missing_frontend": [],
        "missing_backend": [],
    }
    instructions = _build_fix_instructions(eval_result)
    assert "CRITICAL" in instructions
    assert f"attempt 3/{MAX_CODE_EVAL_ITERATIONS}" in instructions


def test_escalating_feedback_absent_at_iteration_2():
    """_build_fix_instructions should NOT include CRITICAL at iteration < 3."""
    eval_result = {
        "iteration": 2,
        "consistency": 90,
        "runnability": 90,
        "experience": 90,
        "missing_frontend": [],
        "missing_backend": [],
    }
    instructions = _build_fix_instructions(eval_result)
    assert "CRITICAL" not in instructions


# --- Phase 1: scope_down Honesty ---


class _FailingLLM:
    """Stub LLM that always raises so scope_down falls back immediately."""

    async def ainvoke(self, messages):
        raise RuntimeError("test: LLM unavailable")


@pytest.mark.asyncio
async def test_scope_down_preserves_real_score_not_fake_75(monkeypatch):
    """scope_down should use max(55.0, real_score), not hardcoded 75.0."""
    import agent.llm as llm_mod

    monkeypatch.setattr(llm_mod, "get_llm", lambda *args, **kwargs: _FailingLLM())

    state = {
        "idea": {"name": "TestApp", "description": "A test application"},
        "scoring": {"decision": "CONDITIONAL", "final_score": 42.0},
        "eval_iteration": 3,
        "flagship_contract": {},
    }
    result = await scope_down(state)
    forced_score = result["scoring"]["final_score"]
    assert forced_score == 55.0, f"Expected max(55.0, 42.0)=55.0, got {forced_score}"
    assert result["scoring"].get("scope_down_applied") is True


@pytest.mark.asyncio
async def test_scope_down_keeps_higher_real_score(monkeypatch):
    """If real score > 55, scope_down should keep it."""
    import agent.llm as llm_mod

    monkeypatch.setattr(llm_mod, "get_llm", lambda *args, **kwargs: _FailingLLM())

    state = {
        "idea": {"name": "GoodApp", "description": "A decent application"},
        "scoring": {"decision": "CONDITIONAL", "final_score": 62.0},
        "eval_iteration": 3,
        "flagship_contract": {},
    }
    result = await scope_down(state)
    forced_score = result["scoring"]["final_score"]
    assert forced_score == 62.0, f"Expected max(55.0, 62.0)=62.0, got {forced_score}"
    assert result["scoring"].get("scope_down_applied") is True


# --- Phase 2: Structural Artifact Fidelity ---


def test_structural_presence_detects_jsx_component():
    """A JSX component like <QueueCard should count as structural presence for 'queue card'."""
    frontend = {
        "src/components/QueueCard.tsx": "export function QueueCard({ data }) { return <div>{data.name}</div>; }"
    }
    assert _check_structural_presence("queue card", frontend, None) is True


def test_structural_presence_rejects_comment_only():
    """A comment mentioning 'queue card' should NOT count as structural presence."""
    frontend = {
        "src/app/page.tsx": "// TODO: add queue card component\nexport default function Page() { return <main />; }"
    }
    assert _check_structural_presence("queue card", frontend, None) is False


def test_structural_presence_detects_function_call():
    """A function call like calculateBudget() should match 'budget'."""
    backend = {"routes.py": "def handle():\n    result = calculateBudget(amount=100)\n    return result\n"}
    assert _check_structural_presence("budget", None, backend) is True


def test_artifact_fidelity_blended_scoring():
    """Verify the 60/40 structural/phrase blend produces expected scores."""
    frontend = {
        "src/components/RouteCard.tsx": "export function RouteCard({ route }) { return <div>{route.name}</div>; }",
        "src/app/page.tsx": "export default function Page() { return <main><RouteCard route={{}} /></main>; }",
    }
    backend = {
        "routes.py": "def get_routes(): return []\ndef calculate_budget(amount): return amount * 0.9\n",
    }
    contract = {
        "required_objects": ["route card", "budget cue"],
        "required_results": ["day-by-day route sequence"],
        "acceptance_checks": [],
    }
    fidelity = _check_flagship_artifact_fidelity(frontend, backend, contract)
    assert "route card" in fidelity["required_object_hits"]
    assert fidelity["score"] > 0


# --- Phase 2: Experience Validation ---


def test_experience_check_rewards_real_usestate():
    """Real useState pattern should score higher than keyword-only."""
    frontend_with_state = {
        "src/app/page.tsx": (
            "'use client';\nimport { useState } from 'react';\nexport default function Page() {\n"
            "  const [loading, setLoading] = useState(false);\n"
            "  return <main>{loading ? <p>Loading...</p> : <p>Content</p>}</main>;\n}"
        ),
        "src/components/Hero.tsx": "export default function Hero() { return <section>Hero</section>; }",
        "src/components/Panel.tsx": "export default function Panel() { return <section>Panel</section>; }",
        "src/components/Grid.tsx": "export default function Grid() { return <section>Grid</section>; }",
        "src/components/Footer.tsx": "export default function Footer() { return <section>Footer</section>; }",
    }
    blueprint = {
        "frontend_files": {
            "src/components/Hero.tsx": {},
            "src/components/Panel.tsx": {},
            "src/components/Grid.tsx": {},
            "src/components/Footer.tsx": {},
        }
    }
    score = _check_experience(frontend_with_state, blueprint)
    assert score >= 40.0, f"Expected >= 40.0 with real useState, got {score}"


def test_experience_check_penalizes_comment_only_state():
    """Comments mentioning 'loading' without actual useState should score lower."""
    frontend_comment_only = {
        "src/app/page.tsx": "// TODO: add loading state\nexport default function Page() { return <main>Content</main>; }",
        "src/components/Hero.tsx": "export default function Hero() { return <section>Hero</section>; }",
        "src/components/Panel.tsx": "export default function Panel() { return <section>Panel</section>; }",
        "src/components/Grid.tsx": "export default function Grid() { return <section>Grid</section>; }",
        "src/components/Footer.tsx": "export default function Footer() { return <section>Footer</section>; }",
    }
    blueprint = {
        "frontend_files": {
            "src/components/Hero.tsx": {},
            "src/components/Panel.tsx": {},
            "src/components/Grid.tsx": {},
            "src/components/Footer.tsx": {},
        }
    }
    score = _check_experience(frontend_comment_only, blueprint)
    assert score < 40.0, f"Comment-only 'loading' should score < 40.0, got {score}"


# --- Phase 3: Content Depth Detection ---


def _make_rich_frontend():
    return {
        "src/app/page.tsx": (
            "'use client';\nimport { useState, useEffect } from 'react';\n"
            "export default function Page() {\n"
            "  const [recipes, setRecipes] = useState([]);\n"
            "  useEffect(() => { fetch('/api/recipes').then(r => r.json()).then(setRecipes); }, []);\n"
            "  return <main>{recipes.map(r => <div key={r.id}>{r.title}</div>)}</main>;\n}"
        ),
        "src/lib/api.ts": (
            "const API_BASE = '/api';\n"
            "export async function getRecipes() { return fetch('/api/recipes').then(r => r.json()); }\n"
            "export async function getCategories() { return fetch('/api/categories').then(r => r.json()); }\n"
        ),
    }


def _make_rich_backend():
    return {
        "main.py": "from fastapi import FastAPI\nimport uvicorn\napp = FastAPI()\n",
        "routes.py": (
            "from fastapi import APIRouter\n"
            "router = APIRouter(prefix='/api')\n"
            "@router.get('/recipes')\nasync def get_recipes():\n    return list_recipes()\n"
            "@router.post('/recipes')\nasync def create_recipe(data: dict):\n    return save_recipe(data)\n"
            "@router.get('/categories')\nasync def get_categories():\n    return list_categories()\n"
        ),
        "ai_service.py": (
            "async def suggest_recipe(ingredients: list):\n    pass\n"
            "async def analyze_nutrition(recipe_id: str):\n    pass\n"
            "async def generate_meal_plan(preferences: dict):\n    pass\n"
        ),
    }


def test_content_depth_clean_code_scores_high():
    depth = _check_content_depth(_make_rich_frontend(), _make_rich_backend())
    assert depth["depth_score"] >= 80, f"Rich code should score >= 80, got {depth['depth_score']}"
    assert not depth["shallow_patterns_found"]
    assert depth["has_domain_logic"] is True


def test_content_depth_detects_sample_item_placeholder():
    frontend = {"src/app/page.tsx": "return <div>Sample Item 1</div><div>Sample Item 2</div>;"}
    depth = _check_content_depth(frontend, _make_rich_backend())
    assert depth["shallow_patterns_found"], "Should detect 'Sample Item N' as shallow"
    assert depth["depth_score"] < 100


def test_content_depth_detects_lorem_ipsum():
    frontend = {"src/app/page.tsx": "return <p>Lorem ipsum dolor sit amet</p>;"}
    depth = _check_content_depth(frontend, _make_rich_backend())
    assert any("lorem" in p for p in depth["shallow_patterns_found"])


def test_content_depth_detects_your_result_here():
    frontend = {"src/app/page.tsx": "return <span>Your Result Here</span>;"}
    depth = _check_content_depth(frontend, _make_rich_backend())
    assert depth["shallow_patterns_found"]


def test_content_depth_detects_coming_soon():
    frontend = {"src/app/page.tsx": "return <div>Coming Soon</div>;"}
    depth = _check_content_depth(frontend, _make_rich_backend())
    assert any("coming" in p for p in depth["shallow_patterns_found"])


def test_content_depth_penalizes_few_endpoints():
    frontend = {"src/app/page.tsx": "export default function Page() { return <main>Hi</main>; }"}
    backend = {"main.py": "from fastapi import FastAPI\napp = FastAPI()\n"}
    depth = _check_content_depth(frontend, backend)
    assert depth["unique_api_endpoints"] < _MIN_UNIQUE_API_ENDPOINTS
    assert depth["depth_score"] < 80


def test_content_depth_rewards_seed_data():
    frontend = {
        "src/app/page.tsx": (
            "const DEMO_RECIPES = [\n"
            '  { id: 1, title: "Pasta Carbonara", category: "Italian", time: 30, rating: 4.5 },\n'
            '  { id: 2, title: "Chicken Tikka Masala", category: "Indian", time: 45, rating: 4.8 },\n'
            '  { id: 3, title: "Caesar Salad", category: "American", time: 15, rating: 4.2 },\n'
            "];\nexport default function Page() { return <main>Content</main>; }"
        ),
    }
    depth = _check_content_depth(frontend, _make_rich_backend())
    assert depth["has_seed_data"] is True


def test_content_depth_detects_no_domain_logic():
    backend = {
        "main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "routes.py": "@router.get('/items')\ndef get(): return []\n",
    }
    depth = _check_content_depth(None, backend)
    assert depth["has_domain_logic"] is False


def test_content_depth_blocker_triggers_below_40():
    frontend = {
        "src/app/page.tsx": (
            "return <div>Sample Item 1</div><div>Sample Item 2</div>"
            "<p>Your Result Here</p><p>Coming Soon</p>"
            "<p>Lorem ipsum dolor sit amet</p>;"
        )
    }
    backend = {"main.py": "app = None\n"}
    blockers = _collect_quality_blockers(frontend, backend, {})
    assert any("shallow" in b for b in blockers)


def test_content_depth_no_blocker_for_rich_code():
    blockers = _collect_quality_blockers(_make_rich_frontend(), _make_rich_backend(), {})
    shallow_blockers = [b for b in blockers if "shallow" in b]
    assert not shallow_blockers


def test_fix_instructions_include_depth_guidance_when_shallow():
    eval_result = {
        "iteration": 1,
        "consistency": 90,
        "runnability": 90,
        "experience": 90,
        "missing_frontend": [],
        "missing_backend": [],
        "content_depth": {
            "depth_score": 30,
            "shallow_patterns_found": [r"sample\s+(item|data)"],
            "unique_api_endpoints": 1,
            "has_seed_data": False,
            "has_domain_logic": False,
        },
    }
    instructions = _build_fix_instructions(eval_result)
    assert "DEPTH" in instructions
    assert "placeholder" in instructions.lower() or "seed" in instructions.lower()


def test_fix_instructions_skip_depth_when_score_high():
    eval_result = {
        "iteration": 1,
        "consistency": 90,
        "runnability": 90,
        "experience": 90,
        "missing_frontend": [],
        "missing_backend": [],
        "content_depth": {
            "depth_score": 85,
            "shallow_patterns_found": [],
            "unique_api_endpoints": 4,
            "has_seed_data": True,
            "has_domain_logic": True,
        },
    }
    instructions = _build_fix_instructions(eval_result)
    assert "DEPTH" not in instructions
