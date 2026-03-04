# vibeDeploy — Technical Implementation Plan

---

## Deployment Architecture

vibeDeploy는 **두 개의 독립적인 배포 단위**로 구성된다:

```
┌──────────────────────────────────────────────────────────────────┐
│                    vibeDeploy Architecture                        │
│                                                                  │
│  ┌─────────────────────────┐    ┌──────────────────────────────┐ │
│  │  A. Frontend            │    │  B. Agent Backend            │ │
│  │  DO App Platform        │    │  Gradient ADK                │ │
│  │                         │    │                              │ │
│  │  Next.js 15             │───▶│  Python + LangGraph          │ │
│  │  Static Site            │    │  @entrypoint                 │ │
│  │  .do/app.yaml           │◀───│  .gradient/agent.yml         │ │
│  │                         │SSE │                              │ │
│  │  https://vibedeploy     │    │  https://agents.do-ai.run/   │ │
│  │  .ondigitalocean.app    │    │  v1/{ws}/vibedeploy/run      │ │
│  └─────────────────────────┘    └──────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────┐    ┌──────────────────────────────┐ │
│  │  C. Database            │    │  D. Storage                  │ │
│  │  Managed PostgreSQL     │    │  DO Spaces (S3)              │ │
│  │  세션, 히스토리          │    │  코드, 문서, 이미지 에셋      │ │
│  └─────────────────────────┘    └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

**핵심:** Agent는 App Platform이 아니라 `gradient agent deploy`로 ADK 인프라에 배포.
ADK는 Public Preview 기간 동안 **무료** (컴퓨팅 호스팅 비용 없음).

---

## Tech Stack

### vibeDeploy 자체 (호스팅 앱)

| Layer | Technology | DO Service | 배포 방식 |
|-------|-----------|-----------|----------|
| **Frontend** | Next.js 15 (App Router) + shadcn/ui + Tailwind CSS | App Platform (Static Site) | `.do/app.yaml` |
| **Agent Backend** | Python 3.12 + Gradient ADK + LangGraph | **Gradient ADK (Agent Hosting)** | `gradient agent deploy` |
| **Database** | PostgreSQL 16 | Managed PostgreSQL | App Platform 연동 |
| **Storage** | 생성된 코드, 문서, 에셋 | Spaces (S3-compatible) | PyDo SDK |
| **AI Models** | Gradient AI Serverless Inference | Gradient Platform | API 호출 |
| **Knowledge Base** | DO 문서, 프레임워크 best practices | Gradient KB | RAG 검색 |

### 생성되는 사용자 앱

| Layer | Options | DO Service |
|-------|---------|-----------|
| **Frontend** | Next.js or Vite+React | App Platform |
| **Backend** | FastAPI or Express.js | App Platform |
| **Database** | PostgreSQL | Managed PostgreSQL (dev) |

---

## Project Structure

```
vibeDeploy/
├── web/                          # Next.js Frontend (→ App Platform)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          # Landing + Input form
│   │   │   ├── meeting/
│   │   │   │   └── [id]/page.tsx # Live Vibe Council Meeting View
│   │   │   └── result/
│   │   │       └── [id]/page.tsx # Result Dashboard
│   │   ├── components/
│   │   │   ├── input-form.tsx
│   │   │   ├── meeting-view.tsx   # Vibe Council 라이브 시각화
│   │   │   ├── council-member.tsx # 개별 에이전트 카드
│   │   │   ├── vibe-score.tsx     # Vibe Score™ 게이지 애니메이션
│   │   │   ├── decision-gate.tsx  # GO/CONDITIONAL/NO-GO
│   │   │   ├── cross-exam.tsx     # Cross-Examination 토론 뷰
│   │   │   ├── doc-viewer.tsx     # 생성된 문서 뷰어
│   │   │   ├── code-preview.tsx   # 코드 미리보기
│   │   │   └── deploy-status.tsx  # 배포 상태
│   │   └── lib/
│   │       ├── sse-client.ts      # SSE 이벤트 수신
│   │       └── api.ts             # Agent API 호출
│   ├── public/
│   ├── package.json
│   └── next.config.js
│
├── agent/                         # Gradient ADK Agent (→ gradient agent deploy)
│   ├── main.py                    # @entrypoint (ADK 진입점)
│   ├── graph.py                   # LangGraph StateGraph 정의
│   ├── state.py                   # VibeDeployState 스키마
│   ├── nodes/
│   │   ├── input_processor.py
│   │   ├── vibe_council.py        # Vibe Council 미팅 오케스트레이션
│   │   ├── decision_gate.py
│   │   ├── doc_generator.py
│   │   ├── code_generator.py
│   │   └── deployer.py
│   ├── council/                   # Vibe Council 에이전트 정의
│   │   ├── architect.py           # 🏗️ Technical Lead
│   │   ├── scout.py               # 🔭 Market Analyst
│   │   ├── guardian.py            # 🛡️ Risk Assessor
│   │   ├── catalyst.py            # ⚡ Innovation Officer
│   │   ├── advocate.py            # 🎯 UX Champion
│   │   └── strategist.py         # 🧭 Session Lead
│   ├── tools/
│   │   ├── youtube.py             # 트랜스크립트 추출
│   │   ├── web_search.py          # 시장 조사 (Scout용)
│   │   ├── github.py              # Repo 생성/push
│   │   ├── digitalocean.py        # DO API 래퍼
│   │   ├── knowledge_base.py      # KB RAG 검색
│   │   └── image_gen.py           # GPT-image-1 래퍼
│   ├── prompts/
│   │   ├── council_prompts.py     # Vibe Council 시스템 프롬프트
│   │   ├── doc_templates.py       # PRD/TechSpec 템플릿
│   │   └── code_templates.py      # 코드 생성 프롬프트
│   ├── templates/
│   │   ├── nextjs/                # Next.js 프로젝트 템플릿
│   │   ├── fastapi/               # FastAPI 프로젝트 템플릿
│   │   └── express/               # Express 프로젝트 템플릿
│   ├── .gradient/
│   │   └── agent.yml              # ADK 배포 설정 (3줄)
│   ├── requirements.txt
│   └── .env.example
│
├── .do/
│   └── app.yaml                   # Frontend-only App Platform 스펙
│
├── docs/
│   └── reference/                 # 해커톤 참조 문서
│
├── LICENSE                        # MIT
└── README.md
```

---

## Configuration Files

### A. Agent: `.gradient/agent.yml` (ADK 배포)

```yaml
agent_environment: production
agent_name: vibedeploy-agent
entrypoint_file: main.py
```

> 3줄. ADK가 나머지를 자동 처리: `POST /run` + `GET /health` 엔드포인트 생성, port 8080.

### B. Frontend: `.do/app.yaml` (App Platform 배포)

```yaml
name: vibedeploy
region: nyc

static_sites:
  - name: web
    github:
      repo: owner/vibeDeploy
      branch: main
      deploy_on_push: true
    source_dir: /web
    build_command: npm run build
    output_dir: .next
    envs:
      - key: NEXT_PUBLIC_AGENT_URL
        value: "https://agents.do-ai.run/v1/{workspace-id}/vibedeploy-agent"
        scope: BUILD_TIME

databases:
  - name: db
    engine: PG
    version: "16"
    production: false
```

> **주의:** `services` 섹션 없음. Agent는 App Platform이 아니라 ADK에 배포.

### C. Agent: `requirements.txt`

```
# Gradient ADK
gradient-adk>=0.0.8
gradient>=0.1.0
langchain-gradient>=0.1.0

# LangGraph
langgraph>=1.0.0

# YouTube Processing
yt-dlp>=2024.1.0

# HTTP Client
httpx>=0.27.0

# Environment
python-dotenv>=1.0.0

# DigitalOcean SDK
pydo>=0.3.0

# GitHub
PyGithub>=2.0.0
```

---

## API Design

### Agent Endpoints (ADK 자동 생성)

ADK `@entrypoint`가 자동 생성하는 엔드포인트:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `https://agents.do-ai.run/v1/{ws}/vibedeploy-agent/run` | 새 세션 시작 (text or YouTube URL) |
| POST | 같은 URL (with thread_id) | 기존 세션 재개 (CONDITIONAL 응답) |
| GET | `https://agents.do-ai.run/v1/{ws}/vibedeploy-agent/health` | 헬스체크 |

### Request/Response

**새 세션 시작:**
```json
// POST /run
{
  "prompt": "식당 예약 대기열을 관리하는 웹앱",
  "config": {
    "configurable": {
      "thread_id": "session-uuid-1234"
    }
  }
}
```

**SSE Response Stream:**
```
event: council.phase.start
data: {"phase": "input_processing", "message": "아이디어를 분석하고 있습니다..."}

event: council.agent.analyzing
data: {"agent": "architect", "status": "analyzing"}

event: council.agent.analysis
data: {"agent": "architect", "score": 85, "summary": "표준 CRUD + WebSocket으로 충분..."}

event: council.debate.start
data: {"pair": "architect_vs_guardian", "topic": "기술적 리스크"}

event: council.debate.exchange
data: {"challenger": "guardian", "response": "architect", "summary": "..."}

event: council.scoring.result
data: {"final_score": 63.85, "decision": "CONDITIONAL", "breakdown": {...}}

event: council.verdict
data: {"decision": "GO", "score": 78.5, "reasoning": "..."}

event: deploy.complete
data: {"url": "https://xxx.ondigitalocean.app", "github": "https://github.com/..."}
```

**CONDITIONAL 응답 (세션 재개):**
```json
// POST /run (resume via interrupt())
{
  "prompt": "네, 수정안으로 진행해주세요",
  "config": {
    "configurable": {
      "thread_id": "session-uuid-1234"  // 기존 세션 ID → MemorySaver로 상태 복원
    }
  }
}
```

---

## Gradient AI Configuration

### Knowledge Bases

| KB Name | Source | 용도 | Embedding Model |
|---------|--------|------|----------------|
| `do-docs` | DO 공식 문서 (web crawl) | App Platform spec, DB config 패턴 | gte-large-en-v1.5 |
| `framework-patterns` | Next.js, FastAPI, Express best practices | 코드 생성 참조 | gte-large-en-v1.5 |

### Model Access Keys

필요한 모델 (모두 `DIGITALOCEAN_INFERENCE_KEY`로 접근):

| 역할 | Model ID | 비용 (In/Out per 1M) |
|------|---------|---------------------|
| 🧭 Strategist | `openai-gpt-5.3-codex` | $1.75/$14.00 |
| 🏗️ Architect, 🔭 Scout, ⚡ Catalyst, 🎯 Advocate | `openai-gpt-5-mini` | $0.25/$2.00 |
| 🛡️ Guardian + Cross-Examination | `openai-gpt-5` | $1.25/$10.00 |
| Code/Doc Generation | `anthropic-claude-4.6-sonnet` | $3.00/$15.00 |
| Video Frame Analysis | `openai-gpt-4o` | $2.50/$10.00 |
| Image Generation | `openai-gpt-image-1` | $5.00/$40.00 |
| Fallback | `openai-gpt-5-nano` | $0.05/$0.40 |

### Agent Evaluation Dataset

```csv
prompt,expected_decision,expected_min_score
"온라인 메모장",GO,75
"AI 주식 자동매매",CONDITIONAL,50
"포트폴리오 웹사이트",GO,85
"실시간 다자간 화상회의 앱",CONDITIONAL,50
"블록체인 기반 투표 시스템",NO_GO,0
"레시피 공유 커뮤니티",GO,78
```

---

## Environment Variables

```bash
# Gradient AI — 모든 모델 접근에 사용
DIGITALOCEAN_INFERENCE_KEY=       # Gradient AI model access key

# DigitalOcean
DIGITALOCEAN_API_TOKEN=           # DO API 토큰 (사용자 앱 배포용)
DIGITALOCEAN_KB_ID=               # Knowledge Base UUID

# GitHub
GITHUB_TOKEN=                     # GitHub API 토큰 (repo 생성용)
GITHUB_ORG=                       # 생성될 repo의 organization

# YouTube
YOUTUBE_API_KEY=                  # YouTube Data API v3 키

# Web Search
SERPER_API_KEY=                   # Serper API (Scout 에이전트 시장 조사용)

# Database
DATABASE_URL=                     # PostgreSQL 연결 문자열 (App Platform 자동 바인딩)
```

---

## Database Schema (vibeDeploy 자체)

```sql
-- 세션 관리
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    input_text TEXT NOT NULL,
    input_type VARCHAR(10) NOT NULL,  -- 'text' | 'youtube'
    youtube_url TEXT,
    thread_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'processing',
    -- processing | analyzing | debating | scoring | generating | deploying | deployed | nogo | error
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vibe Council 분석 결과
CREATE TABLE council_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    agent_name VARCHAR(20) NOT NULL,  -- architect | scout | guardian | catalyst | advocate
    analysis JSONB NOT NULL,
    score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cross-Examination 토론 기록
CREATE TABLE cross_examinations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    debate_pair VARCHAR(50) NOT NULL,  -- architect_vs_guardian | scout_vs_catalyst | advocate_challenge
    exchanges JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vibe Score™ 결과
CREATE TABLE vibe_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    technical_feasibility INTEGER NOT NULL,  -- Architect (0-100)
    market_viability INTEGER NOT NULL,       -- Scout (0-100)
    innovation_score INTEGER NOT NULL,       -- Catalyst (0-100)
    risk_profile INTEGER NOT NULL,           -- Guardian (0-100, inverted in formula)
    user_impact INTEGER NOT NULL,            -- Advocate (0-100)
    final_score DECIMAL(5,2) NOT NULL,       -- Vibe Score™
    decision VARCHAR(15) NOT NULL,           -- GO | CONDITIONAL | NO_GO
    strategist_reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 배포 결과
CREATE TABLE deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    github_repo TEXT,
    do_app_id TEXT,
    live_url TEXT,
    status VARCHAR(20) NOT NULL,
    logs TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Frontend Key Pages

### 1. Landing Page (`/`)
- 히어로 섹션: "From idea to live app"
- 입력 폼: 텍스트 입력 또는 YouTube URL
- 최근 생성된 앱 갤러리 (선택적)

### 2. Vibe Council Meeting View (`/meeting/[id]`)
- **Phase 1:** 5개 에이전트 아바타 + 실시간 분석 카드 (병렬 등장)
- **Phase 2:** Cross-Examination 토론 뷰 (말풍선 UI)
  - Architect ↔ Guardian: 기술 리스크 공방
  - Scout ↔ Catalyst: 시장 현실 vs 혁신 잠재력
  - Advocate: 양측 도전
- **Phase 3:** Vibe Score™ 게이지 애니메이션 (각 축별 실시간 업데이트)
- **Phase 4:** Decision Gate 결과 표시 (GO/CONDITIONAL/NO-GO)
- CONDITIONAL 시: 스코프 축소안 확인 모달 (interrupt 기반)

### 3. Result Dashboard (`/result/[id]`)

**GO 결과:**
- 생성된 문서 탭 (PRD, Tech Spec, API Spec)
- 코드 미리보기 (파일 트리 + 구문 강조)
- 배포 상태 + 라이브 URL
- GitHub 레포 링크

**NO-GO 결과:**
- Strategist의 종합 분석 리포트
- 각 축별 상세 분석 + Cross-Examination 하이라이트
- 개선 방향 제안
- "수정해서 다시 시도" 버튼

---

## Estimated Token Usage & Cost

### 1회 실행 기준 (GO 시나리오)

| Phase | Model | Est. Input | Est. Output | Cost |
|-------|-------|-----------|------------|------|
| Input Processing | GPT-5 mini ($0.25/$2.00) | ~800 | ~500 | $0.001 |
| 🏗️ Architect Analysis | GPT-5 mini | ~2,000 | ~1,500 | $0.004 |
| 🔭 Scout Analysis | GPT-5 mini | ~2,000 | ~1,500 | $0.004 |
| 🛡️ Guardian Analysis | GPT-5 ($1.25/$10.00) | ~2,000 | ~1,500 | $0.018 |
| ⚡ Catalyst Analysis | GPT-5 mini | ~2,000 | ~1,500 | $0.004 |
| 🎯 Advocate Analysis | GPT-5 mini | ~2,000 | ~1,500 | $0.004 |
| Cross-Exam (3 rounds) | GPT-5 | ~6,000 | ~3,000 | $0.038 |
| 🧭 Strategist Verdict | GPT-5.3-Codex ($1.75/$14.00) | ~3,000 | ~1,000 | $0.019 |
| Doc Generation | Claude 4.6 Sonnet ($3/$15) | ~5,000 | ~12,000 | $0.195 |
| Code Gen (Frontend) | Claude 4.6 Sonnet | ~8,000 | ~25,000 | $0.399 |
| Code Gen (Backend) | Claude 4.6 Sonnet | ~8,000 | ~20,000 | $0.324 |
| Config Generation | GPT-5 mini | ~1,000 | ~1,500 | $0.004 |
| Image Gen (logo) | GPT-image-1 ($5/$40) | ~200 | ~500 | $0.021 |
| **TOTAL** | — | **~42,000** | **~71,000** | **~$1.04** |

### $200 크레딧 활용

```
ADK 호스팅: 무료 (Public Preview)
App Platform (frontend): ~$5/월
Managed PostgreSQL (dev): ~$12/월

추론 API 비용: ~$1.04/회
$200 크레딧 / $1.04 ≈ ~192회 배포 가능

해커톤 기간 (2주) 인프라: ~$17
나머지 $183 → 추론 API = ~176회 배포
개발 + 테스트 + 데모: 충분
```

---

## Security Considerations

| 영역 | 대책 |
|------|------|
| API 키 관리 | DO App Platform SECRET env vars (암호화 저장) |
| DIGITALOCEAN_INFERENCE_KEY | ADK 배포 시 `gradient secret set`으로 관리 |
| 사용자 입력 | LLM 프롬프트 인젝션 방지 (입력 sanitize) |
| 생성된 코드 | 기본 보안 패턴 적용 (CORS, helmet, rate limit) |
| GitHub 토큰 | 최소 권한 (repo 생성만), 별도 bot 계정 |
| DO API 토큰 | 배포 전용 토큰, write-only scope |
| 민감 정보 | 생성된 앱에 하드코딩 방지, env var 사용 강제 |

---

## Deploy Commands

### Agent 배포 (Gradient ADK)

```bash
# agent/ 디렉토리에서
cd agent/

# 환경 변수 설정
gradient secret set DIGITALOCEAN_INFERENCE_KEY=<key>
gradient secret set GITHUB_TOKEN=<token>
gradient secret set DIGITALOCEAN_API_TOKEN=<token>
gradient secret set DATABASE_URL=<url>

# 배포
gradient agent deploy

# 결과: https://agents.do-ai.run/v1/{workspace-id}/vibedeploy-agent/run
```

### Frontend 배포 (App Platform)

```bash
# 프로젝트 루트에서
doctl apps create --spec .do/app.yaml

# 또는 GitHub push 시 자동 배포 (deploy_on_push: true)
```

### 로컬 개발

```bash
# Agent (터미널 1)
cd agent/
pip install -r requirements.txt
gradient agent run --host 0.0.0.0 --port 8080

# Frontend (터미널 2)
cd web/
npm install
NEXT_PUBLIC_AGENT_URL=http://localhost:8080 npm run dev
```
