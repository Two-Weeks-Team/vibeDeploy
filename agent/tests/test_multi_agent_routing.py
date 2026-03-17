import pytest

from agent.gradient.agents import AgentConfig, list_agents
from agent.gradient.router import RouterAgent


@pytest.mark.unit
def test_list_agents_returns_three_agents():
    agents = list_agents()
    assert len(agents) == 3


@pytest.mark.unit
def test_list_agents_returns_agent_config_instances():
    agents = list_agents()
    for agent in agents:
        assert isinstance(agent, AgentConfig)


@pytest.mark.unit
def test_list_agents_contains_expected_names():
    agents = list_agents()
    names = {a.name for a in agents}
    assert names == {"scout", "catalyst", "architect"}


@pytest.mark.unit
def test_agent_config_has_required_fields():
    agents = list_agents()
    for agent in agents:
        assert agent.agent_id
        assert agent.name
        assert agent.description
        assert isinstance(agent.endpoint_url, str)


@pytest.mark.unit
def test_route_market_keyword_to_scout():
    router = RouterAgent()
    result = router.route("I want to analyze the market for my SaaS app")
    assert result.agent_name == "scout"
    assert "scout" in result.reason


@pytest.mark.unit
def test_route_competitor_keyword_to_scout():
    router = RouterAgent()
    result = router.route("Who are the main competitor platforms in this space?")
    assert result.agent_name == "scout"


@pytest.mark.unit
def test_route_innovation_keyword_to_catalyst():
    router = RouterAgent()
    result = router.route("I need something truly innovative and disruptive")
    assert result.agent_name == "catalyst"
    assert "catalyst" in result.reason


@pytest.mark.unit
def test_route_creative_keyword_to_catalyst():
    router = RouterAgent()
    result = router.route("Give me a creative approach to this problem")
    assert result.agent_name == "catalyst"


@pytest.mark.unit
def test_route_technical_keyword_to_architect():
    router = RouterAgent()
    result = router.route("What technical stack should I use for this service?")
    assert result.agent_name == "architect"
    assert "architect" in result.reason


@pytest.mark.unit
def test_route_architecture_keyword_to_architect():
    router = RouterAgent()
    result = router.route("Design the architecture for a microservices system")
    assert result.agent_name == "architect"


@pytest.mark.unit
def test_route_unknown_input_falls_back_to_default():
    router = RouterAgent()
    result = router.route("Hello, help me please")
    assert result.agent_name == "architect"
    assert "default" in result.reason.lower()


@pytest.mark.unit
def test_route_returns_routing_result_with_agent_config():
    router = RouterAgent()
    result = router.route("How do I design the system architecture?")
    assert result.agent_config is not None
    assert isinstance(result.agent_config, AgentConfig)
    assert result.agent_config.name == result.agent_name


@pytest.mark.unit
def test_router_list_agents_matches_module_list():
    router = RouterAgent()
    router_agents = router.list_agents()
    module_agents = list_agents()
    assert len(router_agents) == len(module_agents)
    router_names = {a.name for a in router_agents}
    module_names = {a.name for a in module_agents}
    assert router_names == module_names


@pytest.mark.unit
def test_route_case_insensitive_matching():
    router = RouterAgent()
    result_upper = router.route("MARKET analysis for my product")
    result_lower = router.route("market analysis for my product")
    assert result_upper.agent_name == result_lower.agent_name == "scout"


@pytest.mark.unit
def test_route_reason_is_non_empty_string():
    router = RouterAgent()
    for text in [
        "competitor analysis",
        "creative brainstorm",
        "technical architecture",
        "random unrelated text",
    ]:
        result = router.route(text)
        assert isinstance(result.reason, str)
        assert len(result.reason) > 0
