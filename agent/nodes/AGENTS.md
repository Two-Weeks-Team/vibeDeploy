# PIPELINE NODES

## OVERVIEW
`agent/nodes/` holds the state-machine workhorses: idea enrichment, council fan-out, scoring, fallback repair, doc generation, code generation, and deploy.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Evaluation routing | `decision_gate.py` | chooses build vs fix vs scope-down |
| Council fan-out / scoring | `vibe_council.py` | parallel analysis + scoring axes |
| Idea shaping | `input_processor.py`, `enrich.py`, `experience_agent.py`, `inspiration_agent.py` | pre-council preparation |
| Repair loop | `fix_storm.py` | retry / scope reduction path |
| Build pipeline | `doc_generator.py`, `blueprint.py`, `prompt_strategist.py`, `code_generator.py`, `code_evaluator.py` | generation chain |
| Shipping | `deployer.py` | repo push, CI, build, deploy, verify |

## CONVENTIONS
- Follow the node order declared in `agent/graph.py`; that file is the source of truth for transitions.
- Return state fragments keyed for reducer-friendly merges; graph state uses `merge_dicts` for `council_analysis` and `scoring`.
- Preserve event-friendly phase names because SSE/dashboard code depends on them.
- Keep brainstorm-only behavior in dedicated brainstorm modules; do not leak build/deploy assumptions into that flow.
- Large node files are intentional hotspots; extend with surgical edits, not broad rewrites.

## ANTI-PATTERNS
- Do not rename node identifiers casually; `web/src/hooks/use-pipeline-monitor.ts` maps runtime node names to viz ids.
- Do not break loopback behavior from `fix_storm` or `code_evaluator` without updating graph routing and tests.
- Do not move deployment-stage semantics out of `deployer.py` without checking dashboard pipeline visuals and mocked events.
- Do not let node outputs drift from the shapes asserted in `agent/tests/`.

## NOTES
- `code_generator.py` and `deployer.py` are the biggest complexity hotspots in this repo.
- Many tests stub nodes by event name and phase string rather than importing deep implementation details.
