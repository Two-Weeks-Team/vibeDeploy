# EXTERNAL TOOLS

## OVERVIEW
`agent/tools/` wraps external systems: DigitalOcean, GitHub, YouTube, web retrieval, image generation, and function-call surfaces used by the pipeline.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| DO app operations | `digitalocean.py` | deploy metadata, run commands, app listing |
| Function-call bridge | `function_tools.py` | tool contracts exposed to agents |
| GitHub repo operations | `github.py` | repo creation, workflow checks, CI repair inputs |
| Search / retrieval | `web_search.py`, `knowledge_base.py` | web + KB retrieval helpers |
| Media intake | `youtube.py`, `image_gen.py` | inspiration intake and generated imagery |
| Deploy call sites | `../nodes/deployer.py`, `../server.py` | main consumers of tool output |

## CONVENTIONS
- Prefer existing wrappers over ad hoc SDK calls from nodes.
- Keep auth in environment variables; tooling should degrade cleanly when secrets are missing.
- Return structured fallback payloads instead of exploding route handlers on external failures.
- Match the deploy/runtime command vocabulary already embedded in `digitalocean.py` and `deployer.py`.

## ANTI-PATTERNS
- Do not bake secrets or org names into new helpers; `GITHUB_ORG` and DO keys already flow from env/config.
- Do not couple tool return shapes to one caller unless the shape is enforced by tests.
- Do not add async SQLAlchemy or unrelated infra assumptions here; this directory is external integration only.

## NOTES
- Search/KB helpers are allowed to fail closed; tests already cover missing-env scenarios.
- Tool-level behavior often appears in generated prompts and deployment orchestration, so contract drift ripples outward fast.
- `github.py` and `digitalocean.py` are the most deployment-sensitive helpers; shape changes there ripple into CI/deploy flows.

## COMMANDS
```bash
cd agent && pytest tests/test_knowledge_base.py -v --tb=short
cd agent && pytest tests/test_deployer.py -v --tb=short
cd agent && pytest tests/test_runtime_config.py -v --tb=short
```
