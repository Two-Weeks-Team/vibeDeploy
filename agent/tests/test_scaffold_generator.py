import ast
import json

from agent.nodes.scaffold_generator import _NEXT_VERSION, _REACT_VERSION, generate_scaffold


def test_package_json_versions():
    files = generate_scaffold({"app_name": "test-app"})
    pkg = json.loads(files["web/package.json"])
    assert pkg["dependencies"]["next"] == _NEXT_VERSION
    assert pkg["dependencies"]["react"] == _REACT_VERSION
    assert pkg["dependencies"]["react-dom"] == _REACT_VERSION


def test_package_json_app_name():
    files = generate_scaffold({"app_name": "my-cool-app"})
    pkg = json.loads(files["web/package.json"])
    assert pkg["name"] == "my-cool-app"


def test_package_json_default_app_name():
    files = generate_scaffold({})
    pkg = json.loads(files["web/package.json"])
    assert pkg["name"] == "vibe-app"


def test_scaffold_returns_all_nine_files():
    files = generate_scaffold({})
    expected_paths = {
        "web/package.json",
        "web/tsconfig.json",
        "web/next.config.ts",
        "web/postcss.config.js",
        "web/src/app/globals.css",
        "web/src/app/layout.tsx",
        "agent/main.py",
        "agent/models.py",
        "agent/ai_service.py",
        "agent/requirements.txt",
    }
    assert set(files.keys()) == expected_paths


def test_main_py_passes_ast_parse():
    files = generate_scaffold({"app_name": "ast-test"})
    ast.parse(files["agent/main.py"])


def test_models_py_postgres_url_fix():
    files = generate_scaffold({})
    content = files["agent/models.py"]
    assert 'DATABASE_URL.replace("postgres://", "postgresql://", 1)' in content


def test_next_config_contains_standalone_and_rewrite():
    files = generate_scaffold({})
    content = files["web/next.config.ts"]
    assert '"standalone"' in content
    assert "/api/:path*" in content


def test_tsconfig_has_path_alias():
    files = generate_scaffold({})
    tsconfig = json.loads(files["web/tsconfig.json"])
    assert tsconfig["compilerOptions"]["paths"] == {"@/*": ["./src/*"]}


def test_extra_frontend_dependencies_merged():
    blueprint = {"dependencies": {"frontend": {"axios": "^1.0.0"}}}
    files = generate_scaffold(blueprint)
    pkg = json.loads(files["web/package.json"])
    assert pkg["dependencies"]["axios"] == "^1.0.0"
    assert pkg["dependencies"]["next"] == _NEXT_VERSION


def test_extra_backend_dependencies_appended():
    blueprint = {"dependencies": {"backend": ["boto3", "redis"]}}
    files = generate_scaffold(blueprint)
    content = files["agent/requirements.txt"]
    assert "boto3" in content
    assert "redis" in content
    assert "fastapi" in content


def test_globals_css_uses_tailwind_import():
    files = generate_scaffold({})
    assert "tailwindcss" in files["web/src/app/globals.css"]


def test_globals_css_has_oklch_variables():
    files = generate_scaffold({})
    css = files["web/src/app/globals.css"]
    oklch_count = css.count("oklch(")
    assert oklch_count >= 12, f"Expected ≥12 OKLCH variables, got {oklch_count}"


def test_globals_css_has_dark_block():
    files = generate_scaffold({})
    css = files["web/src/app/globals.css"]
    assert ".dark {" in css


def test_globals_css_has_root_block():
    files = generate_scaffold({})
    css = files["web/src/app/globals.css"]
    assert ":root {" in css


def test_globals_css_has_font_variables():
    files = generate_scaffold({})
    css = files["web/src/app/globals.css"]
    assert "--font-display:" in css
    assert "--font-body:" in css


def test_globals_css_domain_preset_applies():
    files_finance = generate_scaffold({"domain": "finance"})
    files_creative = generate_scaffold({"domain": "creative"})
    css_finance = files_finance["web/src/app/globals.css"]
    css_creative = files_creative["web/src/app/globals.css"]
    assert css_finance != css_creative


def test_globals_css_typography_hint_applies():
    files_tech = generate_scaffold({"typography_hint": "tech saas"})
    files_luxury = generate_scaffold({"typography_hint": "luxury fashion"})
    css_tech = files_tech["web/src/app/globals.css"]
    css_luxury = files_luxury["web/src/app/globals.css"]
    assert css_tech != css_luxury


def test_postcss_config_uses_tailwind_plugin():
    files = generate_scaffold({})
    assert "@tailwindcss/postcss" in files["web/postcss.config.js"]


def test_all_files_are_nonempty_strings():
    files = generate_scaffold({})
    for path, content in files.items():
        assert isinstance(content, str), f"{path} is not a string"
        assert len(content.strip()) > 0, f"{path} is empty"
