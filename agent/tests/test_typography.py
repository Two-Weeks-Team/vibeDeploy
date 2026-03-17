import pytest
from nodes.typography import (
    FONT_PAIRINGS,
    generate_layout_font_imports,
    generate_type_scale_css,
    select_font_pairing,
)


def test_all_pairings_have_required_keys():
    for pairing in FONT_PAIRINGS:
        assert "display" in pairing
        assert "body" in pairing
        assert "keywords" in pairing


def test_all_pairings_have_non_empty_fields():
    for pairing in FONT_PAIRINGS:
        assert pairing["display"]
        assert pairing["body"]
        assert len(pairing["keywords"]) > 0


def test_ten_pairings_defined():
    assert len(FONT_PAIRINGS) == 10


def test_select_font_pairing_magazine_returns_editorial():
    result = select_font_pairing("magazine")
    assert result["id"] == "editorial"


def test_select_font_pairing_code_returns_tech_dev():
    result = select_font_pairing("code")
    assert result["id"] == "tech_dev"


def test_select_font_pairing_defaults_to_modern_saas_for_unknown():
    result = select_font_pairing("something completely unknown xyz123")
    assert result["id"] == "modern_saas"


def test_select_font_pairing_case_insensitive():
    result_upper = select_font_pairing("MAGAZINE")
    result_lower = select_font_pairing("magazine")
    assert result_upper["id"] == result_lower["id"]


def test_select_font_pairing_case_insensitive_mixed():
    result = select_font_pairing("MaGaZiNe")
    assert result["id"] == "editorial"


def test_generate_layout_font_imports_contains_import_statement():
    pairing = select_font_pairing("magazine")
    result = generate_layout_font_imports(pairing)
    assert "import" in result
    assert "next/font/google" in result


def test_generate_layout_font_imports_contains_font_display_variable():
    pairing = select_font_pairing("magazine")
    result = generate_layout_font_imports(pairing)
    assert "--font-display" in result


def test_generate_layout_font_imports_contains_font_body_variable():
    pairing = select_font_pairing("magazine")
    result = generate_layout_font_imports(pairing)
    assert "--font-body" in result


def test_generate_layout_font_imports_single_font_pairing():
    pairing = select_font_pairing("saas")
    result = generate_layout_font_imports(pairing)
    assert "--font-display" in result
    assert "--font-body" in result
    assert "next/font/google" in result


def test_generate_layout_font_imports_is_non_empty_string():
    for pairing in FONT_PAIRINGS:
        result = generate_layout_font_imports(pairing)
        assert isinstance(result, str)
        assert len(result) > 0


def test_generate_type_scale_css_has_nine_scale_steps():
    css = generate_type_scale_css()
    step_names = [
        "--type-xs",
        "--type-sm",
        "--type-base",
        "--type-md",
        "--type-lg",
        "--type-xl",
        "--type-2xl",
        "--type-3xl",
        "--type-4xl",
    ]
    for step in step_names:
        assert step in css


def test_generate_type_scale_css_count_exactly_nine():
    css = generate_type_scale_css()
    step_names = [
        "--type-xs",
        "--type-sm",
        "--type-base",
        "--type-md",
        "--type-lg",
        "--type-xl",
        "--type-2xl",
        "--type-3xl",
        "--type-4xl",
    ]
    assert len(step_names) == 9
    for step in step_names:
        assert step in css


def test_generate_type_scale_css_is_valid_non_empty_string():
    css = generate_type_scale_css()
    assert isinstance(css, str)
    assert len(css) > 0
    assert ":root" in css


@pytest.mark.parametrize(
    "hint,expected_id",
    [
        ("news", "editorial"),
        ("luxury", "elegant"),
        ("developer", "tech_dev"),
        ("community", "friendly"),
        ("finance", "business"),
        ("design", "creative"),
        ("portfolio", "minimal"),
        ("history", "classic"),
        ("sports", "bold"),
    ],
)
def test_select_font_pairing_all_keywords(hint, expected_id):
    result = select_font_pairing(hint)
    assert result["id"] == expected_id
