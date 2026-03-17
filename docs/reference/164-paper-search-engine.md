# Task 164: 논문 검색 엔진 (OpenAlex + arXiv) (v2)
상태: 미구현 | Phase 0 | 예상 시간: 6h
의존성: 없음

## 1. 태스크 정의
아이디어의 과학적 근거와 기술적 차별화를 위해 OpenAlex와 arXiv에서 관련 논문을 검색하는 엔진을 구축합니다. 아이디어 키워드를 기반으로 검색 쿼리를 생성하고, 3~5편의 논문 메타데이터(제목, 초록, 인용 수, 연도)를 수집합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: OpenAlex API를 사용하여 관련 논문을 성공적으로 검색함.
- [ ] AC-2: OpenAlex 실패 시 arXiv API로 폴백 동작함.
- [ ] AC-3: 검색 결과에 논문 제목, 초록(abstract), 인용 수, 발행 연도가 포함되어야 함.
- [ ] AC-4: 무료 API 범위 내에서 안정적으로 동작함 (OpenAlex 1,000회/일, arXiv 1req/3s).
- [ ] AC-5: 검색 시작(`zp.paper.search`) 및 완료(`zp.paper.found`) 시 SSE 이벤트를 발행함.

## 3. 변경 대상 파일
- `agent/tools/paper_search.py` (신규)
- `agent/state.py` (PaperMetadata 모델 추가)

## 4. 상세 구현

### PaperMetadata 모델 (agent/state.py)
```python
class PaperMetadata(BaseModel):
    title: str
    abstract: str
    citations: int
    year: int
    url: str
```

### Paper Search Engine (agent/tools/paper_search.py)
```python
import httpx
from agent.state import PaperMetadata

class PaperSearch:
    async def search_openalex(self, query: str, limit: int = 3) -> list[PaperMetadata]:
        # OpenAlex API 호출 및 결과 파싱
        pass

    async def search_arxiv(self, query: str, limit: int = 2) -> list[PaperMetadata]:
        # arXiv API 호출 및 결과 파싱
        pass

    async def get_relevant_papers(self, idea_keywords: str) -> list[PaperMetadata]:
        # 1. zp.paper.search SSE 발행
        # 2. OpenAlex + arXiv 병렬 검색
        # 3. 결과 통합 및 zp.paper.found SSE 발행
        # 4. PaperMetadata 리스트 반환
        pass
```

## 5. 테스트 계획
- `test_openalex_search`: 특정 키워드로 OpenAlex 검색 결과가 올바르게 반환되는지 확인.
- `test_arxiv_fallback`: OpenAlex 실패 시 arXiv에서 결과를 가져오는지 확인.
- `test_paper_metadata_fields`: 반환된 메타데이터의 모든 필드가 채워져 있는지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_paper_search.py` 실행.
- 반환된 논문 리스트의 초록이 아이디어와 관련이 있는지 샘플링 검사.

## 7. 롤백 계획
- `git checkout docs/reference/164-paper-search-engine.md`
- `agent/tools/paper_search.py` 삭제.
