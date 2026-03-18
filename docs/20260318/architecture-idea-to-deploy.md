# vibeDeploy Architecture: Idea to Deploy

> Generated: 2026-03-18 KST

## Entry Points

### Path A: Zero-Prompt Start (Autonomous Discovery)

```
[Start Button]
       │
       ▼
┌─── YouTube Discovery ────────────────────────────────────┐
│  1. YouTube API → 30 candidate videos                    │
│  2. (fallback) Gemini Grounding Discovery                │
│  3. (fallback) 15 hardcoded topics                       │
└──────────────────────────────────────────────────────────┘
       │
       ▼
┌─── Streaming Loop (one video at a time) ─────────────────┐
│                                                          │
│  transcript.py ── Extract transcript (youtube-transcript)│
│       │                                                  │
│  insight_extractor.py ── Gemini structured → AppIdea     │
│       │                                                  │
│  paper_search.py ── OpenAlex + arXiv paper search        │
│       │                                                  │
│  paper_brainstorm.py ── Idea + papers → EnhancedIdea     │
│       │                                                  │
│  competitive_analysis.py ── Brave + Exa parallel search  │
│       │                                                  │
│  verdict.py ── Score → GO (≥70) / NO-GO (<70)            │
│       │                                                  │
│  GO → Kanban "GO Ready" column                           │
│  NO-GO → Kanban "NO-GO / Passed" column                  │
│                                                          │
└─── Loop until 10 GO ideas ── remaining saved to session ─┘
       │
       ▼
┌─── User Actions ────────────────────────────────────────┐
│  [GO!] → queue_build → Build Pipeline trigger            │
│  [Pass] → Open slot → Auto-resume exploration            │
│  [Delete] → Remove NO-GO card                            │
└──────────────────────────────────────────────────────────┘
       │ GO! clicked
       ▼
```

### Path B: Direct Input (Vibe Council)

```
[Idea input] → POST /run
       │
       ▼
```

## Build Pipeline (LangGraph StateGraph — 17 nodes)

```
┌──────────────────────────────────────────────────────────┐
│  Phase 1: Idea Refinement                                │
│                                                          │
│  input_processor ── Normalize input + YouTube URL detect │
│       │                                                  │
│  inspiration_agent ── Similar services/competitor search │
│       │                                                  │
│  experience_agent ── UX perspective analysis             │
│       │                                                  │
│  enrich_idea ── Synthesized idea enrichment              │
└──────────┬───────────────────────────────────────────────┘
           │
           ├── skip_council=true (Zero-Prompt) ──────┐
           │                                         │
           ▼                                         │
┌──── Phase 2: Vibe Council (optional) ───────────┐  │
│                                                  │  │
│  fan_out_analysis ── 5 agents parallel           │  │
│  (Architect, Scout, Guardian, Catalyst, Advocate)│  │
│       │                                          │  │
│  cross_examination ── Structured debate          │  │
│       │                                          │  │
│  fan_out_scoring ── 5-axis scoring               │  │
│       │                                          │  │
│  strategist_verdict ── Vibe Score synthesis      │  │
│       │                                          │  │
│  decision_gate ─── GO (≥70) ──────────────────┐  │  │
│                 ├── CONDITIONAL (50-69) ──┐    │  │  │
│                 └── NO-GO (<50) → END     │    │  │  │
│                                          │    │  │  │
│  scope_down ← CONDITIONAL ───────────────┘    │  │  │
│       │                                       │  │  │
│  fix_storm → fan_out_analysis (re-debate loop)│  │  │
└───────────────────────────────────────────────┘  │  │
           │ GO                                    │  │
           ◄───────────────────────────────────────┘  │
           ◄──────────────────────────────────────────┘
           ▼
┌──── Phase 3: Document Generation ───────────────────────┐
│                                                          │
│  doc_generator ── PRD + Tech Spec + API Spec + DB Schema │
└──────────┬───────────────────────────────────────────────┘
           ▼
┌──── Phase 4: Code Generation ───────────────────────────┐
│                                                          │
│  blueprint_generator ── Deterministic scaffold (Layer 1) │
│    package.json, tsconfig.json, next.config.ts,          │
│    requirements.txt, main.py                             │
│       │                                                  │
│  prompt_strategist ── Per-file prompt optimization       │
│       │                                                  │
│  code_generator ── LLM business logic (Layer 4)          │
│    page.tsx, components/*.tsx, routes.py, ai_service.py  │
│    + OpenAPI types (Layer 2) + Design tokens (Layer 3)   │
│    + Seed data (Layer 5)                                 │
└──────────┬───────────────────────────────────────────────┘
           ▼
┌──── Phase 5: Verification Loop ─────────────────────────┐
│                                                          │
│  code_evaluator ── Code quality evaluation               │
│       │                                                  │
│       ├── Quality fail → code_generator (regenerate)     │
│       │                                                  │
│       ▼                                                  │
│  build_validator ── 4-Tier Build Validation               │
│    Tier 1: Syntax (ast.parse, brace-balance)             │
│    Tier 2: Import (importlib, package.json)              │
│    Tier 3: Docker build (npm run build in container)     │
│    Tier 4: Contract (OpenAPI vs FastAPI routes)          │
│       │                                                  │
│       ├── FAIL → stderr → code_generator (max 3x)       │
│       │          temperature: 0.10 → 0.05 → 0.02        │
│       │                                                  │
│       ├── 3x fail → END (build_failed)                   │
│       │                                                  │
│       ▼ PASS                                             │
└──────────┬───────────────────────────────────────────────┘
           ▼
┌──── Phase 6: Deploy ────────────────────────────────────┐
│                                                          │
│  deployer ── 3-step deployment                           │
│    1. GitHub repo creation + code push                   │
│    2. DO App Platform deploy (.do/app.yaml)              │
│    3. /health smoke test                                 │
│       │                                                  │
│       ▼                                                  │
│  LIVE URL: https://*.ondigitalocean.app                  │
└──────────────────────────────────────────────────────────┘
```

## Infrastructure

```
┌─────────────────────────────────────────────────────────┐
│               DigitalOcean App Platform                  │
│                                                         │
│  ┌─────────────┐    ┌──────────────────┐                │
│  │  Next.js 15  │    │  FastAPI Gateway  │               │
│  │  (web/)      │◄──►│  (agent/)         │               │
│  │  Dashboard   │SSE │  Session Mgmt     │               │
│  │  Zero-Prompt │    │  SSE Relay        │               │
│  │  Meeting     │    │  Build Queue      │               │
│  └──────────────┘    └────────┬─────────┘               │
│                               │                          │
│                     ┌─────────▼─────────┐                │
│                     │  Gradient ADK     │                │
│                     │  LangGraph Graph  │                │
│                     │  (17 nodes)       │                │
│                     └────────┬──────────┘                │
│                              │                           │
│         ┌────────┬───────┬───┴───┬──────────┐           │
│         ▼        ▼       ▼       ▼          ▼           │
│     PostgreSQL  Spaces  KB RAG  Traces  Inference       │
│     (lineage)  (S3)    (2 KBs) (full)  (LLM calls)     │
└─────────────────────────────────────────────────────────┘
```

## LangGraph Node Wiring (graph.py)

```
input_processor
    → inspiration_agent
        → experience_agent
            → enrich_idea
                ├── [skip_council] → doc_generator
                └── [council] → fan_out → run_council_agent (×5 parallel)
                                    → cross_examination
                                        → fan_out → score_axis (×5 parallel)
                                            → strategist_verdict
                                                → decision_gate
                                                    ├── GO → doc_generator
                                                    ├── CONDITIONAL → scope_down → doc_generator
                                                    │              → fix_storm → run_council_agent (loop)
                                                    └── NO-GO → END

doc_generator
    → blueprint_generator
        → prompt_strategist
            → code_generator
                → code_evaluator
                    ├── pass → build_validator
                    │              ├── PASS → deployer → END
                    │              ├── FAIL (≤3) → code_generator (retry)
                    │              └── FAIL (>3) → END
                    └── fail → code_generator (retry)
```

## Web Routes

```
/                    Landing (InputForm + Zero-Prompt link)
/zero-prompt         Zero-Prompt Dashboard (Kanban + Action Feed)
/meeting/:id         Vibe Council live debate (SSE)
/brainstorm/:id      Creative ideation (SSE)
/result/:id          Result + Deploy (Vibe Score, Code, Docs)
/dashboard           Ops dashboard (pipeline viz, history, charts)
```
