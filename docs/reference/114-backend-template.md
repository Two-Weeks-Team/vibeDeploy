# Task 114: 백엔드 템플릿화
상태: 미구현 | Phase 1 | 예상 시간: 6h
의존성: 112-deterministic-scaffold

## 1. 태스크 정의
FastAPI 백엔드 구조를 표준화된 템플릿으로 제공하여 LLM이 비즈니스 로직(routes.py, ai_service.py)에만 집중할 수 있도록 합니다. 이를 통해 백엔드 코드의 일관성을 높이고, DB 연결 및 CORS 설정과 같은 반복적인 오류를 방지합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `main.py`가 `routes.py`의 라우터를 자동으로 임포트하고 등록한다.
- [ ] AC-2: `models.py`가 `Base`, `SessionLocal`, `get_db`를 포함하여 생성된다.
- [ ] AC-3: `ai_service.py`는 DigitalOcean Inference 클라이언트를 사용하는 기본 구조를 포함한다.
- [ ] AC-4: `main.py` 단독 실행 시 `/health` 엔드포인트가 `200 OK`를 반환한다.
- [ ] AC-5: 모든 백엔드 파일은 `ast.parse()`를 통과하는 유효한 Python 코드여야 한다.

## 3. 변경 대상 파일
| 파일 | 변경 유형 | 설명 |
|------|---------|------|
| `agent/nodes/backend_scaffold.py` | 신규 | 백엔드 전용 템플릿 생성 로직 |
| `agent/nodes/blueprint.py` | 수정 | 백엔드 스캐폴드 호출 추가 |

## 4. 상세 구현
### 4.1 generate_backend_scaffold 함수 구현
```python
from typing import Any, Dict, List

def generate_backend_scaffold(blueprint: Dict[str, Any]) -> List[Dict[str, str]]:
    app_name = blueprint.get("app_name", "vibe-app")
    backend_config = blueprint.get("backend", {})
    
    scaffold_files = []
    
    # 1. agent/main.py (Router Integration)
    main_py = f"""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import Base, engine
try:
    from .routes import router as api_router
except ImportError:
    api_router = None

app = FastAPI(title="{app_name} API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if api_router:
    app.include_router(api_router, prefix="/api")

@app.get("/health")
def health():
    return {{"status": "ok"}}

@app.get("/")
def root():
    return {{"message": "Welcome to {app_name} API"}}
"""
    scaffold_files.append({"path": "agent/main.py", "content": main_py})

    # 2. agent/models.py (Standard SQLAlchemy)
    models_py = """import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
    scaffold_files.append({"path": "agent/models.py", "content": models_py})

    # 3. agent/ai_service.py (DO Inference Template)
    ai_service_py = f"""import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.digitalocean.com/v1/inference",
    api_key=os.getenv("DIGITALOCEAN_API_TOKEN")
)

MODEL = "{backend_config.get('ai_model', 'meta-llama-3.1-70b-instruct')}"

async def get_ai_response(prompt: str):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{{"role": "user", "content": prompt}}],
    )
    return response.choices[0].message.content
"""
    scaffold_files.append({"path": "agent/ai_service.py", "content": ai_service_py})

    return scaffold_files
```

## 5. 테스트 계획
### 단위 테스트
```python
import ast
from agent.nodes.backend_scaffold import generate_backend_scaffold

def test_backend_scaffold_syntax():
    blueprint = {"app_name": "test-app", "backend": {"ai_model": "llama-3.1"}}
    files = generate_backend_scaffold(blueprint)
    for f in files:
        if f["path"].endswith(".py"):
            ast.parse(f["content"]) # SyntaxError 발생 시 실패

def test_main_py_router_import():
    blueprint = {}
    files = generate_backend_scaffold(blueprint)
    main_py = next(f for f in files if f["path"] == "agent/main.py")
    assert "from .routes import router" in main_py["content"]
    assert "app.include_router" in main_py["content"]
```

## 6. 검증 방법
| 검증 항목 | 명령어 | 기대 결과 |
|---------|--------|---------|
| main.py 실행 가능 여부 | `cd agent && uvicorn main:app --port 8000` | 서버 정상 시작 |
| health 엔드포인트 확인 | `curl http://localhost:8000/health` | `{"status": "ok"}` |
| AI 서비스 구조 확인 | `grep "OpenAI" agent/ai_service.py` | 일치 |

## 7. 롤백 계획
- `agent/nodes/blueprint.py`에서 `generate_backend_scaffold` 호출을 제거하고 이전의 LLM 기반 백엔드 생성 로직으로 복구한다.
