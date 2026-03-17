# Task 135: 시드 데이터 생성기
상태: 미구현 | Phase 3 | 예상 시간: 3h
의존성: 없음 (독립)

## 1. 태스크 정의
vibeDeploy가 생성하는 앱의 완성도를 높이기 위해 도메인별 현실적인 목업 데이터를 생성하는 시스템을 구축합니다. "Lorem Ipsum"과 같은 무의미한 텍스트를 대체하여, 실제 서비스와 유사한 데이터를 제공함으로써 사용자 경험을 개선합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 5개 핵심 도메인(recipe, project, analytics, social, ecommerce)에 대한 현실적인 데이터 생성 로직 구현
- [ ] AC-2: 각 도메인별 최소 5개 이상의 아이템 생성 보장
- [ ] AC-3: 생성된 데이터가 유효한 JSON 형식을 따름
- [ ] AC-4: "lorem ipsum" 또는 "sample"과 같은 무의미한 문자열 사용 금지
- [ ] AC-5: Python에서 생성된 데이터를 TypeScript `const` 형식으로 변환하는 기능 포함

## 3. 변경 대상 파일
- `agent/nodes/build.py`: `generate_seed_data`, `to_typescript_const` 함수 추가
- `web/src/lib/seed-data.ts`: 생성된 시드 데이터가 저장될 대상 파일

## 4. 상세 구현

### 4.1 도메인별 데이터 생성기 (DOMAIN_GENERATORS)
```python
DOMAIN_GENERATORS = {
    "recipe": lambda count: [
        {"id": str(i), "name": f"지중해식 {['연어 스테이크', '파스타', '샐러드'][i%3]}", "difficulty": "중급", "time": "20분"}
        for i in range(count)
    ],
    "project": lambda count: [
        {"id": str(i), "task": f"{['UI 디자인 시스템', 'API 보안 점검', '마케팅 캠페인'][i%3]} 구축", "status": "진행중", "priority": "높음"}
        for i in range(count)
    ],
    "analytics": lambda count: [
        {"id": str(i), "metric": f"{['일일 활성 사용자', '서버 응답 시간', '전환율'][i%3]}", "value": f"{1000 + i*100}", "trend": "+12%"}
        for i in range(count)
    ],
    "social": lambda count: [
        {"id": str(i), "user": f"사용자_{i}", "content": f"오늘의 {['공부', '운동', '여행'][i%3]} 기록입니다!", "likes": i*5}
        for i in range(count)
    ],
    "ecommerce": lambda count: [
        {"id": str(i), "product": f"{['무선 헤드폰', '기계식 키보드', '게이밍 마우스'][i%3]}", "price": f"{50000 + i*5000}원", "stock": i+10}
        for i in range(count)
    ]
}
```

### 4.2 데이터 생성 및 변환 함수
```python
def generate_seed_data(domain: str, count: int = 10) -> list[dict]:
    generator = DOMAIN_GENERATORS.get(domain, DOMAIN_GENERATORS["project"])
    return generator(count)

def to_typescript_const(data: list[dict], name: str) -> str:
    import json
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    return f"export const {name} = {json_str} as const;\n"
```

## 5. 테스트 계획
- **유닛 테스트**: 5개 도메인을 각각 입력하여 `generate_seed_data`가 의도한 개수와 구조의 데이터를 반환하는지 확인
- **JSON 검증**: 생성된 데이터가 `json.loads`를 통해 정상적으로 파싱되는지 확인

## 6. 검증 방법
- `web/src/lib/seed-data.ts` 파일을 생성하고, 프론트엔드 컴포넌트에서 `import { projectData } from '@/lib/seed-data'`로 데이터를 불러와 화면에 렌더링되는지 확인
- 데이터에 "Lorem Ipsum"이 포함되어 있지 않은지 문자열 검색으로 확인

## 7. 롤백 계획
- 빈 배열(`[]`)을 반환하는 기본 시드 데이터 파일로 복구
- `agent/nodes/build.py`의 시드 데이터 생성 로직 비활성화
