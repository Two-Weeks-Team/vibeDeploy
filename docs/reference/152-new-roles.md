# Task 152: 신규 역할 정의

## 1. 개요
vibeDeploy 파이프라인의 각 단계에 최적의 모델을 배정하기 위해 3개의 신규 역할을 정의하고, `llm.py`의 모델 설정을 업데이트합니다.

## 2. 상세 작업 내용

### 2.1 DEFAULT_MODEL_CONFIG 업데이트
- `agent/llm.py`의 `DEFAULT_MODEL_CONFIG`에 다음 3개 역할 추가:
  - `ui_design`: `google-gemini-3.1-pro` (UI/디자인 생성 전문)
  - `code_review`: `openai-gpt-5.4` (코드 검증 및 에러 분석 전문)
  - `api_contract`: `openai-gpt-5.4` (OpenAPI 스펙 및 구조화 출력 전문)

### 2.2 _MODEL_ENV_OVERRIDES 업데이트
- 각 역할에 대한 환경변수 매핑 추가:
  - `ui_design`: `VIBEDEPLOY_MODEL_UI_DESIGN`, `VIBEDEPLOY_MODEL_ALL`, `VIBEDEPLOY_MODEL`
  - `code_review`: `VIBEDEPLOY_MODEL_CODE_REVIEW`, `VIBEDEPLOY_MODEL_ALL`, `VIBEDEPLOY_MODEL`
  - `api_contract`: `VIBEDEPLOY_MODEL_API_CONTRACT`, `VIBEDEPLOY_MODEL_ALL`, `VIBEDEPLOY_MODEL`

## 3. 수용 기준 (Acceptance Criteria)
1. [ ] `get_model_for_role("ui_design")` 호출 시 기본값으로 `google-gemini-3.1-pro`가 반환됨
2. [ ] `VIBEDEPLOY_MODEL_CODE_REVIEW` 환경변수 설정 시 해당 모델로 오버라이드됨
3. [ ] 기존 14개 역할의 모델 설정에 영향이 없음
4. [ ] `get_runtime_model_config()` 결과에 신규 역할 3개가 포함됨

## 4. 구현 가이드 (Implementation Details)

```python
# agent/llm.py 수정 예시

DEFAULT_MODEL_CONFIG = {
    # ... 기존 역할 ...
    "ui_design": "google-gemini-3.1-pro",
    "code_review": "openai-gpt-5.4",
    "api_contract": "openai-gpt-5.4",
}

_MODEL_ENV_OVERRIDES = {
    # ... 기존 오버라이드 ...
    "ui_design": ("VIBEDEPLOY_MODEL_UI_DESIGN", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "code_review": ("VIBEDEPLOY_MODEL_CODE_REVIEW", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
    "api_contract": ("VIBEDEPLOY_MODEL_API_CONTRACT", "VIBEDEPLOY_MODEL_ALL", "VIBEDEPLOY_MODEL"),
}
```

## 5. 테스트 계획
1. `test_new_roles_default`: 신규 역할의 기본 모델이 올바르게 설정되었는지 확인
2. `test_new_roles_override`: 환경변수를 통한 모델 오버라이드가 정상 동작하는지 확인
3. `test_config_completeness`: `MODEL_CONFIG` 객체에서 신규 역할을 조회할 수 있는지 확인
