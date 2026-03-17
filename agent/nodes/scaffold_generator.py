import ast
import json
from typing import Any

_NEXT_VERSION = "16.1.6"
_REACT_VERSION = "19.2.3"

_TSCONFIG = {
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
        "paths": {"@/*": ["./src/*"]},
    },
    "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
    "exclude": ["node_modules"],
}

_NEXT_CONFIG_TS = """\
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
"""

_POSTCSS_CONFIG_JS = """\
module.exports = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
"""

_GLOBALS_CSS = """\
@import "tailwindcss";
"""

_BASE_REQUIREMENTS = [
    "fastapi",
    "uvicorn[standard]",
    "sqlalchemy",
    "python-dotenv",
    "httpx",
    "psycopg2-binary",
]

_MAIN_PY_TEMPLATE = """\
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import Base, engine

try:
    from .routes import router as api_router
except ImportError:
    api_router = None

app = FastAPI(title="{app_name} API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

if api_router:
    app.include_router(api_router, prefix="/api")


@app.get("/health")
def health():
    return {{"status": "ok"}}


@app.get("/api")
def root():
    return {{"message": "Welcome to {app_name} API"}}
"""

_MODELS_PY = """\
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""


_AI_SERVICE_PY = """\
import os
import httpx

INFERENCE_URL = os.getenv("DIGITALOCEAN_INFERENCE_URL", "https://inference.do-ai.run/v1")
INFERENCE_KEY = os.getenv("DIGITALOCEAN_INFERENCE_KEY", "")


async def call_inference(prompt: str, model: str = "meta-llama/Llama-3.3-70B-Instruct") -> str:
    if not INFERENCE_KEY:
        return "AI service not configured"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{INFERENCE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {INFERENCE_KEY}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
"""


def generate_scaffold(blueprint: dict[str, Any]) -> dict[str, str]:
    app_name = str(blueprint.get("app_name", "vibe-app")).strip() or "vibe-app"
    extra_frontend_deps: dict[str, str] = {}
    extra_backend_deps: list[str] = []

    deps = blueprint.get("dependencies")
    if isinstance(deps, dict):
        frontend_deps = deps.get("frontend")
        if isinstance(frontend_deps, dict):
            extra_frontend_deps = {str(k): str(v) for k, v in frontend_deps.items()}
        backend_deps = deps.get("backend")
        if isinstance(backend_deps, list):
            extra_backend_deps = [str(d) for d in backend_deps if isinstance(d, str)]

    package_json = {
        "name": app_name,
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint",
        },
        "dependencies": {
            "next": _NEXT_VERSION,
            "react": _REACT_VERSION,
            "react-dom": _REACT_VERSION,
            "tailwindcss": "^4",
            "@tailwindcss/postcss": "^4",
            "lucide-react": "^0.500.0",
            "framer-motion": "^12.0.0",
            **extra_frontend_deps,
        },
    }

    main_py_content = _MAIN_PY_TEMPLATE.format(app_name=app_name)
    ast.parse(main_py_content)

    requirements_lines = list(_BASE_REQUIREMENTS) + extra_backend_deps

    return {
        "web/package.json": json.dumps(package_json, indent=2),
        "web/tsconfig.json": json.dumps(_TSCONFIG, indent=2),
        "web/next.config.ts": _NEXT_CONFIG_TS,
        "web/postcss.config.js": _POSTCSS_CONFIG_JS,
        "web/src/app/globals.css": _GLOBALS_CSS,
        "agent/main.py": main_py_content,
        "agent/models.py": _MODELS_PY,
        "agent/requirements.txt": "\n".join(requirements_lines) + "\n",
        "agent/ai_service.py": _AI_SERVICE_PY,
    }
