# Task 123: datamodel-code-generator 통합
상태: 미구현 | Phase 2 | 예상 시간: 3h
의존성: 121

## 1. 태스크 정의
`datamodel-code-generator` 라이브러리를 사용하여 생성된 OpenAPI 스펙에서 백엔드용 Pydantic 모델을 자동으로 생성하는 파이프라인을 구축합니다. 생성된 모델은 `schemas.py` 파일로 백엔드 코드에 주입됩니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `datamodel-codegen` 명령어를 `subprocess`로 실행하여 Pydantic 모델을 생성한다.
- [ ] AC-2: 생성된 `schemas.py` 파일이 `backend_code` 딕셔너리에 포함되어야 한다.
- [ ] AC-3: 모든 OpenAPI 스키마가 Pydantic `BaseModel`로 변환되어야 한다.
- [ ] AC-4: 생성된 코드가 유효한 Python 문법을 따라야 한다 (`ast.parse()` 통과).
- [ ] AC-5: `from schemas import *`가 성공적으로 실행되어야 한다.

## 3. 변경 대상 파일
- `agent/nodes/code_generator.py`: Pydantic 모델 생성 로직 추가 및 파일 주입
- `agent/utils/codegen_helpers.py`: `datamodel-codegen` 실행 래퍼 함수 추가

## 4. 상세 구현

### generate_pydantic_models 함수
```python
import subprocess
import tempfile
import os

def generate_pydantic_models(openapi_json: str) -> str:
    """OpenAPI JSON을 Pydantic 모델 정의로 변환"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
        tmp.write(openapi_json)
        tmp_path = tmp.name
        
    try:
        # datamodel-codegen 실행
        result = subprocess.run(
            [
                "datamodel-codegen",
                "--input", tmp_path,
                "--input-file-type", "openapi",
                "--output-model-type", "pydantic_v2.BaseModel",
                "--target-python-version", "3.12"
            ],
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
    
    # Pydantic 모델 생성
    pydantic_models = generate_pydantic_models(openapi_spec)
    
    # 백엔드 코드에 주입
    backend_code = state.get("backend_code", {})
    backend_code["schemas.py"] = pydantic_models
    
    return {"backend_code": backend_code}
```

## 5. 테스트 계획
- `test_pydantic_model_generation`: 샘플 OpenAPI JSON을 입력으로 넣어 유효한 Pydantic 코드가 출력되는지 확인.
- `test_ast_parsing`: 생성된 `schemas.py` 코드가 `ast.parse()`를 통과하는지 검증.
- `test_import_validation`: 생성된 코드를 임시 파일로 저장하고 `import`가 성공하는지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_codegen_helpers.py` 실행
- 생성된 `schemas.py` 파일을 열어 Pydantic 모델 정의 확인
- `python -c "import ast; ast.parse(open('schemas.py').read())"` 실행하여 문법 오류 확인

## 7. 롤백 계획
- `code_generator.py`에서 `generate_pydantic_models` 호출부를 주석 처리하고 수동 모델 정의 방식으로 복구.
