import multiprocessing
import os
import sys
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _AGENT_DIR.parent

sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(_PROJECT_ROOT)

import uvicorn  # noqa: E402

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(
        "agent.server:app",
        host="0.0.0.0",
        port=8080,
        workers=2,
        timeout_keep_alive=300,
    )
