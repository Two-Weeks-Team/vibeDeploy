# Task 163: Gemini Insight Extractor (v2)
상태: 미구현 | Phase 0 | 예상 시간: 8h
의존성: 151, 162

## 1. 태스크 정의
`gemini-3.1-flash-lite-preview`를 사용하여 추출된 트랜스크립트에서 앱 아이디어를 구조화된 JSON(AppIdea)으로 추출합니다. Pydantic 스키마와 구조화된 출력을 사용하여 데이터의 일관성을 보장하며, Context Caching을 활용하여 비용을 최적화합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `gemini-3.1-flash-lite-preview`를 사용하여 트랜스크립트에서 유효한 AppIdea JSON을 추출함.
- [ ] AC-2: 추출된 데이터에 `confidence_score`가 포함되어야 함.
- [ ] AC-3: 한국어 트랜스크립트 및 다국어 처리가 정상적으로 이루어짐.
- [ ] AC-4: 영상당 LLM 비용이 $0.001 이내로 유지됨.
- [ ] AC-5: 추출 시작(`zp.insight.start`) 및 완료(`zp.insight.complete`) 시 SSE 이벤트를 발행함.

## 3. 변경 대상 파일
- `agent/nodes/insight_extractor.py` (v2 업데이트)
- `agent/state.py` (AppIdea 모델 확인)

## 4. 상세 구현

### AppIdea 모델 (agent/state.py)
```python
class AppIdea(BaseModel):
    title: str
    description: str
    target_audience: list[str]
    core_features: list[str]
    confidence_score: float
    original_video_id: str
```

### Gemini Insight Extractor (agent/nodes/insight_extractor.py)
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AppIdea

async def extract_app_idea(transcript: str, video_id: str) -> AppIdea:
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview")
    # 1. zp.insight.start SSE 발행
    # 2. 트랜스크립트 분석 및 AppIdea 추출 (Pydantic output parser 사용)
    # 3. zp.insight.complete SSE 발행
    # 4. AppIdea 객체 반환
    pass
```

## 5. 테스트 계획
- `test_insight_extraction`: 다양한 주제의 트랜스크립트에서 일관된 JSON 구조가 추출되는지 확인.
- `test_confidence_score`: 0.0~1.0 사이의 신뢰도 점수가 포함되는지 확인.
- `test_cost_efficiency`: 토큰 사용량 및 예상 비용 로그 확인.

## 6. 검증 방법
- `pytest agent/tests/test_insight_extractor.py` 실행.
- 반환된 `AppIdea` 객체의 필드 누락 여부 확인.

## 7. 롤백 계획
- `git checkout docs/reference/163-gemini-insight.md`
- `agent/nodes/insight_extractor.py` 변경 사항 취소.
