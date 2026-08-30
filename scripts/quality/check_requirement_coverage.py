"""Verify that the traceability matrix covers every source requirement."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_REQUIREMENT_IDS = {
    *(f"RF{i:02d}" for i in range(1, 15)),
    "RNF01",
    "RNF02",
    *(f"RNF{i:02d}" for i in range(3, 11)),
}
REQUIREMENT_ID = re.compile(r"\b(?:RF\d{2}|RNF\d{2})\b")


def missing_requirement_ids(path: str | Path) -> tuple[str, ...]:
    """Return required requirement IDs absent from a traceability document."""
    contents = Path(path).read_text(encoding="utf-8")
    present = set(REQUIREMENT_ID.findall(contents))
    return tuple(sorted(REQUIRED_REQUIREMENT_IDS - present))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check requirement coverage in a traceability matrix."
    )
    parser.add_argument("path", type=Path, help="Path to the traceability Markdown file.")
    args = parser.parse_args()
    missing = missing_requirement_ids(args.path)
    if not missing:
        print(f"Requirement coverage passed: {args.path}")
        return 0

    print("Missing requirement IDs: " + ", ".join(missing))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
