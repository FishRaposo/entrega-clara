from scripts.repo.check_app_boundary import find_boundary_violations


def test_application_source_is_allowed_inside_app_but_not_at_root(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("print('allowed')")
    (tmp_path / "root.py").write_text("print('forbidden')")

    assert find_boundary_violations(tmp_path) == ("root.py",)


def test_boundary_reports_node_source_extensions_in_stable_order(tmp_path):
    (tmp_path / "z.ts").write_text("export {}", encoding="utf-8")
    (tmp_path / "a.js").write_text("export {}", encoding="utf-8")
    (tmp_path / "b.py").write_text("pass", encoding="utf-8")
    (tmp_path / "README.md").write_text("allowed", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "support.sh").write_text("true", encoding="utf-8")

    assert find_boundary_violations(tmp_path) == ("a.js", "b.py", "z.ts")
