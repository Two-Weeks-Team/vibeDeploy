#!/usr/bin/env python3
import asyncio
import json
import os
from pathlib import Path

import httpx


async def run_evaluation():
    dataset_path = Path(__file__).parent / "evaluation_dataset.json"
    with open(dataset_path) as f:
        test_cases = json.load(f)

    agent_url = os.getenv("AGENT_URL", "http://localhost:8081")
    results = []
    passed = 0

    for i, tc in enumerate(test_cases):
        print(f"\n[{i + 1}/{len(test_cases)}] Testing: {tc['input'][:60]}...")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{agent_url}/run",
                    json={"prompt": tc["input"]},
                    headers={"Accept": "text/event-stream"},
                )

                verdict_data = {}
                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        try:
                            event = json.loads(line[6:])
                            if event.get("type") == "council.verdict":
                                verdict_data = event
                        except json.JSONDecodeError:
                            continue

                score = verdict_data.get("final_score", 0)
                decision = verdict_data.get("decision", "UNKNOWN")

                ok = True
                if "min_score" in tc and score < tc["min_score"]:
                    ok = False
                if "max_score" in tc and score > tc["max_score"]:
                    ok = False
                if tc.get("expected_decision") and decision != tc["expected_decision"]:
                    ok = False

                status = "PASS" if ok else "FAIL"
                if ok:
                    passed += 1
                print(f"  Score: {score} | Decision: {decision} | {status}")

                results.append(
                    {
                        "input": tc["input"],
                        "expected_decision": tc.get("expected_decision"),
                        "actual_decision": decision,
                        "score": score,
                        "passed": ok,
                    }
                )

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append(
                {
                    "input": tc["input"],
                    "error": str(e),
                    "passed": False,
                }
            )

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{len(test_cases)} passed ({passed / len(test_cases) * 100:.0f}%)")

    output_path = Path(__file__).parent / "evaluation_results.json"
    with open(output_path, "w") as f:
        json.dump({"total": len(test_cases), "passed": passed, "results": results}, f, indent=2)
    print(f"Full results saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
