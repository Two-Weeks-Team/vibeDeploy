import csv
import logging
import time
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_EVAL_DIR = Path(__file__).parent


class TestCase(BaseModel):
    id: int
    category: str
    input: str
    expected_behavior: str
    quality_criteria: str


class EvalResult(BaseModel):
    test_case_id: int
    category: str
    quality_criteria: str
    passed: bool
    score: float = 0.0
    details: str = ""
    duration_seconds: float = 0.0


class EvalSummary(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    by_criteria: dict[str, dict] = {}
    by_category: dict[str, dict] = {}
    timestamp: str = ""


def load_test_cases(path: Path | None = None) -> list[TestCase]:
    csv_path = path or (_EVAL_DIR / "test_cases.csv")
    if not csv_path.exists():
        logger.warning("[Eval] test_cases.csv not found at %s", csv_path)
        return []

    cases: list[TestCase] = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cases.append(
                TestCase(
                    id=int(row["id"]),
                    category=row["category"],
                    input=row["input"],
                    expected_behavior=row["expected_behavior"],
                    quality_criteria=row["quality_criteria"],
                )
            )
    return cases


def compute_summary(results: list[EvalResult]) -> EvalSummary:
    if not results:
        return EvalSummary(timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    scores = [r.score for r in results if r.score > 0]

    by_criteria: dict[str, dict] = {}
    for r in results:
        key = r.quality_criteria
        if key not in by_criteria:
            by_criteria[key] = {"total": 0, "passed": 0}
        by_criteria[key]["total"] += 1
        if r.passed:
            by_criteria[key]["passed"] += 1

    by_category: dict[str, dict] = {}
    for r in results:
        key = r.category
        if key not in by_category:
            by_category[key] = {"total": 0, "passed": 0}
        by_category[key]["total"] += 1
        if r.passed:
            by_category[key]["passed"] += 1

    return EvalSummary(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=round(passed / total * 100, 1) if total > 0 else 0.0,
        avg_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
        by_criteria=by_criteria,
        by_category=by_category,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
