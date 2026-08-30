from pathlib import Path

RUNBOOK = Path(__file__).parents[2] / "docs/runbooks/public-demo-release.md"


def test_release_runbook_audits_all_renderer_safety_categories_on_tracked_paths():
    text = RUNBOOK.read_text()

    assert "tracked paths only" in text
    assert "does not inspect untracked files" in text
    assert ".env" in text
    assert "credential" in text
    assert "certificate" in text
    assert "node_modules" in text
    assert "__pycache__" in text
    assert ".tsbuildinfo" in text
    assert ".egg-info" in text
    assert "build" in text
    assert "coverage" in text
