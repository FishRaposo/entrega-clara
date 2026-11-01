"""Mechanical portfolio audit: the checks a reviewer makes in the first minute.

Read-only by default. Standard library only, cross-platform, no network unless
``--remote`` is passed (and then only via an authenticated ``gh`` CLI).

    python portfolio_audit.py [path] [--remote]

FAIL means the repository is not ready to be looked at (exit code 1).
WARN means it will still be looked at, less generously.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
FIRST_SCREEN_LINES = 80

README_NAMES = ("README.md", "README.markdown", "README.rst", "readme.md")
LICENSE_NAMES = (
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "LICENCE",
    "LICENCE.md",
    "COPYING",
)
TEST_DIRS = ("tests", "test", "spec", "__tests__")
TEST_FILES = ("test_*.py", "*_test.py", "*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx")
CI_FILES = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".gitlab-ci.yml",
    ".circleci/config.yml",
    "azure-pipelines.yml",
)
MEDIA_DIRS = ("docs/media", "media", "screenshots", "assets")
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".webm"}
DEMO_HINTS = ("demo", "live", "app.", "lab", "site", "pages", "vercel", "netlify", "render", "fly.dev")
BADGE_HOSTS = ("shields.io", "badge", "img.shields")


@dataclass
class Result:
    status: str
    name: str
    detail: str


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def find_readme(root: Path) -> Path | None:
    for name in README_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def check_readme(root: Path) -> tuple[Result, Path | None]:
    readme = find_readme(root)
    if readme is None:
        return Result(FAIL, "readme", "no README found; add one with what/why/proof/see"), None
    lines = readme.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 15:
        return Result(WARN, "readme", f"{readme.name} is only {len(lines)} lines; is it complete?"), readme
    return Result(PASS, "readme", f"{readme.name} ({len(lines)} lines)"), readme


def check_license(root: Path) -> Result:
    for name in LICENSE_NAMES:
        if (root / name).is_file():
            return Result(PASS, "license", name)
    return Result(FAIL, "license", "no LICENSE file; add one (MIT/Apache-2.0 are portfolio-friendly)")


def check_tests(root: Path) -> Result:
    for name in TEST_DIRS:
        if (root / name).is_dir():
            return Result(PASS, "tests", f"{name}/ present")
    found = []
    for pattern in TEST_FILES:
        found.extend(path for path in root.rglob(pattern) if "node_modules" not in path.parts)
        if found:
            break
    if found:
        return Result(PASS, "tests", f"{len(found)} test file(s), e.g. {rel(found[0], root)}")
    return Result(FAIL, "tests", "no test suite found; even a small one changes the review")


def check_ci(root: Path) -> Result:
    for pattern in CI_FILES:
        matches = sorted(root.glob(pattern))
        if matches:
            return Result(PASS, "ci", rel(matches[0], root))
    return Result(FAIL, "ci", "no CI workflow; green checks are evidence")


def check_links(root: Path, readme: Path) -> Result:
    text = readme.read_text(encoding="utf-8", errors="replace")
    targets = re.findall(r"\]\(\s*([^)\s]+)", text)
    broken: list[str] = []
    checked = 0
    for target in targets:
        if target.startswith(("http://", "https://", "mailto:", "#", "<")):
            continue
        if target.startswith("www.") or "{" in target or "}" in target:
            continue
        path_part = target.split("#", 1)[0].split("?", 1)[0]
        path_part = unquote(path_part)
        if not path_part:
            continue
        candidate = (root / path_part.lstrip("/")) if path_part.startswith("/") else (readme.parent / path_part)
        checked += 1
        if not candidate.exists():
            broken.append(path_part)
    if broken:
        shown = ", ".join(broken[:4]) + (" ..." if len(broken) > 4 else "")
        return Result(FAIL, "links", f"{len(broken)} broken: {shown}")
    return Result(PASS, "links", f"{checked} relative link(s) resolve")


def check_demo(root: Path, readme: Path) -> Result:
    first_screen = "\n".join(
        readme.read_text(encoding="utf-8", errors="replace").splitlines()[:FIRST_SCREEN_LINES]
    )
    for url in re.findall(r"https?://[^\s)\"']+", first_screen):
        lowered = url.lower()
        if any(host in lowered for host in BADGE_HOSTS):
            continue
        if any(hint in lowered for hint in DEMO_HINTS):
            return Result(PASS, "demo", f"hosted link in the first screen: {url}")
    for target in re.findall(r"\]\(\s*([^)\s]+\.html)", first_screen):
        candidate = readme.parent / unquote(target.split("#", 1)[0])
        if candidate.exists():
            return Result(
                WARN,
                "demo",
                f"offline replay {target} exists; hosting it makes the 60-second test possible",
            )
    return Result(WARN, "demo", "no hosted demo/replay link in the first screen; add one")


def check_media(root: Path) -> Result:
    for name in MEDIA_DIRS:
        directory = root / name
        if not directory.is_dir():
            continue
        media = [p for p in directory.rglob("*") if p.suffix.lower() in MEDIA_SUFFIXES]
        if media:
            return Result(PASS, "media", f"{len(media)} file(s) under {name}/")
    return Result(WARN, "media", "no screenshots or video; one image beats a paragraph")


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def check_git(root: Path) -> Result:
    inside = run_git(root, "rev-parse", "--is-inside-work-tree")
    if inside is None or inside.returncode != 0:
        return Result(WARN, "git", "not a git repository (or git unavailable)")
    status = run_git(root, "status", "--porcelain")
    if status is None:
        return Result(WARN, "git", "could not read working tree status")
    if status.stdout.strip():
        changed = len(status.stdout.strip().splitlines())
        return Result(WARN, "git", f"{changed} uncommitted change(s); reviewers see the pushed tree")
    return Result(PASS, "git", "clean working tree")


def check_remote(root: Path) -> list[Result]:
    if shutil.which("gh") is None:
        return [Result(WARN, "remote", "gh CLI not installed; skipped repo-card checks")]
    try:
        completed = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner,description,repositoryTopics,homepageUrl"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            cwd=root,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return [Result(WARN, "remote", "gh unavailable; skipped repo-card checks")]
    if completed.returncode != 0:
        return [Result(WARN, "remote", "gh is not authenticated or has no remote; skipped")]
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return [Result(WARN, "remote", "could not parse gh output")]
    results: list[Result] = []
    description = str(data.get("description") or "").strip()
    results.append(
        Result(PASS, "description", description[:80])
        if description
        else Result(WARN, "description", "empty repo description; it is the title slide")
    )
    topics = data.get("repositoryTopics") or []
    results.append(
        Result(PASS, "topics", f"{len(topics)} topic(s)")
        if topics
        else Result(WARN, "topics", "no topics; add 6–10 search terms")
    )
    homepage = str(data.get("homepageUrl") or "").strip()
    results.append(
        Result(PASS, "homepage", homepage)
        if homepage
        else Result(WARN, "homepage", "no homepage URL; point it at the demo")
    )
    name = str(data.get("nameWithOwner") or "")
    if name:
        pages = subprocess.run(
            ["gh", "api", f"repos/{name}/pages"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        results.append(
            Result(PASS, "pages", "GitHub Pages enabled")
            if pages.returncode == 0
            else Result(WARN, "pages", "Pages not enabled; a hosted replay is one click")
        )
    return results


def audit(root: Path, *, remote: bool) -> list[Result]:
    results: list[Result] = []
    readme_result, readme = check_readme(root)
    results.append(readme_result)
    results.append(check_license(root))
    results.append(check_tests(root))
    results.append(check_ci(root))
    if readme is not None:
        results.append(check_links(root, readme))
        results.append(check_demo(root, readme))
    results.append(check_media(root))
    results.append(check_git(root))
    if remote:
        results.extend(check_remote(root))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="Repository root (default: .)")
    parser.add_argument("--remote", action="store_true", help="Also check the repo card via gh")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    results = audit(root, remote=args.remote)
    width = max(len(result.name) for result in results)
    print(f"portfolio audit — {root}")
    for result in results:
        print(f"{result.status:<4}  {result.name:<{width}}  {result.detail}")

    failures = sum(1 for result in results if result.status == FAIL)
    warnings = sum(1 for result in results if result.status == WARN)
    print(f"\n{failures} failure(s), {warnings} warning(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
