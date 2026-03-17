# Task 156: 배포 메트릭스 파이프라인

## 1. 개요
vibeDeploy의 배포 성능과 비용을 추적하기 위해 배포 메트릭스 파이프라인을 구축합니다.

## 2. 상세 작업 내용

### 2.1 데이터베이스 스키마 수정
- `agent/db/schema.sql`에 `deployment_metrics` 테이블 추가:
  - `pipeline_id`, `duration_seconds`, `total_cost`, `llm_call_count`, `code_eval_iterations`, `build_validation_attempts`, `deployment_status`, `final_scores` (JSON), `model_config` (JSON), `created_at`

### 2.2 메트릭 기록 로직 추가
- `agent/nodes/deployer.py`에서 배포 완료 시 메트릭을 기록하도록 수정
- `agent/db/metrics_recorder.py` 신규 생성: 메트릭 저장 및 조회 로직 담당

### 2.3 API 엔드포인트 추가
- `agent/server.py`에 `/api/dashboard/metrics` 엔드포인트 추가:
  - 최근 N건의 성공률, 평균 소요시간, 평균 비용 등 통계 데이터 반환

## 3. 수용 기준 (Acceptance Criteria)
1. [ ] `deployment_metrics` 테이블이 정상적으로 생성됨
2. [ ] 배포 완료 시 모든 메트릭 항목이 정확히 기록됨
3. [ ] `/api/dashboard/metrics` 호출 시 올바른 통계 데이터가 반환됨
4. [ ] 성공률 계산이 정확하게 이루어짐 (성공 건수 / 전체 건수)

## 4. 구현 가이드 (Implementation Details)

```sql
-- agent/db/schema.sql 추가 예시
CREATE TABLE IF NOT EXISTS deployment_metrics (
    id SERIAL PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    duration_seconds FLOAT,
    total_cost FLOAT,
    llm_call_count INTEGER,
    code_eval_iterations INTEGER,
    build_validation_attempts INTEGER,
    deployment_status TEXT,
    final_scores JSONB,
    model_config JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5. 테스트 계획
1. `test_metrics_recording`: 배포 완료 후 DB에 메트릭이 올바르게 저장되었는지 확인
2. `test_metrics_api`: API 호출 시 반환되는 통계 데이터의 정확성 확인
3. `test_metrics_aggregation`: 다수의 배포 건에 대해 평균값 계산이 정확한지 확인
