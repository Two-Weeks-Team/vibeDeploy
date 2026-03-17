# Task 163: Gemini Insight Extractor (v2)

상태: 미구현 | Phase 0 | 예상 시간: 8h
의존성: 151, 162

## 1. 태스크 정의

`insight_miner`는 트랜스크립트에서 **빌드 가능한 앱 아이디어 1개**를 구조화된 `AppIdea`로 뽑는다.

이 태스크는 공식 Google SDK 경로를 사용한다.

- 모델: `gemini-3.1-flash-lite-preview`
- API 스타일: `google_generate_content`
- 출력 방식: `application/json` + schema

## 2. 담당 에이전트와 페르소나

- Agent ID: `insight_miner`
- Persona: 제품 발굴가
- 원칙:
  - 영상 요약을 하지 않는다.
  - 앱 아이디어는 1개만 고른다.
  - 과장된 시장성 문구보다 구체적인 타겟/핵심 기능을 우선한다.

## 3. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: `gemini-3.1-flash-lite-preview`로 유효한 `AppIdea`를 생성한다.
- [ ] AC-2: `confidence_score`를 `0.0~1.0` 범위로 포함한다.
- [ ] AC-3: 응답은 Pydantic 검증을 통과해야 한다.
- [ ] AC-4: `zp.insight.start`, `zp.insight.complete` 이벤트를 발행한다.
- [ ] AC-5: 구조화 출력 실패 시 1회 self-repair 재시도를 수행한다.
- [ ] AC-6: 공식 Google SDK 경로를 사용하며 LangChain wrapper를 사용하지 않는다.

## 4. 변경 대상 파일

- `agent/zero_prompt/insight.py` (신규)
- `agent/zero_prompt/schemas.py` (신규)
- `agent/zero_prompt/events.py` (신규)
- `agent/providers/google_adapter.py` (151에서 추가)

## 5. 상세 구현

```python
class AppIdea(BaseModel):
    title: str
    description: str
    target_audience: list[str]
    core_features: list[str]
    confidence_score: float
    original_video_id: str
```

```python
response = google_adapter.invoke(
    model_id="gemini-3.1-flash-lite-preview",
    messages=messages,
    temperature=0.2,
    max_output_tokens=1024,
    response_schema=AppIdea,
    metadata={
        "session_id": session_id,
        "video_id": video_id,
        "stage": "zp_insight",
    },
)
```

## 6. 테스트 계획

- `test_extract_app_idea_returns_valid_schema`
- `test_confidence_score_is_bounded`
- `test_self_repair_retries_once_on_invalid_json`
- `test_insight_events_are_emitted`
- `test_google_sdk_path_is_used`

## 7. 검증 방법

- `pytest agent/tests/test_zero_prompt_insight.py -v`

## 8. 롤백 계획

- `agent/zero_prompt/insight.py` 제거

## 9. 공식 출처

- 가격: [Gemini Developer API 가격](https://ai.google.dev/gemini-api/docs/pricing?hl=ko)
- 모델: [gemini-3.1-flash-lite-preview](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-preview)
- 구조화 출력: [Structured output](https://ai.google.dev/gemini-api/docs/structured-output)
