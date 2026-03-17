# Task 165: 논문 기반 브레인스톰 (v2)
상태: 미구현 | Phase 0 | 예상 시간: 4h
의존성: 163, 164

## 1. 태스크 정의

`novelty_strategist` 에이전트가 원본 앱 아이디어와 논문 메타데이터를 결합해 차별화 포인트를 강화한다. 이 단계는 새 아이디어를 재발명하는 것이 아니라, **원본 아이디어를 논문 근거로 업그레이드**하는 역할이다.

## 2. 담당 에이전트와 페르소나

- Agent ID: `novelty_strategist`
- Persona: 응용 연구자
- 원칙: 추상적인 미래 예측 대신, 논문에서 직접 이어지는 기능 강화만 제안한다.

## 3. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: `EnhancedIdea`를 반환한다.
- [ ] AC-2: `novel_features`, `scientific_backing`, `unexplored_angles`, `novelty_boost`를 포함한다.
- [ ] AC-3: `novelty_boost`는 0.0~0.3 범위다.
- [ ] AC-4: `zp.brainstorm.start`, `zp.brainstorm.complete` 이벤트를 발행한다.

## 4. 변경 대상 파일

- `agent/zero_prompt/paper_brainstorm.py` (신규)
- `agent/zero_prompt/schemas.py` (신규)
- `agent/zero_prompt/events.py` (신규)

## 5. 상세 구현

```python
class EnhancedIdea(AppIdea):
    novel_features: list[str]
    scientific_backing: str
    unexplored_angles: list[str]
    novelty_boost: float
```

## 6. 테스트 계획

- `test_brainstorm_with_papers_returns_enhanced_idea`
- `test_novelty_boost_is_bounded`
- `test_scientific_backing_mentions_source_paper`
- `test_brainstorm_events_are_emitted`

## 7. 검증 방법

- `pytest agent/tests/test_zero_prompt_paper_brainstorm.py -v`

## 8. 롤백 계획

- `agent/zero_prompt/paper_brainstorm.py` 제거
