"""Prevent application source files from being placed at repository root."""

from __future__ import annotations

import argparse
from pathlib import Path


APPLICATION_SOURCE_EXTENSIONS = frozenset(
    {
        ".c",
        ".cc",
        ".cjs",
        ".cts",
        ".cpp",
        ".cs",
        ".css",
        ".cxx",
        ".go",
        ".htm",
        ".html",
        ".java",
        ".jsx",
        ".kt",
        ".kts",
        ".js",
        ".mjs",
        ".mts",
        ".php",
        ".py",
        ".pyi",
        ".rb",
        ".rs",
        ".sass",
        ".scala",
        ".scss",
        ".swift",
        ".ts",
        ".tsx",
        ".vue",
    }
)


def find_boundary_violations(root: Path) -> tuple[str, ...]:
    """Return sorted root-level application source paths outside ``app/``."""
    return tuple(
        sorted(
            path.name
            for path in root.iterdir()
            if path.is_file() and path.suffix.lower() in APPLICATION_SOURCE_EXTENSIONS
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that application source is contained in app/."
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root to inspect (defaults to this repository).",
    )
    args = parser.parse_args()
    violations = find_boundary_violations(args.root)
    if not violations:
        print(f"Application boundary passed: {args.root}")
        return 0

    print("Application source files at repository root: " + ", ".join(violations))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
