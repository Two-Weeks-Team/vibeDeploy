# 153-cost-table

**Issue**: #55
**Status**: Pending
**Priority**: High
**Estimate**: 2h
**Dependencies**: 191

## Summary
vibeDeploy의 비용 추적 시스템을 공식 가격표 기반으로 업데이트하고, surcharge-aware 계산 로직을 도입합니다. ADR-19(B5)에 따라 각 LLM 호출 단위로 상세 비용을 기록하며, 캐싱 및 롱 컨텍스트 할증을 반영합니다.

## Pricing Data (per 1M tokens)
- `gpt-5.4`: Input $2.50, Output $15.00 (Surcharge: >272K input 2x)
- `gpt-5.3-codex`: Input $1.75, Output $14.00
- `gemini-3.1-pro-preview`: Input $2.00, Output $12.00 (Surcharge: >200K input $4.00, Output $18.00)
- `gemini-3.1-flash-lite-preview`: Input $0.25, Output $1.50
- `claude-sonnet-4-6`: Input $3.00, Output $15.00 (Cache hit: $0.30)
- `claude-opus-4-6`: Input $5.00, Output $25.00 (Cache hit: $0.50)

## Tasks
- [ ] `agent/providers/pricing.py` 구현: 위 가격표 및 할증 규칙 통합
- [ ] LLM 호출 기록 로직 수정: `input_tokens`, `output_tokens`, `model_id`, `surcharge_type`, `cost_usd`를 매 호출마다 기록
- [ ] 캐시 할인 반영: Anthropic 및 OpenAI의 Prompt Caching/Cache Hit 할인 로직 적용
- [ ] 롱 컨텍스트 할증 적용: `gpt-5.4` 및 `gemini-3.1-pro`의 입력 크기에 따른 단가 변동 반영
- [ ] Grounding 비용 집계: Gemini Google Search Grounding 등 추가 비용 항목 처리

## Acceptance Criteria
- [ ] 주요 7개 모델에 대해 공식 가격표 기준의 비용 계산이 정확히 수행됨
- [ ] 캐시 히트 발생 시 할인된 단가가 적용되어 기록됨을 확인
- [ ] 롱 컨텍스트(예: 300K 토큰) 입력 시 할증된 단가가 정상적으로 적용됨
- [ ] 각 LLM 호출 결과에 `cost_usd` 필드가 포함되어 반환됨
- [ ] 세션별 총 비용 합산 시 할증 및 할인이 모두 반영된 결과가 도출됨
