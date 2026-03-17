import pytest
from nodes.layout_archetypes import (
    ARCHETYPES,
    generate_layout_css,
    generate_layout_jsx,
    select_archetype,
)

REQUIRED_KEYS = {"id", "name", "css", "jsx", "keywords"}
ARCHETYPE_IDS = {
    "storyboard",
    "operations_console",
    "studio",
    "atlas",
    "notebook",
    "lab",
    "creator_shell",
    "marketplace",
}


def test_archetypes_count():
    assert len(ARCHETYPES) == 8


def test_all_archetypes_have_required_keys():
    for archetype in ARCHETYPES:
        missing = REQUIRED_KEYS - set(archetype.keys())
        assert not missing, f"{archetype.get('id')} missing keys: {missing}"


def test_all_archetype_ids_present():
    ids = {a["id"] for a in ARCHETYPES}
    assert ids == ARCHETYPE_IDS


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_generate_css_returns_string(archetype):
    css = generate_layout_css(archetype)
    assert isinstance(css, str)
    assert len(css) > 0


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_generate_css_contains_grid_or_flex(archetype):
    css = generate_layout_css(archetype)
    assert "grid" in css or "flex" in css


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_generate_css_contains_media_768(archetype):
    css = generate_layout_css(archetype)
    assert "@media (max-width: 768px)" in css


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_generate_jsx_returns_string(archetype):
    jsx = generate_layout_jsx(archetype)
    assert isinstance(jsx, str)
    assert len(jsx) > 0


@pytest.mark.parametrize("archetype", ARCHETYPES)
def test_generate_jsx_contains_classname(archetype):
    jsx = generate_layout_jsx(archetype)
    assert "className" in jsx


def test_select_archetype_keyword_storyboard():
    result = select_archetype("a narrative story blog")
    assert result["id"] == "storyboard"


def test_select_archetype_keyword_studio():
    result = select_archetype("canvas editor for design")
    assert result["id"] == "studio"


def test_select_archetype_keyword_atlas():
    result = select_archetype("geo map exploration")
    assert result["id"] == "atlas"


def test_select_archetype_keyword_notebook():
    result = select_archetype("document wiki for notes")
    assert result["id"] == "notebook"


def test_select_archetype_keyword_lab():
    result = select_archetype("data science experiment lab")
    assert result["id"] == "lab"


def test_select_archetype_keyword_creator_shell():
    result = select_archetype("social feed content creator")
    assert result["id"] == "creator_shell"


def test_select_archetype_keyword_marketplace():
    result = select_archetype("ecommerce shop marketplace")
    assert result["id"] == "marketplace"


def test_select_archetype_keyword_operations_console():
    result = select_archetype("admin dashboard analytics console")
    assert result["id"] == "operations_console"


def test_select_archetype_default_fallback():
    result = select_archetype("something completely unrelated xyz")
    assert result["id"] == "operations_console"


def test_select_archetype_empty_string_fallback():
    result = select_archetype("")
    assert result["id"] == "operations_console"


def test_generate_css_no_double_media_block():
    archetype = next(a for a in ARCHETYPES if a["id"] == "storyboard")
    css = generate_layout_css(archetype)
    assert css.count("@media (max-width: 768px)") == 1


def test_generate_layout_jsx_contains_return():
    for archetype in ARCHETYPES:
        jsx = generate_layout_jsx(archetype)
        assert "return" in jsx


def test_all_archetypes_have_nonempty_keywords():
    for archetype in ARCHETYPES:
        assert isinstance(archetype["keywords"], list)
        assert len(archetype["keywords"]) > 0
