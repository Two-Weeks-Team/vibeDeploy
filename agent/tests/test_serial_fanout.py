import pytest

from agent.nodes import brainstorm as brainstorm_module
from agent.nodes import vibe_council as council_module


def test_council_fan_out_serializes_when_enabled(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_SERIALIZE_AGENT_FANOUT", "1")

    sends = council_module.fan_out_analysis({"idea": {"name": "Demo"}, "idea_summary": "demo"})

    assert len(sends) == 1
    assert sends[0].node == "run_council_agent"
    assert sends[0].arg["serial_run"] is True


@pytest.mark.asyncio
async def test_council_run_serial_mode_merges_all_agents(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_SERIALIZE_AGENT_FANOUT", "1")

    async def fake_analyze(idea):
        return {"findings": [idea["name"]], "score": 77, "reasoning": "ok"}

    for module in council_module.COUNCIL_MEMBERS.values():
        monkeypatch.setattr(module, "analyze", fake_analyze)

    result = await council_module.run_council_agent(
        {"serial_run": True, "agent_names": ["architect", "scout"], "idea": {"name": "Demo"}}
    )

    assert sorted(result["council_analysis"].keys()) == ["architect", "scout"]


def test_brainstorm_fan_out_serializes_when_enabled(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_SERIALIZE_AGENT_FANOUT", "1")

    sends = brainstorm_module.fan_out_brainstorm({"idea": {"name": "Demo"}, "idea_summary": "demo"})

    assert len(sends) == 1
    assert sends[0].node == "run_brainstorm_agent"
    assert sends[0].arg["serial_run"] is True


@pytest.mark.asyncio
async def test_brainstorm_run_serial_mode_merges_all_agents(monkeypatch):
    monkeypatch.setenv("VIBEDEPLOY_SERIALIZE_AGENT_FANOUT", "1")

    class FakeLLM:
        async def ainvoke(self, messages):
            return type("Resp", (), {"content": '{"ideas":[],"opportunities":[],"wild_card":"x","action_items":[]}'})()

    monkeypatch.setattr("agent.llm.get_llm", lambda **kwargs: FakeLLM())
    monkeypatch.setattr("agent.llm.ainvoke_with_retry", lambda llm, messages, **kwargs: llm.ainvoke(messages))
    monkeypatch.setattr("agent.llm.get_rate_limit_fallback_models", lambda model: [])

    result = await brainstorm_module.run_brainstorm_agent(
        {"serial_run": True, "agent_names": ["architect", "scout"], "idea": {"name": "Demo"}}
    )

    assert sorted(result["brainstorm_insights"].keys()) == ["architect", "scout"]
