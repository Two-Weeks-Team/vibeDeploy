# Task 113: 빌드 에러 피드백 루프
상태: 미구현 | Phase 1 | 예상 시간: 4h
의존성: 111-build-validator

## 1. 태스크 정의
`build_validator`에서 발생한 실제 빌드 에러(stderr)를 분석하여 `code_generator`에 피드백으로 전달하는 루프를 구현합니다. 이를 통해 AI가 자신의 실수를 구체적인 에러 메시지를 바탕으로 수정할 수 있게 하며, 최대 3회의 재시도 기회를 부여합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `_trim_build_errors` 함수가 stderr에서 파일별 핵심 에러 3줄만 정확히 추출한다.
- [ ] AC-2: `_build_repair_prompt`가 에러 메시지와 실패한 파일의 현재 코드를 포함하여 생성된다.
- [ ] AC-3: 재시도 횟수가 증가함에 따라 LLM의 `temperature`가 `0.1 → 0.05 → 0.02`로 감소한다.
- [ ] AC-4: 3회 초과 실패 시 `END` 노드로 이동하여 배포를 중단한다.
- [ ] AC-5: `graph.py`에서 `build_validator` → `code_generator`로의 조건부 엣지가 정상 작동한다.

## 3. 변경 대상 파일
| 파일 | 변경 유형 | 설명 |
|------|---------|------|
| `agent/nodes/code_generator.py` | 수정 | 피드백 수용 및 repair 로직 추가 |
| `agent/graph.py` | 수정 | 루프 배선 및 라우팅 로직 추가 |
| `agent/state.py` | 수정 | `build_attempt_count` 필드 추가 |

## 4. 상세 구현
### 4.1 에러 트리밍 및 프롬프트 생성
```python
import re
from typing import Dict, List, Any

def _trim_build_errors(stderr: str) -> str:
    """stderr에서 핵심적인 에러 메시지만 추출 (파일별 최대 3줄)"""
    if not stderr:
        return "Unknown build error"
    
    lines = stderr.splitlines()
    trimmed = []
    error_count = 0
    
    for line in lines:
        if any(keyword in line.lower() for keyword in ["error:", "failed", "exception", "syntaxerror"]):
            trimmed.append(line.strip())
            error_count += 1
        if error_count >= 3:
            break
            
    return "\n".join(trimmed) if trimmed else "\n".join(lines[:3])

def _build_repair_prompt(errors: List[str], failing_files: List[Dict[str, str]]) -> str:
    """수정 요청을 위한 타겟팅 프롬프트 생성"""
    error_str = "\n".join(errors)
    file_context = ""
    for f in failing_files:
        file_context += f"--- FILE: {f['path']} ---\n{f['content']}\n\n"
        
    return f"""
Your previous code generation failed the build validation. 
Please fix the following errors and provide the complete corrected code for each file.

[BUILD ERRORS]
{error_str}

[CURRENT CODE]
{file_context}

INSTRUCTIONS:
1. Fix ONLY the reported errors.
2. Maintain the existing logic and structure.
3. Return the full file content for each corrected file.
"""
```

### 4.2 그래프 라우팅 로직 (agent/graph.py)
```python
def route_build_validation(state: VibeDeployState):
    validation = state.get("build_validation", {})
    attempt = state.get("build_attempt_count", 0)
    
    if validation.get("passed"):
        return "deployer"
    
    if attempt >= 3:
        print(f"Build failed after {attempt} attempts. Stopping.")
        return END
        
    return "code_generator"
```

## 5. 테스트 계획
### 단위 테스트
```python
from agent.nodes.code_generator import _trim_build_errors, _build_repair_prompt

def test_trim_build_errors():
    stderr = "Some noise\nError: Syntax error at line 10\nMore noise\nFailed to compile\nAnother error"
    result = _trim_build_errors(stderr)
    assert "Error: Syntax error" in result
    assert "Failed to compile" in result
    assert len(result.splitlines()) <= 3

def test_repair_prompt_contains_error():
    errors = ["SyntaxError: invalid syntax"]
    files = [{"path": "main.py", "content": "def foo"}]
    prompt = _build_repair_prompt(errors, files)
    assert "SyntaxError: invalid syntax" in prompt
    assert "main.py" in prompt
```

## 6. 검증 방법
| 검증 항목 | 명령어 | 기대 결과 |
|---------|--------|---------|
| 에러 트리밍 검증 | `pytest agent/tests/test_feedback.py -k trim` | Pass |
| 프롬프트 생성 검증 | `pytest agent/tests/test_feedback.py -k prompt` | Pass |
| 루프 횟수 제한 검증 | `pytest agent/tests/test_graph.py -k loop_limit` | 3회 시도 후 종료 확인 |

## 7. 롤백 계획
- `agent/graph.py`에서 `build_validator`의 조건부 엣지를 제거하고 `code_evaluator`의 기존 로직으로 복구한다.
