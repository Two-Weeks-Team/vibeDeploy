import json
import os

import httpx
from gradient_adk.tracing import trace_tool

from ..llm import DO_INFERENCE_BASE_URL, MODEL_CONFIG
from ..model_capabilities import model_endpoint_type


def _responses_output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"]

    output = payload.get("output", [])
    if isinstance(output, list):
        for item in output:
            content = item.get("content", []) if isinstance(item, dict) else []
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                text = block.get("text") or block.get("output_text")
                if isinstance(text, str) and text.strip():
                    return text
    return ""


@trace_tool("web_search")
async def web_search(
    query: str,
    num_results: int = 5,
    search_type: str = "general",
) -> dict:
    api_key = os.getenv("GRADIENT_MODEL_ACCESS_KEY") or os.getenv("DIGITALOCEAN_INFERENCE_KEY")
    if not api_key:
        return {"results": [], "error": "GRADIENT_MODEL_ACCESS_KEY not set"}

    try:
        model = MODEL_CONFIG["web_search"]
        endpoint = model_endpoint_type(model)
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            if endpoint == "responses":
                response = await client.post(
                    f"{DO_INFERENCE_BASE_URL}/responses",
                    headers=headers,
                    json={
                        "model": model,
                        "input": (
                            "You are a web research assistant. Search for the given query and return structured "
                            "results as JSON with a top-level 'results' array. "
                            f"Search query: {query}\nType: {search_type}\nReturn top {num_results} results."
                        ),
                    },
                )
            else:
                response = await client.post(
                    f"{DO_INFERENCE_BASE_URL}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a web research assistant. Search for the given query "
                                    "and return structured results as JSON. Include: title, url, snippet "
                                    "for each result. Return a JSON object with a 'results' array."
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Search query: {query}\nType: {search_type}\nReturn top {num_results} results as JSON."
                                ),
                            },
                        ],
                        "temperature": 0.3,
                        "max_completion_tokens": 512,
                    },
                )
            response.raise_for_status()
            data = response.json()
            if endpoint == "responses":
                content = _responses_output_text(data)
            else:
                content = data["choices"][0]["message"]["content"]

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"results": [], "raw_response": content}

    except httpx.HTTPStatusError as e:
        return {"results": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.TimeoutException:
        return {"results": [], "error": "Search timed out"}
    except Exception as e:
        return {"results": [], "error": str(e)[:200]}


async def search_competitors(idea_summary: str) -> dict:
    return await web_search(
        f"existing apps and competitors similar to: {idea_summary}",
        num_results=8,
        search_type="competitor_analysis",
    )


async def search_tech_stack(idea_summary: str) -> dict:
    return await web_search(
        f"recommended tech stack and frameworks for building: {idea_summary}",
        num_results=5,
        search_type="tech_recommendation",
    )
