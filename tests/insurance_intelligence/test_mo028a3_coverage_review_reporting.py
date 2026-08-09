from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageStatus,
    ProductLifecycleStatus,
)
from insurance_intelligence.coverage_registry.health_seed import HEALTH_COVERAGE_REGISTRY
from insurance_intelligence.coverage_registry.reporting import (
    build_coverage_review_report,
    render_coverage_review_markdown,
)


def test_report_summarizes_both_seeded_insurers() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    assert tuple(item.insurer_id for item in report.insurer_summaries) == (
        "aditya_birla_health",
        "star_health",
    )
    assert all(item.product_count == 1 for item in report.insurer_summaries)


def test_report_preserves_unknown_lifecycle_without_inference() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    assert all(
        item.lifecycle_status is ProductLifecycleStatus.STATUS_UNKNOWN
        for item in report.product_summaries
    )
    assert all(item.lifecycle_known_count == 0 for item in report.insurer_summaries)
    assert all(item.lifecycle_unknown_count == 1 for item in report.insurer_summaries)


def test_product_summary_counts_only_actual_certified_concepts() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    by_name = {item.canonical_product_name: item for item in report.product_summaries}
    assert by_name["Star Comprehensive Insurance Policy"].certified_concept_count == 3
    assert by_name["Activ One NXT"].certified_concept_count == 1


def test_concept_matrix_marks_absent_product_concept_not_covered() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    copay = next(item for item in report.concept_matrix if item.concept_id == "copayment")
    statuses = dict(copay.product_statuses)
    activ = next(
        item.product_reference
        for item in report.product_summaries
        if item.canonical_product_name == "Activ One NXT"
    )
    assert statuses[activ] is ConceptCoverageStatus.NOT_COVERED


def test_report_surfaces_source_limited_and_not_automated_gaps() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    statuses = {(item.concept_id, item.status) for item in report.gaps}
    assert ("room_rent_restriction", "SOURCE_LIMITED") in statuses
    assert ("waiting_periods", "NOT_AUTOMATED") in statuses


def test_report_surfaces_lifecycle_unknown_as_separate_gap_type() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    lifecycle_gaps = [item for item in report.gaps if item.gap_type == "LIFECYCLE_STATUS_UNKNOWN"]
    assert len(lifecycle_gaps) == 2
    assert all(item.concept_id is None for item in lifecycle_gaps)


def test_markdown_contains_all_required_review_sections() -> None:
    markdown = render_coverage_review_markdown(
        build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    )
    assert "## Insurer Summary" in markdown
    assert "## Product Coverage" in markdown
    assert "## Concept Coverage Matrix" in markdown
    assert "## Coverage Gaps" in markdown
    assert "Lifecycle" in markdown


def test_markdown_contains_seeded_product_identity_and_uins() -> None:
    markdown = render_coverage_review_markdown(
        build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    )
    assert "Star Comprehensive Insurance Policy" in markdown
    assert "SHAHLIP26044V092526" in markdown
    assert "Activ One NXT" in markdown
    assert "ADIHLIP24097V012324" in markdown


def test_review_contract_has_no_scoring_or_recommendation_fields() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    forbidden = {
        "score",
        "rating",
        "rank",
        "winner",
        "recommendation",
        "suitability",
        "preferred_product",
    }
    assert forbidden.isdisjoint(report.__dataclass_fields__)
    assert forbidden.isdisjoint(report.product_summaries[0].__dataclass_fields__)
