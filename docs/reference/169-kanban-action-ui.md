# Task 169: Manus 스타일 액션 피드 UI (v2)
상태: 미구현 | Phase 0 | 예상 시간: 10h
의존성: 168

## 1. 태스크 정의

상단 5컬럼 칸반 보드와 하단 액션 피드로 구성된 Zero-Prompt 전용 운영 콘솔을 구축한다. 이 UI의 목적은 "예쁜 대시보드"가 아니라, **탐색/판정/빌드 handoff 상태를 실시간으로 조작하고 관찰하는 작업면**을 제공하는 것이다.

## 2. 수용 기준 (Acceptance Criteria)

- [ ] AC-1: 5컬럼 칸반(탐색 중, GO 대기, 빌드 중, 배포됨, NO-GO)과 하단 액션 피드를 동일 세션 데이터로 렌더링한다.
- [ ] AC-2: 카드 상태(`analyzing`, `go_ready`, `build_queued`, `building`, `deployed`, `nogo`, `passed`, `build_failed`)별 UI 분기를 제공한다.
- [ ] AC-3: "GO!" 클릭은 `queue_build`, "패스" 클릭은 `pass_card` 액션 API를 호출한다.
- [ ] AC-4: 빌드 대기 카드는 GO 컬럼에 남아 `⏳ 빌드 대기 #N` 뱃지로 표시된다.
- [ ] AC-5: 액션 피드는 최대 300줄 유지, 자동 스크롤, 수동 스크롤 시 auto-follow 해제 로직을 가진다.
- [ ] AC-6: 상태바는 `analyzed_count`, `go_ready_count`, `build_queue_count`, `deployed_count`, `total_cost_usd`를 실시간 반영한다.
- [ ] AC-7: 모바일에서는 액션 피드 접기/펼치기와 칸반 가로 스크롤을 지원한다.

## 3. 변경 대상 파일

- `web/src/app/zero-prompt/page.tsx` (신규)
- `web/src/components/zero-prompt/kanban-board.tsx` (신규)
- `web/src/components/zero-prompt/kanban-column.tsx` (신규)
- `web/src/components/zero-prompt/idea-card.tsx` (신규)
- `web/src/components/zero-prompt/action-feed.tsx` (신규)
- `web/src/components/zero-prompt/action-entry.tsx` (신규)
- `web/src/components/zero-prompt/status-bar.tsx` (신규)
- `web/src/hooks/use-zero-prompt.ts` (신규)
- `web/src/lib/zero-prompt-api.ts` (신규)
- `web/src/types/zero-prompt.ts` (신규)

## 4. 상세 구현

### 4.1 타입 모델

```ts
export type ZeroPromptCardStatus =
  | "analyzing"
  | "go_ready"
  | "build_queued"
  | "building"
  | "deployed"
  | "nogo"
  | "passed"
  | "build_failed";

export interface ZeroPromptCard {
  card_id: string;
  status: ZeroPromptCardStatus;
  title: string;
  score?: number;
  reason?: string;
  source_video_id: string;
  queue_position?: number;
  build_thread_id?: string;
  live_url?: string;
}

export interface ZeroPromptSession {
  session_id: string;
  status: "idle" | "running" | "paused" | "completed" | "error";
  analyzed_count: number;
  candidate_count: number;
  go_ready_count: number;
  build_queue_count: number;
  total_cost_usd: number;
  cards: ZeroPromptCard[];
}
```

### 4.2 컬럼 매핑

| 컬럼 | 포함 상태 |
|------|----------|
| `탐색 중` | `analyzing` |
| `GO 대기` | `go_ready`, `build_queued` |
| `빌드 중` | `building` |
| `배포됨` | `deployed` |
| `NO-GO` | `nogo`, `passed`, `build_failed` |

핵심 규칙:
- `build_queued` 카드는 **빌드 중 컬럼으로 이동하지 않는다.**
- 실제 `building` 상태가 될 때만 `빌드 중` 컬럼으로 이동한다.
- `go_ready_count`는 `go_ready` 카드만 집계하며, `build_queued` / `building`은 슬롯 계산에서 제외한다.

### 4.3 인터랙션 계약

버튼과 드래그는 결국 같은 액션 API를 호출해야 한다.

| UI 행동 | API 액션 | 서버 결과 |
|--------|---------|----------|
| GO 카드에서 `GO!` 클릭 | `queue_build` | `go_ready -> build_queued/building` |
| GO 카드에서 `패스` 클릭 | `pass_card` | `go_ready -> passed` |
| GO 카드를 `빌드 중` 컬럼으로 드래그 | `queue_build` | 버튼과 동일 |
| GO 카드를 `NO-GO` 컬럼으로 드래그 | `pass_card` | 버튼과 동일 |
| 헤더의 `Pause` 클릭 | `pause` | 탐색 정지 |
| 헤더의 `Resume` 클릭 | `resume` | 탐색 재개 |

### 4.4 Hook 계약 (`use-zero-prompt.ts`)

```ts
export function useZeroPrompt() {
  // 1. startSession()
  // 2. connectEvents(sessionId)
  // 3. applyEvent(event)
  // 4. dispatchAction(sessionId, action, cardId?)
  // 5. snapshot recovery
}
```

필수 책임:
- `GET session`으로 초기 스냅샷 로드
- `GET events`로 SSE 연결
- 이벤트 순서 보장을 위해 `event_id` 기준 dedupe
- 네트워크 재연결 시 최근 스냅샷 재조회
- 카드 컬럼 분류 selector 제공

### 4.5 액션 피드 렌더링 규칙

```tsx
<ActionFeed
  events={events.slice(-300)}
  autoFollow={autoFollow}
  onAutoFollowChange={setAutoFollow}
/>
```

규칙:
- 최대 300줄 유지
- `zp.go`, `zp.nogo`, `zp.build.start`, `zp.build.complete`, `zp.session.error`는 강조 스타일 적용
- 긴 payload는 요약 1줄 + expandable detail 패턴 사용
- 수동 스크롤이 바닥에서 48px 이상 벗어나면 `autoFollow=false`

### 4.6 카드 UI 규칙

```text
go_ready:
  - 점수
  - 제목
  - 핵심 근거 1줄
  - [GO!] [패스]

build_queued:
  - 기존 go_ready UI 유지
  - 상단 우측에 "⏳ 빌드 대기 #N"
  - GO! 버튼 비활성화

building:
  - 진행률 바
  - 현재 단계명
  - build_thread_id 표시(ops/debug용)

deployed:
  - live URL 버튼

nogo/passed/build_failed:
  - 탈락 사유
```

## 5. 테스트 계획

- `test_kanban_column_mapping`
- `test_build_queued_badge_is_rendered_in_go_column`
- `test_go_button_dispatches_queue_build`
- `test_pass_button_dispatches_pass_card`
- `test_action_feed_caps_at_300_rows`
- `test_reconnect_restores_snapshot_and_resubscribes`
- `test_mobile_layout_uses_horizontal_scroll`

## 6. 검증 방법

- `cd web && npm test -- zero-prompt`
- 브라우저 수동 검증:
  - `/zero-prompt` 접속
  - Start 클릭
  - GO 카드 생성 후 `GO!` 클릭
  - 카드가 `build_queued` 또는 `building`으로 자연스럽게 이동하는지 확인
  - 빌드 완료 후 `deployed` 컬럼으로 이동하는지 확인

## 7. 롤백 계획

- `web/src/app/zero-prompt/` 제거
- `web/src/components/zero-prompt/` 제거
- `web/src/hooks/use-zero-prompt.ts`, `web/src/lib/zero-prompt-api.ts`, `web/src/types/zero-prompt.ts` 제거
