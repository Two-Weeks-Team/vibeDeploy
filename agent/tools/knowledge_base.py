import logging
import os
from typing import Optional

import httpx
from gradient_adk.tracing import trace_tool

logger = logging.getLogger(__name__)
GRADIENT_KB_URL = "https://kbaas.do-ai.run/v1"
KB_SNIPPET_MAX_CHARS = 500
KB_SNIPPET_MAX_COUNT = 3


@trace_tool("query_do_knowledge_base")
async def query_do_knowledge_base(
    query: str,
    kb_id: Optional[str] = None,
    top_k: int = 5,
) -> dict:
    api_key = os.getenv("DIGITALOCEAN_API_TOKEN")
    kb_id = kb_id or os.getenv("DO_KNOWLEDGE_BASE_ID")

    if not api_key:
        return {"matches": [], "error": "DIGITALOCEAN_API_TOKEN not set"}
    if not kb_id:
        return {"matches": [], "error": "DO_KNOWLEDGE_BASE_ID not set"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{GRADIENT_KB_URL}/{kb_id}/retrieve",
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
                matches.append(
                    {
                        "content": result.get("content", ""),
                        "score": result.get("score", 0),
                        "metadata": result.get("metadata", {}),
                    }
                )

            return {"matches": matches}

    except httpx.HTTPStatusError as e:
        return {"matches": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.TimeoutException:
        return {"matches": [], "error": "KB query timed out"}
    except Exception as e:
        return {"matches": [], "error": str(e)[:200]}


@trace_tool("query_framework_patterns")
async def query_framework_patterns(framework: str, pattern_type: str) -> dict:
    return await query_do_knowledge_base(
        f"{framework} {pattern_type} best practices and patterns",
        kb_id=os.getenv("DO_FRAMEWORK_KB_ID"),
    )


@trace_tool("query_do_docs")
async def query_do_docs(topic: str) -> dict:
    return await query_do_knowledge_base(
        f"DigitalOcean {topic} documentation and configuration",
        kb_id=os.getenv("DO_DOCS_KB_ID"),
    )


@trace_tool("query_kb_for_code_context")
async def query_kb_for_code_context(idea_name: str, tech_stack: str = "Next.js FastAPI") -> str:
    results = await query_do_knowledge_base(
        f"Code generation patterns for a '{idea_name}' app using {tech_stack}",
        kb_id=os.getenv("DO_FRAMEWORK_KB_ID"),
        top_k=KB_SNIPPET_MAX_COUNT,
    )
    if results.get("error") or not results.get("matches"):
        return ""

    snippets = [m["content"][:KB_SNIPPET_MAX_CHARS] for m in results["matches"][:KB_SNIPPET_MAX_COUNT]]
    return "\n---\n".join(snippets)


@trace_tool("query_kb_for_idea_enrichment")
async def query_kb_for_idea_enrichment(idea_description: str) -> str:
    results = await query_do_knowledge_base(
        f"app idea patterns similar to: {idea_description}",
        top_k=KB_SNIPPET_MAX_COUNT,
    )
    if results.get("error") or not results.get("matches"):
        return ""

    snippets = [m["content"][:KB_SNIPPET_MAX_CHARS] for m in results["matches"][:KB_SNIPPET_MAX_COUNT]]
    return "\n---\n".join(snippets)
