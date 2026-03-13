# ADK-First Compaction Note

Updated: 2026-03-11 (Asia/Seoul)

## Current vs Target Architecture

### Current live migration state
- `agent/main.py` is now the canonical Gradient ADK entrypoint and streams the full shared pipeline.
- `agent/server.py` now acts as the App Platform gateway and persistence layer.
- The gateway preserves `/api/run`, `/api/resume`, `/api/brainstorm`, `/api/result/*`, `/api/dashboard/*`.
- When `VIBEDEPLOY_ADK_URL` is configured, the gateway proxies SSE requests to the remote ADK `/run`.
- The gateway authenticates remote ADK `/run` calls with `VIBEDEPLOY_ADK_AUTH_TOKEN` or `DIGITALOCEAN_API_TOKEN`, matching the official ADK curl example.
- When `VIBEDEPLOY_ADK_URL` is absent, the gateway falls back to the same shared pipeline locally for tests and dev.

### Target end state
- Gradient ADK hosts the authoritative multi-agent orchestration runtime.
- App Platform hosts the web UI, result persistence, dashboard APIs, and ADK stream proxying.
- Child apps may remain App Platform services.
- Submission claims must describe `ADK core + App Platform gateway/UI + Serverless Inference`.

## Stable ADK Input Contract

POST `/run`

```json
{
  "action": "evaluate | brainstorm | resume",
  "thread_id": "string",
  "prompt": "string",
  "youtube_url": "optional string",
  "reference_urls": ["optional strings"],
  "constraints": "optional string"
}
```

## Stable Runtime Event Contract

New additive events:
- `session.started`
- `phase.started`
- `phase.completed`
- `council.agent.completed`
- `artifact.generated`
- `deploy.step.start`
- `deploy.step.complete`
- `deploy.step.error`
- `session.completed`
- `session.error`

Legacy events preserved for the current frontend:
- `council.phase.start`
- `council.node.start`
- `council.node.complete`
- `council.agent.start`
- `council.agent.analysis`
- `scoring.axis.start`
- `scoring.axis.complete`
- `council.verdict`
- `deploy.complete`
- `council.phase.complete`
- `brainstorm.phase.start`
- `brainstorm.node.start`
- `brainstorm.node.complete`
- `brainstorm.agent.insight`
- `brainstorm.phase.complete`
- `brainstorm.error`

## Model Capability Probe Order

Probe order is implemented in `agent/model_capabilities.py`:
1. `openai-gpt-5.4` via `/v1/responses`
2. `openai-gpt-5.3-codex` via `/v1/responses`
3. `openai-gpt-5.2` via `/v1/responses`
4. `anthropic-claude-opus-4.6` via `/v1/chat/completions`
5. `anthropic-claude-4.6-sonnet` via `/v1/chat/completions`
6. `openai-gpt-oss-120b` via `/v1/chat/completions`

Current verified result:
- Commercial candidates above returned `401 this model is not available for your subscription tier`.
- `openai-gpt-oss-120b` returned `200` and remains the highest-end callable default.

Capability reports are written to `agent/.gradient/model_capabilities.json`.

## Quality Gate Status

Implemented:
- Deterministic fallback bundles now carry explicit marker files.
- `layout_archetype` no longer auto-forces the deterministic frontend scaffold.
- Code evaluation now blocks deployment for:
  - fallback scaffold markers
  - raw object / JSON dumps rendered into UI
  - repeated generic scaffold taxonomy
  - fabricated proof / testimonial copy
  - promised saved-history UX without a real persistence mechanism
- Deployer now refuses to deploy when code evaluation did not pass.

Remaining work:
- Expand the evaluator heuristics from coarse blocker detection to richer UX and originality scoring.
- Replace remaining placeholder fallback content generation with branded, domain-aware rescue paths or hard failure.

## Flagship Registry Shape

Planned checked-in registry shape:

```json
{
  "slug": "creator-workflow",
  "domain": "short-form creator workflow",
  "product_brief": "string",
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "visual_metaphor": "string",
  "forbidden_patterns": ["..."],
  "required_results": ["..."],
  "acceptance_checks": ["..."]
}
```

Required domains:
- short-form creator workflow from YouTube URL
- travel or weekender planning from video/reference
- budget reset or cash runway planner
- interview skill sprint or learning planner
- meal prep or grocery planning assistant

## Deployment Acceptance Checklist

- `gradient agent run` starts locally from `agent/`
- `gradient agent deploy` is the canonical agent deploy path
- App Platform API uses `VIBEDEPLOY_ADK_URL` to proxy to the deployed ADK runtime
- App Platform API authenticates remote ADK calls with a DigitalOcean bearer token
- `/api/models` exposes both runtime models and capability probe report
- `/api/run`, `/api/resume`, `/api/brainstorm` continue to stream the expected SSE contract
- `session.completed` snapshots persist to the gateway database
- Generated apps do not deploy when quality gates fail

## Explicit Implementation Constraint

All future implementation must continue from an ADK-first core.

Do not rebuild the orchestration around App Platform-local LangGraph execution as the primary runtime again.
