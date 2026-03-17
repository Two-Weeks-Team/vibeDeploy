import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    agent_id: str
    name: str
    endpoint_url: str
    description: str


_REGISTRY: dict[str, AgentConfig] = {
    "scout": AgentConfig(
        agent_id="gradient-scout-v1",
        name="scout",
        endpoint_url=os.environ.get("GRADIENT_SCOUT_ENDPOINT_URL", ""),
        description="Market analyst specializing in competition, trends, and market fit research.",
    ),
    "catalyst": AgentConfig(
        agent_id="gradient-catalyst-v1",
        name="catalyst",
        endpoint_url=os.environ.get("GRADIENT_CATALYST_ENDPOINT_URL", ""),
        description="Innovation officer focused on uniqueness, disruption, and creative ideation.",
    ),
    "architect": AgentConfig(
        agent_id="gradient-architect-v1",
        name="architect",
        endpoint_url=os.environ.get("GRADIENT_ARCHITECT_ENDPOINT_URL", ""),
        description="Technical lead evaluating tech stack, complexity, and system architecture.",
    ),
}


def list_agents() -> list[AgentConfig]:
    return list(_REGISTRY.values())


def get_agent(name: str) -> AgentConfig | None:
    return _REGISTRY.get(name)
