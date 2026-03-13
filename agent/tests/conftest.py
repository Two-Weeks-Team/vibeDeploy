import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agent.db.store import ResultStore


@pytest_asyncio.fixture
async def store() -> AsyncIterator[ResultStore]:
    s = ResultStore(":memory:")
    await s.init()
    yield s
    await s.close()


@pytest_asyncio.fixture
async def app_client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncClient]:
    import agent.server as srv

    s = ResultStore(":memory:")
    await s.init()
    monkeypatch.setenv("VIBEDEPLOY_ENABLE_TEST_API", "1")
    monkeypatch.setattr(srv, "_store", s)

    transport = ASGITransport(app=srv.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    await s.close()


def make_chain_event(kind: str, name: str, output: dict | None = None, data: dict | None = None) -> dict[str, Any]:
    ev: dict[str, Any] = {"event": kind, "name": name, "data": dict(data or {})}
    if kind == "on_chain_end" and output is not None:
        ev["data"]["output"] = output
    return ev


def parse_sse_events(raw: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    current_event = ""
    current_data = ""
    for line in raw.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event:
            events.append({"event": current_event, "data": json.loads(current_data)})
            current_event = ""
            current_data = ""
    return events


def _make_fake_graph(events_factory):
    mock = MagicMock()
    mock.astream_events = lambda *a, **kw: events_factory()
    return mock


def _eval_events():
    return [
        make_chain_event("on_chain_start", "input_processor"),
        make_chain_event(
            "on_chain_end",
            "input_processor",
            {"phase": "input_processing", "idea": {"title": "Test App"}, "idea_summary": "A test app"},
        ),
        make_chain_event("on_chain_start", "run_council_agent", data={"input": {"agent_name": "architect"}}),
        make_chain_event(
            "on_chain_end",
            "run_council_agent",
            {"phase": "individual_analysis", "council_analysis": {"architect": {"score": 80, "findings": ["solid"]}}},
        ),
        make_chain_event("on_chain_start", "cross_examination"),
        make_chain_event(
            "on_chain_end",
            "cross_examination",
            {"phase": "cross_examination", "cross_examination": {"tech_feasibility": {"summary": "good"}}},
        ),
        make_chain_event("on_chain_start", "score_axis", data={"input": {"agent_name": "architect"}}),
        make_chain_event(
            "on_chain_end",
            "score_axis",
            {
                "phase": "scoring",
                "scoring": {"technical_feasibility": {"score": 80, "reasoning": "clear", "key_findings": ["solid"]}},
            },
        ),
        make_chain_event("on_chain_start", "strategist_verdict"),
        make_chain_event(
            "on_chain_end", "strategist_verdict", {"phase": "verdict", "scoring": {"final_score": 82, "decision": "GO"}}
        ),
        make_chain_event("on_chain_start", "decision_gate"),
        make_chain_event("on_chain_end", "decision_gate", {"phase": "decision"}),
        make_chain_event("on_chain_start", "doc_generator"),
        make_chain_event(
            "on_chain_end", "doc_generator", {"phase": "doc_generation", "generated_docs": {"prd": "# PRD"}}
        ),
        make_chain_event("on_chain_start", "code_generator"),
        make_chain_event("on_chain_end", "code_generator", {"phase": "code_generation"}),
        make_chain_event("on_chain_start", "deployer"),
        make_chain_event(
            "on_custom_event",
            "deploy.step.start",
            data={
                "type": "deploy.step.start",
                "node": "git_push",
                "phase": "git_push",
                "message": "Repository push started",
            },
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.complete",
            data={
                "type": "deploy.step.complete",
                "node": "git_push",
                "phase": "git_push",
                "message": "Repository push complete",
            },
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.start",
            data={"type": "deploy.step.start", "node": "ci_test", "phase": "ci_test", "message": "CI started"},
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.complete",
            data={"type": "deploy.step.complete", "node": "ci_test", "phase": "ci_test", "message": "CI complete"},
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.start",
            data={"type": "deploy.step.start", "node": "app_spec", "phase": "app_spec", "message": "App spec started"},
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.complete",
            data={
                "type": "deploy.step.complete",
                "node": "app_spec",
                "phase": "app_spec",
                "message": "App spec complete",
            },
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.start",
            data={"type": "deploy.step.start", "node": "do_build", "phase": "do_build", "message": "Build started"},
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.complete",
            data={"type": "deploy.step.complete", "node": "do_build", "phase": "do_build", "message": "Build complete"},
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.start",
            data={"type": "deploy.step.start", "node": "do_deploy", "phase": "do_deploy", "message": "Deploy started"},
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.complete",
            data={
                "type": "deploy.step.complete",
                "node": "do_deploy",
                "phase": "do_deploy",
                "message": "Deploy complete",
            },
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.start",
            data={
                "type": "deploy.step.start",
                "node": "verified",
                "phase": "verified",
                "message": "Verification started",
            },
        ),
        make_chain_event(
            "on_custom_event",
            "deploy.step.complete",
            data={
                "type": "deploy.step.complete",
                "node": "verified",
                "phase": "verified",
                "message": "Verification complete",
            },
        ),
        make_chain_event(
            "on_chain_end",
            "deployer",
            {
                "phase": "deployment",
                "deploy_result": {
                    "live_url": "https://test.app",
                    "github_repo": "https://github.com/test/app",
                    "status": "deployed",
                },
            },
        ),
    ]


def _nogo_events():
    return [
        make_chain_event("on_chain_start", "input_processor"),
        make_chain_event("on_chain_end", "input_processor", {"phase": "input_processing"}),
        make_chain_event("on_chain_start", "run_council_agent", data={"input": {"agent_name": "architect"}}),
        make_chain_event("on_chain_end", "run_council_agent", {"phase": "individual_analysis", "council_analysis": {}}),
        make_chain_event("on_chain_start", "cross_examination"),
        make_chain_event("on_chain_end", "cross_examination", {"phase": "cross_examination"}),
        make_chain_event("on_chain_start", "score_axis", data={"input": {"agent_name": "architect"}}),
        make_chain_event("on_chain_end", "score_axis", {"phase": "scoring", "scoring": {}}),
        make_chain_event("on_chain_start", "strategist_verdict"),
        make_chain_event(
            "on_chain_end",
            "strategist_verdict",
            {"phase": "verdict", "scoring": {"final_score": 30, "decision": "NO_GO"}},
        ),
        make_chain_event("on_chain_start", "decision_gate"),
        make_chain_event("on_chain_end", "decision_gate", {"phase": "decision"}),
        make_chain_event("on_chain_start", "feedback_generator"),
        make_chain_event("on_chain_end", "feedback_generator", {"phase": "feedback", "feedback": "Not viable"}),
    ]


def _brainstorm_events():
    return [
        make_chain_event("on_chain_start", "input_processor"),
        make_chain_event(
            "on_chain_end",
            "input_processor",
            {"phase": "input_processing", "idea": {"title": "Test Idea"}, "idea_summary": "A brainstorm test"},
        ),
        make_chain_event("on_chain_start", "run_brainstorm_agent"),
        make_chain_event(
            "on_chain_end",
            "run_brainstorm_agent",
            {
                "phase": "brainstorming",
                "brainstorm_insights": {"architect": {"ideas": ["idea1", "idea2"], "wild_card": "wild"}},
            },
        ),
        make_chain_event("on_chain_start", "run_brainstorm_agent"),
        make_chain_event(
            "on_chain_end",
            "run_brainstorm_agent",
            {
                "phase": "brainstorming",
                "brainstorm_insights": {"scout": {"ideas": ["market1"], "wild_card": "market_wild"}},
            },
        ),
        make_chain_event("on_chain_start", "synthesize_brainstorm"),
        make_chain_event(
            "on_chain_end",
            "synthesize_brainstorm",
            {"phase": "synthesis", "synthesis": {"top_ideas": ["combined1"], "themes": ["theme1"]}},
        ),
    ]


async def _async_iter(items):
    for item in items:
        yield item


async def _async_iter_then_raise(items, exc):
    for item in items:
        yield item
    raise exc


@pytest_asyncio.fixture
async def mock_eval_graph(monkeypatch):
    import agent.graph as graph_mod

    async def astream_events(*args, **kwargs):
        async for item in _async_iter(_eval_events()):
            yield item

    mock = MagicMock()
    mock.astream_events = astream_events
    monkeypatch.setattr(graph_mod, "app", mock)
    return mock


@pytest_asyncio.fixture
async def mock_nogo_graph(monkeypatch):
    import agent.graph as graph_mod

    async def astream_events(*args, **kwargs):
        async for item in _async_iter(_nogo_events()):
            yield item

    mock = MagicMock()
    mock.astream_events = astream_events
    monkeypatch.setattr(graph_mod, "app", mock)
    return mock


@pytest_asyncio.fixture
async def mock_error_graph(monkeypatch):
    import agent.graph as graph_mod

    async def astream_events(*args, **kwargs):
        yield make_chain_event("on_chain_start", "input_processor")
        raise RuntimeError("LLM provider error")

    mock = MagicMock()
    mock.astream_events = astream_events
    monkeypatch.setattr(graph_mod, "app", mock)
    return mock


@pytest_asyncio.fixture
async def mock_brainstorm_graph(monkeypatch):
    import agent.graph_brainstorm as bs_mod

    async def astream_events(*args, **kwargs):
        async for item in _async_iter(_brainstorm_events()):
            yield item

    mock = MagicMock()
    mock.astream_events = astream_events
    monkeypatch.setattr(bs_mod, "brainstorm_app", mock)
    return mock


@pytest_asyncio.fixture
async def mock_brainstorm_error_graph(monkeypatch):
    import agent.graph_brainstorm as bs_mod

    async def astream_events(*args, **kwargs):
        yield make_chain_event("on_chain_start", "input_processor")
        raise RuntimeError("Brainstorm LLM error")

    mock = MagicMock()
    mock.astream_events = astream_events
    monkeypatch.setattr(bs_mod, "brainstorm_app", mock)
    return mock
