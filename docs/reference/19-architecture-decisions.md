# vibeDeploy 아키텍처 결정 기록 (ADR)

확정일: 2026-03-17
상태: **확정** — 구현 시 이 문서가 기준

---

## 0. 해커톤 제약사항 (모든 결정의 상위 조건)

DigitalOcean Gradient™ AI Hackathon 공식 규칙 기준:

| 제약 | 내용 | 준수 방법 |
|------|------|----------|
| **DO Gradient AI 필수 사용** | "Must use DigitalOcean Gradient™ AI full stack features" | 핵심 빌드 파이프라인(Council, Code Gen, Deploy)에서 DO Gradient Serverless Inference 사용 |
| **심사: 기술 구현** | "Does the project thoroughly leverage the required tool?" | Provider adapter가 DO Gradient를 기본 라우팅으로, 외부 API는 보조/확장으로 |
| **DO App Platform 배포** | 생성된 앱과 vibeDeploy 자체 모두 DO 배포 | `.do/app.yaml` 유지 |
| **공개 레포 + OSI 라이선스** | 코드 공개 필수 | GitHub public repo + LICENSE 파일 |
| **데모 영상 3분 이내** | 기능 시연 영상 | 별도 제작 |

### ADR-A0: 외부 API 직접 호출 + DO Gradient 풀스택 활용 정책

**결정**: 외부 LLM API (Gemini, OpenAI, Anthropic)는 **직접 호출**. DO Gradient는 **LLM 외 전체 기능 활용**.

```
[외부 LLM API — 직접 호출]
  Google Gemini  → google-genai SDK 직접 (Zero-Prompt 탐색)
  OpenAI         → openai SDK 직접 (코드 생성/계획)
  Anthropic      → anthropic SDK 직접 (코드 생성)
  ※ DO Inference 경유하지 않음 (서브스크립션 레벨 제약)

[DO Gradient AI Platform — 풀스택 활용]
  ├── ADK Agent Runtime          — @entrypoint, gradient agent deploy
  ├── Knowledge Base (RAG)       — 아이디어 발굴용 KB, 프레임워크 패턴 KB
  ├── Agent Evaluation           — 생성 앱 품질 평가 메트릭
  ├── Agent Guardrails           — 입력 필터링, 콘텐츠 안전
  ├── Agent Tracing              — @trace_tool, @trace_llm 관측성
  ├── Multi-Agent Routing        — Council 에이전트 DO Agent 배포
  ├── A2A Protocol               — Zero-Prompt → Build Agent 전달
  ├── App Platform               — vibeDeploy + 생성 앱 배포
  ├── Spaces Object Storage      — 생성 앱 아티팩트 저장
  └── Image Generation           — GPT-image-1 via DO Inference (유일한 Inference 활용)
```

**근거**: DO Inference의 서브스크립션 레벨 제약으로 외부 LLM은 직접 호출이 안정적. DO Gradient의 진정한 차별화는 LLM 호출이 아니라 **에이전트 개발/배포/평가/관측 플랫폼 기능**에 있으며, 이를 "thoroughly" 활용하는 것이 심사 점수를 극대화한다.

---

## 1. 확정된 아키텍처 결정 (A1~A4)

### ADR-A1: Google SDK 선택

**결정**: `google-genai` 공식 SDK 직접 사용

| 항목 | 내용 |
|------|------|
| 선택 | `google-genai` (공식 Python SDK) |
| 기각 | `langchain_google_genai` (LangChain 래퍼) |
| 근거 | doc 17 기준 일치. `response_schema` 네이티브 지원. 최신 기능(Batch API, Context Caching) 즉시 사용 가능. Gemini 3.1 preview 모델 지원 |
| 영향 | `agent/providers/google_adapter.py`에서 `google.genai.Client` 사용. LangChain 의존성 아님 |
| 제약 | Zero-Prompt 탐색 lane 전용. 핵심 빌드 lane은 DO Gradient 경유 |

### ADR-A2: Provider Adapter 인터페이스

**결정**: 벤더별 파사드 + registry 라우팅

| 항목 | 내용 |
|------|------|
| 선택 | 벤더별 독립 adapter (google_adapter, openai_adapter, anthropic_adapter) + `registry.py`가 canonical model ID로 라우팅 |
| 기각 | 공통 ABC (`generate()` 메서드 통일) |
| 근거 | doc 17의 `api_style` 필드가 벤더별 고유 API 형태를 반영 (`google_generate_content`, `openai_responses`, `anthropic_messages`). 벤더 고유 기능(vision, grounding, structured output) 손실 없음 |
| 영향 | `agent/providers/` 패키지 신설. `agent/llm.py`는 registry facade로 축소 |

```python
# registry.py 라우팅 예시
class ProviderRegistry:
    def get_adapter(self, model_id: str) -> ProviderAdapter:
        spec = CAPABILITY_REGISTRY[resolve_canonical(model_id)]
        match spec["provider"]:
            case "google":   return GoogleAdapter(spec)
            case "openai":   return OpenAIAdapter(spec)
            case "anthropic": return AnthropicAdapter(spec)
```

### ADR-A3: Zero-Prompt 세션 저장소

**결정**: PostgreSQL (기존 store.py 확장)

| 항목 | 내용 |
|------|------|
| 선택 | PostgreSQL — 기존 `agent/db/store.py` 패턴 확장 |
| 기각 | In-memory + LangGraph checkpoint |
| 근거 | lineage 조회(`source_video_id → card_id → build_job_id → deployment`)에 SQL 필수. 서버 재시작 시 데이터 유지. 기존 DB 인프라 재활용 |
| 영향 | `agent/db/store.py`에 Zero-Prompt 세션/카드/빌드큐 테이블 추가 |

```sql
-- 추가 테이블 (개념)
zero_prompt_sessions (session_id, status, created_at, total_cost)
zero_prompt_cards (card_id, session_id, status, idea_json, score, source_video_id)
build_queue (queue_id, card_id, position, status, pipeline_thread_id)
```

### ADR-A4: 빌드 검증 환경

**결정**: Docker SDK (컨테이너)

| 항목 | 내용 |
|------|------|
| 선택 | Docker SDK — Python `docker` 패키지로 컨테이너 실행 |
| 기각 | tmpdir + subprocess (격리 부족), E2B (외부 의존성 + 비용) |
| 근거 | DO App Platform과 환경 일치 가능 (Node.js/Python 버전). 완전 격리로 보안 위험 제거. 리소스 제한(메모리, CPU, 타임아웃) 네이티브 지원 |
| 영향 | `agent/nodes/build_validator.py`에서 `docker.from_env()` 사용. Docker 데몬 필수 (서버 환경에서 Docker-in-Docker 또는 소켓 마운트) |
| 주의 | DO App Platform에서 Docker-in-Docker는 제한될 수 있음 → 서버에서는 빌드용 별도 Droplet 또는 Docker 소켓 접근 필요 |

```python
# build_validator.py 개념
import docker
client = docker.from_env()
container = client.containers.run(
    "node:20-slim",
    command="sh -c 'npm ci && npm run build'",
    volumes={tmpdir: {"bind": "/app", "mode": "rw"}},
    mem_limit="512m",
    cpu_period=100000, cpu_quota=50000,  # 0.5 CPU
    network_mode="none",  # 네트워크 격리
    remove=True,
    timeout=120,
)
```

---

## 2. 확정된 정책 결정 (B1~B5)

### ADR-B1: 빌드 큐 동시 실행

**결정**: 1개 고정

| 항목 | 내용 |
|------|------|
| 값 | `MAX_CONCURRENT_BUILDS = 1` |
| 근거 | 리소스 예측 가능. 비용 제어 용이. MVP에 충분 |
| 향후 | 환경변수로 변경 가능하도록 설계하되 기본값 1 고정 |

### ADR-B2: GO/NO-GO 임계값

**결정**: 고정 70점 + 카테고리 확장

| 항목 | 내용 |
|------|------|
| 임계값 | `GO_THRESHOLD = 70` (고정, 동적 하향 없음) |
| 후보 소진 대응 | 다음 검색 카테고리로 확장 (최대 5라운드) |
| 라운드 순서 | Science&Tech → Education → HowTo → Startup → Korean Market |
| 근거 | 임계값 하향은 품질 하락 초래. 카테고리 확장이 더 건전한 접근 |

### ADR-B3: 레거시 호환 shim

**결정**: P4 완료 시 즉시 제거

| 항목 | 내용 |
|------|------|
| 정책 | 신규 코드에서 `openai-*`, `anthropic-*`, `google-*` 별칭 사용 금지 |
| 읽기 시점 | `LEGACY_MODEL_ALIASES` 매핑으로 1회 변환 (doc 17 §2.2) |
| 제거 시점 | P4 마일스톤 완료 시 `LEGACY_MODEL_ALIASES` dict 자체 제거 |
| 근거 | doc 17 원칙 준수. 장기 유지는 코드 혼란 초래 |

### ADR-B4: API 버전닝

**결정**: 버전 없음 — `/api/zero-prompt/*`

| 항목 | 내용 |
|------|------|
| 패턴 | `/api/zero-prompt/start`, `/api/zero-prompt/go`, `/api/zero-prompt/pass` |
| 근거 | 기존 `/run`, `/brainstorm`, `/dashboard/*`도 버전 없음. 내부 플랫폼이므로 불필요. 일관성 유지 |
| 향후 | 외부 공개 시 `/api/v1/` 접두사 추가 검토 |

### ADR-B5: 비용 추적 단위

**결정**: 요청 단위 (per LLM call)

| 항목 | 내용 |
|------|------|
| 기록 단위 | 각 LLM 호출의 `input_tokens`, `output_tokens`, `model_id`, `surcharge_type`, `cost_usd` |
| 세션 합산 | SQL 쿼리로 세션/빌드잡 단위 합산 |
| surcharge 반영 | cache hit, long-context (>200K), grounding 비용 별도 기록 |
| 근거 | 상세 분석 가능 + 세션 합산도 가능. 토큰 단위는 과도, 세션 단위는 불충분 |

---

## 3. 결정 적용 매트릭스

| 결정 | 영향받는 문서 | 영향받는 이슈 |
|------|-------------|-------------|
| A1 (google-genai) | 15, 16, 151, 163 | #53, #62 |
| A2 (벤더별 파사드) | 15, 18, 151~154 | #69, #53~#56 |
| A3 (PostgreSQL) | 16, 168 | #67, #72 |
| A4 (Docker) | 12, 111 | #34 |
| B1 (빌드 1개) | 16, 168 | #67 |
| B2 (70점 고정) | 16, 167 | #66 |
| B3 (P4 제거) | 17, 18 | #73 |
| B4 (버전 없음) | 18, 168 | #67 |
| B5 (요청 단위) | 15, 153 | #55 |
| §0 (DO Gradient 필수) | 11, 15, 16, 18 | 전체 |

---

## 4. 미결정 사항 — 없음

**모든 아키텍처 및 정책 결정이 확정되었습니다.**

외부 의존성 리스크(Exa 정책 변경, preview 모델 ID 변경, YouTube IP 차단)는 설계에 폴백이 이미 포함되어 있으므로 추가 결정이 필요하지 않습니다.
