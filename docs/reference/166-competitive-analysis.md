# Task 166: 경쟁사 분석 엔진 (Brave + Exa 병렬 검색) (v2)
상태: 미구현 | Phase 0 | 예상 시간: 8h
의존성: 없음

## 1. 태스크 정의

`market_scout` 에이전트가 **Brave Search + Exa Search를 병렬**로 호출하여 결과를 병합하고, 경쟁사·시장 공백·포화도·차별화 기회를 추출한다. 양쪽 검색에서 동시에 나오는 결과는 `confidence: high`로 표시하여 신뢰도를 높인다.

### Brave + Exa 병렬 검색 방식

- **Brave Search**: API 키 기반 (무료 2,000건/월), 일반 웹 검색
- **Exa Search**: API 키 불필요 — 토큰 자동 발급 (5분 유효, IP당 ~1,000건), 시맨틱 검색
- 결과 **병합 + 중복 제거 + 신뢰도 채점** (양쪽 다 나오면 `confidence: high`)
- 커버리지 2배, 단일 소스 대비 품질 향상

## 2. 담당 에이전트와 페르소나

- Agent ID: `market_scout`
- Persona: 경쟁정보 분석가
- 원칙: "누가 이미 하고 있는가"와 "어디가 비어 있는가"를 짧고 근거 있게 정리한다.

## 3. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: Brave + Exa를 **병렬** 호출하고 결과를 병합한다
- [ ] AC-2: 양쪽 모두에서 나온 URL은 `confidence: high`로 표시한다
- [ ] AC-3: `MarketAnalysis`를 구조화 출력으로 생성한다 (gemini-3.1-flash-lite-preview)
- [ ] AC-4: Brave 실패 시 Exa 단독, Exa 실패 시 Brave 단독으로 폴백한다
- [ ] AC-5: 양쪽 모두 실패 시 LLM 자체 지식 기반 축소 분석으로 폴백한다
- [ ] AC-6: `zp.compete.start`, `zp.compete.complete` SSE 이벤트를 발행한다
- [ ] AC-7: 포화도는 `low | medium | high` 중 하나여야 한다

## 4. 변경 대상 파일

| 파일 | 유형 | 설명 |
|------|------|------|
| `agent/zero_prompt/unified_search.py` | 신규 | Brave + Exa 병렬 검색 엔진 |
| `agent/zero_prompt/competitive_analysis.py` | 신규 | 검색 결과 → LLM 분석 |
| `agent/zero_prompt/schemas.py` | 수정 | MarketAnalysis, SearchResult 스키마 |
| `agent/zero_prompt/events.py` | 수정 | compete 이벤트 추가 |

## 5. 상세 구현

### 5.1 통합 검색 (unified_search.py)

```python
import asyncio
import httpx
import os
from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str | None = None
    source: str  # "brave" | "exa"
    confidence: str = "normal"  # "normal" | "high"


async def unified_search(query: str, limit: int = 5) -> list[SearchResult]:
    """Brave + Exa 병렬 검색 → 병합 + 중복 제거 + 신뢰도 채점."""
    brave_task = asyncio.create_task(_search_brave(query, limit))
    exa_task = asyncio.create_task(_search_exa(query, limit))

    brave_results, exa_results = await asyncio.gather(
        brave_task, exa_task, return_exceptions=True
    )

    # 실패 처리
    if isinstance(brave_results, Exception):
        brave_results = []
    if isinstance(exa_results, Exception):
        exa_results = []

    # 병합 + 중복 제거 + 신뢰도
    return _merge_and_score(
        (brave_results or []) + (exa_results or [])
    )


async def _search_brave(query: str, limit: int) -> list[SearchResult]:
    api_key = os.getenv("BRAVE_API_KEY", "")
    if not api_key:
        return []

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            params={"q": query, "count": limit},
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("description"),
                source="brave",
            )
            for r in data.get("web", {}).get("results", [])[:limit]
        ]


async def _search_exa(query: str, limit: int) -> list[SearchResult]:
    """Exa Search — API 키 불필요, 토큰 자동 발급."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. 토큰 자동 발급 (5분 유효)
        token_resp = await client.post(
            "https://exa.ai/api/token/issue",
            headers={"Content-Type": "application/json"},
            json={},
        )
        token = token_resp.json().get("token")
        if not token:
            return []

        # 2. 검색
        resp = await client.post(
            "https://exa.ai/api/search",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"query": query, "numResults": limit},
        )
        resp.raise_for_status()
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=None,
                source="exa",
            )
            for r in resp.json().get("results", [])[:limit]
        ]


def _normalize_url(url: str) -> str:
    import re
    return re.sub(r"https?://(www\.)?", "", url).rstrip("/")


def _merge_and_score(results: list[SearchResult]) -> list[SearchResult]:
    """URL 기준 중복 제거 + 양쪽 모두 나오면 confidence=high."""
    from collections import defaultdict

    groups: dict[str, list[SearchResult]] = defaultdict(list)
    for r in results:
        groups[_normalize_url(r.url)].append(r)

    merged = []
    for _url, group in groups.items():
        sources = {r.source for r in group}
        best = group[0]
        # snippet이 있는 결과 우선
        for r in group:
            if r.snippet:
                best = r
                break
        merged.append(
            SearchResult(
                title=best.title,
                url=best.url,
                snippet=best.snippet,
                source=",".join(sorted(sources)),
                confidence="high" if len(sources) > 1 else "normal",
            )
        )

    # high confidence 먼저 정렬
    return sorted(merged, key=lambda r: (0 if r.confidence == "high" else 1))
```

### 5.2 경쟁 분석 (competitive_analysis.py)

```python
class MarketAnalysis(BaseModel):
    market_opportunity_score: int  # 0~100
    competitors: list[str]
    gaps: list[str]
    differentiation: str
    saturation_level: Literal["low", "medium", "high"]
    search_confidence: str  # "high" (양쪽), "normal" (한쪽), "llm_only" (폴백)
```

## 6. 테스트 계획

- `test_unified_search_merges_results` — 양쪽 결과 병합 확인
- `test_confidence_high_when_both_sources` — 양쪽 URL 중복 시 high
- `test_brave_only_fallback` — Exa 실패 시 Brave 단독
- `test_exa_only_fallback` — Brave API 키 없을 시 Exa 단독
- `test_both_fail_llm_fallback` — 양쪽 실패 시 LLM 폴백
- `test_compete_events_emitted` — SSE 이벤트 발행

## 7. 검증 방법

| 검증 항목 | 명령어 | 기대 결과 |
|---------|--------|---------|
| 통합 검색 동작 | `pytest tests/test_unified_search.py -v` | 6개 테스트 통과 |
| Exa 토큰 발급 | `curl -s -X POST https://exa.ai/api/token/issue -d '{}'` | `{"token": "eyJ..."}` |

## 8. 롤백 계획

- `agent/zero_prompt/unified_search.py` 제거
- `agent/zero_prompt/competitive_analysis.py` 제거
- 기존 `agent/tools/web_search.py`의 `search_competitors()` 사용으로 복귀

## 9. 환경변수

```bash
# Brave API 키 (무료 2,000건/월)
BRAVE_API_KEY=your_brave_api_key_here

# Exa는 API 키 불필요 — 토큰 자동 발급
# 추가 설정 없음
```
