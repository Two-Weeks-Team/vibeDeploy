from __future__ import annotations

import os

import httpx

KB_API_BASE = "https://api.digitalocean.com/v2/gen-ai/knowledge_bases"


async def query_do_knowledge_base(query: str, top_k: int = 5) -> dict:
    kb_id = os.environ.get("DIGITALOCEAN_KB_ID", "")
    api_token = os.environ.get("DIGITALOCEAN_API_TOKEN", "")

    if not kb_id or not api_token:
        return {"matches": [], "error": "DIGITALOCEAN_KB_ID or DIGITALOCEAN_API_TOKEN not set"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{KB_API_BASE}/{kb_id}/query",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json={"query": query, "top_k": top_k},
        )
        response.raise_for_status()
        data = response.json()

    matches = []
    for result in data.get("results", []):
        matches.append(
            {
                "content": result.get("content", ""),
                "source": result.get("metadata", {}).get("source", ""),
                "score": result.get("score", 0.0),
            }
        )

    return {"matches": matches}


async def query_framework_patterns(query: str, top_k: int = 3) -> dict:
    fw_kb_id = os.environ.get("FRAMEWORK_KB_ID", "")
    api_token = os.environ.get("DIGITALOCEAN_API_TOKEN", "")

    if not fw_kb_id or not api_token:
        return {"matches": [], "error": "FRAMEWORK_KB_ID or DIGITALOCEAN_API_TOKEN not set"}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{KB_API_BASE}/{fw_kb_id}/query",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            json={"query": query, "top_k": top_k},
        )
        response.raise_for_status()
        data = response.json()

    matches = []
    for result in data.get("results", []):
        matches.append(
            {
                "content": result.get("content", ""),
                "source": result.get("metadata", {}).get("source", ""),
                "score": result.get("score", 0.0),
            }
        )

    return {"matches": matches}
