# Task 167: GO / NO-GO 판정 엔진 (v2)
상태: 미구현 | Phase 0 | 예상 시간: 4h
의존성: 163, 165, 166

## 1. 태스크 정의

`verdict_judge` 에이전트가 수집된 데이터에서 종합 점수를 계산하고 GO 또는 NO-GO를 판정한다. 이 태스크는 **점수 계산은 결정론적 코드**, **사유 문구는 짧은 LLM 보조**로 분리해 구현한다.

## 2. 담당 에이전트와 페르소나

- Agent ID: `verdict_judge`
- Persona: 투자 심사역
- 원칙: 점수는 규칙으로, 설명은 사람이 읽기 쉽게.

## 3. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: 종합 점수는 코드로 결정론적으로 계산한다.
- [ ] AC-2: 65점 이상이면 GO, 미만이면 NO-GO다.
- [ ] AC-3: `zp.go` 또는 `zp.nogo` 이벤트를 발행한다.
- [ ] AC-4: 판정 결과는 `score`, `decision`, `reason`, `reason_code`를 포함한다.
- [ ] AC-5: 카드 상태를 `go_ready` 또는 `nogo`로 갱신한다.

## 4. 변경 대상 파일

- `agent/zero_prompt/verdict.py` (신규)
- `agent/zero_prompt/schemas.py` (신규)
- `agent/zero_prompt/events.py` (신규)

## 5. 상세 구현

```python
class Verdict(BaseModel):
    score: int
    decision: Literal["GO", "NO_GO"]
    reason: str
    reason_code: Literal[
        "high_potential",
        "market_saturated",
        "weak_differentiation",
        "low_confidence",
        "weak_paper_backing",
        "technical_risk",
    ]
```

```python
market_opportunity_normalized = market_opportunity_score / 100
differentiation_normalized = differentiation_score / 100
novelty_boost_normalized = min(novelty_boost / 0.30, 1.0)

score = (
    confidence_score * 25
    + engagement_normalized * 20
    + market_opportunity_normalized * 25
    + novelty_boost_normalized * 15
    + differentiation_normalized * 15
)
```

구현 원칙:
- `score`와 `decision`은 코드로 계산한다.
- LLM은 `reason`과 `reason_code` 후보를 짧게 생성하는 용도로만 사용한다.
- 경계값 근처(60~70)는 판정은 유지하되 `reason`에 불확실성을 명시한다.

## 6. 테스트 계획

- `test_score_calculation_is_deterministic`
- `test_threshold_boundary_at_65`
- `test_reason_code_is_from_enum`
- `test_verdict_events_are_emitted`

## 7. 검증 방법

- `pytest agent/tests/test_zero_prompt_verdict.py -v`

## 8. 롤백 계획

- `agent/zero_prompt/verdict.py` 제거
