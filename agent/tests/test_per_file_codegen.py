import json

import pytest
from pydantic import ValidationError

from agent.nodes.per_file_code_generator import (
    FileSpec,
    extract_file_specs,
    generate_single_file,
    per_file_code_generator_node,
)


def _sample_blueprint() -> dict:
    return {
        "design_system": {
            "visual_direction": "editorial control room",
            "typography": "display serif + mono",
        },
        "frontend_files": {
            "src/app/page.tsx": {"purpose": "main dashboard page", "imports_from": ["src/components/Hero.tsx"]},
            "src/components/Hero.tsx": {"purpose": "hero component", "imports_from": ["src/lib/api.ts"]},
            "src/lib/api.ts": {"purpose": "api client", "imports_from": []},
            "src/app/globals.css": {"purpose": "global styles", "imports_from": []},
            "package.json": {"purpose": "npm manifest", "imports_from": []},
        },
        "backend_files": {
            "routes.py": {"purpose": "fastapi routes", "imports_from": ["models", "ai_service"]},
            "ai_service.py": {"purpose": "business logic", "imports_from": []},
            "requirements.txt": {"purpose": "python deps", "imports_from": []},
        },
    }


def test_filespec_model_accepts_valid_payload():
    spec = FileSpec(path="src/app/page.tsx", file_type="page", description="main page", dependencies=["x"])
    assert spec.path == "src/app/page.tsx"
    assert spec.file_type == "page"
    assert spec.dependencies == ["x"]


def test_filespec_model_rejects_invalid_file_type():
    with pytest.raises(ValidationError):
        FileSpec(path="foo.txt", file_type="unknown", description="x", dependencies=[])


def test_extract_file_specs_returns_empty_for_empty_blueprint():
    assert extract_file_specs({}) == []


def test_extract_file_specs_returns_empty_for_non_dict_blueprint():
    assert extract_file_specs(None) == []


def test_extract_file_specs_reads_frontend_and_backend_entries():
    specs = extract_file_specs(_sample_blueprint())
    assert len(specs) == 8
    by_path = {spec.path: spec for spec in specs}

    assert by_path["src/app/page.tsx"].file_type == "page"
    assert by_path["src/components/Hero.tsx"].file_type == "component"
    assert by_path["src/lib/api.ts"].file_type == "api"
    assert by_path["src/app/globals.css"].file_type == "style"
    assert by_path["package.json"].file_type == "config"
    assert by_path["routes.py"].file_type == "route"
    assert by_path["ai_service.py"].file_type == "service"
    assert by_path["requirements.txt"].file_type == "config"


def test_extract_file_specs_uses_defaults_for_string_metadata():
    blueprint = {
        "frontend_files": {"src/components/Box.tsx": "box component"},
        "backend_files": {},
    }
    specs = extract_file_specs(blueprint)
    assert specs[0].description == "box component"
    assert specs[0].dependencies == []


def test_generate_single_file_page_template_contains_next_page_shape():
    spec = FileSpec(path="src/app/page.tsx", file_type="page", description="landing", dependencies=[])
    result = generate_single_file(spec, {"design_system": {"visual_direction": "studio"}, "already_generated": {}})
    content = result["src/app/page.tsx"]
    assert "export default function Page" in content
    assert "landing" in content
    assert "studio" in content


def test_generate_single_file_component_template_contains_component_name():
    spec = FileSpec(path="src/components/HeroBanner.tsx", file_type="component", description="hero", dependencies=[])
    result = generate_single_file(spec, {"already_generated": {}})
    content = result["src/components/HeroBanner.tsx"]
    assert "export function HeroBanner" in content
    assert "export default HeroBanner" in content


def test_generate_single_file_api_template_contains_post_handler():
    spec = FileSpec(path="src/lib/api.ts", file_type="api", description="api client", dependencies=[])
    result = generate_single_file(spec, {"api_contract": "POST /api/plan", "already_generated": {}})
    content = result["src/lib/api.ts"]
    assert "export async function POST" in content
    assert "NextResponse.json" in content
    assert "POST /api/plan" in content


def test_generate_single_file_route_template_contains_router():
    spec = FileSpec(path="routes.py", file_type="route", description="routes", dependencies=[])
    result = generate_single_file(spec, {"already_generated": {}})
    content = result["routes.py"]
    assert "APIRouter" in content
    assert "@router.get" in content


def test_generate_single_file_service_template_contains_class():
    spec = FileSpec(path="ai_service.py", file_type="service", description="svc", dependencies=[])
    result = generate_single_file(spec, {"already_generated": {}})
    content = result["ai_service.py"]
    assert "class AiServiceService" in content
    assert "def execute" in content


def test_generate_single_file_config_template_for_package_json_is_valid_json():
    spec = FileSpec(path="package.json", file_type="config", description="manifest", dependencies=[])
    result = generate_single_file(spec, {"already_generated": {}})
    payload = json.loads(result["package.json"])
    assert payload["private"] is True
    assert payload["description"] == "manifest"


def test_generate_single_file_style_template_contains_css_blocks():
    spec = FileSpec(path="src/app/globals.css", file_type="style", description="styles", dependencies=[])
    result = generate_single_file(spec, {"already_generated": {}})
    content = result["src/app/globals.css"]
    assert ".container" in content
    assert ".title" in content


def test_per_file_code_generator_node_returns_empty_when_env_var_disabled(monkeypatch):
    monkeypatch.delenv("VIBEDEPLOY_USE_PER_FILE_CODEGEN", raising=False)
    result = per_file_code_generator_node({"blueprint": _sample_blueprint()})
    assert result == {}


def test_per_file_code_generator_node_generates_and_splits_frontend_backend(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_USE_PER_FILE_CODEGEN", "1")
    state = {
        "blueprint": _sample_blueprint(),
        "api_contract": "POST /api/plan",
        "frontend_code": {"src/existing.ts": "old"},
        "backend_code": {"existing.py": "old"},
    }

    result = per_file_code_generator_node(state)

    assert result["phase"] == "code_generated"
    assert "src/app/page.tsx" in result["frontend_code"]
    assert "src/components/Hero.tsx" in result["frontend_code"]
    assert "routes.py" in result["backend_code"]
    assert "ai_service.py" in result["backend_code"]
    assert "src/existing.ts" in result["frontend_code"]
    assert "existing.py" in result["backend_code"]


def test_per_file_code_generator_node_handles_empty_blueprint_when_enabled(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_USE_PER_FILE_CODEGEN", "1")
    result = per_file_code_generator_node({"blueprint": {}})
    assert result["frontend_code"] == {}
    assert result["backend_code"] == {}
    assert result["phase"] == "code_generated"
