# vibeDeploy 멀티모델 라우팅 스펙

작성일: 2026-03-17
상태: 제안 (구현 전)

---

## 1. 목적

vibeDeploy 파이프라인의 각 단계에 **최적의 LLM 모델**을 배정하여 품질, 비용, 속도를 동시에 최적화한다.
oh-my-opencode 스타일의 모델 다양화를 채택한다.

---

## 2. 현재 인프라 분석

### 2.1 이미 갖춰진 것

vibeDeploy는 이미 역할별 모델 배정 인프라를 보유하고 있다:

```python
# llm.py — 14개 역할, 각각 독립적 모델 지정 가능
DEFAULT_MODEL_CONFIG = {
    "council":           selected_runtime_model(),  # 현재: 모두 동일 모델
    "strategist":        selected_runtime_model(),
    "cross_exam":        selected_runtime_model(),
    "code_gen":          selected_runtime_model(),
    "code_gen_frontend": selected_runtime_model(),
    "code_gen_backend":  selected_runtime_model(),
    "ci_repair":         selected_runtime_model(),
    "doc_gen":           selected_runtime_model(),
    "image":             "fal-ai/flux/schnell",     # 유일하게 다른 모델
    "brainstorm":        selected_runtime_model(),
    "input":             selected_runtime_model(),
    "decision":          selected_runtime_model(),
    "web_search":        selected_runtime_model(),
}
```

환경변수 캐스케이드 오버라이드:
```
VIBEDEPLOY_MODEL_CODE_GEN_FRONTEND  (가장 구체적)
→ VIBEDEPLOY_MODEL_CODE_GEN
→ DO_INFERENCE_MODEL
→ VIBEDEPLOY_MODEL_ALL
→ VIBEDEPLOY_MODEL                  (가장 일반적)
```

레이트리밋 폴백 체인:
```python
"anthropic-claude-4.6-sonnet": ["openai-gpt-oss-120b", "anthropic-claude-opus-4.6"],
"openai-gpt-oss-120b": ["anthropic-claude-4.6-sonnet", "openai-gpt-oss-20b"],
```

### 2.2 부족한 것

| 항목 | 현재 상태 | 필요한 변경 |
|------|----------|-----------|
| Gemini 프로바이더 | 없음 | `langchain_google_genai` 연동 추가 |
| 직접 OpenAI API | DO Inference 경유만 | 직접 호출 옵션 추가 |
| 역할별 기본 모델 분리 | 모든 역할 동일 모델 | 역할별 최적 모델 매핑 |
| UI 디자인 역할 | 없음 | `ui_design` 역할 신규 정의 |
| 코드 검증 역할 | 없음 | `code_review` 역할 신규 정의 |
| 프롬프트 전략 확장 | anthropic, openai_gpt_oss, qwen3, deepseek_r1 | gemini 패밀리 추가 |
| 비용 테이블 | 6개 모델 | Gemini, GPT-5.4 추가 |

---

## 3. 모델 능력 비교 (2026년 3월 기준)

### 3.1 주요 모델 사양

| 모델 | 코드 생성 | 추론/계획 | UI/비주얼 | 구조화 출력 | 비용 (입력/출력 per 1M) | 컨텍스트 |
|------|----------|----------|----------|-----------|----------------------|---------|
| **GPT-5.4** | ★★★★★ | ★★★★★ | ★★★★☆ | ★★★★★ | $2.50 / $15.00 | 1,050K |
| **Claude Opus 4.6** | ★★★★★ | ★★★★★ | ★★★☆☆ | ★★★★★ | $15.00 / $75.00 | 1M |
| **Claude Sonnet 4.6** | ★★★★☆ | ★★★★☆ | ★★★☆☆ | ★★★★★ | $3.00 / $15.00 | 1M |
| **Gemini 3.1 Pro** | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★☆ | $2.00 / $12.00 | 1M |
| **DeepSeek V3.2** | ★★★★☆ | ★★★★☆ | ★★☆☆☆ | ★★★★☆ | $0.27 / $1.10 | 128K |
| **GPT-OSS-120B** (DO) | ★★★☆☆ | ★★★☆☆ | ★★☆☆☆ | ★★★★☆ | $0.10 / $0.70 | - |

### 3.2 태스크별 최적 모델

| 태스크 | 1순위 | 근거 | 2순위 (폴백) |
|--------|-------|------|-------------|
| 계획/아키텍처 설계 | **GPT-5.4** | 구성 가능 추론 깊이, 1M+ 컨텍스트, 도구 검색 | Claude Opus 4.6 |
| 프론트엔드 코드 생성 (TS) | **Claude Sonnet 4.6** | TypeScript 패턴 최고 품질, Opus의 98% 수준에 1/5 비용 | Claude Opus 4.6 |
| 백엔드 코드 생성 (Python) | **Claude Sonnet 4.6** | Python/FastAPI 강점, 지시 따르기 최상 | GPT-5.4 |
| UI 디자인/레이아웃 | **Gemini 3.1 Pro** | 네이티브 SVG/3D 렌더링, 비주얼 이해, 멀티모달 | GPT-5.4 |
| 코드 검증/리뷰 | **GPT-5.4** | 논리적 검증, 에러 패턴 탐지, 도구 검색 | Claude Sonnet 4.6 |
| 문서 생성 (PRD, 스펙) | **GPT-5.4** | 구조화된 비즈니스 문서 강점 | Gemini 3.1 Pro |
| Council 분석 (5회 병렬) | **DeepSeek V3.2** | 비용 효율 (5회 병렬 시 $0.27 vs $3.00), 충분한 품질 | GPT-OSS-120B |
| 브레인스톰 | **GPT-5.4** | 창의적 발상, 구조화된 아이디어 | Gemini 3.1 Pro |
| CI 수정 | **DeepSeek V3.2** | 단순 수정에 비용 효율 최적 | GPT-OSS-120B |
| 구조화 출력 (JSON) | **GPT-5.4** | 네이티브 JSON 스키마 강제 | Claude Sonnet 4.6 |

---

## 4. 제안하는 역할별 모델 배정

### 4.1 프로파일별 구성

#### 프로파일 A: 품질 최우선 (Quality-First)

```python
DEFAULT_MODEL_CONFIG = {
    "council":              "deepseek-v3.2",              # 비용 효율 (5회 병렬)
    "strategist":           "openai-gpt-5.4",             # 고품질 판정
    "cross_exam":           "openai-gpt-5.4",             # 논리적 토론
    "code_gen":             "anthropic-claude-4.6-sonnet", # 코드 생성 기본
    "code_gen_frontend":    "anthropic-claude-4.6-sonnet", # TS/React 최고
    "code_gen_backend":     "anthropic-claude-4.6-sonnet", # Python/FastAPI 최고
    "ci_repair":            "deepseek-v3.2",              # 단순 수정
    "doc_gen":              "openai-gpt-5.4",             # 구조화 문서
    "image":                "fal-ai/flux/schnell",        # 이미지 생성
    "brainstorm":           "openai-gpt-5.4",             # 창의적 발상
    "input":                "deepseek-v3.2",              # 입력 파싱 (단순)
    "decision":             "openai-gpt-5.4",             # 의사결정
    "ui_design":            "google-gemini-3.1-pro",      # UI 디자인 (신규)
    "code_review":          "openai-gpt-5.4",             # 코드 검증 (신규)
    "api_contract":         "openai-gpt-5.4",             # OpenAPI 스펙 (신규)
}
```

예상 비용: ~$1.00~$1.50/런

#### 프로파일 B: 비용 최적화 (Cost-Optimized)

```python
DEFAULT_MODEL_CONFIG = {
    "council":              "deepseek-v3.2",              # $0.27/M
    "strategist":           "anthropic-claude-4.6-sonnet", # 밸런스
    "cross_exam":           "deepseek-v3.2",              # 비용 절감
    "code_gen":             "anthropic-claude-4.6-sonnet", # 코드 품질
    "code_gen_frontend":    "anthropic-claude-4.6-sonnet", # 코드 품질
    "code_gen_backend":     "anthropic-claude-4.6-sonnet", # 코드 품질
    "ci_repair":            "deepseek-v3.2",              # $0.27/M
    "doc_gen":              "deepseek-v3.2",              # 비용 절감
    "image":                "fal-ai/flux/schnell",
    "brainstorm":           "deepseek-v3.2",              # 비용 절감
    "input":                "deepseek-v3.2",              # $0.27/M
    "decision":             "deepseek-v3.2",              # 비용 절감
    "ui_design":            "google-gemini-3.1-pro",      # $2/M (무료 티어)
    "code_review":          "anthropic-claude-4.6-sonnet", # 밸런스
    "api_contract":         "anthropic-claude-4.6-sonnet", # 밸런스
}
```

예상 비용: ~$0.30~$0.60/런

#### 프로파일 C: 균형 (Balanced) — 권장

```python
DEFAULT_MODEL_CONFIG = {
    "council":              "deepseek-v3.2",              # 비용 효율
    "strategist":           "openai-gpt-5.4",             # 고품질 판정
    "cross_exam":           "deepseek-v3.2",              # 비용 효율
    "code_gen":             "anthropic-claude-4.6-sonnet", # 코드 품질
    "code_gen_frontend":    "anthropic-claude-4.6-sonnet", # TS/React 최고
    "code_gen_backend":     "anthropic-claude-4.6-sonnet", # Python 최고
    "ci_repair":            "deepseek-v3.2",              # 단순 수정
    "doc_gen":              "openai-gpt-5.4",             # 구조화 문서
    "image":                "fal-ai/flux/schnell",
    "brainstorm":           "openai-gpt-5.4",             # 창의적 발상
    "input":                "deepseek-v3.2",              # 입력 파싱
    "decision":             "anthropic-claude-4.6-sonnet", # 밸런스
    "ui_design":            "google-gemini-3.1-pro",      # UI 전문
    "code_review":          "openai-gpt-5.4",             # 검증 전문
    "api_contract":         "openai-gpt-5.4",             # 구조화 출력
}
```

예상 비용: ~$0.60~$0.90/런

### 4.2 비용 시뮬레이션 상세

| 역할 | 호출 횟수 | 토큰 (입/출) | 현재 (단일모델) | 프로파일 C (균형) |
|------|---------|------------|---------------|----------------|
| council | 5× | 2K/4K | $0.30 | $0.03 (DeepSeek) |
| cross_exam | 1× | 4K/8K | $0.13 | $0.01 (DeepSeek) |
| strategist | 1× | 3K/2K | $0.04 | $0.04 (GPT-5.4) |
| doc_gen | 5× | 2K/4K | $0.30 | $0.10 (GPT-5.4) |
| code_gen_fe | 1× | 8K/20K | $0.32 | $0.32 (Claude Sonnet) |
| code_gen_be | 1× | 6K/15K | $0.25 | $0.25 (Claude Sonnet) |
| ui_design | 1× | 4K/6K | - | $0.08 (Gemini) |
| code_review | 1× | 10K/4K | - | $0.09 (GPT-5.4) |
| ci_repair | 0~3× | 3K/3K | $0.06 | $0.00 (DeepSeek) |
| **합계** | **~18회** | | **~$1.40** | **~$0.92** |

비용 절감: **~34%**, 품질: 유지 또는 향상 (역할별 최적 모델 사용)

---

## 5. 구현 상세

### 5.1 Gemini 프로바이더 추가 (llm.py)

```python
def _is_gemini_model(model: str) -> bool:
    """Gemini 모델 감지"""
    normalized = (model or "").strip().lower()
    return "gemini" in normalized or normalized.startswith("google-")


def _gemini_model_id(model: str) -> str:
    """내부 모델 ID → Google API 모델 ID 매핑"""
    mapping = {
        "google-gemini-3.1-pro": "gemini-3.1-pro",
        "google-gemini-2.5-pro": "gemini-2.5-pro-preview-05-06",
        "google-gemini-2.5-flash": "gemini-2.5-flash-preview-04-17",
    }
    return mapping.get(model.strip().lower(), model)


# get_llm() 함수에 Gemini 분기 추가 (Anthropic 분기 다음에 삽입)
def get_llm(model, temperature=0.5, max_tokens=3000, request_timeout=None):
    effective_max_tokens = max(256, max_tokens)
    effective_timeout = request_timeout or DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS

    # 1. Anthropic (기존)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if _is_anthropic_model(model) and anthropic_key:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(...)

    # 2. Gemini (신규)
    google_key = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if _is_gemini_model(model) and google_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=_gemini_model_id(model),
            google_api_key=google_key,
            temperature=_coerce_temperature_for_model(model, temperature),
            max_output_tokens=effective_max_tokens,
            timeout=effective_timeout,
        )

    # 3. DO Inference (기존)
    # 4. Direct OpenAI (기존 폴백)
```

### 5.2 신규 역할 정의 (llm.py)

```python
# DEFAULT_MODEL_CONFIG에 추가
DEFAULT_MODEL_CONFIG = {
    # ... 기존 14개 역할 ...
    "ui_design":     "google-gemini-3.1-pro",     # UI/디자인 생성
    "code_review":   "openai-gpt-5.4",            # 코드 검증
    "api_contract":  "openai-gpt-5.4",            # OpenAPI 스펙 생성
}

# _MODEL_ENV_OVERRIDES에 추가
_MODEL_ENV_OVERRIDES = {
    # ... 기존 ...
    "ui_design": ("VIBEDEPLOY_MODEL_UI_DESIGN", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "code_review": ("VIBEDEPLOY_MODEL_CODE_REVIEW", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "api_contract": ("VIBEDEPLOY_MODEL_API_CONTRACT", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
}
```

### 5.3 비용 테이블 확장 (cost.py)

```python
# PRICE_PER_1M_TOKENS에 추가
PRICE_PER_1M_TOKENS = {
    # ... 기존 ...
    "openai-gpt-5.4":          (2.50, 15.00),
    "openai-gpt-5.3-codex":    (2.50, 15.00),
    "google-gemini-3.1-pro":   (2.00, 12.00),
    "google-gemini-2.5-pro":   (1.25, 10.00),
    "google-gemini-2.5-flash": (0.15, 0.60),
    "deepseek-v3.2":           (0.27, 1.10),
    "deepseek-r1":             (0.55, 2.19),
}
```

### 5.4 프롬프트 전략 확장 (prompt_strategist.py)

```python
# Gemini 패밀리 전략 추가
def _gemini_guidance() -> str:
    return """
## Gemini-Specific Guidance
- Leverage native visual understanding for UI layout decisions
- Use structured JSON output mode for reliable schema generation
- Take advantage of 1M token context for full codebase analysis
- Multimodal: can process design mockups, wireframes, screenshots
- Prefer explicit step-by-step instructions over implicit conventions
- Temperature 0.3-0.5 for code, 0.7-0.8 for creative design
"""

# GPT-5.4 패밀리 전략 추가
def _gpt5_guidance() -> str:
    return """
## GPT-5.4-Specific Guidance
- Use configurable reasoning effort (low/medium/high/xhigh) based on task complexity
- Leverage tool search for cost optimization in agent workflows
- Use native structured output (JSON Schema) for guaranteed format compliance
- Response API endpoint for streaming and parallel tool calls
- Supports 128K output tokens for large code generation
- Enable computer-use when visual verification is needed
"""
```

### 5.5 레이트리밋 폴백 체인 확장

```python
def get_rate_limit_fallback_models(model: str) -> list[str]:
    fallbacks = {
        # 기존
        "anthropic-claude-4.6-sonnet": ["openai-gpt-5.4", "deepseek-v3.2"],
        "anthropic-claude-opus-4.6":   ["anthropic-claude-4.6-sonnet", "openai-gpt-5.4"],
        "openai-gpt-oss-120b":         ["anthropic-claude-4.6-sonnet", "deepseek-v3.2"],
        # 신규
        "openai-gpt-5.4":              ["anthropic-claude-4.6-sonnet", "google-gemini-3.1-pro"],
        "google-gemini-3.1-pro":       ["anthropic-claude-4.6-sonnet", "openai-gpt-5.4"],
        "deepseek-v3.2":               ["openai-gpt-oss-120b", "anthropic-claude-4.6-sonnet"],
    }
    return list(fallbacks.get(model, []))
```

### 5.6 temperature 보정 확장

```python
def _coerce_temperature_for_model(model: str, requested: float) -> float:
    normalized = model.lower()
    if "deepseek-r1" in normalized and requested < 0.5:
        return 0.6
    if "claude" in normalized:
        return min(max(requested, 0.0), 1.0)
    # Gemini: 0.0~2.0 범위 지원하지만 코드 생성 시 0.0~1.0 권장
    if "gemini" in normalized:
        return min(max(requested, 0.0), 1.0)
    return requested
```

---

## 6. 새로운 역할이 사용되는 파이프라인 위치

```
[Phase 3] API 계약서 생성
  → api_contract 역할 사용 (GPT-5.4: 구조화 출력으로 OpenAPI 스펙)

[Phase 4] 레이어드 코드 생성
  Layer 3 (디자인):
    → ui_design 역할 사용 (Gemini 3.1 Pro: 비주얼 이해 + CSS 생성)
  Layer 4 (비즈니스 로직):
    → code_gen_frontend 역할 사용 (Claude Sonnet 4.6: TypeScript/React)
    → code_gen_backend 역할 사용 (Claude Sonnet 4.6: Python/FastAPI)

[Phase 5] 빌드 검증
  → code_review 역할 사용 (GPT-5.4: 빌드 에러 분석 + 수정 제안)
```

---

## 7. 환경변수 구성 예시

```bash
# .env.production — 프로파일 C (균형)

# API 키
ANTHROPIC_API_KEY=sk-ant-api-...
GOOGLE_API_KEY=AIzaSy...
GRADIENT_MODEL_ACCESS_KEY=sk-do-...

# 역할별 모델 (선택적 — 기본값은 코드에 정의됨)
VIBEDEPLOY_MODEL_COUNCIL=deepseek-v3.2
VIBEDEPLOY_MODEL_STRATEGIST=openai-gpt-5.4
VIBEDEPLOY_MODEL_CODE_GEN_FRONTEND=anthropic-claude-4.6-sonnet
VIBEDEPLOY_MODEL_CODE_GEN_BACKEND=anthropic-claude-4.6-sonnet
VIBEDEPLOY_MODEL_DOC_GEN=openai-gpt-5.4
VIBEDEPLOY_MODEL_UI_DESIGN=google-gemini-3.1-pro
VIBEDEPLOY_MODEL_CODE_REVIEW=openai-gpt-5.4
VIBEDEPLOY_MODEL_API_CONTRACT=openai-gpt-5.4

# 레이트리밋 폴백 활성화
VIBEDEPLOY_ENABLE_RATE_LIMIT_MODEL_FALLBACKS=1

# 동시성 (멀티프로바이더이므로 높일 수 있음)
LLM_MAX_CONCURRENCY=3
LLM_MIN_INTERVAL_SECONDS=1.0
```

---

## 8. 구현 순서

| 순서 | 작업 | 예상 시간 | 의존성 |
|------|------|---------|--------|
| 1 | llm.py에 Gemini 프로바이더 추가 | 2시간 | GOOGLE_API_KEY |
| 2 | 신규 역할 3개 정의 (ui_design, code_review, api_contract) | 1시간 | - |
| 3 | cost.py에 GPT-5.4, Gemini, DeepSeek V3.2 가격 추가 | 30분 | - |
| 4 | prompt_strategist.py에 gemini, gpt5 가이던스 추가 | 2시간 | - |
| 5 | DEFAULT_MODEL_CONFIG를 프로파일 C로 변경 | 30분 | 1~4 완료 |
| 6 | 레이트리밋 폴백 체인 확장 | 30분 | - |
| 7 | temperature 보정 확장 | 15분 | - |
| 8 | model_capabilities.py에 Gemini 프로브 추가 | 1시간 | 1 완료 |
| 9 | 테스트 추가 (각 프로바이더 라우팅) | 2시간 | 1~5 완료 |
| **합계** | | **~10시간** | |

---

## 9. 리스크와 완화

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 다수 API 키 관리 | 운영 복잡성 증가 | 환경변수 캐스케이드가 이미 존재 |
| 프로바이더별 응답 형식 차이 | 파싱 실패 가능 | content_to_str() 정규화가 이미 존재 |
| Gemini의 JSON 출력 안정성 | 구조화 출력 실패 | GPT-5.4로 폴백 |
| 비용 예측 불확실성 | 예산 초과 | CostTracker가 이미 실시간 추적 |
| 레이턴시 차이 (프로바이더별) | 파이프라인 병목 | 비동기 + 세마포어가 이미 구현됨 |

---

## 부록: 모델 접속 경로 정리

| 모델 | 접속 경로 | API 엔드포인트 |
|------|----------|--------------|
| Claude Sonnet 4.6 | Anthropic 직접 API | api.anthropic.com/v1/messages |
| Claude Opus 4.6 | Anthropic 직접 API | api.anthropic.com/v1/messages |
| GPT-5.4 | DO Inference 또는 직접 OpenAI | inference.do-ai.run/v1/responses |
| GPT-OSS-120B | DO Inference | inference.do-ai.run/v1/chat/completions |
| Gemini 3.1 Pro | Google AI 직접 API | generativelanguage.googleapis.com |
| DeepSeek V3.2 | DeepSeek API 또는 DO Inference | api.deepseek.com/v1/chat/completions |
| fal.ai Flux | fal.ai API | - |
