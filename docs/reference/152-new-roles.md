# 152-new-roles

**Issue**: #54
**Status**: Pending
**Priority**: High
**Estimate**: 2h
**Dependencies**: 191

## Summary
vibeDeploy의 에이전트 역할(Role) 정의를 공식 모델 ID 체계로 정렬하고, 피벗된 아키텍처에 필요한 신규 역할을 추가합니다. 모든 역할은 `agent/providers/registry.py`를 경유하여 모델을 할당받습니다.

## Roles
- `council`: `claude-sonnet-4-6` (DO Inference)
- `code_gen_frontend`: `gpt-5.3-codex` (DO Inference)
- `code_gen_backend`: `gpt-5.3-codex` (DO Inference)
- `doc_gen`: `gemini-3.1-pro-preview` (Google Direct)
- `ui_design`: `gemini-3.1-pro-preview` (Google Direct)
- `code_review`: `gpt-5.4` (DO Inference)
- `api_contract`: `gpt-5.4` (DO Inference)
- `ci_repair`: `gpt-5.4` (DO Inference)
- `brainstorm`: `claude-opus-4-6` (DO Inference)
- `zero_prompt_discovery`: `gemini-3.1-flash-lite-preview` (Google Direct)

## Tasks
- [ ] `DEFAULT_ROLE_MODEL_CONFIG` 업데이트: 위 10개 역할에 대해 canonical model ID 할당
- [ ] `agent/llm.py` 연동: 역할을 통해 모델을 조회할 때 Provider Registry를 사용하도록 수정
- [ ] 환경변수 오버라이드 지원: `VIBEDEPLOY_MODEL_[ROLE_NAME]` 패턴의 환경변수 우선 적용 로직 유지
- [ ] 레거시 별칭 처리: 설정 파일이나 환경변수에 레거시 별칭이 있을 경우 읽기 시점에 canonical ID로 변환

## Acceptance Criteria
- [ ] 10개의 모든 역할에 대해 올바른 canonical model ID가 조회됨을 확인
- [ ] `llm.py`를 직접 호출하지 않고 Registry Facade를 통해 모델 인스턴스를 획득함
- [ ] 환경변수를 통한 모델 오버라이드가 정상적으로 작동함
- [ ] 기존에 정의된 역할들의 기능이 유지되면서 모델 ID만 공식 명칭으로 변경됨
- [ ] 신규 추가된 역할(`ci_repair`, `zero_prompt_discovery` 등)이 정상적으로 등록됨
