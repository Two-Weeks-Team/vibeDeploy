# E2E Verification Report

> Verified: 2026-03-18 (commit 610deb5, deployment b7bc6f60)

## Deployment

| Item | Result |
|------|--------|
| Deployment ID | `b7bc6f60-92f7-41c0-96b6-cd411a6aa86c` |
| Phase | **ACTIVE** |
| Trigger | commit `610deb5` pushed to main |
| Previous failures | 2 (langchain-gradient version conflict, fixed in PR #189) |

## Endpoint Verification

### Core Endpoints (API component)

| Endpoint | Method | HTTP | Response |
|----------|--------|------|----------|
| `/health` | GET | **200** | `{"status":"ok","provider":"do-app-platform-gateway"}` |
| `/api/models` | GET | **200** | 19 roles configured with canonical model IDs |
| `/api/zero-prompt/start` | POST | **200** | SSE stream with `zp.session.start` event |
| `/api/zero-prompt/active` | GET | **200** | `{"sessions":[]}` (empty, correct for no active sessions) |
| `/api/dashboard/stats` | GET | **200** | `{"total_meetings":0,"total_brainstorms":0,...}` |

### Web Endpoints (Next.js component)

| Route | HTTP | Content |
|-------|------|---------|
| `/` | **200** | Landing page (Next.js 16.1.7 Turbopack) |
| `/dashboard` | **200** | Dashboard page (renders, fetches from /api/dashboard/*) |
| `/zero-prompt` | **200** | Zero-Prompt Kanban UI page |

### Model Configuration (from /api/models)

| Role | Model | Provider |
|------|-------|----------|
| council | claude-sonnet-4-6 | Anthropic (via DO Inference) |
| strategist | gpt-5.4 | OpenAI (via DO Inference) |
| code_gen | gpt-5.3-codex | OpenAI (via DO Inference) |
| zero_prompt_discovery | gemini-3.1-flash-lite-preview | Google |
| ui_design | gemini-3.1-pro-preview | Google |
| selected_runtime_model | openai-gpt-oss-120b | DO Inference (free tier) |

Note: Premium models (gpt-5.4, claude-sonnet-4-6) return 401 on DO Inference (subscription tier limit). Runtime falls back to `openai-gpt-oss-120b` which is available.

## Pivot Document Acceptance Criteria

### P0: Runtime Substrate
- [x] Provider Adapter Registry: 3 adapters (OpenAI, Anthropic, Google) in `agent/providers/`
- [x] Canonical model IDs: 19 roles mapped in `/api/models`
- [x] Gemini SDK: `google.genai` used in `insight_extractor.py`
- [x] Legacy aliases: `LEGACY_MODEL_ALIASES = {}` (emptied)

### P1: Build Lane
- [x] OpenAPI contract generation: `api_contract_generator.py`
- [x] TypeScript types + API client: `type_generator.py`
- [x] Pydantic models: `pydantic_generator.py`
- [x] Contract validation: `contract_validator.py`
- [x] Build validator: `build_validator.py`
- [x] Per-file generation + AST validation + retry: `per_file_code_generator.py`, `per_file_regeneration.py`
- [x] Design tokens: OKLCH (`design_tokens.py`), Typography (`typography.py`), Motion (`motion_tokens.py`)
- [x] Layout archetypes: 8 archetypes in `layout_archetypes.py`
- [x] Seed data: 5 domains in `seed_data.py`

### P2: Zero-Prompt Lane
- [x] YouTube Discovery: `discovery.py`
- [x] Transcript extraction: `transcript.py`
- [x] Gemini Insight: `insight_extractor.py` (real SDK call + rule-based fallback)
- [x] Paper search: `paper_search.py` (OpenAlex + arXiv)
- [x] Paper brainstorm: `paper_brainstorm.py`
- [x] Competitive analysis: `competitive_analysis.py` (Brave + Exa)
- [x] GO/NO-GO verdict: `verdict.py` (deterministic scoring)
- [x] Orchestrator + Session API: `orchestrator.py`, `queue_manager.py`
- [x] API routes: 5 ZP endpoints registered in `server.py`
- [x] SSE events: 26 event types in `events.py`
- [x] Kanban UI: `/zero-prompt` page + 8 components
- [x] Live endpoint: POST `/api/zero-prompt/start` returns SSE stream

### P3: Dashboard & Result Model
- [x] Deployment metrics: `deployment_metrics.py`
- [x] Dashboard API split: `dashboard-api.ts` separate from `api.ts`
- [x] Lineage store: `LineageStore` in `store.py`

### P4: Stabilization
- [x] Frontend tests: Vitest 8 tests passing
- [x] CI: pytest-cov 80%, ruff, ESLint, tsc, bandit, mypy, npm audit
- [x] Legacy cleanup: dead pricing entries removed, dead SSE events removed

## CI Evidence

| Check | Result |
|-------|--------|
| Agent Lint (ruff) | 1285 tests passed |
| Agent Tests (pytest) | 1285 passed, 1 skipped |
| Web Lint (eslint) | Passed |
| Web Tests (vitest) | 8 passed |
| Web Build (next) | 6 routes compiled |
| Web Typecheck (tsc) | Passed |
| Agent Security (bandit) | Passed (audit mode) |

## Known Limitations

1. Premium DO Inference models (gpt-5.4, claude-sonnet-4-6) require paid subscription tier
2. Runtime falls back to `openai-gpt-oss-120b` (free) when premium models unavailable
3. `/dashboard/stats` bare route serves Next.js page, use `/api/dashboard/stats` for API access
4. ADK URL not configured in App Platform (`adk_url_configured: false`)
