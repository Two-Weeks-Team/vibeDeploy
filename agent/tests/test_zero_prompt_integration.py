"""Integration tests for zero_prompt modules targeting 90%+ coverage.

Covers:
  - zero_prompt/unified_search.py  (lines 24-36, 48-67, 82, 107-120)
  - zero_prompt/paper_search.py    (lines 40-41, 50, 54-116, 133-169, 186, 202-203, 241-242)
  - zero_prompt/discovery.py       (lines 55-72, 76-86, 90-103, 176, 188-189, 205)

All external HTTP calls are mocked — no real APIs are called.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client(get_side_effect=None, get_return=None, post_return=None):
    """Return a mock httpx.AsyncClient that works as an async context manager."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    if get_side_effect is not None:
        mock_client.get = AsyncMock(side_effect=get_side_effect)
    elif get_return is not None:
        mock_client.get = AsyncMock(return_value=get_return)
    if post_return is not None:
        mock_client.post = AsyncMock(return_value=post_return)
    return mock_client


def _make_resp(json_data=None, text_data=None, raise_for_status=None):
    """Return a mock httpx response."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock() if raise_for_status is None else raise_for_status
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    if text_data is not None:
        resp.text = text_data
    return resp


# ===========================================================================
# unified_search.py tests
# ===========================================================================


class TestSearchBrave:
    @pytest.mark.asyncio
    async def test_brave_no_api_key_returns_empty(self, monkeypatch):
        """_search_brave returns [] when BRAVE_API_KEY is unset."""
        monkeypatch.delenv("BRAVE_API_KEY", raising=False)
        monkeypatch.setenv("BRAVE_API_KEY", "")

        from agent.zero_prompt.unified_search import _search_brave

        result = await _search_brave("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_brave_success(self, monkeypatch):
        """_search_brave returns SearchResult list on a successful API response."""
        monkeypatch.setenv("BRAVE_API_KEY", "fake-key")

        resp = _make_resp(
            json_data={
                "web": {
                    "results": [
                        {"title": "Result A", "url": "https://example.com/a", "description": "desc a"},
                        {"title": "Result B", "url": "https://example.com/b", "description": "desc b"},
                    ]
                }
            }
        )
        mock_client = _make_mock_client(get_return=resp)

        with patch("agent.zero_prompt.unified_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.unified_search import _search_brave

            results = await _search_brave("test query", limit=5)

        assert len(results) == 2
        assert results[0].title == "Result A"
        assert results[0].source == "brave"
        assert results[0].snippet == "desc a"

    @pytest.mark.asyncio
    async def test_brave_empty_results(self, monkeypatch):
        """_search_brave handles empty web results gracefully."""
        monkeypatch.setenv("BRAVE_API_KEY", "fake-key")

        resp = _make_resp(json_data={"web": {"results": []}})
        mock_client = _make_mock_client(get_return=resp)

        with patch("agent.zero_prompt.unified_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.unified_search import _search_brave

            results = await _search_brave("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_brave_missing_web_key(self, monkeypatch):
        """_search_brave handles response without 'web' key."""
        monkeypatch.setenv("BRAVE_API_KEY", "fake-key")

        resp = _make_resp(json_data={})
        mock_client = _make_mock_client(get_return=resp)

        with patch("agent.zero_prompt.unified_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.unified_search import _search_brave

            results = await _search_brave("test query")

        assert results == []


class TestSearchExa:
    @pytest.mark.asyncio
    async def test_exa_with_api_key(self, monkeypatch):
        """_search_exa uses Bearer token directly when EXA_API_KEY is set."""
        monkeypatch.setenv("EXA_API_KEY", "fake-exa-key")

        resp = _make_resp(
            json_data={
                "results": [
                    {"title": "Exa Result 1", "url": "https://exa.ai/result1", "text": "snippet 1"},
                ]
            }
        )
        mock_client = _make_mock_client(post_return=resp)

        with patch("agent.zero_prompt.unified_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.unified_search import _search_exa

            results = await _search_exa("test query", limit=3)

        assert len(results) == 1
        assert results[0].title == "Exa Result 1"
        assert results[0].source == "exa"
        assert results[0].snippet == "snippet 1"

    @pytest.mark.asyncio
    async def test_exa_without_api_key_fetches_token(self, monkeypatch):
        """_search_exa fetches a temp token from EXA_TOKEN_URL when no key is set."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.setenv("EXA_API_KEY", "")

        token_resp = _make_resp(json_data={"token": "temp-token-xyz"})
        search_resp = _make_resp(
            json_data={
                "results": [
                    {"title": "Tokenized Result", "url": "https://exa.ai/r", "text": "text"},
                ]
            }
        )

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        # post is called twice: first for token, second for search
        mock_client.post = AsyncMock(side_effect=[token_resp, search_resp])

        with patch("agent.zero_prompt.unified_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.unified_search import _search_exa

            results = await _search_exa("test query", limit=2)

        assert len(results) == 1
        assert results[0].title == "Tokenized Result"

    @pytest.mark.asyncio
    async def test_exa_without_api_key_no_token_returns_empty(self, monkeypatch):
        """_search_exa returns [] when token endpoint returns no token."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.setenv("EXA_API_KEY", "")

        token_resp = _make_resp(json_data={})  # no 'token' key

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=token_resp)

        with patch("agent.zero_prompt.unified_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.unified_search import _search_exa

            results = await _search_exa("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_exa_empty_results(self, monkeypatch):
        """_search_exa handles empty results list."""
        monkeypatch.setenv("EXA_API_KEY", "fake-exa-key")

        resp = _make_resp(json_data={"results": []})
        mock_client = _make_mock_client(post_return=resp)

        with patch("agent.zero_prompt.unified_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.unified_search import _search_exa

            results = await _search_exa("test query")

        assert results == []


class TestMergeAndScore:
    def test_merge_skips_empty_url(self):
        """_merge_and_score skips results with empty URL (line 82)."""
        from agent.zero_prompt.schemas import SearchResult
        from agent.zero_prompt.unified_search import _merge_and_score

        results = [
            SearchResult(title="No URL", url="", source="brave"),
            SearchResult(title="Has URL", url="https://example.com/page", source="exa"),
        ]
        merged = _merge_and_score(results)
        assert len(merged) == 1
        assert merged[0].title == "Has URL"

    def test_merge_deduplicates_same_url(self):
        """_merge_and_score deduplicates results with the same normalized URL."""
        from agent.zero_prompt.schemas import SearchResult
        from agent.zero_prompt.unified_search import _merge_and_score

        results = [
            SearchResult(title="Page", url="https://example.com/page", snippet="brave snippet", source="brave"),
            SearchResult(title="Page", url="http://www.example.com/page/", source="exa"),
        ]
        merged = _merge_and_score(results)
        assert len(merged) == 1
        assert merged[0].confidence == "high"
        assert "brave" in merged[0].source
        assert "exa" in merged[0].source

    def test_merge_high_confidence_sorted_first(self):
        """_merge_and_score puts high-confidence (multi-source) results first."""
        from agent.zero_prompt.schemas import SearchResult
        from agent.zero_prompt.unified_search import _merge_and_score

        results = [
            SearchResult(title="Only Brave", url="https://a.com", source="brave"),
            SearchResult(title="Both B", url="https://b.com", snippet="s", source="brave"),
            SearchResult(title="Both E", url="https://b.com", snippet="se", source="exa"),
        ]
        merged = _merge_and_score(results)
        assert merged[0].confidence == "high"

    def test_merge_snippet_preferred(self):
        """_merge_and_score picks the result with a snippet as 'best'."""
        from agent.zero_prompt.schemas import SearchResult
        from agent.zero_prompt.unified_search import _merge_and_score

        results = [
            SearchResult(title="No Snip", url="https://c.com", snippet=None, source="brave"),
            SearchResult(title="Has Snip", url="https://c.com", snippet="good snippet", source="exa"),
        ]
        merged = _merge_and_score(results)
        assert merged[0].snippet == "good snippet"


class TestUnifiedSearch:
    @pytest.mark.asyncio
    async def test_unified_search_both_succeed(self, monkeypatch):
        """unified_search merges results from both brave and exa."""
        monkeypatch.setenv("BRAVE_API_KEY", "fake")
        monkeypatch.setenv("EXA_API_KEY", "fake")

        from agent.zero_prompt import unified_search as us_module
        from agent.zero_prompt.schemas import SearchResult

        async def fake_brave(query, limit=5):
            return [SearchResult(title="B1", url="https://brave.com/1", source="brave")]

        async def fake_exa(query, limit=5):
            return [SearchResult(title="E1", url="https://exa.com/1", source="exa")]

        monkeypatch.setattr(us_module, "_search_brave", fake_brave)
        monkeypatch.setattr(us_module, "_search_exa", fake_exa)

        results = await us_module.unified_search("test")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_unified_search_brave_fails(self, monkeypatch):
        """unified_search continues when brave raises an exception."""
        from agent.zero_prompt import unified_search as us_module
        from agent.zero_prompt.schemas import SearchResult

        async def failing_brave(query, limit=5):
            raise httpx.ConnectError("brave down")

        async def fake_exa(query, limit=5):
            return [SearchResult(title="E1", url="https://exa.com/1", source="exa")]

        monkeypatch.setattr(us_module, "_search_brave", failing_brave)
        monkeypatch.setattr(us_module, "_search_exa", fake_exa)

        results = await us_module.unified_search("test")
        assert len(results) == 1
        assert results[0].source == "exa"

    @pytest.mark.asyncio
    async def test_unified_search_exa_fails(self, monkeypatch):
        """unified_search continues when exa raises an exception."""
        from agent.zero_prompt import unified_search as us_module
        from agent.zero_prompt.schemas import SearchResult

        async def fake_brave(query, limit=5):
            return [SearchResult(title="B1", url="https://brave.com/1", source="brave")]

        async def failing_exa(query, limit=5):
            raise httpx.TimeoutException("exa timeout")

        monkeypatch.setattr(us_module, "_search_brave", fake_brave)
        monkeypatch.setattr(us_module, "_search_exa", failing_exa)

        results = await us_module.unified_search("test")
        assert len(results) == 1
        assert results[0].source == "brave"

    @pytest.mark.asyncio
    async def test_unified_search_both_fail(self, monkeypatch):
        """unified_search returns [] when both sources fail."""
        from agent.zero_prompt import unified_search as us_module

        async def failing(query, limit=5):
            raise RuntimeError("down")

        monkeypatch.setattr(us_module, "_search_brave", failing)
        monkeypatch.setattr(us_module, "_search_exa", failing)

        results = await us_module.unified_search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_unified_search_deduplication(self, monkeypatch):
        """unified_search deduplicates when both sources return the same URL."""
        from agent.zero_prompt import unified_search as us_module
        from agent.zero_prompt.schemas import SearchResult

        shared_url = "https://shared.com/page"

        async def fake_brave(query, limit=5):
            return [SearchResult(title="Shared", url=shared_url, snippet="brave snip", source="brave")]

        async def fake_exa(query, limit=5):
            return [SearchResult(title="Shared", url=shared_url, snippet="exa snip", source="exa")]

        monkeypatch.setattr(us_module, "_search_brave", fake_brave)
        monkeypatch.setattr(us_module, "_search_exa", fake_exa)

        results = await us_module.unified_search("test")
        assert len(results) == 1
        assert results[0].confidence == "high"


# ===========================================================================
# paper_search.py tests
# ===========================================================================


class TestOpenAlexSearch:
    @pytest.mark.asyncio
    async def test_openalex_success(self):
        """_openalex_search returns PaperMetadata list on success."""
        resp = _make_resp(
            json_data={
                "results": [
                    {
                        "title": "ML for App Dev",
                        "cited_by_count": 150,
                        "publication_year": 2023,
                        "doi": "https://doi.org/10.1234/test",
                        "abstract_inverted_index": {"machine": [0], "learning": [1], "paper": [2]},
                        "authorships": [
                            {"author": {"display_name": "Alice"}},
                            {"author": {"display_name": "Bob"}},
                        ],
                    }
                ]
            }
        )
        mock_client = _make_mock_client(get_return=resp)

        with patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.paper_search import _openalex_search

            results = await _openalex_search("machine learning", max_results=3)

        assert len(results) == 1
        paper = results[0]
        assert paper.source == "openalex"
        assert paper.title == "ML for App Dev"
        assert paper.citations == 150
        assert paper.year == 2023
        assert paper.doi == "10.1234/test"
        assert "machine" in paper.abstract
        assert "Alice" in paper.authors

    @pytest.mark.asyncio
    async def test_openalex_skips_empty_title(self):
        """_openalex_search skips works without a title."""
        resp = _make_resp(
            json_data={
                "results": [
                    {"title": "", "cited_by_count": 10, "publication_year": 2022},
                    {"title": "Valid Paper", "cited_by_count": 5, "publication_year": 2021},
                ]
            }
        )
        mock_client = _make_mock_client(get_return=resp)

        with patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.paper_search import _openalex_search

            results = await _openalex_search("test")

        assert len(results) == 1
        assert results[0].title == "Valid Paper"

    @pytest.mark.asyncio
    async def test_openalex_no_abstract_no_doi(self):
        """_openalex_search handles missing abstract and DOI."""
        resp = _make_resp(
            json_data={
                "results": [
                    {
                        "title": "Paper No Abstract",
                        "cited_by_count": 0,
                        "publication_year": 2020,
                        "doi": None,
                        "abstract_inverted_index": None,
                        "authorships": [],
                        "id": "https://openalex.org/W123",
                    }
                ]
            }
        )
        mock_client = _make_mock_client(get_return=resp)

        with patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.paper_search import _openalex_search

            results = await _openalex_search("test")

        assert len(results) == 1
        assert results[0].abstract == ""
        assert results[0].doi == ""
        assert results[0].url == "https://openalex.org/W123"

    @pytest.mark.asyncio
    async def test_openalex_retry_then_success(self):
        """_openalex_search retries on transient HTTP errors and succeeds."""
        good_resp = _make_resp(
            json_data={
                "results": [
                    {"title": "Retry Paper", "cited_by_count": 10, "publication_year": 2024},
                ]
            }
        )
        error = httpx.TimeoutException("timeout")

        # First call raises, second returns good response
        mock_client = _make_mock_client(get_side_effect=[error, good_resp])

        with (
            patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client),
            patch("agent.zero_prompt.paper_search.asyncio.sleep", new=AsyncMock()),
        ):
            from agent.zero_prompt.paper_search import _openalex_search

            results = await _openalex_search("test")

        assert len(results) == 1
        assert results[0].title == "Retry Paper"

    @pytest.mark.asyncio
    async def test_openalex_all_retries_fail(self):
        """_openalex_search raises the last exception when all retries are exhausted."""
        error = httpx.ConnectError("connection refused")
        # Fail on every attempt (3 total: attempt 0, 1, 2)
        mock_client = _make_mock_client(get_side_effect=[error, error, error])

        with (
            patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client),
            patch("agent.zero_prompt.paper_search.asyncio.sleep", new=AsyncMock()),
        ):
            from agent.zero_prompt.paper_search import _openalex_search

            with pytest.raises(httpx.ConnectError):
                await _openalex_search("test")


class TestArxivSearch:
    @pytest.mark.asyncio
    async def test_arxiv_success(self):
        """_arxiv_search parses a valid Atom XML response."""
        xml_text = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Neural Networks Survey</title>
    <summary>A comprehensive survey of neural networks.</summary>
    <author><name>Carol</name></author>
    <published>2024-01-15T00:00:00Z</published>
    <id>http://arxiv.org/abs/2401.12345</id>
  </entry>
</feed>"""
        resp = _make_resp(json_data={})
        resp.text = xml_text
        mock_client = _make_mock_client(get_return=resp)

        with (
            patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client),
            patch("agent.zero_prompt.paper_search._ARXIV_LAST_REQUEST", 0.0),
        ):
            from agent.zero_prompt import paper_search as ps_module

            ps_module._ARXIV_LAST_REQUEST = 0.0
            results = await ps_module._arxiv_search("neural networks")

        assert len(results) == 1
        assert results[0].title == "Neural Networks Survey"
        assert results[0].year == 2024
        assert results[0].source == "arxiv"

    @pytest.mark.asyncio
    async def test_arxiv_throttle_waits(self):
        """_arxiv_search waits if the last request was too recent."""
        xml_text = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>"""
        resp = _make_resp(json_data={})
        resp.text = xml_text
        mock_client = _make_mock_client(get_return=resp)

        sleep_calls = []

        async def fake_sleep(n):
            sleep_calls.append(n)

        with (
            patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client),
            patch("agent.zero_prompt.paper_search.asyncio.sleep", side_effect=fake_sleep),
        ):
            from agent.zero_prompt import paper_search as ps_module

            # Simulate last request just happened
            ps_module._ARXIV_LAST_REQUEST = time.time()
            await ps_module._arxiv_search("test query")

        # Should have slept at least once for throttle
        assert len(sleep_calls) >= 1
        assert sleep_calls[0] > 0

    @pytest.mark.asyncio
    async def test_arxiv_retry_then_success(self):
        """_arxiv_search retries on transient error."""
        xml_text = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Retry Paper</title>
    <summary>Abstract.</summary>
    <published>2023-06-01T00:00:00Z</published>
    <id>http://arxiv.org/abs/2306.00001</id>
  </entry>
</feed>"""
        good_resp = _make_resp(json_data={})
        good_resp.text = xml_text
        error = httpx.TimeoutException("timeout")

        mock_client = _make_mock_client(get_side_effect=[error, good_resp])

        with (
            patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client),
            patch("agent.zero_prompt.paper_search.asyncio.sleep", new=AsyncMock()),
        ):
            from agent.zero_prompt import paper_search as ps_module

            ps_module._ARXIV_LAST_REQUEST = 0.0
            results = await ps_module._arxiv_search("test")

        assert len(results) == 1
        assert results[0].title == "Retry Paper"

    @pytest.mark.asyncio
    async def test_arxiv_all_retries_fail(self):
        """_arxiv_search raises when all retries are exhausted."""
        error = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        mock_client = _make_mock_client(get_side_effect=[error, error])

        with (
            patch("agent.zero_prompt.paper_search.httpx.AsyncClient", return_value=mock_client),
            patch("agent.zero_prompt.paper_search.asyncio.sleep", new=AsyncMock()),
        ):
            from agent.zero_prompt import paper_search as ps_module

            ps_module._ARXIV_LAST_REQUEST = 0.0
            with pytest.raises(httpx.HTTPStatusError):
                await ps_module._arxiv_search("test")


class TestPaperSearchCache:
    @pytest.mark.asyncio
    async def test_cache_expired_triggers_refetch(self, monkeypatch):
        """_is_cache_valid removes stale entries (lines 40-41) and re-fetches."""
        from agent.zero_prompt import paper_search as ps_module
        from agent.zero_prompt.schemas import PaperMetadata

        call_count = 0

        async def fake_openalex(query, max_results=5):
            nonlocal call_count
            call_count += 1
            return [PaperMetadata(title="Fresh Paper", citations=1, year=2024, source="openalex")]

        async def fake_arxiv(query, max_results=5):
            return []

        monkeypatch.setattr(ps_module, "_openalex_search", fake_openalex)
        monkeypatch.setattr(ps_module, "_arxiv_search", fake_arxiv)
        ps_module._CACHE.clear()

        cache_key = ps_module._cache_key("expired test", 5)
        # Artificially insert an expired entry (TTL = 86400, insert epoch 0 so it's "expired")
        ps_module._CACHE[cache_key] = (0.0, [PaperMetadata(title="Old Paper", source="openalex")])

        # Should detect expiry, delete, and re-fetch
        result = await ps_module.search_papers("expired test", max_results=5)
        assert call_count == 1
        assert result[0].title == "Fresh Paper"

    @pytest.mark.asyncio
    async def test_cache_eviction_maxsize(self, monkeypatch):
        """_cache_put evicts oldest entries when cache exceeds _CACHE_MAX_SIZE (line 50)."""
        from agent.zero_prompt import paper_search as ps_module
        from agent.zero_prompt.schemas import PaperMetadata

        ps_module._CACHE.clear()

        # Fill cache up to max size
        for i in range(ps_module._CACHE_MAX_SIZE):
            key = f"query_{i}:5"
            ps_module._CACHE[key] = (time.time(), [PaperMetadata(title=f"P{i}", source="openalex")])

        assert len(ps_module._CACHE) == ps_module._CACHE_MAX_SIZE

        # Adding one more entry should trigger eviction
        extra_key = "extra_query:5"
        ps_module._cache_put(extra_key, [PaperMetadata(title="Extra", source="openalex")])

        assert len(ps_module._CACHE) == ps_module._CACHE_MAX_SIZE
        # The very first entry (query_0:5) should have been evicted
        assert "query_0:5" not in ps_module._CACHE
        assert extra_key in ps_module._CACHE

    @pytest.mark.asyncio
    async def test_search_papers_both_sources_fail(self, monkeypatch):
        """search_papers logs and returns [] when both sources fail (lines 241-242)."""
        from agent.zero_prompt import paper_search as ps_module

        async def failing_openalex(query, max_results=5):
            raise ConnectionError("OpenAlex down")

        async def failing_arxiv(query, max_results=5):
            raise ConnectionError("arXiv down")

        monkeypatch.setattr(ps_module, "_openalex_search", failing_openalex)
        monkeypatch.setattr(ps_module, "_arxiv_search", failing_arxiv)
        ps_module._CACHE.clear()

        result = await ps_module.search_papers("both fail test", max_results=5)
        assert result == []


class TestParseArxivXml:
    def test_parse_invalid_year(self):
        """_parse_arxiv_xml handles malformed year (lines 202-203)."""
        xml_text = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Bad Year Paper</title>
    <summary>Abstract.</summary>
    <published>XXXX-01-01T00:00:00Z</published>
    <id>http://arxiv.org/abs/9999.00001</id>
  </entry>
</feed>"""
        from agent.zero_prompt.paper_search import _parse_arxiv_xml

        results = _parse_arxiv_xml(xml_text)
        assert len(results) == 1
        assert results[0].year == 0  # default when parsing fails

    def test_parse_empty_title_skipped(self):
        """_parse_arxiv_xml skips entries with empty titles."""
        xml_text = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>   </title>
    <summary>Abstract.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <id>http://arxiv.org/abs/0001.00001</id>
  </entry>
  <entry>
    <title>Real Paper</title>
    <summary>Good abstract.</summary>
    <published>2024-02-01T00:00:00Z</published>
    <id>http://arxiv.org/abs/0001.00002</id>
  </entry>
</feed>"""
        from agent.zero_prompt.paper_search import _parse_arxiv_xml

        results = _parse_arxiv_xml(xml_text)
        assert len(results) == 1
        assert results[0].title == "Real Paper"

    def test_parse_bad_xml_returns_empty(self):
        """_parse_arxiv_xml returns [] on malformed XML (line 186)."""
        from agent.zero_prompt.paper_search import _parse_arxiv_xml

        results = _parse_arxiv_xml("<broken><xml>")
        assert results == []


# ===========================================================================
# discovery.py tests
# ===========================================================================


class TestHttpGet:
    @pytest.mark.asyncio
    async def test_http_get_success(self):
        """_http_get returns parsed JSON on success (lines 55-61)."""
        data = {"items": [{"id": {"videoId": "abc123"}}]}
        resp = _make_resp(json_data=data)
        mock_client = _make_mock_client(get_return=resp)

        with patch("agent.zero_prompt.discovery.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.discovery import _http_get

            result = await _http_get("https://api.example.com", {"key": "fake"})

        assert result == data

    @pytest.mark.asyncio
    async def test_http_get_retry_then_success(self):
        """_http_get retries on transient error and returns on success (lines 62-71)."""
        data = {"items": []}
        good_resp = _make_resp(json_data=data)
        error = httpx.TimeoutException("timeout")

        # First call fails, second succeeds
        mock_client = _make_mock_client(get_side_effect=[error, good_resp])

        with patch("agent.zero_prompt.discovery.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.discovery import _http_get

            result = await _http_get("https://api.example.com", {})

        assert result == data

    @pytest.mark.asyncio
    async def test_http_get_all_retries_fail(self):
        """_http_get raises last exception after all retries are exhausted (line 72)."""
        error = httpx.ConnectError("connection refused")
        mock_client = _make_mock_client(get_side_effect=[error, error, error])

        with patch("agent.zero_prompt.discovery.httpx.AsyncClient", return_value=mock_client):
            from agent.zero_prompt.discovery import _http_get

            with pytest.raises(httpx.ConnectError):
                await _http_get("https://api.example.com", {})


class TestSearchVideos:
    @pytest.mark.asyncio
    async def test_search_videos_returns_video_ids(self):
        """_search_videos returns list of video IDs (lines 76-86)."""

        async def fake_http_get(url, params):
            return {
                "items": [
                    {"id": {"videoId": "vid1"}},
                    {"id": {"videoId": "vid2"}},
                    {"id": {}},  # No videoId — should be skipped
                ]
            }

        with patch("agent.zero_prompt.discovery._http_get", side_effect=fake_http_get):
            from agent.zero_prompt.discovery import _search_videos

            ids = await _search_videos("fake-api-key", {"q": "test"}, max_results=10)

        assert ids == ["vid1", "vid2"]

    @pytest.mark.asyncio
    async def test_search_videos_limits_max_results_to_50(self):
        """_search_videos caps maxResults at 50."""
        captured_params = {}

        async def fake_http_get(url, params):
            captured_params.update(params)
            return {"items": []}

        with patch("agent.zero_prompt.discovery._http_get", side_effect=fake_http_get):
            from agent.zero_prompt.discovery import _search_videos

            await _search_videos("key", {"q": "q"}, max_results=200)

        assert captured_params["maxResults"] == 50


class TestGetVideoDetails:
    @pytest.mark.asyncio
    async def test_get_video_details_empty_ids(self):
        """_get_video_details returns [] for empty input (line 90-91)."""
        from agent.zero_prompt.discovery import _get_video_details

        result = await _get_video_details("fake-key", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_video_details_batches_requests(self):
        """_get_video_details batches IDs in chunks of 50 (lines 90-103)."""
        batch_calls = []

        async def fake_http_get(url, params):
            batch_calls.append(params["id"])
            return {"items": [{"id": params["id"]}]}

        with patch("agent.zero_prompt.discovery._http_get", side_effect=fake_http_get):
            from agent.zero_prompt.discovery import _get_video_details

            # 51 IDs should produce 2 batch calls
            ids = [f"vid{i}" for i in range(51)]
            result = await _get_video_details("key", ids)

        assert len(batch_calls) == 2
        assert len(result) == 2  # one item per batch call

    @pytest.mark.asyncio
    async def test_get_video_details_success(self):
        """_get_video_details returns video item dicts."""

        async def fake_http_get(url, params):
            return {
                "items": [
                    {
                        "id": "vid1",
                        "snippet": {"title": "Video 1", "channelTitle": "Ch1"},
                        "statistics": {"viewCount": "1000", "likeCount": "100", "commentCount": "10"},
                        "contentDetails": {"duration": "PT10M", "caption": "false"},
                    }
                ]
            }

        with patch("agent.zero_prompt.discovery._http_get", side_effect=fake_http_get):
            from agent.zero_prompt.discovery import _get_video_details

            result = await _get_video_details("key", ["vid1"])

        assert len(result) == 1
        assert result[0]["id"] == "vid1"


class TestYouTubeDiscovery:
    @pytest.mark.asyncio
    async def test_fetch_candidate_pool_no_api_key(self, monkeypatch):
        """fetch_candidate_pool raises ValueError when no API key (line 176)."""
        monkeypatch.delenv("YOUTUBE_DATA_API_KEY", raising=False)
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

        from agent.zero_prompt.discovery import YouTubeDiscovery

        disc = YouTubeDiscovery(api_key="")
        with pytest.raises(ValueError, match="YOUTUBE_DATA_API_KEY"):
            await disc.fetch_candidate_pool()

    @pytest.mark.asyncio
    async def test_fetch_candidate_pool_category_search_fails(self):
        """fetch_candidate_pool logs and skips failed category searches (lines 188-189)."""
        from agent.zero_prompt.discovery import YouTubeDiscovery

        call_count = 0

        async def fake_search_videos(api_key, query_params, max_results=50):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("network error")
            return []

        async def fake_get_video_details(api_key, video_ids):
            return []

        with (
            patch("agent.zero_prompt.discovery._search_videos", side_effect=fake_search_videos),
            patch("agent.zero_prompt.discovery._get_video_details", side_effect=fake_get_video_details),
        ):
            disc = YouTubeDiscovery(api_key="fake-key")
            # Should NOT raise even if one category fails
            result = await disc.fetch_candidate_pool(categories=["science_tech", "education"])

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_fetch_candidate_pool_default_cat_label(self):
        """fetch_candidate_pool uses categories[0] as fallback label (line 205)."""
        video_item = {
            "id": "vid_abc",
            "snippet": {
                "title": "Test Video",
                "channelTitle": "Test Channel",
                "publishedAt": "2024-01-01T00:00:00Z",
                "description": "desc",
                "thumbnails": {"default": {"url": "https://img.example.com/thumb.jpg"}},
                # categoryId is '99' — doesn't match any known category
                "categoryId": "99",
            },
            "statistics": {"viewCount": "50000", "likeCount": "2000", "commentCount": "100"},
            "contentDetails": {"duration": "PT5M", "caption": "false"},
        }

        async def fake_search_videos(api_key, query_params, max_results=50):
            return ["vid_abc"]

        async def fake_get_video_details(api_key, video_ids):
            return [video_item]

        with (
            patch("agent.zero_prompt.discovery._search_videos", side_effect=fake_search_videos),
            patch("agent.zero_prompt.discovery._get_video_details", side_effect=fake_get_video_details),
        ):
            from agent.zero_prompt.discovery import _CACHE, YouTubeDiscovery

            _CACHE.clear()
            disc = YouTubeDiscovery(api_key="fake-key")
            # Request only one category → fallback to categories[0]
            result = await disc.fetch_candidate_pool(
                categories=["science_tech"],
                min_views=0,
                min_likes=0,
                min_engagement_rate=0.0,
            )

        # The video should be present with category = "science_tech" (fallback)
        assert len(result) == 1
        assert result[0].category == "science_tech"

    @pytest.mark.asyncio
    async def test_fetch_candidate_pool_cache_hit(self):
        """fetch_candidate_pool returns cached results without re-fetching."""
        from agent.zero_prompt.discovery import _CACHE, YouTubeDiscovery, _cache_key
        from agent.zero_prompt.schemas import VideoCandidate

        _CACHE.clear()
        # Pre-populate the cache
        ck = _cache_key(("science_tech",), 0, 0, 0.0, 60)
        cached_video = VideoCandidate(
            video_id="cached_vid",
            title="Cached",
            channel_title="CH",
            published_at="2024-01-01T00:00:00Z",
        )
        _CACHE[ck] = (time.time(), [cached_video])

        call_count = 0

        async def fake_search_videos(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return []

        with patch("agent.zero_prompt.discovery._search_videos", side_effect=fake_search_videos):
            disc = YouTubeDiscovery(api_key="fake-key")
            result = await disc.fetch_candidate_pool(
                categories=["science_tech"],
                min_views=0,
                min_likes=0,
                min_engagement_rate=0.0,
            )

        assert call_count == 0
        assert result[0].video_id == "cached_vid"

    @pytest.mark.asyncio
    async def test_fetch_candidate_pool_filters_applied(self):
        """fetch_candidate_pool filters results by min_views, min_likes, engagement_rate."""
        video_items = [
            {
                "id": "low_views",
                "snippet": {
                    "title": "Low Views",
                    "channelTitle": "CH",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "description": "",
                    "thumbnails": {},
                    "categoryId": "28",
                },
                "statistics": {"viewCount": "100", "likeCount": "5", "commentCount": "1"},
                "contentDetails": {"duration": "PT1M", "caption": "false"},
            },
            {
                "id": "high_views",
                "snippet": {
                    "title": "High Views",
                    "channelTitle": "CH",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "description": "",
                    "thumbnails": {},
                    "categoryId": "28",
                },
                "statistics": {"viewCount": "100000", "likeCount": "5000", "commentCount": "500"},
                "contentDetails": {"duration": "PT10M", "caption": "true"},
            },
        ]

        async def fake_search_videos(api_key, query_params, max_results=50):
            return ["low_views", "high_views"]

        async def fake_get_video_details(api_key, video_ids):
            return video_items

        with (
            patch("agent.zero_prompt.discovery._search_videos", side_effect=fake_search_videos),
            patch("agent.zero_prompt.discovery._get_video_details", side_effect=fake_get_video_details),
        ):
            from agent.zero_prompt.discovery import _CACHE, YouTubeDiscovery

            _CACHE.clear()
            disc = YouTubeDiscovery(api_key="fake-key")
            result = await disc.fetch_candidate_pool(
                categories=["science_tech"],
                min_views=10_000,
                min_likes=200,
                min_engagement_rate=0.02,
            )

        # Only the high_views video passes
        assert len(result) == 1
        assert result[0].video_id == "high_views"

    @pytest.mark.asyncio
    async def test_fetch_candidate_pool_default_categories(self):
        search_call_count = 0

        async def fake_search_videos(api_key, query_params, max_results=50):
            nonlocal search_call_count
            search_call_count += 1
            return []

        async def fake_get_video_details(api_key, video_ids):
            return []

        with (
            patch("agent.zero_prompt.discovery._search_videos", side_effect=fake_search_videos),
            patch("agent.zero_prompt.discovery._get_video_details", side_effect=fake_get_video_details),
        ):
            from agent.zero_prompt.discovery import _CACHE, _CATEGORY_QUERIES, YouTubeDiscovery

            _CACHE.clear()
            disc = YouTubeDiscovery(api_key="fake-key")
            result = await disc.fetch_candidate_pool(
                categories=None,
                min_views=0,
                min_likes=0,
                min_engagement_rate=0.0,
            )

        assert search_call_count == len(_CATEGORY_QUERIES)
        assert isinstance(result, list)
