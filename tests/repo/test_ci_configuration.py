from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_ci_workflow_runs_required_quality_commands():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    for command in [
        "pytest tests",
        "ruff check",
        "mypy",
        "npm test",
        "npm run typecheck",
        "npm run build",
        "git diff --check",
    ]:
        assert command in workflow


def test_ci_checkout_fetches_full_history_for_committed_whitespace_check():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert "- uses: actions/checkout@v4\n        with:\n          fetch-depth: 0" in workflow


def test_compose_supplies_the_web_proxy_with_the_internal_api_url():
    compose = (ROOT / "docker-compose.yml").read_text()

    assert "API_INTERNAL_BASE_URL: http://api:8000" in compose
