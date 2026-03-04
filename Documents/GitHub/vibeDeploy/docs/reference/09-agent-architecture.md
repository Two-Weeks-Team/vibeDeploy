# Agent Development Kit - Official Docs Text (Original)

Source URL: https://docs.digitalocean.com/products/gradient-ai-platform/getting-started/use-adk/
Fetched: 2026-03-04 (Asia/Seoul)

Use Agent Development Kit to Build, Test, and Deploy Agents (public)

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

The Agent Development Kit (ADK) is an SDK to build, test, and deploy agent workflows from within your development environments.

Prerequisites
- Python version 3.10 or higher.
- ADK Feature Preview enabled.
- API access keys:
  - GRADIENT_MODEL_ACCESS_KEY
  - DIGITALOCEAN_API_TOKEN
- An .env file with those variables.
- A requirements.txt file at the root of the folder or repo.

Build New Agent
1. Initialize a new agent project:
   gradient agent init

Directory structure created by init:
- main.py
- .gradient/agent.yml
- requirements.txt
- .env
- agents/
- tools/

2. Run and test locally:
   gradient agent run

3. Deploy agent:
   export DIGITALOCEAN_API_TOKEN="<your_api-token>"
   gradient agent deploy

4. Test deployed endpoint using POST /run.

The documentation notes deployment typically takes 1 to 5 minutes and returns a deployment URL after success.
