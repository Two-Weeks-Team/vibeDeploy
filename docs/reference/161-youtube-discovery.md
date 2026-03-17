# Task 161: YouTube Discovery Engine (v2)
상태: 미구현 | Phase 0 | 예상 시간: 8h
의존성: 없음

## 1. 태스크 정의
YouTube Data API v3를 사용하여 트렌딩 및 고인게이지먼트 영상 후보 풀을 구성하는 엔진을 구축합니다. v2에서는 300개 고정 배치가 아닌, 탐색 큐에서 호출되어 후보 ID 풀을 반환하고, GO 대기 슬롯이 10개 미만일 때만 스트리밍 루프의 시작점 역할을 합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `googleapiclient.discovery`를 사용하여 `search.list(order=viewCount)`와 `videos.list`를 성공적으로 호출함.
- [ ] AC-2: 지정된 카테고리(Science&Tech, Education, Startup 등)별 검색 및 인게이지먼트 필터(조회수 1만+, 좋아요 200+, 인게이지먼트율 2%+) 적용.
- [ ] AC-3: 탐색 큐에서 호출 시 50+개의 유효한 후보 영상 ID 리스트를 반환함.
- [ ] AC-4: 1회 후보 풀 구성 시 YouTube API 쿼터 소비가 606 units 이내여야 함.
- [ ] AC-5: API 키가 없거나 유효하지 않을 경우 적절한 에러 메시지와 함께 Graceful하게 종료됨.

## 3. 변경 대상 파일
- `agent/tools/youtube_discovery.py` (v2 업데이트)
- `agent/state.py` (DiscoveryState 추가)

## 4. 상세 구현

### DiscoveryState (agent/state.py)
```python
class DiscoveryState(BaseModel):
    candidate_pool: list[str] = []  # 영상 ID 리스트
    current_index: int = 0
    is_paused: bool = False
```

### YouTube Discovery Engine (agent/tools/youtube_discovery.py)
```python
import os
from googleapiclient.discovery import build

class YouTubeDiscovery:
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_DATA_API_KEY")
        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    async def fetch_candidate_pool(self, queries: list[str]) -> list[str]:
        # search.list로 후보 ID 수집 (order='viewCount')
        # videos.list로 상세 스탯 확인 및 필터링
        # 필터를 통과한 video_id 리스트 반환
        pass
```

## 5. 테스트 계획
- `test_fetch_candidates`: 실제 API 호출을 통해 필터링된 ID 리스트가 반환되는지 확인.
- `test_quota_usage`: 쿼터 소비량이 제한 내인지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_youtube_discovery.py` 실행.
- 반환된 리스트의 모든 영상이 인게이지먼트 기준을 충족하는지 샘플링 검사.

## 7. 롤백 계획
- `git checkout docs/reference/161-youtube-discovery.md`
- `agent/tools/youtube_discovery.py` 변경 사항 취소.
