# vibeDeploy 디자인 시스템 명세서 (v1.0)

이 문서는 vibeDeploy가 생성하는 모든 애플리케이션의 시각적 품질과 일관성을 보장하기 위한 디자인 시스템 표준을 정의합니다. 본 시스템은 단순한 템플릿을 넘어, 도메인별 특성에 최적화된 고품질 UI를 자동으로 생성하는 것을 목표로 합니다.

---

## 1. OKLCH 컬러 토큰 시스템 (OKLCH Color Token System)

vibeDeploy는 지각적으로 균일한 색상 공간인 OKLCH를 사용하여 다크/라이트 모드에서 일관된 대비와 채도를 유지합니다. Radix UI의 12단계 스케일 패턴을 따릅니다.

### 1.1 시맨틱 역할 매핑
- **Background**: 앱의 기본 배경 (L: 98% / 2%)
- **Foreground**: 기본 텍스트 색상 (L: 15% / 95%)
- **Primary**: 브랜드 핵심 색상 (Step 9)
- **Accent**: 강조 및 상호작용 색상 (Step 10)
- **Card**: 카드 및 섹션 배경 (L: 100% / 18%)
- **Muted**: 보조 텍스트 및 비활성 요소 (Step 6-7)
- **Border**: 구분선 및 테두리 (Step 4-5)
- **Success/Warning/Error**: 상태 피드백 색상

### 1.2 도메인별 팔레트 프리셋
1. **Finance/Business**: `navy (oklch(25% 0.05 260))` + `gold (oklch(85% 0.15 85))`
2. **Health/Wellness**: `sage (oklch(85% 0.04 150))` + `coral (oklch(70% 0.18 25))`
3. **Creative/Art**: `deep purple (oklch(35% 0.2 290))` + `amber (oklch(80% 0.18 75))`
4. **Food/Dining**: `warm earth (oklch(30% 0.08 45))` + `vermillion (oklch(60% 0.25 35))`
5. **Tech/Dev**: `cool gray (oklch(20% 0.02 250))` + `electric blue (oklch(65% 0.25 250))`

### 1.3 globals.css 생성 파이썬 함수
```python
def generate_globals_css(design_system: dict) -> str:
    """blueprint의 design_system 정보를 바탕으로 Tailwind용 globals.css 생성"""
    colors = design_system.get("color_tokens", {})
    primary = colors.get("primary", "oklch(60% 0.2 250)")
    
    css_content = """@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
"""
    # 라이트 모드 토큰 생성
    for role, val in colors.items():
        css_content += f"    --{role}: {val};\n"
    
    # Radix 스타일 12단계 스케일 자동 계산 (간략화된 로직)
    css_content += f"    --primary-step-1: oklch(99% 0.01 250);\n"
    css_content += f"    --primary-step-9: {primary};\n"
    css_content += "    --radius: 0.75rem;\n"
    css_content += "  }\n\n  .dark {\n"
    
    # 다크 모드 반전 로직
    for role, val in colors.items():
        if role == "background": css_content += "    --background: oklch(12% 0.02 250);\n"
        elif role == "foreground": css_content += "    --foreground: oklch(98% 0.01 250);\n"
        elif role == "card": css_content += "    --card: oklch(18% 0.03 255);\n"
        else: css_content += f"    --{role}: {val};\n"
        
    css_content += "  }\n}\n"
    return css_content
```

### 1.4 출력 예시 (CSS)
```css
@layer base {
  :root {
    --background: oklch(98% 0.01 250);
    --foreground: oklch(15% 0.02 250);
    --primary: oklch(60% 0.2 250);
    --accent: oklch(70% 0.25 200);
    --card: oklch(100% 0 0);
    --border: oklch(90% 0.01 250);
  }
  .dark {
    --background: oklch(12% 0.02 250);
    --foreground: oklch(95% 0.01 250);
    --card: oklch(18% 0.02 255);
    --border: oklch(25% 0.03 250);
  }
}
```

---

## 2. 타이포그래피 시스템 (Typography System)

vibeDeploy는 가독성과 시각적 위계를 위해 정교한 타입 스케일을 사용합니다.

### 2.1 타입 스케일 정의
- **display-xl**: 4.5rem / 1.1 / -0.02em (Hero 타이틀)
- **display**: 3.75rem / 1.2 / -0.02em
- **title-1**: 2.25rem / 1.3 / -0.01em (섹션 헤더)
- **title-2**: 1.5rem / 1.4 / -0.01em
- **title-3**: 1.25rem / 1.5 / 0
- **body-lg**: 1.125rem / 1.6 / 0
- **body**: 1rem / 1.6 / 0 (본문)
- **body-sm**: 0.875rem / 1.5 / 0
- **caption**: 0.75rem / 1.4 / 0.01em (보조 정보)

### 2.2 10가지 추천 폰트 페어링 (next/font/google)
1. **Editorial**: `Playfair Display` (700) + `Inter` (400) - 매거진, 뉴스
2. **Modern SaaS**: `Geist` (800) + `Geist` (400) - 기술, 도구
3. **Elegant**: `Cormorant Garamond` (600) + `Montserrat` (400) - 럭셔리, 뷰티
4. **Tech/Dev**: `JetBrains Mono` (700) + `Inter` (400) - 개발자 도구
5. **Friendly**: `Quicksand` (700) + `Outfit` (400) - 커뮤니티, 교육
6. **Business**: `Lora` (700) + `Open Sans` (400) - 금융, 법률
7. **Creative**: `Syne` (800) + `Work Sans` (400) - 디자인, 예술
8. **Minimal**: `Space Grotesk` (700) + `Inter` (400) - 포트폴리오
9. **Classic**: `Libre Baskerville` (700) + `Source Sans 3` (400) - 아카이브
10. **Bold**: `Archivo Black` (900) + `Archivo` (400) - 스포츠, 엔터테인먼트

### 2.3 layout.tsx 생성 파이썬 함수
```python
def generate_layout_tsx(typography_config: dict) -> str:
    display_font = typography_config.get("display", "Inter")
    body_font = typography_config.get("body", "Inter")
    
    return f"""
import {{ {display_font}, {body_font} }} from 'next/font/google';

const display = {display_font}({{ 
  subsets: ['latin'], 
  variable: '--font-display',
  weight: ['700', '800'] 
}});

const body = {body_font}({{ 
  subsets: ['latin'], 
  variable: '--font-body',
  weight: ['400', '500'] 
}});

export default function RootLayout({{ children }}) {{
  return (
    <html lang="ko" className="{{`${{display.variable}} ${{body.variable}}` font-sans text-foreground bg-background"}}>
      <body className="antialiased min-h-screen flex flex-col">
        {{children}}
      </body>
    </html>
  );
}}
"""
```

---

## 3. 모션 토큰 라이브러리 (Motion Token Library)

Framer Motion을 활용하여 앱에 생동감을 불어넣습니다.

### 3.1 motion-tokens.ts 구성
```typescript
export const transitions = {
  fast: { duration: 0.15, ease: "easeOut" },
  normal: { duration: 0.25, ease: [0.22, 1, 0.36, 1] }, // outQuart
  slow: { duration: 0.4, type: "spring", stiffness: 100 },
};

export const variants = {
  fadeInUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: transitions.normal
  },
  fadeInLeft: {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
    transition: transitions.normal
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    transition: transitions.normal
  },
  staggerContainer: {
    animate: { transition: { staggerChildren: 0.1 } }
  },
  cardHover: {
    whileHover: { y: -5, scale: 1.02, transition: transitions.fast },
    whileTap: { scale: 0.98 }
  },
  skeletonPulse: {
    animate: { 
      opacity: [0.4, 0.7, 0.4],
      transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" }
    }
  }
};
```

### 3.2 컴포넌트 적용 예시
```tsx
<motion.div 
  variants={variants.staggerContainer}
  initial="initial"
  animate="animate"
  className="grid grid-cols-1 md:grid-cols-3 gap-6"
>
  {items.map(item => (
    <motion.div key={item.id} variants={variants.fadeInUp} {...variants.cardHover}>
      <Card className="p-6 border bg-card rounded-xl shadow-sm">
        <h3 className="text-title-3 font-display">{item.title}</h3>
        <p className="text-body-sm text-muted mt-2">{item.description}</p>
      </Card>
    </motion.div>
  ))}
</motion.div>
```

---

## 4. 레이아웃 아키타입 시스템 (Layout Archetype System)

도메인 목적에 맞는 8가지 레이아웃 구조를 제공합니다.

### 4.1 아키타입 정의
1. **storyboard**: 매거진 스타일. `grid-cols-12` 기반 비대칭 레이아웃.
2. **operations_console**: 대시보드 스타일. `flex h-screen` + `aside` + `main`.
3. **studio**: 창작 도구 스타일. 중앙 캔버스 + 양측 툴바 패널.
4. **atlas**: 지도/데이터 중심. `h-screen` 전체 화면 + 플로팅 UI.
5. **notebook**: 문서 중심. `max-w-3xl mx-auto` 단일 컬럼 스크롤.
6. **lab**: 실험실 스타일. `grid-cols-4` 메트릭 카드 + 대형 차트 영역.
7. **creator-shell**: 콘텐츠 생성 집중. 상단 툴바 + 중앙 에디터 영역.
8. **marketplace**: 커머스 스타일. 좌측 필터(`w-64`) + 우측 상품 그리드.

### 4.2 아키타입 생성 파이썬 함수
```python
def generate_page_structure(archetype: str) -> str:
    layouts = {
        "operations_console": """
<div className="flex h-screen overflow-hidden bg-background">
  <aside className="w-64 border-r bg-card/50 hidden lg:block">
    <SidebarNav />
  </aside>
  <div className="flex-1 flex flex-col overflow-hidden">
    <header className="h-16 border-b flex items-center px-6 bg-background/80 backdrop-blur">
      <GlobalSearch />
    </header>
    <main className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-8">{children}</div>
    </main>
  </div>
</div>""",
        "storyboard": """
<div className="min-h-screen bg-background p-4 md:p-12">
  <div className="grid grid-cols-1 md:grid-cols-12 gap-8 max-w-[1600px] mx-auto">
    <header className="md:col-span-12 mb-12"><Logo /></header>
    <section className="md:col-span-8 space-y-12">{main_content}</section>
    <aside className="md:col-span-4 space-y-8">{sidebar_content}</aside>
  </div>
</div>"""
    }
    return layouts.get(archetype, "<div>{children}</div>")
```

---

## 5. 컴포넌트 품질 표준 (Component Quality Standards)

vibeDeploy가 생성하는 모든 컴포넌트는 다음 기준을 충족해야 합니다.

### 5.1 품질 정의
- **Hero**: 명확한 시각적 계층 구조, 강력한 CTA, 배경 블러 또는 그라디언트 처리 필수.
- **Data Display**: 데이터 로딩 시 Skeleton UI 제공, 데이터 없을 시 Empty State 디자인 포함.
- **Forms**: 인라인 유효성 검사, 명확한 에러 메시지, 제출 중 로딩 상태 표시.
- **Cards**: 호버 시 미세한 리프트 효과(`shadow-lg`), 포커스 링(`ring-primary`).

### 5.2 안티 패턴 체크리스트 (Anti-patterns)
- [ ] 평면적인 순수 흰색 배경 (`bg-white` 대신 `bg-background` 사용)
- [ ] 회색조의 단조로운 카드 그리드 (그라디언트 보더 또는 미세한 틴트 추가)
- [ ] 의미 없는 "Lorem Ipsum" 텍스트 (도메인 맞춤형 텍스트 생성 필수)
- [ ] "Item 1, Item 2" 식의 무성의한 더미 데이터
- [ ] 3개의 기능 카드만 있는 전형적인 랜딩 페이지 (다양한 섹션 구성 권장)

---

## 6. 시드 데이터 생성 (Seed Data Generation)

도메인에 특화된 현실적인 데이터를 생성하여 앱의 완성도를 높입니다.

### 6.1 도메인 데이터 생성 함수
```python
def generate_seed_data(domain: str, count: int = 5) -> list:
    """도메인별 현실적인 JSON 데이터 생성 (LLM 프롬프트 기반)"""
    # 실제 구현에서는 도메인별 팩토리 로직 실행
    data_map = {
        "recipe": [{"id": "1", "name": "트러플 오일 파스타", "difficulty": "중급", "time": "20분"}],
        "project": [{"id": "1", "task": "UI 디자인 시스템 구축", "status": "진행중", "priority": "높음"}],
        "analytics": [{"id": "1", "metric": "일일 활성 사용자", "value": "1,240", "trend": "+12%"}]
    }
    return data_map.get(domain, [{"id": "1", "title": "샘플 데이터"}])
```

### 6.2 도메인별 예시
- **Recipe App**: "지중해식 연어 스테이크", "비건 렌틸콩 수프" (재료, 조리법 포함)
- **Project Manager**: "Q2 마케팅 캠페인 기획", "API 보안 취약점 점검" (담당자, 마감일 포함)
- **Analytics**: "사용자 유지율(Retention) 분석", "서버 응답 시간 모니터링" (수치 데이터 포함)
