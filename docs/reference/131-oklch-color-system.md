# Task 131: OKLCH 색상 토큰 시스템
상태: 미구현 | Phase 3 | 예상 시간: 4h
의존성: 112 (결정론적 스캐폴드)

## 1. 태스크 정의
vibeDeploy가 생성하는 앱의 시각적 정체성을 결정하는 OKLCH 기반 색상 시스템을 구축합니다. 도메인별 프리셋을 바탕으로 지각적으로 균일한 12단계 색상 스케일을 생성하고, 이를 Tailwind CSS v4(@theme) 형식의 `globals.css`로 출력합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 5개 핵심 도메인(finance, health, creative, food, tech)에 대한 유효한 OKLCH 프리셋 정의
- [ ] AC-2: 각 도메인별로 Primary 색상의 12단계 스케일(Step 1~12) 자동 생성 로직 구현
- [ ] AC-3: 모든 시맨틱 역할(background, foreground, primary, accent, card, muted, border, success, warning, error) 포함
- [ ] AC-4: 다크 모드 지원을 위한 `.dark` 클래스 기반 CSS 변수 오버라이드 생성
- [ ] AC-5: 생성된 CSS가 문법 오류 없이 Tailwind CSS에서 즉시 사용 가능함

## 3. 변경 대상 파일
- `agent/nodes/build.py`: `generate_color_tokens` 함수 추가 및 `globals.css` 생성 로직 통합
- `web/src/app/globals.css`: 생성된 토큰이 주입될 대상 파일

## 4. 상세 구현

### 4.1 도메인 프리셋 정의 (DOMAIN_PRESETS)
```python
DOMAIN_PRESETS = {
    "finance": {
        "primary": "oklch(25% 0.05 260)", # Navy
        "accent": "oklch(85% 0.15 85)",   # Gold
        "base_hue": 260
    },
    "health": {
        "primary": "oklch(85% 0.04 150)", # Sage
        "accent": "oklch(70% 0.18 25)",   # Coral
        "base_hue": 150
    },
    "creative": {
        "primary": "oklch(35% 0.2 290)",  # Deep Purple
        "accent": "oklch(80% 0.18 75)",   # Amber
        "base_hue": 290
    },
    "food": {
        "primary": "oklch(30% 0.08 45)",  # Warm Earth
        "accent": "oklch(60% 0.25 35)",   # Vermillion
        "base_hue": 45
    },
    "tech": {
        "primary": "oklch(20% 0.02 250)", # Cool Gray
        "accent": "oklch(65% 0.25 250)",  # Electric Blue
        "base_hue": 250
    }
}
```

### 4.2 색상 토큰 생성 함수 (generate_color_tokens)
```python
def generate_color_tokens(design_system: dict) -> str:
    domain = design_system.get("domain", "tech")
    preset = DOMAIN_PRESETS.get(domain, DOMAIN_PRESETS["tech"])
    hue = preset["base_hue"]
    
    def make_scale(h, chroma_base):
        # 12단계 스케일 생성 (L: 99% -> 10%, C: 미세조정)
        steps = []
        for i in range(1, 13):
            lightness = 100 - (i * 7.5)
            chroma = chroma_base if i > 6 else chroma_base * (i / 7)
            steps.append(f"oklch({lightness}% {chroma:.3f} {h})")
        return steps

    primary_scale = make_scale(hue, 0.15)
    
    css = "@theme {\n"
    # 시맨틱 토큰 매핑
    css += f"  --color-background: oklch(98% 0.01 {hue});\n"
    css += f"  --color-foreground: oklch(15% 0.02 {hue});\n"
    css += f"  --color-card: oklch(100% 0 0);\n"
    css += f"  --color-border: oklch(90% 0.01 {hue});\n"
    
    for i, val in enumerate(primary_scale, 1):
        css += f"  --color-primary-{i}: {val};\n"
    
    css += f"  --color-primary: var(--color-primary-9);\n"
    css += f"  --color-accent: {preset['accent']};\n"
    css += "  --color-success: oklch(70% 0.15 140);\n"
    css += "  --color-warning: oklch(80% 0.15 70);\n"
    css += "  --color-error: oklch(60% 0.2 25);\n"
    css += "}\n\n"
    
    # 다크 모드 오버라이드
    css += "@layer base {\n  .dark {\n"
    css += f"    --color-background: oklch(12% 0.02 {hue});\n"
    css += f"    --color-foreground: oklch(95% 0.01 {hue});\n"
    css += f"    --color-card: oklch(18% 0.03 {hue + 5});\n"
    css += f"    --color-border: oklch(25% 0.03 {hue});\n"
    css += "  }\n}\n"
    
    return css
```

## 5. 테스트 계획
- **유닛 테스트**: `generate_color_tokens` 함수에 5개 도메인을 각각 입력하여 반환된 문자열에 필수 키워드(oklch, --color-primary-12, .dark)가 포함되어 있는지 검증
- **시각적 검증**: 생성된 `globals.css`를 실제 Next.js 프로젝트에 적용하여 색상 대비가 WCAG AA 기준을 충족하는지 확인

## 6. 검증 방법
- `pytest agent/tests/test_build_assets.py` 실행 (색상 토큰 생성 테스트 포함)
- `npx tailwindcss -i ./web/src/app/globals.css -o ./dist/output.css` 명령어로 CSS 빌드 에러 여부 확인

## 7. 롤백 계획
- 이전 버전의 정적 `globals.css` 템플릿으로 복구
- `agent/nodes/build.py`의 변경 사항을 `git checkout`으로 되돌림
