import pytest

from agent.nodes.design_tokens import DOMAIN_PRESETS, _make_scale, generate_color_tokens


@pytest.mark.parametrize("domain", list(DOMAIN_PRESETS.keys()))
def test_domain_preset_produces_valid_css(domain):
    css = generate_color_tokens({"domain": domain})
    assert isinstance(css, str)
    assert len(css) > 0
    assert "oklch(" in css


def test_css_contains_theme_keyword():
    css = generate_color_tokens({"domain": "tech"})
    assert "@theme" in css


def test_css_contains_all_12_primary_steps():
    css = generate_color_tokens({"domain": "tech"})
    for i in range(1, 13):
        assert f"--color-primary-{i}:" in css


def test_css_contains_semantic_role_background():
    css = generate_color_tokens({"domain": "tech"})
    assert "--color-background:" in css


def test_css_contains_semantic_role_foreground():
    css = generate_color_tokens({"domain": "tech"})
    assert "--color-foreground:" in css


def test_css_contains_semantic_role_primary():
    css = generate_color_tokens({"domain": "tech"})
    assert "--color-primary:" in css


def test_css_contains_semantic_role_accent():
    css = generate_color_tokens({"domain": "tech"})
    assert "--color-accent:" in css


def test_css_contains_dark_mode_section():
    css = generate_color_tokens({"domain": "finance"})
    assert ".dark {" in css


def test_unknown_domain_falls_back_to_tech():
    css_unknown = generate_color_tokens({"domain": "unknown_domain_xyz"})
    css_tech = generate_color_tokens({"domain": "tech"})
    assert css_unknown == css_tech


def test_make_scale_produces_12_values():
    scale = _make_scale(hue=250)
    assert len(scale) == 12


def test_make_scale_values_contain_oklch():
    scale = _make_scale(hue=150)
    for value in scale:
        assert "oklch(" in value


def test_css_balanced_braces():
    for domain in DOMAIN_PRESETS:
        css = generate_color_tokens({"domain": domain})
        assert css.count("{") == css.count("}")


def test_css_contains_card_border_muted_roles():
    css = generate_color_tokens({"domain": "health"})
    assert "--color-card:" in css
    assert "--color-border:" in css
    assert "--color-muted:" in css


def test_css_contains_success_warning_error_roles():
    css = generate_color_tokens({"domain": "creative"})
    assert "--color-success:" in css
    assert "--color-warning:" in css
    assert "--color-error:" in css
