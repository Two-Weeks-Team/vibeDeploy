# 151-gemini-provider

**Issue**: #53
**Status**: Pending
**Priority**: High
**Estimate**: 4h
**Dependencies**: 191

## Summary
vibeDeploy의 Google Gemini 연동을 `langchain_google_genai`에서 공식 `google-genai` SDK로 전환합니다. ADR-19(A1)에 따라 `agent/providers/google_adapter.py`를 구현하고, 최신 Gemini 3.1 모델의 기능을 네이티브하게 지원합니다.

## Tasks
- [ ] `agent/providers/google_adapter.py` 구현: `google.genai.Client`를 사용한 공식 SDK 연동
- [ ] `generate_content()` 호출 구현: 프로덕션 기본 경로로 설정
- [ ] 구조화 출력 지원: `response_schema` (Pydantic 모델)를 통한 네이티브 JSON 출력 강제
- [ ] Context Caching 지원: 긴 컨텍스트 재사용을 위한 캐싱 로직 추가
- [ ] Batch API 옵션 구현: 대량 작업 처리를 위한 비동기 배치 호출 지원
- [ ] 모델 ID 정렬: `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite-preview` 공식 ID 사용

## Acceptance Criteria
- [ ] `google.genai.Client`가 정상적으로 생성되고 인증됨을 확인
- [ ] `generate_content()`를 통해 텍스트 및 멀티모달 응답을 성공적으로 수신함
- [ ] Pydantic 모델을 `response_schema`로 전달했을 때 구조화된 JSON 응답이 반환됨
- [ ] API 키가 설정되지 않은 경우 적절한 에러 핸들링 또는 폴백이 작동함
- [ ] `gemini-3.1-flash-lite-preview` 모델을 사용한 고속 루프 테스트 통과

## Implementation Notes
- `google-genai` SDK는 `response_mime_type="application/json"`과 `response_schema`를 함께 사용하여 강력한 타입 안정성을 제공합니다.
- Zero-Prompt 탐색 lane에서는 비용 효율적인 `flash-lite` 모델을 우선적으로 사용합니다.
- 핵심 빌드 lane에서는 `pro-preview` 모델의 긴 컨텍스트와 정교한 추론 능력을 활용합니다.
