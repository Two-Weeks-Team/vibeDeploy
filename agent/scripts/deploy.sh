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

if [ -z "${DIGITALOCEAN_INFERENCE_KEY:-}" ]; then
  echo "Error: DIGITALOCEAN_INFERENCE_KEY not set"
  exit 1
fi

echo "Step 1: Deploy Gradient ADK Agent"
echo "================================="
cd "$AGENT_DIR"

gradient secret set DIGITALOCEAN_INFERENCE_KEY="$DIGITALOCEAN_INFERENCE_KEY"
gradient secret set DIGITALOCEAN_API_TOKEN="$DIGITALOCEAN_API_TOKEN"
gradient secret set GITHUB_TOKEN="${GITHUB_TOKEN:-}"
gradient secret set GITHUB_ORG="${GITHUB_ORG:-Two-Weeks-Team}"

echo "Deploying agent..."
gradient agent deploy

AGENT_URL=$(gradient agent status 2>/dev/null | grep -o 'https://agents.do-ai.run[^ ]*' || echo "")
echo "Agent URL: ${AGENT_URL:-'Check DO Console for URL'}"

echo ""
echo "Step 2: Deploy App Platform (Frontend + API + DB)"
echo "=================================================="
cd "$ROOT_DIR"

if command -v doctl &>/dev/null; then
  EXISTING_APP=$(doctl apps list --format ID,Spec.Name --no-header 2>/dev/null | grep vibedeploy | awk '{print $1}' || echo "")

  if [ -n "$EXISTING_APP" ]; then
    echo "Updating existing app: $EXISTING_APP"
    doctl apps update "$EXISTING_APP" --spec .do/app.yaml
  else
    echo "Creating new app..."
    doctl apps create --spec .do/app.yaml
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
echo "3. Update NEXT_PUBLIC_AGENT_URL in App Platform env vars"
