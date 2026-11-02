"""Portfolio-wide sweep: run the single-repository audit across checkouts.

Discovers git repositories under a root (stopping at each repository, skipping
build and dependency directories), runs the same checks as ``portfolio_audit``,
and writes an aggregated Markdown report.

    python portfolio_sweep.py ~/Projects --depth 2 --remote --network \
        --output portfolio-audit.md

Exit code is 1 when any repository has a FAIL (or any WARN with ``--strict``).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from portfolio_audit import FAIL, WARN, Result, audit

SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    ".next",
    "target",
    "vendor",
    "__pycache__",
    ".cache",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "coverage",
}


@dataclass
class RepoAudit:
    path: Path
    results: list[Result]

    @property
    def failures(self) -> list[Result]:
        return [result for result in self.results if result.status == FAIL]

    @property
    def warnings(self) -> list[Result]:
        return [result for result in self.results if result.status == WARN]


def find_repos(root: Path, max_depth: int) -> list[Path]:
    if (root / ".git").exists():
        return [root]
    repos: list[Path] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        if ".git" in dirs or ".git" in files:
            repos.append(current_path)
            dirs[:] = []
            continue
        if depth >= max_depth:
            dirs[:] = []
            continue
        dirs[:] = sorted(
            name for name in dirs if not name.startswith(".") and name not in SKIP_DIRS
        )
    return sorted(repos)


def display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix() or "."
    except ValueError:
        return path.as_posix()


def run_audit(path: Path, *, remote: bool, network: bool) -> list[Result]:
    try:
        return audit(path, remote=remote, network=network)
    except Exception as error:  # noqa: BLE001 - one broken repo must not stop the sweep
        return [Result(FAIL, "audit", f"error: {error}")]


def top_findings(item: RepoAudit) -> str:
    names = [result.name for result in item.failures + item.warnings]
    if not names:
        return "clean"
    shown = ", ".join(names[:4])
    return shown + (" ..." if len(names) > 4 else "")


def print_summary(items: list[RepoAudit], root: Path) -> None:
    width = max(len(display_path(item.path, root)) for item in items)
    print(f"portfolio sweep — {root} ({len(items)} repositories)")
    for item in items:
        print(
            f"{display_path(item.path, root):<{width}}  "
            f"{len(item.failures)}F {len(item.warnings)}W  {top_findings(item)}"
        )
    failures = sum(len(item.failures) for item in items)
    warnings = sum(len(item.warnings) for item in items)
    print(f"\n{failures} failure(s), {warnings} warning(s) across {len(items)} repositories")


def markdown_report(items: list[RepoAudit], root: Path, *, remote: bool, network: bool) -> str:
    today = time.strftime("%Y-%m-%d", time.localtime())
    failures = sum(len(item.failures) for item in items)
    warnings = sum(len(item.warnings) for item in items)
    mode = "local"
    if remote:
        mode += " + remote"
    if network:
        mode += " + network"
    lines = [
        f"# Portfolio audit — {today}",
        "",
        (
            f"Root: `{root}` · {len(items)} repositories · "
            f"{failures} failure(s) · {warnings} warning(s)"
        ),
        "",
        f"Mode: {mode}",
        "",
        "| Repository | Fail | Warn | Top findings |",
        "| --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| `{display_path(item.path, root)}` | {len(item.failures)} | "
            f"{len(item.warnings)} | {top_findings(item)} |"
        )
    lines.extend(["", "## Fix first", ""])
    fixes = [
        f"- **`{display_path(item.path, root)}`** — {result.name}: {result.detail}"
        for item in items
        for result in item.failures
    ]
    lines.extend(fixes or ["- No blockers. Work through warnings by impact."])
    lines.extend(["", "## Details"])
    for item in items:
        lines.extend(["", f"### {display_path(item.path, root)}", ""])
        for result in item.results:
            lines.append(f"- `{result.status}` {result.name} — {result.detail}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="Portfolio root (default: .)")
    parser.add_argument("--depth", type=int, default=2, help="Maximum directory depth (default: 2)")
    parser.add_argument("--remote", action="store_true", help="Check repo cards and CI via gh")
    parser.add_argument("--network", action="store_true", help="Probe hosted demo URLs")
    parser.add_argument("--output", type=Path, help="Write the full Markdown report here")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on warnings too")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    repos = find_repos(root, max(1, args.depth))
    if not repos:
        print(f"no git repositories found under {root} (depth {args.depth})", file=sys.stderr)
        return 1

    items = [
        RepoAudit(path, run_audit(path, remote=args.remote, network=args.network))
        for path in repos
    ]
    print_summary(items, root)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            markdown_report(items, root, remote=args.remote, network=args.network),
            encoding="utf-8",
        )
        print(f"\nreport: {args.output}")

    failures = sum(len(item.failures) for item in items)
    warnings = sum(len(item.warnings) for item in items)
    return 1 if failures or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
