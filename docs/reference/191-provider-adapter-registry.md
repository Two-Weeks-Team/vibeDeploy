# 191-provider-adapter-registry

**Issue**: #69
**Status**: Pending
**Priority**: High
**Estimate**: 12h
**Dependencies**: None

## Summary
vibeDeploy의 LLM 호출 구조를 벤더별 공식 SDK 기반의 Provider Adapter Registry 체계로 재구성합니다. ADR-19(A2)에 따라 `agent/llm.py`의 비대한 책임을 분산하고, canonical model ID를 통한 동적 라우팅을 구현합니다.

## Tasks
- [ ] `agent/providers/registry.py` 구현: canonical model ID를 기반으로 적절한 adapter 인스턴스 반환
- [ ] `agent/providers/google_adapter.py` 구현: `google-genai` SDK를 직접 사용하여 `generate_content` 호출 및 구조화 출력 처리
- [ ] `agent/providers/openai_adapter.py` 구현: DigitalOcean Serverless Inference 및 OpenAI Direct API 대응
- [ ] `agent/providers/anthropic_adapter.py` 구현: Anthropic Messages API 직접 호출 (LangChain 미사용)
- [ ] `agent/providers/pricing.py` 구현: surcharge-aware(cache, long-context, grounding) 비용 계산 로직 통합
- [ ] `agent/llm.py` 리팩토링: 기존 로직을 제거하고 Registry Facade 역할만 수행하도록 축소
- [ ] `agent/model_capabilities.py` 재작성: `CAPABILITY_REGISTRY` 딕셔너리에 provider, model_id, api_style, supports_tools 등 상세 스펙 정의
- [ ] `LEGACY_MODEL_ALIASES` 매핑 구현: 읽기 시점에 레거시 별칭을 canonical ID로 변환

## Acceptance Criteria
- [ ] `gemini-3.1-pro-preview`, `gpt-5.4`, `claude-sonnet-4-6` 등 주요 7개 모델에 대한 lookup 및 adapter 생성 테스트 통과
- [ ] `openai-gpt-5.4`와 같은 레거시 별칭이 canonical ID로 정상 매핑됨을 확인
- [ ] `agent/llm.py`가 내부 구현 없이 Registry를 호출하는 Facade 패턴으로 동작함
- [ ] 기존의 모든 LLM 호출 테스트가 신규 Registry 체계 위에서 성공적으로 수행됨
- [ ] `google-genai` SDK 사용 시 `response_schema`를 통한 Pydantic 구조화 출력이 정상 작동함
