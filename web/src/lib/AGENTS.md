# WEB API LAYER

## OVERVIEW
`web/src/lib/` holds the browser-side boundary to the Python gateway plus a couple of small shared browser utilities.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Meeting start/resume | `api.ts` | creates thread ids and POSTs `/run` / `/resume` |
| Brainstorm start/result | `api.ts` | brainstorm equivalents |
| Dashboard data fetches | `api.ts` | stats, results, brainstorms, deployments |
| URL normalization | `api.ts` | `AGENT_URL` vs `DASHBOARD_API_URL` |
| Streaming helper | `sse-client.ts` | shared SSE parsing/client utilities |
| UI helpers | `utils.ts` | shared class-name / utility helpers |
| Downstream consumers | `../hooks/use-dashboard.ts`, `../hooks/use-pipeline-monitor.ts` | payload compatibility points |

## CONVENTIONS
- Use the exported helpers instead of sprinkling raw fetch calls through route components.
- Keep fallback behavior conservative: dashboard list helpers return empty arrays, health/result helpers return `false` or `null` on fetch failure.
- Preserve the `crypto.randomUUID()` thread/session id creation pattern for meeting and brainstorm starts.

## ANTI-PATTERNS
- Do not hardcode `/api` onto every request; only deployed `ondigitalocean.app` agent URLs need that prefix.
- Do not silently change result/deployment payload shapes without checking `web/src/hooks/` and `web/src/types/`.
- Do not move thread-id creation into UI components unless every caller is updated together.

## NOTES
- `MeetingResult` includes optional deploy metadata such as CI status and local URLs; many screens tolerate partial deployment data.
- This directory is small but high-leverage: tiny shape changes fan out across the whole web runtime.
- `api.ts` is the contract-heavy file here; `sse-client.ts` and `utils.ts` are lighter-weight support modules.

## COMMANDS
```bash
cd web && npx eslint src/lib/api.ts src/hooks/use-dashboard.ts src/hooks/use-pipeline-monitor.ts
cd web && NEXT_PUBLIC_AGENT_URL=http://localhost:8080 npm run build
```
