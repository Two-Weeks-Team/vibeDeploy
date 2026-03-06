import asyncio
import json
import time
import uuid

import httpx

BASE_URL = "http://localhost:8081"

PROMPTS = [
    "A restaurant queue management app with QR codes. Customers scan a QR code at the entrance to join a digital queue, see their position in real-time via mobile web, and get push notifications when their table is ready. Staff dashboard for managing waitlist, estimated wait times, and table assignments.",
    "An AI-powered personal finance tracker that analyzes spending patterns and provides actionable savings recommendations. Connects to bank transaction data via CSV upload, categorizes expenses automatically using AI, and generates weekly spending reports with budget optimization suggestions.",
    "A pet health monitoring app where pet owners log symptoms, meals, and activities. An AI symptom checker suggests possible conditions based on the pet's breed, age, and symptom history. Includes vaccination reminders, vet appointment scheduling, and a timeline of health events.",
]


async def stream_sse(client, method, url, body, label):
    start = time.time()
    result = {"agents": {}, "verdict": None, "deploy": None, "errors": [], "duration_sec": 0}
    try:
        async with client.stream(method, url, json=body, timeout=600.0) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    d = json.loads(line[6:])
                    t = d.get("type", "")
                    el = f"[{time.time() - start:.0f}s]"
                    if "node.start" in t:
                        print(f"  {el} START {d.get('node', '')}: {d.get('message', '')}")
                    elif "node.complete" in t:
                        print(f"  {el} DONE  {d.get('node', '')}")
                    elif "agent.analysis" in t:
                        result["agents"][d.get("agent", "")] = d.get("score", 0)
                        print(f"  {el} AGENT {d.get('agent', '')}: score={d.get('score', 0)}")
                    elif t == "council.verdict":
                        result["verdict"] = {"score": d.get("final_score"), "decision": d.get("decision")}
                        print(f"  {el} VERDICT: {d.get('decision')} (score={d.get('final_score')})")
                    elif t == "deploy.complete":
                        result["deploy"] = {
                            "live_url": d.get("live_url", ""),
                            "github_repo": d.get("github_repo", ""),
                            "status": d.get("status", ""),
                        }
                        print(f"  {el} DEPLOY: {d.get('status', '')} repo={d.get('github_repo', '')}")
                    elif "error" in t:
                        result["errors"].append(d.get("error", "")[:300])
                        print(f"  {el} ERROR: {d.get('error', '')[:150]}")
                    elif "phase.complete" in t:
                        print(f"  {el} {label} COMPLETE")
                except (json.JSONDecodeError, KeyError):
                    pass
    except Exception as e:
        result["errors"].append(str(e)[:300])
        print(f"  EXCEPTION: {e}")
    result["duration_sec"] = round(time.time() - start, 1)
    return result


async def run_pipeline(client, idx, prompt):
    tid = f"pipeline-{idx + 1}-{uuid.uuid4().hex[:8]}"
    print(f"\n{'=' * 60}\nPIPELINE #{idx + 1} | thread_id={tid}\nPrompt: {prompt[:80]}...\n{'=' * 60}")

    r = await stream_sse(
        client,
        "POST",
        f"{BASE_URL}/run",
        {"prompt": prompt, "config": {"configurable": {"thread_id": tid}}},
        "PIPELINE",
    )

    if r["verdict"] and r["verdict"].get("decision") == "CONDITIONAL" and not r["deploy"]:
        print("\n  >>> CONDITIONAL — auto-resuming with 'proceed'...")
        r2 = await stream_sse(client, "POST", f"{BASE_URL}/resume", {"thread_id": tid, "action": "proceed"}, "RESUME")
        r["deploy"] = r2.get("deploy")
        r["errors"].extend(r2.get("errors", []))
        r["duration_sec"] += r2.get("duration_sec", 0)

    print(f"\n  FINAL: verdict={r['verdict']} deploy={r['deploy']} duration={r['duration_sec']}s")
    r["thread_id"] = tid
    return r


async def main():
    results = []
    async with httpx.AsyncClient() as client:
        print(f"Server: {(await client.get(f'{BASE_URL}/health', timeout=5.0)).json()}")
        for i, p in enumerate(PROMPTS):
            results.append(await run_pipeline(client, i, p))

    print(f"\n\n{'=' * 60}\nFINAL SUMMARY\n{'=' * 60}")
    for r in results:
        has_deploy = r.get("deploy") and r["deploy"].get("github_repo")
        print(
            f"\n  #{results.index(r) + 1}: {'DEPLOYED' if has_deploy else 'NO_DEPLOY'} | {r['verdict']} | {r.get('deploy')} | {r['duration_sec']}s"
        )

    with open("/tmp/vibedeploy-3-pipelines-result.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nSaved to /tmp/vibedeploy-3-pipelines-result.json")


if __name__ == "__main__":
    asyncio.run(main())
