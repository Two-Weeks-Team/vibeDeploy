# vibeDeploy — Product Concept

> **"한 줄의 아이디어 → AI 팀 회의 → MVP 개발 → DigitalOcean 배포"**

## One-Liner

문장 하나 또는 YouTube URL을 입력하면, **The Vibe Council** — 6명의 전문 AI 에이전트가
라이브 토론을 벌이고, Vibe Score로 실현 가능성을 판정한다.
GO 판정이 나면 실제 MVP를 개발하여 DigitalOcean에 배포하고 라이브 URL을 제공한다.

---

## 핵심 차별점

| 기존 바이브코딩 도구 | vibeDeploy |
|---|---|
| 코드 생성까지만 | 아이디어 → **배포된 라이브 앱**까지 |
| 단일 AI가 코드 작성 | **다중 전문가 AI 팀이 회의하여** 의사결정 |
| 결과물의 품질을 사용자가 판단 | AI 팀이 **자체적으로 실현가능성 검증** |
| 배포는 별도 작업 | DigitalOcean에 **자동 배포 + 라이브 URL** |
| "만들어줘"만 가능 | **YouTube 영상 URL**로도 프로젝트 시작 가능 |

---

## 유저 플로우

### Input 형태 (2가지)

**A. 텍스트 (문장)**
```
"식당 예약 대기열을 관리하는 웹앱을 만들고 싶어.
손님이 QR코드를 스캔하면 대기열에 등록되고,
순서가 오면 카톡 알림을 받는 서비스."
```

**B. YouTube URL**
```
https://www.youtube.com/watch?v=xxxxxxx
→ 영상에서 아이디어/프로덕트 컨셉 자동 추출
```

### Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: INPUT PROCESSING                                │
│                                                         │
│  텍스트 → 아이디어 구조화                                 │
│  YouTube URL →                                           │
│    1) 트랜스크립트 추출 (with timestamps)                  │
│    2) 키 세그먼트 탐지 ("여기 보시면", "데모", "화면")       │
│    3) 해당 타임스탬프 프레임 추출 (yt-dlp + ffmpeg)         │
│    4) GPT-4o (vision)로 프레임 분석                        │
│    5) 텍스트 + 시각 컨텍스트 결합 → 아이디어 구조화          │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 2: VIBE COUNCIL MEETING (AI 에이전트 라이브 토론)     │
│                                                         │
│  🏗️ Architect — 기술 스택, 복잡도, 구현 가능성 분석         │
│  🔭 Scout — 시장 조사, 경쟁 분석, 트렌드 파악              │
│  🛡️ Guardian — 보안, 법적 이슈, 실패 시나리오 분석          │
│  ⚡ Catalyst — 독창성, 혁신 잠재력, 임팩트 평가             │
│  🎯 Advocate — 사용자 관점, 접근성, 도입 장벽 분석          │
│  🧭 Strategist — 종합, 스코어링, 최종 판정                 │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 3: DECISION GATE                                   │
│                                                         │
│  ┌─────────────┐          ┌──────────────────────────┐  │
│  │ NOT FEASIBLE │          │ FEASIBLE                 │  │
│  │              │          │                          │  │
│  │ • 이유 설명   │          │ • PRD 생성               │  │
│  │ • 부족한 부분  │          │ • Tech Spec 생성         │  │
│  │ • 대안 제시   │          │ • DO 아키텍처 설계        │  │
│  │ • 개선 방향   │          │ • 비용 추정              │  │
│  └─────────────┘          └──────────┬───────────────┘  │
└─────────────────────────────────────┬───────────────────┘
                                      ▼ (feasible일 때만)
┌─────────────────────────────────────────────────────────┐
│ Phase 4: DOCUMENT GENERATION                             │
│                                                         │
│  • PRD (Product Requirements Document)                   │
│  • Technical Architecture (DO-optimized)                 │
│  • API Spec / Database Schema                           │
│  • Frontend Component Tree                              │
│  • Deployment Config (App Spec YAML)                    │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 5: DEVELOPMENT                                     │
│                                                         │
│  Frontend Agent → Next.js/React 코드 생성                │
│  Backend Agent → FastAPI/Express 코드 생성               │
│  Integration → API 연결, DB 설정                         │
│  Testing → 기본 동작 검증                                │
└────────────────────────┬────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 6: DEPLOYMENT                                      │
│                                                         │
│  GitHub Repo 생성 (자동)                                 │
│  DO App Platform 배포 (PyDo SDK)                         │
│  Managed DB 프로비저닝 (필요시)                           │
│  ✅ 라이브 URL 제공: https://xxx.ondigitalocean.app      │
└─────────────────────────────────────────────────────────┘
```

---

## The Vibe Council — AI 에이전트 라이브 토론

vibeDeploy 고유의 의사결정 프레임워크. 6명의 전문 AI 에이전트가 서로 **도전하고 반박하는 라이브 토론**을 통해 아이디어를 검증한다.

### 에이전트 역할

| Agent | Role | 성격 | 초점 | 핵심 질문 |
|-------|------|------|------|---------|
| 🏗️ **Architect** | Technical Lead | 정밀하고 체계적 | 기술 스택, 복잡도, 구현 가능성 | "이걸 어떻게 만들 것인가?" |
| 🔭 **Scout** | Market Analyst | 호기심 많고 데이터 중심 | 경쟁 분석, 트렌드, 시장 적합성 | "누가 이걸 원하는가?" |
| 🛡️ **Guardian** | Risk Assessor | 신중하고 꼼꼼 | 보안, 법적 이슈, 실패 시나리오 | "왜 실패할 수 있는가?" |
| ⚡ **Catalyst** | Innovation Officer | 열정적이고 비전적 | 독창성, 파괴적 잠재력, 임팩트 | "이게 왜 특별한가?" |
| 🎯 **Advocate** | UX Champion | 공감적이고 실용적 | 사용자 관점, 접근성, 도입 장벽 | "사용자가 실제로 쓸까?" |
| 🧭 **Strategist** | Session Lead | 균형잡히고 결단력 있음 | 종합, 스코어링, 최종 판정 | "결론은 무엇인가?" |

### 회의 프로세스 (4 Phase)

```
Phase 1: INDIVIDUAL ANALYSIS (병렬 실행)
  → 각 에이전트가 자기 관점에서 아이디어를 독립 분석
  → Architect: 기술 스택/복잡도 평가
  → Scout: 시장 데이터/경쟁 분석
  → Guardian: 리스크/법적 이슈 식별
  → Catalyst: 혁신성/차별점 평가
  → Advocate: UX/접근성 평가

Phase 2: CROSS-EXAMINATION (순차 토론)
  → Architect ↔ Guardian: 기술적 리스크에 대한 공방
  → Scout ↔ Catalyst: 시장 현실 vs 혁신 잠재력 토론
  → Advocate가 양측 도전: "사용자 관점에서 이건..."
  → 각 에이전트가 상대 의견에 반박하거나 수용

Phase 3: SCORING (병렬 채점)
  → 토론 결과를 반영하여 각 에이전트가 자기 축에서 0-100점 부여
  → Cross-Examination 결과에 따라 초기 분석에서 점수 조정

Phase 4: VERDICT (Strategist 종합)
  → Strategist가 5축 가중 평균 산출 = Vibe Score™
  → Decision Gate 적용 → GO / CONDITIONAL / NO-GO
```

---

## Scoring System (점수 체계)

### 5개 평가 축 (Dimension)

각 에이전트가 자신의 전문 영역에서 0-100점을 부여한다.

| 축 | 채점 에이전트 | 가중치 | 평가 대상 |
|---|---|---|---|
| **Technical Feasibility** | 🏗️ Architect | **25%** | 기술적으로 구현 가능한가? 스택, 복잡도, 타임라인 |
| **Market Viability** | 🔭 Scout | **20%** | 시장 수요가 있는가? 경쟁, 트렌드, 적합성 |
| **Innovation Score** | ⚡ Catalyst | **20%** | 얼마나 독창적인가? 파괴적 잠재력, 임팩트 |
| **Risk Profile** | 🛡️ Guardian | **20%** | 리스크가 감당 가능한가? (역채점: 리스크 낮을수록 고점) |
| **User Impact** | 🎯 Advocate | **15%** | 사용자가 실제로 쓸까? 접근성, 도입 장벽, UX |

> 🧭 Strategist는 채점하지 않음 — 종합 및 판정만 담당

### Vibe Score™ 산출 공식

```
Vibe Score™ = (Tech × 0.25) + (Market × 0.20) + (Innovation × 0.20) + ((100 - Risk) × 0.20) + (UserImpact × 0.15)
```

### Decision Gate (3단계 판정)

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│   Score ≥ 75   →  🟢 GO: 즉시 개발 + 배포 진행       │
│                                                      │
│   50 ≤ Score < 75 →  🟡 CONDITIONAL: 조건부 진행     │
│     → 부족한 축을 명시하고 스코프 축소안 제시           │
│     → 사용자가 수정안 수락 시 개발 진행                │
│                                                      │
│   Score < 50   →  🔴 NO-GO: 개발 불가 판정           │
│     → 실패 사유 상세 리포트                           │
│     → 개선 방향 및 대안 아이디어 제시                  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 각 축별 채점 기준 (Rubric)

#### Technical Feasibility (Architect, 25%)

| 점수 | 기준 |
|------|------|
| 90-100 | 표준 스택으로 바로 구현 가능. 외부 의존성 없음. |
| 70-89 | 구현 가능하지만 일부 복잡한 연동 필요 (결제, 실시간 등) |
| 50-69 | 구현 가능하지만 MVP 스코프 대폭 축소 필요 |
| 30-49 | 핵심 기능에 해결 불가능한 기술적 난제 존재 |
| 0-29 | 현재 기술로 구현 불가능하거나 비현실적 |

#### Market Viability (Scout, 20%)

| 점수 | 기준 |
|------|------|
| 90-100 | 검증된 시장 수요 + 명확한 차별점 + 수익 모델 |
| 70-89 | 시장 수요 존재하지만 경쟁 치열 or 차별점 약함 |
| 50-69 | 잠재 수요는 있지만 검증 부족 |
| 30-49 | 니치 시장이거나 수익화 어려움 |
| 0-29 | 시장 수요 없음 or 이미 완전히 해결된 문제 |

#### Innovation Score (Catalyst, 20%)

| 점수 | 기준 |
|------|------|
| 90-100 | 완전히 새로운 접근. 기존에 없는 솔루션 |
| 70-89 | 기존 아이디어에 의미 있는 혁신 추가 |
| 50-69 | 약간의 차별점이 있지만 대부분 기존 패턴 |
| 30-49 | 거의 차별점 없음. 레드오션 |
| 0-29 | 완전히 기존 것과 동일. 혁신 없음 |

#### User Impact (Advocate, 15%)

| 점수 | 기준 |
|------|------|
| 90-100 | 2-3 페이지로 핵심 UX 구현 가능. 표준 UI 패턴 |
| 70-89 | 구현 가능하지만 복잡한 인터랙션 필요 (드래그, 실시간 등) |
| 50-69 | 많은 페이지/상태 관리 필요. MVP 스코프 축소 시 가능 |
| 30-49 | 시각적으로 복잡하거나 UX 자체가 불명확 |
| 0-29 | 웹으로 표현 불가능한 경험 (VR, 하드웨어 필요 등) |

#### Risk Profile (Guardian, 20%) — 역채점

| 점수 | 기준 |
|------|------|
| 90-100 | 리스크 거의 없음. 법적/기술적/보안 이슈 없음 |
| 70-89 | 경미한 리스크. 완화 방안 명확 |
| 50-69 | 중간 리스크. 일부 해결 불확실 |
| 30-49 | 심각한 리스크 (개인정보, 법적 이슈, 보안 취약점) |
| 0-29 | 치명적 blocker 존재 (불법, 불가능, 위험) |

### 점수 예시

**입력:** "식당 예약 대기열을 관리하는 웹앱"

| 축 | 채점 에이전트 | 점수 | 근거 |
|---|---|---|---|
| Technical Feasibility | 🏗️ Architect | **85** | CRUD + WebSocket. 표준 스택. 외부 API 최소 |
| Market Viability | 🔭 Scout | **72** | 수요 있지만 테이블링 등 경쟁 존재 |
| Innovation Score | ⚡ Catalyst | **65** | 기존 패턴이지만 QR+카톡 연동은 차별점 |
| Risk Profile | 🛡️ Guardian | **90** | 리스크 거의 없음. 개인정보 최소 (역채점: 100-90=10) |
| User Impact | 🎯 Advocate | **88** | QR 스캔 → 대기 등록 → 현황 확인. 심플 |

```
Vibe Score™ = (85×0.25) + (72×0.20) + (65×0.20) + ((100-90)×0.20) + (88×0.15)
            = 21.25 + 14.4 + 13.0 + 2.0 + 13.2
            = 63.85 → 🟡 CONDITIONAL
```

> 🧭 Strategist 판정: "기술적으로 충분히 구현 가능하나, 리스크가 매우 낮아 역채점 시 기여도 감소. 혁신성 보완 시 GO 가능."

**입력:** "AI로 주식 자동매매하는 앱"

| 축 | 채점 에이전트 | 점수 | 근거 |
|---|---|---|---|
| Technical Feasibility | 🏗️ Architect | **45** | 실시간 시세, 증권사 API 연동, 복잡한 알고리즘 |
| Market Viability | 🔭 Scout | **60** | 수요 있지만 규제 환경 불확실 |
| Innovation Score | ⚡ Catalyst | **40** | 이미 수많은 자동매매 봇 존재. 차별점 불명확 |
| Risk Profile | 🛡️ Guardian | **25** | 금융 규제, 손실 책임, 법적 리스크 치명적 (역채점: 100-25=75) |
| User Impact | 🎯 Advocate | **55** | 차트, 실시간 데이터 시각화 복잡 |

```
Vibe Score™ = (45×0.25) + (60×0.20) + (40×0.20) + ((100-25)×0.20) + (55×0.15)
            = 11.25 + 12.0 + 8.0 + 15.0 + 8.25
            = 54.5 → 🟡 CONDITIONAL
```

> 🧭 Strategist 판정: "리스크가 높아 역채점 점수는 올라가지만, 기술적 난이도와 혁신성 부족이 문제. MVP 스코프를 '모의투자 시뮬레이터'로 축소 시 재평가 권장."

---

### 회의 결과물 (JSON)

```json
{
  "vibe_score": {
    "technical_feasibility": { "score": 85, "weight": 0.25, "agent": "architect" },
    "market_viability": { "score": 72, "weight": 0.20, "agent": "scout" },
    "innovation_score": { "score": 65, "weight": 0.20, "agent": "catalyst" },
    "risk_profile": { "score": 90, "weight": 0.20, "agent": "guardian", "inverted": true },
    "user_impact": { "score": 88, "weight": 0.15, "agent": "advocate" },
    "final_score": 63.85,
    "decision": "CONDITIONAL",
    "threshold_applied": "50 ≤ score < 75 → CONDITIONAL"
  },
  "summary": "식당 대기열 관리 앱은 기술적으로 구현 가능하며 시장 수요 존재하나 혁신성 보완 필요",
  "conditions": ["QR+카톡 연동 차별점 강화", "MVP 스코프 구체화"],
  "council": {
    "architect": {
      "recommended_stack": "FastAPI + PostgreSQL + WebSocket",
      "key_apis": ["POST /queue", "GET /queue/status", "WebSocket /ws/updates"],
      "do_services": ["App Platform", "Managed PostgreSQL"],
      "complexity": "medium",
      "key_findings": ["표준 CRUD + WebSocket으로 충분", "외부 API 의존성 최소"]
    },
    "scout": {
      "market_size": "한국 외식업 시장 160조원, 대기열 관리 니즈 높음",
      "competitors": ["테이블링", "캐치테이블"],
      "differentiation": "QR 기반 무설치, 카톡 알림 연동",
      "target_user": "소규모 식당 (직원 5명 이하)",
      "revenue_model": "프리미엄 (월 구독)"
    },
    "guardian": {
      "risks": [
        "카카오톡 알림 API 연동이 MVP 범위에서 어려움 → SMS 대체 가능",
        "실시간 업데이트 필요 → WebSocket or polling"
      ],
      "mitigations": ["MVP에서는 브라우저 push notification으로 대체"],
      "blockers": [],
      "severity_summary": "LOW — 모든 리스크 완화 가능"
    },
    "catalyst": {
      "innovation_level": "incremental",
      "unique_angles": ["QR 기반 무설치 접근", "카톡 알림 통합"],
      "disruption_potential": "낮음 — 기존 패턴의 개선",
      "suggestion": "AI 기반 대기 시간 예측 추가 시 차별점 강화"
    },
    "advocate": {
      "recommended_ux": "Next.js + shadcn/ui",
      "key_pages": ["QR 랜딩", "대기열 현황", "관리자 대시보드"],
      "accessibility": "높음 — QR 스캔만으로 접근 가능",
      "onboarding_friction": "매우 낮음"
    }
  },
  "cross_examination": {
    "architect_vs_guardian": "Guardian이 WebSocket 복잡도를 지적했으나 Architect가 표준 패턴으로 반박 → Guardian 수용",
    "scout_vs_catalyst": "Catalyst가 혁신성 부족을 지적, Scout이 시장 수요로 반박 → 양측 부분 수용",
    "advocate_challenge": "Advocate가 카톡 알림 없이도 UX 가치 충분함을 주장 → 전원 동의"
  }
}
```

---

## 왜 이 컨셉이 해커톤에서 이기는가

### 심사 기준 매칭

| 기준 (25% each) | 이 컨셉의 강점 |
|---|---|
| **Technological Implementation** | Gradient AI 7+ 기능 활용, Multi-agent orchestration, LangGraph StateGraph, RAG, Evaluations, Tracing |
| **Design** | Chat-first UX + 실시간 회의 시각화 + 결과 대시보드 |
| **Potential Impact** | 비개발자도 아이디어 → 앱 제작 가능 = 소프트웨어 접근성 혁명 |
| **Quality of the Idea** | Vibe Council 라이브 AI 토론 + YouTube → App은 아무도 안 했음 |

### 보너스 상 매칭

| 상 | 적합도 | 이유 |
|---|---|---|
| **Best AI Agent Persona** | ★★★★★ | 6개 에이전트가 각자 뚜렷한 성격으로 회의 |
| **Best Program for the People** | ★★★★★ | 비개발자에게 앱 개발 민주화 |
| **Great Whale Prize** | ★★★★★ | "아이디어 → 라이브 앱" = 가장 큰 스코프 |

### 데모 비디오 킬러 시나리오

```
0:00-0:10  "What if building an app was as easy as describing your idea?"
0:10-0:25  유저가 YouTube URL을 붙여넣기
0:25-1:00  Vibe Council 실시간 시각화 (에이전트들이 토론, Cross-Examination)
1:00-1:15  "Feasible! Score: 82/100" → 개발 시작
1:15-1:45  코드 생성 과정 (split screen: frontend + backend)
1:45-2:10  배포 → 라이브 URL → 실제 앱 동작 시연
2:10-2:30  "From idea to live app. Powered by DigitalOcean Gradient AI."
```

---

## 기술 스택 결정

### DO Gradient AI 활용 (8개 기능)

| Gradient Feature | 용도 |
|---|---|
| **ADK** | 전체 에이전트 시스템 호스팅 |
| **Serverless Inference (Text)** | 6개 에이전트 + 코드 생성 LLM |
| **Serverless Inference (Image)** | 앱 로고, UI 목업, placeholder 이미지 생성 |
| **Knowledge Bases (RAG)** | DO 문서, 프레임워크 best practices |
| **Multi-Agent Routing** | Vibe Council 오케스트레이션 (LangGraph Send API 병렬 실행) |
| **Evaluations** | 에이전트 응답 품질 측정 |
| **Tracing** | 전체 파이프라인 디버깅 |
| **Function Calling** | DO API, GitHub API, YouTube API 호출 |

### 이미지 생성 활용

> Multimodal 모델은 ADK 에이전트에서 직접 사용 불가.
> Tool로 래핑하여 Serverless Inference API를 별도 호출한다.

| 활용 | 생성 단계 | 모델 | 비용 |
|------|----------|------|------|
| **앱 로고** | Phase 4 (Doc Gen) | GPT-image-1 | $5/$40 per 1M tokens |
| **UI 목업 (회의용)** | Phase 2 (Meeting) | GPT-image-1 | Frontend Dev가 시각 자료 제시 |
| **OG Image / 소셜 카드** | Phase 6 (Deploy) | Flux Schnell | $0.003/megapixel |
| **Placeholder 이미지** | Phase 5 (Code Gen) | Fast SDXL | $0.0011/compute sec |

**구현 패턴:**
```python
from gradient import AsyncGradient
import os

@tool
async def generate_app_logo(app_name: str, description: str) -> str:
    """Generate a logo for the app via Gradient Serverless Inference."""
    client = AsyncGradient(model_access_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"])
    response = await client.images.generate(
        model="openai-gpt-image-1",
        prompt=f"Minimal flat logo for '{app_name}': {description}. Clean, modern, SVG style.",
        n=1, size="512x512"
    )
    image_url = response.data[0].url
    # Upload to DO Spaces
    return upload_to_spaces(image_url, f"logos/{app_name}.png")
```

### 모델 배정

| 역할 | 모델 (Model ID) | 이유 |
|------|------|------|
| **Strategist (Session Lead)** | `openai-gpt-5.3-codex` | 에이전틱 워크플로우 특화, Tool Calling |
| **Architect** | `openai-gpt-5-mini` | 기술 분석에 충분, 비용 효율 |
| **Scout** | `openai-gpt-5-mini` + Web Search Tool | 시장 리서치 |
| **Guardian** | `openai-gpt-5` | 비판적 분석, 균형 잡힌 추론 |
| **Catalyst** | `openai-gpt-5-mini` | 혁신성 평가 |
| **Advocate** | `openai-gpt-5-mini` | UX 관점 분석 |
| **Cross-Examination** | `openai-gpt-5` | 에이전트 간 토론/반박 |
| **Code Generator (Phase 5)** | `anthropic-claude-4.6-sonnet` | SWE-bench 73.2%, 1M ctx |
| **Image Generator** | GPT-image-1 / Fast SDXL / Flux | 용도별 선택 |
| **Config Generator (Phase 6)** | `openai-gpt-5-mini` | YAML 생성에 충분 |

### DO 서비스 활용

| DO Service | 용도 |
|---|---|
| **Gradient AI Platform** | 에이전트 호스팅 + 텍스트/이미지 추론 |
| **App Platform** | vibeDeploy 자체 호스팅 + 사용자 앱 배포 대상 |
| **Managed PostgreSQL** | 사용자 앱 DB + vibeDeploy 자체 DB |
| **Spaces** | 생성된 코드, 문서, 이미지 에셋 저장 |

---

## MVP 범위 (해커톤용)

### 포함 (Must Have)
- [x] 텍스트 입력 → Vibe Council Meeting → 결과
- [x] YouTube URL → 트랜스크립트 추출 → Vibe Council Meeting
- [x] Feasibility 판정 (점수 + 상세 피드백)
- [x] 실현 가능 시: PRD + Tech Spec 자동 생성
- [x] 코드 생성 (Next.js frontend + FastAPI/Express backend)
- [x] AI 이미지 생성 (앱 로고 + placeholder 이미지)
- [x] DO App Platform 자동 배포
- [x] 라이브 URL 제공
- [x] 실시간 진행 상황 UI (회의 과정 시각화)

### 제외 (Out of Scope)
- [ ] 사용자 인증/계정 시스템
- [ ] 생성된 앱의 지속적 유지보수
- [ ] 커스텀 도메인 설정
- [ ] 복잡한 프로젝트 (마이크로서비스, 모바일 앱 등)
- [ ] 결제 시스템 연동된 앱 생성
