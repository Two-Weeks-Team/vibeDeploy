import json

from langchain_core.tools import tool


@tool
async def search_competitors(query: str) -> str:
    """Search for existing apps and competitors in the market. Use this to find competitive landscape data."""
    from .web_search import web_search

    result = await web_search(
        f"existing apps and competitors: {query}", num_results=5, search_type="competitor_analysis"
    )
    return json.dumps(result, ensure_ascii=False)


@tool
async def search_tech_stack(query: str) -> str:
    """Search for recommended tech stacks and frameworks for building a specific type of application."""
    from .web_search import web_search

    result = await web_search(f"recommended tech stack for: {query}", num_results=5, search_type="tech_recommendation")
    return json.dumps(result, ensure_ascii=False)


@tool
async def query_platform_docs(query: str) -> str:
    """Query DigitalOcean platform documentation for deployment and infrastructure guidance."""
    from .knowledge_base import query_do_docs

    result = await query_do_docs(query)
    return json.dumps(result, ensure_ascii=False)


@tool
async def query_framework_best_practices(framework: str, pattern_type: str) -> str:
    """Query knowledge base for framework-specific patterns and best practices."""
    from .knowledge_base import query_framework_patterns

    result = await query_framework_patterns(framework, pattern_type)
    return json.dumps(result, ensure_ascii=False)


SCOUT_TOOLS = [search_competitors, search_tech_stack]
ARCHITECT_TOOLS = [search_tech_stack, query_platform_docs, query_framework_best_practices]
