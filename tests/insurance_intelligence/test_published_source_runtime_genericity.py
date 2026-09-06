from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_star_specific_published_source_runtime_adapter_is_retired() -> None:
    assert not (
        ROOT
        / "insurance_intelligence"
        / "evidence"
        / "star_health_publication_source.py"
    ).exists()


def test_published_runtime_tests_do_not_import_retired_star_source_adapter() -> None:
    targets = (
        ROOT / "tests" / "insurance_intelligence" / "test_published_evidence_resolver.py",
        ROOT / "tests" / "insurance_intelligence" / "test_user_answer_evidence_orchestration.py",
    )
    for path in targets:
        text = path.read_text(encoding="utf-8")
        assert "star_health_publication_source" not in text
        assert "load_star_published_evidence_source" not in text


def test_generic_coverage_registry_source_contains_no_insurer_specific_routing() -> None:
    path = (
        ROOT
        / "insurance_intelligence"
        / "evidence"
        / "coverage_registry_source.py"
    )
    text = path.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "star_health",
        "bajaj",
        "hdfc",
        "room rent",
        "bariatric",
        "waiting period",
    ):
        assert forbidden not in text
