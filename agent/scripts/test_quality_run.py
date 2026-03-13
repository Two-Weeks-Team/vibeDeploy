"""Run 2 pipelines end-to-end and analyze generated code quality + uniqueness."""

from __future__ import annotations

import asyncio
import json
import re
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(AGENT_DIR / ".env.test")

PROMPTS = [
    {
        "id": "habit-tracker",
        "prompt": (
            "Build a habit tracker web app with streak visualization and daily reminders. "
            "Users create habits (e.g. exercise, reading, meditation), check them off daily, "
            "and see their streak count and a heatmap calendar. Includes a statistics page "
            "showing completion rates, longest streaks, and weekly trends. "
            "The AI generates personalized habit suggestions based on user goals."
        ),
    },
    {
        "id": "recipe-community",
        "prompt": (
            "Build a recipe sharing community with AI-powered ingredient substitution suggestions. "
            "Users browse, search, and save recipes by cuisine type. Each recipe page shows "
            "ingredients, step-by-step instructions, nutrition info, and user ratings. "
            "The AI can suggest ingredient substitutions for dietary restrictions (vegan, "
            "gluten-free, etc.) and generate meal plans based on available pantry items."
        ),
    },
]


def _parse_sse_event(line: str) -> dict | None:
    if not line.startswith("data: "):
        return None
    try:
        return json.loads(line[6:])
    except json.JSONDecodeError:
        return None


async def run_pipeline(prompt_config: dict) -> dict:
    from agent.pipeline_runtime import stream_action_session

    thread_id = f"quality-{prompt_config['id']}-{uuid.uuid4().hex[:6]}"
    payload = {
        "action": "evaluate",
        "thread_id": thread_id,
        "prompt": prompt_config["prompt"],
    }

    summary = {
        "id": prompt_config["id"],
        "thread_id": thread_id,
        "verdict": None,
        "deployment": None,
        "code_eval_results": [],
        "code_files": [],
        "errors": [],
        "phases": [],
        "duration_sec": 0.0,
    }

    started_at = time.time()
    print(f"\n{'=' * 70}")
    print(f"PIPELINE: {prompt_config['id']} | thread_id={thread_id}")
    print(f"Prompt: {prompt_config['prompt'][:100]}...")
    print(f"{'=' * 70}")

    try:
        async for chunk in stream_action_session(payload):
            for line in str(chunk).splitlines():
                event = _parse_sse_event(line)
                if not event:
                    continue

                event_type = event.get("type", "")
                elapsed = f"[{time.time() - started_at:.0f}s]"

                if "node.start" in event_type:
                    node = event.get("node", "")
                    print(f"  {elapsed} START {node}: {event.get('message', '')}")
                elif "node.complete" in event_type:
                    node = event.get("node", "")
                    print(f"  {elapsed} DONE  {node}")
                    summary["phases"].append(node)
                elif "agent.analysis" in event_type:
                    agent = event.get("agent", "")
                    score = event.get("score", 0)
                    print(f"  {elapsed} AGENT {agent}: score={score}")
                elif event_type == "council.verdict":
                    summary["verdict"] = {
                        "final_score": event.get("final_score"),
                        "decision": event.get("decision"),
                    }
                    print(f"  {elapsed} VERDICT: {event.get('decision')} (score={event.get('final_score')})")
                elif event_type == "code_eval.result":
                    eval_data = {
                        "iteration": event.get("iteration"),
                        "passed": event.get("passed"),
                        "match_rate": event.get("match_rate"),
                        "completeness": event.get("completeness"),
                        "consistency": event.get("consistency"),
                        "runnability": event.get("runnability"),
                        "blockers": event.get("blockers", []),
                    }
                    summary["code_eval_results"].append(eval_data)
                    status = "PASS" if eval_data["passed"] else "FAIL"
                    print(
                        f"  {elapsed} CODE_EVAL iter={eval_data['iteration']} {status} "
                        f"match={eval_data['match_rate']} blockers={eval_data['blockers']}"
                    )
                elif event_type == "code_gen.complete":
                    fe = event.get("frontend_files", 0)
                    be = event.get("backend_files", 0)
                    print(f"  {elapsed} CODE_GEN frontend={fe} backend={be}")
                elif event_type == "deploy.complete":
                    summary["deployment"] = {
                        "live_url": event.get("live_url", ""),
                        "github_repo": event.get("github_repo", ""),
                        "status": event.get("status", ""),
                        "local_app_dir": event.get("local_app_dir", ""),
                    }
                    print(f"  {elapsed} DEPLOY: status={event.get('status')} repo={event.get('github_repo', '')}")
                elif event_type == "session.completed":
                    result = event.get("result") if isinstance(event.get("result"), dict) else {}
                    summary["code_files"] = result.get("code_files", [])
                elif "error" in event_type:
                    err = str(event.get("error", ""))[:300]
                    summary["errors"].append(err)
                    print(f"  {elapsed} ERROR: {err[:150]}")

    except Exception as exc:
        summary["errors"].append(str(exc)[:500])
        print(f"  EXCEPTION: {exc}")

    summary["duration_sec"] = round(time.time() - started_at, 1)
    print(
        f"\n  RESULT: verdict={summary['verdict']} deploy={summary.get('deployment')} duration={summary['duration_sec']}s"
    )
    return summary


def analyze_code_quality(summary: dict) -> dict:
    from agent.nodes.code_evaluator import _check_content_depth

    code_files = summary.get("code_files", [])
    frontend_code = {}
    backend_code = {}
    for f in code_files:
        if f.get("source") == "frontend":
            frontend_code[f["path"]] = f.get("content", "")
        elif f.get("source") == "backend":
            backend_code[f["path"]] = f.get("content", "")

    depth = _check_content_depth(frontend_code, backend_code) if (frontend_code or backend_code) else {}

    all_code = "\n".join(f.get("content", "") for f in code_files)
    unique_identifiers = set(re.findall(r"(?:function|const|class|def|export)\s+(\w+)", all_code))

    return {
        "id": summary["id"],
        "frontend_file_count": len(frontend_code),
        "backend_file_count": len(backend_code),
        "total_code_lines": sum(len((f.get("content") or "").splitlines()) for f in code_files),
        "content_depth": depth,
        "unique_identifiers_count": len(unique_identifiers),
        "unique_identifiers_sample": sorted(list(unique_identifiers))[:20],
        "has_errors": bool(summary.get("errors")),
        "final_eval_passed": (summary["code_eval_results"][-1]["passed"] if summary["code_eval_results"] else False),
        "deployed": bool(summary.get("deployment", {}).get("github_repo")),
    }


def compare_uniqueness(analyses: list[dict]) -> dict:
    if len(analyses) < 2:
        return {"unique": True, "overlap_ratio": 0.0}

    ids_a = set(analyses[0].get("unique_identifiers_sample", []))
    ids_b = set(analyses[1].get("unique_identifiers_sample", []))
    overlap = ids_a & ids_b
    union = ids_a | ids_b
    overlap_ratio = len(overlap) / max(len(union), 1)

    common_boilerplate = {"default", "Home", "Page", "app", "router", "main", "get", "post", "useState", "useEffect"}
    meaningful_overlap = overlap - common_boilerplate

    return {
        "unique": overlap_ratio < 0.5,
        "overlap_ratio": round(overlap_ratio, 3),
        "overlapping_identifiers": sorted(list(overlap)),
        "meaningful_overlap": sorted(list(meaningful_overlap)),
        "unique_to_a": sorted(list(ids_a - ids_b))[:10],
        "unique_to_b": sorted(list(ids_b - ids_a))[:10],
    }


async def main():
    print("=" * 70)
    print("vibeDeploy E2E Quality Test — 2 Pipeline Runs")
    print("=" * 70)

    summaries = []
    for prompt_config in PROMPTS:
        result = await run_pipeline(prompt_config)
        summaries.append(result)

    print(f"\n\n{'=' * 70}")
    print("QUALITY ANALYSIS")
    print(f"{'=' * 70}")

    analyses = []
    for summary in summaries:
        analysis = analyze_code_quality(summary)
        analyses.append(analysis)
        print(f"\n--- {analysis['id']} ---")
        print(f"  Frontend files: {analysis['frontend_file_count']}")
        print(f"  Backend files:  {analysis['backend_file_count']}")
        print(f"  Total lines:    {analysis['total_code_lines']}")
        print(f"  Eval passed:    {analysis['final_eval_passed']}")
        print(f"  Deployed:       {analysis['deployed']}")
        depth = analysis.get("content_depth", {})
        if depth:
            print(f"  Depth score:    {depth.get('depth_score', 'N/A')}")
            print(f"  Shallow hits:   {depth.get('shallow_patterns_found', [])}")
            print(f"  API endpoints:  {depth.get('unique_api_endpoints', 0)}")
            print(f"  Has seed data:  {depth.get('has_seed_data', False)}")
            print(f"  Domain logic:   {depth.get('has_domain_logic', False)}")
        if summary.get("errors"):
            print(f"  ERRORS:         {summary['errors'][:3]}")

    uniqueness = compare_uniqueness(analyses)
    print("\n--- UNIQUENESS ---")
    print(f"  Unique:             {uniqueness['unique']}")
    print(f"  Overlap ratio:      {uniqueness['overlap_ratio']}")
    print(f"  Meaningful overlap: {uniqueness.get('meaningful_overlap', [])}")

    output_path = "/tmp/vibedeploy-quality-test.json"
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "summaries": summaries,
        "analyses": analyses,
        "uniqueness": uniqueness,
    }
    for s in output["summaries"]:
        s.pop("code_files", None)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to {output_path}")

    all_passed = all(a["final_eval_passed"] for a in analyses)
    all_deep = all((a.get("content_depth", {}).get("depth_score", 0) or 0) >= 60 for a in analyses)
    is_unique = uniqueness["unique"]

    print(f"\n{'=' * 70}")
    print(f"VERDICT: eval_passed={all_passed} depth_ok={all_deep} unique={is_unique}")
    if all_passed and all_deep and is_unique:
        print("SUCCESS — Pipeline generates unique, deep MVPs")
    else:
        print("NEEDS IMPROVEMENT — See details above")
    print(f"{'=' * 70}")

    return 0 if (all_passed and all_deep and is_unique) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
