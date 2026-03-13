"""Gradient ADK entrypoint for the full vibeDeploy orchestration pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from gradient_adk import RequestContext, entrypoint

_AGENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AGENT_DIR.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.pipeline_runtime import stream_action_session  # noqa: E402


@entrypoint
async def main(input: dict, context: RequestContext):
    _ = context
    async for chunk in stream_action_session(input):
        yield chunk
