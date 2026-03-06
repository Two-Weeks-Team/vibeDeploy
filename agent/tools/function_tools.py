import json

from langchain_core.tools import tool


@tool
async def search_competitors(query: str) -> str:
    """Search Competitors: Find existing apps and competitors in the target market.

    Parameters:
      - query (str): Description of the app idea or market segment to research.

    Returns: JSON string containing up to 5 competitor analysis results with names, \
descriptions, strengths, and weaknesses.

    Constraints:
      - Maximum 5 results per search.
      - Results focus on direct and adjacent competitors only.
    """
    from .web_search import web_search

    result = await web_search(
        f"existing apps and competitors: {query}", num_results=5, search_type="competitor_analysis"
    )
    return json.dumps(result, ensure_ascii=False)


@tool
async def search_tech_stack(query: str) -> str:
    """Search Tech Stack: Find recommended frameworks and technologies for a specific app type.

    Parameters:
      - query (str): Description of the application type or technical requirements.

    Returns: JSON string containing up to 5 tech stack recommendations with \
framework names, pros/cons, and community adoption data.

    Constraints:
      - Maximum 5 results per search.
      - Recommendations prioritize DigitalOcean-compatible stacks.
    """
    from .web_search import web_search

    result = await web_search(f"recommended tech stack for: {query}", num_results=5, search_type="tech_recommendation")
    return json.dumps(result, ensure_ascii=False)


@tool
async def query_platform_docs(query: str) -> str:
    """Query Platform Docs: Search DigitalOcean documentation for deployment and infrastructure guidance.

    Parameters:
      - query (str): Specific question about DO services, deployment, or infrastructure.

    Returns: JSON string containing relevant documentation excerpts from the \
DigitalOcean Knowledge Base with source references.

    Constraints:
      - Queries are scoped to DigitalOcean platform documentation only.
      - Results are retrieved via RAG from the vibedeploy-docs Knowledge Base.
    """
    from .knowledge_base import query_do_docs

    result = await query_do_docs(query)
    return json.dumps(result, ensure_ascii=False)


@tool
async def query_framework_best_practices(framework: str, pattern_type: str) -> str:
    """Query Framework Best Practices: Retrieve framework-specific patterns and conventions.

    Parameters:
      - framework (str): Framework name (e.g., "Next.js", "FastAPI", "React").
      - pattern_type (str): Type of pattern to search (e.g., "auth", "routing", "state").

    Returns: JSON string containing best practice patterns, code conventions, \
and recommended approaches for the specified framework and pattern type.

    Constraints:
      - Results are retrieved via RAG from the vibedeploy-docs Knowledge Base.
      - Patterns prioritize production-ready, DO-deployable implementations.
    """
    from .knowledge_base import query_framework_patterns

    result = await query_framework_patterns(framework, pattern_type)
    return json.dumps(result, ensure_ascii=False)


SCOUT_TOOLS = [search_competitors, search_tech_stack]
ARCHITECT_TOOLS = [search_tech_stack, query_platform_docs, query_framework_best_practices]
