# Task 133: Framer Motion 토큰 라이브러리
상태: 미구현 | Phase 3 | 예상 시간: 3h
의존성: 112 (결정론적 스캐폴드)

## 1. 태스크 정의
vibeDeploy가 생성하는 앱에 생동감과 전문성을 더하기 위해 `Framer Motion` 기반의 모션 토큰 라이브러리를 구축합니다. 도메인별 모션 강도(Intensity)를 조절하고, 재사용 가능한 애니메이션 변수(Variants)를 `motion-tokens.ts` 파일로 자동 생성합니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 유효한 TypeScript 파일(`motion-tokens.ts`) 생성 및 Named Exports 제공
- [ ] AC-2: 3단계 Duration(fast, normal, slow) 및 Easing(outExpo, outQuart, spring) 정의
- [ ] AC-3: 10개 이상의 Pre-built Variants(fadeInUp, staggerContainer, cardHover 등) 포함
- [ ] AC-4: 도메인별 모션 강도(editorial: subtle, dashboard: snappy, creative: dramatic) 적용
- [ ] AC-5: `framer-motion` 라이브러리와의 완벽한 호환성 보장

## 3. 변경 대상 파일
- `agent/nodes/build.py`: `generate_motion_tokens` 함수 추가
- `web/src/lib/motion-tokens.ts`: 생성된 모션 토큰이 저장될 대상 파일

## 4. 상세 구현

### 4.1 도메인별 모션 강도 (MOTION_INTENSITY)
```python
MOTION_INTENSITY = {
    "editorial": {"duration_scale": 1.2, "stagger": 0.15, "ease": "easeOut"},
    "dashboard": {"duration_scale": 0.8, "stagger": 0.05, "ease": [0.22, 1, 0.36, 1]},
    "creative": {"duration_scale": 1.5, "stagger": 0.2, "ease": [0.16, 1, 0.3, 1]},
    "default": {"duration_scale": 1.0, "stagger": 0.1, "ease": "easeInOut"}
}
```

### 4.2 모션 토큰 생성 함수 (generate_motion_tokens)
```python
def generate_motion_tokens(design_system: dict) -> str:
    visual_dir = design_system.get("visual_direction", "dashboard")
    intensity = MOTION_INTENSITY.get(visual_dir, MOTION_INTENSITY["default"])
    ds = intensity["duration_scale"]
    
    return f"""
import {{ Variants }} from 'framer-motion';

export const transitions = {{
  fast: {{ duration: {0.15 * ds}, ease: "{intensity['ease']}" }},
  normal: {{ duration: {0.25 * ds}, ease: {intensity['ease']} }},
  slow: {{ duration: {0.4 * ds}, type: "spring", stiffness: 100 }},
}};

export const variants: Record<string, Variants> = {{
  fadeInUp: {{
    initial: {{ opacity: 0, y: 20 }},
    animate: {{ opacity: 1, y: 0 }},
    transition: transitions.normal
  }},
  fadeInDown: {{
    initial: {{ opacity: 0, y: -20 }},
    animate: {{ opacity: 1, y: 0 }},
    transition: transitions.normal
  }},
  fadeInLeft: {{
    initial: {{ opacity: 0, x: -20 }},
    animate: {{ opacity: 1, x: 0 }},
    transition: transitions.normal
  }},
  scaleIn: {{
    initial: {{ opacity: 0, scale: 0.95 }},
    animate: {{ opacity: 1, scale: 1 }},
    transition: transitions.normal
  }},
  staggerContainer: {{
    animate: {{ transition: {{ staggerChildren: {intensity['stagger']} }} }}
  }},
  staggerItem: {{
    initial: {{ opacity: 0, y: 10 }},
    animate: {{ opacity: 1, y: 0 }}
  }},
  pageTransition: {{
    initial: {{ opacity: 0, x: 10 }},
    animate: {{ opacity: 1, x: 0 }},
    exit: {{ opacity: 0, x: -10 }}
  }},
  cardHover: {{
    whileHover: {{ y: -5, scale: 1.02, transition: transitions.fast }},
    whileTap: {{ scale: 0.98 }}
  }},
  buttonPress: {{
    whileTap: {{ scale: 0.95 }}
  }},
  skeletonPulse: {{
    animate: {{ 
      opacity: [0.4, 0.7, 0.4],
      transition: {{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
    }}
  }}
}};
"""
```

## 5. 테스트 계획
- **유닛 테스트**: `generate_motion_tokens` 함수가 반환하는 문자열이 유효한 TypeScript 구문인지 확인
- **강도 검증**: `editorial`과 `dashboard` 입력 시 `duration` 값이 의도한 대로 다르게 생성되는지 비교 테스트

## 6. 검증 방법
- `web/src/lib/motion-tokens.ts` 파일을 생성하고, 다른 컴포넌트에서 `import { variants } from '@/lib/motion-tokens'`로 정상적으로 불러와지는지 확인
- `framer-motion`의 `motion.div`에 `variants={variants.fadeInUp}`을 적용하여 애니메이션 동작 확인

## 7. 롤백 계획
- 정적인 `motion-tokens.ts` 기본 파일로 복구
- `agent/nodes/build.py`의 모션 생성 로직 비활성화
