from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_scaffold_contains_all_application_and_supporting_boundaries():
    required_directories = [
        "app/backend/src/delivery_platform",
        "app/web/src",
        "data/seed",
        "data/scenarios",
        "docs/adr",
        "docs/architecture",
        "docs/requirements",
        "scripts/data",
        "scripts/demo",
        "scripts/quality",
        "tests/api",
        "tests/domain",
        "tests/e2e",
        "tests/frontend",
        "tests/routing",
        "tests/repo",
        "tests/scripts",
    ]

    for relative_path in required_directories:
        assert (ROOT / relative_path).is_dir()


def test_seed_and_traceability_are_not_empty():
    seed = ROOT / "docs/superpowers/specs/2026-08-29-food-delivery-platform-seed-design.md"
    traceability = ROOT / "docs/requirements/traceability.md"

    assert len(seed.read_text()) > 10000
    assert len(traceability.read_text()) > 1000
