# Task 125: 계약 검증 (Tier 4)
상태: 미구현 | Phase 2 | 예상 시간: 6h
의존성: 111, 121

## 1. 태스크 정의
`build_validator`의 Tier 4 검증 단계로, 실제 구현된 FastAPI 서버가 원본 OpenAPI 스펙과 일치하는지 런타임 수준에서 검증합니다. 서버를 임시로 시작하여 `/openapi.json`을 추출하고, 이를 원본 스펙과 비교하여 불일치를 감지합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 모든 엔드포인트 경로와 HTTP 메서드가 원본 스펙과 일치해야 한다.
- [ ] AC-2: 요청/응답 스키마 구조(필드 이름, 타입)가 원본 스펙과 일치해야 한다.
- [ ] AC-3: 불일치 감지 시 구체적인 오류 메시지(누락된 엔드포인트, 타입 불일치 등)를 반환해야 한다.
- [ ] AC-4: 불일치 시 자동 수정 전략(누락 엔드포인트 추가, 스키마 재생성)을 트리거해야 한다.
- [ ] AC-5: 전체 검증 프로세스는 10초 이내에 완료되어야 한다.

## 3. 변경 대상 파일
- `agent/nodes/build_validator.py`: Tier 4 검증 로직 추가
- `agent/utils/contract_checker.py`: (신규) OpenAPI 비교 유틸리티

## 4. 상세 구현

### validate_api_contract 함수
```python
import requests
import subprocess
import time
import os

def validate_api_contract(openapi_spec: str, backend_code: Dict[str, str]) -> Dict[str, Any]:
    """FastAPI 서버를 실행하여 실제 OpenAPI 스펙과 비교 검증"""
    # 1. 임시 서버 실행 (Uvicorn)
    # ... (생략: 임시 파일 저장 및 subprocess 실행 로직)
    
    try:
        # 2. 실제 생성된 openapi.json 가져오기
        response = requests.get("http://localhost:8001/openapi.json", timeout=5)
        actual_spec = response.json()
        
        # 3. 원본 스펙과 비교
        expected_spec = json.loads(openapi_spec)
        diffs = compare_schemas(expected_spec, actual_spec)
        
        if diffs:
            return {"status": "fail", "errors": diffs}
        return {"status": "pass"}
    finally:
        # 4. 서버 종료 및 임시 파일 삭제
        pass
```

### compare_schemas 함수
```python
def compare_schemas(expected: dict, actual: dict) -> List[str]:
    """두 OpenAPI 스펙 간의 차이점 분석"""
    errors = []
    
    # 엔드포인트 및 메서드 일치 확인
    for path, methods in expected['paths'].items():
        if path not in actual['paths']:
            errors.append(f"Missing path: {path}")
            continue
        for method in methods:
            if method not in actual['paths'][path]:
                errors.append(f"Missing method {method} for path {path}")
                
    # 스키마 구조 비교 (Deep Diff)
    # ... (생략: components/schemas 비교 로직)
    
    return errors
```

## 5. 테스트 계획
- `test_contract_validation_pass`: 일치하는 스펙과 코드를 입력으로 넣어 검증 통과 확인.
- `test_missing_endpoint_detection`: 엔드포인트가 누락된 코드를 입력으로 넣어 오류 감지 확인.
- `test_schema_mismatch_detection`: 필드 타입이 다른 코드를 입력으로 넣어 오류 감지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_contract_checker.py` 실행
- `build_validator` 노드 실행 시 로그에서 Tier 4 검증 결과 확인

## 7. 롤백 계획
- `build_validator.py`에서 Tier 4 검증 호출부를 주석 처리하고 Tier 3(정적 분석)까지만 수행하도록 복구.
