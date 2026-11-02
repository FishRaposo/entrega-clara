"""Mechanical portfolio audit: the checks a reviewer makes in the first minute.

It classifies the current checkout first: a piece gets the full checks, while a
hub/collection gets index and git checks and skips piece-specific expectations.

Read-only by default. Standard library only, cross-platform. ``--remote`` reads
the repo card and the default-branch CI status through an authenticated ``gh``;
``--network`` probes the hosted demo URL; ``--claims`` lists numeric claims for
manual artifact verification.

    python portfolio_audit.py [path] [--remote] [--network] [--claims]

FAIL means the repository is not ready to be looked at (exit code 1).
WARN means it will still be looked at, less generously.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.request
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
PREFERRED_CI_WORKFLOWS = (
    "ci.yml",
    "ci.yaml",
    "test.yml",
    "test.yaml",
    "tests.yml",
    "tests.yaml",
    "build.yml",
    "build.yaml",
)
DOC_LINK_FILES = (
    "docs/for-reviewers.md",
    "docs/verification.md",
    "docs/origin.md",
    "docs/README.md",
)
HUB_ROOT_MARKERS = (
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "setup.py",
    "src",
    "app",
)
HUB_README_PATTERN = re.compile(
    r"\b(hub|collection|workspace|playbook|registry|monorepo|assignments|exercises)\b",
    re.IGNORECASE,
)
CONTEXT_FILE = ".portfolio-context"
SUBPROJECT_MARKERS = (
    "README.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "tests",
    "test",
)
SUBPROJECT_SUFFIXES = {
    ".py",
    ".ipynb",
    ".js",
    ".ts",
    ".tsx",
    ".java",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".html",
    ".css",
}
HUB_SKIP_DIRS = {
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
MEDIA_DIRS = ("docs/media", "media", "screenshots", "assets")
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".mp4", ".webm"}
SOCIAL_PREVIEW_NAMES = ("social-preview.png", "social-preview.jpg", "og-image.png", "og-image.jpg")
SOCIAL_PREVIEW_DIRS = ("docs/media", "media", "assets", ".")
DEMO_HINTS = (
    "demo",
    "live",
    "app.",
    "lab",
    "site",
    "pages",
    "github.io",
    "vercel",
    "netlify",
    "render",
    "fly.dev",
)
BADGE_HOSTS = ("shields.io", "badge", "img.shields")
CI_FAILURES = {"failure", "cancelled", "timed_out", "action_required", "startup_failure"}
CI_PENDING = {"in_progress", "queued", "waiting", "requested", "pending"}
CLAIM_UNITS = re.compile(
    r"\d[\d,.]*\s*(?:ms|s\b|%|nodes?|expansions?|tests?|adrs?|gates?|mb|kb|queries|shortcuts|stops?)",
    re.IGNORECASE,
)


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


def find_ci_workflow(root: Path) -> Path | None:
    workflows = root / ".github" / "workflows"
    if workflows.is_dir():
        for name in PREFERRED_CI_WORKFLOWS:
            candidate = workflows / name
            if candidate.is_file():
                return candidate
    for pattern in CI_FILES:
        matches = sorted(root.glob(pattern))
        if matches:
            return matches[0]
    return None


def _looks_like_subproject(path: Path) -> bool:
    if any((path / marker).exists() for marker in SUBPROJECT_MARKERS):
        return True
    try:
        return any(
            child.is_file() and child.suffix.lower() in SUBPROJECT_SUFFIXES
            for child in path.iterdir()
        )
    except OSError:
        return False


def _readme_identifies_hub(root: Path) -> bool:
    readme = find_readme(root)
    if readme is None:
        return False
    text = readme.read_text(encoding="utf-8", errors="replace")[:4000]
    return bool(HUB_README_PATTERN.search(text))


def detect_hub(root: Path) -> tuple[bool, list[Path]]:
    if any((root / marker).exists() for marker in HUB_ROOT_MARKERS):
        return False, []
    try:
        children = sorted(root.iterdir())
    except OSError:
        return False, []
    visible = [
        child
        for child in children
        if child.is_dir()
        and not child.name.startswith(".")
        and child.name not in HUB_SKIP_DIRS
    ]
    subprojects = [child for child in visible if _looks_like_subproject(child)]
    if _readme_identifies_hub(root) and len(visible) >= 3:
        return True, []
    return len(subprojects) >= 2, subprojects


def check_ci(root: Path) -> Result:
    workflow = find_ci_workflow(root)
    if workflow is not None:
        return Result(PASS, "ci", rel(workflow, root))
    return Result(FAIL, "ci", "no CI workflow; green checks are evidence")


def strip_fences(text: str) -> str:
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            lines.append("")
            continue
        lines.append("" if in_fence else line)
    return "\n".join(lines)


def check_links(root: Path, files: list[Path]) -> Result:
    broken: list[str] = []
    checked = 0
    scanned = 0
    for file in dict.fromkeys(files):
        if not file.is_file():
            continue
        scanned += 1
        text = strip_fences(file.read_text(encoding="utf-8", errors="replace"))
        for target in re.findall(r"\]\(\s*([^)\s]+)", text):
            if target.startswith(("http://", "https://", "mailto:", "#", "<")):
                continue
            if target.startswith("www.") or "{" in target or "}" in target:
                continue
            path_part = target.split("#", 1)[0].split("?", 1)[0]
            path_part = unquote(path_part)
            if not path_part:
                continue
            candidate = (
                (root / path_part.lstrip("/"))
                if path_part.startswith("/")
                else (file.parent / path_part)
            )
            checked += 1
            if not candidate.exists():
                broken.append(f"{rel(file, root)} -> {path_part}")
    if broken:
        shown = ", ".join(broken[:4]) + (" ..." if len(broken) > 4 else "")
        return Result(FAIL, "links", f"{len(broken)} broken: {shown}")
    return Result(PASS, "links", f"{checked} relative link(s) across {scanned} file(s) resolve")


def _probe_url(url: str) -> int:
    headers = {"User-Agent": "portfolio-audit/1.0"}
    request = urllib.request.Request(url, method="HEAD", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        if error.code not in (403, 405):
            return int(error.code)
        request = urllib.request.Request(url, headers={**headers, "Range": "bytes=0-0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            return int(response.status)


def check_demo(root: Path, readme: Path, *, network: bool) -> Result:
    first_screen = "\n".join(
        readme.read_text(encoding="utf-8", errors="replace").splitlines()[:FIRST_SCREEN_LINES]
    )
    candidates: list[tuple[str, str]] = []
    for text, url in re.findall(r"(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)\)", first_screen):
        if any(host in url.lower() for host in BADGE_HOSTS):
            continue
        haystack = f"{text} {url}".lower()
        if any(hint in haystack for hint in DEMO_HINTS):
            candidates.append((text, url))
    if not candidates:
        for url in re.findall(r"https?://[^\s)\"']+", first_screen):
            if any(host in url.lower() for host in BADGE_HOSTS):
                continue
            if any(hint in url.lower() for hint in DEMO_HINTS):
                candidates.append(("", url))
                break
    if candidates:
        _, url = candidates[0]
        if not network:
            return Result(
                PASS,
                "demo",
                f"hosted link: {url} (reachability not checked; use --network)",
            )
        try:
            status = _probe_url(url)
        except (urllib.error.URLError, TimeoutError) as error:
            return Result(WARN, "demo", f"could not reach {url}: {error}")
        if 200 <= status < 400:
            return Result(PASS, "demo", f"hosted link: {url} (HTTP {status})")
        return Result(FAIL, "demo", f"hosted link returned HTTP {status}: {url}")
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


def check_social_preview(root: Path) -> Result:
    for directory in SOCIAL_PREVIEW_DIRS:
        base = root if directory == "." else root / directory
        for name in SOCIAL_PREVIEW_NAMES:
            path = base / name
            if not path.is_file():
                continue
            if path.suffix.lower() != ".png":
                return Result(WARN, "social", f"{rel(path, root)} found; verify 1280x640 manually")
            with path.open("rb") as handle:
                header = handle.read(24)
            if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
                return Result(WARN, "social", f"{rel(path, root)} is not a valid PNG")
            width, height = struct.unpack(">II", header[16:24])
            if (width, height) == (1280, 640):
                return Result(PASS, "social", f"{rel(path, root)} (1280x640)")
            return Result(WARN, "social", f"{rel(path, root)} is {width}x{height}; use 1280x640")
    return Result(
        WARN,
        "social",
        "no social-preview image; upload is UI-only, so commit a 1280x640 PNG",
    )


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
    changed = len(status.stdout.strip().splitlines()) if status.stdout.strip() else 0
    upstream = run_git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    has_upstream = upstream is not None and upstream.returncode == 0
    ahead = 0
    if has_upstream:
        count = run_git(root, "rev-list", "--count", "@{u}..HEAD")
        if count is not None and count.returncode == 0:
            try:
                ahead = int(count.stdout.strip() or "0")
            except ValueError:
                ahead = 0
    if changed:
        detail = f"{changed} uncommitted change(s)"
        if ahead:
            detail += f", {ahead} unpushed commit(s)"
        return Result(WARN, "git", detail + "; reviewers see the pushed tree")
    if ahead:
        return Result(WARN, "git", f"{ahead} unpushed commit(s); push before sharing")
    if not has_upstream:
        return Result(WARN, "git", "clean, but no upstream configured; cannot confirm the pushed tree")
    return Result(PASS, "git", "clean working tree, up to date with upstream")


def check_ci_status(root: Path, workflow: Path | None, branch: str) -> Result:
    if workflow is None:
        return Result(WARN, "ci status", "no workflow file to query")
    if ".github" not in workflow.parts:
        return Result(WARN, "ci status", "non-GitHub CI; verify the default branch manually")
    try:
        completed = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                workflow.name,
                "--branch",
                branch,
                "--limit",
                "1",
                "--json",
                "conclusion,status,url",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            cwd=root,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return Result(WARN, "ci status", "gh unavailable; skipped")
    if completed.returncode != 0:
        return Result(WARN, "ci status", "gh could not query workflow runs")
    try:
        runs = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return Result(WARN, "ci status", "could not parse gh run output")
    if not runs:
        return Result(WARN, "ci status", f"no runs for {workflow.name} on {branch}")
    run = runs[0]
    conclusion = str(run.get("conclusion") or "").lower()
    status = str(run.get("status") or "").lower()
    url = str(run.get("url") or "")
    if conclusion == "success":
        return Result(PASS, "ci status", f"{workflow.name} on {branch}: success")
    if conclusion in CI_FAILURES:
        suffix = f" ({url})" if url else ""
        return Result(FAIL, "ci status", f"{workflow.name} on {branch}: {conclusion}{suffix}")
    if status in CI_PENDING:
        suffix = f" ({url})" if url else ""
        return Result(WARN, "ci status", f"{workflow.name} on {branch}: {status}{suffix}")
    return Result(WARN, "ci status", f"{workflow.name} on {branch}: {conclusion or status or 'unknown'}")


def repo_metadata(root: Path) -> dict | None:
    if shutil.which("gh") is None:
        return None
    try:
        completed = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                "--json",
                (
                    "nameWithOwner,description,repositoryTopics,homepageUrl,defaultBranchRef,"
                    "isPrivate,visibility"
                ),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            cwd=root,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def check_remote(root: Path, data: dict | None = None) -> list[Result]:
    data = data if data is not None else repo_metadata(root)
    if data is None:
        return [Result(WARN, "remote", "gh unavailable, not authenticated, or no remote; skipped")]
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
    branch = str((data.get("defaultBranchRef") or {}).get("name") or "main")
    results.append(check_ci_status(root, find_ci_workflow(root), branch))
    return results


def collect_claims(readme: Path, limit: int = 60) -> list[str]:
    text = strip_fences(readme.read_text(encoding="utf-8", errors="replace"))
    claims: list[str] = []
    section = "top"
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            section = stripped.lstrip("#").strip() or "top"
            continue
        if not stripped or set(stripped) <= {"|", "-", " "}:
            continue
        if not CLAIM_UNITS.search(stripped):
            continue
        links = re.findall(r"\]\(([^)]+)\)", stripped)
        source = ", ".join(links) if links else f"section: {section}"
        claims.append(f"L{number}: {stripped[:150]}  [{source}]")
    if len(claims) > limit:
        claims = claims[:limit] + [f"... {len(claims) - limit} more claim-like line(s)"]
    return claims


def read_context(root: Path) -> str | None:
    path = root / CONTEXT_FILE
    if not path.is_file():
        return None
    try:
        first = path.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0]
    except (OSError, IndexError):
        return None
    value = first.strip().lower()
    return value if value in {"piece", "hub", "private"} else None


def _hub_audit(
    root: Path,
    subprojects: list[Path],
    *,
    declared: bool = False,
    private: bool = False,
) -> list[Result]:
    if declared:
        detail = "hub declared (.portfolio-context)"
    elif subprojects:
        names = ", ".join(path.name for path in subprojects[:4])
        if len(subprojects) > 4:
            names += ", ..."
        detail = f"hub detected ({len(subprojects)} subprojects: {names})"
    else:
        detail = "hub detected (README identifies a hub)"
    if private:
        detail += "; private repository"
    detail += "; piece checks skipped"
    results = [Result(PASS, "context", detail)]
    readme = find_readme(root)
    if readme is None:
        results.append(
            Result(WARN, "readme", "hub has no index README (optional; add one if pinned)")
        )
    else:
        readme_result, _ = check_readme(root)
        results.append(readme_result)
        results.append(check_links(root, [readme]))
    results.append(check_git(root))
    return results


def _private_audit(root: Path) -> list[Result]:
    return [
        Result(PASS, "context", "private repository; public portfolio checks skipped"),
        check_git(root),
    ]


def audit(root: Path, *, remote: bool, network: bool) -> list[Result]:
    override = read_context(root)
    if override == "piece":
        pass
    elif override == "hub":
        _, subprojects = detect_hub(root)
        metadata = repo_metadata(root) if remote else None
        private = bool(metadata and metadata.get("isPrivate"))
        return _hub_audit(root, subprojects, declared=True, private=private)
    elif override == "private":
        return _private_audit(root)
    else:
        is_hub, subprojects = detect_hub(root)
        if is_hub:
            metadata = repo_metadata(root) if remote else None
            private = bool(metadata and metadata.get("isPrivate"))
            return _hub_audit(root, subprojects, private=private)

    metadata = repo_metadata(root) if remote else None
    if metadata is not None and metadata.get("isPrivate") and override != "piece":
        return _private_audit(root)

    results: list[Result] = []
    readme_result, readme = check_readme(root)
    results.append(readme_result)
    results.append(check_license(root))
    results.append(check_tests(root))
    results.append(check_ci(root))
    if readme is not None:
        files = [readme] + [
            root / name for name in DOC_LINK_FILES if (root / name).is_file()
        ]
        results.append(check_links(root, files))
        results.append(check_demo(root, readme, network=network))
    results.append(check_media(root))
    results.append(check_social_preview(root))
    results.append(check_git(root))
    if remote:
        results.extend(check_remote(root, metadata))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="Repository root (default: .)")
    parser.add_argument("--remote", action="store_true", help="Check the repo card and CI status via gh")
    parser.add_argument("--network", action="store_true", help="Probe the hosted demo URL")
    parser.add_argument(
        "--claims",
        action="store_true",
        help="List claim-like numeric lines with section/link context",
    )
    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    results = audit(root, remote=args.remote, network=args.network)
    width = max(len(result.name) for result in results)
    print(f"portfolio audit — {root}")
    for result in results:
        print(f"{result.status:<4}  {result.name:<{width}}  {result.detail}")

    if args.claims:
        non_piece = any(
            result.name == "context" and "skipped" in result.detail
            for result in results
        )
        if non_piece:
            print("\nclaim inventory skipped: not a portfolio piece")
        else:
            readme = find_readme(root)
            if readme is None:
                print("\nno README; no claim inventory")
            else:
                print("\nnumeric claims — verify each against its artifact")
                claims = collect_claims(readme)
                for claim in claims:
                    print(f"  {claim}")
                if not claims:
                    print("  none found")

    failures = sum(1 for result in results if result.status == FAIL)
    warnings = sum(1 for result in results if result.status == WARN)
    print(f"\n{failures} failure(s), {warnings} warning(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
