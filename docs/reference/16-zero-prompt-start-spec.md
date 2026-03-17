# vibeDeploy Zero-Prompt Start 스펙 (v2)

작성일: 2026-03-17 | 최종 수정: 2026-03-17
상태: 제안 (구현 전)

---

## 1. 개요

사용자가 **"Start" 버튼 하나만 누르면** 시스템이 자동으로:
1. YouTube에서 트렌딩/고인게이지먼트 영상을 **스트리밍으로** 탐색하고
2. `gemini-3.1-flash-lite-preview`로 아이디어를 추출하고
3. **논문 검색**(OpenAlex + arXiv)으로 아이디어를 브레인스톰/강화하고
4. 경쟁사를 자동 분석(Brave Search)하고
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
- 사용자가 **"GO!" 버튼**을 누르면 해당 아이디어만 빌드 파이프라인 시작. 해당 카드는 패널에서 "빌드 중" 상태로 전환되고, **빈 슬롯이 생기므로 탐색 재개**.
- **항상 사용자에게 10개의 GO 선택지가 제공되는 상태를 유지**하는 것이 목표.

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
         │  🏢 경쟁사 검색       │  Brave Search API
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
         ├─ "GO!" 클릭 → 빌드 시작 + 슬롯 비움 → 탐색 재개
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
[02:21] 🔨 빌드 파이프라인 시작: Council → Build → Deploy
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
    "zp.complete":           {"icon": "🎉", "color": "green"},
}
```

### 3.4 화면 레이아웃

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
4. 사용자가 카드를 **"🚀 빌드" 컬럼으로 드래그** 또는 **"GO!" 버튼 클릭** → 빌드 시작
5. 빌드된 카드는 **"빌드 중" → "배포됨" 컬럼**으로 자동 이동
6. 마음에 안 드는 카드는 **"패스" 컬럼으로 드래그** 또는 삭제 → 슬롯 비움 → 탐색 재개
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
| ✅ GO 대기 | GO 판정 아이디어 (max 10) | "🚀GO!" → 빌드 중, "패스" → NO-GO |
| 🔨 빌드 중 | 빌드 파이프라인 진행 중 | 자동: Council → Code → Deploy 진행률 표시 |
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

### 3.5 프론트엔드 컴포넌트 구조

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

### 5.1 판정 로직 (gemini-3.1-flash-lite-preview)

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
score = (
    confidence_score × 25 +       # Gemini 추출 품질
    engagement_normalized × 20 +   # 원본 영상 인기도
    market_opportunity × 25 +      # 경쟁사 분석 기회
    paper_novelty_boost × 15 +     # 논문 기반 참신도
    differentiation_score × 15     # 차별화 가능성
)

GO:    score >= 65
NO-GO: score < 65
```

---

## 6. 모델 배정

**탐색, 수집, 분석의 모든 LLM 호출은 `gemini-3.1-flash-lite-preview`를 사용한다.**

| 단계 | 모델 | 용도 |
|------|------|------|
| 아이디어 추출 | `gemini-3.1-flash-lite-preview` | 트랜스크립트 → AppIdea JSON |
| 논문 쿼리 생성 | `gemini-3.1-flash-lite-preview` | 아이디어 → 검색 키워드 |
| 브레인스톰 | `gemini-3.1-flash-lite-preview` | 아이디어 + 논문 → 강화된 아이디어 |
| 경쟁사 분석 | `gemini-3.1-flash-lite-preview` | 검색 결과 → 기회 점수 |
| GO/NO-GO 판정 | `gemini-3.1-flash-lite-preview` | 종합 데이터 → 판정 |

비용: 아이디어 1개당 ~5회 LLM 호출 × $0.001 = **$0.005/아이디어**
GO 10개 수집에 평균 30~50개 분석 시: **$0.15~$0.25 총비용**

---

## 7. 기존 인프라 재사용

| 컴포넌트 | 재사용 | 변경 |
|---------|--------|------|
| `agent/sse.py` — `format_sse()` | ✅ 그대로 | 이벤트 타입 추가만 |
| `web/src/hooks/use-pipeline-monitor.ts` | ✅ 패턴 참조 | `use-zero-prompt.ts` 신규 (동일 패턴) |
| `web/src/components/dashboard/live-monitor.tsx` | ✅ 패턴 참조 | Manus 스타일로 확장 |
| `agent/tools/youtube.py` — `extract_youtube_transcript()` | ✅ 그대로 | 배치 래퍼만 추가 |
| `agent/tools/web_search.py` — `search_competitors()` | ⚠️ 부분 | Brave Search API로 교체 |
| Vibe Council | ❌ 불필요 | Zero-Prompt는 자체 GO/NO-GO |

---

## 8. 태스크 분해 (업데이트)

| 태스크 | 제목 | 예상 시간 | 의존성 |
|--------|------|---------|--------|
| 161 | YouTube Discovery Engine | 8h | 없음 |
| 162 | 스트리밍 트랜스크립트 추출 | 6h | 161 |
| 163 | Gemini Insight Extractor (`gemini-3.1-flash-lite-preview`) | 8h | 151, 162 |
| 164 | 📚 논문 검색 엔진 (OpenAlex + arXiv) | 6h | 없음 |
| 165 | 🧠 논문 기반 브레인스톰 | 4h | 163, 164 |
| 166 | 경쟁사 분석 엔진 (Brave Search) | 8h | 없음 |
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
| 경쟁사 검색 (Brave Search) | 무료 (월 $5 크레딧) |
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
