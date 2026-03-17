# Task 143: 파일별 재생성 로직 (Per-file Regeneration Logic)

## 1. 개요
파일별 AST 검증(Task 142)에서 실패한 파일에 대해, 이전 시도의 오류 정보를 바탕으로 정밀하게 재생성하는 로직을 구현합니다. 재시도 횟수가 늘어날수록 LLM의 온도를 낮추어 결정론적인 출력을 유도합니다.

## 2. 주요 요구사항
- **에러 피드백**: 재생성 프롬프트에 이전 시도에서 발생한 구체적인 에러 메시지를 포함합니다.
- **온도 감쇠 (Temperature Decay)**: 1차 시도 0.1, 2차 시도 0.05, 3차 시도 0.02로 온도를 점진적으로 낮춥니다.
- **폴백 전략**: 3회 연속 실패 시 해당 파일을 기본 템플릿으로 대체하거나, 기존 단일샷 `code_generator`로 전체 재생성을 시도합니다.
- **성공률 로깅**: 각 파일별 재생성 성공 여부와 시도 횟수를 로깅하여 성능을 모니터링합니다.

## 3. 구현 코드 (Python)

```python
async def regenerate_file(file_spec: Dict[str, Any], error: str, attempt: int, context: List[Dict]) -> str:
    """실패한 파일에 대해 에러 피드백을 포함하여 재생성"""
    # 온도 설정 (0.1 -> 0.05 -> 0.02)
    temp_map = {1: 0.1, 2: 0.05, 3: 0.02}
    temperature = temp_map.get(attempt, 0.02)
    
    prompt = _build_regen_prompt(file_spec, error, context)
    llm = get_llm(temperature=temperature)
    
    response = await ainvoke_with_retry(llm, [("system", CODE_GENERATION_BASE_SYSTEM_PROMPT), ("user", prompt)])
    return response.content

def _build_regen_prompt(file_spec: Dict[str, Any], error: str, context: List[Dict]) -> str:
    """재생성 전용 프롬프트 구성"""
    return f"""
    [RETRY REQUEST]
    The previous attempt to generate the following file failed validation.
    
    Path: {file_spec['path']}
    Description: {file_spec['description']}
    
    [Error from Previous Attempt]
    {error}
    
    [Instructions]
    Please fix the error above and provide the complete, corrected code for this file.
    Ensure all syntax is valid and all braces/brackets are balanced.
    Generate ONLY the code. No explanations.
    """
```

## 4. 수용 기준 (Acceptance Criteria)
1. 이전 시도의 에러 메시지가 재생성 프롬프트에 정확히 포함되는가?
2. 시도 횟수에 따라 LLM의 `temperature`가 의도한 대로 감소하는가?
3. 3회 실패 시 정의된 폴백(템플릿 대체 등)이 정상적으로 발동하는가?
4. 재생성 성공 시 해당 파일이 `generated_files` 리스트에 올바르게 업데이트되는가?

## 5. 테스트 케이스
- **Test 1**: 재생성 프롬프트에 에러 메시지가 포함되어 있는지 문자열 검사
- **Test 2**: 2차 시도 시 `temperature=0.05`가 적용되는지 확인
- **Test 3**: 3회 실패 후 폴백 로직이 호출되는지 확인
- **Test 4**: 재생성된 코드가 AST 검증을 통과하는지 확인
