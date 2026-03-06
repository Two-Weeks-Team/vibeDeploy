import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

uvicorn.run(
    "agent.server:app",
    host="0.0.0.0",
    port=8080,
    workers=2,
    timeout_keep_alive=300,
)
