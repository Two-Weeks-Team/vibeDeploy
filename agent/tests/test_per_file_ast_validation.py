from agent.nodes.per_file_code_generator import (
    _MAX_RETRY_ATTEMPTS,
    generate_files_with_validation,
    generate_single_file,
    validate_generated_file,
    validate_generated_files,
)

VALID_PYTHON = "def add(a, b):\n    return a + b\n"
INVALID_PYTHON = "def add(a, b\n    return a + b\n"

VALID_TSX = (
    'import { useState } from "react";\n'
    "export default function App() {\n"
    "  const [count, setCount] = useState(0);\n"
    "  return <button onClick={() => setCount(count + 1)}>{count}</button>;\n"
    "}\n"
)

UNBALANCED_BRACE_TSX = (
    'import { useState } from "react";\nexport default function App() {\n  return <div>hello</div>;\n'
)

UNBALANCED_PAREN_TSX = "export default function App( {\n  return <div>hello</div>;\n}\n"

UNBALANCED_BRACKET_TSX = (
    "const items = [1, 2, 3;\nexport default function App() {\n  return <div>{items.length}</div>;\n}\n"
)

BROKEN_IMPORT_TSX = 'import from "react";\nexport default function App() { return <div />; }\n'


class TestValidatePython:
    def test_valid_python_passes(self):
        result = validate_generated_file("main.py", VALID_PYTHON)
        assert result["passed"] is True
        assert result["error"] == ""

    def test_invalid_python_fails_with_syntax_error(self):
        result = validate_generated_file("main.py", INVALID_PYTHON)
        assert result["passed"] is False
        assert "SyntaxError" in result["error"]

    def test_empty_python_file_passes(self):
        result = validate_generated_file("utils.py", "")
        assert result["passed"] is True

    def test_whitespace_only_python_passes(self):
        result = validate_generated_file("utils.py", "   \n\n  \t  \n")
        assert result["passed"] is True

    def test_complex_valid_python_passes(self):
        code = (
            "from typing import List\n\n"
            "class Processor:\n"
            "    def __init__(self, items: List[str]) -> None:\n"
            "        self.items = items\n\n"
            "    def run(self) -> List[str]:\n"
            "        return [item.upper() for item in self.items]\n"
        )
        result = validate_generated_file("processor.py", code)
        assert result["passed"] is True


class TestValidateJsTs:
    def test_valid_tsx_passes(self):
        result = validate_generated_file("App.tsx", VALID_TSX)
        assert result["passed"] is True
        assert result["error"] == ""

    def test_unbalanced_brace_fails(self):
        result = validate_generated_file("App.tsx", UNBALANCED_BRACE_TSX)
        assert result["passed"] is False
        assert "Unbalanced bracket" in result["error"]

    def test_unbalanced_paren_fails(self):
        result = validate_generated_file("App.tsx", UNBALANCED_PAREN_TSX)
        assert result["passed"] is False
        assert "Unbalanced bracket" in result["error"]

    def test_unbalanced_bracket_fails(self):
        result = validate_generated_file("page.ts", UNBALANCED_BRACKET_TSX)
        assert result["passed"] is False
        assert "Unbalanced bracket" in result["error"]

    def test_broken_import_fails(self):
        result = validate_generated_file("App.tsx", BROKEN_IMPORT_TSX)
        assert result["passed"] is False
        assert "Invalid import" in result["error"]

    def test_empty_ts_file_passes(self):
        result = validate_generated_file("types.ts", "")
        assert result["passed"] is True

    def test_valid_js_with_template_literal_passes(self):
        code = 'const msg = `Hello ${"world"}`;\nconsole.log(msg);\n'
        result = validate_generated_file("helper.js", code)
        assert result["passed"] is True

    def test_bracket_inside_string_ignored(self):
        code = 'const x = "unmatched {";\nexport default function f() { return x; }\n'
        result = validate_generated_file("util.ts", code)
        assert result["passed"] is True

    def test_bracket_inside_line_comment_ignored(self):
        code = "export default function f() {\n  return 1; // closed }\n}\n"
        result = validate_generated_file("util.ts", code)
        assert result["passed"] is True


class TestUnsupportedExtension:
    def test_css_file_always_passes(self):
        result = validate_generated_file("styles.css", "body { color: red")
        assert result["passed"] is True

    def test_json_file_always_passes(self):
        result = validate_generated_file("config.json", '{"broken": true')
        assert result["passed"] is True

    def test_markdown_file_always_passes(self):
        result = validate_generated_file("README.md", "# Hello")
        assert result["passed"] is True


class TestValidateGeneratedFiles:
    def test_returns_per_file_map(self):
        files = {
            "main.py": VALID_PYTHON,
            "App.tsx": VALID_TSX,
            "broken.py": INVALID_PYTHON,
        }
        results = validate_generated_files(files)
        assert set(results.keys()) == {"main.py", "App.tsx", "broken.py"}
        assert results["main.py"]["passed"] is True
        assert results["App.tsx"]["passed"] is True
        assert results["broken.py"]["passed"] is False

    def test_empty_dict_returns_empty_map(self):
        assert validate_generated_files({}) == {}


class TestGenerateSingleFile:
    def test_passes_on_first_try(self):
        outcome = generate_single_file("main.py", lambda: VALID_PYTHON)
        assert outcome["validation"]["passed"] is True
        assert outcome["content"] == VALID_PYTHON
        assert outcome["attempts"] == 1
        assert outcome["used_fallback"] is False

    def test_returns_fallback_after_max_retries(self):
        outcome = generate_single_file("main.py", lambda: INVALID_PYTHON)
        assert outcome["used_fallback"] is True
        assert outcome["attempts"] == _MAX_RETRY_ATTEMPTS
        assert "vibedeploy-fallback" in outcome["content"]
        assert outcome["validation"]["passed"] is False

    def test_fallback_content_for_py_uses_hash_comment(self):
        outcome = generate_single_file("service.py", lambda: INVALID_PYTHON)
        assert outcome["content"].startswith("#")

    def test_fallback_content_for_tsx_uses_slash_comment(self):
        outcome = generate_single_file("App.tsx", lambda: UNBALANCED_BRACE_TSX)
        assert outcome["content"].startswith("//")

    def test_custom_max_retries_respected(self):
        call_count = 0

        def bad_factory():
            nonlocal call_count
            call_count += 1
            return INVALID_PYTHON

        outcome = generate_single_file("main.py", bad_factory, max_retries=2)
        assert call_count == 2
        assert outcome["used_fallback"] is True
        assert outcome["attempts"] == 2

    def test_factory_exception_counts_as_failed_attempt(self):
        call_count = 0

        def exploding_factory():
            nonlocal call_count
            call_count += 1
            raise ValueError("simulated generation error")

        outcome = generate_single_file("main.py", exploding_factory, max_retries=3)
        assert call_count == 3
        assert outcome["used_fallback"] is True
        assert "content_factory raised" in outcome["validation"]["error"]


class TestGenerateFilesWithValidation:
    def test_only_failed_file_retried_not_all(self):
        files = {
            "ok.py": VALID_PYTHON,
            "broken.py": INVALID_PYTHON,
            "also_ok.tsx": VALID_TSX,
        }

        result = generate_files_with_validation(files, max_retries=3)

        assert result["retry_metadata"]["ok.py"]["attempts"] == 1
        assert result["retry_metadata"]["ok.py"]["used_fallback"] is False
        assert result["retry_metadata"]["also_ok.tsx"]["attempts"] == 1
        assert result["retry_metadata"]["broken.py"]["used_fallback"] is True

    def test_passing_files_content_unchanged(self):
        files = {"ok.py": VALID_PYTHON, "app.tsx": VALID_TSX}
        result = generate_files_with_validation(files)
        assert result["files"]["ok.py"] == VALID_PYTHON
        assert result["files"]["app.tsx"] == VALID_TSX

    def test_validation_results_present_for_all_files(self):
        files = {"ok.py": VALID_PYTHON, "broken.py": INVALID_PYTHON}
        result = generate_files_with_validation(files)
        assert "ok.py" in result["validation_results"]
        assert "broken.py" in result["validation_results"]
        assert result["validation_results"]["ok.py"]["passed"] is True

    def test_failed_file_replaced_with_fallback_marker(self):
        files = {"broken.py": INVALID_PYTHON}
        result = generate_files_with_validation(files, max_retries=3)
        assert "vibedeploy-fallback" in result["files"]["broken.py"]

    def test_empty_files_dict_returns_empty_result(self):
        result = generate_files_with_validation({})
        assert result["files"] == {}
        assert result["validation_results"] == {}
        assert result["retry_metadata"] == {}
