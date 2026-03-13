from __future__ import annotations

from typing import Any


def coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for entry in value:
        text = str(entry or "").strip()
        if text:
            items.append(text)
    return items


def derive_execution_tasks(idea: dict | None, flagship_contract: dict | None = None) -> list[dict[str, str]]:
    source = dict(idea or {})
    contract = dict(flagship_contract or {})
    tasks: list[dict[str, str]] = []

    for idx, item in enumerate(
        coerce_string_list(source.get("reference_objects")) or coerce_string_list(contract.get("required_objects")),
        start=1,
    ):
        tasks.append(
            {
                "id": f"ui-{idx}",
                "kind": "ui_object",
                "title": item,
                "target": "frontend",
                "success_signal": f"{item} is visible and named clearly in the product",
                "priority": "high",
            }
        )

    for idx, item in enumerate(
        coerce_string_list(source.get("output_entities")) or coerce_string_list(contract.get("required_results")),
        start=1,
    ):
        tasks.append(
            {
                "id": f"artifact-{idx}",
                "kind": "output_artifact",
                "title": item,
                "target": "frontend+backend",
                "success_signal": f"{item} is generated as a concrete user-visible result",
                "priority": "high",
            }
        )

    for idx, item in enumerate(
        coerce_string_list(source.get("acceptance_checks")) or coerce_string_list(contract.get("acceptance_checks")),
        start=1,
    ):
        tasks.append(
            {
                "id": f"acceptance-{idx}",
                "kind": "acceptance",
                "title": item,
                "target": "evaluation",
                "success_signal": item,
                "priority": "medium",
            }
        )

    return dedupe_tasks(tasks)


def build_task_distribution(tasks: list[dict[str, str]]) -> dict[str, Any]:
    by_target: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for task in tasks:
        target = str(task.get("target") or "unassigned")
        kind = str(task.get("kind") or "generic")
        by_target[target] = by_target.get(target, 0) + 1
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "total": len(tasks),
        "by_target": by_target,
        "by_kind": by_kind,
    }


def build_repair_tasks_from_fixes(fixes: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for idx, fix in enumerate(fixes or [], start=1):
        axis = str((fix or {}).get("axis") or "quality").strip() or "quality"
        description = str((fix or {}).get("fix_description") or "Refine the weak area.").strip()
        expected = str((fix or {}).get("expected_improvement") or "Raise score and reduce blocker risk.").strip()
        tasks.append(
            {
                "id": f"repair-{idx}",
                "kind": "repair",
                "title": description,
                "target": axis,
                "success_signal": expected,
                "priority": "high",
            }
        )
    return dedupe_tasks(tasks)


def build_repair_tasks_from_eval(eval_result: dict | None) -> list[dict[str, str]]:
    result = dict(eval_result or {})
    tasks: list[dict[str, str]] = []

    for idx, file_name in enumerate(result.get("missing_frontend") or [], start=1):
        tasks.append(
            {
                "id": f"missing-fe-{idx}",
                "kind": "repair",
                "title": f"Add missing frontend file: {file_name}",
                "target": "frontend",
                "success_signal": f"{file_name} exists and matches the blueprint contract",
                "priority": "high",
            }
        )

    for idx, file_name in enumerate(result.get("missing_backend") or [], start=1):
        tasks.append(
            {
                "id": f"missing-be-{idx}",
                "kind": "repair",
                "title": f"Add missing backend file: {file_name}",
                "target": "backend",
                "success_signal": f"{file_name} exists and matches the blueprint contract",
                "priority": "high",
            }
        )

    for idx, blocker in enumerate(result.get("blockers") or [], start=1):
        tasks.append(
            {
                "id": f"blocker-{idx}",
                "kind": "repair",
                "title": str(blocker).strip(),
                "target": "quality_gate",
                "success_signal": f"The blocker '{blocker}' no longer appears in evaluation",
                "priority": "high",
            }
        )

    fidelity = result.get("artifact_fidelity") if isinstance(result.get("artifact_fidelity"), dict) else {}
    for idx, miss in enumerate(fidelity.get("required_result_misses") or [], start=1):
        tasks.append(
            {
                "id": f"artifact-result-{idx}",
                "kind": "repair",
                "title": f"Materialize result artifact: {miss}",
                "target": "frontend+backend",
                "success_signal": f"{miss} appears as a concrete generated result",
                "priority": "high",
            }
        )
    for idx, miss in enumerate(fidelity.get("required_object_misses") or [], start=1):
        tasks.append(
            {
                "id": f"artifact-object-{idx}",
                "kind": "repair",
                "title": f"Materialize visible object: {miss}",
                "target": "frontend",
                "success_signal": f"{miss} is visibly represented in the UI",
                "priority": "medium",
            }
        )

    return dedupe_tasks(tasks)


def dedupe_tasks(tasks: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for task in tasks:
        title = str(task.get("title") or "").strip()
        target = str(task.get("target") or "").strip()
        key = (title.lower(), target.lower())
        if not title or key in seen:
            continue
        seen.add(key)
        deduped.append(task)
    return deduped
