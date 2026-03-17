# Task 142: 파일별 AST 검증 (Per-file AST Validation)

## 1. 개요
파일별 코드 생성 직후 즉시 구문 검증을 수행하여, 오류가 있는 코드가 전체 프로젝트에 포함되는 것을 방지합니다. 검증 실패 시 해당 파일만 즉시 재생성하도록 설계합니다.

## 2. 주요 요구사항
- **즉시 검증**: 각 파일 생성 직후 `validate_generated_file` 함수를 호출합니다.
- **Python 검증**: `ast.parse()`를 사용하여 구문 오류를 감지합니다.
- **TSX/TS 검증**: 중괄호(`{}`) 및 대괄호(`[]`) 균형, `import` 문 유효성 등 기본적인 구문 체크를 수행합니다.
- **부분 재생성**: 검증 실패 시 전체 프로젝트가 아닌 해당 파일만 최대 3회 재생성합니다.

## 3. 구현 코드 (Python)

```python
import ast
import re
from typing import Dict, Any, Optional

class ValidationResult:
    def __init__(self, passed: bool, error: Optional[str] = None):
        self.passed = passed
        self.error = error

def validate_generated_file(path: str, content: str) -> ValidationResult:
    """파일 확장자에 따른 구문 검증 수행"""
    if path.endswith(".py"):
        return _validate_python(content)
    elif path.endswith((".tsx", ".ts", ".jsx", ".js")):
        return _validate_tsx(content)
    return ValidationResult(True) # 기타 파일은 통과

def _validate_python(content: str) -> ValidationResult:
    """Python ast.parse() 검증"""
    try:
        ast.parse(content)
        return ValidationResult(True)
    except SyntaxError as e:
        return ValidationResult(False, f"Python Syntax Error: {e.msg} at line {e.lineno}")

def _validate_tsx(content: str) -> ValidationResult:
    """TSX/TS 기본 구문 검증 (Brace Balance & Imports)"""
    # 1. 중괄호 균형 체크
    if content.count("{") != content.count("}"):
        return ValidationResult(False, "Brace imbalance: '{' and '}' counts do not match.")
    
    # 2. 대괄호 균형 체크
    if content.count("[") != content.count("]"):
        return ValidationResult(False, "Bracket imbalance: '[' and ']' counts do not match.")
        
    # 3. 빈 파일 체크
    if not content.strip():
        return ValidationResult(False, "Generated file is empty.")
        
    # 4. import 문 유효성 (간단한 정규식)
    if "import" in content and not re.search(r'import\s+.*\s+from\s+[\'"].*[\'"]', content):
        if "import '" not in content and 'import "' not in content:
             return ValidationResult(False, "Invalid import statement detected.")
             
    return ValidationResult(True)
```

## 4. 수용 기준 (Acceptance Criteria)
1. Python 파일의 구문 에러(예: 콜론 누락)를 즉시 감지하는가?
2. TSX 파일의 중괄호 불균형을 감지하는가?
3. 검증 실패 시 해당 파일만 재생성 로직으로 전달되는가?
4. 3회 연속 실패 시 기존 단일샷 `code_generator`로 폴백하거나 템플릿을 사용하는가?

## 5. 테스트 케이스
- **Test 1**: 의도적인 Python 구문 에러 주입 시 `passed=False` 반환 확인
- **Test 2**: TSX 파일에서 중괄호 하나를 삭제했을 때 에러 감지 확인
- **Test 3**: 정상적인 코드 입력 시 `passed=True` 반환 확인
- **Test 4**: 빈 문자열 입력 시 에러 감지 확인
