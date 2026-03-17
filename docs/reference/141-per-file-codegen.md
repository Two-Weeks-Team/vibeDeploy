# Task 141: 파일별 코드 생성 아키텍처 (Per-file Code Generation Architecture)

## 1. 개요
기존의 `code_generator`는 전체 프로젝트 코드를 한 번에 생성하여 컨텍스트 창 제한 및 정확도 저하 문제가 있었습니다. 본 태스크에서는 블루프린트의 각 파일 명세를 순회하며 개별적으로 LLM을 호출하는 `per_file_code_generator` 노드를 추가합니다.

## 2. 주요 요구사항
- **노드 추가**: 기존 `code_generator.py`를 수정하지 않고 새로운 `per_file_code_generator` 노드 함수를 추가합니다.
- **환경변수 스위치**: `VIBEDEPLOY_USE_PER_FILE_CODEGEN=1` 설정 시에만 새로운 로직이 작동하며, 그렇지 않으면 기존 `code_generator`로 폴백합니다.
- **컨텍스트 주입**: 각 파일 생성 시 `api_contract`, `design_system`, 그리고 이전에 생성된 파일들의 내용을 컨텍스트로 제공합니다.
- **레이어 스킵**: Layer 1(스캐폴드), Layer 2(타입), Layer 3(디자인) 파일은 이미 존재하므로 Layer 4(비즈니스 로직) 파일만 LLM을 호출합니다.

## 3. 구현 코드 (Python)

```python
async def per_file_code_generator(state: VibeDeployState) -> Dict[str, Any]:
    """블루프린트의 파일 명세를 순회하며 개별적으로 코드를 생성하는 노드"""
    if os.getenv("VIBEDEPLOY_USE_PER_FILE_CODEGEN") != "1":
        return await legacy_code_generator(state) # 기존 노드로 위임

    blueprint = state["blueprint"]
    generated_files = state.get("generated_files", []) # 이미 생성된 레이어 파일들 포함
    
    # 생성 대상 파일 필터링 (generation: "llm"인 파일만)
    target_files = [f for f in blueprint.get("file_specs", []) if f.get("generation") == "llm"]
    
    for file_spec in target_files:
        # 중복 생성 방지
        if any(f["path"] == file_spec["path"] for f in generated_files):
            continue
            
        content = await _generate_single_file(file_spec, generated_files, blueprint)
        generated_files.append({"path": file_spec["path"], "content": content})
        
    return {"generated_files": generated_files}

async def _generate_single_file(file_spec: Dict[str, Any], context_files: List[Dict], blueprint: Dict) -> str:
    """단일 파일 생성 로직"""
    prompt = _build_file_prompt(file_spec, context_files, blueprint)
    llm = get_llm(temperature=0.1)
    
    response = await ainvoke_with_retry(llm, [("system", CODE_GENERATION_BASE_SYSTEM_PROMPT), ("user", prompt)])
    return response.content

def _build_file_prompt(file_spec: Dict[str, Any], context_files: List[Dict], blueprint: Dict) -> str:
    """파일별 최적화된 프롬프트 구성"""
    context_summary = "\n".join([f"- {f['path']}" for f in context_files])
    return f"""
    [File to Generate]
    Path: {file_spec['path']}
    Description: {file_spec['description']}
    
    [Project Context]
    App Name: {blueprint.get('app_name')}
    API Contract: {blueprint.get('api_contract')}
    Existing Files: {context_summary}
    
    Generate ONLY the code for this file. No explanations.
    """
```

## 4. 수용 기준 (Acceptance Criteria)
1. 각 파일이 독립적인 LLM 호출을 통해 생성되는가?
2. 출력 형식이 기존 `generated_files` 리스트 구조와 동일한가?
3. `VIBEDEPLOY_USE_PER_FILE_CODEGEN` 환경변수로 활성화/비활성화가 가능한가?
4. 특정 파일 생성 실패 시 해당 파일에 대한 재시도 로직이 동작하는가?

## 5. 테스트 케이스
- **Test 1**: 환경변수 미설정 시 기존 `code_generator` 호출 확인
- **Test 2**: 블루프린트의 `file_specs` 수만큼 LLM 호출이 발생하는지 확인
- **Test 3**: 생성된 파일 리스트에 Layer 1-3 파일과 신규 생성 파일이 모두 포함되는지 확인
- **Test 4**: 파일 경로와 설명이 프롬프트에 정확히 포함되는지 확인
