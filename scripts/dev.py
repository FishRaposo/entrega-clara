"""Run backend + frontend dev servers — no Docker required (stdlib only)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "delivery_platform.api.main:create_app",
         "--factory", "--reload", "--port", "8000"],
        cwd=ROOT / "app" / "backend",
    )
    frontend = subprocess.Popen(
        ["npm", "run", "dev"], cwd=ROOT / "app" / "web", shell=sys.platform == "win32"
    )
    print("backend  -> http://localhost:8000")
    print("frontend -> http://localhost:3000")
    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()


if __name__ == "__main__":
    main()
