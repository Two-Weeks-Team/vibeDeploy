# Prometheus Plan: vibeDeploy Hackathon Implementation

> Generated: 2026-03-04
> Deadline: 2026-03-18 17:00 EDT (2026-03-19 06:00 KST)
> Repository: https://github.com/Two-Weeks-Team/vibeDeploy

---

## Strategic Overview

Build vibeDeploy end-to-end: Agent backend (Python/ADK/LangGraph) + Frontend (Next.js) + Deploy to DigitalOcean.
Critical path: Scaffold → Agent Core → Build Pipeline → Frontend → Deploy → Submit.
**14 days remaining. Every hour counts.**

## Dependency Graph

```
Phase 1 (M1): Scaffold [Mar 4-5]
  #1 agent scaffold ──┐
                      ├──► Phase 2 (M2): Agent Core [Mar 5-9]
  #2 web scaffold ────┘
                      
  #1 ──► #11 tools
  #1 ──► #3 input processor ──► #4 phase 1 ──► #5 phase 2 ──► #6 phase 3+4 ──► #7 decision gate
  #1+#3-7 ──► #15 graph wiring
  
Phase 3 (M3): Build Pipeline [Mar 9-12]
  #15 ──► #8 doc gen ──► #9 code gen ──► #10 deployer
  #1 ──► #19 KB setup
  #1 ──► #20 DB schema

Phase 4 (M4): Frontend [Mar 12-14]
  #2 ──► #12 landing ──► #13 meeting view ──► #14 result dashboard

Phase 5 (M5): Deploy & Submit [Mar 14-18]
  #15+#12-14 ──► #16 production deploy
  #15 ──► #22 evaluations
  #12-14 ──► #21 UI polish
  #16 ──► #17 demo video ──► #18 devpost submission
```

## Parallelization Strategy

- **Wave 1**: #1 + #2 (scaffold, parallel)
- **Wave 2**: #11 + #3 + #19 + #20 (tools, input processor, KB, DB — all depend only on #1)
- **Wave 3**: #4 (phase 1 analysis — depends on #3)
- **Wave 4**: #5 + #12 (cross-exam + landing page — parallel tracks)
- **Wave 5**: #6 + #13 (scoring + meeting view — parallel tracks)
- **Wave 6**: #7 + #14 (decision gate + result dashboard — parallel tracks)
- **Wave 7**: #15 (graph wiring — needs all agent nodes)
- **Wave 8**: #8 → #9 → #10 (build pipeline — sequential)
- **Wave 9**: #16 + #21 + #22 (deploy + polish + evals)
- **Wave 10**: #17 → #18 (video → submit)

---

## Task Execution Plan

### Wave 1: Project Scaffold [Day 1]

- [ ] **Task 1.1** — Agent scaffold (#1)
  - Create `agent/` directory structure
  - `main.py` with `@entrypoint`, `graph.py` skeleton, `state.py` with VibeDeployState
  - All node stubs, council stubs, tool stubs, prompt file
  - `.gradient/agent.yml`, `requirements.txt`, `.env.example`
  - **Verify**: `pip install -r requirements.txt` succeeds
  - **Category**: `quick` | **Skills**: [] | **Est**: 2h

- [ ] **Task 1.2** — Web scaffold (#2)
  - `npx create-next-app@latest` in `web/`
  - shadcn/ui + Tailwind + dark theme
  - Page stubs, component stubs, lib stubs
  - `.do/app.yaml` for App Platform
  - **Verify**: `npm run build` succeeds
  - **Category**: `quick` | **Skills**: [`frontend-ui-ux`] | **Est**: 2h

### Wave 2: Foundation Layer [Day 1-2]

- [ ] **Task 2.1** — Tool implementations (#11)
  - `tools/youtube.py`, `tools/web_search.py`, `tools/knowledge_base.py`
  - `tools/image_gen.py`, `tools/github.py`, `tools/digitalocean.py`
  - All with error handling + retry
  - **Verify**: Each tool callable with mock inputs
  - **Category**: `unspecified-high` | **Skills**: [] | **Est**: 4h

- [ ] **Task 2.2** — Input Processor (#3)
  - Text → structured idea JSON
  - YouTube URL → transcript → visual segments → frame analysis → idea
  - SSE events: `council.phase.start`
  - **Verify**: Text input returns structured idea; YouTube URL extracts transcript
  - **Category**: `deep` | **Skills**: [] | **Est**: 4h

- [ ] **Task 2.3** — Knowledge Base setup (#19)
  - DO docs KB + framework patterns KB in Gradient console
  - Retrieve API integration in `tools/knowledge_base.py`
  - **Verify**: Query returns relevant DO documentation
  - **Category**: `quick` | **Skills**: [] | **Est**: 1h

- [ ] **Task 2.4** — Database schema (#20)
  - SQL migration for sessions, council_analyses, cross_examinations, vibe_scores, deployments
  - Connection setup via DATABASE_URL
  - **Verify**: Tables created in local PostgreSQL
  - **Category**: `quick` | **Skills**: [] | **Est**: 1h

### Wave 3: Vibe Council Phase 1 [Day 2-3]

- [ ] **Task 3.1** — Phase 1: Individual Analysis (#4)
  - 6 system prompts in `council_prompts.py`
  - `fan_out_analysis()` with LangGraph Send API
  - `run_council_agent()` for each of 5 agents
  - All agents run in parallel, return structured JSON
  - SSE events: `council.agent.analyzing`, `council.agent.analysis`
  - **Verify**: 5 agents produce valid analysis JSON for test input
  - **Category**: `deep` | **Skills**: [] | **Est**: 6h

### Wave 4: Cross-Examination + Landing [Day 3-4]

- [ ] **Task 4.1** — Phase 2: Cross-Examination (#5)
  - 3 debate rounds: Architect↔Guardian, Scout↔Catalyst, Advocate challenges
  - Structured debate output
  - SSE events: `council.debate.start`, `council.debate.exchange`
  - **Verify**: Debate produces coherent exchanges referencing Phase 1 analysis
  - **Category**: `deep` | **Skills**: [] | **Est**: 4h

- [ ] **Task 4.2** — Landing page (#12)
  - Hero section, text/URL input form
  - Form submission → POST to agent → redirect to meeting
  - Responsive, dark theme
  - **Verify**: Form submits and creates thread_id
  - **Category**: `visual-engineering` | **Skills**: [`frontend-ui-ux`] | **Est**: 3h

### Wave 5: Scoring + Meeting View [Day 4-5]

- [ ] **Task 5.1** — Phase 3+4: Scoring + Verdict (#6)
  - Parallel scoring via Send API
  - Vibe Score™ formula implementation
  - Decision Gate routing
  - Strategist verdict generation
  - SSE events: `council.scoring.result`, `council.verdict`
  - **Verify**: Correct score calculation; correct GO/CONDITIONAL/NO-GO routing
  - **Category**: `deep` | **Skills**: [] | **Est**: 4h

- [ ] **Task 5.2** — Meeting View page (#13)
  - SSE EventSource connection
  - Phase 1: agent avatars + analysis cards
  - Phase 2: debate speech bubbles
  - Phase 3: score gauge animation
  - Phase 4: decision banner
  - CONDITIONAL modal
  - **Verify**: All SSE events render correctly in UI
  - **Category**: `visual-engineering` | **Skills**: [`frontend-ui-ux`] | **Est**: 6h

### Wave 6: Decision Gate + Result Dashboard [Day 5-6]

- [ ] **Task 6.1** — Decision Gate + Conditional Review (#7)
  - `decision_gate()` routing
  - `conditional_review` with `interrupt()`
  - `feedback_generator` for NO-GO reports
  - Resume via thread_id + MemorySaver
  - **Verify**: Each path (GO/CONDITIONAL/NO-GO) executes correctly
  - **Category**: `unspecified-high` | **Skills**: [] | **Est**: 3h

- [ ] **Task 6.2** — Result Dashboard (#14)
  - GO: doc tabs, code preview, deploy status, live URL
  - NO-GO: failure report, suggestions, retry button
  - Build/deploy SSE event handling
  - **Verify**: Both GO and NO-GO views render correctly
  - **Category**: `visual-engineering` | **Skills**: [`frontend-ui-ux`] | **Est**: 4h

### Wave 7: Graph Wiring [Day 6-7]

- [ ] **Task 7.1** — Complete StateGraph + SSE Entrypoint (#15)
  - Wire all nodes in `graph.py`
  - `@entrypoint` SSE streaming in `main.py`
  - MemorySaver checkpointer
  - End-to-end test with real LLM calls
  - **Verify**: Text input → complete pipeline → SSE events emitted
  - **Category**: `deep` | **Skills**: [] | **Est**: 4h

### Wave 8: Build Pipeline [Day 7-9]

- [ ] **Task 8.1** — Doc Generator (#8)
  - PRD, Tech Spec, API Spec, DB Schema, App Spec YAML
  - RAG from DO Knowledge Base
  - Claude 4.6 Sonnet for generation
  - **Verify**: All 5 doc types generated with valid content
  - **Category**: `deep` | **Skills**: [] | **Est**: 4h

- [ ] **Task 8.2** — Code Generator (#9)
  - Frontend (Next.js) + Backend (FastAPI) in parallel
  - Uses templates as base, LLM customizes
  - App logo via GPT-image-1
  - **Verify**: Generated code builds and runs
  - **Category**: `deep` | **Skills**: [] | **Est**: 6h

- [ ] **Task 8.3** — Deployer (#10)
  - GitHub repo creation + push
  - DO App Platform deployment via pydo
  - Status polling, error recovery
  - **Verify**: Generated app accessible at live URL
  - **Category**: `deep` | **Skills**: [] | **Est**: 4h

### Wave 9: Polish & Deploy [Day 10-12]

- [ ] **Task 9.1** — Deploy vibeDeploy (#16)
  - Agent → `gradient agent deploy`
  - Frontend → App Platform
  - End-to-end production test
  - **Verify**: Full pipeline works on production URLs
  - **Category**: `unspecified-high` | **Skills**: [] | **Est**: 3h

- [ ] **Task 9.2** — UI Polish (#21)
  - Animations, transitions, responsive
  - Loading states, error states
  - **Verify**: Demo-quality visual polish
  - **Category**: `visual-engineering` | **Skills**: [`frontend-ui-ux`] | **Est**: 4h

- [ ] **Task 9.3** — Evaluations + Tracing (#22)
  - Evaluation dataset, tracing setup
  - **Verify**: Eval results recorded, traces visible
  - **Category**: `quick` | **Skills**: [] | **Est**: 2h

### Wave 10: Submit [Day 13-14]

- [ ] **Task 10.1** — Demo Video (#17)
  - Record <3 min demo showing full pipeline
  - Upload to YouTube/Vimeo
  - **Verify**: Video shows real working demo
  - **Manual task** | **Est**: 3h

- [ ] **Task 10.2** — Devpost Submission (#18)
  - All required fields filled
  - Video URL, GitHub URL, live URL
  - Screenshots
  - Apply for all 4 prize categories
  - **Verify**: Submission complete on Devpost
  - **Manual task** | **Est**: 2h

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| ADK deploy fails | Test early (Wave 1), have local fallback |
| LLM quality poor | Tune prompts iteratively, use stronger models for critical agents |
| Code gen produces broken code | Templates provide structure, LLM fills gaps; test with simple inputs first |
| DO deployment fails | Manual App Platform creation via console as backup |
| Time crunch | Cut evaluations (#22) and DB (#20) first; focus on demo-visible features |

## Cut List (if time is short)
1. **Cut first**: #22 (evaluations) — nice for scoring, not visible in demo
2. **Cut second**: #20 (DB schema) — use in-memory state for hackathon
3. **Cut third**: #19 (KB setup) — hardcode DO patterns instead of RAG
4. **Reduce scope**: YouTube input can be simplified (transcript only, no vision)
