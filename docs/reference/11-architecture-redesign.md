# vibeDeploy 아키텍처 전면 재설계 보고서

작성일: 2026-03-17
상태: 제안 (구현 전)

---

## 1. 목적

vibeDeploy의 핵심 약속은 **"텍스트 한 줄 → 실제 작동하는 풀스택 앱이 라이브 URL로 배포"**이다.

현재 아키텍처는 이 약속을 안정적으로 이행하지 못한다.
이 문서는 매번 프로덕션 수준의 MVP를 완성할 수 있는 플랫폼으로 전환하기 위한 전면 재설계 방향을 정의한다.

---

## 2. 현재 아키텍처 진단

### 2.1 파이프라인 전체 흐름 (15개 노드)

```
[입력] raw_input
  │
  ├─ ① input_processor      텍스트/YouTube 파싱, 아이디어 구조화
  ├─ ② inspiration_agent    도메인별 UI/UX 패턴 매핑
  ├─ ③ experience_agent     경험 계약서(UX spec) 생성
  ├─ ④ enrich_idea          기술/시장 상세 보강
  │
  ├─ ⑤ fan_out_analysis     5개 Council 에이전트 병렬 분석 (LLM ×5)
  ├─ ⑥ cross_examination    구조화된 토론 (LLM ×1)
  ├─ ⑦ fan_out_scoring      5축 점수 산출 (LLM ×5)
  ├─ ⑧ strategist_verdict   Vibe Score → GO/CONDITIONAL/NO-GO
  ├─ ⑨ decision_gate        라우팅 (빌드 or 수정 or 축소)
  │
  ├─ ⑩ doc_generator        PRD, 기술스펙, API스펙, DB스키마, app_spec (LLM ×5)
  ├─ ⑪ blueprint_generator  파일 매니페스트
  ├─ ⑫ prompt_strategist    모델별 프롬프트 최적화
  ├─ ⑬ code_generator       프론트엔드+백엔드 코드 생성 (LLM ×2)
  ├─ ⑭ code_evaluator       휴리스틱 검증 (regex 기반, 최대 5회 루프)
  │
  └─ ⑮ deployer             GitHub → CI → DO App Platform → 라이브 URL
```

- 총 LLM 호출 수: 런당 15~25회
- 예상 파이프라인 소요시간: 3~8분
- 예상 비용: $0.50~$1.00/회

### 2.2 치명적 결함

#### 결함 1: 컴파일/빌드 검증 부재 (심각도: 치명적)

`code_evaluator`는 regex 기반 휴리스틱만 사용한다:
- "package.json에 `next`가 포함되어 있는가?" → 있으면 점수 +1
- "main.py에 `FastAPI`가 포함되어 있는가?" → 있으면 점수 +1
- "`use client` 디렉티브가 있는가?" → 있으면 점수 +0.5

실제 TypeScript 컴파일 에러, Python import 실패, 런타임 버그는 **전혀 감지하지 못한다**.

비교:
- bolt.new: WebContainer에서 즉시 컴파일
- v0: AST 파서 + 결정론적 오토픽서
- Replit Agent: Playwright로 자체 테스트
- **vibeDeploy: regex 검사 후 배포**

#### 결함 2: 단일 샷 코드 생성 (심각도: 치명적)

한 번의 LLM 호출로 프론트엔드 전체 (약 20개 파일)를 하나의 JSON blob으로 생성한다.

문제점:
- JSON 파싱 실패 시 전체 유실
- 하나의 파일 오류로 전체 재생성 필요
- LLM이 20개 파일을 한 번에 완벽하게 생성하기 극도로 어려움

비교:
- Lovable: 파일별 diff 생성
- v0: 컴포넌트 단위 생성

#### 결함 3: 타입 안전성 부재 (심각도: 높음)

프론트엔드(TypeScript)와 백엔드(Python) 사이에 공유 스키마가 없다.

현재 계약 구조:
```python
"frontend_backend_contract": [
    {
        "frontend_file": "src/lib/api.ts",
        "calls": "POST /api/plan",
        "backend_file": "routes.py",
        "request_fields": ["query", "preferences"],   # 타입 정보 없음
        "response_fields": ["summary", "items"]        # 타입 정보 없음
    }
]
```

검증은 필드 **이름** 일치만 확인 — 타입, 중첩 구조, Optional 여부, 열거형 값은 검증 불가.

타입 안전성 수준: 약 5%.

#### 결함 4: 디자인 시스템 실행 갭 (심각도: 높음)

프롬프트가 명시하는 것:
- "generic dashboard 금지"
- "next/font 사용"
- "1~2개 모션 추가"
- "OKLCH 색상"

폴백 코드가 실제로 생성하는 것:
- 시스템 폰트 (`Georgia, Times New Roman, serif`)
- 하드코딩 7개 CSS 변수 (OKLCH 아님)
- 애니메이션 0개
- 단일 반응형 중단점 (1080px)

LLM이 프롬프트를 무시하거나, 폴백이 발동되면 디자인 의도가 완전히 상실된다.

#### 결함 5: Council이 배포 성공률에 기여하지 않음 (심각도: 중간)

8~10회 LLM 호출로 "평가 시어터"를 수행하지만, 점수가 코드 품질에 구조적으로 영향을 주지 않는다.
Council 결과는 코드 생성 프롬프트에 `blueprint` 컨텍스트로 전달되지만, LLM이 이를 무시하는 것을 방지하는 메커니즘이 없다.

### 2.3 잘 작동하는 영역

| 강점 | 상세 |
|------|------|
| Vibe Council UX | 6명의 AI 에이전트 토론은 해커톤/데모에서 독보적 차별점. 어떤 경쟁사에도 없는 UX |
| SSE 이벤트 스트리밍 | 실시간 파이프라인 진행 상황을 프론트엔드에 전달. 대시보드가 활성 파이프라인을 추적 |
| 멀티모델 LLM 라우팅 | Anthropic, OpenAI, DO Inference, Qwen, DeepSeek — 역할별 구성 + 레이트리밋 시 자동 폴백 |
| CI 복구 루프 | TypeScript nullability, SQLAlchemy import, "use client" 등 결정론적 자동 수정 |
| Blueprint 계약 기반 생성 | 프론트/백엔드 API 계약서를 기반으로 코드를 생성하는 개념은 건전함 |
| 프롬프트 품질 | 정확한 버전 지정, 안티패턴 명시, 도메인별 요구사항 상세 |
| 대시보드 프론트엔드 | Next.js 16 + React 19 + Tailwind 4 + Framer Motion. SSE 소비, 파이프라인 시각화 |

---

## 3. 경쟁사 아키텍처 분석

### 3.1 플랫폼별 핵심 패턴

| 플랫폼 | 핵심 아키텍처 | 코드 검증 방식 | 에러 복구 | 백엔드 전략 |
|--------|-------------|--------------|----------|-----------|
| bolt.new | WebContainer (브라우저 내 Node.js) | 클라이언트 즉시 컴파일 + 라이브 프리뷰 | 사용자가 에러 → AI 수정 | Supabase 연동 |
| Lovable | Patch 기반 diff 생성 | `salvage_correct_hunks()` — 유효한 diff만 적용 | 최대 3회 반복 정제 | Supabase 주 백엔드 |
| v0 | LLM Suspense (스트림 변환) + AST 오토픽서 | 3층: 동적 프롬프트 → 스트림 교정 → AST 수정 | 원시 에러율 ~10% → 파이프라인 후 ~0% | Vercel Functions |
| Replit Agent | REPL 기반 자체 테스트 + Playwright | 에이전트가 직접 테스트 작성/실행 | 테스트 서브에이전트가 검증 → 피드백 | 내장 Replit DB |

### 3.2 공통 패턴: 모든 성공한 플랫폼은 배포 전 코드를 검증한다

```
경쟁사:     생성 → 컴파일 → 수정 → 컴파일 → 배포
vibeDeploy: 생성 → (regex) → 배포 → 기도
```

### 3.3 백엔드 생성 전략 비교

성공한 플랫폼들은 백엔드를 **생성하지 않고 통합한다** (Supabase, Replit DB 등).
vibeDeploy만 유일하게 FastAPI 전체를 LLM으로 생성하며, 이것이 실패율을 크게 높인다.

---

## 4. 제안 아키텍처: "Contract-First, Validate-Always"

### 4.1 핵심 패러다임 전환

```
현재:  "LLM이 모든 것을 생성하고, 우리는 결과를 검사한다"
제안:  "우리가 구조를 정의하고, LLM은 비즈니스 로직만 채운다. 그리고 실제로 빌드해본다."
```

### 4.2 새로운 파이프라인 구조

```
[Phase 1] 아이디어 정제 — 변경 없음
  input_processor → inspiration_agent → experience_agent → enrich
      │
      ▼
[Phase 2] Vibe Council — 데모 모드로 전환
  5개 에이전트 분석 → 토론 → 채점 → 판정
  ✅ SSE 스트리밍 유지 (UX 차별점)
  🔧 빌드 크리티컬 패스에서 분리
  🔧 "바로 빌드" 옵션 추가
      │
      ▼
[Phase 3] API 계약서 생성 (신규)
  LLM → OpenAPI 3.1 스펙 (구조화 출력)
  → openapi-typescript → TypeScript 타입 자동 생성
  → datamodel-code-generator → Pydantic 모델 자동 생성
  결과: FE/BE가 동일한 스키마에서 파생 → 100% 타입 정합성
      │
      ▼
[Phase 4] 레이어드 코드 생성
  Layer 1: 결정론적 스캐폴드 (LLM 불필요)
    package.json, tsconfig, next.config, requirements.txt, main.py 뼈대
  Layer 2: 생성된 타입 (OpenAPI에서 자동)
    src/types/api.d.ts, schemas.py, src/lib/api-client.ts
  Layer 3: 디자인 시스템 (blueprint에서 구성)
    globals.css (OKLCH 토큰), layout.tsx (next/font), motion-tokens.ts
  Layer 4: LLM 비즈니스 로직 (파일별 개별 호출)
    page.tsx, components/*.tsx, routes.py, ai_service.py
      │
      ▼
[Phase 5] 다층 빌드 검증 (신규)
  Tier 1: 구문 검증 (< 1초) — ast.parse, TS AST
  Tier 2: 임포트 검증 (< 3초) — importlib, package.json 교차
  Tier 3: 실제 빌드 (30~60초) — npm run build, pip install + import
  Tier 4: 계약 검증 (< 5초) — OpenAPI vs 생성 코드 교차
  실패 시 → 정확한 stderr를 LLM에 피드백 → 최대 3회 반복
      │
      ▼
[Phase 6] 배포 — 기존 deployer 유지 + 강화
  GitHub → CI → DO App Platform → 헬스체크
```

### 4.3 레이어드 코드 생성 상세

| 레이어 | 생성 방식 | 실패 확률 | 내용 |
|--------|----------|----------|------|
| L1: 스캐폴드 | 결정론적 템플릿 | ~0% | package.json, tsconfig, next.config, requirements.txt, main.py 뼈대 |
| L2: 타입 | OpenAPI에서 자동 | ~0% | TypeScript 인터페이스, Pydantic 모델 |
| L3: 디자인 | blueprint에서 구성 | ~5% | OKLCH 색상 토큰, 폰트 페어링, 모션 토큰 |
| L4: 비즈니스 | LLM (파일별) | ~15-25% | 컴포넌트, 라우트 핸들러, AI 서비스 |

성공률 비교:
- 현재: LLM 1회 → 20개 파일 JSON blob → 실패율 ~40%
- 제안: 결정론적 8개 + LLM 5~7회 (각 1~2개 파일) → 실패율 ~15%

### 4.4 결정론적으로 주입할 파일 목록

프론트엔드 (LLM이 생성하면 안 되는 파일):
- `web/package.json` — blueprint 의존성 + 고정 버전으로 구성
- `web/tsconfig.json` — 항상 동일
- `web/next.config.ts` — standalone output + API rewrite
- `web/postcss.config.js` — 항상 동일
- `web/tailwind.config.ts` — blueprint 테마 토큰으로 구성
- `web/src/app/layout.tsx` — 루트 레이아웃 (메타데이터 + next/font)
- `web/src/app/globals.css` — Tailwind imports + OKLCH CSS 변수
- `web/src/lib/motion-tokens.ts` — Framer Motion 사전 설정

백엔드 (템플릿 기반):
- `requirements.txt` — 고정된 의존성 목록
- `main.py` — FastAPI 앱 엔트리포인트 (라우터 임포트 + CORS + health)
- `models.py` — SQLAlchemy 보일러플레이트 (DB 설정, Base 선언)
- `schemas.py` — OpenAPI에서 자동 생성된 Pydantic 모델

LLM이 생성해야 하는 파일 (비즈니스 로직):
- `web/src/app/page.tsx` — 메인 페이지
- `web/src/components/*.tsx` — 도메인별 컴포넌트 (3~5개)
- `web/src/lib/api.ts` — 타입 안전 API 클라이언트
- `routes.py` — API 엔드포인트 핸들러
- `ai_service.py` — DO Inference 연동

---

## 5. 핵심 설계 결정과 근거

### 5.1 왜 OpenAPI를 단일 소스로?

| 대안 | 장점 | 단점 | 판단 |
|------|------|------|------|
| tRPC | 100% 타입 추론 | TypeScript 전용, Python 불가 | 부적합 |
| GraphQL | 강력한 스키마 | LLM이 생성하기 복잡, 추가 인프라 | 부적합 |
| py2ts | Python 중심 | OpenAPI만큼 풍부한 메타데이터 없음 | 차선 |
| **OpenAPI 3.1** | FastAPI 네이티브, 양방향 코드 생성, 표준 | LLM 호출 1회 추가 | **채택** |

### 5.2 왜 파일별 생성?

정량적 근거:
- 현재: LLM 1회 → 20개 파일 → 실패율 ~40%
- 파일별: LLM 5~7회 → 각 1~2개 파일 → 파일당 실패율 ~15%, 독립적 재시도 가능
- 전체 성공률: ~60% → ~85%+

v0의 교훈: 원시 LLM 에러율 ~10%이지만, Suspense + Autofixer 파이프라인으로 거의 0%.

### 5.3 왜 Council을 유지하되 분리?

- 유지 이유: 6명의 AI 에이전트 토론은 vibeDeploy의 유일한 차별점
- 분리 이유: Council 판정이 코드 품질에 구조적으로 기여하지 않음
- 구현: SSE 이벤트 스트리밍 유지, 빌드는 Council과 병렬/독립 진행

### 5.4 왜 tmpdir + subprocess (Phase 1)?

| 방식 | 속도 | 격리 | 복잡도 | 적용 시점 |
|------|------|------|--------|---------|
| tmpdir + subprocess | 30~60초 | 낮음 | 낮음 | Phase 1 (즉시) |
| bubblewrap | 30~60초 | 중간 | 중간 | Phase 2 (Linux) |
| Docker SDK | 40~90초 | 높음 | 중간 | 스케일링 |
| E2B | 10~60초 | 매우 높음 | 낮음 | 프로덕션 |

Phase 1에서는 tmpdir + subprocess가 충분. 목적은 "대부분의 빌드 에러를 미리 잡는 것".

### 5.5 왜 디자인 시스템을 코드로 주입?

현재 문제: 프롬프트에 "OKLCH 사용", "모션 추가"라고 적어도 LLM이 무시.
해결: CSS 변수, next/font, 모션 토큰을 실제 파일로 생성. LLM은 이를 사용만 하면 됨.

---

## 6. 테스트 & 품질 인프라 현황과 제안

### 6.1 현재 상태

| 영역 | 현재 |
|------|------|
| Agent 테스트 | 27개 파일, pytest (LLM 호출은 모두 mock) |
| 프론트엔드 테스트 | 0개 (테스트 프레임워크 없음) |
| 코드 커버리지 | 추적 없음 |
| 타입 체크 | CI에 없음 |
| 보안 스캔 | 없음 |
| 배포 성공률 추적 | 상태 enum만 (pending/live/failed) |
| CI 게이트 | ruff lint → pytest → eslint → next build |

### 6.2 제안

| 영역 | 제안 |
|------|------|
| 프론트엔드 테스트 | Vitest + React Testing Library (API 클라이언트, SSE 훅) |
| 코드 커버리지 | pytest-cov + 80% 임계값 |
| 타입 체크 | mypy (Python) + tsc --noEmit (TypeScript) |
| 보안 스캔 | bandit (Python SAST) + npm audit |
| 배포 메트릭스 | 성공/실패/소요시간/비용/반복횟수/최종점수 |
| 계약 테스트 | OpenAPI 스펙 vs 생성 코드 교차 검증 |
| E2E 스모크 | 생성된 앱에 Playwright 기본 테스트 자동 생성 |

---

## 7. 구현 로드맵

### Phase 0: Zero-Prompt Start (2~3주)

프롬프트 없이 "Start" 버튼 하나로 앱 아이디어 탐색 → 빌드 → 배포.
상세 스펙: `16-zero-prompt-start-spec.md`, 태스크: `161~169`

| 작업 | 상세 | 예상 시간 |
|------|------|---------|
| YouTube Discovery Engine | YouTube Data API v3 트렌딩 영상 검색 | 8시간 |
| 스트리밍 트랜스크립트 | 영상별 순차 추출 (youtube-transcript-api) | 6시간 |
| Gemini Insight Extractor | gemini-3.1-flash-lite-preview로 아이디어 추출 | 8시간 |
| 논문 검색 엔진 | OpenAlex + arXiv 논문 검색 | 6시간 |
| 논문 브레인스톰 | 아이디어 + 논문 → 강화 | 4시간 |
| 경쟁사 분석 | Brave Search + LLM 분석 | 8시간 |
| GO/NO-GO 판정 | 종합 점수 → GO(≥65) / NO-GO | 4시간 |
| 스트리밍 오케스트레이터 | 루프 + 큐 관리 + API | 8시간 |
| 칸반 + 액션 피드 UI | 5컬럼 칸반 + 300줄 터미널 | 10시간 |

### Phase 1: 기반 구축 (1~2주)

| 작업 | 상세 | 예상 시간 |
|------|------|---------|
| build_validator 노드 | tmpdir + subprocess로 npm build + pip install | 8시간 |
| 결정론적 스캐폴드 분리 | package.json, tsconfig 등을 템플릿으로 | 4시간 |
| 빌드 에러 피드백 루프 | 실제 stderr → code_generator 프롬프트 | 4시간 |
| 백엔드 템플릿화 | FastAPI 뼈대를 템플릿으로, LLM은 핸들러만 | 6시간 |
| Council 데모 모드 | 빌드 패스에서 분리, "바로 빌드" 옵션 | 3시간 |

### Phase 2: 타입 안전성 (2~3주)

| 작업 | 상세 | 예상 시간 |
|------|------|---------|
| OpenAPI 스펙 생성 노드 | LLM이 구조화된 OpenAPI 3.1 스펙 생성 | 12시간 |
| openapi-typescript 통합 | 스펙 → TS 타입 자동 생성 | 4시간 |
| datamodel-code-generator 통합 | 스펙 → Pydantic 모델 자동 생성 | 4시간 |
| 타입 안전 API 클라이언트 | 생성된 TS 타입을 사용하는 fetch 래퍼 | 6시간 |
| 계약 검증 (Tier 4) | FastAPI /openapi.json vs TS 타입 교차 | 6시간 |

### Phase 3: 비주얼 품질 (2~3주)

| 작업 | 상세 | 예상 시간 |
|------|------|---------|
| OKLCH 색상 토큰 시스템 | 도메인별 12단계 스케일, 다크/라이트 | 8시간 |
| next/font 타이포그래피 | 도메인별 폰트 페어링 10쌍 | 6시간 |
| Framer Motion 토큰 | 사전 정의 variants + 도메인별 모션 | 6시간 |
| 레이아웃 아키타입 강화 | CSS Grid/Flexbox 실제 구현 | 8시간 |
| 시드 데이터 생성기 | 도메인별 현실적 목업 데이터 | 6시간 |

### Phase 4: 파일별 생성 (3~4주)

| 작업 | 상세 | 예상 시간 |
|------|------|---------|
| 파일별 코드 생성 아키텍처 | code_generator 리팩토링 | 20시간 |
| 파일별 AST 검증 | 생성 즉시 구문 + import 검증 | 8시간 |
| 파일별 재생성 로직 | 실패한 파일만 타겟팅 재생성 | 8시간 |
| 프롬프트 최적화 | 파일별 생성에 맞는 컨텍스트 주입 | 12시간 |

### Phase 5: 테스트 & 관측성 (2~3주)

| 작업 | 상세 | 예상 시간 |
|------|------|---------|
| 프론트엔드 테스트 인프라 | Vitest + RTL + 핵심 컴포넌트 | 12시간 |
| 배포 메트릭스 파이프라인 | 성공률/소요시간/비용/반복횟수 | 8시간 |
| CI 강화 | pytest-cov, mypy, tsc, bandit | 6시간 |
| E2E 스모크 테스트 | Playwright 기본 테스트 자동 생성 | 12시간 |

---

## 8. 예상 효과

| 메트릭 | 현재 추정 | Phase 1 후 | Phase 2 후 | Phase 4 후 |
|--------|----------|-----------|-----------|-----------|
| 배포 성공률 | ~40-50% | ~70-80% | ~85-90% | ~90-95% |
| FE/BE 타입 정합성 | ~5% | ~15% | ~95%+ | ~95%+ |
| 비주얼 품질 | 해커톤 데모 | 해커톤 데모 | 해커톤+ | 프로덕트 MVP |
| 파이프라인 소요시간 | 3~8분 | 4~10분 | 4~10분 | 5~12분 |
| LLM 호출당 비용 | $0.50~$1.00 | $0.40~$0.80 | $0.60~$1.20 | $0.80~$1.50 |

---

## 부록: 참고 자료

### 분석에 사용된 소스

내부:
- agent/nodes/ 전체 16개 노드 코드 분석
- agent/prompts/code_templates.py — 프론트/백엔드 시스템 프롬프트 전문
- agent/nodes/code_evaluator.py — 1,113줄 전체 분석
- agent/nodes/code_generator.py — 2,386줄 전체 분석
- agent/tests/ 27개 테스트 파일 감사
- .github/workflows/ci.yml — CI 파이프라인

외부:
- Vercel v0 블로그: "How we made v0 an effective coding agent" (Jan 2026)
- Replit 블로그: "Enabling Agent 3 to Self-Test at Scale" (Dec 2025)
- bolt.new GitHub 소스코드: action-runner.ts, stores
- GPT Engineer GitHub 소스코드: steps.py
- StackBlitz: WebContainer API 문서
- FastAPI 공식 문서: OpenAPI 스펙 생성
- openapi-typescript, hey-api/openapi-ts, datamodel-code-generator 문서
