# Deployment Status

> Last verified: 2026-03-18 (Asia/Seoul)

## Live URLs

| Service | URL | Status |
|---------|-----|--------|
| **Web Frontend** | https://vibedeploy-7tgzk.ondigitalocean.app | Serving |
| **API Health** | https://vibedeploy-7tgzk.ondigitalocean.app/health | `{"status":"ok"}` |
| **Dashboard** | https://vibedeploy-7tgzk.ondigitalocean.app/dashboard | Serving |
| **Zero-Prompt** | https://vibedeploy-7tgzk.ondigitalocean.app/zero-prompt | Serving (after deploy fix) |
| **API Models** | https://vibedeploy-7tgzk.ondigitalocean.app/api/models | Returns model config |
| **ZP Start** | https://vibedeploy-7tgzk.ondigitalocean.app/api/zero-prompt/start | POST endpoint |

## App Platform

| Property | Value |
|----------|-------|
| App ID | `1ffc4731-93e9-47e0-ac38-76658f8417b2` |
| Region | NYC |
| API component | Python 3.12, FastAPI, port 8080 |
| Web component | Node.js 20, Next.js 16.1.7, port 3000 |
| Auto-deploy | On push to `main` |

## Generated Demo Apps

| App | URL |
|-----|-----|
| FlavorSwap Lite | https://flavorswap-lite-637431-dl43t.ondigitalocean.app |
| GardenBreak | https://gardenbreak-377462-h9bmg.ondigitalocean.app |
| Creator Batch Studio | https://creator-batch-studio-640303-segyb.ondigitalocean.app |

## Environment Variables

Required environment variables are defined in `agent/.env.example`. For App Platform, they are configured in `.do/app.yaml` under each component's `envs` section.

### API Component Secrets

| Variable | Scope | Description |
|----------|-------|-------------|
| `DATABASE_URL` | RUN_TIME | PostgreSQL connection |
| `DIGITALOCEAN_INFERENCE_KEY` | RUN_TIME | DO Inference API key |
| `GRADIENT_MODEL_ACCESS_KEY` | RUN_TIME | DO Gradient model access |
| `DIGITALOCEAN_API_TOKEN` | RUN_TIME | DO API for app creation |
| `GITHUB_TOKEN` | RUN_TIME | Repo creation |
| `GITHUB_ORG` | RUN_TIME | Target org for repos |

### Web Component Variables

| Variable | Scope | Description |
|----------|-------|-------------|
| `NEXT_PUBLIC_AGENT_URL` | BUILD_TIME | API base URL (`${APP_URL}`) |
| `PORT` | RUN_TIME | `3000` |
| `HOSTNAME` | RUN_TIME | `0.0.0.0` |

## Build Command (API)

The API build uses a split install to work around the `langchain-gradient` / `langchain-core` version conflict:

```bash
pip install langchain-gradient>=0.1.24 --no-deps && \
grep -v '^langchain-gradient' requirements.txt > /tmp/req-filtered.txt && \
pip install -r /tmp/req-filtered.txt
```

This mirrors the CI pipeline approach in `.github/workflows/ci.yml`.

## Deployment Methods

### Auto-deploy (recommended)

Push to `main` triggers automatic deployment via App Platform.

### Manual via doctl

```bash
doctl apps create-deployment 1ffc4731-93e9-47e0-ac38-76658f8417b2
```

### Full deploy via script

```bash
export DIGITALOCEAN_API_TOKEN=...
export DIGITALOCEAN_INFERENCE_KEY=...
export GITHUB_TOKEN=...
cd agent && bash scripts/deploy.sh
```

## Monitoring

```bash
# App Platform logs
doctl apps logs 1ffc4731-93e9-47e0-ac38-76658f8417b2 --type=run
doctl apps logs 1ffc4731-93e9-47e0-ac38-76658f8417b2 --type=build

# Gradient agent
gradient agent logs

# Check deployment status
doctl apps list-deployments 1ffc4731-93e9-47e0-ac38-76658f8417b2 --format ID,Phase,CreatedAt
```

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| API build fails | `langchain-gradient` version conflict | Already fixed in `.do/app.yaml` build command |
| `/zero-prompt` 404 | Old deployment serving | Push to main to trigger new deploy |
| All models show `openai-gpt-oss-120b` | External API keys not set in App Platform | Add `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` to app envs |
| Health returns `adk_url_configured: false` | `VIBEDEPLOY_ADK_URL` not set | Set in App Platform envs after ADK deploy |
