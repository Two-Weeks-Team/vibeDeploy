# 154-prompt-strategy-expansion

**Issue**: #56
**Status**: Pending
**Priority**: High
**Estimate**: 3h
**Dependencies**: 191

## Summary
vibeDeploy의 프롬프트 전략을 벤더별 고유 기능에 맞춰 확장합니다. 모델 패밀리를 자동으로 감지하고, 각 벤더의 최신 기능(Gemini 구조화 출력, GPT-5 추론 제어, Claude 확장 사고 등)을 최적으로 활용할 수 있는 가이던스를 시스템 프롬프트에 주입합니다.

## Vendor Strategies
- **Gemini**: 네이티브 구조화 출력(`response_schema`), 멀티모달 컨텍스트 활용, Temperature 0.3~0.5 권장
- **GPT-5.4**: `reasoning.effort` 명시적 제어, Responses API 도구 활용, 128K 출력 한도 고려
- **Claude 4.6**: Extended Thinking(사고 과정 노출) 활용, Tool Use 최적화, Temperature 0.0~1.0 가변 적용

## Tasks
- [ ] 모델 패밀리 감지 로직 구현: Canonical model ID에서 provider 및 family 추출 (Registry 경유)
- [ ] Gemini 가이던스 적용: 구조화 출력 스키마 명시 및 멀티모달 입력 처리 지침 추가
- [ ] GPT-5 가이던스 적용: 추론 노력(Reasoning Effort) 설정 및 도구 지원 프롬프트 설계
- [ ] Claude 가이던스 적용: 프롬프트 캐싱 효율화 및 확장 사고(Extended Thinking) 활성화 지침 추가
- [ ] 기존 4개 패밀리 유지: `generic`, `openai_gpt_oss`, `qwen3`, `deepseek_r1` 전략과의 호환성 유지

## Acceptance Criteria
- [ ] Gemini 모델 사용 시 `google_gemini` 가이던스가 시스템 프롬프트에 포함됨을 확인
- [ ] GPT-5 모델 사용 시 `openai_gpt5` 가이던스가 적용되어 추론 제어 지침이 주입됨
- [ ] Claude 모델 사용 시 `anthropic_claude46` 가이던스가 적용되어 캐싱 및 사고 지침이 주입됨
- [ ] 모델 ID로부터 올바른 벤더 패밀리를 추출하는 테스트 통과
- [ ] 각 벤더별 고유 기능(구조화 출력, 도구 사용 등)에 대한 프롬프트 최적화 결과 검증
