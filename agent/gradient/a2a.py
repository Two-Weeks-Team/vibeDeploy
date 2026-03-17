from agent.gradient.a2a_schemas import A2AMessage, A2AResponse

_MESSAGE_LOG: list[A2AMessage] = []

_KNOWN_AGENTS = {"scout", "catalyst", "architect", "guardian", "advocate", "strategist"}

_REQUIRED_HANDOFF_FIELDS = {"idea_name", "score"}


def validate_handoff(payload: dict) -> bool:
    return _REQUIRED_HANDOFF_FIELDS.issubset(payload.keys())


def get_message_log() -> list[A2AMessage]:
    return list(_MESSAGE_LOG)


def send_message(message: A2AMessage) -> A2AResponse:
    if message.receiver_agent not in _KNOWN_AGENTS:
        return A2AResponse(
            status="error",
            details=f"Unknown receiver agent: {message.receiver_agent}",
            receiver_agent=message.receiver_agent,
        )

    if message.message_type == "idea_handoff":
        if not validate_handoff(message.payload):
            missing = _REQUIRED_HANDOFF_FIELDS - set(message.payload.keys())
            return A2AResponse(
                status="rejected",
                details=f"idea_handoff payload missing required fields: {sorted(missing)}",
                receiver_agent=message.receiver_agent,
            )

    _MESSAGE_LOG.append(message)
    return A2AResponse(
        status="accepted",
        details=f"Message of type '{message.message_type}' delivered to {message.receiver_agent}",
        receiver_agent=message.receiver_agent,
    )


def clear_message_log() -> None:
    _MESSAGE_LOG.clear()
