# Task 167: GO / NO-GO 판정 엔진 (v2)
상태: 미구현 | Phase 0 | 예상 시간: 4h
의존성: 163, 165, 166

## 1. 태스크 정의
수집된 모든 데이터(Gemini 인사이트, 논문 브레인스톰, 경쟁사 분석)를 종합하여 아이디어의 최종 점수를 계산하고 GO 또는 NO-GO 판정을 내립니다. 판정 결과에 따라 SSE 이벤트를 발행하고 칸반 보드의 상태를 업데이트합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 정의된 공식에 따라 종합 점수(0~100)를 정확히 계산함.
- [ ] AC-2: 점수가 65점 이상이면 GO, 65점 미만이면 NO-GO로 판정함.
- [ ] AC-3: 판정 결과에 따라 `zp.go` 또는 `zp.nogo` SSE 이벤트를 발행함.
- [ ] AC-4: NO-GO 판정 시 구체적인 탈락 사유(시장 포화, 기술적 한계 등)를 포함함.
- [ ] AC-5: 판정 완료 후 칸반 보드의 해당 카드 상태를 `go_ready` 또는 `nogo`로 업데이트함.

## 3. 변경 대상 파일
- `agent/nodes/verdict_engine.py` (신규)
- `agent/state.py` (Verdict 모델 추가)

## 4. 상세 구현

### 종합 점수 공식
```
score = (
    confidence_score × 25 +       # Gemini 추출 품질
    engagement_normalized × 20 +   # 원본 영상 인기도
    market_opportunity × 25 +      # 경쟁사 분석 기회
    paper_novelty_boost × 15 +     # 논문 기반 참신도
    differentiation_score × 15     # 차별화 가능성
)
```

### Verdict Engine (agent/nodes/verdict_engine.py)
```python
from agent.state import EnhancedIdea, MarketAnalysis, Verdict

async def evaluate_verdict(idea: EnhancedIdea, market: MarketAnalysis) -> Verdict:
    # 1. 점수 계산 로직 수행
    # 2. GO (>=65) / NO-GO (<65) 판정
    # 3. zp.go / zp.nogo SSE 발행
    # 4. Verdict 객체 반환 (score, decision, reason 포함)
    pass
```

## 5. 테스트 계획
- `test_score_calculation`: 다양한 입력값에 대해 점수 공식이 올바르게 적용되는지 확인.
- `test_verdict_threshold`: 65점 경계값에서 GO/NO-GO 판정이 정확한지 확인.
- `test_sse_verdict_emission`: 판정 결과에 따른 SSE 이벤트 발행 확인.

## 6. 검증 방법
- `pytest agent/tests/test_verdict_engine.py` 실행.
- 로그를 통해 계산된 점수와 판정 결과가 논리적으로 타당한지 확인.

## 7. 롤백 계획
- `git checkout docs/reference/167-go-nogo-engine.md`
- `agent/nodes/verdict_engine.py` 삭제.
