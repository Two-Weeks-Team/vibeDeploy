from agent.nodes.per_file_prompts import (
    AVAILABLE_CONTEXT_KEYS,
    PROMPT_TEMPLATES,
    build_prompt,
    estimate_tokens,
    get_context_keys_for_type,
)


def test_all_required_file_types_have_templates():
    assert "page.tsx" in PROMPT_TEMPLATES
    assert "component.tsx" in PROMPT_TEMPLATES
    assert "api.ts" in PROMPT_TEMPLATES
    assert "routes.py" in PROMPT_TEMPLATES
    assert "ai_service.py" in PROMPT_TEMPLATES


def test_template_config_has_required_fields_and_types():
    for cfg in PROMPT_TEMPLATES.values():
        assert isinstance(cfg["role"], str)
        assert isinstance(cfg["context_keys"], list)
        assert isinstance(cfg["template"], str)
        assert isinstance(cfg["max_tokens"], int)


def test_context_strategy_mappings_match_spec():
    assert get_context_keys_for_type("page.tsx") == ["design_system", "layout", "navigation"]
    assert get_context_keys_for_type("component.tsx") == ["design_system", "props_spec"]
    assert get_context_keys_for_type("api.ts") == ["api_contract", "types"]
    assert get_context_keys_for_type("routes.py") == ["api_contract", "models"]
    assert get_context_keys_for_type("ai_service.py") == ["api_contract"]


def test_unknown_type_falls_back_to_empty_context_keys():
    assert get_context_keys_for_type("unknown.ext") == []


def test_build_prompt_includes_file_path_and_description():
    prompt = build_prompt(
        "api.ts",
        {
            "file_path": "web/src/lib/api.ts",
            "description": "API client for dashboard",
        },
    )
    assert "File path: web/src/lib/api.ts" in prompt
    assert "Description: API client for dashboard" in prompt


def test_build_prompt_filters_irrelevant_context():
    prompt = build_prompt(
        "page.tsx",
        {
            "file_path": "web/src/app/page.tsx",
            "description": "Main landing page",
            "design_system": "high contrast theme",
            "layout": "hero + cards",
            "navigation": "top nav",
            "props_spec": "should not be included",
        },
    )
    assert "- design_system: high contrast theme" in prompt
    assert "- layout: hero + cards" in prompt
    assert "- navigation: top nav" in prompt
    assert "props_spec" not in prompt


def test_build_prompt_skips_missing_and_empty_declared_keys():
    prompt = build_prompt(
        "component.tsx",
        {
            "file_path": "web/src/components/Card.tsx",
            "description": "Reusable card",
            "design_system": "tokenized spacing",
            "props_spec": "",
        },
    )
    assert "- design_system: tokenized spacing" in prompt
    assert "props_spec" not in prompt


def test_empty_context_is_handled():
    prompt = build_prompt("routes.py", {})
    assert "File path: <unknown-path>" in prompt
    assert "Description: <no-description>" in prompt
    assert "Relevant context:" in prompt
    assert "- none" in prompt


def test_unknown_type_fallback_prompt_is_generic():
    prompt = build_prompt(
        "unknown.ext",
        {
            "file_path": "x/unknown.ext",
            "description": "Unknown file",
            "design_system": "not used",
        },
    )
    assert "Role: Senior software engineer" in prompt
    assert "File path: x/unknown.ext" in prompt
    assert "Description: Unknown file" in prompt
    assert "design_system" not in prompt


def test_max_tokens_not_exceed_limit():
    for cfg in PROMPT_TEMPLATES.values():
        assert cfg["max_tokens"] <= 8000


def test_context_keys_are_subset_of_available_keys():
    for cfg in PROMPT_TEMPLATES.values():
        assert set(cfg["context_keys"]).issubset(AVAILABLE_CONTEXT_KEYS)


def test_estimate_tokens_returns_int_with_expected_formula():
    prompt = "a" * 123
    token_count = estimate_tokens(prompt)
    assert isinstance(token_count, int)
    assert token_count == 30


def test_estimate_tokens_empty_prompt_returns_zero():
    assert estimate_tokens("") == 0
