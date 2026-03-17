# 193-dashboard-console-split

**Issue**: #71
**Status**: Pending
**Priority**: High
**Estimate**: 8h
**Dependencies**: 169

## Summary
vibeDeploy의 프론트엔드 구조를 운영 목적에 맞게 분리합니다. 기존의 통합 대시보드에서 Zero-Prompt 탐색 기능을 독립된 `/zero-prompt` 경로로 분리하고, API 모듈과 Hook의 책임을 명확히 나누어 유지보수성을 높입니다.

## Tasks
- [ ] `web/src/app/dashboard/page.tsx` 리팩토링: Zero-Prompt 관련 UI를 제거하고 Evaluation Ops 및 History 전용 페이지로 전환
- [ ] `web/src/app/zero-prompt/page.tsx` 신설: 독립된 Zero-Prompt 운영 콘솔(칸반 보드 + 액션 피드) 구현
- [ ] `web/src/lib/api.ts` 모듈 분리: `meeting-api.ts`, `brainstorm-api.ts`, `dashboard-api.ts`, `zero-prompt-api.ts`로 기능별 분할
- [ ] Hook 책임 분리: 기존 `use-pipeline-monitor.ts`에서 Zero-Prompt 관련 로직을 제거하고 `use-zero-prompt.ts` 신규 생성
- [ ] 네비게이션 업데이트: 사이드바 또는 상단 메뉴에 `/dashboard`와 `/zero-prompt`를 명확히 구분하여 배치

## Acceptance Criteria
- [ ] `/dashboard` 경로에서 Zero-Prompt 관련 UI나 상태가 더 이상 노출되지 않음
- [ ] `/zero-prompt` 경로가 독립적으로 작동하며 전용 칸반 보드와 액션 피드를 제공함
- [ ] API 호출이 4개의 분리된 모듈을 통해 목적에 맞게 수행됨
- [ ] `use-zero-prompt` Hook이 Zero-Prompt 세션 및 카드 상태를 독립적으로 관리함
- [ ] 각 페이지 간의 전환이 매끄럽고 상태 충돌이 발생하지 않음을 확인
