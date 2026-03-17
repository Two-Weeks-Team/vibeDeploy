# Task 169: Manus 스타일 액션 피드 UI (v2)
상태: 미구현 | Phase 0 | 예상 시간: 10h
의존성: 168

## 1. 태스크 정의
상단 5컬럼 칸반 보드와 하단 300줄 액션 피드로 구성된 Zero-Prompt 전용 UI를 구축합니다. 실시간 SSE 이벤트를 시각화하고, 사용자가 아이디어를 선택(GO!)하거나 패스할 수 있는 인터랙션을 제공합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 5컬럼 칸반(탐색 중, GO 대기, 빌드 중, 배포됨, NO-GO) 렌더링 및 카드 상태별 UI 분기.
- [ ] AC-2: 하단 300줄 액션 피드: SSE 이벤트별 아이콘/색상 적용, 자동 스크롤, Framer Motion 애니메이션.
- [ ] AC-3: 카드 인터랙션: "🚀GO!" 버튼 클릭 시 빌드 큐 추가, "패스" 클릭 시 NO-GO 이동 및 슬롯 비움.
- [ ] AC-4: 상태바: 분석 진행률, GO 대기 수, 빌드 수, 배포 수, 누적 비용 실시간 표시.
- [ ] AC-5: 모바일 반응형: 칸반 가로 스크롤, 액션 피드 접기/펼치기 지원.

## 3. 변경 대상 파일
- `web/src/app/zero-prompt/page.tsx` (신규)
- `web/src/components/zero-prompt/kanban-board.tsx` (신규)
- `web/src/components/zero-prompt/action-feed.tsx` (신규)
- `web/src/hooks/use-zero-prompt.ts` (신규)

## 4. 상세 구현

### 칸반 컬럼 구조
- **🔍 탐색 중**: 현재 분석 중인 영상 (analyzing)
- **✅ GO 대기**: GO 판정 아이디어 (go_ready, build_queued)
- **🔨 빌드 중**: 빌드 파이프라인 진행 중 (building)
- **🚀 배포됨**: 라이브 URL 확보 완료 (deployed)
- **❌ NO-GO**: 탈락 아이디어 (nogo, passed)

### UI 컴포넌트 (web/src/components/zero-prompt/)
```tsx
// action-feed.tsx
export const ActionFeed = ({ events }) => {
  // 300줄 유지, 자동 스크롤, Framer Motion 애니메이션
  return (
    <div className="bg-zinc-950 font-mono text-xs overflow-y-auto h-64">
      {events.map(event => <ActionEntry key={event.id} {...event} />)}
    </div>
  );
};

// kanban-board.tsx
export const KanbanBoard = ({ ideas }) => {
  // 5컬럼 레이아웃, 카드 드래그 또는 버튼 인터랙션
  return (
    <div className="grid grid-cols-5 gap-4">
      <KanbanColumn title="🔍 탐색 중" ideas={ideas.analyzing} />
      <KanbanColumn title="✅ GO 대기" ideas={ideas.go_ready} />
      {/* ... */}
    </div>
  );
};
```

## 5. 테스트 계획
- `test_kanban_rendering`: 5개 컬럼이 올바르게 표시되는지 확인.
- `test_sse_feed_update`: SSE 이벤트 수신 시 액션 피드에 즉시 반영되는지 확인.
- `test_card_action_trigger`: GO! 버튼 클릭 시 API 호출 및 상태 변경 확인.

## 6. 검증 방법
- 브라우저에서 `/zero-prompt` 접속 후 "Start" 버튼 클릭.
- 액션 피드에 로그가 실시간으로 쌓이고, GO 판정 시 칸반에 카드가 추가되는지 확인.
- 모바일 뷰에서 레이아웃이 깨지지 않는지 확인.

## 7. 롤백 계획
- `git checkout docs/reference/169-kanban-action-ui.md`
- `web/src/app/zero-prompt/` 관련 파일 삭제.
