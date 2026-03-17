# Task 168: 스트리밍 루프 오케스트레이터 + API (v2)
상태: 미구현 | Phase 0 | 예상 시간: 8h
의존성: 161~167

## 1. 태스크 정의
전체 스트리밍 루프를 제어하고 큐를 관리하는 오케스트레이터를 구축합니다. `/run/zero-prompt` API를 통해 탐색을 시작하며, GO 대기 슬롯이 10개 미만일 때만 탐색 워커를 실행하고, 빌드 큐는 FIFO 방식으로 동시 1개만 처리하도록 관리합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `/run/zero-prompt` API 호출 시 스트리밍 탐색 루프가 성공적으로 시작됨.
- [ ] AC-2: 탐색 큐 관리: GO 대기 슬롯 < 10일 때 탐색 실행, = 10일 때 일시정지 로직 구현.
- [ ] AC-3: 빌드 큐 관리: FIFO 방식, 동시 실행 1개 제한, 완료 시 다음 대기열 자동 시작.
- [ ] AC-4: 영상 1개당 전체 파이프라인(transcript → insight → paper → brainstorm → compete → verdict) 순차 실행 보장.
- [ ] AC-5: 사용자 행동(GO! 클릭, 패스 클릭)에 따른 큐 상태 및 칸반 상태 업데이트 연동.

## 3. 변경 대상 파일
- `agent/orchestrator.py` (신규 또는 v2 업데이트)
- `agent/server.py` (`/run/zero-prompt` 엔드포인트 추가)
- `agent/queue_manager.py` (신규)

## 4. 상세 구현

### Queue Manager (agent/queue_manager.py)
```python
class QueueManager:
    def __init__(self):
        self.discovery_queue = []
        self.go_ready_list = [] # max 10
        self.build_queue = [] # FIFO
        self.is_building = False

    async def process_next_build(self):
        # 빌드 큐에서 하나 꺼내서 빌드 파이프라인 실행
        # 완료 후 다음 빌드 자동 시작
        pass
```

### Streaming Orchestrator (agent/orchestrator.py)
```python
async def run_zero_prompt_loop():
    # 1. YouTube Discovery로 후보 풀 확보
    # 2. while True:
    #    if len(go_ready_list) < 10:
    #        video_id = candidate_pool.pop(0)
    #        await process_video_pipeline(video_id)
    #    else:
    #        await asyncio.sleep(5) # 일시정지 대기
    pass
```

## 5. 테스트 계획
- `test_orchestrator_pause`: GO 대기 슬롯이 10개일 때 탐색이 멈추는지 확인.
- `test_build_queue_fifo`: 여러 개의 GO! 클릭 시 순서대로 빌드가 진행되는지 확인.
- `test_api_endpoint`: `/run/zero-prompt` 호출 시 200 OK 및 루프 시작 확인.

## 6. 검증 방법
- `pytest agent/tests/test_orchestrator.py` 실행.
- SSE 로그를 통해 탐색과 빌드가 의도한 큐 규칙에 따라 진행되는지 확인.

## 7. 롤백 계획
- `git checkout docs/reference/168-streaming-orchestrator.md`
- `agent/orchestrator.py`, `agent/server.py` 변경 사항 취소.
