import json

from gradient_adk import RequestContext, entrypoint


@entrypoint
async def main(input: dict, context: RequestContext):
    """vibeDeploy agent entrypoint — SSE streaming"""
    prompt = input.get("prompt", "")
    config = input.get("config", {})
    thread_id = config.get("configurable", {}).get("thread_id", "default")

    _ = (prompt, thread_id, context)

    async def stream():
        yield f"event: council.phase.start\ndata: {json.dumps({'phase': 'starting', 'message': 'vibeDeploy starting...'})}\n\n"
        # TODO: Wire to graph execution
        yield f"event: council.phase.start\ndata: {json.dumps({'phase': 'complete', 'message': 'Pipeline complete'})}\n\n"

    return stream()
