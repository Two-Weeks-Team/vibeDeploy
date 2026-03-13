#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$AGENT_DIR")"

echo "=== vibeDeploy Deployment ==="
echo ""

if [ -z "${DIGITALOCEAN_API_TOKEN:-}" ]; then
  echo "Error: DIGITALOCEAN_API_TOKEN not set"
  exit 1
fi

MODEL_ACCESS_KEY="${GRADIENT_MODEL_ACCESS_KEY:-${DIGITALOCEAN_INFERENCE_KEY:-}}"

if [ -z "${MODEL_ACCESS_KEY:-}" ]; then
  echo "Error: GRADIENT_MODEL_ACCESS_KEY (or DIGITALOCEAN_INFERENCE_KEY) not set"
  exit 1
fi

echo "Step 1: Deploy Gradient ADK Agent"
echo "================================="
cd "$AGENT_DIR"

gradient secret set DIGITALOCEAN_INFERENCE_KEY="$MODEL_ACCESS_KEY"
gradient secret set GRADIENT_MODEL_ACCESS_KEY="$MODEL_ACCESS_KEY"
gradient secret set DIGITALOCEAN_API_TOKEN="$DIGITALOCEAN_API_TOKEN"
gradient secret set GITHUB_TOKEN="${GITHUB_TOKEN:-}"
gradient secret set GITHUB_ORG="${GITHUB_ORG:-Two-Weeks-Team}"

echo "Deploying agent..."
DEPLOY_OUTPUT="$(gradient agent deploy 2>&1)"
printf '%s\n' "$DEPLOY_OUTPUT"

AGENT_URL="$(printf '%s\n' "$DEPLOY_OUTPUT" | grep -o 'https://agents.do-ai.run[^[:space:]]*' | head -n 1 || true)"
if [ -z "$AGENT_URL" ] && [ -n "${VIBEDEPLOY_ADK_URL:-}" ]; then
  AGENT_URL="$VIBEDEPLOY_ADK_URL"
fi
echo "Agent URL: ${AGENT_URL:-'Check DO Console for URL'}"

echo ""
echo "Step 2: Deploy App Platform (Frontend + API + DB)"
echo "=================================================="
cd "$ROOT_DIR"

if command -v doctl &>/dev/null; then
  APP_SPEC=".do/app.yaml"
  TEMP_SPEC="$(mktemp)"
  export VIBEDEPLOY_RENDERED_ADK_URL="${AGENT_URL:-${VIBEDEPLOY_ADK_URL:-}}"
  python - "$APP_SPEC" "$TEMP_SPEC" <<'PY'
import os
import sys
from pathlib import Path

source_path = Path(sys.argv[1])
target_path = Path(sys.argv[2])
rendered = source_path.read_text()
replacements = {
    "ENC[REPLACE_WITH_DB_URL]": os.getenv("DATABASE_URL", ""),
    "REPLACE_WITH_MODEL_ACCESS_KEY": os.getenv("GRADIENT_MODEL_ACCESS_KEY", "") or os.getenv("DIGITALOCEAN_INFERENCE_KEY", ""),
    "REPLACE_WITH_API_TOKEN": os.getenv("DIGITALOCEAN_API_TOKEN", ""),
    "REPLACE_WITH_GITHUB_TOKEN": os.getenv("GITHUB_TOKEN", ""),
    "REPLACE_WITH_KB_ID": os.getenv("DO_KNOWLEDGE_BASE_ID", ""),
    "REPLACE_WITH_ADK_URL": os.getenv("VIBEDEPLOY_RENDERED_ADK_URL", ""),
    "REPLACE_WITH_ADK_AUTH_TOKEN": (
        os.getenv("VIBEDEPLOY_ADK_AUTH_TOKEN", "")
        or os.getenv("GRADIENT_AGENT_ACCESS_KEY", "")
    ),
}
for placeholder, value in replacements.items():
    rendered = rendered.replace(placeholder, value)
target_path.write_text(rendered)
PY
  SPEC_TO_APPLY="$TEMP_SPEC"
  EXISTING_APP=$(doctl apps list --format ID,Spec.Name --no-header 2>/dev/null | grep vibedeploy | awk '{print $1}' || echo "")

  if [ -n "$EXISTING_APP" ]; then
    echo "Updating existing app: $EXISTING_APP"
    doctl apps update "$EXISTING_APP" --spec "$SPEC_TO_APPLY"
  else
    echo "Creating new app..."
    doctl apps create --spec "$SPEC_TO_APPLY"
  fi
  if [ "${TEMP_SPEC:-}" != "" ] && [ -f "$TEMP_SPEC" ]; then
    rm -f "$TEMP_SPEC"
  fi
else
  echo "doctl not installed. Install: brew install doctl"
  echo "Then run: doctl apps create --spec .do/app.yaml"
fi

echo ""
echo "Step 3: Create Knowledge Base"
echo "=============================="
cd "$AGENT_DIR"
source .venv/bin/activate 2>/dev/null || true
python scripts/create_knowledge_base.py

echo ""
echo "=== Deployment Complete ==="
echo "1. ADK Agent: ${AGENT_URL:-'Check DO Console'}"
echo "2. App Platform: Check DO Console → Apps → vibedeploy"
echo "3. VIBEDEPLOY_ADK_URL wired to the deployed ADK agent when available"
echo "4. Prefer VIBEDEPLOY_ADK_AUTH_TOKEN or GRADIENT_AGENT_ACCESS_KEY for gateway auth"
