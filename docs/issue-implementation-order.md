# vibeDeploy 이슈 전수 조사 및 구현 워크플랜

작성일: 2026-03-17
기준 문서: `docs/reference/11-architecture-redesign.md`, `docs/reference/19-architecture-decisions.md`

---

## 1. 전체 현황 요약

| 구분 | 총 | CLOSED | OPEN |
|------|-----|--------|------|
| M1-M5 (초기 해커톤) | 22 | 22 | 0 |
| Phase 0 — Zero-Prompt | 9 | 0 | 9 |
| Phase 1 — 기반 구축 | 5 | 0 | 5 |
| Phase 2 — 타입 안전성 | 5 | 0 | 5 |
| Phase 3 — 비주얼 품질 | 5 | 0 | 5 |
| Phase 4 — 파일별 생성 | 4 | 0 | 4 |
| Phase 5 — 테스트/관측성 | 3+4 | 4 | 3 |
| Pivot (P0-P4) | 5 | 1 | 4 |
| Gradient (G1-G10) | 10 | 3 | 7 |
| **합계** | **68** | **30** | **38** |

---

## 2. 문서 충돌 해소 (구현 전 반드시 확인)

### Docker vs Subprocess — 결론: Docker SDK

| 문서 | 주장 | 권위 |
|------|------|------|
| `11-architecture-redesign.md` §5.4 | Phase 1은 tmpdir+subprocess | 제안 문서 |
| `19-architecture-decisions.md` ADR-A4 | Docker SDK 확정 | **최종 권위** ("이 문서가 기준") |

**결론**: ADR-A4에 따라 `build_validator`(#34)는 Docker SDK(`docker.from_env()`)로 구현한다.
`docs/reference/12-implementation-specs.md`와 `111-build-validator.md`의 subprocess 코드는 무시한다.

### State 필드 불일치 — 결론: 실제 코드 기준

| 스펙 문서의 가정 | 실제 코드 (`state.py`) |
|-----------------|----------------------|
| `state["generated_files"]` → `List[{path, content}]` | `state["frontend_code"]` → `Dict[str, str]` |
| | `state["backend_code"]` → `Dict[str, str]` |

**결론**: `build_validator`는 `frontend_code`/`backend_code` dict를 받아 파일로 변환한다.
스펙 문서의 `generated_files` 참조 코드를 그대로 복사하면 안 된다.

### 누락 문서

- `18-final-pivot-refactor-plan.md` — `11-architecture-redesign.md`에서 참조하지만 미존재
- Pivot #74 (Master Tracker)가 대체하는 것으로 간주

---

## 3. 즉시 착수 가능한 이슈 (NOW)

의존성이 모두 충족된 이슈만 표시. 병렬 착수 가능.

### Phase 1 (의존성 없음 — 즉시 착수)

| # | Task | 내용 | 시간 | 변경 파일 | 스펙 문서 |
|---|------|------|------|----------|----------|
| **#34** | 111 | build_validator 노드 | 8h | `nodes/build_validator.py`(신규), `graph.py`, `state.py` | `111-build-validator.md` |
| **#35** | 112 | 결정론적 스캐폴드 분리 | 4h | `nodes/scaffold_generator.py`(신규), `graph.py` | `112-deterministic-scaffold.md` |
| **#38** | 115 | Council 데모 모드 전환 | 3h | `graph.py`, `server.py` | `115-council-demo-mode.md` |

### Phase 0 (의존성 없음 — 즉시 착수)

| # | Task | 내용 | 시간 | 스펙 문서 |
|---|------|------|------|----------|
| **#60** | 161 | YouTube Discovery Engine | 8h | `161-youtube-discovery.md` |
| **#63** | 164 | 논문 검색 엔진 (OpenAlex+arXiv) | 6h | `164-paper-search-engine.md` |
| **#65** | 166 | 경쟁사 분석 엔진 | 8h | `166-competitive-analysis.md` |

### Gradient (독립 — 즉시 착수)

| # | 내용 | 스펙 문서 |
|---|------|----------|
| **#76** | [G2] Agent Evaluation 도입 | 없음 (이슈 본문 참조) |
| **#79** | [G5] Multi-Agent Routing | 없음 (이슈 본문 참조) |
| **#80** | [G6] A2A Protocol | 없음 (이슈 본문 참조) |
| **#81** | [G7] DO Spaces 아티팩트 저장 | 없음 (이슈 본문 참조) |
| **#82** | [G8] Image Generation | 없음 (이슈 본문 참조) |
| **#83** | [G9] DO MCP Server 통합 | 없음 (이슈 본문 참조) |
| **#84** | [G10] Agent Versioning | 없음 (이슈 본문 참조) |

---

## 4. 블로커 체인 (이 순서대로만 진행 가능)

### 크리티컬 패스 A: Phase 1 → Phase 2 → Phase 4

```
#34 (111 build_validator, 8h)
 ├→ #36 (113 빌드 에러 피드백, 4h)
 ├→ #70 (P1 Deploy health gate, 6h)
 └→ #39 (121 OpenAPI 스펙 생성, 12h)
      ├→ #40 (122 openapi-typescript, 4h) → #42 (124 타입 안전 API, 6h)
      ├→ #41 (123 datamodel-codegen, 4h)
      └→ #43 (125 계약 검증, 6h)
           └→ Phase 4 (#49→#50→#51→#52, 48h)
```

**총 크리티컬 패스 길이: #34 → #39 → #40 → #42 → Phase 4 = ~78h**

### 크리티컬 패스 B: Phase 0 → Pivot 후반

```
#60 (161, 8h) → #61 (162, 6h) → #62 (163, 8h)
  + #63 (164, 6h)                                → #64 (165, 4h)
  + #65 (166, 8h)                                → #66 (167, 4h)
                                                    → #67 (168, 8h)
                                                        → #68 (169, 10h)
                                                            → #71 (P3 Dashboard, 8h)
                                                                → #72 (P3 Schema, 8h)
                                                                    → #73 (P4 Cleanup, 4h)
```

**총 크리티컬 패스 길이: #60 → #61 → #62 → #67 → #68 → #71 → #72 → #73 = ~60h**

### 크리티컬 패스 C: 112 → Phase 3

```
#35 (112, 4h) → #37 (114 백엔드 템플릿, 6h)
              → #44 (131, 4h) + #45 (132, 3h) + #46 (133, 3h) → #47 (134, 5h)
```

**총 크리티컬 패스 길이: #35 → #44 → #47 = ~13h**

---

## 5. 전체 구현 순서 (단계별)

### 단계 1: NOW (의존성 없음, 병렬 착수)

| 트랙 | 이슈 | 시간 |
|------|------|------|
| Phase 1 | #34, #35, #38 | 15h |
| Phase 0 | #60, #63, #65 | 22h |
| Gradient | #76~#84 (우선순위에 따라 선택) | - |

### 단계 2: Phase 1 1차 완료 후

| 이슈 | 블로커 | 시간 |
|------|--------|------|
| #36 (113 빌드 에러 피드백) | #34 완료 | 4h |
| #37 (114 백엔드 템플릿) | #35 완료 | 6h |
| #70 (P1 Deploy health gate) | #34 완료 | 6h |
| #61 (162 스트리밍 트랜스크립트) | #60 완료 | 6h |
| #64 (165 논문 브레인스톰) | #63 완료 | 4h |
| #66 (167 GO/NO-GO) | #65 완료 | 4h |

### 단계 3: Phase 0 중반 + Phase 2 시작

| 이슈 | 블로커 | 시간 |
|------|--------|------|
| #39 (121 OpenAPI 스펙 생성) | #34 완료 | 12h |
| #62 (163 Gemini Insight) | #61 완료 + #53(done) | 8h |
| #44, #45, #46, #48 (Phase 3 병렬) | #35 완료 | 14h |

### 단계 4: Phase 2 완료 + Phase 0 후반

| 이슈 | 블로커 | 시간 |
|------|--------|------|
| #40, #41, #43 (Phase 2 병렬) | #39 완료 | 14h |
| #67 (168 스트리밍 오케스트레이터) | #60~#66 전부 | 8h |
| #47 (134 레이아웃 아키타입) | #44+#45+#46 | 5h |

### 단계 5: Phase 2 마무리 + Phase 0 마무리

| 이슈 | 블로커 | 시간 |
|------|--------|------|
| #42 (124 타입 안전 API 클라이언트) | #40 완료 | 6h |
| #68 (169 Kanban UI) | #67 완료 | 10h |

### 단계 6: Phase 4 (순차)

| 이슈 | 블로커 | 시간 |
|------|--------|------|
| #49 → #50 → #51 → #52 | Phase 2 전체 | 48h |

### 단계 7: Phase 5 + Pivot 후반

| 이슈 | 블로커 | 시간 |
|------|--------|------|
| #57, #58, #59 (병렬) | - | 26h |
| #71 (Dashboard 분리) | #68 완료 | 8h |
| #72 (Schema 정규화) | #71 완료 | 8h |
| #73 (Legacy cleanup) | 모든 Pivot 완료 | 4h |

---

## 6. 이슈별 착수 가능 여부 요약표

| # | Task | Phase | 블로커 | 착수 가능? | 예상 시간 | 스펙 문서 |
|---|------|-------|--------|-----------|----------|----------|
| #34 | 111 | P1 | 없음 | **NOW** | 8h | `111-build-validator.md` |
| #35 | 112 | P1 | 없음 | **NOW** | 4h | `112-deterministic-scaffold.md` |
| #36 | 113 | P1 | #34 | BLOCKED | 4h | `113-build-error-feedback.md` |
| #37 | 114 | P1 | #35 | BLOCKED | 6h | `114-backend-template.md` |
| #38 | 115 | P1 | 없음 | **NOW** | 3h | `115-council-demo-mode.md` |
| #39 | 121 | P2 | #34 | BLOCKED | 12h | `121-openapi-spec-generator.md` |
| #40 | 122 | P2 | #39 | BLOCKED | 4h | `122-openapi-typescript.md` |
| #41 | 123 | P2 | #39 | BLOCKED | 4h | `123-datamodel-codegen.md` |
| #42 | 124 | P2 | #40 | BLOCKED | 6h | `124-typesafe-api-client.md` |
| #43 | 125 | P2 | #34,#39 | BLOCKED | 6h | `125-contract-validation.md` |
| #44 | 131 | P3 | #35 | BLOCKED | 4h | `131-oklch-color-system.md` |
| #45 | 132 | P3 | #35 | BLOCKED | 3h | `132-typography-system.md` |
| #46 | 133 | P3 | #35 | BLOCKED | 3h | `133-motion-tokens.md` |
| #47 | 134 | P3 | #44,#45,#46 | BLOCKED | 5h | `134-layout-archetypes.md` |
| #48 | 135 | P3 | 없음 | **NOW** | 3h | `135-seed-data-generator.md` |
| #49 | 141 | P4 | Phase 2 | BLOCKED | 20h | `141-per-file-codegen.md` |
| #50 | 142 | P4 | #49 | BLOCKED | 8h | `142-per-file-ast-validation.md` |
| #51 | 143 | P4 | #50 | BLOCKED | 8h | `143-per-file-regeneration.md` |
| #52 | 144 | P4 | #51 | BLOCKED | 12h | `144-prompt-optimization.md` |
| #57 | 155 | P5 | 없음 | **NOW** | 12h | `155-frontend-tests.md` |
| #58 | 156 | P5 | 없음 | **NOW** | 8h | `156-deployment-metrics.md` |
| #59 | 157 | P5 | 없음 | **NOW** | 6h | `157-ci-enhancement.md` |
| #60 | 161 | P0 | 없음 | **NOW** | 8h | `161-youtube-discovery.md` |
| #61 | 162 | P0 | #60 | BLOCKED | 6h | `162-streaming-transcript.md` |
| #62 | 163 | P0 | #61 | BLOCKED | 8h | `163-gemini-insight.md` |
| #63 | 164 | P0 | 없음 | **NOW** | 6h | `164-paper-search-engine.md` |
| #64 | 165 | P0 | #62,#63 | BLOCKED | 4h | `165-paper-brainstorm.md` |
| #65 | 166 | P0 | 없음 | **NOW** | 8h | `166-competitive-analysis.md` |
| #66 | 167 | P0 | #62,#64,#65 | BLOCKED | 4h | `167-go-nogo-engine.md` |
| #67 | 168 | P0 | #60~#66 | BLOCKED | 8h | `168-streaming-orchestrator.md` |
| #68 | 169 | P0 | #67 | BLOCKED | 10h | `169-kanban-action-ui.md` |
| #70 | P1 | Pivot | #34 | BLOCKED | 6h | `192-deploy-health-gate.md` |
| #71 | P3 | Pivot | #68 | BLOCKED | 8h | `193-dashboard-console-split.md` |
| #72 | P3 | Pivot | #71 | BLOCKED | 8h | `194-result-schema-normalization.md` |
| #73 | P4 | Pivot | all P0~P3 | BLOCKED | 4h | `195-legacy-cleanup.md` |
| #74 | - | Pivot | - | TRACKER | - | - |
| #76 | G2 | Gradient | 없음 | **NOW** | - | 이슈 본문 |
| #79 | G5 | Gradient | 없음 | **NOW** | - | 이슈 본문 |
| #80 | G6 | Gradient | 없음 | **NOW** | - | 이슈 본문 |
| #81 | G7 | Gradient | 없음 | **NOW** | - | 이슈 본문 |
| #82 | G8 | Gradient | 없음 | **NOW** | - | 이슈 본문 |
| #83 | G9 | Gradient | 없음 | **NOW** | - | 이슈 본문 |
| #84 | G10 | Gradient | 없음 | **NOW** | - | 이슈 본문 |

**NOW = 15개** | **BLOCKED = 22개** | **TRACKER = 1개**

---

## 7. 의존성 그래프 (전체)

### Phase 0: Zero-Prompt Start

```
#60 (161) YouTube Discovery ──→ #61 (162) 스트리밍 트랜스크립트 ──→ #62 (163) Gemini Insight
#63 (164) 논문 검색 ───────────→ #64 (165) 논문 브레인스톰 [+#62]
#65 (166) 경쟁사 분석 ─────────→ #66 (167) GO/NO-GO [+#62,#64,#65]
                                                                    |
                                  #67 (168) 스트리밍 오케스트레이터 [#60~#66]
                                                    |
                                  #68 (169) Kanban + Action Feed UI
```

### Phase 1: 기반 구축

```
#34 (111) build_validator ──→ #36 (113) 빌드 에러 피드백
#35 (112) 결정론적 스캐폴드 ──→ #37 (114) 백엔드 템플릿
#38 (115) Council 데모 모드    (독립)
```

### Phase 2: 타입 안전성

```
#39 (121) OpenAPI 스펙 생성 [needs #34] ──→ #40 (122) openapi-typescript ──→ #42 (124) 타입 안전 API
                                          |→ #41 (123) datamodel-codegen
#43 (125) 계약 검증 [needs #34, #39]
```

### Phase 3: 비주얼 품질

```
#44 (131) OKLCH [needs #35] ───┐
#45 (132) 타이포그래피 [needs #35] |→ #47 (134) 레이아웃 [needs #44,#45,#46]
#46 (133) Motion [needs #35] ──┘
#48 (135) 시드 데이터 (독립)
```

### Phase 4: 파일별 생성

```
#49 (141) → #50 (142) → #51 (143) → #52 (144)  [needs Phase 2 전체]
```

### Phase 5 + Pivot

```
#57 (155), #58 (156), #59 (157) — 모두 독립

#70 (P1) [needs #34] → #71 (P3) [needs #68] → #72 (P3) [needs #71] → #73 (P4) [needs all]
```

---

## 8. 발견된 문제점

### Phase 라벨 누락

- #57, #58, #59 (Tasks 155-157)에 `phase:5-testing` 라벨 없음
- #71, #72에 `phase:pivot` 라벨 없음

### Gradient 이슈 스펙 부재

- #76~#84 (G2~G10)에는 `docs/reference/` 스펙 문서가 없음
- 이슈 본문만으로 구현해야 함 — 예상 시간 추정 불가

### 누락 문서

- `18-final-pivot-refactor-plan.md` — `11-architecture-redesign.md`에서 참조하지만 미존재

---

## 9. 이슈 적합성 판정

전체 38개 오픈 이슈 모두 적합. 각 이슈는 스펙 문서(Gradient 제외)와 1:1 매핑되고,
의존성 그래프가 문서와 일치함. 중복이나 불필요한 이슈 없음.
