"""Tests for build_meeting_result score logic in pipeline_runtime.py.

Covers the fix where final_score=0 must be preserved and not overwritten by match_rate.
"""

from agent.pipeline_runtime import build_meeting_result


class TestBuildMeetingResultScore:
    """Score field in build_meeting_result must follow the fallback chain:
    scoring.final_score  ->  code_eval_result.match_rate  ->  0
    """

    def test_final_score_zero_preserved(self):
        """final_score=0 must be preserved in the result, not overwritten by match_rate."""
        state = {
            "scoring": {"final_score": 0, "decision": "NO_GO"},
            "code_eval_result": {"match_rate": 85},
        }
        result = build_meeting_result(state)
        assert result["score"] == 0

    def test_final_score_nonzero_used(self):
        """A non-zero final_score should appear as-is in the result."""
        state = {
            "scoring": {"final_score": 72, "decision": "GO"},
        }
        result = build_meeting_result(state)
        assert result["score"] == 72

    def test_no_final_score_falls_back_to_match_rate(self):
        """When final_score is absent (None), score should fall back to match_rate."""
        state = {
            "scoring": {"decision": "NO_GO"},
            "code_eval_result": {"match_rate": 65},
        }
        result = build_meeting_result(state)
        assert result["score"] == 65

    def test_final_score_none_falls_back_to_match_rate(self):
        """When final_score is explicitly None, score should fall back to match_rate."""
        state = {
            "scoring": {"final_score": None, "decision": "NO_GO"},
            "code_eval_result": {"match_rate": 50},
        }
        result = build_meeting_result(state)
        assert result["score"] == 50

    def test_no_final_score_no_match_rate_defaults_to_zero(self):
        """When neither final_score nor match_rate exist, score should be 0."""
        state = {
            "scoring": {"decision": "NO_GO"},
        }
        result = build_meeting_result(state)
        assert result["score"] == 0

    def test_empty_state_defaults_to_zero(self):
        """A completely empty state should produce score=0."""
        result = build_meeting_result({})
        assert result["score"] == 0

    def test_match_rate_zero_used_as_fallback(self):
        """match_rate=0 is a valid numeric fallback (not None)."""
        state = {
            "scoring": {"decision": "NO_GO"},
            "code_eval_result": {"match_rate": 0},
        }
        result = build_meeting_result(state)
        assert result["score"] == 0

    def test_match_rate_float_accepted(self):
        """match_rate as a float should be accepted as a valid score."""
        state = {
            "scoring": {"decision": "GO"},
            "code_eval_result": {"match_rate": 92.5},
        }
        result = build_meeting_result(state)
        assert result["score"] == 92.5

    def test_code_eval_result_not_dict_ignored(self):
        """If code_eval_result is not a dict, match_rate fallback should not apply."""
        state = {
            "scoring": {"decision": "NO_GO"},
            "code_eval_result": "invalid",
        }
        result = build_meeting_result(state)
        assert result["score"] == 0

    def test_match_rate_string_not_used(self):
        """A non-numeric match_rate should not be used as score (isinstance check)."""
        state = {
            "scoring": {"decision": "NO_GO"},
            "code_eval_result": {"match_rate": "high"},
        }
        result = build_meeting_result(state)
        assert result["score"] == 0


class TestBuildMeetingResultVerdict:
    """Verdict logic tests to complement the score tests."""

    def test_go_verdict(self):
        state = {"scoring": {"final_score": 80, "decision": "GO"}}
        result = build_meeting_result(state)
        assert result["verdict"] == "GO"

    def test_nogo_verdict(self):
        state = {"scoring": {"final_score": 30, "decision": "NO_GO"}}
        result = build_meeting_result(state)
        assert result["verdict"] == "NO-GO"

    def test_conditional_verdict(self):
        state = {"scoring": {"final_score": 55, "decision": "CONDITIONAL"}}
        result = build_meeting_result(state)
        assert result["verdict"] == "CONDITIONAL"

    def test_pipeline_success_overrides_verdict_to_go(self):
        state = {
            "scoring": {"final_score": 30, "decision": "NO_GO"},
            "code_eval_result": {"passed": True},
            "build_validation": {"passed": True},
            "local_runtime_validation": {"passed": True},
            "deploy_gate_result": {"passed": True},
            "deploy_result": {"status": "deployed"},
        }
        result = build_meeting_result(state)
        assert result["verdict"] == "GO"
