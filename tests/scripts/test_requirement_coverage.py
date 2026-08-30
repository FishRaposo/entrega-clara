from scripts.quality.check_requirement_coverage import (
    REQUIRED_REQUIREMENT_IDS,
    missing_requirement_ids,
)


def test_traceability_covers_all_source_requirement_ids():
    assert missing_requirement_ids("docs/requirements/traceability.md") == ()


def test_requirement_coverage_reports_missing_ids_in_stable_order(tmp_path):
    traceability = tmp_path / "traceability.md"
    present = REQUIRED_REQUIREMENT_IDS - {"RF02", "RNF09"}
    traceability.write_text(" ".join(sorted(present)), encoding="utf-8")

    assert missing_requirement_ids(traceability) == ("RF02", "RNF09")
