# AGENT RUNTIME

## OVERVIEW
`agent/` is the Python runtime: Gradient ADK entrypoint, FastAPI gateway, LangGraph orchestration, persistence, deploy helpers, and tests.

## STRUCTURE
```text
agent/
|- main.py            # Gradient ADK entrypoint
|- server.py          # FastAPI gateway + dashboard APIs + SSE
|- graph.py           # evaluation/build graph
|- graph_brainstorm.py# brainstorm graph
|- nodes/             # pipeline node implementations
|- tools/             # DO/GitHub/YouTube/search integrations
|- council/           # council persona modules
|- db/                # store + connection helpers
|- prompts/           # prompt templates / doc templates
`- tests/             # pytest suite with in-memory store + mocked graphs
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| ADK request streaming | `main.py` | thin wrapper over `stream_action_session` |
| HTTP + dashboard routes | `server.py` | local + deployed API surface |
| Graph ordering | `graph.py`, `graph_brainstorm.py` | authoritative flow |
| Persistence | `db/store.py` | SQLite/Postgres switch |
| Deploy orchestration | `scripts/deploy.sh` | ADK deploy + App Platform update |
| Runtime model config | `llm.py`, `model_capabilities.py` | model selection / fallback |

## CONVENTIONS
- `server.py` loads `agent/.env.test` on import; prefer test-safe env wiring over editing shared env files.
- Run the local gateway from repo root semantics via `python run_server.py`; that script adjusts `sys.path` and cwd.
- Keep route parity between `/api/...` and local bare paths when changing request/response shapes.
- Use `ResultStore` abstractions; do not scatter direct DB logic through route handlers.
- Ruff settings live in `pyproject.toml`; line length is 120, quotes are double.

## ANTI-PATTERNS
- Do not bypass `run_server.py` assumptions when documenting local startup; it owns worker-count/env behavior.
- Do not expose test endpoints without the `VIBEDEPLOY_ENABLE_TEST_API` guard.
- Do not hardcode deploy secrets into `.do/app.yaml`; `scripts/deploy.sh` renders placeholders into a temp file.
- Do not mix first-party code review with `agent/.venv/`; exclude that tree from searches.

## COMMANDS
```bash
cd agent && ruff check .
cd agent && ruff format --check .
cd agent && pytest tests/ -v --tb=short
cd agent && python run_server.py
cd agent && ./scripts/deploy.sh
```

## NOTES
- Local `python run_server.py` binds to `0.0.0.0:8080`; operator guidance treats shared `8080` as production-sensitive.
- `server.py` also serves dashboard stats/results/events; this directory is not just ADK logic.
- `graph.py` loops back from `fix_storm` to council analysis and from `code_evaluator` back to `code_generator`.
