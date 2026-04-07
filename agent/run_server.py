import multiprocessing
import os
import sys
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AGENT_DIR.parent

sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(_PROJECT_ROOT)

import uvicorn  # noqa: E402


def _read_worker_count() -> int:
    raw = os.environ.get("UVICORN_WORKERS") or os.environ.get("WEB_CONCURRENCY") or "1"
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(
        "agent.server:app",
        host=os.environ.get("UVICORN_HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8080")),
        workers=_read_worker_count(),
        timeout_keep_alive=300,
        server_header=False,
        proxy_headers=True,
        forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "*"),
    )
