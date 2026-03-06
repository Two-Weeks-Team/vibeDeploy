<p align="center">
  <img src="https://img.shields.io/badge/hackathon-DigitalOcean%20Gradient%20AI%202026-0080FF?style=for-the-badge&logo=digitalocean&logoColor=white" alt="Hackathon Badge"/>
</p>

<h1 align="center">vibeDeploy</h1>

<p align="center">
  <strong>One sentence. One meeting. One live app.</strong>
</p>

<p align="center">
  <a href="https://vibedeploy-7tgzk.ondigitalocean.app"><img src="https://img.shields.io/badge/LIVE%20DEMO-vibedeploy--7tgzk.ondigitalocean.app-00C853?style=for-the-badge&logo=digitalocean&logoColor=white" alt="Live Demo"/></a>
</p>

<p align="center">
  <a href="https://github.com/Two-Weeks-Team/vibeDeploy/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=flat-square" alt="License: MIT"/></a>
  <a href="https://github.com/Two-Weeks-Team/vibeDeploy/issues"><img src="https://img.shields.io/github/issues/Two-Weeks-Team/vibeDeploy?style=flat-square&color=orange" alt="Issues"/></a>
  <a href="https://github.com/Two-Weeks-Team/vibeDeploy/pulls"><img src="https://img.shields.io/github/issues-pr/Two-Weeks-Team/vibeDeploy?style=flat-square&color=blue" alt="PRs"/></a>
  <img src="https://img.shields.io/badge/python-3.12-blue?style=flat-square&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/next.js-15-black?style=flat-square&logo=next.js&logoColor=white" alt="Next.js"/>
  <img src="https://img.shields.io/badge/LangGraph-1.0-purple?style=flat-square" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/Gradient%20ADK-0.0.8-0080FF?style=flat-square&logo=digitalocean" alt="Gradient ADK"/>
</p>

<p align="center">
  <a href="#what-is-vibedeploy">What</a> &bull;
  <a href="#the-vibe-council">Council</a> &bull;
  <a href="#brainstorm-mode">Brainstorm</a> &bull;
  <a href="#how-it-works">How</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#tech-stack">Stack</a> &bull;
  <a href="#getting-started">Start</a> &bull;
  <a href="#deployment">Deploy</a>
</p>

---

## What is vibeDeploy?

**vibeDeploy** takes a sentence describing your app idea — or a YouTube URL — and turns it into a **live, deployed application** on DigitalOcean. No coding required.

Between your idea and the deployed app, **The Vibe Council** — a panel of 6 specialized AI agents — holds a live debate meeting to evaluate feasibility, challenge assumptions, and score your idea before a single line of code is written.

```
"I want a restaurant queue management app with QR codes"
                          ↓
              🏛️ The Vibe Council convenes
              🏗️ Architect → 🔭 Scout → 🛡️ Guardian → ⚡ Catalyst → 🎯 Advocate
              🧭 Strategist synthesizes → Vibe Score™: 78.5 → 🟢 GO
                          ↓
              📄 PRD + Tech Spec + API Spec generated
              💻 Frontend + Backend code generated
              🚀 Deployed to DigitalOcean
                          ↓
              ✅ https://your-app.ondigitalocean.app
```

### Key Differentiators

| Traditional Vibe Coding | vibeDeploy |
|---|---|
| Generates code only | Idea → **live deployed app** |
| Single AI writes code | **6 AI experts debate** before building |
| You judge quality | AI team **self-validates feasibility** |
| Deployment is separate | **Auto-deploy + live URL** |
| Text input only | **YouTube URL** also works |
| One mode fits all | **Evaluate** or **Brainstorm** — you choose |

---

## The Vibe Council

vibeDeploy's unique decision-making framework. Six specialized AI agents engage in **structured debate** — challenging, questioning, and refining your idea through a live meeting.

| Agent | Role | Focus | Core Question |
|-------|------|-------|---------------|
| 🏗️ **Architect** | Technical Lead | Tech stack, complexity, feasibility | "How do we build this?" |
| 🔭 **Scout** | Market Analyst | Competition, trends, market fit | "Who wants this?" |
| 🛡️ **Guardian** | Risk Assessor | Security, legal, failure modes | "Why could this fail?" |
| ⚡ **Catalyst** | Innovation Officer | Uniqueness, disruption, impact | "What makes this special?" |
| 🎯 **Advocate** | UX Champion | User perspective, accessibility | "Will people use this?" |
| 🧭 **Strategist** | Session Lead | Synthesis, scoring, verdict | "What's the verdict?" |

### 4-Phase Meeting

```
Phase 1: INDIVIDUAL ANALYSIS    → 5 agents analyze in parallel
Phase 2: CROSS-EXAMINATION      → Structured debate (Architect↔Guardian, Scout↔Catalyst, Advocate challenges)
Phase 3: SCORING                 → Each agent scores their axis (0-100)
Phase 4: VERDICT                 → Strategist calculates Vibe Score™ → GO / CONDITIONAL / NO-GO
```

### Vibe Score™

```
Vibe Score™ = (Tech × 0.25) + (Market × 0.20) + (Innovation × 0.20) + ((100 - Risk) × 0.20) + (UserImpact × 0.15)

≥ 70 → 🟢 GO          Build and deploy immediately
50-69 → 🟡 CONDITIONAL  Propose scope reduction, user decides
< 50  → 🔴 NO-GO        Detailed failure report + alternatives
```

---

## Brainstorm Mode

Not ready to evaluate? **Brainstorm first.** The same 5 council agents switch from judge mode to **creative ideation mode** — generating possibilities instead of scores.

```
Your idea → 💡 Brainstorm Mode
                    ↓
  🏗️ Architect: "3 innovative tech stack combos..."
  🔭 Scout:     "3 untapped market segments..."
  ⚡ Catalyst:  "3 ways to make this 10x more disruptive..."
  🛡️ Guardian:  "3 risks turned into competitive advantages..."
  🎯 Advocate:  "3 delightful UX micro-interactions..."
                    ↓
  🧭 Strategist synthesizes all insights into:
     • Top 5 ranked ideas across agents
     • Recurring themes & synergies
     • 3 quick wins to implement first
     • Strategic direction recommendation
```

Each agent generates **ideas, opportunities, wild cards, and action items** from their unique perspective. The Strategist then synthesizes everything into a coherent creative brief — no scoring, no judgment, pure creative fuel.

---

## How It Works

### Input → Meeting → Build → Deploy

```
┌──────────────────────────────────────────────────────────────┐
│  INPUT                                                        │
│  Text: "Build a recipe sharing community with AI suggestions" │
│  — or —                                                       │
│  YouTube: https://youtube.com/watch?v=...                     │
│  (auto-extracts idea from transcript + key frame analysis)    │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  THE VIBE COUNCIL (Live AI Debate)                            │
│                                                               │
│  Phase 1: 5 agents analyze independently (parallel)           │
│  Phase 2: Cross-Examination debates                           │
│  Phase 3: Each agent scores their axis                        │
│  Phase 4: Strategist → Vibe Score™ → Decision                │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  BUILD (if GO or CONDITIONAL-accepted)                        │
│                                                               │
│  📄 PRD + Tech Spec + API Spec + DB Schema                   │
│  💻 Next.js frontend + FastAPI/Express backend                │
│  🎨 App logo + placeholder images (AI-generated)              │
└──────────────────┬───────────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  DEPLOY                                                       │
│                                                               │
│  📦 GitHub repo created automatically                         │
│  🚀 Deployed to DigitalOcean App Platform                     │
│  🔗 Live URL: https://your-app.ondigitalocean.app            │
└──────────────────────────────────────────────────────────────┘
```

---

## Architecture

```
┌─────────────────────────────────┐     ┌──────────────────────────────┐
│  Frontend (App Platform)        │     │  Agent Backend (Gradient ADK) │
│  Next.js 15 + shadcn/ui        │────▶│  Python + LangGraph           │
│  Static Site                    │◀────│  @entrypoint → POST /run      │
│  .do/app.yaml                   │ SSE │  .gradient/agent.yml          │
└─────────────────────────────────┘     └──────────────────────────────┘
                                                     │
                          ┌──────────────────────────┼──────────────────┐
                          ▼                          ▼                  ▼
                   ┌─────────────┐          ┌──────────────┐   ┌──────────────┐
                   │ Gradient AI │          │ Managed      │   │ DO Spaces    │
                   │ Inference   │          │ PostgreSQL   │   │ (S3)         │
                   │ (8 models)  │          │              │   │              │
                   └─────────────┘          └──────────────┘   └──────────────┘
```

**Two independent deployments:**
- **Agent** → `gradient agent deploy` to ADK infrastructure (FREE during preview)
- **Frontend** → DO App Platform via `.do/app.yaml`

---

## Tech Stack

### Core

| Component | Technology | DigitalOcean Service |
|-----------|-----------|---------------------|
| Frontend | Next.js 15 + shadcn/ui + Tailwind CSS | App Platform |
| Agent Backend | Python 3.12 + Gradient ADK + LangGraph | Gradient ADK |
| Database | PostgreSQL 16 | Managed PostgreSQL |
| Storage | S3-compatible object storage | Spaces |
| AI Models | 4 open-source model families via Serverless Inference | Gradient AI Platform |
| Knowledge Base | RAG over DO docs + framework patterns | Gradient KB |

### DigitalOcean Gradient AI Features Used (8)

| # | Feature | Usage |
|---|---------|-------|
| 1 | **ADK (Agent Development Kit)** | Agent system hosting |
| 2 | **Serverless Inference (Text)** | 6 council agents + code generation |
| 3 | **Serverless Inference (Image)** | App logos, UI mockups, placeholders |
| 4 | **Knowledge Bases (RAG)** | DO docs, framework best practices |
| 5 | **Multi-Agent Routing** | LangGraph Send API parallel execution |
| 6 | **Evaluations** | Agent response quality measurement |
| 7 | **Tracing** | Full pipeline debugging |
| 8 | **Function Calling** | DO API, GitHub API, YouTube API |

### Model Assignment

| Role | Model | Type | Cost (per 1M tokens) |
|------|-------|------|---------------------|
| Council (5 agents) | `openai-gpt-oss-120b` | Open-Source (120B) | $0.10 / $0.70 |
| Strategist | `deepseek-r1-distill-llama-70b` | Open-Source (70B) | $0.99 / $0.99 |
| Cross-Examination | `deepseek-r1-distill-llama-70b` | Open-Source (70B) | $0.99 / $0.99 |
| Code Generation | `openai-gpt-oss-120b` | Open-Source (120B) | $0.10 / $0.70 |
| CI Repair | `openai-gpt-oss-120b` | Open-Source (120B) | $0.10 / $0.70 |
| Doc Generation | `alibaba-qwen3-32b` | Open-Source (32B) | $0.25 / $0.55 |
| Input Processing | `openai-gpt-oss-120b` | Open-Source (120B) | $0.10 / $0.70 |
| Decision Gate | `deepseek-r1-distill-llama-70b` | Open-Source (70B) | $0.99 / $0.99 |
| Brainstorm Agents | `openai-gpt-oss-120b` | Open-Source (120B) | $0.10 / $0.70 |
| Brainstorm Synthesis | `deepseek-r1-distill-llama-70b` | Open-Source (70B) | $0.99 / $0.99 |
| Web Search | `mistral-nemo-instruct-2407` | Open-Source (12B) | $0.30 / $0.30 |
| Image Generation | `fal-ai/flux/schnell` | Open-Source (fal) | ~$0.003 / image |

**Multi-model open-source AI: 4 model families via DO Serverless Inference**
**Cost per full deployment: ~$0.12** | $200 credits = ~1,600+ deployments

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- [Gradient CLI](https://docs.digitalocean.com/products/gradient-ai-platform/getting-started/)
- [DigitalOcean account](https://mlh.link/digitalocean-signup) (free $200 credits for hackathon)

### Local Development

```bash
# Clone
git clone https://github.com/Two-Weeks-Team/vibeDeploy.git
cd vibeDeploy

# Agent Backend
cd agent/
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in your keys
gradient agent run --host 0.0.0.0 --port 8080

# Frontend (new terminal)
cd web/
npm install
NEXT_PUBLIC_AGENT_URL=http://localhost:8080 npm run dev
```

Open `http://localhost:3000` and enter your idea.

---

## Deployment

**Live at: [https://vibedeploy-7tgzk.ondigitalocean.app](https://vibedeploy-7tgzk.ondigitalocean.app)**

### Full Stack → App Platform

The FastAPI backend and Next.js frontend are both deployed via DigitalOcean App Platform:

```bash
doctl apps create --spec .do/app.yaml
# Or push to main → auto-deploy (deploy_on_push: true)
# → https://vibedeploy-7tgzk.ondigitalocean.app
```

### Gradient AI Agent (API)

```bash
# Create agent via doctl (attach Knowledge Base for RAG)
doctl gradient agent create \
  --name "vibedeploy-agent" \
  --project-id "<project-id>" \
  --model-id "<model-uuid>" \
  --region "tor1" \
  --instruction "Your agent instruction" \
  --knowledge-base-id "<kb-uuid>"
```

### Knowledge Base (RAG)

```bash
doctl gradient knowledge-base create \
  --name vibedeploy-docs \
  --region tor1 \
  --project-id "<project-id>" \
  --embedding-model-uuid "<embedding-model-uuid>" \
  --data-sources '[{"web_crawler_data_source":{"base_url":"https://docs.digitalocean.com/products/app-platform/","crawling_option":"UNKNOWN","embed_media":false}}]'
```

---

## Project Structure

```
vibeDeploy/
├── web/                          # Next.js Frontend → App Platform
│   ├── src/app/                  # Pages (landing, meeting, brainstorm, result)
│   ├── src/components/           # UI components (council, brainstorm, scores, deploy)
│   └── src/lib/                  # SSE client, API helpers
├── agent/                        # Python Agent → Gradient ADK
│   ├── main.py                   # @entrypoint (Gradient ADK)
│   ├── server.py                 # Local FastAPI server (dev)
│   ├── graph.py                  # Evaluation pipeline (LangGraph StateGraph)
│   ├── graph_brainstorm.py       # Brainstorm pipeline (LangGraph StateGraph)
│   ├── nodes/                    # Pipeline nodes (input, council, brainstorm, build)
│   ├── council/                  # 6 Vibe Council agent definitions
│   ├── tools/                    # YouTube (yt-dlp), GitHub, DO, search tools
│   └── .gradient/agent.yml       # ADK config (3 lines)
├── .do/app.yaml                  # App Platform spec (frontend only)
├── docs/reference/               # 10 planning documents
└── LICENSE                       # MIT
```

---

## Documentation

Comprehensive planning docs in [`docs/reference/`](docs/reference/):

| # | Document | Description |
|---|----------|-------------|
| 01 | [Hackathon Rules](docs/reference/01-hackathon-rules.md) | Rules, timeline, $200 credits guide |
| 02 | [Judging Criteria](docs/reference/02-judging-criteria.md) | 4 criteria × 25% each |
| 03 | [Submission Checklist](docs/reference/03-submission-checklist.md) | Devpost requirements |
| 04 | [Prizes](docs/reference/04-prizes.md) | $20K total, 6 categories |
| 05 | [Gradient AI Platform](docs/reference/05-digitalocean-gradient-ai.md) | SDK patterns, models, pricing |
| 06 | [DO Products](docs/reference/06-digitalocean-products.md) | App Platform, DB, Spaces |
| 07 | [Winning Strategy](docs/reference/07-winning-strategy.md) | Demo video, judge targeting |
| 08 | [Product Concept](docs/reference/08-vibedeploy-concept.md) | Vibe Council, scoring system |
| 09 | [Agent Architecture](docs/reference/09-agent-architecture.md) | LangGraph, state, nodes, prompts |
| 10 | [Technical Plan](docs/reference/10-technical-plan.md) | Deployment, costs, DB schema |

---

## Hackathon

<table>
  <tr>
    <td><strong>Event</strong></td>
    <td><a href="https://digitalocean.devpost.com/">DigitalOcean Gradient AI Hackathon 2026</a></td>
  </tr>
  <tr>
    <td><strong>Prizes</strong></td>
    <td>$20,000 total (1st: $5,000 + $2,000 DO credits)</td>
  </tr>
  <tr>
    <td><strong>Deadline</strong></td>
    <td>March 18, 2026, 5:00 PM EDT</td>
  </tr>
  <tr>
    <td><strong>Team</strong></td>
    <td><a href="https://github.com/Two-Weeks-Team">Two-Weeks-Team</a></td>
  </tr>
</table>

### Target Prizes

| Prize | Why vibeDeploy Fits |
|-------|-------------------|
| **1st Place ($5,000)** | Deep Gradient AI integration (8 features), full pipeline |
| **Best AI Agent Persona** | 6 distinct agents with personalities debating live |
| **Best Program for the People** | Democratizes app development for non-coders |
| **Great Whale Prize** | Largest scope: idea → live deployed app |

---

## License

[MIT](LICENSE) - See [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with DigitalOcean Gradient AI for the <a href="https://digitalocean.devpost.com/">DO Gradient AI Hackathon 2026</a></sub>
</p>
