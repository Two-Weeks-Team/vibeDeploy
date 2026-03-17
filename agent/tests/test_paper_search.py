import pytest

from agent.zero_prompt.events import (
    ZP_PAPER_FOUND,
    ZP_PAPER_SEARCH,
    paper_found_event,
    paper_search_event,
)
from agent.zero_prompt.paper_search import (
    _parse_arxiv_xml,
    _reconstruct_abstract,
    search_papers,
)
from agent.zero_prompt.schemas import PaperMetadata


def test_reconstruct_abstract():
    inverted = {"hello": [0], "world": [1], "foo": [2]}
    assert _reconstruct_abstract(inverted) == "hello world foo"


def test_reconstruct_abstract_empty():
    assert _reconstruct_abstract({}) == ""


def test_parse_arxiv_xml_extracts_entries():
    xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Deep Learning for App Development</title>
    <summary>A survey of techniques.</summary>
    <author><name>Jane Doe</name></author>
    <author><name>John Smith</name></author>
    <published>2024-03-15T00:00:00Z</published>
    <id>http://arxiv.org/abs/2403.12345</id>
  </entry>
</feed>"""
    results = _parse_arxiv_xml(xml)
    assert len(results) == 1
    assert results[0].title == "Deep Learning for App Development"
    assert results[0].year == 2024
    assert results[0].source == "arxiv"
    assert len(results[0].authors) == 2
    assert results[0].url == "http://arxiv.org/abs/2403.12345"


def test_parse_arxiv_xml_handles_invalid_xml():
    results = _parse_arxiv_xml("not valid xml <<<<")
    assert results == []


def test_paper_metadata_model():
    paper = PaperMetadata(title="Test Paper", source="openalex")
    assert paper.citations == 0
    assert paper.year == 0
    assert paper.authors == []


def test_paper_search_event_structure():
    event = paper_search_event("machine learning apps", ["openalex", "arxiv"])
    assert event["type"] == ZP_PAPER_SEARCH
    assert event["query"] == "machine learning apps"
    assert event["sources"] == ["openalex", "arxiv"]


def test_paper_found_event_structure():
    event = paper_found_event(total=5, source="openalex")
    assert event["type"] == ZP_PAPER_FOUND
    assert event["total"] == 5
    assert event["source"] == "openalex"


@pytest.mark.asyncio
async def test_search_papers_uses_cache(monkeypatch):
    from agent.zero_prompt import paper_search as ps_module

    call_count = 0

    async def fake_openalex(query, max_results=5):
        nonlocal call_count
        call_count += 1
        return [
            PaperMetadata(
                title="Cached Paper",
                abstract="Abstract",
                citations=100,
                year=2024,
                url="https://doi.org/10.1234/test",
                source="openalex",
            )
        ]

    async def fake_arxiv(query, max_results=5):
        return []

    monkeypatch.setattr(ps_module, "_openalex_search", fake_openalex)
    monkeypatch.setattr(ps_module, "_arxiv_search", fake_arxiv)
    ps_module._CACHE.clear()

    result1 = await search_papers("test query")
    result2 = await search_papers("test query")

    assert len(result1) == len(result2)
    assert call_count == 1


@pytest.mark.asyncio
async def test_search_papers_falls_back_to_arxiv_on_openalex_failure(monkeypatch):
    from agent.zero_prompt import paper_search as ps_module

    async def failing_openalex(query, max_results=5):
        raise ConnectionError("OpenAlex is down")

    async def fake_arxiv(query, max_results=5):
        return [
            PaperMetadata(
                title="arXiv Paper",
                abstract="Fallback result",
                citations=0,
                year=2025,
                url="http://arxiv.org/abs/2503.99999",
                source="arxiv",
            )
        ]

    monkeypatch.setattr(ps_module, "_openalex_search", failing_openalex)
    monkeypatch.setattr(ps_module, "_arxiv_search", fake_arxiv)
    ps_module._CACHE.clear()

    result = await search_papers("fallback test", max_results=5)
    assert len(result) == 1
    assert result[0].source == "arxiv"


@pytest.mark.asyncio
async def test_search_papers_deduplicates_by_title(monkeypatch):
    from agent.zero_prompt import paper_search as ps_module

    async def fake_openalex(query, max_results=5):
        return [
            PaperMetadata(title="Same Paper", citations=50, year=2024, source="openalex"),
        ]

    async def fake_arxiv(query, max_results=5):
        return [
            PaperMetadata(title="Same Paper", citations=0, year=2024, source="arxiv"),
            PaperMetadata(title="Different Paper", citations=10, year=2023, source="arxiv"),
        ]

    monkeypatch.setattr(ps_module, "_openalex_search", fake_openalex)
    monkeypatch.setattr(ps_module, "_arxiv_search", fake_arxiv)
    ps_module._CACHE.clear()

    result = await search_papers("dedup test", max_results=5)
    titles = [p.title for p in result]
    assert titles.count("Same Paper") == 1
    assert "Different Paper" in titles
