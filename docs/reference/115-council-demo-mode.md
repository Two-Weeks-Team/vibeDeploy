# Task 115: Council 데모 모드 전환
상태: 미구현 | Phase 1 | 예상 시간: 3h
의존성: 없음

## 1. 태스크 정의
Vibe Council(6명의 AI 에이전트 토론)을 빌드 크리티컬 패스에서 분리하여 선택적으로 실행할 수 있도록 합니다. `skip_council` 플래그를 통해 데모 시에는 토론 과정을 건너뛰고 즉시 빌드로 진입하여 전체 파이프라인 시간을 40% 이상 단축합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `VibeDeployState`에 `skip_council: bool` 필드가 추가된다.
- [ ] AC-2: `skip_council=True`일 때 `enrich_idea` 노드 이후 바로 `doc_generator`로 라우팅된다.
- [ ] AC-3: `/run` API 엔드포인트에서 `skip_council` 파라미터를 수용한다.
- [ ] AC-4: `skip_council=False`일 때 기존의 Council 토론 및 채점 로직이 정상 작동한다.
- [ ] AC-5: Council을 건너뛰더라도 SSE 이벤트 스트리밍 구조는 유지되어 프론트엔드 UX가 깨지지 않는다.

## 3. 변경 대상 파일
| 파일 | 변경 유형 | 설명 |
|------|---------|------|
| `agent/state.py` | 수정 | `skip_council` 필드 추가 |
| `agent/graph.py` | 수정 | 조건부 라우팅 로직 추가 |
| `agent/server.py` | 수정 | API 파라미터 추가 및 전달 |

## 4. 상세 구현
### 4.1 상태 및 그래프 수정 (agent/graph.py)
```python
# agent/state.py
class VibeDeployState(TypedDict):
    # ... 기존 필드
    skip_council: bool

# agent/graph.py
def route_after_enrich(state: VibeDeployState):
    if state.get("skip_council"):
        return "doc_generator"
    return "run_council_agent"

def create_graph():
    workflow = StateGraph(PipelineState)
    # ... 노드 추가
    
    workflow.add_conditional_edges(
        "enrich_idea",
        route_after_enrich,
        {
            "doc_generator": "doc_generator",
            "run_council_agent": "run_council_agent"
        }
    )
    # ... 나머지 배선
```

### 4.2 API 엔드포인트 수정 (agent/server.py)
```python
@app.post("/run")
async def run_pipeline(
    request: Request,
    idea: str,
    skip_council: bool = False # 파라미터 추가
):
    initial_state = {
        "raw_input": idea,
        "skip_council": skip_council,
        # ... 초기 상태
    }
    # ... 그래프 실행 로직
```

## 5. 테스트 계획
### 통합 테스트
```python
import pytest
from agent.graph import create_graph

@pytest.mark.asyncio
async def test_skip_council_routing():
    graph = create_graph()
    state = {"skip_council": True, "raw_input": "test idea"}
    # enrich_idea 노드 실행 후 다음 노드 확인
    # (실제 테스트 코드는 graph.get_next_nodes() 등을 활용)
    pass

@pytest.mark.asyncio
async def test_no_skip_council_routing():
    graph = create_graph()
    state = {"skip_council": False, "raw_input": "test idea"}
    # run_council_agent로 가는지 확인
    pass
```

## 6. 검증 방법
| 검증 항목 | 명령어 | 기대 결과 |
|---------|--------|---------|
| Council 건너뛰기 확인 | `curl -X POST .../run?skip_council=true` | Council 노드 로그 없이 빌드 시작 |
| 기존 동작 확인 | `curl -X POST .../run?skip_council=false` | Council 토론 로그 출력 확인 |
| 파이프라인 시간 측정 | `time curl ...` | skip_council=true 시 40% 이상 단축 확인 |

## 7. 롤백 계획
- `agent/graph.py`에서 `route_after_enrich` 조건부 엣지를 제거하고 `enrich_idea` → `run_council_agent` 고정 엣지로 복구한다.
