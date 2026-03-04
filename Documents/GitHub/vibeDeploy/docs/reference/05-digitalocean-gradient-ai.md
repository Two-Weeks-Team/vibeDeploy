# DigitalOcean Gradient AI - Technical Reference

> The CORE technology requirement for this hackathon.
> Must use "DigitalOcean Gradient AI full-stack features" to be eligible.

## What is Gradient AI?

DigitalOcean Gradient is a **unified AI cloud platform** with three pillars:

| Pillar | What It Does |
|--------|-------------|
| **Gradient Infrastructure** | GPU Droplets, Bare Metal GPUs, vector databases, optimized software |
| **Gradient Platform** | Build and monitor intelligent agents with RAG, function calling, evaluations |
| **Gradient Applications** | Pre-built agents for specific use cases (SRE automation, support, etc.) |

Philosophy: **"Bring your agent code, we handle the rest."**

---

## 1. Serverless Inference API

Access foundation models directly via API without managing infrastructure.

**Endpoint:** `https://inference.do-ai.run`

### Available API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /v1/models` | List available models |
| `POST /v1/chat/completions` | Chat-style prompts |
| `POST /v1/responses` | Text/multimodal responses |
| `POST /v1/images/generations` | Image generation |
| `POST /v1/async-invoke` | Async requests for fal models |

### Foundation Models (Complete Catalog, March 2026)

#### Tier 1: Frontier (Code/Agent 최적)

| Model | Model ID | Context | In/Out Price | Tool Call | Cache | Best For |
|-------|----------|---------|-------------|-----------|-------|----------|
| **Claude Opus 4.6** | `anthropic-claude-opus-4.6` | **1M** | $5/$25 | ✅ | ✅ | 대규모 코드베이스 리팩토링 |
| **GPT-5.3-Codex** | `openai-gpt-5.3-codex` | **400K** | $1.75/$14 | ✅ | ✅ | 에이전틱 코딩, 멀티스텝 워크플로우 |
| **Claude Sonnet 4.6** | `anthropic-claude-4.6-sonnet` | **1M** | $3/$15 | ✅ | ✅ | **코드 가성비 최강** |

#### Tier 2: High Performance

| Model | Model ID | Context | In/Out Price | Tool Call | Cache |
|-------|----------|---------|-------------|-----------|-------|
| Claude Opus 4.5 | `anthropic-claude-opus-4.5` | 200K+ | $5/$25 | ✅ | ✅ |
| Claude Sonnet 4.5 | `anthropic-claude-4.5-sonnet` | 1M | $3/$15 | ✅ | ✅ |
| Claude Sonnet 4 | `anthropic-claude-sonnet-4` | 1M | $3/$15 | ✅ | ✅ |
| GPT-5.2 | `openai-gpt-5.2` | 128K | $1.75/$14 | ✅ | ✅ |
| GPT-5 | `openai-gpt-5` | 128K | $1.25/$10 | ✅ | ✅ |

#### Tier 3: Cost-Optimized

| Model | Model ID | Context | In/Out Price | Tool Call | Cache |
|-------|----------|---------|-------------|-----------|-------|
| **GPT-5 mini** | `openai-gpt-5-mini` | 128K | $0.25/$2 | ✅ | ✅ |
| **GPT-5 nano** | `openai-gpt-5-nano` | 128K | $0.05/$0.40 | ✅ | ✅ |
| Claude Haiku 4.5 | `anthropic-claude-4.5-haiku` | 128K | $1/$5 | ✅ | ❌ |
| GPT-4o mini | `openai-gpt-4o-mini` | 128K | $0.15/$0.60 | ✅ | ✅ |

#### Tier 4: Open Source & Specialized

| Model | Model ID | Context | In/Out Price | Tool Call | Cache |
|-------|----------|---------|-------------|-----------|-------|
| Llama 3.3 70B | `llama3.3-70b-instruct` | 128K | $0.65/$0.65 | ❌ | ❌ |
| GPT-oss-120b | `openai-gpt-oss-120b` | 128K | $0.10/$0.70 | ❌ | ❌ |
| GPT-oss-20b | `openai-gpt-oss-20b` | 128K | $0.05/$0.45 | ❌ | ❌ |
| DeepSeek R1 Distill | `deepseek-r1-distill-llama-70b` | 128K | $0.99/$0.99 | ❌ | ❌ |
| Qwen3-32B | `alibaba-qwen3-32b` | 128K | $0.25/$0.55 | ❌ | ❌ |

#### Reasoning Models

| Model | Model ID | In/Out Price | Tool Call |
|-------|----------|-------------|-----------|
| o1 | `openai-o1` | $15/$60 | ✅ |
| o3 | `openai-o3` | $2/$8 | ✅ |
| o3-mini | `openai-o3-mini` | $1.10/$4.40 | ✅ |

#### Multimodal (Serverless Inference Only — NOT available in ADK agents)

| Model | Type | Pricing |
|-------|------|---------|
| GPT-image-1 | Image Gen | $5/$40 per 1M tokens |
| Fast SDXL (fal) | Image Gen | $0.0011/compute sec |
| Flux Schnell (fal) | Image Gen | $0.0030/megapixel |
| Stable Audio 2.5 (fal) | Audio Gen | $0.00058/compute sec |
| Multilingual TTS v2 (fal) | TTS | $0.10/1K chars |

### Critical: Tool Calling Support

> **Anthropic + OpenAI 모델만 Tool/Function Calling 지원.**
> Llama, DeepSeek, Qwen, Mistral은 Tool Calling 불가 → 에이전트 핵심 루프에 사용 불가.

### Embedding Models

| Model | Token Window | Price (per 1M) | Best For |
|-------|-------------|----------------|----------|
| gte-large-en-v1.5 | 8,192 | $0.09 | 긴 문서 (추천) |
| all-mini-lm-l6-v2 | 256 | $0.009 | 가벼운 임베딩 |
| multi-qa-mpnet-base | 512 | $0.009 | QA 검색 |
| Qwen3 Embedding 0.6B | 8,000 | varies | 다국어 |

### Benchmarks (Feb 2026)

| Model | SWE-bench | Terminal-Bench 2.0 | GPQA Diamond |
|-------|-----------|-------------------|--------------|
| **Claude Opus 4.6** | **79.4%** | — | **77.3%** |
| **GPT-5.3-Codex** | — | **77.3%** | — |
| Claude Sonnet 4.6 | 73.2% | — | 72.1% |

### vibeDeploy 모델 배정

| 역할 | 모델 | 비용 | 이유 |
|------|------|------|------|
| Supervisor (Orchestrator) | GPT-5.3-Codex | $1.75/1M | 에이전틱 특화, Tool Calling |
| Code/Doc Generator | Claude Sonnet 4.6 | $3/$15 per 1M | SWE-bench 73.2%, 1M ctx |
| Vibe Council (6 agents) | GPT-5 mini | $0.25/$2 per 1M | 분석에 충분, 저비용 |
| Cross-Examination | GPT-5 | $1.25/$10 per 1M | 에이전트 간 토론/반박 |
| Fallback | GPT-5 nano | $0.05/$0.40 per 1M | 최저가, Tool Calling ✅ |

---

## 2. Agent Development Kit (ADK) - PUBLIC PREVIEW

**The recommended way to build agents on Gradient AI.**

### Installation & CLI

```bash
pip install gradient-adk
```

```bash
gradient agent init          # Initialize project
gradient agent run           # Local testing with hot-reload
gradient agent deploy        # Deploy to DigitalOcean
gradient agent logs          # View runtime logs
gradient agent traces        # Open traces UI
gradient agent evaluate      # Run evaluations
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Framework Agnostic** | Works with LangGraph, LangChain, CrewAI, PydanticAI, custom code |
| **One-Command Deploy** | `gradient agent deploy` |
| **FREE During Preview** | No compute hosting costs during public preview |
| **Built-in Observability** | Automatic traces, evaluations, insights |
| **Streaming Support** | Real-time response streaming |

### ADK Resources

- **ADK GitHub**: https://github.com/digitalocean/gradient-adk
- **ADK Templates**: https://github.com/digitalocean/gradient-adk-templates
- **CUA Chat Template**: https://github.com/digitalocean/template-app-platform-gradient-cua-chat

---

## 3. Agent Platform Features

### Knowledge Bases (RAG)
- Auto-indexing from **S3, Dropbox, Spaces, URLs, files**
- Vector storage via managed **OpenSearch**
- Chunking and embedding automated
- Re-indexing only when changes detected

**Pricing:**
- Indexing: $0.009-$0.09 per 1M tokens (depends on embedding model)
- Storage: Billed via OpenSearch

### Multi-Agent Routing
- Route queries between specialized agents
- Orchestration layer for complex workflows

### Function Calling
- Call external APIs
- Invoke DigitalOcean Functions
- Custom tool integrations

### Guardrails

| Guardrail | Purpose | Price (per 1M tokens) |
|-----------|---------|----------------------|
| Sensitive Data Detection | Anonymize PII, credit cards | $0.34 |
| Jailbreak Detection | Prevent malicious inputs | $0.20 |
| Content Moderation | Filter violence, hate, etc. | $0.20 |

### Agent Evaluations
- **19 built-in metrics**: correctness, tone, toxicity, etc.
- Automated testing pipeline
- Compare model versions

### Agent Tracing
- Step-by-step timeline
- Token usage tracking
- Processing time per step
- Debug and optimize

### Version Management
- Track changes across deployments
- Rollback to previous versions

---

## 4. GPU Droplets

### Available GPUs

| GPU | VRAM | On-Demand | Use Case |
|-----|------|-----------|----------|
| **NVIDIA HGX H100** | 80 GB HBM3 | $3.39/GPU/hr | Training, inference, HPC |
| **NVIDIA HGX H200** | 141 GB HBM3e | $3.44/GPU/hr | Large model inference |
| **AMD MI300X** | 192 GB HBM3 | $1.99/GPU/hr | Training, inference (best value) |
| **AMD MI325X** | 256 GB | ~$2.10/GPU/hr | Training, fine-tuning |
| **AMD MI350X** | 288 GB | ~$3.18/GPU/hr | Next-gen AI workloads |

### Per-GPU Specs

| Resource | Value |
|----------|-------|
| Memory | 240 GiB |
| vCPUs | 20 |
| Boot Disk | 720 GiB NVMe |
| Scratch Disk | 5 TiB NVMe |
| Transfer | 15,000 GiB |
| GPUs/Droplet | 1 or 8 |

**Pre-installed:** Python, PyTorch, CUDA, FlashAttention-3, FP8 quantization

---

## 5. Python SDK

```bash
pip install gradient          # Serverless inference
pip install gradient-adk      # Agent Development Kit
```

### Usage

```python
from gradient import Gradient, AsyncGradient

# Serverless Inference (sync)
client = Gradient(model_access_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"])
response = client.chat.completions.create(
    model="openai-gpt-5-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Serverless Inference (async — recommended for agents)
async_client = AsyncGradient(model_access_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"])
response = await async_client.chat.completions.create(
    model="anthropic-claude-4.6-sonnet",
    messages=[{"role": "user", "content": "Hello!"}]
)

# LangGraph Integration (recommended for agent nodes)
from langchain_gradient import ChatGradient
llm = ChatGradient(model="openai-gpt-5-mini", temperature=0.3)

# Knowledge Base Retrieval
kb_client = Gradient(access_token=os.environ["DIGITALOCEAN_API_TOKEN"])
results = kb_client.retrieve.documents(
    knowledge_base_id=os.environ["DIGITALOCEAN_KB_ID"],
    query="search query",
    num_results=5
)

# Agent Management
api_client = Gradient(access_token=os.environ["DIGITALOCEAN_API_TOKEN"])
agents = api_client.agents.list()
```

### Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `DIGITALOCEAN_API_TOKEN` | Deployment, agent management, KB access | Yes |
| `DIGITALOCEAN_INFERENCE_KEY` | Model inference (Serverless API) | Yes |
| `DIGITALOCEAN_KB_ID` | Knowledge Base ID (if using RAG) | Optional |

---

## 6. API Reference Links

| Resource | URL |
|----------|-----|
| **Gradient AI Docs** | https://docs.digitalocean.com/products/gradient-ai-platform |
| **REST API** | https://docs.digitalocean.com/reference/api/digitalocean/#tag/GradientAI-Platform |
| **Python SDK Docs** | https://gradientai-sdk.digitalocean.com/api/python |
| **ADK GitHub** | https://github.com/digitalocean/gradient-adk |
| **Pricing** | https://www.digitalocean.com/pricing/gradient-platform |
| **GPU Pricing** | https://www.digitalocean.com/pricing/gpu-droplets |

---

## Hackathon Integration Strategy

To score maximum on "Technological Implementation" criteria:

```
USE MULTIPLE GRADIENT AI FEATURES:
├── Serverless Inference API (chat completions)
├── Knowledge Bases (RAG with auto-indexing)
├── Agent Platform (multi-agent routing)
├── Guardrails (content moderation)
├── Evaluations (quality metrics)
├── Tracing (observability)
└── ADK (deployment)
```

The more Gradient AI features integrated, the stronger the submission.
