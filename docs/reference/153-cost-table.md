# Task 153: 비용 테이블 확장

## 1. 개요
vibeDeploy의 비용 추적 시스템(`cost.py`)에 신규 모델들의 가격 정보를 추가하여 정확한 비용 계산이 가능하도록 합니다.

## 2. 상세 작업 내용

### 2.1 PRICING_PER_MILLION 업데이트
- `agent/cost.py`의 `PRICING_PER_MILLION` 딕셔너리에 다음 모델들의 가격(입력/출력 per 1M tokens) 추가:
  - `openai-gpt-5.4`: ($2.50, $15.00)
  - `google-gemini-3.1-pro`: ($2.00, $12.00)
  - `google-gemini-2.5-flash`: ($0.15, $0.60)
  - `deepseek-v3.2`: ($0.27, $1.10)
  - `deepseek-r1`: ($0.55, $2.19)

### 2.2 CostTracker 검증
- `CostTracker.record()`가 신규 모델들에 대해 정확한 비용을 계산하는지 확인합니다.

## 3. 수용 기준 (Acceptance Criteria)
1. [ ] 5개 신규 모델의 가격이 `PRICING_PER_MILLION`에 등록됨
2. [ ] `CostTracker.record()` 호출 시 등록된 가격을 기반으로 비용이 계산됨
3. [ ] 미등록 모델에 대해서는 기본값 (0.0, 0.0)이 적용되어 에러가 발생하지 않음
4. [ ] `total_cost` 속성이 모든 항목의 합계를 정확히 반영함

## 4. 구현 가이드 (Implementation Details)

```python
# agent/cost.py 수정 예시

PRICING_PER_MILLION = {
    # ... 기존 모델 ...
    "openai-gpt-5.4": (2.50, 15.00),
    "google-gemini-3.1-pro": (2.00, 12.00),
    "google-gemini-2.5-flash": (0.15, 0.60),
    "deepseek-v3.2": (0.27, 1.10),
    "deepseek-r1": (0.55, 2.19),
}
```

## 5. 테스트 계획
1. `test_gpt5_cost`: GPT-5.4 모델의 비용 계산 정확성 확인
2. `test_gemini_pro_cost`: Gemini 3.1 Pro 모델의 비용 계산 정확성 확인
3. `test_gemini_flash_cost`: Gemini 2.5 Flash 모델의 비용 계산 정확성 확인
4. `test_deepseek_v3_cost`: DeepSeek V3.2 모델의 비용 계산 정확성 확인
5. `test_deepseek_r1_cost`: DeepSeek R1 모델의 비용 계산 정확성 확인
