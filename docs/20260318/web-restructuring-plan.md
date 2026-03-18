# Web Restructuring Plan — bkit Orchestration Patterns Applied

> Generated: 2026-03-18 KST
> Reference: [popup-studio-ai/bkit-claude-code](https://github.com/popup-studio-ai/bkit-claude-code)

## Context

bkit-claude-code is a Claude Code plugin (not a web app), but its orchestration patterns are directly applicable to vibeDeploy's web frontend:

| bkit Pattern | vibeDeploy Web Equivalent |
|---|---|
| **Hook System** (event-driven, 6 layers) | Event bus for SSE events + component lifecycle |
| **Skill Frontmatter** (metadata-driven) | Route metadata + page guards |
| **Agent Frontmatter** (role-based) | Centralized agent definitions |
| **Centralized State** (paths.js) | Unified store (Zustand or Context) |
| **Skill Orchestrator** (module federation) | Dynamic feature loading |
| **PDCA State Machine** (phase transitions) | Pipeline state machine |
| **Config-Driven** (bkit.config.json) | Feature flags + dynamic config |
| **Template System** (import resolver) | Component composition patterns |
| **Eval Framework** (quality scoring) | Component testing patterns |

---

## Current Problems (8 architectural issues)

| # | Problem | Severity | Files |
|---|---------|----------|-------|
| 1 | **GOD COMPONENT**: pipeline-viz.tsx 598 lines | HIGH | dashboard/pipeline-viz.tsx |
| 2 | **Duplicated SSE logic**: use-pipeline-monitor inlines parsing | HIGH | hooks/use-pipeline-monitor.ts |
| 3 | **Agent mapping x3**: name/emoji/color in 3+ files | MEDIUM | meeting-view, brainstorm-view, pipeline-viz |
| 4 | **Tight coupling**: idea-card + card-detail-modal duplicate rendering | MEDIUM | zero-prompt/idea-card.tsx, card-detail-modal.tsx |
| 5 | **No error boundaries** | MEDIUM | (missing) |
| 6 | **No index exports** for component directories | LOW | dashboard/, zero-prompt/ |
| 7 | **Mixed state patterns**: polling vs SSE without unified layer | LOW | hooks/ |
| 8 | **Only 2 test files** | LOW | hooks/__tests__, lib/__tests__ |

---

## Proposed Structure (bkit-inspired)

### Current

```
web/src/
├── app/                    # Routes (flat)
├── components/             # Mixed hierarchy
│   ├── dashboard/          # 5 files, no index
│   ├── zero-prompt/        # 7 files, no index
│   ├── ui/                 # shadcn primitives
│   └── (10 root files)     # meeting-view, brainstorm-view, etc.
├── hooks/                  # 3 hooks (mixed patterns)
├── lib/                    # 3 API modules + SSE + utils
└── types/                  # 2 files
```

### Proposed

```
web/src/
├── app/                         # Routes (unchanged)
│   ├── layout.tsx
│   ├── page.tsx
│   ├── dashboard/page.tsx
│   ├── zero-prompt/page.tsx
│   ├── meeting/[id]/page.tsx
│   ├── brainstorm/[id]/page.tsx
│   └── result/[id]/page.tsx
│
├── components/
│   ├── ui/                      # shadcn primitives (unchanged)
│   │
│   ├── meeting/                 # Meeting flow (extracted from root)
│   │   ├── index.ts             # Barrel export
│   │   ├── meeting-view.tsx
│   │   ├── council-member.tsx
│   │   ├── cross-exam.tsx
│   │   └── decision-gate.tsx
│   │
│   ├── brainstorm/              # Brainstorm flow (extracted from root)
│   │   ├── index.ts
│   │   └── brainstorm-view.tsx
│   │
│   ├── result/                  # Result flow (extracted from root)
│   │   ├── index.ts
│   │   ├── vibe-score.tsx
│   │   ├── code-preview.tsx
│   │   ├── doc-viewer.tsx
│   │   └── deploy-status.tsx
│   │
│   ├── dashboard/               # Dashboard (split pipeline-viz)
│   │   ├── index.ts
│   │   ├── pipeline-viz/        # <-- GOD COMPONENT SPLIT
│   │   │   ├── index.tsx        # Composition root
│   │   │   ├── pipeline-graph.tsx
│   │   │   ├── pipeline-node.tsx
│   │   │   ├── pipeline-edge.tsx
│   │   │   └── particle-layer.tsx
│   │   ├── live-monitor.tsx
│   │   ├── dashboard-charts.tsx
│   │   ├── history-list.tsx
│   │   └── deployed-apps.tsx
│   │
│   ├── zero-prompt/             # Zero-Prompt (unchanged, already well-organized)
│   │   ├── index.ts
│   │   ├── kanban-board.tsx
│   │   ├── kanban-column.tsx
│   │   ├── idea-card.tsx
│   │   ├── card-detail-modal.tsx
│   │   ├── status-bar.tsx
│   │   ├── action-feed.tsx
│   │   └── session-header.tsx
│   │
│   ├── shared/                  # Shared components (NEW)
│   │   ├── error-boundary.tsx   # <-- MISSING: error boundary
│   │   └── loading-skeleton.tsx
│   │
│   └── input-form.tsx           # Landing form (stays at root)
│
├── config/                      # <-- NEW: bkit-inspired config layer
│   ├── agents.ts                # Centralized agent definitions (name, emoji, color, role)
│   ├── pipeline.ts              # Pipeline node definitions + status colors
│   └── features.ts              # Feature flags / dynamic config
│
├── hooks/                       # Hooks (unified patterns)
│   ├── use-dashboard.ts         # Polling
│   ├── use-pipeline-monitor.ts  # SSE (refactored to use sse-client)
│   ├── use-zero-prompt.ts       # SSE
│   └── use-event-bus.ts         # <-- NEW: bkit-inspired event bus
│
├── lib/                         # API + utilities
│   ├── api.ts
│   ├── dashboard-api.ts
│   ├── zero-prompt-api.ts
│   ├── sse-client.ts            # Shared SSE infrastructure
│   └── utils.ts
│
└── types/                       # Type definitions
    ├── dashboard.ts
    ├── zero-prompt.ts
    └── agents.ts                # <-- NEW: agent type definitions
```

---

## Implementation Phases

### Phase 1: Config Layer (LOW RISK, HIGH VALUE)

**bkit pattern**: Centralized agent/pipeline definitions like `bkit.config.json`

| Task | Files | Effort |
|------|-------|--------|
| Create `config/agents.ts` with agent definitions | NEW | 30min |
| Replace 3x duplicated agent mappings | meeting-view, brainstorm-view, pipeline-viz | 1h |
| Create `config/pipeline.ts` with node definitions | NEW | 30min |

```typescript
// config/agents.ts — Single source of truth
export const AGENTS = {
  architect: { name: "Architect", emoji: "🏗️", color: "blue", role: "Technical Lead" },
  scout: { name: "Scout", emoji: "🔍", color: "green", role: "Market Analyst" },
  guardian: { name: "Guardian", emoji: "🛡️", color: "red", role: "Risk Assessor" },
  catalyst: { name: "Catalyst", emoji: "⚡", color: "amber", role: "Innovation" },
  advocate: { name: "Advocate", emoji: "❤️", color: "pink", role: "UX Champion" },
  strategist: { name: "Strategist", emoji: "🎯", color: "purple", role: "Session Lead" },
} as const;
```

### Phase 2: Component Reorganization (MEDIUM RISK)

| Task | From | To | Effort |
|------|------|-----|--------|
| Move meeting components | `components/` root | `components/meeting/` | 1h |
| Move result components | `components/` root | `components/result/` | 30min |
| Move brainstorm component | `components/` root | `components/brainstorm/` | 30min |
| Add barrel exports | — | `index.ts` per directory | 30min |
| Update all import paths | All pages | — | 1h |

### Phase 3: Pipeline-Viz Split (HIGH VALUE, MEDIUM RISK)

**bkit pattern**: Skill decomposition into focused modules

| Sub-component | Lines | Responsibility |
|---------------|-------|----------------|
| `pipeline-graph.tsx` | ~100 | SVG container + layout |
| `pipeline-node.tsx` | ~80 | Individual node rendering |
| `pipeline-edge.tsx` | ~60 | Edge/connection rendering |
| `particle-layer.tsx` | ~100 | Animation particles |
| `index.tsx` | ~50 | Composition root |

### Phase 4: SSE Unification (HIGH VALUE)

**bkit pattern**: Hook system with centralized event handling

| Task | Files | Effort |
|------|-------|--------|
| Refactor use-pipeline-monitor to use sse-client.ts | hooks/use-pipeline-monitor.ts | 2h |
| Create use-event-bus.ts for cross-component events | NEW | 1h |

### Phase 5: Error Boundaries + Testing (MEDIUM VALUE)

| Task | Files | Effort |
|------|-------|--------|
| Add ErrorBoundary component | NEW: components/shared/error-boundary.tsx | 30min |
| Wrap each route page in ErrorBoundary | app/*/page.tsx | 30min |
| Add tests for config/agents.ts | NEW | 30min |

---

## What NOT to change

| Item | Reason |
|------|--------|
| `app/` route structure | Already clean, no benefit from change |
| `components/ui/` | shadcn standard, don't touch |
| `components/zero-prompt/` | Already well-organized (7 focused files) |
| `lib/` API modules | Clean separation, working correctly |
| `types/` | Adequate for current needs |
| State management approach | No need for Zustand/Redux — hooks + SSE is appropriate for this app size |

---

## Priority Order

```
Phase 1 (Config Layer)     → 2h   — Eliminates duplication, highest ROI
Phase 3 (Pipeline Split)   → 3h   — Eliminates god component
Phase 2 (Component Reorg)  → 3h   — Clean architecture
Phase 4 (SSE Unification)  → 3h   — Removes duplicated parsing
Phase 5 (Error + Tests)    → 1.5h — Polish

Total: ~12.5 hours
```

---

## Risk Assessment

| Phase | Risk | Mitigation |
|-------|------|-----------|
| Phase 1 | LOW — pure addition + find-replace | Import changes verified by tsc |
| Phase 2 | MEDIUM — import path changes | Batch with `ast-grep` or LSP rename |
| Phase 3 | MEDIUM — visual regression risk | Compare screenshots before/after |
| Phase 4 | LOW — internal hook refactor | Existing test covers behavior |
| Phase 5 | LOW — pure addition | No breaking changes |
