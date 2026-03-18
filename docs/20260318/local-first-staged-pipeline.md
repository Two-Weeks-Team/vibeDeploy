# Local-First Staged Pipeline

## Goal

Prevent static mockups and fragile deploys by enforcing a staged, contract-first generation flow that must pass local gates before any cloud deployment.

## Hackathon Constraints

- The submission must be a **new working software application**.
- The project must **function as depicted** in the video and text description.
- The repository must remain **public** and include an **open source license**.
- DigitalOcean Gradient / App Platform resources should be used as the primary execution environment.
- Cloud deployment is allowed only after local verification gates pass.

## Feature Flag

Use `VIBEDEPLOY_USE_STAGED_PIPELINE=true` to activate the staged graph.

Default behavior remains the legacy graph for backward compatibility.

## Node Roles

### Phase 1 — Idea Refinement
- `input_processor`: normalize prompt and extract source context
- `inspiration_agent`: add external inspiration and category framing
- `experience_agent`: derive UX and experience constraints
- `enrich_idea`: merge the refined idea payload

### Phase 2 — Contract Freeze
- `doc_generator`: create PRD / tech spec / db schema
- `blueprint_generator`: create frontend/backend manifest and initial interaction contract
- `api_contract_generator`: convert blueprint contract into executable OpenAPI JSON
- `spec_freeze_gate`: reject incomplete or invalid contracts before code generation

### Phase 3 — Deterministic Foundation
- `scaffold_generator`: write deterministic scaffold files
- `type_generator`: generate `src/types/api.d.ts` and `src/lib/api-client.ts`
- `pydantic_generator`: generate backend `schemas.py`
- `design_system_generator`: freeze design-system context before code generation

### Phase 4 — Business Logic
- `prompt_strategist`: choose prompt shape and enforce design/behavior rules
- `code_generator`: generate frontend/backend implementation on top of frozen contract
- `contract_validator`: compare generated backend to OpenAPI contract

### Phase 5 — Local Gates
- `code_evaluator`: heuristic quality gate
- `build_validator`: syntax + Docker build + design anti-pattern checks
- `local_runtime_validator`: start generated backend locally and verify `/health`
- `deploy_gate`: block deploy unless contract/build/runtime all pass

### Phase 6 — Deployment
- `deployer`: GitHub repo, CI, App Platform deploy, health check

## Local Verification Order

1. **Spec gate**
   - OpenAPI JSON must parse and validate
   - Blueprint contract endpoints must exist in the spec

2. **Foundation gate**
   - Scaffold files must exist
   - Generated TypeScript API client and Pydantic models must exist

3. **Contract gate**
   - Backend routes must match the frozen OpenAPI contract
   - Missing endpoints or schema mismatches block progress

4. **Build gate**
   - Backend import / Docker checks pass
   - Frontend build checks pass
   - Design anti-pattern checks pass
   - `skipped=true` is treated as a deploy blocker

5. **Runtime gate**
   - Generated backend must start locally in a temp directory
   - `GET /health` must return 200

6. **Deploy gate**
   - Only when all previous gates pass

## Retry Policy

- `spec_freeze_gate`: max 2 attempts, then stop
- `contract_validator`: loop back to `code_generator` on failure
- `build_validator`: max 3 attempts (existing)
- `local_runtime_validator`: loop back to `code_generator` until build attempt budget is exhausted
- `deploy_gate`: no retry, only pass/fail

## Standard Tool Usage

### Local development
```bash
cd agent && python run_server.py
```

### Staged graph activation
```bash
VIBEDEPLOY_USE_STAGED_PIPELINE=true python -c "from agent.graph import create_graph; create_graph()"
```

### Verification
```bash
cd agent && ruff check . && ruff format --check .
cd agent && pytest tests/test_staged_pipeline_nodes.py -v --tb=short
```

## Why This Exists

The previous graph generated frontend and backend in a single jump after blueprint generation. That made route names, response shapes, and UI wiring drift apart. The staged flow moves the contract into a first-class artifact and forces every later step to respect it.
