"""Cross-platform quality gate runner — stdlib only (Windows-friendly).

Runs the full local gate without needing POSIX env syntax. Exit non-zero on the
first failing gate.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GATES = [
    ("seed validation", [sys.executable, "scripts/data/validate_seed.py", "data/scenarios/lunch-rush.json"], ROOT),
    ("requirement coverage", [sys.executable, "scripts/quality/check_requirement_coverage.py", "docs/requirements/traceability.md"], ROOT),
    ("app boundary", [sys.executable, "scripts/repo/check_app_boundary.py"], ROOT),
    ("static lab up to date", [sys.executable, "scripts/media/check_static_lab.py"], ROOT),
    ("routing benchmark smoke", [sys.executable, "scripts/bench/routing_benchmark.py", "--smoke"], ROOT),
    ("ruff", [sys.executable, "-m", "ruff", "check", "app/backend/src", "tests", "scripts"], ROOT),
    ("mypy", [sys.executable, "-m", "mypy", "app/backend/src"], ROOT),
    ("backend tests", [sys.executable, "-m", "pytest", "tests", "-q"], ROOT),
    ("web vitest", ["npm", "test", "--", "--run"], ROOT / "app" / "web"),
    ("web lint", ["npm", "run", "lint"], ROOT / "app" / "web"),
    ("web typecheck", ["npm", "run", "typecheck"], ROOT / "app" / "web"),
]


def main() -> int:
    failed: list[str] = []
    for name, cmd, cwd in GATES:
        print(f"\n=== {name} ===", flush=True)
        shell = sys.platform == "win32" and cmd[0] == "npm"
        result = subprocess.run(cmd, check=False, cwd=cwd, shell=shell)
        if result.returncode != 0:
            failed.append(name)
    if failed:
        print(f"\nFAILED gates: {', '.join(failed)}")
        return 1
    print("\nAll gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
