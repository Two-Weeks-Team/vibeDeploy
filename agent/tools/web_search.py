import json
import os

import httpx

from ..llm import DO_INFERENCE_BASE_URL, MODEL_CONFIG


async def web_search(
    query: str,
    num_results: int = 5,
    search_type: str = "general",
) -> dict:
    api_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY")
    if not api_key:
        return {"results": [], "error": "DIGITALOCEAN_INFERENCE_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{DO_INFERENCE_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL_CONFIG["web_search"],
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
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()
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
