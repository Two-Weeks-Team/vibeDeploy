# 194-result-schema-normalization

**Issue**: #72
**Status**: Pending
**Priority**: High
**Estimate**: 8h
**Dependencies**: 193

## Summary
vibeDeploy의 데이터 일관성과 추적성을 위해 결과 스키마를 정규화하고 Lineage 연결을 강화합니다. ADR-19(A3)에 따라 PostgreSQL을 기반으로 세션, 카드, 빌드, 배포 간의 관계를 정의하고 공통 스키마를 적용합니다.

## Tasks
- [ ] Lineage Key 정의: `source_video_id → card_id → build_job_id → deployment`로 이어지는 추적 체계 구축
- [ ] 공통 스키마 설계: `meeting`, `brainstorm`, `zero_prompt_session`, `build_job`, `deployment`에서 공통으로 사용할 필드(id, status, created_at, cost 등) 정의
- [ ] PostgreSQL 테이블 생성/수정: `zero_prompt_sessions`, `zero_prompt_cards`, `build_jobs`, `deployments` 테이블 구현
- [ ] API View Model 정규화: 대시보드 및 히스토리 API가 정규화된 View Model을 반환하도록 수정
- [ ] SSE 이벤트 페이로드 일치: SSE 이벤트의 데이터 구조와 DB 저장소의 필드명을 일치시켜 프론트엔드 처리 단순화

## Acceptance Criteria
- [ ] 특정 배포 결과로부터 원본 소스(YouTube ID 등)까지의 Lineage를 API를 통해 추적할 수 있음
- [ ] 모든 세션 및 작업 결과가 공통 스키마를 준수하여 일관된 형태로 조회됨
- [ ] 대시보드 히스토리에서 정규화된 요약 정보를 정상적으로 표시함
- [ ] DB 필드명과 SSE 페이로드 필드명이 1:1로 매칭되어 추가 변환 로직이 불필요함
- [ ] 신규 테이블에 대한 CRUD 및 관계 쿼리 테스트 통과
