# Task 151: Gemini 프로바이더 추가

## 1. 개요
vibeDeploy의 LLM 라우팅 엔진(`llm.py`)에 Google Gemini 모델 지원을 추가합니다. `langchain_google_genai` 패키지를 사용하여 Gemini 모델을 호출할 수 있도록 구현합니다.

## 2. 상세 작업 내용

### 2.1 의존성 추가
- `agent/requirements.txt`에 `langchain-google-genai` 추가

### 2.2 llm.py 수정
- **모델 감지 함수 추가**: `_is_gemini_model(model: str) -> bool`
  - "gemini" 포함 또는 "google-"로 시작하는 모델명 감지
- **모델 ID 매핑 함수 추가**: `_gemini_model_id(model: str) -> str`
  - `google-gemini-3.1-pro` → `gemini-3.1-pro` 등 매핑
- **get_llm() 분기 추가**:
  - `GOOGLE_API_KEY` 또는 `GEMINI_API_KEY` 환경변수 확인
  - `ChatGoogleGenerativeAI` 인스턴스 생성 및 반환
- **temperature 보정 추가**: `_coerce_temperature_for_model()` 수정
  - Gemini 모델의 경우 0.0~1.0 범위로 제한 (API는 2.0까지 지원하지만 코드 생성 안정성을 위해 제한)

## 3. 수용 기준 (Acceptance Criteria)
1. [ ] Gemini 모델명이 입력되었을 때 `_is_gemini_model`이 `True`를 반환함
2. [ ] `get_llm()` 호출 시 Gemini 모델에 대해 `ChatGoogleGenerativeAI` 객체가 생성됨
3. [ ] API 키가 설정되지 않은 경우 다음 프로바이더(OpenAI 폴백 등)로 정상적으로 넘어감
4. [ ] `requirements.txt`에 필요한 패키지가 명시됨

## 4. 구현 가이드 (Implementation Details)

```python
# agent/llm.py 수정 예시

def _is_gemini_model(model: str) -> bool:
    normalized = (model or "").strip().lower()
    return "gemini" in normalized or normalized.startswith("google-")

def _gemini_model_id(model: str) -> str:
    mapping = {
        "google-gemini-3.1-pro": "gemini-3.1-pro",
        "google-gemini-2.5-flash": "gemini-2.5-flash",
    }
    return mapping.get(model.strip().lower(), model)

# get_llm 내부에 추가
google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if _is_gemini_model(model) and google_key:
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=_gemini_model_id(model),
        google_api_key=google_key,
        temperature=_coerce_temperature_for_model(model, temperature),
        max_output_tokens=effective_max_tokens,
        timeout=effective_timeout,
    )
```

## 5. 테스트 계획
1. `test_is_gemini_model`: 다양한 Gemini 모델명에 대한 감지 여부 확인
2. `test_gemini_routing`: API 키가 있을 때 `ChatGoogleGenerativeAI` 반환 확인
3. `test_gemini_temperature_coercion`: 1.0 이상의 temperature가 1.0으로 보정되는지 확인
