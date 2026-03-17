# Task 134: 레이아웃 아키타입 강화
상태: 미구현 | Phase 3 | 예상 시간: 5h
의존성: 112, 131, 132, 133

## 1. 태스크 정의
vibeDeploy가 생성하는 앱의 구조적 완성도를 높이기 위해 도메인 목적에 최적화된 8가지 레이아웃 아키타입을 구축합니다. 각 아키타입은 CSS Grid/Flexbox를 활용한 반응형 구조를 포함하며, `blueprint.design_system.visual_direction` 키워드 매칭을 통해 자동으로 선택됩니다.

## 2. 수용 기준 (Acceptance Criteria)
- [ ] AC-1: 8개 아키타입(storyboard, operations_console, studio, atlas, notebook, lab, creator_shell, marketplace) 정의
- [ ] AC-2: 각 아키타입별로 유효한 CSS Grid/Flexbox 정의 및 모바일 반응형(768px 중단점) 포함
- [ ] AC-3: `blueprint` 키워드 매칭을 통한 아키타입 선택 로직 구현
- [ ] AC-4: `page.tsx`의 기본 구조를 선택된 아키타입 기반으로 생성
- [ ] AC-5: 생성된 JSX 구조가 유효한 TSX 구문을 따름

## 3. 변경 대상 파일
- `agent/nodes/build.py`: `select_archetype`, `generate_page_structure` 함수 추가
- `web/src/app/page.tsx`: 생성된 레이아웃 구조가 주입될 대상 파일

## 4. 상세 구현

### 4.1 아키타입 설정 (ARCHETYPE_CONFIGS)
```python
ARCHETYPE_CONFIGS = {
    "operations_console": {
        "css": "flex h-screen overflow-hidden bg-background",
        "structure": """
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
</div>"""
    },
    "storyboard": {
        "css": "min-h-screen bg-background p-4 md:p-12",
        "structure": """
<div className="min-h-screen bg-background p-4 md:p-12">
  <div className="grid grid-cols-1 md:grid-cols-12 gap-8 max-w-[1600px] mx-auto">
    <header className="md:col-span-12 mb-12"><Logo /></header>
    <section className="md:col-span-8 space-y-12">{main_content}</section>
    <aside className="md:col-span-4 space-y-8">{sidebar_content}</aside>
  </div>
</div>"""
    },
    # ... 나머지 6개 아키타입 설정 (studio, atlas, notebook, lab, creator_shell, marketplace)
}
```

### 4.2 아키타입 선택 및 페이지 생성
```python
def select_archetype(visual_direction: str) -> str:
    mapping = {
        "dashboard": "operations_console",
        "magazine": "storyboard",
        "tool": "studio",
        "map": "atlas",
        "document": "notebook",
        "analytics": "lab",
        "editor": "creator_shell",
        "shop": "marketplace"
    }
    return mapping.get(visual_direction.lower(), "operations_console")

def generate_page_structure(archetype_id: str) -> str:
    config = ARCHETYPE_CONFIGS.get(archetype_id, ARCHETYPE_CONFIGS["operations_console"])
    return config["structure"]
```

## 5. 테스트 계획
- **유닛 테스트**: 8개 아키타입 ID를 각각 입력하여 `generate_page_structure`가 유효한 문자열을 반환하는지 확인
- **반응형 검증**: 생성된 CSS 클래스에 `md:`, `lg:`, `hidden` 등 반응형 접두사가 포함되어 있는지 확인

## 6. 검증 방법
- `web/src/app/page.tsx`에 생성된 구조를 주입하고, 브라우저에서 화면 크기를 조절하며 레이아웃이 의도한 대로 변하는지 확인
- `npx tailwindcss` 빌드 시 사용된 모든 레이아웃 클래스가 정상적으로 추출되는지 확인

## 7. 롤백 계획
- 기본 `max-w-7xl mx-auto` 단일 컬럼 레이아웃으로 복구
- `agent/nodes/build.py`의 아키타입 생성 로직 비활성화
