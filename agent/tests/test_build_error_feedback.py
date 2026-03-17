from agent.graph import route_after_build
from agent.nodes.build_validator import (
    MAX_BUILD_ATTEMPTS,
    TEMPERATURE_SCHEDULE,
    _build_repair_prompt,
    _trim_build_errors,
)


def test_trim_build_errors_extracts_up_to_3_errors():
    stderr = "\n".join(
        [
            "line1: error: something went wrong",
            "line2: error: another issue",
            "line3: error: third problem",
            "line4: error: fourth problem should be dropped",
        ]
    )
    result = _trim_build_errors(stderr)
    lines = result.splitlines()
    assert len(lines) == 3


def test_trim_build_errors_handles_empty_stderr():
    result = _trim_build_errors("")
    assert result == "Unknown build error"


def test_trim_build_errors_handles_none_like_empty():
    result = _trim_build_errors(None)
    assert result == "Unknown build error"


def test_trim_build_errors_extracts_error_keywords():
    stderr = "some log\nerror: bad thing happened\nanother log\nfailed to compile"
    result = _trim_build_errors(stderr)
    assert "error: bad thing happened" in result or "failed to compile" in result


def test_trim_build_errors_falls_back_to_first_3_lines_when_no_keywords():
    stderr = "line one\nline two\nline three\nline four"
    result = _trim_build_errors(stderr)
    lines = result.splitlines()
    assert len(lines) == 3
    assert "line one" in lines[0]


def test_build_repair_prompt_includes_errors_and_code():
    errors = "error: missing import"
    failing_files = {"main.py": "import missing_module\n"}
    result = _build_repair_prompt(errors, failing_files)
    assert "error: missing import" in result
    assert "main.py" in result
    assert "import missing_module" in result


def test_build_repair_prompt_includes_all_failing_files():
    errors = "error: build failed"
    failing_files = {
        "main.py": "code1\n",
        "utils.py": "code2\n",
    }
    result = _build_repair_prompt(errors, failing_files)
    assert "main.py" in result
    assert "utils.py" in result
    assert "code1" in result
    assert "code2" in result


def test_temperature_schedule_has_3_values():
    assert len(TEMPERATURE_SCHEDULE) == 3


def test_temperature_schedule_values_are_descending():
    for i in range(len(TEMPERATURE_SCHEDULE) - 1):
        assert TEMPERATURE_SCHEDULE[i] > TEMPERATURE_SCHEDULE[i + 1]


def test_max_build_attempts_is_3():
    assert MAX_BUILD_ATTEMPTS == 3


def test_route_after_build_passed_returns_deployer():
    state = {"build_validation": {"passed": True}, "build_attempt_count": 0}
    assert route_after_build(state) == "deployer"


def test_route_after_build_failed_3_times_returns_end():
    state = {"build_validation": {"passed": False}, "build_attempt_count": 3}
    assert route_after_build(state) == "__end__"


def test_route_after_build_failed_less_than_3_returns_code_generator():
    state = {"build_validation": {"passed": False}, "build_attempt_count": 1}
    assert route_after_build(state) == "code_generator"


def test_route_after_build_zero_attempts_failed_returns_code_generator():
    state = {"build_validation": {"passed": False}, "build_attempt_count": 0}
    assert route_after_build(state) == "code_generator"


def test_route_after_build_missing_build_validation_returns_code_generator():
    state = {"build_attempt_count": 0}
    assert route_after_build(state) == "code_generator"


def test_route_after_build_missing_attempt_count_treats_as_zero():
    state = {"build_validation": {"passed": False}}
    assert route_after_build(state) == "code_generator"
