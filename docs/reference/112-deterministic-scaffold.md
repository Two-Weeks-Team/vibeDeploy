# Task 112: 결정론적 스캐폴드 분리

> **Implementation Note**: The production scaffold uses Next.js 16.1.6 / React 19.2.3 (updated per issue #35 discussion). The versions below reflect the original spec.

상태: 미구현 | Phase 1 | 예상 시간: 4h
의존성: 없음

## 1. 태스크 정의
LLM이 매번 생성할 필요가 없는 보일러플레이트 파일 8개를 템플릿화하여 결정론적으로 생성합니다. 이를 통해 빌드 안정성을 확보하고, LLM의 토큰 사용량을 줄이며, 생성 속도를 향상시킵니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: `package.json`의 `next` 버전이 `15.0.3`으로 고정되어 생성된다.
- [ ] AC-2: `main.py`는 `ast.parse()`를 통과하는 유효한 Python 코드여야 한다.
- [ ] AC-3: `models.py`는 `postgres://`를 `postgresql://`로 자동 수정하는 로직을 포함한다.
- [ ] AC-4: `next.config.ts`는 `standalone` 출력 및 `/api` 리라이트 설정을 포함한다.
- [ ] AC-5: 생성된 8개 파일 모두 유효한 JSON/Python/TS 형식이어야 한다.

## 3. 변경 대상 파일
| 파일 | 변경 유형 | 설명 |
|------|---------|------|
| `agent/nodes/scaffold_generator.py` | 신규 | 스캐폴드 생성 로직 구현 |
| `agent/nodes/blueprint.py` | 수정 | 스캐폴드 생성 함수 호출 추가 |

## 4. 상세 구현
### 4.1 generate_scaffold 함수 구현
```python
import json
from typing import Any, Dict, List

def generate_scaffold(blueprint: Dict[str, Any]) -> List[Dict[str, str]]:
    app_name = blueprint.get("app_name", "vibe-app")
    deps = blueprint.get("dependencies", {})
    theme = blueprint.get("theme_tokens", {})
    
    scaffold_files = []
    
    # 1. web/package.json
    package_json = {
        "name": app_name,
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint"
        },
        "dependencies": {
            "next": "15.0.3",
            "react": "19.0.0-rc-6632212951-20241107",
            "react-dom": "19.0.0-rc-6632212951-20241107",
            "tailwindcss": "3.4.17",
            "lucide-react": "0.454.0",
            "framer-motion": "11.12.0",
            **deps.get("frontend", {})
        }
    }
    scaffold_files.append({"path": "web/package.json", "content": json.dumps(package_json, indent=2)})

    # 2. web/tsconfig.json
    tsconfig = {
        "compilerOptions": {
            "target": "ES2017",
            "lib": ["dom", "dom.iterable", "esnext"],
            "allowJs": True,
            "skipLibCheck": True,
            "strict": True,
            "noEmit": True,
            "esModuleInterop": True,
            "module": "esnext",
            "moduleResolution": "bundler",
            "resolveJsonModule": True,
            "isolatedModules": True,
            "jsx": "preserve",
            "incremental": True,
            "plugins": [{"name": "next"}],
            "paths": {"@/*": ["./src/*"]}
        },
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        "exclude": ["node_modules"]
    }
    scaffold_files.append({"path": "web/tsconfig.json", "content": json.dumps(tsconfig, indent=2)})

    # 3. web/next.config.ts
    next_config = f"""import type {{ NextConfig }} from "next";

const nextConfig: NextConfig = {{
  output: "standalone",
  async rewrites() {{
    return [
      {{
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      }},
    ];
  }},
}};

export default next_config;
"""
    scaffold_files.append({"path": "web/next.config.ts", "content": next_config})

    # 4. agent/requirements.txt
    requirements = [
        "fastapi", "uvicorn", "sqlalchemy", "python-dotenv", "httpx", "openai", "psycopg2-binary"
    ]
    requirements.extend(deps.get("backend", []))
    scaffold_files.append({"path": "agent/requirements.txt", "content": "\n".join(requirements)})

    # 5. agent/main.py
    main_py = f"""from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import Base, engine

app = FastAPI(title="{app_name} API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {{"status": "ok"}}

@app.get("/")
def root():
    return {{"message": "Welcome to {app_name} API"}}
"""
    scaffold_files.append({"path": "agent/main.py", "content": main_py})

    # 6. agent/models.py
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

    return scaffold_files
```

## 5. 테스트 계획
### 단위 테스트
```python
import ast
import json
from agent.nodes.scaffold_generator import generate_scaffold

def test_generate_scaffold_package_json():
    blueprint = {"app_name": "test-app"}
    files = generate_scaffold(blueprint)
    pkg = next(f for f in files if f["path"] == "web/package.json")
    data = json.loads(pkg["content"])
    assert data["name"] == "test-app"
    assert data["dependencies"]["next"] == "15.0.3"

def test_generate_scaffold_python_syntax():
    blueprint = {}
    files = generate_scaffold(blueprint)
    main_py = next(f for f in files if f["path"] == "agent/main.py")
    ast.parse(main_py["content"]) # SyntaxError 발생 시 테스트 실패
```

## 6. 검증 방법
| 검증 항목 | 명령어 | 기대 결과 |
|---------|--------|---------|
| package.json 버전 확인 | `grep '"next": "15.0.3"' web/package.json` | 일치 |
| main.py 구문 검사 | `python -m py_compile agent/main.py` | 성공 |
| models.py DB URL 변환 | `pytest agent/tests/test_scaffold.py -k db_url` | Pass |

## 7. 롤백 계획
- `agent/nodes/blueprint.py`에서 `generate_scaffold` 호출을 제거하고 이전의 LLM 기반 생성 로직으로 복구한다.
