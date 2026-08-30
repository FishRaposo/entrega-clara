"""Render the intentional repository layout from safe, git-tracked paths."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from pathlib import Path, PurePath, PurePosixPath

ROOT = Path(__file__).parents[2]
CANONICAL_ROOT_LABEL = "entrega-clara/"

EXCLUDED_COMPONENTS = {
    ".cache",
    ".coverage",
    ".git",
    ".mypy_cache",
    ".next",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".superpowers",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "coverage",
    "dist",
    "node_modules",
    "venv",
}
SENSITIVE_NAME_TOKENS = {
    "cert",
    "certificate",
    "credential",
    "credentials",
    "key",
    "secret",
    "secrets",
    "token",
    "tokens",
}
SENSITIVE_FILE_SUFFIXES = {
    ".cer",
    ".cert",
    ".crt",
    ".jks",
    ".key",
    ".keystore",
    ".p12",
    ".pem",
    ".pfx",
}
SENSITIVE_KEY_NAMES = {"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"}
TOKEN_SEPARATOR = re.compile(r"[^a-z0-9]+")

TreeNode = dict[str, "TreeNode"]


def _tracked_repository_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [path for path in result.stdout.split("\0") if path]


def _is_safe_component(component: str) -> bool:
    normalized = component.casefold()
    if normalized in EXCLUDED_COMPONENTS or normalized.endswith((".egg-info", ".tsbuildinfo")):
        return False
    if normalized == ".env" or normalized.startswith(".env."):
        return False
    if normalized in SENSITIVE_KEY_NAMES or any(
        normalized.endswith(suffix) for suffix in SENSITIVE_FILE_SUFFIXES
    ):
        return False
    tokens = {token for token in TOKEN_SEPARATOR.split(normalized) if token}
    return tokens.isdisjoint(SENSITIVE_NAME_TOKENS)


def _safe_parts(path: str | PurePath) -> tuple[str, ...] | None:
    candidate = PurePosixPath(path.as_posix() if isinstance(path, PurePath) else path)
    if candidate.is_absolute() or not candidate.parts:
        return None
    if any(part in {"", ".", ".."} or not _is_safe_component(part) for part in candidate.parts):
        return None
    return candidate.parts


def _build_tree(paths: Iterable[str | PurePath]) -> TreeNode:
    tree: TreeNode = {}
    for path in paths:
        parts = _safe_parts(path)
        if parts is None:
            continue
        node = tree
        for part in parts:
            node = node.setdefault(part, {})
    return tree


def render_tree(
    root: Path = ROOT,
    *,
    tracked_paths: Iterable[str | PurePath] | None = None,
) -> str:
    """Return a deterministic tree of safe tracked paths.

    ``tracked_paths`` is an explicit controlled-fixture seam. Normal repository
    rendering leaves it unset and obtains the intentional path set from Git.
    """
    paths = _tracked_repository_paths(root) if tracked_paths is None else tracked_paths
    tree = _build_tree(paths)
    lines = [CANONICAL_ROOT_LABEL]

    def visit(node: TreeNode, prefix: str = "") -> None:
        children = sorted(
            node.items(),
            key=lambda item: (not bool(item[1]), item[0].casefold(), item[0]),
        )
        for index, (name, descendants) in enumerate(children):
            last_child = index == len(children) - 1
            branch = "└── " if last_child else "├── "
            label = f"{name}/" if descendants else name
            lines.append(f"{prefix}{branch}{label}")
            if descendants:
                visit(descendants, prefix + ("    " if last_child else "│   "))

    visit(tree)
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_tree())
