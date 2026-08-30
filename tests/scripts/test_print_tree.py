import subprocess
from pathlib import Path

from scripts.repo.print_tree import render_tree


def test_default_tree_output_shows_project_boundaries_and_hides_generated_directories():
    output = render_tree()

    assert output.startswith("entrega-clara/\n")
    assert "app/" in output
    assert "docs/" in output
    assert "tests/" in output
    assert "scripts/" in output
    assert "superpowers/" in output
    assert "2026-08-29-food-delivery-platform-seed-design.md" in output
    assert ".superpowers/" not in output
    assert "node_modules/" not in output
    assert "__pycache__/" not in output
    assert "tsconfig.tsbuildinfo" not in output


def test_controlled_git_tree_uses_only_safe_tracked_paths(tmp_path: Path):
    tracked_paths = [
        "README.md",
        "Makefile",
        "app/backend/src/main.py",
        "docs/README.md",
        "scripts/repo/tool.py",
        "tests/scripts/test_tool.py",
        ".env.local",
        "deploy-credentials.json",
        "private-key.pem",
        "server.cert",
        "app/web/node_modules/package/index.js",
        "app/web/.next/cache/webpack.bin",
        "app/backend/__pycache__/main.pyc",
        "app/backend/.pytest_cache/state",
        "app/backend/.mypy_cache/state",
        "app/backend/.ruff_cache/state",
        "app/backend/.cache/state",
        "app/backend/cache/state",
        "app/backend/build/package.bin",
        "app/backend/dist/package.whl",
        "app/backend/coverage/index.html",
        ".coverage",
        "app/backend/package.egg-info/PKG-INFO",
        "app/web/tsconfig.tsbuildinfo",
        ".superpowers/sdd/task-8-report.md",
        "docs/superpowers/plans/internal-plan.md",
    ]
    for relative_path in tracked_paths:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "-f", "--", *tracked_paths],
        check=True,
    )
    (tmp_path / "untracked-notes.txt").write_text("must not appear")

    output = render_tree(tmp_path)

    assert output == """entrega-clara/
├── app/
│   └── backend/
│       └── src/
│           └── main.py
├── docs/
│   ├── superpowers/
│   │   └── plans/
│   │       └── internal-plan.md
│   └── README.md
├── scripts/
│   └── repo/
│       └── tool.py
├── tests/
│   └── scripts/
│       └── test_tool.py
├── Makefile
└── README.md"""


def test_explicit_tracked_paths_keep_fixture_rendering_deterministic(tmp_path: Path):
    output = render_tree(tmp_path / "arbitrary-checkout-name", tracked_paths=["README.md"])

    assert output == """entrega-clara/
└── README.md"""
