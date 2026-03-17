# Task 154: 프롬프트 전략 확장

## 1. 개요
vibeDeploy의 프롬프트 전략 엔진(`prompt_strategist.py`)에 Gemini 및 GPT-5 모델 패밀리에 대한 가이던스를 추가하여 모델별 최적의 성능을 끌어낼 수 있도록 합니다.

## 2. 상세 작업 내용

### 2.1 _STATIC_MODEL_GUIDANCE 업데이트
- `agent/nodes/prompt_strategist.py`의 `_STATIC_MODEL_GUIDANCE`에 `gemini` 및 `gpt5` 키 추가:
  - **Gemini**: 비주얼 이해 활용, 명시적 단계별 지시, temperature 0.3-0.5 권장 등
  - **GPT-5**: 구성 가능 추론 깊이, 도구 검색, 네이티브 JSON 스키마 활용 등

### 2.2 infer_model_family() 수정
- 모델명에서 `gemini` 또는 `gpt-5` 패턴을 감지하여 각각 `gemini`, `gpt5` 패밀리로 분류하도록 로직 추가

### 2.3 _extract_guidance_from_source() 수정
- `gemini` 및 `gpt5` 패밀리에 대한 소스 기반 가이던스 추출 로직 추가

## 3. 수용 기준 (Acceptance Criteria)
1. [ ] Gemini 모델에 대해 `gemini` 가이던스가 적용됨
2. [ ] GPT-5 모델에 대해 `gpt5` 가이던스가 적용됨
3. [ ] 기존 `anthropic`, `openai_gpt_oss`, `qwen3`, `deepseek_r1` 가이던스가 유지됨
4. [ ] `infer_model_family()`가 신규 모델들을 올바르게 분류함

## 4. 구현 가이드 (Implementation Details)

```python
# agent/nodes/prompt_strategist.py 수정 예시

_STATIC_MODEL_GUIDANCE = {
    # ... 기존 가이던스 ...
    "gemini": [
        "Leverage native visual understanding for UI layout decisions.",
        "Use structured JSON output mode for reliable schema generation.",
        "Take advantage of 1M token context for full codebase analysis.",
        "Prefer explicit step-by-step instructions over implicit conventions.",
    ],
    "gpt5": [
        "Use configurable reasoning effort based on task complexity.",
        "Leverage tool search for cost optimization in agent workflows.",
        "Use native structured output (JSON Schema) for guaranteed format compliance.",
        "Enable computer-use when visual verification is needed.",
    ],
}

def infer_model_family(model: str) -> str:
    normalized = (model or "").strip().lower()
    # ... 기존 로직 ...
    if "gemini" in normalized or normalized.startswith("google-"):
        return "gemini"
    if "gpt-5" in normalized:
        return "gpt5"
    return "generic"
```

## 5. 테스트 계획
1. `test_gemini_guidance_application`: Gemini 모델 사용 시 `gemini` 가이던스가 포함되는지 확인
2. `test_gpt5_guidance_application`: GPT-5 모델 사용 시 `gpt5` 가이던스가 포함되는지 확인
3. `test_family_inference`: 다양한 모델명에 대해 올바른 패밀리가 추론되는지 확인
