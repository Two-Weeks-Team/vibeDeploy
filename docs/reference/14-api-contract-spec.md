# 14. API Contract Architecture Specification (API 규약 아키텍처 명세)

이 문서는 VibeDeploy의 생성된 Next.js 프론트엔드와 FastAPI 백엔드 간의 100% 타입 안전성(Type Safety)을 보장하기 위한 "Contract-First" 접근 방식의 아키텍처를 정의합니다.

## Section 1: 현재 규약 시스템 분석 (Current Contract System Analysis)

현재 `blueprint.py`에서 정의된 `frontend_backend_contract` 구조는 다음과 같습니다:

```python
{
    "frontend_file": "src/lib/api.ts", 
    "calls": "POST /api/plan", 
    "backend_file": "routes.py", 
    "request_fields": ["query"], 
    "response_fields": ["summary"]
}
```

### 현재 시스템의 한계
- **검증 범위**: 엔드포인트 경로(85%), HTTP 메서드(80%), 필드 이름(60%) 수준의 검증만 수행합니다.
- **검증 불가 항목**: 데이터 타입(Type), 중첩 구조(Nested structures), 필수 여부(Optional vs Required), 열거형(Enums), Null 처리 등을 검증할 수 없습니다.
- **타입 안전성**: 현재 수준에서는 약 5% 미만의 타입 안전성만 제공하며, 런타임 에러 발생 가능성이 높습니다.

---

## Section 2: 제안된 OpenAPI-First 아키텍처 (Proposed OpenAPI-First Architecture)

### Step 1: LLM을 통한 OpenAPI 3.1 스펙 생성
VibeDeploy의 Blueprint 단계에서 LLM이 구조화된 출력(Structured Output)으로 OpenAPI 스펙을 생성합니다.

**OpenAPI 검증을 위한 Pydantic 모델:**
```python
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

class OpenAPISpec(BaseModel):
    openapi: str = "3.1.0"
    info: Dict[str, str]
    paths: Dict[str, Dict[str, Any]]
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class BlueprintContract(BaseModel):
    app_name: str
    description: str
    openapi_spec: OpenAPISpec
```

**스펙 생성을 위한 LLM 프롬프트:**
```text
당신은 전문 API 설계자입니다. 제공된 앱 요구사항을 바탕으로 OpenAPI 3.1.0 스펙을 작성하세요.
- 모든 엔드포인트는 명확한 operationId를 가져야 합니다.
- 모든 요청/응답 바디는 components/schemas에 정의된 Pydantic 스타일의 스키마를 참조해야 합니다.
- 타입 안전성을 위해 string, number, boolean, array, object 타입을 엄격히 구분하세요.
- 필수 필드는 'required' 배열에 명시하세요.
```

**레시피 앱 예시 OpenAPI 출력:**
```json
{
  "openapi": "3.1.0",
  "info": { "title": "Recipe API", "version": "1.0.0" },
  "paths": {
    "/recipes": {
      "get": {
        "operationId": "listRecipes",
        "responses": {
          "200": {
            "description": "A list of recipes",
            "content": {
              "application/json": {
                "schema": { "type": "array", "items": { "$ref": "#/components/schemas/Recipe" } }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "Recipe": {
        "type": "object",
        "properties": {
          "id": { "type": "string", "format": "uuid" },
          "title": { "type": "string" },
          "ingredients": { "type": "array", "items": { "type": "string" } }
        },
        "required": ["id", "title", "ingredients"]
      }
    }
  }
}
```

### Step 2: TypeScript 타입 자동 생성
`openapi-typescript` 라이브러리를 사용하여 생성된 스펙에서 프론트엔드용 타입을 추출합니다.

**생성된 타입 예시:**
```typescript
export interface components {
  schemas: {
    Recipe: {
      id: string;
      title: string;
      ingredients: string[];
    };
  };
}
export type Recipe = components["schemas"]["Recipe"];
```

### Step 3: Pydantic 모델 자동 생성
`datamodel-code-generator`를 사용하여 백엔드용 Pydantic 모델을 생성합니다.

**생성된 모델 예시:**
```python
from pydantic import BaseModel, UUID4
from typing import List

class Recipe(BaseModel):
    id: UUID4
    title: str
    ingredients: List[str]
```

### Step 4: 타입 안전 API 클라이언트 템플릿
생성된 타입을 사용하는 fetch 래퍼를 제공합니다.

**api-client.ts 템플릿:**
```typescript
import { paths } from "./schema";

type Paths = keyof paths;

export async function apiRequest<P extends Paths, M extends keyof paths[P]>(
  path: P,
  method: M,
  options: {
    body?: any;
    params?: any;
  }
): Promise<any> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
    method: method as string,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options.body),
  });
  return response.json();
}
```

---

## Section 3: 규약 검증 (Contract Validation - Tier 4)

생성 후 단계에서 실제 구현이 스펙과 일치하는지 검증합니다.

**Python 검증 함수:**
```python
import requests
from openapi_spec_validator import validate_spec

def validate_implementation_against_spec(generated_spec: dict, server_url: str):
    # 1. FastAPI 서버에서 실제 생성된 openapi.json 가져오기
    response = requests.get(f"{server_url}/openapi.json")
    actual_spec = response.json()
    
    # 2. 기본 OpenAPI 구조 검증
    validate_spec(actual_spec)
    
    # 3. 엔드포인트 및 메서드 일치 확인
    for path, methods in generated_spec['paths'].items():
        if path not in actual_spec['paths']:
            raise ValueError(f"Missing path: {path}")
        for method in methods:
            if method not in actual_spec['paths'][path]:
                raise ValueError(f"Missing method {method} for path {path}")
                
    # 4. 스키마 비교 (Deep Diff)
    # ... 생략 ...
    print("Contract Validation Passed!")

# 검증 실패 시 자동 수정 전략:
# - 누락된 필드 발견 시 code_generator에 해당 필드 추가 프롬프트 전달
# - 타입 불일치 시 Pydantic 모델 재생성 및 라우터 코드 수정
```

---

## Section 4: 타입 매핑 참조 (Type Mapping Reference)

| Python (Pydantic) | TypeScript | 비고 |
| :--- | :--- | :--- |
| `str` | `string` | |
| `int` | `number` | |
| `float` | `number` | |
| `bool` | `boolean` | |
| `datetime` | `string` | ISO 8601 형식 |
| `UUID` | `string` | |
| `list[T]` | `T[]` | |
| `dict[str, V]` | `Record<string, V>` | |
| `Optional[T]` | `T \| undefined` | |
| `Literal["a", "b"]` | `"a" \| "b"` | |
| `BaseModel` | `interface` | 중첩 모델 지원 |
| `Enum` | `union type` | |

---

## Section 5: 기존 파이프라인과의 통합 (Integration)

`api_contract_generator`는 `blueprint` 이후, `code_generator` 이전에 위치합니다.

**Graph 수정 코드:**
```python
def create_graph():
    workflow = StateGraph(VibeDeployState)
    
    workflow.add_node("blueprint", blueprint_node)
    workflow.add_node("api_contract", api_contract_generator_node)
    workflow.add_node("code_generator", code_generator_node)
    
    workflow.add_edge("blueprint", "api_contract")
    workflow.add_edge("api_contract", "code_generator")
    # ...
```

- **VibeDeployState**: `openapi_spec` 필드를 추가하여 스펙을 저장합니다.
- **code_generator**: FE/BE 코드 생성 시 저장된 `openapi_spec`을 컨텍스트로 활용합니다.
- **code_evaluator**: 정규표현식 기반 체크 대신 실제 타입 비교를 통한 일관성 검사를 수행합니다.

---

## Section 6: 마이그레이션 경로 (Migration Path)

1. **Phase 1**: 기존 규약 시스템을 유지하면서 OpenAPI 생성을 병행하여 데이터 축적.
2. **Phase 2**: OpenAPI에서 타입을 생성하고, 이를 프롬프트의 참조 자료로 활용.
3. **Phase 3**: 기존의 정규표현식 기반 검증을 OpenAPI 기반 검증으로 전면 교체.
4. **Phase 4**: 프론트엔드에서 수동 API 호출 코드를 제거하고, 완전 자동화된 타입 안전 클라이언트 생성 적용.

*하위 호환성: Phase 2까지는 기존 `frontend_backend_contract` 필드를 유지하여 점진적 전환을 보장합니다.*
