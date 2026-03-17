# Task 165: 논문 기반 브레인스톰 (v2)
상태: 미구현 | Phase 0 | 예상 시간: 4h
의존성: 163, 164

## 1. 태스크 정의
`gemini-3.1-flash-lite-preview`를 사용하여 추출된 아이디어와 검색된 논문 데이터를 결합하여 아이디어를 강화합니다. 논문의 과학적 근거를 바탕으로 새로운 기능을 제안하고, 아이디어의 참신도(novelty_boost)를 계산합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `gemini-3.1-flash-lite-preview`를 사용하여 아이디어 + 논문 기반 강화된 아이디어(EnhancedIdea)를 생성함.
- [ ] AC-2: 결과에 `novel_features`, `scientific_backing`, `unexplored_angles`, `novelty_boost` 필드가 포함되어야 함.
- [ ] AC-3: `novelty_boost`는 0.0~0.3 사이의 가산점으로 계산되어야 함.
- [ ] AC-4: 브레인스톰 시작(`zp.brainstorm.start`) 및 완료(`zp.brainstorm.complete`) 시 SSE 이벤트를 발행함.

## 3. 변경 대상 파일
- `agent/nodes/paper_brainstorm.py` (신규)
- `agent/state.py` (EnhancedIdea 모델 추가)

## 4. 상세 구현

### EnhancedIdea 모델 (agent/state.py)
```python
class EnhancedIdea(AppIdea):
    novel_features: list[str]
    scientific_backing: str
    unexplored_angles: list[str]
    novelty_boost: float
```

### Paper Brainstorm Node (agent/nodes/paper_brainstorm.py)
```python
from langchain_google_genai import ChatGoogleGenerativeAI
from agent.state import AppIdea, PaperMetadata, EnhancedIdea

async def brainstorm_with_papers(idea: AppIdea, papers: list[PaperMetadata]) -> EnhancedIdea:
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview")
    # 1. zp.brainstorm.start SSE 발행
    # 2. 아이디어와 논문 데이터를 프롬프트에 주입
    # 3. 강화된 기능 및 과학적 근거 추출
    # 4. zp.brainstorm.complete SSE 발행
    # 5. EnhancedIdea 객체 반환
    pass
```

## 5. 테스트 계획
- `test_brainstorm_enhancement`: 논문 데이터가 주어졌을 때 아이디어가 구체화되는지 확인.
- `test_novelty_boost_range`: 가산점이 0.0~0.3 범위 내에서 생성되는지 확인.
- `test_scientific_backing_content`: 논문의 제목이나 연도가 근거 문자열에 포함되는지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_paper_brainstorm.py` 실행.
- 강화된 아이디어의 `novel_features`가 원본 아이디어와 차별화되는지 샘플링 검사.

## 7. 롤백 계획
- `git checkout docs/reference/165-paper-brainstorm.md`
- `agent/nodes/paper_brainstorm.py` 삭제.
