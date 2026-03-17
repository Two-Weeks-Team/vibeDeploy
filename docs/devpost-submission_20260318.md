# Devpost Submission Text

> Copy-paste this into the Devpost submission form fields.

---

## Project Title

vibeDeploy

## Short Description (one line)

Zero prompts, zero coding — one button autonomously discovers ideas from YouTube, validates with academic research, writes type-safe code, Docker-verifies it compiles, and deploys a live app to DigitalOcean.

---

## Detailed Description

### What it does

vibeDeploy is an autonomous AI agent platform that closes the entire gap from idea to live deployed application on DigitalOcean. It operates in three modes:

**Zero-Prompt Start**: Press one button. 9 specialized AI agents autonomously explore YouTube for trending content, extract app ideas using Gemini structured output, validate each idea against academic papers (OpenAlex + arXiv), run competitive analysis (Brave + Exa), and score with a deterministic GO/NO-GO engine. Users watch ideas accumulate on a real-time Kanban board — then click "Build" to deploy any GO idea. Cost: ~$0.20 for 10 validated ideas.

**Vibe Council Evaluation**: Submit an idea in one sentence. 6 AI agents (Architect, Scout, Guardian, Catalyst, Advocate, Strategist) hold a live, structured 4-phase debate — individual analysis, cross-examination, scoring, and verdict. The Strategist synthesizes a Vibe Score. If GO, the build pipeline starts automatically.

**Brainstorm Mode**: The same 5 agents switch to creative ideation, generating possibilities instead of scores.

### How we built it

vibeDeploy is a dual-runtime application: a Python backend (Gradient ADK + FastAPI + LangGraph) and a Next.js frontend, deployed together on DigitalOcean App Platform.

The architectural breakthrough is **Contract-First, Validate-Always** — a 6-phase pipeline:

1. **Idea Refinement** — input processing, inspiration, experience design
2. **Vibe Council** — 6 agents debate in parallel via LangGraph Send API (optional — "skip to build" available)
3. **Contract Generation** — LLM generates OpenAPI 3.1 spec; TypeScript types AND Pydantic models are auto-derived from this single source of truth
4. **Layered Code Generation** — 5 layers from deterministic scaffolds (0% failure) to per-file LLM business logic (15-25% per file)
5. **4-Tier Build Validation** — syntax check, import verification, Docker SDK `npm run build` in container, OpenAPI vs FastAPI contract cross-check. Failures trigger targeted per-file regeneration with temperature decay (0.10 → 0.05 → 0.02)
6. **Deploy + Health Gate** — GitHub repo creation, DO App Platform deployment, `/health` endpoint smoke test

This architecture improved deploy success rate from ~40% to ~95%.

### DigitalOcean Gradient AI Usage (13 features)

vibeDeploy leverages 13 distinct DigitalOcean Gradient AI features:

| # | Feature | Usage |
|---|---------|-------|
| 1 | **ADK** | `@entrypoint` for agent request streaming, `gradient agent deploy` for production |
| 2 | **Knowledge Bases (RAG)** | Two KBs: DO deployment docs + framework best practices |
| 3 | **Evaluations** | 25 test cases measuring generated app quality |
| 4 | **Guardrails** | Content moderation + jailbreak detection + PII redaction |
| 5 | **Tracing** | `@trace_tool` and `@trace_llm` on every tool/LLM call |
| 6 | **Multi-Agent Routing** | 6 Council + 9 Zero-Prompt agents via LangGraph Send API |
| 7 | **A2A Protocol** | Zero-Prompt discovery hands off GO ideas to build pipeline |
| 8 | **Serverless Inference** | All LLM calls via Provider Adapter Registry |
| 9 | **App Platform** | vibeDeploy itself AND all generated apps deploy here |
| 10 | **Spaces** | Build artifacts, source archives, logs in S3 storage |
| 11 | **Image Generation** | App logos + OG images via DO Inference |
| 12 | **Agent Versioning** | A/B test pipeline changes with rollback |
| 13 | **MCP Integration** | DO platform APIs via Model Context Protocol |

DO Gradient AI is the **platform** (agent lifecycle, evaluation, tracing, deployment, storage). External LLMs (Gemini, Claude) are interchangeable models accessed through our Provider Adapter Registry — swap any model without touching platform code.

### Challenges we ran into

1. **~40% → ~95% deploy success** — The original single-shot code generator produced broken apps. We redesigned the entire pipeline with deterministic scaffolds, OpenAPI contracts, per-file generation, and Docker-based validation.
2. **Docker build validation on App Platform** — Running `npm run build` inside containers required 512MB RAM limits and network isolation with graceful degradation.
3. **SSE streaming across dual deployment** — ADK runtime and App Platform gateway are separate services. Relaying events without drops required buffering and reconnection logic.
4. **Per-file regeneration with context** — Regenerating one failed file while maintaining cross-file imports required full context passing with temperature decay.
5. **Academic API rate limits** — arXiv's 1-request-per-3-seconds throttle required async queuing with OpenAlex as primary.

### Accomplishments we're proud of

- 4 live deployed apps generated from single sentences, running on DigitalOcean
- 13 Gradient AI features integrated — the deepest platform usage possible
- Contract-First architecture that guarantees frontend/backend type compatibility
- Docker-based build validation that actually compiles the code before deploying
- Zero-Prompt Start — fully autonomous idea discovery that costs $0.20

### What we learned

- **Docker SDK build validation** catches ~95% of issues vs ~40% with regex heuristics
- **OpenAPI as single source of truth** eliminates the entire category of FE/BE type mismatches
- **Per-file generation** is dramatically more reliable than monolithic blob generation
- **Gradient ADK** makes agent deployment remarkably simple
- **Streaming UX** transforms waiting into watching — users stay engaged

### What's next

- Multi-provider model orchestration with cost optimization
- Collaborative multi-user sessions
- Template marketplace for generated app patterns
- Integration with more DigitalOcean services (Functions, Kubernetes)

---

## Built With

- Python 3.12
- DigitalOcean Gradient ADK
- LangGraph
- FastAPI
- Next.js 15
- PostgreSQL
- Docker SDK
- Google Gemini (structured output)
- Anthropic Claude (council debate)
- shadcn/ui
- Tailwind CSS
- Framer Motion
- OpenAlex API
- arXiv API

## Links

- **GitHub**: https://github.com/Two-Weeks-Team/vibeDeploy
- **Live Demo**: https://vibedeploy-7tgzk.ondigitalocean.app
- **Video**: [YouTube link — REPLACE AFTER UPLOAD]
