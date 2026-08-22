from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageRecord,
    ConceptCoverageStatus,
    EvidenceCoverageStatus,
    InsuranceIntelligenceCoverageRegistry,
    ProductCoverageRecord,
    ProductLifecycleStatus,
)
from insurance_intelligence.coverage_registry.reporting import (
    build_coverage_review_report,
    render_coverage_review_markdown,
)


def _concept(
    concept_id: str,
    *,
    status: ConceptCoverageStatus,
    comparison_ready: bool = False,
    decision_support_ready: bool = False,
    limitations: tuple[str, ...] = (),
) -> ConceptCoverageRecord:
    evidence = ()
    if status in {
        ConceptCoverageStatus.EVIDENCE_AVAILABLE,
        ConceptCoverageStatus.NORMALIZED,
        ConceptCoverageStatus.GOVERNED,
        ConceptCoverageStatus.CERTIFIED,
        ConceptCoverageStatus.PARTIAL,
        ConceptCoverageStatus.SOURCE_LIMITED,
    }:
        evidence = (f"evidence:{concept_id}",)
    return ConceptCoverageRecord(
        concept_id=concept_id,
        status=status,
        evidence_reference_ids=evidence,
        comparison_ready=comparison_ready,
        decision_support_ready=decision_support_ready,
        limitations=limitations,
    )


def _product(
    *,
    reference: str,
    insurer: str,
    product_id: str,
    name: str,
    uin: str,
    concepts: tuple[ConceptCoverageRecord, ...],
) -> ProductCoverageRecord:
    return ProductCoverageRecord(
        product_reference=reference,
        insurer_id=insurer,
        product_id=product_id,
        canonical_product_name=name,
        uin=uin,
        lifecycle_status=ProductLifecycleStatus.STATUS_UNKNOWN,
        evidence_status=EvidenceCoverageStatus.PARTIAL,
        concepts=concepts,
    )


def _registry() -> InsuranceIntelligenceCoverageRegistry:
    first = _product(
        reference="insurer_a:product_a:v1",
        insurer="insurer_a",
        product_id="product_a",
        name="Product A",
        uin="UIN-A",
        concepts=(
            _concept(
                "copayment",
                status=ConceptCoverageStatus.CERTIFIED,
                comparison_ready=True,
            ),
            _concept(
                "waiting_periods",
                status=ConceptCoverageStatus.NOT_AUTOMATED,
                limitations=("Waiting-period automation is not certified.",),
            ),
        ),
    )
    second = _product(
        reference="insurer_b:product_b:v1",
        insurer="insurer_b",
        product_id="product_b",
        name="Product B",
        uin="UIN-B",
        concepts=(
            _concept(
                "room_rent_restriction",
                status=ConceptCoverageStatus.SOURCE_LIMITED,
                limitations=("Only limited governed evidence is available.",),
            ),
        ),
    )
    return InsuranceIntelligenceCoverageRegistry((first, second))


def test_report_is_derived_only_from_registry_state() -> None:
    report = build_coverage_review_report(_registry())
    assert tuple(item.insurer_id for item in report.insurer_summaries) == (
        "insurer_a",
        "insurer_b",
    )
    assert all(item.lifecycle_unknown_count == 1 for item in report.insurer_summaries)
    assert all(item.lifecycle_known_count == 0 for item in report.insurer_summaries)


def test_matrix_marks_absent_concepts_not_covered_without_mutating_registry() -> None:
    report = build_coverage_review_report(_registry())
    copayment = next(row for row in report.concept_matrix if row.concept_id == "copayment")
    statuses = dict(copayment.product_statuses)
    assert statuses["insurer_a:product_a:v1"] is ConceptCoverageStatus.CERTIFIED
    assert statuses["insurer_b:product_b:v1"] is ConceptCoverageStatus.NOT_COVERED


def test_report_surfaces_recorded_gaps_and_unknown_lifecycle() -> None:
    report = build_coverage_review_report(_registry())
    gap_keys = {(gap.gap_type, gap.subject_reference, gap.concept_id, gap.status) for gap in report.gaps}
    assert (
        "CONCEPT_COVERAGE_GAP",
        "insurer_a:product_a:v1",
        "waiting_periods",
        "NOT_AUTOMATED",
    ) in gap_keys
    assert (
        "CONCEPT_COVERAGE_GAP",
        "insurer_b:product_b:v1",
        "room_rent_restriction",
        "SOURCE_LIMITED",
    ) in gap_keys
    assert sum(1 for gap in report.gaps if gap.gap_type == "LIFECYCLE_STATUS_UNKNOWN") == 2


def test_rendered_review_has_no_product_scoring_or_recommendation_semantics() -> None:
    report = build_coverage_review_report(_registry())
    markdown = render_coverage_review_markdown(report)
    assert "## Insurer Summary" in markdown
    assert "## Product Coverage" in markdown
    assert "## Concept Coverage Matrix" in markdown
    assert "## Coverage Gaps" in markdown
    forbidden = {"winner", "recommendation", "preferred product", "score"}
    assert all(term not in markdown.lower() for term in forbidden)
