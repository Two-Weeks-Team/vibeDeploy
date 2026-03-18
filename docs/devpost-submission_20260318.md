# Devpost Submission Text

> Copy-paste this into the Devpost submission form fields.

---

## Project Title

vibeDeploy

## Short Description (one line)

One click starts AI-powered idea discovery, a live Kanban ranks GO ideas, and vibeDeploy builds and deploys the selected app to DigitalOcean.

---

## Detailed Description

### What it does

vibeDeploy is an autonomous AI workflow that closes the gap between an idea and a live deployed app on DigitalOcean.

The primary flow is `Zero-Prompt Start`:

1. The user clicks one button.
2. AI agents explore YouTube and extract app ideas.
3. The system validates each idea with academic research and competitive analysis.
4. A live Kanban fills with GO and NO-GO cards.
5. The user picks a GO card to build.
6. vibeDeploy generates, validates, and deploys the selected app.

The product also supports:

- `Vibe Council Evaluation`: a six-agent review for a user-submitted idea
- `Brainstorm Mode`: structured idea expansion without a build verdict

### How we built it

vibeDeploy is a dual-runtime application:

- a Python backend built with Gradient ADK, FastAPI, and LangGraph
- a Next.js frontend deployed with the backend on DigitalOcean App Platform

The core architecture is contract-first:

1. Idea refinement
2. Evaluation through Zero-Prompt or Vibe Council
3. OpenAPI contract generation
4. Layered code generation
5. Validation across syntax, imports, build, and contract checks
6. Deploy plus health verification

This keeps the system observable for the user while reducing mismatches between frontend, backend, and deployment output.

### DigitalOcean usage

We currently document `13` DigitalOcean capabilities across Gradient AI and the broader platform:

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

Managed PostgreSQL is also used for session, lineage, and workflow data.

### Current models in the project

- Zero-Prompt discovery: `gemini-3.1-flash-lite-preview`
- Council analysis: `claude-sonnet-4-6`
- Strategist and docs: `gpt-5.4`
- Code generation: `gpt-5.3-codex`
- CI repair: `gpt-5.2`

### Challenges we ran into

1. Coordinating a dual-runtime system with streaming UI and long-running backend work
2. Replacing one-shot generation with a contract-first, layered pipeline
3. Validating generated apps before deployment instead of trusting raw output
4. Keeping the product story focused on the Zero-Prompt Kanban rather than mixing it with older dashboard terminology
5. Maintaining consistent submission copy across README, Devpost docs, and live links

### Accomplishments we're proud of

- A Zero-Prompt Kanban workflow that people can watch live
- Four public generated demo apps with working links during the latest submission audit
- A unified idea -> evaluate -> build -> deploy flow on DigitalOcean
- A cleaner, current submission story aligned with the codebase and live product

### What we learned

- Validation and consistency matter as much as generation quality
- A live product workflow is easier to understand than a hidden batch pipeline
- Contract-first generation helps keep the system maintainable as it grows
- Submission copy drifts quickly if it is not kept in sync with the source of truth

### What's next

- Improve the GO-card-to-build handoff and final app reveal
- Expand reusable templates and scoring criteria
- Add tighter feedback loops from deployed apps back into future builds
- Continue simplifying the submission-facing Zero-Prompt experience

---

## Built With

- Python 3.12.4
- DigitalOcean Gradient ADK
- LangGraph
- FastAPI
- Next.js 16.1.7
- PostgreSQL
- Docker SDK
- Google Gemini
- Anthropic Claude
- OpenAI GPT
- Tailwind CSS
- Framer Motion
- OpenAlex API
- arXiv API

## Links

- **GitHub**: https://github.com/Two-Weeks-Team/vibeDeploy
- **Live Demo**: https://vibedeploy-7tgzk.ondigitalocean.app
- **Video**: add the final public YouTube or Vimeo URL before submission
