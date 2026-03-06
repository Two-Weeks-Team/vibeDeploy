# vibeDeploy — Devpost Submission

## Inspiration

Every AI code generator produces code — but none validates whether the idea is worth building, and none deploys the result. We wanted to create the complete pipeline: from a single sentence to a live, deployed application — with AI experts debating the idea's viability before a single line of code is written.

## What it does

vibeDeploy takes a sentence describing your app idea and turns it into a **live deployed application** on DigitalOcean. Between your idea and the deployed app, **The Vibe Council** — six specialized AI agents — holds a structured debate to evaluate feasibility, market fit, and technical risk.

**Two modes:**
- **Evaluate Mode**: 6 AI agents analyze, debate, and score your idea (Vibe Score 0-100). If GO → auto-generate code → deploy to DigitalOcean.
- **Brainstorm Mode**: Same 6 agents switch to creative ideation — generating possibilities instead of scores.

## How we built it

**Architecture:**
- **Gradient ADK** hosts the core agent pipeline with LangGraph StateGraph for multi-agent orchestration
- **App Platform** runs the FastAPI API server (10+ endpoints) + Next.js frontend + Managed PostgreSQL
- **Serverless Inference** powers all LLM calls — mixing DO-native models (Llama 3.3 70B) with OpenAI models (GPT-5.3 Codex for code generation)
- **Knowledge Base** provides RAG over DigitalOcean docs for deployment guidance
- **Function Calling** enables agents to use tools for real-time market research and tech stack validation

**The Vibe Council agents:**
| Agent | Role | Model |
|-------|------|-------|
| Architect | Technical Lead | Llama 3.3 70B (DO-native) |
| Scout | Market Analyst | Llama 3.3 70B (DO-native) |
| Guardian | Risk Assessor | Llama 3.3 70B (DO-native) |
| Catalyst | Innovation Officer | Llama 3.3 70B (DO-native) |
| Advocate | UX Champion | Llama 3.3 70B (DO-native) |
| Strategist | Session Lead | GPT-5.2 (OpenAI via DO) |

## DigitalOcean Gradient AI Features Used (10)

1. **ADK (Agent Development Kit)** — Agent system hosting with @entrypoint
2. **Serverless Inference (Text)** — 6 council agents + code generation via DO endpoint
3. **Serverless Inference (Image)** — AI-generated app logos and UI mockups
4. **Knowledge Bases (RAG)** — DO docs + framework best practices for deployment guidance
5. **Multi-Agent Routing** — LangGraph Send API for parallel agent execution
6. **Function Calling** — Agents use bound tools (@tool + bind_tools) for real-time research
7. **Evaluations** — 10-case test suite measuring decision accuracy and scoring calibration
8. **Tracing** — Automatic pipeline debugging via ADK + LangGraph integration
9. **Streaming** — Real-time SSE for live meeting experience
10. **Guardrails** — PII filtering + prompt injection protection on all inputs

## Challenges we ran into

- **ADK single endpoint limitation**: The ADK only exposes POST /run, but our system has 10+ API endpoints. Solution: deploy ADK for the core pipeline and App Platform Service for the full API server.
- **Model diversity**: Balancing DO-native models (fast, no external keys) with OpenAI models (stronger reasoning) required careful role assignment.
- **CI auto-repair**: Generated projects sometimes had CI failures. We built a 3-iteration repair loop using GPT-5.3 Codex to automatically fix CI errors.

## Accomplishments that we're proud of

- **Complete pipeline**: Idea → AI debate → code generation → GitHub repo → CI pass → live URL. No manual steps.
- **Real AI debate**: Not just sequential analysis — agents cross-examine each other's findings.
- **10 Gradient AI features**: Deep platform integration, not surface-level usage.
- **CI auto-repair loop**: Generated projects self-heal when CI fails.

## What we learned

- LangGraph's Send API enables elegant parallel multi-agent execution
- Mixing DO-native and OpenAI models through DO Inference provides both cost efficiency and quality
- The ADK's automatic tracing removes the need for manual instrumentation
- Guardrails (PII filtering, prompt injection detection) are essential for any user-facing AI system

## What's next for vibeDeploy

- **More deployment targets**: Kubernetes, Vercel, AWS
- **Collaborative meetings**: Multiple users watch and influence the AI debate in real-time
- **Project iteration**: Feed deployed app analytics back to improve future builds
- **Template marketplace**: Save and share successful project templates

## Built With

- digitalocean-app-platform
- digitalocean-gradient-adk
- digitalocean-serverless-inference
- digitalocean-managed-postgresql
- python
- fastapi
- langgraph
- nextjs
- typescript
- tailwindcss
