import logging
from dataclasses import dataclass

from agent.gradient.agents import AgentConfig, get_agent, list_agents

logger = logging.getLogger(__name__)

_INTENT_RULES: list[tuple[list[str], str]] = [
    (["market", "competitor", "competition", "trend", "audience"], "scout"),
    (["innovation", "creative", "disrupt", "unique", "novel", "idea"], "catalyst"),
    (["technical", "architecture", "tech stack", "system design", "infrastructure", "code"], "architect"),
]

_DEFAULT_AGENT = "architect"


@dataclass
class RoutingResult:
    agent_name: str
    agent_config: AgentConfig
    reason: str


class RouterAgent:
    def list_agents(self) -> list[AgentConfig]:
        return list_agents()

    def route(self, input_text: str) -> RoutingResult:
        lowered = input_text.lower()
        for keywords, agent_name in _INTENT_RULES:
            for kw in keywords:
                if kw in lowered:
                    config = get_agent(agent_name)
                    if config is None:
                        logger.warning("[RouterAgent] Agent '%s' in _INTENT_RULES not found in registry", agent_name)
                        continue
                    return RoutingResult(
                        agent_name=agent_name,
                        agent_config=config,
                        reason=f"Input contains '{kw}' keyword matched to {agent_name} agent.",
                    )
        config = get_agent(_DEFAULT_AGENT)
        if config is None:
            raise RuntimeError(f"Default agent '{_DEFAULT_AGENT}' not found in registry.")
        return RoutingResult(
            agent_name=_DEFAULT_AGENT,
            agent_config=config,
            reason=f"No specific intent detected; routed to default agent '{_DEFAULT_AGENT}'.",
        )
