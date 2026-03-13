# WEB RUNTIME

## OVERVIEW
`web/` is a standalone Next.js App Router app for landing, meeting, brainstorm, result, and operational dashboard flows.

## STRUCTURE
```text
web/
|- src/app/                 # route entrypoints
|- src/components/          # app-specific UI + dashboard views + ui primitives
|- src/hooks/               # polling + SSE state hooks
|- src/lib/                 # API boundary, utils
|- src/types/               # shared dashboard/result types
|- public/                  # static assets
`- package.json             # only npm scripts in repo
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Landing flow | `src/app/page.tsx` | input form entry |
| Dashboard route | `src/app/dashboard/page.tsx` | uses dashboard hooks + charts + pipeline viz |
| Meeting/result routes | `src/app/meeting/[id]/page.tsx`, `src/app/result/[id]/page.tsx` | live session pages |
| Browser API layer | `src/lib/api.ts` | fetch helpers |
| Polling state | `src/hooks/use-dashboard.ts` | periodic stats/results/deployments |
| Live SSE state | `src/hooks/use-pipeline-monitor.ts` | event stream + node statuses |

## CONVENTIONS
- TypeScript is strict; `tsconfig.json` defines `@/*` as `./src/*`.
- `next.config.ts` uses `output: "standalone"` because App Platform runs `node .next/standalone/server.js`.
- Default agent URL is `http://localhost:8080`; deployed builds rewrite to `${NEXT_PUBLIC_AGENT_URL}/api` only for `ondigitalocean.app` agent URLs.
- Dashboard behavior spans `src/app/dashboard`, `src/components/dashboard`, `src/hooks`, and `src/types`; avoid documenting it in one narrow child folder.
- ESLint config is flat and intentionally minimal; use CI commands as the source of truth.

## ANTI-PATTERNS
- Do not import from `@/src/...`; the alias already points at `src/`.
- Do not assume local and deployed API paths are identical; `DASHBOARD_API_URL` handles the split.
- Do not reduce dashboard UX to generic admin cards; repo prompts/tests explicitly guard against that aesthetic.
- Do not treat `web/README.md` as authoritative; it is mostly create-next-app boilerplate.

## COMMANDS
```bash
cd web && npm ci
cd web && npx eslint .
cd web && NEXT_PUBLIC_AGENT_URL=http://localhost:8080 npm run build
cd web && NEXT_PUBLIC_AGENT_URL=http://localhost:8080 npm run dev
```

## NOTES
- CI uses Node 20 and `npm ci`.
- The dashboard points at the backend gateway, not a separate frontend-only data source.
