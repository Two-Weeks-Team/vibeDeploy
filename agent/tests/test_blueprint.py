from agent.nodes.blueprint import _normalize_blueprint


def test_normalize_blueprint_adds_secondary_surfaces_for_collection_apps():
    blueprint = {
        "frontend_files": {
            "package.json": {"purpose": "manifest", "imports_from": [], "exports": []},
            "src/app/page.tsx": {"purpose": "page", "imports_from": [], "exports": ["default"]},
        },
        "backend_files": {},
    }
    idea = {
        "problem": "Users need to save bookmarks, browse history, and keep favorites organized.",
        "key_features": ["save links", "favorites", "dashboard"],
    }

    normalized = _normalize_blueprint(blueprint, idea)
    frontend_files = normalized["frontend_files"]
    experience_contract = normalized["experience_contract"]

    assert "src/components/Hero.tsx" in frontend_files
    assert "src/components/InsightPanel.tsx" in frontend_files
    assert "src/components/CollectionPanel.tsx" in frontend_files
    assert "src/components/StatsStrip.tsx" in frontend_files
    assert "src/components/CollectionPanel.tsx" in frontend_files["src/app/page.tsx"]["imports_from"]
    assert len(frontend_files) >= 8
    assert "saved library and recent activity" in experience_contract["required_surfaces"]
    assert "loading" in experience_contract["required_states"]
