# Task 162: 스트리밍 트랜스크립트 추출 (v2)
상태: 미구현 | Phase 0 | 예상 시간: 6h
의존성: 161

## 1. 태스크 정의

`transcript_fetcher` 에이전트가 후보 영상 1개를 입력받아 자막 또는 메타데이터 컨텍스트를 추출한다. 기존 `agent/tools/youtube.py`의 기능을 재사용하되, Zero-Prompt용 이벤트와 결과 타입을 감싸는 어댑터를 만든다.

## 2. 담당 에이전트와 페르소나

- Agent ID: `transcript_fetcher`
- Persona: 기록 담당 조사원
- 원칙: 텍스트를 최대한 잃지 않고 수집하고, 실패 시에도 빈 문자열 대신 설명 가능한 폴백을 남긴다.

## 3. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: 단일 `video_id` 또는 URL에 대해 텍스트를 추출한다.
- [ ] AC-2: `zp.transcript.start`, `zp.transcript.complete` 이벤트를 발행한다.
- [ ] AC-3: 자막 부재나 IP 차단 시 메타데이터 폴백을 반환한다.
- [ ] AC-4: 토큰 수와 추출 방식(`manual`, `auto`, `metadata_fallback`)을 로그에 남긴다.

## 4. 변경 대상 파일

- `agent/zero_prompt/transcript.py` (신규)
- `agent/tools/youtube.py` (기존 재사용, 필요한 경우 helper export 추가)
- `agent/zero_prompt/events.py` (신규)
- `agent/zero_prompt/schemas.py` (신규)

## 5. 상세 구현

```python
class TranscriptArtifact(BaseModel):
    video_id: str
    text: str
    source: Literal["manual", "auto", "metadata_fallback", "error"]
    language: str | None = None
    token_count: int = 0
```

```python
async def fetch_transcript_artifact(video_id: str) -> TranscriptArtifact:
    # 1. zp.transcript.start
    # 2. 기존 extract_youtube_transcript 재사용
    # 3. token_count 계산
    # 4. zp.transcript.complete
    ...
```

## 6. 테스트 계획

- `test_fetch_transcript_artifact_success`
- `test_metadata_fallback_is_returned_when_transcript_missing`
- `test_token_count_is_recorded`
- `test_transcript_events_are_emitted`

## 7. 검증 방법

- `pytest agent/tests/test_zero_prompt_transcript.py -v`

## 8. 롤백 계획

- `agent/zero_prompt/transcript.py` 제거
