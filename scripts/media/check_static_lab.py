"""Fail when the committed static lab is stale relative to its sources.

Regenerates ``site/index.html`` and compares it with the committed copy: traces,
benchmarks, graph or template changes must be reflected in the page a reviewer
clicks. The regenerated file is left in place so the fix is a commit.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "site" / "index.html"


def main() -> int:
    before = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    subprocess.run(
        [sys.executable, "scripts/media/export_static_lab.py"],
        cwd=ROOT,
        check=True,
    )
    after = TARGET.read_text(encoding="utf-8")
    if before != after:
        print("site/index.html was stale; it has been regenerated — commit it")
        return 1
    print("static lab is up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
