# Task 121: OpenAPI 스펙 생성 노드
상태: 미구현 | Phase 2 | 예상 시간: 4h
의존성: 111

## 1. 태스크 정의
`blueprint` 노드에서 생성된 `frontend_backend_contract`를 바탕으로 완전한 OpenAPI 3.1.0 스펙을 생성하는 새로운 LangGraph 노드를 구현합니다. 이 스펙은 이후 단계에서 TypeScript 타입 및 Pydantic 모델 생성의 원천(Source of Truth)이 됩니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 유효한 OpenAPI 3.1.0 JSON 문자열을 생성하고 `state["api_contract"]`에 저장한다.
- [ ] AC-2: `blueprint`에 정의된 모든 엔드포인트와 필드가 스펙에 포함되어야 한다.
- [ ] AC-3: 모든 요청/응답 스키마는 `components/schemas`를 참조하는 구조여야 한다.
- [ ] AC-4: 생성된 JSON은 `OpenAPISpec` Pydantic 모델의 검증을 통과해야 한다.
- [ ] AC-5: `graph.py`에서 `blueprint` -> `api_contract` -> `prompt_strategist` 순서로 흐름이 연결되어야 한다.

## 3. 변경 대상 파일
- `agent/state.py`: `VibeDeployState`에 `api_contract` 필드 추가
- `agent/nodes/api_contract_generator.py`: (신규) 노드 구현
- `agent/graph.py`: 워크플로우에 노드 및 에지 추가

## 4. 상세 구현

### OpenAPISpec Pydantic 모델
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

class OpenAPISpec(BaseModel):
    openapi: str = "3.1.0"
    info: Dict[str, str] = Field(..., description="API 제목 및 버전 정보")
    paths: Dict[str, Dict[str, Any]] = Field(..., description="엔드포인트 경로 및 메서드 정의")
    components: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {"schemas": {}}, 
        description="재사용 가능한 스키마 정의"
    )
```

### api_contract_generator 노드
```python
async def api_contract_generator_node(state: VibeDeployState) -> Dict[str, Any]:
    blueprint = state.get("blueprint", {})
    contracts = blueprint.get("frontend_backend_contract", [])
    
    prompt = API_CONTRACT_PROMPT.format(
        app_name=blueprint.get("app_name"),
        contracts=json.dumps(contracts, indent=2)
    )
    
    llm = get_llm(role="api_contract")
    response = await ainvoke_with_retry(llm, prompt, response_format={"type": "json_object"})
    spec_json = content_to_str(response.content)
    
    # 검증
    spec_data = json.loads(spec_json)
    OpenAPISpec(**spec_data)
    
    return {"api_contract": spec_json}
```

### 프롬프트 (API_CONTRACT_PROMPT)
```text
당신은 전문 API 설계자입니다. 제공된 blueprint 계약을 바탕으로 OpenAPI 3.1.0 스펙을 작성하세요.
앱 이름: {app_name}
계약 내용: {contracts}

규칙:
1. 모든 엔드포인트는 명확한 operationId를 가져야 합니다.
2. 모든 요청/응답 바디는 components/schemas에 정의된 스키마를 참조해야 합니다.
3. 타입 안전성을 위해 string, number, boolean, array, object 타입을 엄격히 구분하세요.
4. 필수 필드는 'required' 배열에 명시하세요.
5. JSON 객체만 반환하세요.
```

## 5. 테스트 계획
- `test_api_contract_generation`: 샘플 blueprint를 입력으로 넣어 유효한 OpenAPI JSON이 생성되는지 확인.
- `test_schema_reference_integrity`: 모든 path의 content가 components/schemas를 올바르게 참조하는지 검사.
- `test_pydantic_validation_failure`: 잘못된 구조의 OpenAPI 입력 시 Pydantic 에러가 발생하는지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_api_contract_generator.py` 실행
- 생성된 `api_contract`를 [Swagger Editor](https://editor.swagger.io/)에 붙여넣어 문법 오류 확인

## 7. 롤백 계획
- `agent/graph.py`에서 `api_contract` 노드를 제거하고 `blueprint`에서 `prompt_strategist`로 직접 연결하도록 에지 복구.
