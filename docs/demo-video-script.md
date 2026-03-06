# vibeDeploy Demo Video Script (3 min max)

## 0:00-0:15 — Hook
"What if you could turn a single sentence into a live deployed app? Meet vibeDeploy."

[SCREEN: Landing page with animated logo]

## 0:15-0:35 — The Problem
"Traditional vibe coding gives you code — but no validation, no deployment. You're left wondering: is this idea even good?"

[SCREEN: Quick montage of other AI coding tools → just code output]

"vibeDeploy changes that. Six AI experts debate your idea before a single line of code is written."

## 0:35-1:15 — Live Demo: Evaluate Mode
[SCREEN: Type prompt into vibeDeploy]
"Let's build a restaurant queue management app with QR codes."

[SCREEN: The Vibe Council meeting starts — show each agent analyzing in parallel]
- Architect: "Next.js + FastAPI, 3 endpoints, medium complexity"
- Scout: "Growing market, Yelp Waitlist is main competitor"
- Guardian: "Low risk — standard tech stack"
- Catalyst: "QR code + SMS notifications = strong differentiator"
- Advocate: "3 screens for MVP — excellent UX simplicity"

[SCREEN: Cross-Examination debate happening live]
[SCREEN: Vibe Score appears: 78.5 → GO verdict]

## 1:15-1:45 — Build & Deploy
[SCREEN: Docs being generated (PRD, Tech Spec, API Spec)]
[SCREEN: Code generation with progress bar]
[SCREEN: GitHub repo created automatically with CI badge]
[SCREEN: Live URL appears — click to show deployed app]

"From idea to live app in under 5 minutes. Fully deployed on DigitalOcean."

## 1:45-2:15 — Brainstorm Mode
"Not ready to build? Brainstorm first."

[SCREEN: Switch to Brainstorm mode, enter a vague idea]
[SCREEN: 5 agents generating creative ideas in parallel]
[SCREEN: Synthesis with top 5 ranked ideas, quick wins, strategic direction]

"The same AI council, now in creative mode — generating possibilities instead of scores."

## 2:15-2:45 — Tech Deep Dive
"Under the hood: 10 DigitalOcean Gradient AI features."

[SCREEN: Architecture diagram with labels]
- Gradient ADK: Agent hosting with auto-tracing
- Serverless Inference: Mix of DO-native (Llama 3.3 70B) + OpenAI models
- Knowledge Base: RAG over DO docs for deployment guidance
- Function Calling: Agents use tools for real-time market research
- Evaluations: 10-case test suite measuring decision accuracy
- Guardrails: PII filtering + prompt injection protection
- App Platform: Static site + FastAPI service + Managed PostgreSQL
- Multi-Agent: 6 specialized council agents via LangGraph
- Streaming: Real-time SSE for live meeting experience
- Image Generation: AI-powered app logos and UI mockups

## 2:45-3:00 — Closing
"vibeDeploy — one sentence, one meeting, one live app. Built entirely on DigitalOcean."

[SCREEN: Logo + GitHub URL + "Try it at vibedeploy.ondigitalocean.app"]
