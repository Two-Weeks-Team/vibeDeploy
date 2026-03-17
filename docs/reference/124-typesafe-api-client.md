# Task 124: 타입 안전 API 클라이언트 템플릿
상태: 미구현 | Phase 2 | 예상 시간: 4h
의존성: 122

## 1. 태스크 정의
생성된 TypeScript 타입을 활용하여 프론트엔드에서 사용할 수 있는 타입 안전(Type-Safe) API 클라이언트를 생성합니다. 이 클라이언트는 `fetch`를 래핑하며, 모든 엔드포인트에 대해 자동 완성 및 타입 검사를 지원합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: OpenAPI 스펙의 모든 엔드포인트에 대해 타입 안전한 함수가 생성되어야 한다.
- [ ] AC-2: 요청(Request) 및 응답(Response) 타입이 `src/types/api.d.ts`와 일치해야 한다.
- [ ] AC-3: `NEXT_PUBLIC_API_URL` 환경변수를 기본 베이스 URL로 사용해야 한다.
- [ ] AC-4: 공통 에러 처리를 위한 `ApiError` 클래스가 포함되어야 한다.
- [ ] AC-5: 생성된 클라이언트 코드가 `tsc --noEmit`을 통과해야 한다.

## 3. 변경 대상 파일
- `agent/nodes/code_generator.py`: API 클라이언트 생성 로직 추가
- `agent/prompts/templates.py`: (신규) API 클라이언트 TypeScript 템플릿

## 4. 상세 구현

### API 클라이언트 템플릿 (TypeScript)
```typescript
import { paths } from "./types/api";

type Paths = keyof paths;

export class ApiError extends Error {
  constructor(public status: number, message: string, public data?: any) {
    super(message);
  }
}

async function apiRequest<P extends Paths, M extends keyof paths[P]>(
  path: P,
  method: M,
  options: {
    body?: any;
    params?: any;
    headers?: Record<string, string>;
  } = {}
): Promise<any> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || "";
  const url = new URL(`${baseUrl}${path}`);
  
  if (options.params) {
    Object.keys(options.params).forEach(key => 
      url.searchParams.append(key, options.params[key])
    );
  }

  const response = await fetch(url.toString(), {
    method: method as string,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new ApiError(response.status, "API Request Failed", data);
  }
  return data;
}

// 엔드포인트별 래퍼 함수 예시 (LLM이 생성)
export const api = {
  listRecipes: (params?: any) => apiRequest("/recipes", "get", { params }),
  createRecipe: (body: any) => apiRequest("/recipes", "post", { body }),
};
```

### generate_api_client 함수
```python
def generate_api_client(openapi_spec: str) -> str:
    """OpenAPI 스펙을 바탕으로 타입 안전 API 클라이언트 코드 생성"""
    # LLM을 사용하여 템플릿에 엔드포인트 래퍼 함수를 채워넣음
    prompt = f"다음 OpenAPI 스펙을 바탕으로 'api' 객체 래퍼 함수들을 생성하세요: {openapi_spec}"
    llm = get_llm()
    response = ainvoke_with_retry(llm, prompt)
    
    # 기본 템플릿과 결합하여 반환
    return BASE_TEMPLATE + response.content
```

## 5. 테스트 계획
- `test_api_client_generation`: 샘플 OpenAPI 스펙을 입력으로 넣어 유효한 TypeScript 클라이언트 코드가 생성되는지 확인.
- `test_type_consistency`: 생성된 클라이언트의 함수 시그니처가 `api.d.ts`의 정의와 일치하는지 검증.
- `test_error_handling`: `ApiError` 클래스가 올바르게 포함되고 예외 발생 시 정상 동작하는지 확인.

## 6. 검증 방법
- `pytest agent/tests/test_api_client_generator.py` 실행
- 생성된 `src/lib/api.ts` 파일을 VS Code에서 열어 자동 완성 기능 확인
- `cd web && npx tsc --noEmit` 실행하여 타입 오류 여부 확인

## 7. 롤백 계획
- `code_generator.py`에서 `generate_api_client` 호출부를 제거하고 기존의 수동 `fetch` 호출 방식으로 복구.
