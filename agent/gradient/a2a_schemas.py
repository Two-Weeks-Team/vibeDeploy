from typing import Literal

from pydantic import BaseModel


class A2AMessage(BaseModel):
    sender_agent: str
    receiver_agent: str
    payload: dict
    message_type: Literal["idea_handoff", "build_request", "status_update"]
    timestamp: str


class A2AResponse(BaseModel):
    status: Literal["accepted", "rejected", "error"]
    details: str
    receiver_agent: str
