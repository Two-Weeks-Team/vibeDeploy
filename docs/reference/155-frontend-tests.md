# Task 155: 프론트엔드 테스트 인프라

## 1. 개요
vibeDeploy 프론트엔드(`web/`)의 안정성을 확보하기 위해 Vitest와 React Testing Library를 기반으로 한 테스트 인프라를 구축합니다.

## 2. 상세 작업 내용

### 2.1 의존성 설치
- `web/package.json`의 `devDependencies`에 `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` 추가

### 2.2 설정 파일 생성
- `web/vitest.config.ts`: Vitest 설정 (alias, environment 등)
- `web/setupTests.ts`: 테스트 환경 초기화 (jest-dom 매처 등)

### 2.3 핵심 테스트 작성
- `web/src/lib/api.test.ts`: API 클라이언트(`api.ts`)의 fetch 로직 테스트
- `web/src/hooks/use-pipeline-monitor.test.ts`: SSE 훅(`use-pipeline-monitor.ts`)의 상태 관리 테스트

### 2.4 스크립트 및 CI 연동
- `web/package.json`에 `test` 스크립트 추가 (`vitest run`)
- `.github/workflows/ci.yml`에 `web-test` 작업 추가

## 3. 수용 기준 (Acceptance Criteria)
1. [ ] `npm test` 실행 시 모든 테스트가 성공함
2. [ ] `api.ts`에 대한 최소 3개 이상의 테스트 케이스가 존재함
3. [ ] `use-pipeline-monitor.ts`에 대한 최소 2개 이상의 테스트 케이스가 존재함
4. [ ] CI 파이프라인에서 프론트엔드 테스트가 자동으로 실행되고 통과함

## 4. 구현 가이드 (Implementation Details)

```typescript
// web/vitest.config.ts 예시
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./setupTests.ts'],
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

## 5. 테스트 계획
1. `api.test.ts`: `startMeeting`, `getPipelineStatus` 등 주요 API 호출 성공/실패 시나리오 테스트
2. `use-pipeline-monitor.test.ts`: SSE 이벤트 수신 시 상태 업데이트 및 노드 상태 변경 테스트
