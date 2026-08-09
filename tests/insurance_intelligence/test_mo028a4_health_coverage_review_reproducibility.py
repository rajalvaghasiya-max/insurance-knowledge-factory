from pathlib import Path

from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.coverage_registry.reporting import (
    build_coverage_review_report,
    render_coverage_review_markdown,
)
from scripts.render_health_coverage_review import write_health_coverage_review


def test_health_review_writer_matches_deterministic_renderer_bytes(tmp_path: Path) -> None:
    output_path = tmp_path / "health_coverage_review.md"

    written_path = write_health_coverage_review(output_path)

    expected = render_coverage_review_markdown(
        build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    ).encode("utf-8")
    actual = written_path.read_bytes()

    assert actual == expected
    assert b"\r\n" not in actual


def test_persisted_health_review_matches_current_registry() -> None:
    expected = render_coverage_review_markdown(
        build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    ).encode("utf-8")
    persisted = Path(
        "docs/architecture/HEALTH_INSURANCE_INTELLIGENCE_COVERAGE_REVIEW.md"
    ).read_bytes()

    assert persisted == expected
