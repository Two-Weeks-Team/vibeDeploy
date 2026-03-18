# vibeDeploy - Devpost Description

## Inspiration

Most AI coding tools stop at code. They do not help users discover which idea is worth building, they do not show the decision process live, and they still leave validation and deployment work to the user.

We built `vibeDeploy` to close that gap: start from an idea, validate it with AI and research, then move all the way to a live deployed app on DigitalOcean.

## What it does

`vibeDeploy` is an autonomous AI product workflow with three modes:

- `Zero-Prompt Start`: one click launches idea discovery from YouTube, research-backed evaluation, competitive analysis, and a live Kanban of GO / NO-GO cards. The user chooses any GO card to build.
- `Evaluate`: a specific idea goes through the Vibe Council, a six-agent review that scores feasibility, market signal, risk, and user value.
- `Brainstorm`: the same system shifts into idea expansion and produces a structured concept brief instead of a build verdict.

The core product experience is the Zero-Prompt Kanban: discovery starts automatically, the board fills live, and a GO card can be built and deployed from the same workflow.

## How we built it

`vibeDeploy` is a dual-runtime system:

- `web/` is a Next.js 16.1.7 frontend for Zero-Prompt, evaluation, brainstorm, and monitoring views.
- `agent/` is a Python 3.12.4 backend that combines Gradient ADK, FastAPI, and LangGraph.

The build pipeline follows a contract-first approach:

1. Idea refinement
2. Council review or Zero-Prompt evaluation
3. OpenAPI contract generation
4. Layered code generation
5. Validation (syntax, imports, build, contract checks)
6. Deploy plus health verification

This structure lets us keep the user-facing story simple while the underlying system remains observable and testable.

## DigitalOcean usage

We currently document `13` DigitalOcean capabilities across Gradient AI and the deployment stack:

1. Gradient ADK
2. Knowledge Bases
3. Evaluations
4. Guardrails
5. Tracing
6. Multi-Agent Routing
7. A2A handoff
8. Serverless Inference
9. App Platform
10. Spaces
11. Image Generation
12. Agent Versioning
13. MCP Integration

The product also uses Managed PostgreSQL for session and lineage data.

## Models in the current build

- `gemini-3.1-flash-lite-preview` for Zero-Prompt discovery and lightweight brainstorming
- `claude-sonnet-4-6` for council analysis and cross-examination
- `gpt-5.4` for strategist synthesis and document generation
- `gpt-5.3-codex` for code generation
- `gpt-5.2` for CI repair

## Challenges we ran into

- Keeping a dual-runtime system consistent across a streaming UI, FastAPI gateway, and ADK runtime
- Moving from one-shot generation to contract-first, layered generation
- Validating generated apps before deploy instead of trusting raw output
- Handling SSE and long-running jobs without making the product feel opaque
- Coordinating YouTube discovery, paper search, and competitive analysis inside one visible workflow

## Accomplishments we're proud of

- A public Zero-Prompt experience that shows discovery and ranking live on a Kanban board
- Four public generated demo apps with working URLs at the time of the latest submission audit
- A single product that covers discovery, evaluation, generation, validation, and deployment
- A clearer split between the user-facing Zero-Prompt flow and the operational dashboard

## What we learned

- Reviewers trust consistent evidence more than large claim counts
- Contract-first generation makes frontend and backend changes easier to keep in sync
- A visible live workflow is easier to understand than a hidden batch job
- Submission copy needs the same level of rigor as the codebase itself

## What's next for vibeDeploy

- Improve the handoff from GO card selection to deployed app preview
- Expand reusable generation templates and evaluation criteria
- Add stronger iteration loops after deployment feedback
- Keep tightening the Zero-Prompt submission experience around a single clear story

## Built With

- Python 3.12.4
- Next.js 16.1.7
- FastAPI
- LangGraph
- DigitalOcean Gradient ADK
- DigitalOcean App Platform
- Managed PostgreSQL
- Docker SDK
- Google Gemini
- Anthropic Claude
- OpenAI GPT
