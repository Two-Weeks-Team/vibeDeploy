# Task 166: 경쟁사 분석 엔진 (Brave Search) (v2)
상태: 미구현 | Phase 0 | 예상 시간: 8h
의존성: 없음

## 1. 태스크 정의
Brave Search API를 사용하여 아이디어와 관련된 경쟁사를 발견하고, `gemini-3.1-flash-lite-preview`로 시장 기회 점수와 차별화 포인트를 분석합니다. 시장 포화도와 직접 경쟁사 리스트를 추출하여 GO/NO-GO 판정의 핵심 데이터를 제공합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: Brave Search API를 사용하여 관련 서비스 및 경쟁사를 성공적으로 검색함.
- [ ] AC-2: `gemini-3.1-flash-lite-preview`를 사용하여 검색 결과에서 `market_opportunity_score`, `competitors`, `gaps`, `differentiation`을 추출함.
- [ ] AC-3: Brave Search API 키가 없거나 실패 시 LLM 폴백(자체 지식 기반 분석)이 동작함.
- [ ] AC-4: 분석 결과에 5개 이상의 경쟁사 리스트가 포함되어야 함.
- [ ] AC-5: 분석 시작(`zp.compete.start`) 및 완료(`zp.compete.complete`) 시 SSE 이벤트를 발행함.

## 3. 변경 대상 파일
- `agent/tools/competitive_analysis.py` (신규)
- `agent/state.py` (MarketAnalysis 모델 추가)

## 4. 상세 구현

### MarketAnalysis 모델 (agent/state.py)
```python
class MarketAnalysis(BaseModel):
    market_opportunity_score: int  # 0~100
    competitors: list[str]
    gaps: list[str]
    differentiation: str
    saturation_level: str  # low, medium, high
```

### Competitive Analysis Engine (agent/tools/competitive_analysis.py)
```python
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import MarketAnalysis

class CompetitiveAnalysis:
    def __init__(self):
        self.brave_api_key = os.getenv("BRAVE_SEARCH_API_KEY")

    async def analyze_market(self, idea_title: str, idea_description: str) -> MarketAnalysis:
        # 1. zp.compete.start SSE 발행
        # 2. Brave Search API로 경쟁사 검색
        # 3. gemini-3.1-flash-lite-preview로 검색 결과 분석
        # 4. zp.compete.complete SSE 발행
        # 5. MarketAnalysis 객체 반환
        pass
```

## 5. 테스트 계획
- `test_brave_search_integration`: Brave Search API 호출 및 결과 파싱 확인.
- `test_market_analysis_llm`: 검색 결과가 주어졌을 때 LLM이 기회 점수와 차별화 포인트를 올바르게 추출하는지 확인.
- `test_fallback_mechanism`: API 키 부재 시 LLM 폴백 동작 확인.

## 6. 검증 방법
- `pytest agent/tests/test_competitive_analysis.py` 실행.
- 반환된 경쟁사 리스트가 실제 존재하는 서비스인지 샘플링 검사.

## 7. 롤백 계획
- `git checkout docs/reference/166-competitive-analysis.md`
- `agent/tools/competitive_analysis.py` 삭제.
