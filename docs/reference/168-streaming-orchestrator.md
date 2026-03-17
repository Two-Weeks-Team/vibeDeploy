# Task 168: 스트리밍 루프 오케스트레이터 + API (v2)
상태: 미구현 | Phase 0 | 예상 시간: 8h
의존성: 161~167

## 1. 태스크 정의

전체 Zero-Prompt 세션의 상태를 관리하는 오케스트레이터를 구축한다. 이 모듈은 탐색 워커, 빌드 워커, GO 슬롯 수, 사용자 액션, 세션 전용 SSE 스트림을 단일 기준으로 관리한다.

이 태스크의 핵심은 알고리즘 구현보다 **세션 계약을 고정하는 것**이다.

## 2. 명시적 결정

- 세션당 탐색 워커는 1개만 실행한다.
- 세션당 빌드 워커는 1개만 실행한다.
- `GO!`는 기존 `/api/run` 파이프라인으로 handoff하며, 기본값은 `skip_council=true`다.
- `pause`는 탐색만 멈춘다. 이미 시작한 빌드는 계속 진행한다.
- Phase 0 저장소는 인메모리 우선이며, 서버 재시작 시 세션 유실은 허용한다.

## 3. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: `POST /api/zero-prompt/start` 호출 시 세션이 생성되고 `zp.session.start` 이벤트가 발행된다.
- [ ] AC-2: `go_ready < goal_go_cards`일 때만 탐색 워커가 다음 후보 영상을 처리한다.
- [ ] AC-3: 빌드 큐는 FIFO이며 동시에 1개만 `building` 상태를 가질 수 있다.
- [ ] AC-4: 영상 1개당 `transcript -> insight -> paper -> brainstorm -> compete -> verdict`가 순차 실행된다.
- [ ] AC-5: `queue_build`, `pass_card`, `delete_card`, `pause`, `resume` 액션이 세션 상태에 반영된다.
- [ ] AC-6: 기존 빌드 파이프라인의 `thread_id`를 `build_thread_id`로 카드에 연결한다.
- [ ] AC-7: 세션 SSE 재연결 시 `GET /api/zero-prompt/{session_id}` 로 상태를 복구할 수 있다.

## 4. 변경 대상 파일

- `agent/zero_prompt/orchestrator.py` (신규)
- `agent/zero_prompt/queue_manager.py` (신규)
- `agent/zero_prompt/schemas.py` (신규)
- `agent/zero_prompt/events.py` (신규)
- `agent/server.py` (Zero-Prompt endpoint 추가)

## 5. 상세 구현

### 5.1 권장 상태 모델

```python
from pydantic import BaseModel, Field
from typing import Literal


class ZeroPromptCard(BaseModel):
    card_id: str
    status: Literal[
        "analyzing",
        "go_ready",
        "build_queued",
        "building",
        "deployed",
        "nogo",
        "passed",
        "build_failed",
    ]
    title: str
    source_video_id: str
    score: int | None = None
    reason: str | None = None
    queue_position: int | None = None
    build_thread_id: str | None = None
    live_url: str | None = None


class ZeroPromptSession(BaseModel):
    session_id: str
    status: Literal["idle", "running", "paused", "completed", "error"] = "idle"
    goal_go_cards: int = 10
    candidate_pool: list[str] = Field(default_factory=list)
    cards: list[ZeroPromptCard] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    analyzed_count: int = 0
    build_queue: list[str] = Field(default_factory=list)  # card_id FIFO
    active_build_card_id: str | None = None
```

### 5.2 Queue Manager (`agent/zero_prompt/queue_manager.py`)

```python
class QueueManager:
    def __init__(self, session: ZeroPromptSession):
        self.session = session

    def available_go_count(self) -> int:
        return sum(
            1
            for card in self.session.cards
            if card.status == "go_ready"
        )

    def should_continue_discovery(self) -> bool:
        return self.session.status == "running" and self.available_go_count() < self.session.goal_go_cards

    def enqueue_build(self, card_id: str) -> int:
        if card_id not in self.session.build_queue:
            self.session.build_queue.append(card_id)
        return self.session.build_queue.index(card_id) + 1

    def pop_next_build(self) -> str | None:
        if self.session.active_build_card_id or not self.session.build_queue:
            return None
        next_card_id = self.session.build_queue.pop(0)
        self.session.active_build_card_id = next_card_id
        return next_card_id
```

### 5.3 Orchestrator (`agent/zero_prompt/orchestrator.py`)

```python
class ZeroPromptOrchestrator:
    def __init__(self, session_store, event_bus):
        self.session_store = session_store
        self.event_bus = event_bus

    async def start_session(self, request: ZeroPromptStartRequest) -> ZeroPromptSession:
        # 1. 세션 생성
        # 2. 후보 풀 확보
        # 3. discovery_worker, build_worker task 시작
        # 4. zp.session.start 발행
        ...

    async def discovery_worker(self, session_id: str) -> None:
        # while session.running:
        #   if should_continue_discovery():
        #       video_id = next candidate
        #       await process_video(video_id)
        #   else:
        #       emit pause/resume as needed
        #       await asyncio.sleep(1)
        ...

    async def process_video(self, session_id: str, video_id: str) -> None:
        # transcript -> insight -> paper -> brainstorm -> compete -> verdict
        ...

    async def build_worker(self, session_id: str) -> None:
        # active_build_card_id 없을 때만 next build 시작
        # 기존 /api/run handoff 호출
        ...
```

### 5.4 Build handoff

오케스트레이터는 코드를 직접 생성하지 않는다. 선택된 카드를 기존 빌드 파이프라인으로 넘긴다.

```python
payload = {
    "prompt": build_prompt_from_card(card),
    "thread_id": build_thread_id,
    "constraints": "",
    "selected_flagship": "",
    "skip_council": True,
}
```

요구사항:
- 같은 `card_id`에 대한 중복 handoff 방지
- handoff 성공 시 `zp.build.start`
- 기존 빌드 SSE를 요약하여 `zp.build.progress`
- live URL 확보 시 `zp.build.complete`
- 실패 시 `build_failed` 상태와 `zp.build.failed`

### 5.5 API 계약

| 메서드 | 경로 | 설명 |
|------|------|------|
| `POST` | `/api/zero-prompt/start` | 세션 생성 및 스트림 시작 |
| `POST` | `/api/zero-prompt/{session_id}/actions` | `queue_build`, `pass_card`, `delete_card`, `pause`, `resume` |
| `GET` | `/api/zero-prompt/{session_id}` | 스냅샷 조회 |
| `GET` | `/api/zero-prompt/{session_id}/events` | 세션 전용 SSE |

bare route alias:
- `/zero-prompt/start`
- `/zero-prompt/{session_id}/actions`
- `/zero-prompt/{session_id}`
- `/zero-prompt/{session_id}/events`

### 5.6 상태 전이

```text
analyzing
  -> go_ready
  -> nogo

go_ready
  -> build_queued   (queue_build)
  -> passed         (pass_card)
  -> deleted        (delete_card; 실제 저장은 제거)

build_queued
  -> building       (queue head)
  -> passed         (사용자가 빌드 시작 전 큐에서 제거)

building
  -> deployed
  -> build_failed

nogo / passed / deployed / build_failed
  -> terminal
```

Phase 0 제약:
- `build_queued` 상태의 카드는 삭제 대신 `pass_card`만 허용한다.
- `building` 상태의 카드는 사용자 액션으로 취소하지 않는다.

## 6. 테스트 계획

- `test_start_session_emits_session_start`
- `test_discovery_pauses_at_goal_slots`
- `test_queue_build_fifo_order`
- `test_build_handoff_uses_skip_council_true`
- `test_pass_card_frees_slot_and_resumes_discovery`
- `test_session_snapshot_can_recover_ui_after_reconnect`
- `test_build_failure_marks_card_build_failed`

## 7. 검증 방법

- `pytest agent/tests/test_zero_prompt_orchestrator.py -v`
- 수동 검증:
  - `/zero-prompt`에서 Start 클릭
  - GO 카드 2개 생성 후 연속으로 `GO!` 클릭
  - 첫 카드는 `building`, 두 번째 카드는 `build_queued`
  - GO 슬롯이 다시 비면 탐색이 재개되는지 확인

## 8. 롤백 계획

- `agent/zero_prompt/orchestrator.py`, `agent/zero_prompt/queue_manager.py` 제거
- `agent/server.py`의 Zero-Prompt endpoint 제거
- 기존 `/run`, `/brainstorm`, `/dashboard/events` 동작 확인
