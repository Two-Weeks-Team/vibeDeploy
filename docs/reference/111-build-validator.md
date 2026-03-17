# Task 111: build_validator 노드 구현
상태: 미구현 | Phase 1 | 예상 시간: 8h
의존성: 없음
ADR: A4 — **Docker SDK (컨테이너)** 사용 확정 (`docs/reference/19-architecture-decisions.md`)

## 1. 태스크 정의
`build_validator`는 `code_evaluator`와 `deployer` 사이에 위치하여 생성된 코드가 실제 런타임 환경에서 빌드 및 실행 가능한지 검증하는 LangGraph 노드입니다. **Docker 컨테이너** 내에서 실제 컴파일 및 빌드 프로세스를 수행하여 DO App Platform과 환경을 일치시키고 배포 성공률을 획기적으로 높입니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: Python 파일에 대한 `ast.parse()`를 통해 구문 에러(Syntax Error)를 100% 감지한다.
- [ ] AC-2: `pip install -r requirements.txt` 실패 시 에러를 감지하고 `passed=False`를 반환한다.
- [ ] AC-3: `npm run build` 실패 시 에러를 감지하고 `passed=False`를 반환한다.
- [ ] AC-4: 모든 빌드 단계 성공 시 `passed=True`와 `tier="runtime"`을 반환한다.
- [ ] AC-5: 각 빌드 단계는 120초 타임아웃이 적용되어야 하며, 초과 시 타임아웃 에러를 기록한다.
- [ ] AC-6: 에러 발생 시 `stderr`에서 핵심적인 첫 3줄만 추출하여 피드백으로 제공한다.

## 3. 변경 대상 파일
| 파일 | 변경 유형 | 설명 |
|------|---------|------|
| `agent/nodes/build_validator.py` | 신규 | 노드 로직 구현 |
| `agent/graph.py` | 수정 | 노드 추가 및 배선 |
| `agent/state.py` | 수정 | `build_validation` 상태 필드 추가 |

## 4. 상세 구현
### 4.1 build_validator 노드 구현
```python
import ast
import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import docker

from ..state import VibeDeployState

async def build_validator(state: VibeDeployState) -> Dict[str, Any]:
    """Docker 컨테이너 내에서 실제 빌드 검증을 수행한다. (ADR-A4)"""
    generated_files = state.get("generated_files", [])
    errors = []
    passed = True
    tier = "syntax"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 0. 파일 쓰기 + AST 사전 검증 (Docker 실행 전, 빠른 필터)
        for file_info in generated_files:
            f_path = tmp_path / file_info["path"]
            f_path.parent.mkdir(parents=True, exist_ok=True)
            f_path.write_text(file_info["content"], encoding="utf-8")

            if file_info["path"].endswith(".py"):
                try:
                    ast.parse(file_info["content"])
                except SyntaxError as e:
                    errors.append(f"Syntax Error in {file_info['path']}: {e.msg} (Line {e.lineno})")
                    passed = False

        if not passed:
            return {"build_validation": {"passed": False, "errors": errors[:3], "tier": "syntax"}}

        # 1. Docker 클라이언트 초기화
        client = docker.from_env()

        # 2. 백엔드 검증 (Python 컨테이너)
        tier = "backend_build"
        if (tmp_path / "requirements.txt").exists():
            result = _run_docker(
                client,
                image="python:3.12-slim",
                command="sh -c 'pip install -r requirements.txt -q && python -c \"from main import app\"'",
                volumes={str(tmp_path): {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                mem_limit="512m",
                timeout=120,
            )
            if not result["success"]:
                errors.append(f"Backend Build Failed:\n{_trim_errors(result['stderr'])}")
                passed = False

        # 3. 프론트엔드 검증 (Node.js 컨테이너)
        if passed:
            tier = "frontend_build"
            web_path = tmp_path / "web"
            if (web_path / "package.json").exists():
                # npm ci
                success, out = await _run_with_limits(
                    ["npm", "ci"], cwd=web_path, env={**os.environ, "NODE_OPTIONS": "--max-old-space-size=512"}
                )
                if not success:
                    errors.append(f"Frontend npm ci Failed: {_trim_errors(out)}")
                    passed = False
                
                # npm run build
                if passed:
                    success, out = await _run_with_limits(
                        ["npm", "run", "build"], cwd=web_path, env={**os.environ, "NODE_OPTIONS": "--max-old-space-size=512"}
                    )
                    if not success:
                        errors.append(f"Frontend Build Failed: {_trim_errors(out)}")
                        passed = False

    return {
        "build_validation": {
            "passed": passed,
            "errors": errors,
            "tier": "runtime" if passed else tier
        }
    }

async def _run_with_limits(cmd: List[str], cwd: Path, env: Dict = None, timeout: int = 120) -> (bool, str):
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode == 0:
                return True, ""
            return False, stderr.decode()
        except asyncio.TimeoutExpired:
            proc.kill()
            return False, "Process timed out after {}s".format(timeout)
    except Exception as e:
        return False, str(e)

def _trim_errors(stderr: str) -> str:
    lines = [line for line in stderr.splitlines() if line.strip()]
    return "\n".join(lines[:3])
```

## 5. 테스트 계획
### 단위 테스트
```python
import pytest
from agent.nodes.build_validator import build_validator

@pytest.mark.asyncio
async def test_build_validator_syntax_error():
    state = {"generated_files": [{"path": "agent/main.py", "content": "def invalid syntax"}]}
    result = await build_validator(state)
    assert result["build_validation"]["passed"] is False
    assert "Syntax Error" in result["build_validation"]["errors"][0]

@pytest.mark.asyncio
async def test_build_validator_pip_fail():
    state = {"generated_files": [
        {"path": "agent/requirements.txt", "content": "non-existent-package==9.9.9"},
        {"path": "agent/main.py", "content": "print('hello')"}
    ]}
    result = await build_validator(state)
    assert result["build_validation"]["passed"] is False
    assert "Pip Install Failed" in result["build_validation"]["errors"][0]

@pytest.mark.asyncio
async def test_build_validator_success():
    # Mocking or minimal valid files
    state = {"generated_files": [
        {"path": "agent/main.py", "content": "from fastapi import FastAPI\napp = FastAPI()"},
        {"path": "agent/requirements.txt", "content": "fastapi"}
    ]}
    # 실제 환경에서는 pip install이 필요하므로 테스트 환경에 따라 mock 처리 필요
    pass
```

## 6. 검증 방법
| 검증 항목 | 명령어 | 기대 결과 |
|---------|--------|---------|
| 구문 에러 감지 | `pytest agent/tests/test_build_validator.py -k syntax_error` | Pass |
| 타임아웃 동작 | `pytest agent/tests/test_build_validator.py -k timeout` | Pass (120초 후 실패 기록) |
| 전체 빌드 성공 | `pytest agent/tests/test_build_validator.py -k success` | Pass (passed=True) |

## 7. 롤백 계획
- `agent/graph.py`에서 `build_validator` 노드를 제거하고 `code_evaluator`에서 바로 `deployer`로 연결하도록 수정한다.
