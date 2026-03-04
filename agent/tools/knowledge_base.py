import os
from typing import Optional

import httpx

GRADIENT_KB_URL = "https://api.digitalocean.com/v2/gen-ai/knowledge-bases"


async def query_do_knowledge_base(
    query: str,
    kb_id: Optional[str] = None,
    top_k: int = 5,
) -> dict:
    api_key = os.getenv("DIGITALOCEAN_INFERENCE_KEY")
    kb_id = kb_id or os.getenv("DO_KNOWLEDGE_BASE_ID")

    if not api_key:
        return {"matches": [], "error": "DIGITALOCEAN_INFERENCE_KEY not set"}
    if not kb_id:
        return {"matches": [], "error": "DO_KNOWLEDGE_BASE_ID not set"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{GRADIENT_KB_URL}/{kb_id}/query",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "top_k": top_k,
                },
            )
            response.raise_for_status()
            data = response.json()

            matches = []
            for result in data.get("results", []):
                matches.append({
                    "content": result.get("content", ""),
                    "score": result.get("score", 0),
                    "metadata": result.get("metadata", {}),
                })

            return {"matches": matches}

    except httpx.HTTPStatusError as e:
        return {"matches": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.TimeoutException:
        return {"matches": [], "error": "KB query timed out"}
    except Exception as e:
        return {"matches": [], "error": str(e)[:200]}


async def query_framework_patterns(framework: str, pattern_type: str) -> dict:
    return await query_do_knowledge_base(
        f"{framework} {pattern_type} best practices and patterns",
        kb_id=os.getenv("DO_FRAMEWORK_KB_ID"),
    )


async def query_do_docs(topic: str) -> dict:
    return await query_do_knowledge_base(
        f"DigitalOcean {topic} documentation and configuration",
        kb_id=os.getenv("DO_DOCS_KB_ID"),
    )
