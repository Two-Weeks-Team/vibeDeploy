# vibeDeploy — Agent Architecture

> LangGraph StateGraph + The Vibe Council on DigitalOcean Gradient ADK

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        vibeDeploy Web UI                        │
│                  (Next.js on DO App Platform)                   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  Input Form  │  │  Meeting View    │  │  Result Dashboard│  │
│  │  (text/URL)  │  │  (live council)  │  │  (PRD/deploy)    │  │
│  └──────┬───────┘  └────────▲─────────┘  └────────▲─────────┘  │
│         │ POST /run         │ SSE stream          │ result     │
└─────────┼───────────────────┼─────────────────────┼─────────────┘
          │                   │                     │
          ▼                   │                     │
┌─────────────────────────────┴─────────────────────┴─────────────┐
│  Gradient ADK Agent (gradient agent deploy)                     │
│  URL: https://agents.do-ai.run/v1/{workspace}/vibedeploy/run   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              LangGraph StateGraph                         │  │
│  │                                                           │  │
│  │  input_processor ──► vibe_council_meeting ──► decision    │  │
│  │                                                 │         │  │
│  │                              ┌──────────────────┼───────┐ │  │
│  │                              ▼          ▼       ▼       │ │  │
│  │                         doc_gen    cond_review  feedback │ │  │
│  │                           │            │                │ │  │
│  │                           ▼            ▼                │ │  │
│  │                        code_gen   doc_gen or END        │ │  │
│  │                           │                             │ │  │
│  │                           ▼                             │ │  │
│  │                        deployer ──► END                 │ │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Knowledge Bases: DO Docs, Framework Best Practices             │
│  Tracing: Automatic (LangGraph nodes)                           │
│  Checkpointer: MemorySaver (thread-based session persistence)   │
└─────────────────────────────────────────────────────────────────┘
```

---

## State Schema

```python
from typing import TypedDict, Optional, Literal, List, Dict, Annotated
from langgraph.graph import add_messages

class AgentScore(TypedDict):
    score: int              # 0-100
    reasoning: str          # 채점 근거
    key_findings: List[str] # 핵심 발견사항

class CouncilAnalysis(TypedDict):
    architect: Dict         # 기술 분석 결과
    scout: Dict             # 시장 분석 결과
    guardian: Dict          # 리스크 분석 결과
    catalyst: Dict          # 혁신성 분석 결과
    advocate: Dict          # UX/사용자 분석 결과

class ScoringResult(TypedDict):
    technical_feasibility: AgentScore   # Architect (25%)
    market_viability: AgentScore        # Scout (20%)
    innovation_score: AgentScore        # Catalyst (20%)
    risk_profile: AgentScore            # Guardian (20%, inverted)
    user_impact: AgentScore             # Advocate (15%)
    final_score: float                  # Vibe Score™
    decision: Literal["GO", "CONDITIONAL", "NO_GO"]

class CrossExamination(TypedDict):
    architect_vs_guardian: Dict   # 기술 리스크 공방
    scout_vs_catalyst: Dict      # 시장 현실 vs 혁신 잠재력
    advocate_challenges: Dict    # UX 관점에서 양측 도전
    score_adjustments: Dict      # 토론 결과 점수 조정

class GeneratedDocs(TypedDict):
    prd: str                # Product Requirements Document
    tech_spec: str          # Technical Specification
    api_spec: str           # API Specification
    db_schema: str          # Database Schema
    app_spec_yaml: str      # DO App Platform Spec

class DeployResult(TypedDict):
    app_id: str
    live_url: str
    github_repo: str
    status: str

class VibeDeployState(TypedDict):
    # Input
    raw_input: str                          # 사용자 원본 입력
    input_type: Literal["text", "youtube"]  # 입력 유형
    transcript: Optional[str]               # YouTube 트랜스크립트 (있을 경우)
    key_frames: Optional[List[Dict]]        # 추출된 키프레임 [{ timestamp, image_url, analysis }]
    visual_context: Optional[str]           # GPT-4o vision 분석 결과 종합

    # Structured idea
    idea: Dict                              # 구조화된 아이디어 (텍스트 + 시각 컨텍스트 결합)
    idea_summary: str                       # 한 줄 요약

    # Vibe Council Meeting
    meeting_messages: Annotated[list, add_messages]  # 회의 대화 로그
    council_analysis: Optional[CouncilAnalysis]      # Phase 1 결과
    cross_examination: Optional[CrossExamination]    # Phase 2 결과

    # Scoring
    scoring: Optional[ScoringResult]

    # Conditional path
    user_feedback: Optional[str]            # 사용자 피드백 (CONDITIONAL 시)
    scope_adjustment: Optional[str]         # 스코프 조정안

    # Documents
    generated_docs: Optional[GeneratedDocs]

    # Code
    frontend_code: Optional[Dict]           # { filepath: content }
    backend_code: Optional[Dict]            # { filepath: content }

    # Deployment
    deploy_result: Optional[DeployResult]

    # Meta
    phase: str                              # 현재 단계
    error: Optional[str]
```

---

## Node Definitions

### Node 1: input_processor

**역할:** 입력을 파싱하고 아이디어를 구조화

```python
from langchain_gradient import ChatGradient
from gradient import AsyncGradient
import os

# LLM instances
llm_mini = ChatGradient(
    model="openai-gpt-5-mini",
    gradient_api_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"],
    temperature=0.3
)

vision_client = AsyncGradient(
    model_access_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"]
)

async def input_processor(state: VibeDeployState) -> dict:
    raw = state["raw_input"]

    if is_youtube_url(raw):
        # Step 1: 트랜스크립트 추출 (with timestamps)
        transcript = await extract_youtube_transcript(raw)

        # Step 2: 키 세그먼트 탐지 — 시각 정보가 중요한 구간 식별
        key_segments = await detect_visual_segments(transcript, llm=llm_mini)
        # → [{ timestamp: 45.2, reason: "UI 데모 시작" }, ...]

        # Step 3: 해당 타임스탬프에서 프레임 추출
        frames = await extract_video_frames(raw, [s["timestamp"] for s in key_segments])

        # Step 4: GPT-4o (vision)로 프레임 분석
        key_frames = []
        for frame, segment in zip(frames, key_segments):
            analysis = await vision_client.chat.completions.create(
                model="openai-gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"이 프레임은 '{segment['reason']}' 시점의 캡처입니다. 무엇이 보이나요?"},
                        {"type": "image_url", "image_url": {"url": frame["image_path"]}}
                    ]
                }]
            )
            key_frames.append({
                "timestamp": frame["timestamp"],
                "image_url": await upload_to_spaces(frame["image_path"]),
                "analysis": analysis.choices[0].message.content
            })

        # Step 5: 텍스트 + 시각 컨텍스트 결합
        visual_context = "\n".join([
            f"[{kf['timestamp']}s] {kf['analysis']}" for kf in key_frames
        ])
        idea = await structurize_idea(transcript, visual_context=visual_context, llm=llm_mini)

        return {
            "input_type": "youtube",
            "transcript": transcript,
            "key_frames": key_frames,
            "visual_context": visual_context,
            "idea": idea,
            "idea_summary": idea["summary"],
            "phase": "input_processed"
        }
    else:
        idea = await structurize_idea(raw, llm=llm_mini)
        return {
            "input_type": "text",
            "idea": idea,
            "idea_summary": idea["summary"],
            "phase": "input_processed"
        }
```

**모델:**
- `openai-gpt-5-mini` (트랜스크립트 구조화, 키 세그먼트 탐지) — via `ChatGradient`
- `openai-gpt-4o` (프레임 vision 분석) — via `AsyncGradient`

**도구:**
- `youtube_transcript_extractor` — YouTube Data API v3
- `detect_visual_segments` — 트랜스크립트에서 시각 참조 구간 탐지
- `extract_video_frames` — yt-dlp + ffmpeg로 프레임 추출
- `upload_to_spaces` — DO Spaces에 프레임 이미지 저장

### Node 2: vibe_council_meeting

**역할:** The Vibe Council 4-Phase 미팅 — 분석 → 토론 → 채점 → 판정

```python
from langgraph.graph import Send
from langchain_gradient import ChatGradient
import os

# Council 에이전트별 LLM 인스턴스
council_llm = ChatGradient(
    model="openai-gpt-5-mini",
    gradient_api_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"],
    temperature=0.7
)

guardian_llm = ChatGradient(
    model="openai-gpt-5",
    gradient_api_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"],
    temperature=0.5
)

debate_llm = ChatGradient(
    model="openai-gpt-5",
    gradient_api_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"],
    temperature=0.7
)

strategist_llm = ChatGradient(
    model="openai-gpt-5.3-codex",
    gradient_api_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"],
    temperature=0.3
)

COUNCIL_MEMBERS = ["architect", "scout", "guardian", "catalyst", "advocate"]

# === Phase 1: Individual Analysis (병렬 — Send API) ===

def fan_out_analysis(state: VibeDeployState):
    """Send API로 5개 에이전트 병렬 분석 실행"""
    return [
        Send("run_council_agent", {
            "agent_name": name,
            "idea": state["idea"],
            "idea_summary": state["idea_summary"]
        })
        for name in COUNCIL_MEMBERS
    ]

async def run_council_agent(input: dict) -> dict:
    """개별 Council 에이전트 분석 실행"""
    agent_name = input["agent_name"]
    idea = input["idea"]

    # 에이전트별 LLM 선택
    llm = guardian_llm if agent_name == "guardian" else council_llm

    # 에이전트별 시스템 프롬프트 적용
    prompt = COUNCIL_PROMPTS[agent_name]
    response = await llm.ainvoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"다음 아이디어를 분석해주세요:\n\n{json.dumps(idea, ensure_ascii=False)}"}
    ])

    return {"agent_name": agent_name, "analysis": parse_analysis(response.content)}

# === Phase 2: Cross-Examination (순차 토론) ===

async def cross_examination(state: VibeDeployState) -> dict:
    """Strategist가 진행하는 에이전트 간 토론"""
    analysis = state["council_analysis"]

    # Round 1: Architect ↔ Guardian (기술적 리스크 공방)
    arch_vs_guard = await debate_llm.ainvoke([
        {"role": "system", "content": "You are moderating a debate between Architect and Guardian."},
        {"role": "user", "content": f"""
Architect의 기술 분석: {json.dumps(analysis['architect'])}
Guardian의 리스크 분석: {json.dumps(analysis['guardian'])}

Guardian의 리스크 지적에 대해 Architect가 반박하고,
Architect의 낙관론에 대해 Guardian이 재반박하세요.
각 에이전트의 관점에서 2라운드 토론을 진행하세요."""}
    ])

    # Round 2: Scout ↔ Catalyst (시장 현실 vs 혁신 잠재력)
    scout_vs_catalyst = await debate_llm.ainvoke([
        {"role": "system", "content": "You are moderating a debate between Scout and Catalyst."},
        {"role": "user", "content": f"""
Scout의 시장 분석: {json.dumps(analysis['scout'])}
Catalyst의 혁신성 분석: {json.dumps(analysis['catalyst'])}

Scout이 시장 데이터 기반으로 현실을 제시하고,
Catalyst가 혁신 잠재력을 주장하세요.
각 에이전트의 관점에서 2라운드 토론을 진행하세요."""}
    ])

    # Round 3: Advocate가 양측 도전
    advocate_challenge = await debate_llm.ainvoke([
        {"role": "system", "content": "You are the Advocate, challenging both sides from the user's perspective."},
        {"role": "user", "content": f"""
이전 토론 결과를 바탕으로, 사용자 관점에서 양측의 주장에 도전하세요.
Advocate의 UX 분석: {json.dumps(analysis['advocate'])}
기술 토론: {arch_vs_guard.content}
시장 토론: {scout_vs_catalyst.content}"""}
    ])

    return {
        "cross_examination": {
            "architect_vs_guardian": parse_debate(arch_vs_guard.content),
            "scout_vs_catalyst": parse_debate(scout_vs_catalyst.content),
            "advocate_challenges": parse_debate(advocate_challenge.content),
        },
        "phase": "cross_examination_complete"
    }

# === Phase 3: Scoring (병렬 — Send API) ===

def fan_out_scoring(state: VibeDeployState):
    """토론 결과를 반영하여 각 에이전트가 자기 축 채점"""
    return [
        Send("score_axis", {
            "agent_name": name,
            "idea": state["idea"],
            "analysis": state["council_analysis"][name],
            "cross_examination": state["cross_examination"]
        })
        for name in COUNCIL_MEMBERS
    ]

async def score_axis(input: dict) -> dict:
    """개별 에이전트의 채점"""
    agent_name = input["agent_name"]
    llm = guardian_llm if agent_name == "guardian" else council_llm

    response = await llm.ainvoke([
        {"role": "system", "content": SCORING_PROMPTS[agent_name]},
        {"role": "user", "content": f"""
초기 분석: {json.dumps(input['analysis'])}
토론 결과: {json.dumps(input['cross_examination'])}

토론 결과를 반영하여 0-100점으로 채점하고 근거를 제시하세요.
JSON 형식: {{"score": int, "reasoning": str, "key_findings": [str]}}"""}
    ])
    return {"agent_name": agent_name, "score": parse_score(response.content)}

# === Phase 4: Verdict (Strategist 종합) ===

async def strategist_verdict(state: VibeDeployState) -> dict:
    """Strategist가 Vibe Score™ 산출 및 최종 판정"""
    scores = state["scoring"]

    # Vibe Score™ 산출
    vibe_score = (
        scores["technical_feasibility"]["score"] * 0.25 +
        scores["market_viability"]["score"] * 0.20 +
        scores["innovation_score"]["score"] * 0.20 +
        (100 - scores["risk_profile"]["score"]) * 0.20 +
        scores["user_impact"]["score"] * 0.15
    )

    # Decision Gate
    if vibe_score >= 75:
        decision = "GO"
    elif vibe_score >= 50:
        decision = "CONDITIONAL"
    else:
        decision = "NO_GO"

    # Strategist 종합 분석
    verdict = await strategist_llm.ainvoke([
        {"role": "system", "content": COUNCIL_PROMPTS["strategist"]},
        {"role": "user", "content": f"""
Vibe Score™: {vibe_score:.2f}
Decision: {decision}
각 축 점수: {json.dumps(scores)}
토론 결과: {json.dumps(state['cross_examination'])}

최종 판정 근거와 핵심 인사이트를 종합해주세요."""}
    ])

    return {
        "scoring": {
            **scores,
            "final_score": round(vibe_score, 2),
            "decision": decision
        },
        "phase": "verdict_delivered"
    }
```

**모델 배정:**

| Council Member | 모델 | 비용 (In/Out per 1M) | 이유 |
|----------------|------|---------------------|------|
| 🏗️ Architect | `openai-gpt-5-mini` | $0.25/$2.00 | 기술 분석에 충분, 비용 효율 |
| 🔭 Scout | `openai-gpt-5-mini` + Web Search | $0.25/$2.00 | 시장 리서치 |
| 🛡️ Guardian | `openai-gpt-5` | $1.25/$10.00 | 비판적 분석에 고품질 추론 필요 |
| ⚡ Catalyst | `openai-gpt-5-mini` | $0.25/$2.00 | 혁신성 평가 |
| 🎯 Advocate | `openai-gpt-5-mini` | $0.25/$2.00 | UX 관점 분석 |
| Cross-Examination | `openai-gpt-5` | $1.25/$10.00 | 에이전트 간 토론/반박 |
| 🧭 Strategist | `openai-gpt-5.3-codex` | $1.75/$14.00 | 종합 판단 + Tool Calling |

### Node 3: decision_gate

**역할:** Vibe Score™ 기반 라우팅

```python
def decision_gate(state: VibeDeployState) -> str:
    decision = state["scoring"]["decision"]

    if decision == "GO":           # score >= 75
        return "doc_generator"
    elif decision == "CONDITIONAL": # 50 <= score < 75
        return "conditional_review"
    else:                           # score < 50
        return "feedback_generator"
```

### Node 4a: conditional_review (CONDITIONAL 경로)

**역할:** 스코프 축소안 제시 → 사용자 입력 대기 (human-in-the-loop)

```python
from langgraph.types import interrupt

async def conditional_review(state: VibeDeployState) -> dict:
    # 부족한 축 식별 (점수 < 65인 축)
    weak_dimensions = identify_weak_dimensions(state["scoring"])

    # Strategist가 스코프 축소안 생성
    adjustment = await strategist_llm.ainvoke([
        {"role": "system", "content": COUNCIL_PROMPTS["strategist"]},
        {"role": "user", "content": f"""
Vibe Score™: {state['scoring']['final_score']} (CONDITIONAL)
부족한 축: {json.dumps(weak_dimensions)}
Council 분석: {json.dumps(state['council_analysis'])}
토론 결과: {json.dumps(state['cross_examination'])}

부족한 영역을 보완하기 위한 MVP 스코프 축소안을 제시하세요.
구체적인 기능 삭제/수정 사항을 포함하세요."""}
    ])

    # Human-in-the-loop: 사용자에게 확인 요청
    user_response = interrupt({
        "type": "conditional_review",
        "score": state["scoring"]["final_score"],
        "weak_dimensions": weak_dimensions,
        "proposed_adjustment": adjustment.content,
        "message": "일부 영역에서 보완이 필요합니다. 아래 수정안으로 진행할까요?"
    })

    if user_response.get("accepted"):
        return {
            "scope_adjustment": adjustment.content,
            "user_feedback": user_response.get("feedback", ""),
            "phase": "conditional_accepted"
        }
    else:
        return {"phase": "cancelled"}
```

### Node 4b: feedback_generator (NO-GO 경로)

**역할:** 실패 사유 리포트 + 대안 제시

```python
async def feedback_generator(state: VibeDeployState) -> dict:
    feedback = await strategist_llm.ainvoke([
        {"role": "system", "content": COUNCIL_PROMPTS["strategist"]},
        {"role": "user", "content": f"""
Vibe Score™: {state['scoring']['final_score']} (NO-GO)
각 축 점수: {json.dumps(state['scoring'])}
Council 분석: {json.dumps(state['council_analysis'])}
토론 결과: {json.dumps(state['cross_examination'])}

실패 사유 리포트를 작성하세요:
1. 핵심 실패 이유
2. 각 축별 상세 분석
3. 개선 방향
4. 대안 아이디어 2-3개"""}
    ])

    return {
        "phase": "feedback_delivered",
        "error": None  # NO-GO도 유효한 결과
    }
```

### Node 5: doc_generator (GO 경로)

**역할:** PRD, Tech Spec, API Spec, DB Schema, App Spec YAML 생성

```python
from langchain_gradient import ChatGradient

doc_gen_llm = ChatGradient(
    model="anthropic-claude-4.6-sonnet",
    gradient_api_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"],
    temperature=0.2
)

async def doc_generator(state: VibeDeployState) -> dict:
    idea = state["idea"]
    council = state["council_analysis"]
    adjustment = state.get("scope_adjustment")  # CONDITIONAL인 경우

    # RAG: DO 문서에서 관련 패턴 검색
    do_context = await query_do_knowledge_base(
        f"App Platform deployment for {council['architect'].get('recommended_stack', 'Next.js + FastAPI')}"
    )

    docs = await generate_all_docs(
        llm=doc_gen_llm,
        idea=idea,
        architect_analysis=council["architect"],
        advocate_analysis=council["advocate"],
        do_context=do_context,
        scope_adjustment=adjustment
    )

    return {
        "generated_docs": docs,
        "phase": "docs_generated"
    }
```

**모델:** `anthropic-claude-4.6-sonnet` ($3/$15 per 1M tokens)
**도구:** `query_do_knowledge_base` (Gradient KB RAG)

### Node 6: code_generator

**역할:** 실제 프로젝트 코드 생성

```python
import asyncio

code_gen_llm = ChatGradient(
    model="anthropic-claude-4.6-sonnet",
    gradient_api_key=os.environ["DIGITALOCEAN_INFERENCE_KEY"],
    temperature=0.1,
    max_tokens=8192
)

async def code_generator(state: VibeDeployState) -> dict:
    docs = state["generated_docs"]
    council = state["council_analysis"]

    # Frontend + Backend 병렬 생성
    frontend_task = generate_frontend_code(
        llm=code_gen_llm,
        tech_spec=docs["tech_spec"],
        api_spec=docs["api_spec"],
        ux_analysis=council["advocate"]
    )

    backend_task = generate_backend_code(
        llm=code_gen_llm,
        tech_spec=docs["tech_spec"],
        api_spec=docs["api_spec"],
        db_schema=docs["db_schema"],
        arch_analysis=council["architect"]
    )

    frontend_code, backend_code = await asyncio.gather(
        frontend_task, backend_task
    )

    return {
        "frontend_code": frontend_code,  # { "src/app/page.tsx": "...", ... }
        "backend_code": backend_code,    # { "main.py": "...", ... }
        "phase": "code_generated"
    }
```

**모델:** `anthropic-claude-4.6-sonnet` (SWE-bench 73.2%, 1M context window)

### Node 7: deployer

**역할:** GitHub repo 생성 + DO App Platform 배포

```python
async def deployer(state: VibeDeployState) -> dict:
    # 1. GitHub repo 생성 + 코드 push
    repo = await create_github_repo(
        name=sanitize_name(state["idea_summary"]),
        files={
            **state["frontend_code"],
            **state["backend_code"],
            ".do/app.yaml": state["generated_docs"]["app_spec_yaml"],
            "README.md": generate_readme(state),
            "LICENSE": MIT_LICENSE
        }
    )

    # 2. DO App Platform 배포 (사용자 앱은 App Platform에 배포)
    app = await deploy_to_digitalocean(
        repo_url=repo["url"],
        app_spec=state["generated_docs"]["app_spec_yaml"]
    )

    # 3. 배포 상태 폴링
    live_url = await wait_for_deployment(app["app_id"])

    return {
        "deploy_result": {
            "app_id": app["app_id"],
            "live_url": live_url,
            "github_repo": repo["url"],
            "status": "deployed"
        },
        "phase": "deployed"
    }
```

**모델:** 없음 (도구만 사용)
**도구:** `github_api`, `pydo_apps_create`, `pydo_deployment_status`

---

## Graph Definition

```python
from langgraph.graph import StateGraph, END, Send
from langgraph.checkpoint.memory import MemorySaver

workflow = StateGraph(VibeDeployState)

# Add nodes
workflow.add_node("input_processor", input_processor)
workflow.add_node("run_council_agent", run_council_agent)     # Phase 1 (병렬 분석)
workflow.add_node("cross_examination", cross_examination)      # Phase 2 (순차 토론)
workflow.add_node("score_axis", score_axis)                    # Phase 3 (병렬 채점)
workflow.add_node("strategist_verdict", strategist_verdict)    # Phase 4 (판정)
workflow.add_node("decision_gate", decision_gate)
workflow.add_node("conditional_review", conditional_review)
workflow.add_node("feedback_generator", feedback_generator)
workflow.add_node("doc_generator", doc_generator)
workflow.add_node("code_generator", code_generator)
workflow.add_node("deployer", deployer)

# Define flow
workflow.set_entry_point("input_processor")

# Phase 1: 병렬 분석 (Send API)
workflow.add_conditional_edges("input_processor", fan_out_analysis)

# Phase 1 결과 수집 → Phase 2
workflow.add_edge("run_council_agent", "cross_examination")

# Phase 2 → Phase 3: 병렬 채점
workflow.add_conditional_edges("cross_examination", fan_out_scoring)

# Phase 3 결과 수집 → Phase 4
workflow.add_edge("score_axis", "strategist_verdict")

# Phase 4 → Decision
workflow.add_edge("strategist_verdict", "decision_gate")

# Decision gate routing
workflow.add_conditional_edges("decision_gate", decision_gate, {
    "doc_generator": "doc_generator",
    "conditional_review": "conditional_review",
    "feedback_generator": "feedback_generator"
})

# Conditional review → docs or END
workflow.add_conditional_edges("conditional_review", lambda s: (
    "doc_generator" if s["phase"] == "conditional_accepted" else END
))

# Linear flow after GO
workflow.add_edge("doc_generator", "code_generator")
workflow.add_edge("code_generator", "deployer")
workflow.add_edge("deployer", END)
workflow.add_edge("feedback_generator", END)

# Compile with checkpointer for session persistence
app = workflow.compile(checkpointer=MemorySaver())
```

---

## Agent System Prompts

### 🏗️ Architect (Technical Lead)

```
You are the Architect of The Vibe Council — a technical lead who evaluates ideas with precision.
Your focus: tech stack selection, implementation complexity, timeline estimation, DigitalOcean deployment feasibility.
Personality: Methodical and precise. You think in systems, APIs, and data flows.
Core question: "How would we build this?"

Analyze the idea and provide:
1. Recommended tech stack (frontend + backend + DB)
2. Key API endpoints needed
3. DigitalOcean services required (App Platform, Managed DB, Spaces, etc.)
4. Complexity assessment (low/medium/high)
5. MVP timeline estimate
6. Technical risks and dependencies

Score: Technical Feasibility (0-100)
```

### 🔭 Scout (Market Analyst)

```
You are the Scout of The Vibe Council — a market analyst driven by data and curiosity.
Your focus: market size, competition analysis, trends, product-market fit, revenue potential.
Personality: Curious and data-driven. You back claims with evidence, not speculation.
Core question: "Who wants this and why?"

Analyze the idea and provide:
1. Market size estimation
2. Existing competitors and their strengths/weaknesses
3. Target user persona
4. Differentiation opportunities
5. Revenue model viability
6. Growth potential

If data is unavailable, state "insufficient data" rather than speculating.
Score: Market Viability (0-100)
```

### 🛡️ Guardian (Risk Assessor)

```
You are the Guardian of The Vibe Council — the one who finds what could go wrong.
Your focus: security vulnerabilities, legal/regulatory risks, technical blockers, failure scenarios.
Personality: Cautious and thorough. You protect the team from blind spots.
Core question: "Why could this fail?"

For each risk, classify severity:
- BLOCKER: Cannot proceed without resolution
- HIGH: Significant risk, mitigation required
- MEDIUM: Manageable with proper planning
- LOW: Minor concern

Provide:
1. Technical risks and blockers
2. Legal/regulatory concerns
3. Security vulnerabilities
4. External dependency risks
5. Mitigation strategies for each risk

Score: Risk Profile (0-100) where 100 = maximum risk, 0 = no risk at all.
NOTE: This score is INVERTED in the Vibe Score™ formula: (100 - Risk) is used.
```

### ⚡ Catalyst (Innovation Officer)

```
You are the Catalyst of The Vibe Council — the visionary who spots what makes ideas special.
Your focus: uniqueness, disruptive potential, competitive moat, "wow factor".
Personality: Enthusiastic and visionary, but grounded in reality. You celebrate innovation while demanding substance.
Core question: "What makes this special?"

Analyze the idea and provide:
1. Innovation level (revolutionary / evolutionary / incremental / derivative)
2. Unique angles and differentiators
3. Disruption potential
4. Competitive moat strength
5. "Wow factor" for demo/pitch
6. Suggestions to increase innovation score

Score: Innovation Score (0-100)
```

### 🎯 Advocate (UX Champion)

```
You are the Advocate of The Vibe Council — the voice of the end user.
Your focus: user experience, accessibility, onboarding friction, page count, UI complexity for MVP.
Personality: Empathetic and practical. You think from the user's seat, not the developer's.
Core question: "Will real people actually use this?"

Analyze the idea and provide:
1. Key pages/screens for MVP (minimize scope)
2. Recommended UI framework (Next.js + shadcn/ui preferred)
3. Onboarding friction assessment
4. Accessibility considerations
5. Mobile responsiveness needs
6. User journey (3-5 steps max for MVP)

Think in terms of MVP scope. Propose the simplest UI that delivers value.
Score: User Impact (0-100)
```

### 🧭 Strategist (Session Lead)

```
You are the Strategist of The Vibe Council — the session leader who synthesizes all perspectives.
Your role:
1. Facilitate Cross-Examination debates between Council members
2. Calculate the Vibe Score™ using the weighted formula
3. Deliver the final GO / CONDITIONAL / NO-GO verdict
4. Provide actionable next steps

You do NOT score any axis. You synthesize the 5 agents' scores:
Vibe Score™ = (Tech × 0.25) + (Market × 0.20) + (Innovation × 0.20) + ((100 - Risk) × 0.20) + (UserImpact × 0.15)

Decision Gate:
- ≥ 75 → GO: Proceed to development
- 50-74 → CONDITIONAL: Propose scope reduction
- < 50 → NO-GO: Provide failure report + alternatives

Personality: Balanced, decisive, impartial. You weight evidence over enthusiasm.
When agents disagree, identify the root cause and seek resolution.
```

---

## Vibe Score™ Formula

```
Vibe Score™ = (Tech × 0.25) + (Market × 0.20) + (Innovation × 0.20) + ((100 - Risk) × 0.20) + (UserImpact × 0.15)

여기서:
  Tech       = Architect의 Technical Feasibility 점수 (0-100)
  Market     = Scout의 Market Viability 점수 (0-100)
  Innovation = Catalyst의 Innovation Score 점수 (0-100)
  Risk       = Guardian의 Risk Profile 점수 (0-100, 높을수록 위험) → 역채점
  UserImpact = Advocate의 User Impact 점수 (0-100)

Decision Gate:
  Score ≥ 75   → 🟢 GO: 즉시 개발 + 배포 진행
  50 ≤ Score < 75 → 🟡 CONDITIONAL: 조건부 진행 (스코프 축소안 제시)
  Score < 50   → 🔴 NO-GO: 개발 불가 (실패 리포트 + 대안 제시)
```

---

## Tool Registry

### Input Processing Tools

| Tool | 사용 에이전트 | Function | API |
|------|-------------|----------|-----|
| `youtube_transcript` | input_processor | YouTube 트랜스크립트 추출 | YouTube Data API v3 |
| `detect_visual_segments` | input_processor | 시각 참조 구간 탐지 | LLM (GPT-5 mini) |
| `extract_video_frames` | input_processor | 프레임 추출 | yt-dlp + ffmpeg |
| `analyze_frame_vision` | input_processor | 프레임 분석 (multimodal) | GPT-4o via AsyncGradient |
| `structurize_idea` | input_processor | 자연어 → 구조화 JSON | GPT-5 mini |

### Meeting Tools

| Tool | 사용 에이전트 | Function | API |
|------|-------------|----------|-----|
| `web_search` | 🔭 Scout | 시장 조사, 경쟁사 분석 | Serper API / Exa |
| `query_do_kb` | 🏗️ Architect | DO 문서 KB 검색 | Gradient KB Retrieve API |

### Image Generation Tools

| Tool | 사용 에이전트 | Function | API |
|------|-------------|----------|-----|
| `generate_app_logo` | doc_generator | 앱 로고 생성 | GPT-image-1 via AsyncGradient |
| `generate_placeholder` | code_generator | placeholder 이미지 | Fast SDXL |

### Development Tools

| Tool | 사용 노드 | Function | API |
|------|----------|----------|-----|
| `github_create_repo` | deployer | GitHub 레포 생성 | GitHub API v3 |
| `github_push_files` | deployer | 파일 커밋 + push | GitHub API v3 |

### Deployment Tools

| Tool | 사용 노드 | Function | API |
|------|----------|----------|-----|
| `do_create_app` | deployer | DO App Platform 앱 생성 | PyDo `apps.create()` |
| `do_create_db` | deployer | DO Managed DB 생성 | PyDo `databases.create_cluster()` |
| `do_deployment_status` | deployer | 배포 상태 폴링 | PyDo `apps.list_deployments()` |
| `do_get_logs` | deployer | 배포 로그 조회 | PyDo `apps.get_logs()` |

---

## Streaming Architecture

ADK `@entrypoint`를 통해 사용자에게 실시간 회의 과정 스트리밍:

```python
from gradient_adk import entrypoint, RequestContext

@entrypoint
async def main(input: dict, context: RequestContext):
    """vibeDeploy agent entrypoint — SSE streaming"""

    async def stream_vibe_council():
        state = {"raw_input": input["prompt"]}

        # Phase 1: Input Processing
        yield f'event: council.phase.start\ndata: {{"phase": "input_processing", "message": "아이디어를 분석하고 있습니다..."}}\n\n'
        state = await input_processor(state)

        # Phase 2: Individual Analysis (병렬)
        yield f'event: council.phase.start\ndata: {{"phase": "individual_analysis", "message": "Vibe Council이 아이디어를 분석합니다..."}}\n\n'

        for agent_name in ["architect", "scout", "guardian", "catalyst", "advocate"]:
            yield f'event: council.agent.analyzing\ndata: {{"agent": "{agent_name}", "status": "analyzing"}}\n\n'

        # 5 에이전트 병렬 실행 (Send API)
        analysis_results = await run_parallel_analysis(state)

        for agent_name, result in analysis_results.items():
            yield f'event: council.agent.analysis\ndata: {{"agent": "{agent_name}", "analysis": {json.dumps(result)}}}\n\n'

        # Phase 3: Cross-Examination
        yield f'event: council.phase.start\ndata: {{"phase": "cross_examination", "message": "에이전트 간 토론이 시작됩니다..."}}\n\n'

        yield f'event: council.debate.start\ndata: {{"pair": "architect_vs_guardian", "topic": "기술적 리스크"}}\n\n'
        arch_guard = await run_debate_round("architect", "guardian", state)
        yield f'event: council.debate.exchange\ndata: {json.dumps(arch_guard)}\n\n'

        yield f'event: council.debate.start\ndata: {{"pair": "scout_vs_catalyst", "topic": "시장 vs 혁신"}}\n\n'
        scout_catalyst = await run_debate_round("scout", "catalyst", state)
        yield f'event: council.debate.exchange\ndata: {json.dumps(scout_catalyst)}\n\n'

        yield f'event: council.debate.start\ndata: {{"pair": "advocate_challenge", "topic": "사용자 관점 도전"}}\n\n'
        advocate_ch = await run_advocate_challenge(state)
        yield f'event: council.debate.exchange\ndata: {json.dumps(advocate_ch)}\n\n'

        # Phase 4: Scoring + Verdict
        yield f'event: council.phase.start\ndata: {{"phase": "scoring", "message": "채점 중..."}}\n\n'
        scoring = await run_scoring(state)
        yield f'event: council.scoring.result\ndata: {json.dumps(scoring)}\n\n'

        verdict = scoring["decision"]
        yield f'event: council.verdict\ndata: {{"decision": "{verdict}", "score": {scoring["final_score"]}}}\n\n'

        # Branch based on verdict
        if verdict == "GO":
            yield f'event: build.docs.progress\ndata: {{"status": "generating", "message": "문서 생성 중..."}}\n\n'
            docs = await generate_docs(state)
            yield f'event: build.docs.progress\ndata: {{"status": "complete"}}\n\n'

            yield f'event: build.code.progress\ndata: {{"status": "generating", "message": "코드 생성 중..."}}\n\n'
            code = await generate_code(state)
            yield f'event: build.code.progress\ndata: {{"status": "complete"}}\n\n'

            yield f'event: deploy.status\ndata: {{"status": "deploying", "message": "배포 중..."}}\n\n'
            result = await deploy(state)
            yield f'event: deploy.complete\ndata: {{"url": "{result["live_url"]}", "github": "{result["github_repo"]}"}}\n\n'

        elif verdict == "CONDITIONAL":
            # interrupt()로 사용자 입력 대기
            yield f'event: council.conditional\ndata: {json.dumps(state["scope_adjustment"])}\n\n'

        else:  # NO_GO
            yield f'event: council.nogo\ndata: {json.dumps(state["feedback"])}\n\n'

    return stream_vibe_council()
```

### SSE Event Types

| Event | Data | UI Rendering |
|-------|------|-------------|
| `council.phase.start` | phase name + message | 진행 단계 표시 업데이트 |
| `council.agent.analyzing` | agent name + status | 에이전트 아바타 활성화 + 로딩 |
| `council.agent.analysis` | agent analysis JSON | 에이전트 발언 카드 표시 |
| `council.debate.start` | debate pair + topic | 토론 쌍 표시, 활성화 |
| `council.debate.exchange` | challenge + response | 토론 로그 (말풍선 UI) |
| `council.scoring.result` | all scores + Vibe Score™ | 점수 게이지 애니메이션 |
| `council.verdict` | decision + score | GO/CONDITIONAL/NO-GO 배너 |
| `council.conditional` | adjustment proposal | 사용자 확인 모달 |
| `council.nogo` | feedback report | NO-GO 상세 리포트 |
| `build.docs.progress` | doc type + status | 문서 생성 진행바 |
| `build.code.progress` | file path + status | 코드 파일 생성 애니메이션 |
| `deploy.status` | deployment status | 배포 진행 상태 |
| `deploy.complete` | live URL + github URL | 성공 화면 + URL 링크 |

---

## Tracing & Observability

LangGraph 자동 트레이싱으로 모든 노드가 기록됨:

```
Trace: vibedeploy-session-abc123
├── input_processor              (2.1s, ~1,300 tokens)
├── vibe_council_meeting
│   ├── Phase 1: Individual Analysis (병렬)
│   │   ├── architect_agent      (2.5s, ~3,500 tokens)
│   │   ├── scout_agent          (2.8s, ~3,500 tokens)
│   │   ├── guardian_agent       (3.0s, ~3,500 tokens)
│   │   ├── catalyst_agent       (2.3s, ~3,500 tokens)
│   │   └── advocate_agent       (2.4s, ~3,500 tokens)
│   ├── Phase 2: Cross-Examination (순차)
│   │   ├── architect↔guardian   (3.5s, ~3,000 tokens)
│   │   ├── scout↔catalyst      (3.2s, ~3,000 tokens)
│   │   └── advocate_challenge   (2.8s, ~3,000 tokens)
│   ├── Phase 3: Scoring (병렬)
│   │   ├── architect_score      (1.2s, ~800 tokens)
│   │   ├── scout_score          (1.1s, ~800 tokens)
│   │   ├── guardian_score       (1.3s, ~800 tokens)
│   │   ├── catalyst_score       (1.0s, ~800 tokens)
│   │   └── advocate_score       (1.1s, ~800 tokens)
│   └── Phase 4: Strategist Verdict (1.5s, ~4,000 tokens)
├── decision_gate                (0.1s, scoring only)
├── doc_generator                (8.5s, ~17,000 tokens)
├── code_generator
│   ├── frontend                 (15.2s, ~33,000 tokens)
│   └── backend                  (12.8s, ~28,000 tokens)
└── deployer                     (45.0s, tools only)

Total: ~1m 52s, ~113,000 tokens
Estimated cost: ~$1.04 per full deployment (GO scenario)
```

---

## Error Recovery

| 실패 지점 | 복구 전략 |
|-----------|----------|
| YouTube 트랜스크립트 추출 실패 | 사용자에게 수동 텍스트 입력 요청 |
| Council 에이전트 LLM 호출 실패 | 3회 재시도 → 폴백 모델 (`openai-gpt-5-nano`, $0.05/$0.40) |
| Cross-Examination 타임아웃 | 토론 스킵, Phase 1 결과만으로 채점 진행 |
| 코드 생성 불완전 | 누락 파일 감지 → 재생성 |
| GitHub API 실패 | 재시도 → 실패 시 코드를 ZIP으로 다운로드 제공 |
| DO App Platform 배포 실패 | 로그 분석 → 자동 config 수정 → 재배포 (최대 2회) |
| 배포 타임아웃 (5분) | 사용자에게 DO 대시보드 링크 제공 |
| Vision API 실패 (프레임 분석) | 텍스트 트랜스크립트만으로 진행 (visual_context = None) |
