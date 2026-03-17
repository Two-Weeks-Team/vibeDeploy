# 192-deploy-health-gate

**Issue**: #70
**Status**: Pending
**Priority**: High
**Estimate**: 6h
**Dependencies**: 111

## Summary
vibeDeploy의 배포 안정성을 확보하기 위해 Deploy Health Gate를 도입합니다. ADR-19(A4)의 Docker SDK 기반 빌드 검증 결과와 연동하여, 빌드가 성공한 경우에만 배포를 진행하고 배포 후에는 `/health` 엔드포인트를 통한 최종 Smoke Check를 수행합니다.

## Tasks
- [ ] `agent/nodes/deployer.py` 수정: `build_validation.passed != true`인 경우 배포 실행을 차단하는 로직 추가
- [ ] 백엔드 Scaffold 템플릿 수정: 생성되는 모든 앱에 `/health` 엔드포인트(ADR-A3 store.py 패턴 기반)를 기본 포함
- [ ] 배포 후 Smoke Check 구현: 배포 완료 직후 해당 URL의 `/health` 엔드포인트 호출 및 200 OK 확인
- [ ] 상태 기록 및 SSE 이벤트 연동: Smoke Check 실패 시 `deploy_failed` 상태로 기록하고 대시보드에 SSE 이벤트 전송
- [ ] `agent/db/store.py` 연동: 성공 시에만 `deployed` 상태로 최종 업데이트

## Acceptance Criteria
- [ ] 빌드 검증을 통과하지 못한 아이디어에 대해 배포 프로세스가 시작되지 않음을 확인
- [ ] 배포된 앱의 `/health` 엔드포인트가 200 OK를 반환할 때만 최종 성공으로 간주함
- [ ] Smoke Check 실패 시 대시보드에 명확한 실패 상태와 원인이 표시됨
- [ ] 배포 실패 시 `deploy_failed` 상태가 DB에 정확히 기록됨
- [ ] 로컬 테스트 환경에서 강제로 빌드 실패를 유도하여 배포 차단 로직 검증
