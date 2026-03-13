# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-12 Asia/Seoul
**Commit:** f34fc90
**Branch:** main

## OVERVIEW
vibeDeploy is a dual-runtime app: `agent/` is the Python Gradient ADK + FastAPI gateway, `web/` is the Next.js UI, and `.do/app.yaml` wires both into one App Platform deploy.

## STRUCTURE
```text
vibeDeploy/
|- agent/               # ADK entrypoint, FastAPI gateway, LangGraph pipeline, deploy helpers
|- web/                 # Next.js app + dashboard UI
|- .do/app.yaml         # App Platform spec for api + web
|- docs/reference/      # numbered planning docs; static reference, not runtime
|- screenshots/         # demo assets
|- output/              # generated artifacts / Playwright output
`- agent/.venv/         # checked-in local venv; ignore during repo analysis
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| ADK entrypoint | `agent/main.py` | `@entrypoint`, streams orchestration chunks |
| Local API server | `agent/server.py` | `/run`, `/resume`, `/brainstorm`, dashboard endpoints |
| Pipeline topology | `agent/graph.py` | evaluation/build graph |
| Brainstorm topology | `agent/graph_brainstorm.py` | brainstorm-only graph |
| DO deploy spec | `.do/app.yaml` | api + web components, env injection |
| Agent deploy script | `agent/scripts/deploy.sh` | ADK deploy, spec rendering, `doctl` update/create |
| Web API boundary | `web/src/lib/api.ts` | browser-to-gateway calls |
| Live dashboard state | `web/src/hooks/use-pipeline-monitor.ts` | SSE + viz-node mapping |
| Main dashboard screen | `web/src/app/dashboard/page.tsx` | consumes hooks and dashboard components |
| CI commands | `.github/workflows/ci.yml` | canonical lint/test/build commands |

## CODE MAP
| Symbol | Type | Location | Refs | Role |
|--------|------|----------|------|------|
| `main` | ADK entrypoint | `agent/main.py:20` | high | Gradient ADK surface |
| `app` | FastAPI app | `agent/server.py` | high | gateway + dashboard API |
| `create_graph` | function | `agent/graph.py:40` | high | evaluation/build pipeline topology |
| `create_brainstorm_graph` | function | `agent/graph_brainstorm.py:34` | medium | brainstorm topology |
| `DashboardPage` | component | `web/src/app/dashboard/page.tsx:36` | high | dashboard composition root |
| `usePipelineMonitor` | hook | `web/src/hooks/use-pipeline-monitor.ts:73` | high | live SSE client + node states |
| `startMeeting` | function | `web/src/lib/api.ts:8` | medium | starts evaluation run |

## CONVENTIONS
- Treat `agent/` and `web/` as separate runtimes with separate tooling; there is no root package manager.
- Ignore `agent/.venv/`, `.ruff_cache/`, `.hypothesis/`, `.playwright-cli/`, and `output/` when searching or scoring structure.
- Root docs should mention the split deploy model; child docs should cover local domain rules only.
- `web/` uses `@/* -> ./src/*`; alias imports should start at `@/`, not `@/src/`.
- The web app talks to `DASHBOARD_API_URL`, which becomes `${NEXT_PUBLIC_AGENT_URL}/api` only on deployed `ondigitalocean.app` URLs.

## ANTI-PATTERNS (THIS PROJECT)
- Do not treat this repo as the Go backend described in older operator notes; the checked-in runtime here is Python + Next.js.
- Do not control a shared production server on port `8080`; operator guidance says production restart/stop stays manual.
- Do not edit `.env` without explicit user direction; the local gateway already loads `agent/.env.test`.
- Do not search inside `agent/.venv/` and mistake vendored packages for first-party code.
- Do not add child `AGENTS.md` files for every busy directory; only create them where workflow or constraints materially change.

## UNIQUE STYLES
- Dashboard UX is not a generic admin shell; prompts and tests explicitly reject blank KPI-grid defaults.
- The dashboard is operational, not marketing: live SSE events, active pipeline state, deploy stages, result reconciliation.
- The backend exposes both `/api/*` and bare routes (`/run`, `/dashboard/*`) because App Platform ingress and local dev differ.

## COMMANDS
```bash
# agent lint / tests
cd agent && ruff check . && ruff format --check . && pytest tests/ -v --tb=short

# local agent gateway
cd agent && python run_server.py

# ADK local runtime
cd agent && gradient agent run --host 0.0.0.0 --port 8080

# web lint / build
cd web && npm ci && npx eslint . && NEXT_PUBLIC_AGENT_URL=http://localhost:8080 npm run build

# web dev
cd web && NEXT_PUBLIC_AGENT_URL=http://localhost:8080 npm run dev
```

## NOTES
- `.do/app.yaml` deploys two components from one repo: `agent/` as `api`, `web/` as `web`.
- `agent/run_server.py` respects `UVICORN_WORKERS` / `WEB_CONCURRENCY`; default is one worker.
- `agent/server.py` contains hidden test-only endpoints guarded by `VIBEDEPLOY_ENABLE_TEST_API`.
- `agent/scripts/deploy.sh` renders placeholders into a temp spec before `doctl apps update/create`.
