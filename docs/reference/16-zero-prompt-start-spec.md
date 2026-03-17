# vibeDeploy Zero-Prompt Start 스펙 (v2)

작성일: 2026-03-17 | 최종 수정: 2026-03-17
상태: 제안 (구현 전)

---

## 1. 개요

사용자가 **"Start" 버튼 하나만 누르면** 시스템이 자동으로:
1. YouTube에서 트렌딩/고인게이지먼트 영상을 **스트리밍으로** 탐색하고
2. `gemini-3.1-flash-lite-preview`로 아이디어를 추출하고
3. **논문 검색**(OpenAlex + arXiv)으로 아이디어를 브레인스톰/강화하고
4. 경쟁사를 자동 분석(**Brave + Exa 병렬 검색**)하고
5. **GO / NO-GO 판정**을 내리며
6. **GO가 10개 모일 때까지** 루프를 계속한다
7. 모든 과정을 **Manus 스타일 액션 피드**로 실시간 SSE 시각화한다

핵심 원칙:
- **고정 배치가 아닌 스트리밍 루프**. 한 영상씩 처리하며 GO/NO-GO를 판단한다.
- **GO / NO-GO 모두 액션 피드에 실시간 표시**한다.
- **탐색 기준: GO 패널에 10개가 유지되고 있느냐**
  - GO 패널 < 10개 → 탐색 진행
  - GO 패널 = 10개 → 탐색 일시정지
  - 사용자가 GO 카드를 **삭제**하거나 **"GO!"로 빌드 시작**하면 → 패널 < 10개 → 탐색 자동 재개
- 사용자가 **"GO!" 버튼**을 누르면 해당 아이디어는 빌드 큐에 등록된다. 빌드 워커가 비어 있으면 즉시 `building`, 아니면 `build_queued`가 되며, **GO 슬롯이 재계산되므로 탐색이 자동 재개**된다.
- **항상 사용자에게 10개의 GO 선택지가 제공되는 상태를 유지**하는 것이 목표.

### 1.1 현재 문서의 문제점과 이번 보강 방향

이 문서의 기존 v2 초안은 방향성은 좋지만, 실제 구현 단계로 들어가면 다음 문제가 있었다.

| 문제 | 영향 | 이번 보강 |
|------|------|----------|
| 탐색 루프와 빌드 파이프라인, Council의 관계가 불명확 | 구현자마다 다른 해석 가능 | Zero-Prompt 평가 단계와 빌드 핸드오프를 명시적으로 분리 |
| 에이전트/페르소나 정의 부재 | 프롬프트 품질과 역할 경계가 흔들림 | 실행 에이전트, 시스템 에이전트, 출력 계약을 고정 |
| 도구 호출 계약 부재 | 타임아웃, 재시도, 캐시, 폴백이 제각각 구현될 위험 | 도구별 호출 규칙과 SSE 책임을 정의 |
| 세션/카드/API 스키마 부재 | 백엔드와 프론트 상태 모델이 쉽게 어긋남 | `session_id`, `card_id`, 액션 API, SSE envelope를 추가 |
| 파일 구조가 기존 코드베이스와 부분 충돌 | 실제 구현 시 파일 배치 혼선 | `agent/zero_prompt/` 패키지 기준의 권장 구조를 제시 |

이번 보강본의 목표는 "아이디어 설명서"가 아니라, **구현자가 바로 모듈과 상태 모델을 만들 수 있는 실행 계약서**로 올리는 것이다.

---

## 2. 스트리밍 루프 아키텍처

### 2.1 핵심 플로우

```
[Start 버튼] → YouTube Discovery (후보 풀 구성)
                    │
                    ▼
         ┌──── 스트리밍 루프 ────┐
         │                       │
         │  영상 N번째 선택      │
         │       ↓               │
         │  트랜스크립트 추출    │  gemini-3.1-flash-lite-preview
         │       ↓               │
         │  아이디어 추출        │  gemini-3.1-flash-lite-preview
         │       ↓               │
         │  📚 논문 검색         │  OpenAlex + arXiv (무료)
         │       ↓               │
         │  🧠 브레인스톰        │  gemini-3.1-flash-lite-preview
         │  (아이디어 + 논문)    │  → 강화된 아이디어
         │       ↓               │
         │  🏢 경쟁사 검색       │  Brave + Exa 병렬 검색 (무료)
         │       ↓               │
         │  ⚖️ GO / NO-GO 판정  │  gemini-3.1-flash-lite-preview
         │       ↓               │
         │  GO → 수집            │
         │  NO-GO → 다음 영상    │
         │                       │
         └── GO 10개까지 반복 ──┘
                    │
                    ▼
         [GO 아이디어가 사이드 패널에 실시간 누적]
         │
         ├─ GO 패널 < 10개 → 루프 계속
         ├─ GO 패널 = 10개 → 루프 일시정지
         │
         [사용자 행동]
         ├─ "GO!" 클릭 → 빌드 큐 등록(또는 즉시 빌드) + 슬롯 재계산 → 탐색 재개
         ├─ "삭제" 클릭 → 슬롯 비움 → 탐색 재개
         └─ 아무것도 안 함 → 10개 유지, 탐색 대기
```

### 2.2 배치가 아닌 이유

| 기존 설계 (v1) | 새 설계 (v2) |
|---------------|-------------|
| 300개 수집 → 전부 분석 → 랭킹 → 선택 | 하나씩 분석 → GO/NO-GO → 10개면 멈춤 |
| 43분 대기 후 결과 | **실시간으로 GO가 쌓이는 것을 시청** |
| 비용: ~$2.34 고정 | 비용: GO 10개 나올 때까지만 (더 저렴) |
| UX: 로딩 → 결과 | UX: **Manus처럼 에이전트 행동 실시간 관찰** |

### 2.3 명시적 아키텍처 결정

- **Zero-Prompt의 탐색/평가 단계는 Vibe Council을 사용하지 않는다.**
  - YouTube 탐색, 아이디어 추출, 논문 검색, 경쟁 분석, GO/NO-GO는 Zero-Prompt 전용 경량 에이전트 체인으로 수행한다.
- **사용자가 `GO!`를 누르면 기존 빌드 파이프라인으로 handoff한다.**
  - 기본값은 `skip_council=true`로 즉시 빌드에 진입한다.
  - 추후 옵션으로 `with_council=true`를 추가할 수 있지만, Phase 0 기본 동작은 비활성화다.
- **세션 단위 동시성은 `탐색 워커 1 + 빌드 워커 1`이다.**
  - 탐색은 영상 1개씩 순차 처리한다.
  - 빌드는 동시에 1개만 실행한다.
- **Phase 0의 세션 저장소는 인메모리 우선이다.**
  - 브라우저 재연결을 위해 `session_id` 기준 조회와 SSE 재구독은 지원한다.
  - 영구 저장은 후속 단계이며, Phase 0의 필수 범위가 아니다.
- **Zero-Prompt 전용 구현은 `agent/zero_prompt/` 패키지에 모은다.**
  - 기존 `agent/tools/youtube.py`, `agent/sse.py`, `agent/server.py`, `web/src/hooks/use-pipeline-monitor.ts`는 어댑터/패턴 재사용 대상으로 취급한다.

### 2.4 에이전트 구성과 페르소나

Zero-Prompt는 "한 개의 만능 에이전트"가 아니라, 책임이 좁고 출력이 구조화된 소형 에이전트 집합으로 구성한다.

| Agent ID | 유형 | 페르소나 | 책임 | 주 출력 | 모델 |
|----------|------|----------|------|--------|------|
| `discovery_curator` | 결정론적 + 규칙 | 트렌드 에디터 | 후보 영상 수집, engagement 필터링, 중복 제거 | `VideoCandidate[]` | 없음 |
| `transcript_fetcher` | 결정론적 | 기록 담당 조사원 | 자막/메타데이터 수집, 토큰 수 계산 | `TranscriptArtifact` | 없음 |
| `insight_miner` | LLM | 제품 발굴가 | 트랜스크립트에서 앱 아이디어 구조화 | `AppIdea` | `gemini-3.1-flash-lite-preview` |
| `research_librarian` | LLM + API | 연구 사서 | 논문 검색 쿼리 생성, OpenAlex/arXiv 수집 | `PaperMetadata[]` | `gemini-3.1-flash-lite-preview` |
| `novelty_strategist` | LLM | 응용 연구자 | 논문 근거 기반 기능/차별화 강화 | `EnhancedIdea` | `gemini-3.1-flash-lite-preview` |
| `market_scout` | LLM + API | 경쟁정보 분석가 | Brave 결과 요약, 시장 공백과 포화도 판단 | `MarketAnalysis` | `gemini-3.1-flash-lite-preview` |
| `verdict_judge` | 규칙 + LLM | 투자 심사역 | 점수 계산, GO/NO-GO, 사유 작성 | `Verdict` | `gemini-3.1-flash-lite-preview` |
| `queue_conductor` | 결정론적 | 관제실 오퍼레이터 | 세션 상태, GO 슬롯, 빌드 FIFO, pause/resume 관리 | `ZeroPromptSession` | 없음 |
| `build_runner` | 결정론적 | 배포 핸드오프 관리자 | 선택된 카드의 기존 `/run` 파이프라인 호출 | `BuildJobRef` | 없음 |

**페르소나 작성 규칙**
- 모든 LLM 에이전트는 과장된 마케팅 카피가 아니라 **짧고 근거 중심의 작업어조**를 사용한다.
- 아이디어 이름은 짧고 구체적으로 작성하고, 점수/근거/출처를 함께 남긴다.
- NO-GO 판정은 감정 표현 없이 `시장 포화`, `논문 근거 부족`, `차별화 미흡`, `기술 난이도 높음` 같은 분류형 사유를 남긴다.

### 2.5 에이전트별 도구 호출 계약

| Agent ID | 허용 도구 | 호출 규칙 | 폴백 |
|----------|----------|----------|------|
| `discovery_curator` | `youtube_discovery.fetch_candidate_pool()` | timeout 20초, retry 2회, 카테고리별 결과 병합, 15분 캐시 | 쿼리 축소 후 재시도 |
| `transcript_fetcher` | `youtube.extract_youtube_transcript()` | timeout 30초, retry 1회, 토큰 수 계산 필수 | 메타데이터 컨텍스트로 대체 |
| `research_librarian` | `paper_search.search_openalex()`, `paper_search.search_arxiv()` | OpenAlex 우선, arXiv는 1req/3s throttle, 24시간 캐시 | OpenAlex 실패 시 arXiv-only |
| `market_scout` | `competitive_analysis.unified_search()` | Brave+Exa 병렬, timeout 15초, 12시간 캐시 | 양쪽 결과 병합, 중복 제거, 양쪽 다 나오면 confidence=high |
| `build_runner` | `POST /api/run` handoff | idempotency key 포함, 동일 카드 중복 요청 금지 | `build_failed` 상태 기록 |

**LLM 호출 공통 규칙**
- 각 단계는 기본적으로 **1회의 구조화 출력 호출**을 사용한다.
- 구조화 출력 파싱 실패 시 **동일 입력으로 1회 self-repair 재시도**한다.
- 2회 연속 실패하면 해당 카드는 `nogo`로 보내지 않고 `analysis_error` 로그를 남긴 뒤 다음 후보로 넘어간다.
- 모든 LLM 단계는 `session_id`, `card_id`, `video_id`를 로그 컨텍스트에 포함한다.

### 2.6 세션, 카드, 식별자 모델

```python
class ZeroPromptIds(BaseModel):
    session_id: str          # zp_20260317_xxx
    card_id: str             # card_<video_id>_<hash8>
    build_job_id: str | None # build_<ts>_<hash8>


class ZeroPromptCard(BaseModel):
    card_id: str
    status: Literal[
        "analyzing",
        "go_ready",
        "build_queued",
        "building",
        "deployed",
        "nogo",
        "passed",
        "build_failed",
    ]
    title: str
    score: int | None = None
    reason: str | None = None
    source_video_id: str
    queue_position: int | None = None
    build_thread_id: str | None = None
    live_url: str | None = None


class ZeroPromptSession(BaseModel):
    session_id: str
    status: Literal["idle", "running", "paused", "completed", "error"]
    goal_go_cards: int = 10
    cards: list[ZeroPromptCard]
    analyzed_count: int = 0
    candidate_count: int = 0
    go_ready_count: int = 0
    build_queue_count: int = 0
    build_active: bool = False
    total_cost_usd: float = 0.0
```

**ID 규칙**
- `session_id`는 브라우저가 없는 백엔드 생성 가능해야 하며 UUID 또는 `zp_<date>_<rand>` 형식이면 충분하다.
- `card_id`는 `video_id` 기반으로 안정적으로 생성하여 중복 GO 카드 발생을 막는다.
- 빌드 파이프라인으로 handoff할 때의 `thread_id`는 `build_thread_id`로 별도 저장한다.

**슬롯 계산 규칙**
- 탐색 재개 조건은 `go_ready < 10` 이다.
- `build_queued`와 `building`은 UI에는 남아 있을 수 있지만, "사용자가 지금 선택 가능한 GO 카드" 수에는 포함하지 않는다.

---

## 3. Manus 스타일 액션 피드

### 3.1 UI 사양

- **300줄 뷰포트** (스크롤 가능, 최대 300줄 유지)
- 자동 스크롤 (최하단 고정, 수동 스크롤 시 해제)
- 다크 테마 (`bg-zinc-950`, 모노스페이스 폰트)
- 액션별 아이콘 + 색상 코딩
- Framer Motion: 새 로그 엔트리 fadeInUp 애니메이션
- AnimatePresence: 오래된 엔트리 fade out (300줄 초과 시)

### 3.2 액션 피드 예시

```
[00:01] 🔍 YouTube 트렌딩 검색 시작 (Science & Technology, Education)
[00:03] 📋 후보 47개 발견 — 인게이지먼트 순 정렬

[00:04] ─── 영상 1/47 ──────────────────────────────────
[00:04] 🎬 "Best AI Tools 2026" (조회수 1.2M, 👍 45K, 💬 3.2K)
[00:06] 📝 트랜스크립트 추출 중... (en, 4,832 tokens)
[00:08] 🧠 Gemini 분석 중...
[00:10] 💡 아이디어: "AI 워크플로우 자동화 도구"
[00:10]    ├─ 타겟: 마케터, PM
[00:10]    ├─ 핵심기능: 노코드 파이프라인, Slack 연동
[00:10]    └─ confidence: 0.82
[00:11] 📚 논문 검색: "workflow automation machine learning pipeline"
[00:12]    ├─ [1] "AutoML Pipeline Optimization" (2025, 142 citations)
[00:12]    ├─ [2] "Low-Code AI Workflow Systems" (2024, 89 citations)
[00:12]    └─ [3] "Human-in-the-Loop Automation" (2025, 67 citations)
[00:13] 🧠 브레인스톰: 논문 기반 강화...
[00:14]    └─ 추가 기능: AutoML 기반 자동 파이프라인 추천
[00:15] 🏢 경쟁사 검색: Zapier, Make, n8n, Bardeen (4개 발견)
[00:16]    └─ 시장 포화도: ● 높음 (주요 4개사 확립)
[00:17] ❌ NO-GO — 시장 포화, 차별화 어려움 (score: 32/100)

[00:18] ─── 영상 2/47 ──────────────────────────────────
[00:18] 🎬 "This App Changed How I Care For My Dog" (조회수 890K, 👍 52K)
[00:20] 📝 트랜스크립트 추출 중... (en, 6,210 tokens)
[00:22] 🧠 Gemini 분석 중...
[00:24] 💡 아이디어: "AI 반려동물 건강 추적 앱"
[00:25] 📚 논문 검색: "pet health IoT wearable veterinary AI"
[00:26]    ├─ [1] "AI 수의학 진단 정확도 94%" (2025, 203 citations)
[00:26]    └─ [2] "IoT 기반 반려동물 활동량 분석" (2024, 156 citations)
[00:27] 🧠 브레인스톰: 논문 기반 강화...
[00:28]    └─ 추가: AI 사진 기반 피부질환 사전 탐지 (논문 근거)
[00:29] 🏢 경쟁사: PetPace, FitBark (한국 시장 미진출)
[00:30]    └─ 시장 포화도: ○ 낮음 (한국 시장 공백)
[00:31] ✅ GO #1 — AI 진단 + 한국 시장 갭 (score: 87/100)
[00:31]    └─ 📌 수집됨 [1/10]

...

[02:15] ✅ GO #3 — "프리랜서 세금 자동화" (score: 82/100)
[02:15]    └─ 📌 사이드 패널에 추가 [3/10]

─── 사용자가 GO #1 "AI 반려동물 건강 추적"의 [🚀 GO!] 클릭 ───

[02:20] 🚀 빌드 큐 추가: "AI 반려동물 건강 추적 앱" (score: 87)
[02:20]    └─ 빌드 큐 위치: #1 → 즉시 빌드 시작
[02:21] 🔨 빌드 파이프라인 시작: Input → Build → Deploy (`skip_council=true`)
[02:21]    input_processor: 아이디어 분석 중...
[02:23]    inspiration_agent: 레퍼런스 매핑 중...

[02:24] ─── 영상 8/47 (탐색 계속, GO 대기 슬롯: 2/10) ──────
[02:24] 🎬 "How I Automated My Finances" (520K views)
[02:26] 📝 트랜스크립트 추출 중...
       ... (탐색과 빌드가 동시 진행) ...
```

### 3.3 SSE 이벤트 타입 (신규)

기존 `format_sse()` 확장:

```python
# 새로운 Zero-Prompt 이벤트 타입
ZERO_PROMPT_EVENTS = {
    # Session
    "zp.session.start":      {"icon": "▶", "color": "green"},
    "zp.session.pause":      {"icon": "⏸", "color": "yellow"},
    "zp.session.resume":     {"icon": "▶", "color": "green"},
    "zp.session.error":      {"icon": "⚠", "color": "red"},

    # Discovery
    "zp.search.start":       {"icon": "🔍", "color": "blue"},
    "zp.search.complete":    {"icon": "📋", "color": "blue"},

    # Per-video loop
    "zp.video.start":        {"icon": "🎬", "color": "default"},
    "zp.transcript.start":   {"icon": "📝", "color": "blue"},
    "zp.transcript.complete":{"icon": "📝", "color": "green"},
    "zp.insight.start":      {"icon": "🧠", "color": "purple"},
    "zp.insight.complete":   {"icon": "💡", "color": "purple"},

    # Paper search
    "zp.paper.search":       {"icon": "📚", "color": "blue"},
    "zp.paper.found":        {"icon": "📚", "color": "green"},

    # Brainstorm
    "zp.brainstorm.start":   {"icon": "🧠", "color": "purple"},
    "zp.brainstorm.complete":{"icon": "🧠", "color": "green"},

    # Competitive
    "zp.compete.start":      {"icon": "🏢", "color": "blue"},
    "zp.compete.complete":   {"icon": "🏢", "color": "default"},

    # Verdict
    "zp.go":                 {"icon": "✅", "color": "green"},
    "zp.nogo":               {"icon": "❌", "color": "red"},
    "zp.card.passed":        {"icon": "↩", "color": "yellow"},

    # Build queue / handoff
    "zp.build.queued":       {"icon": "🚀", "color": "blue"},
    "zp.build.start":        {"icon": "🔨", "color": "green"},
    "zp.build.progress":     {"icon": "🔨", "color": "default"},
    "zp.build.complete":     {"icon": "🚀", "color": "green"},
    "zp.build.failed":       {"icon": "⚠", "color": "red"},

    "zp.complete":           {"icon": "🎉", "color": "green"},
}
```

### 3.4 SSE 이벤트 페이로드 계약

모든 Zero-Prompt SSE 이벤트는 아래 envelope를 따른다.

```json
{
  "type": "zp.go",
  "session_id": "zp_20260317_a1b2c3",
  "event_id": "evt_000184",
  "ts": "2026-03-17T14:21:03.204Z",
  "card_id": "card_dQw4w9WgXcQ_91a1ef20",
  "message": "GO #3 - AI 반려동물 건강 추적 앱",
  "payload": {
    "score": 87,
    "reason": "논문 근거 확보, 경쟁 밀도 낮음"
  },
  "cost_usd": 0.0038
}
```

필수 필드:
- `type`, `session_id`, `event_id`, `ts`, `message`

조건부 필드:
- `card_id`: 카드 관련 이벤트에서 필수
- `payload`: 단계별 상세 데이터
- `cost_usd`: 해당 단계까지 누적 비용 또는 단계 비용

### 3.5 화면 레이아웃

```
┌──────────────────────────────────────────────────────────────────────┐
│  vibeDeploy Zero-Prompt                            [● 탐색 중...]   │
├────────────────────────────────────┬─────────────────────────────────┤
│                                    │                                 │
│                                                                      │
│  ┌─ 칸반 보드 (상단) ───────────────────────────────────────────────┐ │
│  │ 🔍 탐색 중  │ ✅ GO 대기(3/10)│ 🔨 빌드 중  │ 🚀 배포됨 │ ❌ NO-GO    │ │
│  │ ──────────  │ ──────────────  │ ──────────  │ ────────  │ ──────────  │ │
│  │ 🎬 영상 12 │┌──────────────┐│┌───────────┐│┌────────┐│┌──────────┐│ │
│  │ 🧠 분석 중 ││ 반려동물  87 │││ 세금자동화│││ 번역 ✅│││ AI워크플로││ │
│  │            ││ [🚀GO!][패스]│││  빌드 23% │││live URL│││ 32점     ││ │
│  │            │└──────────────┘││  ████░░░░ ││└────────┘││ 시장 포화 ││ │
│  │            │┌──────────────┐│└───────────┘│          │└──────────┘│ │
│  │            ││ AI노트   76  ││             │          │┌──────────┐│ │
│  │            ││ [🚀GO!][패스]││             │          ││ SNS분석  ││ │
│  │            │└──────────────┘│             │          ││ 41점     ││ │
│  │            │┌──────────────┐│             │          ││ 기술난이도││ │
│  │            ││ 운동추적  81 ││             │          │└──────────┘│ │
│  │            ││ [🚀GO!][패스]││             │          │ ...        │ │
│  │            │└──────────────┘│             │          │            │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─ 액션 피드 (하단, 300줄 뷰포트, 리사이즈 가능) ─────────────────┐ │
│  │ [00:04] 🎬 영상 1/47 "Best AI Tools 2026" (1.2M views)         │ │
│  │ [00:08] 🧠 Gemini → "AI 워크플로우 자동화"                      │ │
│  │ [00:11] 📚 논문 3편 → AutoML Pipeline (142 citations)           │ │
│  │ [00:15] 🏢 Zapier, Make, n8n (포화)                             │ │
│  │ [00:17] ❌ NO-GO (score: 32) — 시장 포화                        │ │
│  │ [00:18] 🎬 영상 2/47 "This App Changed My Life" (890K views)    │ │
│  │ [00:24] 💡 "AI 반려동물 건강 추적" → 📚 수의학 AI 94% 정확도   │ │
│  │ [00:31] ✅ GO #1 (score: 87) → 칸반 GO 대기로 이동 ↑           │ │
│  │ ▼ 자동 스크롤                                                    │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  분석: 12/47 영상 | GO 대기: 3 | 빌드 중: 1 | 배포됨: 1 | $0.06   │
└──────────────────────────────────────────────────────────────────────┘
```

**인터랙션 플로우:**
1. 사용자가 **"Start" 버튼** 클릭 → 스트리밍 시작
2. 좌측 액션 피드에서 **에이전트 행동 실시간 관찰** (GO/NO-GO 모두 표시)
3. GO가 나오면 우측 **칸반 보드의 "GO 대기" 컬럼에 카드 자동 추가**
4. 사용자가 카드를 **빌드 액션으로 드래그** 또는 **"GO!" 버튼 클릭** → `queue_build` 액션 호출
5. 빌드된 카드는 **"빌드 중" → "배포됨" 컬럼**으로 자동 이동
6. 마음에 안 드는 카드는 **NO-GO 액션으로 드래그** 또는 삭제/패스 → 슬롯 비움 → 탐색 재개
7. **GO 대기 컬럼이 항상 10개를 유지**하도록 탐색이 자동 조절됨

**칸반 컬럼 구조:**

```
┌────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ 🔍 탐색 중  │ ✅ GO 대기    │ 🔨 빌드 중    │ 🚀 배포됨     │ ❌ NO-GO     │
│ (현재 분석)  │ (max 10)     │              │              │ (탈락 사유)   │
├────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│            │┌────────────┐│┌────────────┐│┌────────────┐│┌────────────┐│
│ 🎬 영상 7  ││ GO #1      │││ GO #3      │││ GO #2      │││ AI워크플로  ││
│ 📝 추출 중  ││ 반려동물    │││ 세금자동화  │││ 번역회의록  │││ score:32   ││
│ 🧠 분석 중  ││ score:87   │││ 빌드 23%   │││ ✅ live!   │││ 시장 포화   ││
│            ││ [🚀GO!]    │││ ████░░░░   │││ [URL 열기]  ││└────────────┘│
│            ││ [패스]      ││└────────────┘│└────────────┘│┌────────────┐│
│            │└────────────┘│              │              ││ SNS분석    ││
│            │┌────────────┐│              │              ││ score:41   ││
│            ││ GO #4      ││              │              ││ 기술 난이도 ││
│            ││ AI노트      ││              │              │└────────────┘│
│            ││ score:76   ││              │              │ ...          │
│            ││ [🚀GO!]    ││              │              │              │
│            ││ [패스]      ││              │              │              │
│            │└────────────┘│              │              │              │
│            │ ...          │              │              │              │
└────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

**칸반 5컬럼:**
| 컬럼 | 설명 | 카드 행동 |
|------|------|----------|
| 🔍 탐색 중 | 현재 분석 중인 영상 (1장) | 분석 완료 → GO 대기 또는 NO-GO로 자동 이동 |
| ✅ GO 대기 | GO 판정 아이디어 (max 10) | "🚀GO!" → 빌드 큐 등록, "패스" → NO-GO |
| 🔨 빌드 중 | 빌드 파이프라인 진행 중 | 자동: 기존 `/run` 단계 진행률 표시 (`skip_council=true` 기본) |
| 🚀 배포됨 | 라이브 URL 확보 완료 | URL 열기, 결과 확인 |
| ❌ NO-GO | 탈락 아이디어 + 사유 | 접을 수 있음, 참고용 기록 |

**큐 관리 시스템:**

빌드는 비용이 높으므로 **1개씩만 진행**. 나머지는 큐로 대기.

```
┌─────────────────────────────────────────────────────┐
│                    큐 관리자                          │
│                                                      │
│  [탐색 큐]  GO 대기 < 10? ──→ 탐색 워커 (1개 실행)  │
│              ↓ GO 판정                               │
│  [GO 대기]  max 10장, FIFO                           │
│              ↓ 사용자 "GO!" 클릭                     │
│  [빌드 큐]  FIFO 대기열, 동시 실행: 1개만            │
│              ↓ 빌드 완료                             │
│  [배포됨]   완료 기록                                │
│                                                      │
│  [NO-GO]    탈락 기록 (탐색 or 사용자 패스)          │
└─────────────────────────────────────────────────────┘
```

| 큐 | 동시 실행 | 트리거 | 비고 |
|----|---------|--------|------|
| **탐색 큐** | 1 (영상 1개씩 순차) | `GO 대기` < 10 | GO 10개 차면 일시정지 |
| **GO 대기** | — (저장소, 큐 아님) | 탐색 GO 판정 | max 10, 사용자 행동 대기 |
| **빌드 큐** | **1** (동시 빌드 1개) | 사용자 "GO!" | FIFO — 여러 개 GO! 누르면 순서대로 |
| **NO-GO** | — (저장소) | 탐색 NO-GO 또는 사용자 "패스" | 접기/펼치기, 기록용 |

**빌드 큐 동작:**
- 사용자가 GO #1, GO #3, GO #5 순서로 "GO!" 클릭
- → 빌드 큐: `[GO #1, GO #3, GO #5]`
- GO #1 빌드 시작 (빌드 중 컬럼)
- GO #3, GO #5는 **"빌드 대기"** 상태로 GO 대기 컬럼에 잔류 (뱃지: "⏳ 빌드 대기 #2")
- GO #1 빌드 완료 → 배포됨 컬럼 → GO #3 빌드 자동 시작
- GO 대기 슬롯이 비었으므로 → 탐색 재개

**칸반 카드 상태:**
```
카드 상태 (card.status):
  "analyzing"     → 🔍 탐색 중 컬럼
  "go_ready"      → ✅ GO 대기 컬럼 (사용자 행동 대기)
  "build_queued"  → ✅ GO 대기 컬럼 (뱃지: ⏳ 빌드 대기 #N)
  "building"      → 🔨 빌드 중 컬럼 (진행률 표시)
  "deployed"      → 🚀 배포됨 컬럼
  "nogo"          → ❌ NO-GO 컬럼
  "passed"        → ❌ NO-GO 컬럼 (사용자 패스)
```

**모바일 레이아웃:**
- 상단: 액션 피드 (접을 수 있음)
- 하단: 칸반 보드 (가로 스크롤)
- GO 발생 시 **진동 + 뱃지 카운터**

### 3.6 프론트엔드 컴포넌트 구조

```
web/src/
├── app/zero-prompt/
│   └── page.tsx                     # 칸반(상단) + 액션 피드(하단) 레이아웃
├── components/zero-prompt/
│   ├── kanban-board.tsx             # 5컬럼 칸반 보드 (드래그 지원)
│   ├── kanban-column.tsx            # 개별 칸반 컬럼
│   ├── idea-card.tsx                # 칸반 카드 (상태별 UI 분기)
│   ├── action-feed.tsx              # 하단: Manus 스타일 액션 피드 (300줄)
│   ├── action-entry.tsx             # 개별 액션 로그 엔트리 (아이콘+색상)
│   ├── status-bar.tsx               # 최하단: 진행 통계 + 비용
│   └── start-button.tsx             # Start 버튼 (초기 히어로)
└── hooks/
    ├── use-zero-prompt.ts           # SSE 소비 + 칸반 상태 관리
    └── use-build-queue.ts           # 빌드 큐 관리 (FIFO, 동시 1개)
```

---

## 4. 논문 검색 브레인스톰

### 4.1 왜 논문?

YouTube 인사이트만으로는:
- "반려동물 건강 앱" → 이미 있는 아이디어의 반복
- 차별화 근거 부족, 기술적 깊이 없음

논문을 추가하면:
- "AI 수의학 진단 정확도 94%" → **과학적 근거 확보**
- "IoT 웨어러블 센서 기반 활동량 분석" → **기술적 차별화 아이디어**
- "한국 반려동물 시장 2025 분석" → **시장 데이터**

### 4.2 API 스택 (전부 무료)

| API | 용도 | 비용 | 커버리지 |
|-----|------|------|---------|
| **OpenAlex** (Primary) | 종합 논문 검색 | 무료 ($1/day 크레딧) | 250M+ 논문 |
| **arXiv** (Secondary) | CS/AI 논문 | 무료 | 2.5M+ 프리프린트 |

### 4.3 검색 → 브레인스톰 플로우

```python
async def paper_brainstorm(idea: AppIdea) -> EnhancedIdea:
    # 1. 아이디어에서 검색 쿼리 생성 (gemini-3.1-flash-lite-preview)
    queries = await generate_paper_queries(idea)
    # → ["pet health IoT wearable", "veterinary AI diagnosis", "companion animal monitoring"]

    # 2. 논문 검색 (OpenAlex + arXiv 병렬)
    papers = await asyncio.gather(
        search_openalex(queries[0], limit=3),
        search_arxiv(queries[1], limit=2),
    )
    # → 5편의 논문 (title, abstract, citations, year)

    # 3. 브레인스톰 (gemini-3.1-flash-lite-preview)
    enhanced = await brainstorm_with_papers(idea, papers)
    # → {
    #     "enhanced_features": ["AI 사진 기반 피부질환 사전 탐지"],
    #     "scientific_backing": "수의학 AI 진단 정확도 94% (2025, 203 citations)",
    #     "unexplored_angles": ["한국 수의사 원격 상담 연동"],
    #     "novelty_boost": 0.15  # 아이디어 참신도 가산점
    #   }

    return EnhancedIdea(
        **idea.dict(),
        paper_insights=enhanced,
        total_score=idea.confidence_score + enhanced["novelty_boost"]
    )
```

### 4.4 비용: 무료

OpenAlex 검색: 1,000회/일 무료 → 아이디어 300개 분석 가능
arXiv: 1 req/3초 → 50개 아이디어에 5분

---

## 5. GO / NO-GO 판정 기준

### 5.1 판정 로직 (점수 계산은 코드, 설명은 `gemini-3.1-flash-lite-preview`)

```python
GO_CRITERIA = {
    "confidence_score": 0.7,        # Gemini 추출 신뢰도 >= 0.7
    "engagement_rate": 0.02,        # 원본 영상 인게이지먼트 >= 2%
    "market_opportunity": 50,       # 경쟁 분석 기회 점수 >= 50/100
    "has_paper_backing": True,      # 논문 기반 강화 성공
    "competitor_count_max": 5,      # 직접 경쟁사 5개 이하
    "market_saturation_max": "medium", # 시장 포화도 medium 이하
}
```

### 5.2 종합 점수 (0~100)

```
market_opportunity_normalized = market_opportunity / 100
differentiation_normalized = differentiation_score / 100
novelty_boost_normalized = min(paper_novelty_boost / 0.30, 1.0)

score = (
    confidence_score × 25 +       # Gemini 추출 품질
    engagement_normalized × 20 +   # 원본 영상 인기도
    market_opportunity_normalized × 25 +  # 경쟁사 분석 기회
    novelty_boost_normalized × 15 +       # 논문 기반 참신도
    differentiation_normalized × 15       # 차별화 가능성
)

GO:    score >= 65
NO-GO: score < 65
```

---

## 6. 모델 배정

**탐색, 수집, 분석의 모든 LLM 호출은 `gemini-3.1-flash-lite-preview`를 사용한다.**

단, `score` 계산 자체는 구현 코드에서 결정론적으로 수행하고, LLM은 쿼리 생성/요약/사유 설명에만 사용한다.

| 단계 | 모델 | 용도 |
|------|------|------|
| 아이디어 추출 | `gemini-3.1-flash-lite-preview` | 트랜스크립트 → AppIdea JSON |
| 논문 쿼리 생성 | `gemini-3.1-flash-lite-preview` | 아이디어 → 검색 키워드 |
| 브레인스톰 | `gemini-3.1-flash-lite-preview` | 아이디어 + 논문 → 강화된 아이디어 |
| 경쟁사 분석 | `gemini-3.1-flash-lite-preview` | 검색 결과 → 기회 점수 |
| GO/NO-GO 설명 생성 | `gemini-3.1-flash-lite-preview` | 종합 데이터 → reason / reason_code |

비용은 `gemini-3.1-flash-lite-preview` 공식 단가 기준으로 계산한다.

- 대략치: 아이디어 1개당 **$0.004~$0.01**
- 가정: step당 `2K~4K` 입력, `0.8K~1.5K` 출력, 총 5회 호출
- GO 10개 수집에 평균 30~50개 분석 시: **약 $0.12~$0.50**

### 6.1 공식 API 사용 정책

Zero-Prompt의 Gemini 호출은 모두 **공식 Google GenAI SDK의 `models.generate_content` 경로**를 사용한다.

- `gemini-3.1-flash-lite-preview`는 이 스펙의 기본 모델이다.
- Google 공식 Interactions API 문서는 beta이며, production workload는 계속 표준 `generateContent` API를 쓰라고 명시한다.
- Zero-Prompt는 짧은 step을 연속 호출하는 구조이므로 session-oriented beta API보다 step-local deterministic 호출이 더 적합하다.

정책:

- Phase 0 기본 경로: `generate_content`
- `response_mime_type="application/json"` + schema 기반 구조화 출력
- Interactions API: Phase 0 기본 범위에서 제외
- `gemini-3.1-pro-preview` 또는 `gemini-3.1-pro-preview-customtools`: 후속 고급 브레인스톰/멀티모달 보강 단계에서만 feature flag 아래 검토

### 6.2 공식 출처

- 가격: [Gemini Developer API 가격](https://ai.google.dev/gemini-api/docs/pricing?hl=ko)
- 모델: [gemini-3.1-flash-lite-preview](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-preview)
- 구조화 출력: [Structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- 함수 호출: [Function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- 캐싱: [Caching](https://ai.google.dev/gemini-api/docs/caching)
- Interactions API: [Interactions](https://ai.google.dev/gemini-api/docs/interactions)

---

## 7. 기존 인프라 재사용

| 컴포넌트 | 재사용 | 변경 |
|---------|--------|------|
| `agent/sse.py` — `format_sse()` | ✅ 그대로 | transport 재사용, 이벤트 레지스트리는 Zero-Prompt 전용 모듈에서 관리 |
| `web/src/hooks/use-pipeline-monitor.ts` | ✅ 패턴 참조 | `use-zero-prompt.ts` 신규 (동일 패턴) |
| `web/src/components/dashboard/live-monitor.tsx` | ✅ 패턴 참조 | Manus 스타일로 확장 |
| `agent/tools/youtube.py` — `extract_youtube_transcript()` | ✅ 그대로 | Zero-Prompt transcript adapter에서 재사용 |
| `agent/tools/web_search.py` — `search_competitors()` | ⚠️ 부분 | Zero-Prompt 전용 Brave adapter로 분리 |
| 기존 `/run` 빌드 파이프라인 | ✅ 그대로 | `GO!` handoff 시 `skip_council=true` 기본값 추가 |
| Vibe Council | ⚠️ 선택적 | Zero-Prompt 평가 단계에서는 사용하지 않음 |

### 7.1 권장 파일 구조

```text
agent/
├── zero_prompt/
│   ├── __init__.py
│   ├── schemas.py
│   ├── events.py
│   ├── discovery.py
│   ├── transcript.py
│   ├── insight.py
│   ├── paper_search.py
│   ├── paper_brainstorm.py
│   ├── competitive_analysis.py
│   ├── verdict.py
│   ├── queue_manager.py
│   └── orchestrator.py
├── tools/
│   └── youtube.py              # 기존 재사용
└── server.py                   # start/action/status/events endpoint 연결

web/src/
├── app/zero-prompt/page.tsx
├── components/zero-prompt/
├── hooks/use-zero-prompt.ts
├── hooks/use-build-queue.ts
├── lib/zero-prompt-api.ts
└── types/zero-prompt.ts
```

### 7.2 빌드 핸드오프 계약

- `GO!` 클릭 시 카드는 즉시 `build_queued` 또는 `building` 상태로 전환된다.
- 빌드 워커가 비어 있으면 즉시 기존 `/api/run` 파이프라인을 호출한다.
- handoff payload는 카드에서 생성한 정제된 prompt를 사용한다.
- 기본 파라미터:

```json
{
  "prompt": "AI 반려동물 건강 추적 앱 ...",
  "thread_id": "zpbuild_20260317_001",
  "constraints": "",
  "selected_flagship": "",
  "skip_council": true
}
```

- 추후 `with_council=true` 옵션이 생기더라도 Zero-Prompt Phase 0의 기본값은 유지한다.

### 7.3 API Surface

Zero-Prompt는 기존 bare route + `/api/*` 이중 노출 규칙을 따른다.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/api/zero-prompt/start` / `/zero-prompt/start` | 세션 시작 및 SSE 스트림 연결 |
| `POST` | `/api/zero-prompt/{session_id}/actions` / `/zero-prompt/{session_id}/actions` | `queue_build`, `pass_card`, `delete_card`, `pause`, `resume` |
| `GET` | `/api/zero-prompt/{session_id}` / `/zero-prompt/{session_id}` | 현재 세션 스냅샷 |
| `GET` | `/api/zero-prompt/{session_id}/events` / `/zero-prompt/{session_id}/events` | 세션 전용 SSE 이벤트 |
| `GET` | `/api/zero-prompt/active` / `/zero-prompt/active` | 활성 세션 목록 (ops/debug 용도) |

---

## 8. 태스크 분해 (업데이트)

| 태스크 | 제목 | 예상 시간 | 의존성 |
|--------|------|---------|--------|
| 161 | YouTube Discovery Engine | 8h | 없음 |
| 162 | 스트리밍 트랜스크립트 추출 | 6h | 161 |
| 163 | Gemini Insight Extractor (`gemini-3.1-flash-lite-preview`) | 8h | 151, 162 |
| 164 | 📚 논문 검색 엔진 (OpenAlex + arXiv) | 6h | 없음 |
| 165 | 🧠 논문 기반 브레인스톰 | 4h | 163, 164 |
| 166 | 경쟁사 분석 엔진 (Brave + Exa 병렬) | 8h | 없음 |
| 167 | GO/NO-GO 판정 엔진 | 4h | 163, 165, 166 |
| 168 | 스트리밍 루프 오케스트레이터 + API | 8h | 161~167 |
| 169 | Manus 스타일 액션 피드 UI | 10h | 168 |

### 의존성 그래프

```
[독립] 161, 164, 166

161 → 162 → 163 ─┐
                   ├→ 165 → 167 → 168 → 169
164 ──────────────┘       ↑
166 ──────────────────────┘
```

---

## 9. 비용 총정리

| 항목 | 비용 |
|------|------|
| YouTube Data API | 무료 (쿼터 내) |
| 트랜스크립트 추출 | 무료 (youtube-transcript-api) |
| Gemini Flash Lite (30~50개 영상 분석) | $0.15~$0.25 |
| 논문 검색 (OpenAlex + arXiv) | 무료 |
| 경쟁사 검색 (Brave + Exa 병렬) | 무료 (Brave 2,000건/월 + Exa 토큰 자동발급) |
| **GO 10개 수집 총비용** | **~$0.20** |

---

## 10. 리스크와 완화

| 리스크 | 완화 |
|--------|------|
| GO 10개 모이기 전 후보 소진 | 검색 쿼리를 다음 카테고리로 확장 (최대 5라운드) |
| 모든 아이디어가 NO-GO | 기준 임계값 동적 하향 (65→55→45) + 사용자 알림 |
| 논문 API 레이트리밋 | OpenAlex 1차, arXiv 폴백, 캐시 적용 |
| YouTube IP 차단 | yt-dlp 메타데이터 폴백 (기존 로직) |
| Gemini API 다운 | DO Inference의 다른 모델로 폴백 |
