from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_application_source_is_contained_by_app_directory():
    forbidden_root_source_files = {
        "main.py",
        "index.ts",
        "index.tsx",
        "app.py",
    }

    root_files = {
        path.name
        for path in ROOT.iterdir()
        if path.is_file()
    }

    assert root_files.isdisjoint(forbidden_root_source_files)
    assert (ROOT / "app").is_dir()
    assert (ROOT / "docs").is_dir()
    assert (ROOT / "tests").is_dir()
    assert (ROOT / "scripts").is_dir()


def test_required_project_documents_exist():
    required_files = [
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/superpowers/specs/2026-08-29-food-delivery-platform-seed-design.md",
    ]

    for relative_path in required_files:
        assert (ROOT / relative_path).is_file()


def test_deferred_e2e_directory_is_documented_without_a_source_placeholder():
    assert (ROOT / "tests/e2e/README.md").is_file()
    assert not (ROOT / "tests/e2e/.gitkeep").exists()


def test_root_contract_documents_the_demo_preview_make_target():
    layout = (ROOT / "docs/architecture/repository-layout.md").read_text()

    assert "demo-preview" in layout
