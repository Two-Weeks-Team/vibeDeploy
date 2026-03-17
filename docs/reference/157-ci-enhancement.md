# Task 157: CI 강화

## 1. 개요
vibeDeploy의 코드 품질과 보안을 강화하기 위해 CI 파이프라인을 확장하고 정적 분석 도구를 도입합니다.

## 2. 상세 작업 내용

### 2.1 .github/workflows/ci.yml 수정
- `pytest-cov` 추가 및 80% 커버리지 임계값 설정
- `mypy` (agent/ 디렉토리) 정적 타입 검사 추가
- `tsc --noEmit` (web/ 디렉토리) TypeScript 타입 검사 추가
- `npm audit` 보안 취약점 스캔 추가
- `bandit` (Python SAST) 보안 분석 추가

### 2.2 설정 파일 생성 및 수정
- `agent/pyproject.toml`: `mypy` 설정 (strict 모드 등)
- `agent/.banditrc`: `bandit` 제외 규칙 설정

## 3. 수용 기준 (Acceptance Criteria)
1. [ ] 모든 CI 작업이 정의되고 정상적으로 실행됨
2. [ ] 테스트 커버리지가 80% 미만일 경우 CI가 실패함
3. [ ] `mypy` strict 모드 검사를 통과함
4. [ ] `tsc --noEmit` 검사를 통과함
5. [ ] `bandit` 보안 스캔에서 심각한 취약점이 발견되지 않음

## 4. 구현 가이드 (Implementation Details)

```yaml
# .github/workflows/ci.yml 수정 예시
jobs:
  agent-test:
    steps:
      - name: Run tests with coverage
        run: |
          pytest --cov=agent --cov-fail-under=80 tests/

  agent-lint:
    steps:
      - name: Run mypy
        run: mypy agent/
      - name: Run bandit
        run: bandit -r agent/ -c .banditrc

  web-test:
    steps:
      - name: Run frontend tests
        run: cd web && npm test
      - name: Run tsc
        run: cd web && npx tsc --noEmit
```

## 5. 테스트 계획
1. CI 파이프라인 실행 결과 확인
2. 커버리지 미달 시 CI 실패 여부 확인
3. 타입 에러 또는 보안 취약점 발생 시 CI 실패 여부 확인
