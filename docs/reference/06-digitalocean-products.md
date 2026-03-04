# DigitalOcean Product Ecosystem Reference

> All DO products available to complement Gradient AI in the hackathon.
> Using multiple DO products demonstrates deeper platform knowledge = higher scores.

## Quick Product Map

```
┌──────────────────────────────────────────────────────────────┐
│                      COMPUTE                                  │
│  App Platform (PaaS) │ Droplets (VMs) │ GPU Droplets │ K8s   │
├──────────────────────────────────────────────────────────────┤
│                      AI/ML                                    │
│  Gradient AI Platform │ Serverless Inference │ ADK            │
├──────────────────────────────────────────────────────────────┤
│                      DATA                                     │
│  PostgreSQL │ MySQL │ MongoDB │ Redis │ Kafka │ OpenSearch    │
├──────────────────────────────────────────────────────────────┤
│                    STORAGE                                    │
│  Spaces (S3) │ Volumes (Block) │ Container Registry           │
├──────────────────────────────────────────────────────────────┤
│                   NETWORKING                                  │
│  VPC │ Load Balancers │ Firewalls │ DNS │ CDN                 │
├──────────────────────────────────────────────────────────────┤
│                 SERVERLESS                                    │
│  Functions (FaaS) │ App Platform Workers/Jobs                 │
├──────────────────────────────────────────────────────────────┤
│                DEVELOPER TOOLS                                │
│  doctl CLI │ PyDo (Python) │ godo (Go) │ Terraform            │
└──────────────────────────────────────────────────────────────┘
```

---

## 1. App Platform (PaaS)

**Best for:** Deploying the web frontend and API backend fast.

| Feature | Details |
|---------|---------|
| **Auto-deploy** | Push-to-deploy from GitHub/GitLab/Bitbucket |
| **Buildpacks** | Auto-detect language (Node.js, Python, Go, Ruby, PHP, Rust, Bun) |
| **Dockerfile** | Native Docker support |
| **Components** | Web Services, Static Sites, Workers, Functions, Jobs |
| **Scaling** | Vertical + horizontal auto-scaling |
| **SSL** | Let's Encrypt auto-provisioned |
| **Custom Domains** | Free custom domain support |
| **DB Integration** | Direct managed database attachment |

**Component Types:**
- **Web Services** — HTTP-accessible apps (frontend, API)
- **Static Sites** — JAMstack/SPA (React, Vue, etc.)
- **Workers** — Background processing
- **Jobs** — One-time or scheduled (cron) tasks

---

## 2. Managed Databases

| Engine | Starting Price | Max Storage | Best For |
|--------|---------------|-------------|----------|
| **PostgreSQL** | ~$15/mo | 30 TB | App data, metadata, user accounts |
| **MySQL** | ~$15/mo | 20 TB | Traditional web apps |
| **MongoDB** | ~$15/mo | 16 TB | Document data, flexible schema |
| **Redis/Valkey** | ~$15/mo | 192 GB | Caching, rate limiting, sessions |
| **Kafka** | ~$15/mo | 1 TB | Event streaming, data pipelines |
| **OpenSearch** | ~$15/mo | 16 TB | Vector search, log analytics |

**All include:** Auto-backups, failover, SSL, VPC isolation, connection pooling, read replicas.

---

## 3. Spaces Object Storage (S3-Compatible)

| Feature | Value |
|---------|-------|
| **Base Plan** | $5/mo |
| **Included Storage** | 250 GiB |
| **Included Transfer** | 1 TiB outbound |
| **Inbound** | FREE |
| **CDN** | Built-in edge caching |
| **API** | Full S3 compatibility (boto3, AWS CLI) |

**Use for:** Model artifacts, datasets, generated images/audio, backups.

---

## 4. Functions (Serverless)

| Feature | Value |
|---------|-------|
| **Free Tier** | 90,000 GiB-seconds/month |
| **Max Timeout** | 15 minutes |
| **Runtimes** | Node.js, Python, Go, PHP |
| **Deploy** | doctl or App Platform |

**Use for:** Lightweight inference endpoints, webhooks, data processing.

---

## 5. Managed Kubernetes (DOKS)

| Feature | Value |
|---------|-------|
| **Control Plane** | FREE (HA included) |
| **Node Pricing** | From $12/node/mo |
| **GPU Support** | Schedule GPU workloads |
| **Autoscaling** | Cluster + node autoscaling |

**Use for:** Microservices, scaling inference, distributed workloads.

---

## 6. Container Registry (DOCR)

| Plan | Price | Repos | Storage |
|------|-------|-------|---------|
| **Starter** | FREE | 1 | 500 MiB |
| **Basic** | $5/mo | 5 | 5 GiB |
| **Professional** | $20/mo | Unlimited | 100 GiB |

**Use for:** Custom Docker images for ML inference containers.

---

## 7. Networking

| Service | Price | Purpose |
|---------|-------|---------|
| **VPC** | FREE | Private networking between resources |
| **Regional LB** | $12/mo | Single-region load balancing |
| **Global LB** | $24/mo | Multi-region with CDN |
| **Cloud Firewalls** | FREE | Network traffic filtering |
| **DNS** | FREE | Domain management |

---

## 8. Monitoring

| Service | Price | Features |
|---------|-------|----------|
| **Monitoring** | FREE | CPU, memory, disk, bandwidth graphs |
| **Uptime Checks** | 1 FREE | HTTP/HTTPS/Ping/TCP, 1-min intervals |
| **Alerts** | FREE | Email/Slack notifications |

---

## 9. Developer Tools

### doctl CLI
```bash
brew install doctl           # macOS
doctl auth init              # Authenticate
doctl compute droplet list   # List Droplets
doctl apps create --spec app.yaml  # Deploy App
```

### PyDo (Python SDK)
```bash
pip install pydo
```
```python
from pydo import Client
client = Client(token="your_token")
droplets = client.droplets.list()
```

### godo (Go SDK)
```go
import "github.com/digitalocean/godo"
client, _ := godo.NewClient(httpClient)
```

### Other
- **Terraform Provider** — Infrastructure as Code
- **digitalocean-js** — TypeScript/JavaScript (community)

---

## $200 Free Credits

- **URL:** https://mlh.link/digitalocean-signup
- **Valid:** 60 days
- **Applies to:** ALL products including GPU Droplets

**Estimated usage with $200:**

| Resource | Duration |
|----------|----------|
| GPU H100 (1x) | ~60 hours |
| GPU MI300X (1x) | ~100 hours |
| App Platform (basic) | Full hackathon period |
| Managed PostgreSQL | Full hackathon period |
| Spaces | Full hackathon period |

---

## Recommended Hackathon Architecture

```
┌─────────────────────────────────────────────────────────┐
│   App Platform (Next.js/React Frontend)    ← Free tier  │
│   + Custom Domain + SSL                                 │
└────────────────────┬────────────────────────────────────┘
                     │ API calls
┌────────────────────▼────────────────────────────────────┐
│   App Platform (Python/Node.js API)                     │
│   or Gradient ADK (Agent endpoint)                      │
└────────────────────┬────────────────────────────────────┘
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
┌─────────────┐ ┌────────┐ ┌────────────┐
│ Gradient AI │ │Postgres│ │  Spaces    │
│ Inference   │ │  (DB)  │ │ (Storage)  │
│ + Knowledge │ │        │ │            │
│   Bases     │ └────────┘ └────────────┘
│ + Agents    │
│ + Guardrails│
└─────────────┘
```
