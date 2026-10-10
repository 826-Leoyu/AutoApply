from __future__ import annotations

import uvicorn

from server.main import app
from server.paths import PORT, ensure_dirs

if __name__ == "__main__":
    from pathlib import Path
    import os

    os.chdir(Path(__file__).resolve().parent.parent)
    ensure_dirs()
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
