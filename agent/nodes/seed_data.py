import json

_RECIPE_NAMES = [
    "지중해식 연어 스테이크",
    "트러플 크림 파스타",
    "아보카도 퀴노아 샐러드",
    "한우 불고기 덮밥",
    "새우 감바스 알 아히요",
    "태국식 팟타이",
    "구운 치킨 시저 샐러드",
    "매콤 해물 짬뽕",
    "바질 페스토 피자",
    "차슈 라멘",
]

_RECIPE_DIFFICULTIES = ["초급", "중급", "상급"]
_RECIPE_TIMES = ["15분", "20분", "30분", "45분", "1시간"]

_PROJECT_TASKS = [
    "UI 디자인 시스템 구축",
    "API 보안 점검 및 강화",
    "마케팅 캠페인 기획",
    "데이터베이스 마이그레이션",
    "성능 최적화 프로젝트",
    "사용자 피드백 분석",
    "CI/CD 파이프라인 개선",
    "모바일 앱 프로토타입",
    "결제 시스템 통합",
    "문서화 자동화 도구",
]
_PROJECT_STATUSES = ["진행중", "검토중", "완료", "대기중"]
_PROJECT_PRIORITIES = ["높음", "중간", "낮음"]

_ANALYTICS_METRICS = [
    ("일일 활성 사용자", 12847, "명", 12.3),
    ("월간 활성 사용자", 89234, "명", 8.7),
    ("서버 응답 시간", 142, "ms", -5.2),
    ("전환율", 3.8, "%", 0.4),
    ("이탈률", 28.5, "%", -2.1),
    ("세션 지속 시간", 272, "초", 15.8),
    ("페이지 뷰", 342567, "", 22.1),
    ("신규 가입", 1205, "명", 18.4),
    ("결제 완료율", 67.3, "%", 3.2),
    ("고객 만족도", 4.6, "/5.0", 0.2),
]

_SOCIAL_CONTENTS = [
    "오늘의 코딩 챌린지를 완료했습니다! 알고리즘 실력이 늘고 있어요.",
    "새로운 프로젝트 아이디어가 떠올랐습니다. AI 기반 레시피 추천 앱은 어떨까요?",
    "주말 하이킹으로 북한산 정상에 다녀왔습니다. 서울의 전경이 장관이에요.",
    "TypeScript로 전환한 지 한 달, 타입 안전성의 가치를 절실히 느끼고 있습니다.",
    "팀 스프린트 회고를 마쳤습니다. 이번 주 배포 성공률 98%!",
    "카페에서 사이드 프로젝트 작업 중. 집중이 잘 되는 날이에요.",
    "오픈소스 기여 첫 PR이 머지됐습니다! 작은 시작이지만 의미 있네요.",
    "운동 100일 챌린지 60일차. 매일 5km 러닝 기록 갱신 중!",
    "디자인 시스템을 구축하면서 일관성의 중요성을 다시 한번 깨달았습니다.",
    "읽고 있는 책: '클린 아키텍처'. 소프트웨어 설계에 대한 시야가 넓어졌어요.",
]

_ECOMMERCE_PRODUCTS = [
    ("소니 WH-1000XM5 무선 헤드폰", 389000, 45, "오디오"),
    ("로지텍 MX Keys S 키보드", 149000, 128, "키보드"),
    ("애플 에어팟 프로 2세대", 329000, 67, "오디오"),
    ("삼성 갤럭시 탭 S9", 899000, 23, "태블릿"),
    ("레이저 DeathAdder V3 마우스", 89000, 234, "마우스"),
    ("벤큐 SW272U 모니터", 1290000, 12, "모니터"),
    ("앱스 아이패드 거치대", 45000, 567, "액세서리"),
    ("코세어 K70 RGB 키보드", 179000, 89, "키보드"),
    ("JBL Charge 5 블루투스 스피커", 189000, 156, "오디오"),
    ("엘가토 Stream Deck MK.2", 169000, 78, "스트리밍"),
]


def _gen_recipe(count: int) -> list[dict]:
    n = len(_RECIPE_NAMES)
    data = []
    for i in range(count):
        cycle = i // n
        name = _RECIPE_NAMES[i % n]
        suffix = f" (시즌 {cycle + 2})" if cycle > 0 else ""
        data.append(
            {
                "id": str(i + 1),
                "name": f"{name}{suffix}",
                "difficulty": _RECIPE_DIFFICULTIES[i % len(_RECIPE_DIFFICULTIES)],
                "time": _RECIPE_TIMES[i % len(_RECIPE_TIMES)],
                "servings": 2 + (i % 4),
                "rating": round(4.0 + (i % 10) * 0.1, 1),
            }
        )
    return data


def _gen_project(count: int) -> list[dict]:
    n = len(_PROJECT_TASKS)
    data = []
    for i in range(count):
        cycle = i // n
        task = _PROJECT_TASKS[i % n]
        suffix = f" Phase {cycle + 2}" if cycle > 0 else ""
        data.append(
            {
                "id": str(i + 1),
                "task": f"{task}{suffix}",
                "status": _PROJECT_STATUSES[i % len(_PROJECT_STATUSES)],
                "priority": _PROJECT_PRIORITIES[i % len(_PROJECT_PRIORITIES)],
                "progress": min(100, (i * 15) % 105),
                "assignee": f"팀원 {chr(65 + i % 8)}",
            }
        )
    return data


def _gen_analytics(count: int) -> list[dict]:
    n = len(_ANALYTICS_METRICS)
    data = []
    for i in range(count):
        metric, value_raw, unit, trend_pct = _ANALYTICS_METRICS[i % n]
        multiplier = 1 + (i // n) * 0.05 if i >= n else 1
        adjusted = round(value_raw * multiplier, 2) if isinstance(value_raw, float) else int(value_raw * multiplier)
        data.append(
            {
                "id": str(i + 1),
                "metric": metric,
                "value_raw": adjusted,
                "value_display": f"{adjusted:,}{unit}",
                "trend_pct": round(trend_pct + (i // n) * 0.3, 1),
                "period": "최근 30일",
            }
        )
    return data


def _gen_social(count: int) -> list[dict]:
    n = len(_SOCIAL_CONTENTS)
    data = []
    for i in range(count):
        cycle = i // n
        day = 10 + i % 20
        month = 3 + cycle
        if month > 12:
            month = ((month - 1) % 12) + 1
        data.append(
            {
                "id": str(i + 1),
                "user": f"사용자_{1000 + i}",
                "content": _SOCIAL_CONTENTS[i % n],
                "likes": 5 + i * 7,
                "comments": 1 + i * 2,
                "created_at": f"2025-{month:02d}-{day:02d}T{8 + i % 14:02d}:00:00Z",
            }
        )
    return data


def _gen_ecommerce(count: int) -> list[dict]:
    n = len(_ECOMMERCE_PRODUCTS)
    data = []
    for i in range(count):
        product, base_price, base_stock, category = _ECOMMERCE_PRODUCTS[i % n]
        price_jitter = (i // n) * 1000 * ((-1) ** i)
        data.append(
            {
                "id": str(i + 1),
                "product": product if i < n else f"{product} (v{1 + i // n})",
                "price": max(1000, base_price + price_jitter),
                "stock": max(0, base_stock - (i // n) * 3),
                "rating": round(4.0 + (i % 10) * 0.1, 1),
                "category": category,
            }
        )
    return data


DOMAIN_GENERATORS = {
    "recipe": _gen_recipe,
    "project": _gen_project,
    "analytics": _gen_analytics,
    "social": _gen_social,
    "ecommerce": _gen_ecommerce,
}


def generate_seed_data(domain: str, count: int = 10) -> list[dict]:
    generator = DOMAIN_GENERATORS.get(domain, DOMAIN_GENERATORS["project"])
    return generator(max(1, count))


def to_typescript_const(data: list[dict], name: str) -> str:
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    return f"export const {name} = {json_str} as const;\n"
