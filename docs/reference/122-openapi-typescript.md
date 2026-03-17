# Task 122: openapi-typescript 통합
상태: 미구현 | Phase 2 | 예상 시간: 3h
의존성: 121

## 1. 태스크 정의
`openapi-typescript` 라이브러리를 사용하여 생성된 OpenAPI 스펙에서 TypeScript 타입을 자동으로 추출하는 파이프라인을 구축합니다. 이 타입은 프론트엔드 코드 생성 시 `src/types/api.d.ts` 파일로 주입됩니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `npx openapi-typescript` 명령어를 `subprocess`로 실행하여 타입을 생성한다.
- [ ] AC-2: 생성된 `.d.ts` 파일이 `frontend_code` 딕셔너리에 `src/types/api.d.ts` 경로로 포함되어야 한다.
- [ ] AC-3: 모든 OpenAPI 스키마가 TypeScript `interface` 또는 `type`으로 변환되어야 한다.
- [ ] AC-4: 생성된 타입 파일이 유효한 TypeScript 문법을 따라야 한다 (`tsc --noEmit` 통과).

## 3. 변경 대상 파일
- `agent/nodes/code_generator.py`: 타입 생성 로직 추가 및 파일 주입
- `agent/utils/codegen_helpers.py`: (신규) `openapi-typescript` 실행 래퍼 함수

## 4. 상세 구현

### generate_typescript_types 함수
```python
import subprocess
import tempfile
import os

def generate_typescript_types(openapi_json: str) -> str:
    """OpenAPI JSON을 TypeScript 타입 정의로 변환"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write(openapi_json)
        tmp_path = tmp.name
        
    try:
        # npx openapi-typescript 실행
        result = subprocess.run(
            ["npx", "openapi-typescript", tmp_path],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
```

### code_generator 통합
```python
def code_generator_node(state: VibeDeployState):
    openapi_spec = state.get("api_contract")
    
    # TypeScript 타입 생성
    ts_types = generate_typescript_types(openapi_spec)
    
    # 프론트엔드 코드에 주입
    frontend_code = state.get("frontend_code", {})
    frontend_code["src/types/api.d.ts"] = ts_types
    
    return {"frontend_code": frontend_code}
```

## 5. 테스트 계획
- `test_ts_type_generation`: 샘플 OpenAPI JSON을 입력으로 넣어 유효한 TypeScript 코드가 출력되는지 확인.
- `test_complex_schema_conversion`: 중첩된 객체 및 배열 스키마가 올바른 TypeScript 인터페이스로 변환되는지 검증.
- `test_npx_not_found_error`: `npx` 명령어가 없을 때 적절한 예외 처리가 발생하는지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_codegen_helpers.py` 실행
- 생성된 `src/types/api.d.ts` 파일을 VS Code에서 열어 타입 정의 확인
- `cd web && npx tsc --noEmit` 실행하여 타입 오류 여부 확인

## 7. 롤백 계획
- `code_generator.py`에서 `generate_typescript_types` 호출부를 주석 처리하고 수동 타입 정의 방식으로 복구.
