# Task 161: YouTube Discovery Engine (v2)
상태: 미구현 | Phase 0 | 예상 시간: 8h
의존성: 없음

## 1. 태스크 정의

`discovery_curator` 에이전트가 YouTube Data API v3를 사용해 후보 영상 풀을 구성한다. 이 단계는 LLM이 아니라 규칙 기반 필터링이 핵심이며, 결과는 Zero-Prompt 오케스트레이터가 한 개씩 소비할 수 있는 `VideoCandidate[]` 이어야 한다.

## 2. 담당 에이전트와 페르소나

- Agent ID: `discovery_curator`
- Persona: 트렌드 에디터
- 원칙: 과장 없이 조회수/좋아요/댓글과 카테고리 적합성으로 후보를 고른다.

## 3. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: `search.list` + `videos.list` 조합으로 후보를 수집한다.
- [ ] AC-2: 카테고리 필터와 engagement 필터를 적용한다.
- [ ] AC-3: 1회 호출 시 50개 이상의 유효 후보를 반환한다.
- [ ] AC-4: 시작/완료 시 `zp.search.start`, `zp.search.complete` 이벤트를 발행한다.
- [ ] AC-5: API 키가 없으면 명확한 에러를 남기고 세션을 `error`로 전환한다.

## 4. 변경 대상 파일

- `agent/zero_prompt/discovery.py` (신규)
- `agent/zero_prompt/schemas.py` (신규)
- `agent/zero_prompt/events.py` (신규)

## 5. 상세 구현

### 5.1 데이터 모델

```python
class VideoCandidate(BaseModel):
    video_id: str
    title: str
    channel_title: str
    published_at: str
    view_count: int
    like_count: int
    comment_count: int
    engagement_rate: float
    category: str
```

### 5.2 구현 계약

```python
class YouTubeDiscovery:
    async def fetch_candidate_pool(
        self,
        categories: list[str],
        *,
        min_views: int = 10_000,
        min_likes: int = 200,
        min_engagement_rate: float = 0.02,
        max_results: int = 60,
    ) -> list[VideoCandidate]:
        ...
```

도구 호출 규칙:
- timeout 20초
- retry 2회
- 15분 캐시
- 중복 `video_id` 제거

## 6. 테스트 계획

- `test_fetch_candidate_pool_returns_filtered_candidates`
- `test_duplicate_video_ids_are_removed`
- `test_search_events_are_emitted`
- `test_missing_api_key_fails_gracefully`

## 7. 검증 방법

- `pytest agent/tests/test_zero_prompt_discovery.py -v`

## 8. 롤백 계획

- `agent/zero_prompt/discovery.py` 제거
