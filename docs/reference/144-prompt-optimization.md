# Task 144: 파일별 프롬프트 최적화 (Per-file Prompt Optimization)

## 1. 개요
파일 유형별로 최적화된 프롬프트 템플릿을 사용하여 코드 생성의 정확도를 높이고 토큰 사용량을 최적화합니다. 각 파일 유형에 필요한 핵심 컨텍스트만 주입하여 LLM이 더 정밀한 코드를 생성하도록 유도합니다.

## 2. 주요 요구사항
- **유형별 템플릿**: `page.tsx`, `component.tsx`, `api.ts`, `routes.py`, `ai_service.py` 등 5가지 주요 파일 유형에 대한 전용 프롬프트를 정의합니다.
- **컨텍스트 주입**: 각 유형에 맞는 핵심 정보(디자인 토큰, OpenAPI 스펙, Pydantic 모델 등)를 선별적으로 주입합니다.
- **토큰 절약**: 불필요한 전체 프로젝트 컨텍스트를 제외하고, 해당 파일과 직접 연관된 정보만 포함하여 8K 토큰 이하로 유지합니다.

## 3. 구현 코드 (Python)

```python
FILE_TYPE_PROMPTS = {
    "page.tsx": """
    [Page Archetype]
    Layout: {layout_type}
    Design Tokens: {design_tokens}
    Components to Use: {component_list}
    
    Generate a Next.js 15 page component using Tailwind CSS.
    """,
    "component.tsx": """
    [Component Spec]
    Props Interface: {props_interface}
    Usage Example: {usage_example}
    Design Context: {design_context}
    
    Generate a reusable React component with Lucide icons.
    """,
    "api.ts": """
    [API Client Spec]
    OpenAPI Spec: {openapi_spec}
    Type Imports: {type_imports}
    Error Handling: Standard fetch with try-catch.
    
    Generate a frontend API client using fetch.
    """,
    "routes.py": """
    [Backend Route Spec]
    OpenAPI Spec: {openapi_spec}
    Pydantic Models: {pydantic_models}
    DB Session: Use Depends(get_db).
    
    Generate FastAPI route handlers.
    """,
    "ai_service.py": """
    [AI Service Spec]
    DO Inference Client: Use DigitalOcean Serverless Inference.
    Prompt Structure: {prompt_structure}
    
    Generate an AI service class for backend processing.
    """
}

def _build_file_prompt(file_spec: Dict[str, Any], context: Dict[str, Any]) -> str:
    """파일 유형을 감지하고 최적화된 프롬프트 템플릿 적용"""
    path = file_spec['path']
    template = ""
    
    if path.endswith("page.tsx"):
        template = FILE_TYPE_PROMPTS["page.tsx"].format(**context.get("page_ctx", {}))
    elif path.endswith("component.tsx"):
        template = FILE_TYPE_PROMPTS["component.tsx"].format(**context.get("comp_ctx", {}))
    elif path.endswith("api.ts"):
        template = FILE_TYPE_PROMPTS["api.ts"].format(**context.get("api_ctx", {}))
    elif path.endswith("routes.py"):
        template = FILE_TYPE_PROMPTS["routes.py"].format(**context.get("route_ctx", {}))
    elif "ai_service" in path:
        template = FILE_TYPE_PROMPTS["ai_service.py"].format(**context.get("ai_ctx", {}))
    else:
        template = "Generate code for this file: " + file_spec['description']
        
    return template + "\nGenerate ONLY the code. No explanations."
```

## 4. 수용 기준 (Acceptance Criteria)
1. 5가지 주요 파일 유형에 대해 서로 다른 프롬프트 템플릿이 존재하는가?
2. 각 프롬프트에 해당 파일 유형에 필요한 핵심 컨텍스트(예: `routes.py`의 경우 Pydantic 모델)가 주입되는가?
3. 생성된 프롬프트의 총 길이가 8K 토큰을 초과하지 않는가?
4. 불필요한 컨텍스트(예: 백엔드 파일 생성 시 프론트엔드 패키지 목록)가 제외되었는가?

## 5. 테스트 케이스
- **Test 1**: `page.tsx` 생성 시 디자인 토큰 정보가 프롬프트에 포함되는지 확인
- **Test 2**: `routes.py` 생성 시 `Depends(get_db)` 관련 지침이 포함되는지 확인
- **Test 3**: `ai_service.py` 생성 시 DigitalOcean Inference 관련 지침이 포함되는지 확인
- **Test 4**: 프롬프트 토큰 수 측정 (8K 이하 여부)
- **Test 5**: 알 수 없는 파일 유형에 대해 기본 프롬프트가 적용되는지 확인
