from threading import Lock

from agent.gradient.a2a_schemas import A2AMessage, A2AResponse

_MESSAGE_LOG: list[A2AMessage] = []
_LOG_LOCK = Lock()

_KNOWN_AGENTS = {"scout", "catalyst", "architect", "guardian", "advocate", "strategist"}

_REQUIRED_HANDOFF_FIELDS = {"idea_name", "score"}


def validate_handoff(payload: dict) -> set[str]:
    return _REQUIRED_HANDOFF_FIELDS - set(payload.keys())


def get_message_log() -> list[A2AMessage]:
    with _LOG_LOCK:
        return list(_MESSAGE_LOG)


def send_message(message: A2AMessage) -> A2AResponse:
    if message.receiver_agent not in _KNOWN_AGENTS:
        return A2AResponse(
            status="error",
            details=f"Unknown receiver agent: {message.receiver_agent}",
            receiver_agent=message.receiver_agent,
        )

    if message.message_type == "idea_handoff":
        if missing := validate_handoff(message.payload):
            return A2AResponse(
                status="rejected",
                details=f"idea_handoff payload missing required fields: {sorted(missing)}",
                receiver_agent=message.receiver_agent,
            )

    with _LOG_LOCK:
        _MESSAGE_LOG.append(message)
    return A2AResponse(
        status="accepted",
        details=f"Message of type '{message.message_type}' delivered to {message.receiver_agent}",
        receiver_agent=message.receiver_agent,
    )


def clear_message_log() -> None:
    with _LOG_LOCK:
        _MESSAGE_LOG.clear()
