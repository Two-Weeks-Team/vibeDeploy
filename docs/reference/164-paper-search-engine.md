# Task 164: 논문 검색 엔진 (OpenAlex + arXiv) (v2)
상태: 미구현 | Phase 0 | 예상 시간: 6h
의존성: 없음

## 1. 태스크 정의

`research_librarian` 에이전트가 아이디어에 맞는 검색 쿼리를 생성하고, OpenAlex와 arXiv에서 관련 논문 메타데이터를 수집한다. 이 태스크는 "논문을 많이 긁는 것"보다 **짧고 근거 있는 3~5편**을 안정적으로 반환하는 것이 중요하다.

## 2. 담당 에이전트와 페르소나

- Agent ID: `research_librarian`
- Persona: 연구 사서
- 원칙: 논문 수집보다 관련성과 근거 품질을 우선한다.

## 3. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: OpenAlex 검색이 정상 동작한다.
- [ ] AC-2: arXiv 검색이 정상 동작하며 rate limit을 지킨다.
- [ ] AC-3: 3~5편의 `PaperMetadata`를 반환한다.
- [ ] AC-4: `zp.paper.search`, `zp.paper.found` 이벤트를 발행한다.
- [ ] AC-5: OpenAlex 실패 시 arXiv-only로 축소 동작한다.

## 4. 변경 대상 파일

- `agent/zero_prompt/paper_search.py` (신규)
- `agent/zero_prompt/schemas.py` (신규)
- `agent/zero_prompt/events.py` (신규)

## 5. 상세 구현

```python
class PaperMetadata(BaseModel):
    title: str
    abstract: str
    citations: int
    year: int
    url: str
    source: Literal["openalex", "arxiv"]
```

도구 호출 규칙:
- OpenAlex: timeout 10초, retry 2회, 24시간 캐시
- arXiv: timeout 10초, retry 1회, global throttle 1req/3s

## 6. 테스트 계획

- `test_generate_paper_queries_from_idea`
- `test_openalex_results_are_parsed`
- `test_arxiv_throttle_is_respected`
- `test_paper_events_are_emitted`

## 7. 검증 방법

- `pytest agent/tests/test_zero_prompt_paper_search.py -v`

## 8. 롤백 계획

- `agent/zero_prompt/paper_search.py` 제거
