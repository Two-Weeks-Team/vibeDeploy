# vibeDeploy 구현 사양서 (Implementation Specifications)

이 문서는 vibeDeploy의 안정성과 코드 품질을 향상시키기 위한 핵심 컴포넌트들의 기술 사양 및 구현 가이드를 제공합니다. 모든 구현은 Python 3.12+, FastAPI, Next.js 15 및 LangGraph 프레임워크를 기반으로 합니다.

---

## 1. build_validator 노드 (Build Validation Node)

`build_validator`는 `code_evaluator`와 `deployer` 사이에 위치하여 생성된 코드가 실제 런타임 환경에서 실행 가능한지 검증합니다.

### 주요 기능
- 임시 디렉토리에 생성된 모든 파일 기록
- Python 파일에 대한 `ast.parse()` 구문 검사
- 백엔드: 의존성 설치 및 FastAPI 앱 로드 테스트
- 프론트엔드: `npm ci` 및 `npm run build` 실행
- 리소스 제한: 120초 타임아웃 및 512MB 메모리 제한

### 구현 코드 (Python)

```python
import ast
import subprocess
import tempfile
import shutil
import os
from pathlib import Path
from typing import Dict, List, Any

def build_validator(state: Dict[str, Any]) -> Dict[str, Any]:
    """생성된 코드의 빌드 및 실행 가능성을 검증하는 LangGraph 노드"""
    generated_files = state.get("generated_files", [])
    validation_errors = []
    passed = True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # 1. 파일 쓰기 및 AST 검증
        for file_info in generated_files:
            file_path = tmp_path / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            content = file_info["content"]
            file_path.write_text(content, encoding="utf-8")
            
            if file_info["path"].endswith(".py"):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    validation_errors.append(f"Syntax Error in {file_info['path']}: {e.msg} (Line {e.lineno})")
                    passed = False

        if not passed:
            return {"build_validation": {"passed": False, "errors": validation_errors[:3], "tier": "syntax"}}

        # 2. 백엔드 검증 (FastAPI)
        backend_path = tmp_path / "agent"
        if backend_path.exists():
            try:
                # 의존성 설치 (제한된 환경)
                subprocess.run(
                    ["pip", "install", "-r", "requirements.txt"],
                    cwd=backend_path, capture_output=True, timeout=60, check=True
                )
                # 앱 로드 테스트
                subprocess.run(
                    ["python", "-c", "from main import app"],
                    cwd=backend_path, capture_output=True, timeout=30, check=True,
                    env={**os.environ, "PYTHONPATH": str(backend_path)}
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                stderr = e.stderr.decode() if hasattr(e, "stderr") else str(e)
                validation_errors.append(f"Backend Load Failed: {stderr.splitlines()[:3]}")
                passed = False

        # 3. 프론트엔드 검증 (Next.js)
        web_path = tmp_path / "web"
        if web_path.exists() and passed:
            try:
                # npm ci 및 build 실행 (메모리 제한 설정)
                env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=512"}
                subprocess.run(
                    ["npm", "ci"], cwd=web_path, capture_output=True, timeout=120, check=True, env=env
                )
                subprocess.run(
                    ["npm", "run", "build"], cwd=web_path, capture_output=True, timeout=120, check=True, env=env
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                stderr = e.stderr.decode() if hasattr(e, "stderr") else str(e)
                validation_errors.append(f"Frontend Build Failed: {stderr.splitlines()[:3]}")
                passed = False

    return {
        "build_validation": {
            "passed": passed,
            "errors": validation_errors,
            "tier": "runtime" if passed else "build_failure"
        }
    }
```

---

## 2. 결정론적 스캐폴드 생성기 (Deterministic Scaffold Generator)

LLM이 반복적으로 생성하는 보일러플레이트 코드를 템플릿화하여 일관성을 유지하고 토큰을 절약합니다.

### 구현 코드 (Python)

```python
from typing import Dict, List, Any

def generate_scaffold(blueprint: Dict[str, Any]) -> List[Dict[str, str]]:
    """블루프린트를 기반으로 표준 프로젝트 구조 및 설정 파일을 생성"""
    app_name = blueprint.get("app_name", "vibe-app")
    deps = blueprint.get("dependencies", {})
    
    scaffold_files = []
    
    # 1. Frontend: package.json (Pinned Versions)
    package_json = {
        "name": app_name,
        "version": "0.1.0",
        "private": True,
        "scripts": {"dev": "next dev", "build": "next build", "start": "next start", "lint": "next lint"},
        "dependencies": {
            "next": "15.0.3",
            "react": "19.0.0-rc-6632212951-20241107",
            "react-dom": "19.0.0-rc-6632212951-20241107",
            "tailwindcss": "^3.4.1",
            "lucide-react": "^0.454.0",
            **deps.get("frontend", {})
        }
    }
    scaffold_files.append({"path": "web/package.json", "content": str(package_json).replace("'", '"')})

    # 2. Backend: main.py (FastAPI Boilerplate)
    main_py = f'''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import Base, engine

app = FastAPI(title="{app_name} API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health_check():
    return {{"status": "healthy"}}

@app.get("/")
def root():
    return {{"message": "Welcome to {app_name} API"}}
'''
    scaffold_files.append({"path": "agent/main.py", "content": main_py})

    # 3. Backend: models.py (SQLAlchemy Setup)
    models_py = '''from sqlalchemy import create_env, engine_from_config
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
'''
    scaffold_files.append({"path": "agent/models.py", "content": models_py})

    # 4. Backend: requirements.txt
    requirements = ["fastapi", "uvicorn", "sqlalchemy", "psycopg2-binary", "pydantic-settings"]
    requirements.extend(deps.get("backend", []))
    scaffold_files.append({"path": "agent/requirements.txt", "content": "\n".join(requirements)})

    return scaffold_files
```

---

## 3. 파일별 코드 생성 아키텍처 (Per-file Code Generation Architecture)

전체 코드를 한 번에 생성하는 대신, 파일 단위로 LLM을 호출하여 정확도를 높이고 개별 파일에 대한 즉각적인 검증을 수행합니다.

### 구현 코드 (Python)

```python
from typing import Dict, List, Any
from agent.llm import call_llm_with_fallback
import ast

async def generate_single_file(file_spec: Dict[str, Any], context: List[Dict[str, str]]) -> str:
    """특정 파일에 대한 코드를 생성하고 AST 검증을 수행"""
    prompt = f"""
    File Path: {file_spec['path']}
    Description: {file_spec['description']}
    Context: {context}
    API Contract: {file_spec.get('api_contract', 'N/A')}
    
    Generate only the code for this file. No markdown blocks.
    """
    
    for attempt in range(3):
        content = await call_llm_with_fallback(prompt, temperature=0.2 - (attempt * 0.1))
        if file_spec['path'].endswith(".py"):
            try:
                ast.parse(content)
                return content
            except SyntaxError:
                continue
        else:
            return content
    return "# Error: Failed to generate valid code after 3 attempts"

async def per_file_code_generator(state: Dict[str, Any]) -> Dict[str, Any]:
    """블루프린트의 파일 명세에 따라 순차적으로 코드를 생성"""
    blueprint = state["blueprint"]
    generated_files = state.get("generated_files", [])
    
    for file_spec in blueprint["file_specs"]:
        # 이미 생성된 파일은 건너뜀 (재시도 시 활용)
        if any(f["path"] == file_spec["path"] for f in generated_files):
            continue
            
        content = await generate_single_file(file_spec, generated_files)
        generated_files.append({"path": file_spec["path"], "content": content})
        
    return {"generated_files": generated_files}
```

---

## 4. 빌드 오류 피드백 루프 (Build Error Feedback Loop)

빌드 과정에서 발생한 실제 오류 메시지를 분석하여 `code_generator`에 전달함으로써 정밀한 코드 수정을 유도합니다.

### 구현 코드 (Python)

```python
def build_repair_prompt(failed_files: List[Dict[str, str]], errors: List[str]) -> str:
    """빌드 오류 정보를 바탕으로 수정 요청 프롬프트를 생성"""
    error_context = "\n".join(errors)
    file_contents = "\n\n".join([f"--- {f['path']} ---\n{f['content']}" for f in failed_files])
    
    return f"""
    The following files failed the build validation:
    
    [Errors]
    {error_context}
    
    [Current Code]
    {file_contents}
    
    Please fix the errors above. Return the complete corrected code for each file.
    Focus only on the reported errors and maintain the existing logic.
    """

async def code_repair_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """빌드 오류 발생 시 호출되는 복구 노드"""
    validation = state["build_validation"]
    errors = validation["errors"]
    generated_files = state["generated_files"]
    
    # 오류와 관련된 파일 식별 (단순화된 로직)
    failed_files = [f for f in generated_files if any(err in f["path"] for err in errors)]
    if not failed_files: failed_files = generated_files # 전체 대상
    
    repair_prompt = build_repair_prompt(failed_files, errors)
    # 온도 설정을 낮추어 결정론적 수정 유도
    repaired_code = await call_llm_with_fallback(repair_prompt, temperature=0.1)
    
    # 수정된 파일 반영 로직 (생략)
    return {"generated_files": updated_files, "build_attempt_count": state.get("build_attempt_count", 0) + 1}
```

---

## 5. 그래프 배선 변경 (Graph Wiring Changes)

`agent/graph.py`에서 `build_validator`를 삽입하고 루프 제어 로직을 추가하는 방법입니다.

### 구현 코드 (Python)

```python
from langgraph.graph import StateGraph, END

def route_build_validation(state: Dict[str, Any]):
    """빌드 결과에 따른 라우팅 결정"""
    validation = state.get("build_validation", {})
    attempt_count = state.get("build_attempt_count", 0)
    
    if validation.get("passed"):
        return "deployer"
    
    if attempt_count >= 3:
        return END # 최대 재시도 횟수 초과 시 종료
        
    return "code_generator" # 오류 피드백과 함께 재생성 노드로 이동

# 그래프 구성 예시
workflow = StateGraph(VibeDeployState)

workflow.add_node("code_generator", per_file_code_generator)
workflow.add_node("code_evaluator", code_evaluator)
workflow.add_node("build_validator", build_validator)
workflow.add_node("deployer", deployer)

# 배선 설정
workflow.add_edge("code_generator", "code_evaluator")
workflow.add_edge("code_evaluator", "build_validator")

workflow.add_conditional_edges(
    "build_validator",
    route_build_validation,
    {
        "deployer": "deployer",
        "code_generator": "code_generator",
        END: END
    }
)
```
