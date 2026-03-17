# 195-legacy-cleanup

**Issue**: #73
**Status**: Pending
**Priority**: High
**Estimate**: 4h
**Dependencies**: All P0~P3 tasks completed

## Summary
vibeDeploy의 피벗 리팩토링이 완료된 후, 더 이상 사용되지 않는 레거시 별칭과 데드 코드를 정리합니다. ADR-19(B3)에 따라 내부 별칭을 제거하고 공식 모델 ID 체계로 완전히 전환합니다.

## Tasks
- [ ] 레거시 별칭 제거: 코드 전반에서 `openai-*`, `anthropic-*`, `google-*` 접두사가 붙은 내부 별칭을 제거하고 canonical ID로 교체
- [ ] 데드 루트 정리: 더 이상 사용되지 않는 API 엔드포인트 및 SSE 이벤트 핸들러 제거
- [ ] 데드 테스트 정리: 이전 아키텍처 기반의 낡은 테스트 케이스 삭제 또는 신규 체계로 업데이트
- [ ] Compatibility Shim 제거: `LEGACY_MODEL_ALIASES` 매핑 딕셔너리 및 관련 변환 로직 최종 제거
- [ ] 코드 드리프트 검증: doc 18의 리팩토링 계획과 실제 구현 결과 사이의 차이가 없는지 최종 확인

## Acceptance Criteria
- [ ] 코드베이스 내에 `openai-gpt-5.4`와 같은 레거시 별칭이 존재하지 않음
- [ ] 사용되지 않는 경로(Dead Path)가 모두 제거되어 린트 및 빌드 시 경고가 발생하지 않음
- [ ] 모든 신규 테스트 및 기존 유효 테스트가 성공적으로 수행됨
- [ ] `agent/llm.py` 및 `agent/providers/` 내에 불필요한 호환성 코드가 남아있지 않음
- [ ] 최종 결과물이 doc 17 및 doc 18의 명세와 완벽히 일치함
