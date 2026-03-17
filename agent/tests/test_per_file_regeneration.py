from agent.nodes.per_file_regeneration import (
    TEMPERATURE_SCHEDULE,
    RegenerationResult,
    build_regen_prompt,
    get_temperature_for_attempt,
    log_regeneration_stats,
    regenerate_file,
)


def test_temperature_schedule_has_three_values():
    assert len(TEMPERATURE_SCHEDULE) == 3


def test_get_temperature_attempt_1():
    assert get_temperature_for_attempt(1) == 0.1


def test_get_temperature_attempt_2():
    assert get_temperature_for_attempt(2) == 0.05


def test_get_temperature_attempt_3():
    assert get_temperature_for_attempt(3) == 0.02


def test_get_temperature_clamps_for_overflow():
    assert get_temperature_for_attempt(4) == 0.02
    assert get_temperature_for_attempt(99) == 0.02


def test_build_regen_prompt_includes_error_text():
    prompt = build_regen_prompt("generate a page", "SyntaxError: invalid syntax", attempt=2)
    assert "SyntaxError: invalid syntax" in prompt


def test_build_regen_prompt_includes_attempt_number():
    prompt = build_regen_prompt("generate a page", "some error", attempt=3)
    assert "3" in prompt


def test_build_regen_prompt_no_error_still_contains_original_and_attempt():
    prompt = build_regen_prompt("generate a page", "", attempt=1)
    assert "generate a page" in prompt
    assert "1" in prompt


def test_regenerate_file_succeeds_on_first_try():
    def factory(_prompt: str, _temp: float) -> str:
        return "def hello():\n    return 42\n"

    result = regenerate_file("app.py", "generate a function", factory)
    assert isinstance(result, RegenerationResult)
    assert result.used_fallback is False
    assert result.attempts == 1
    assert "hello" in result.content


def test_regenerate_file_retries_with_decaying_temperature():
    call_log: list[float] = []

    def factory(_prompt: str, temp: float) -> str:
        call_log.append(temp)
        if len(call_log) < 2:
            return "def broken!!!\n"
        return "def ok():\n    pass\n"

    result = regenerate_file("app.py", "generate", factory)
    assert result.used_fallback is False
    assert result.attempts == 2
    assert call_log[0] == 0.1
    assert call_log[1] == 0.05


def test_regenerate_file_returns_fallback_after_max_retries():
    def factory(_prompt: str, _temp: float) -> str:
        return "def broken!!!\n"

    result = regenerate_file("app.py", "generate", factory, max_retries=3)
    assert result.used_fallback is True
    assert result.attempts == 3


def test_regenerate_file_tracks_temperatures_used():
    def factory(_prompt: str, _temp: float) -> str:
        return "def broken!!!\n"

    result = regenerate_file("app.py", "generate", factory, max_retries=3)
    assert result.temperatures_used == [0.1, 0.05, 0.02]


def test_regenerate_file_tracks_errors_list():
    def factory(_prompt: str, _temp: float) -> str:
        return "def broken!!!\n"

    result = regenerate_file("app.py", "generate", factory, max_retries=3)
    assert len(result.errors) == 3
    for err in result.errors:
        assert isinstance(err, str)
        assert len(err) > 0


def test_regenerate_file_uses_full_temperature_schedule_for_three_attempts():
    temps: list[float] = []

    def factory(_prompt: str, temp: float) -> str:
        temps.append(temp)
        return "def broken!!!\n"

    regenerate_file("app.py", "generate", factory, max_retries=3)
    assert temps == [0.1, 0.05, 0.02]


def test_regenerate_file_factory_exception_recorded_in_errors():
    def factory(_prompt: str, _temp: float) -> str:
        raise RuntimeError("network timeout")

    result = regenerate_file("app.py", "generate", factory, max_retries=2)
    assert result.used_fallback is True
    assert len(result.errors) == 2
    assert all("network timeout" in e for e in result.errors)


def test_log_regeneration_stats_computes_correct_summary():
    results = [
        RegenerationResult(
            path="a.py", content="x", attempts=1, used_fallback=False, temperatures_used=[0.1], errors=[]
        ),
        RegenerationResult(
            path="b.py", content="y", attempts=2, used_fallback=False, temperatures_used=[0.1, 0.05], errors=["e1"]
        ),
        RegenerationResult(
            path="c.py",
            content="z",
            attempts=3,
            used_fallback=True,
            temperatures_used=[0.1, 0.05, 0.02],
            errors=["e1", "e2", "e3"],
        ),
    ]
    stats = log_regeneration_stats(results)
    assert stats["total"] == 3
    assert stats["succeeded"] == 2
    assert stats["failed"] == 1
    assert stats["fallback_count"] == 1
    assert abs(stats["avg_attempts"] - 2.0) < 1e-9


def test_log_regeneration_stats_empty_list_returns_zero_summary():
    stats = log_regeneration_stats([])
    assert stats["total"] == 0
    assert stats["succeeded"] == 0
    assert stats["failed"] == 0
    assert stats["fallback_count"] == 0
    assert stats["avg_attempts"] == 0.0
