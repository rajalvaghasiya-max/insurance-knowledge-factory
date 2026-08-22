"""Deterministic review reporting for the MO-028A coverage registry.

The report is an internal governance/readiness view. It summarizes only registry
state already present in governed coverage records and derives gaps mechanically.
It does not fetch external data, infer product lifecycle, score products, or make
recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageStatus,
    InsuranceIntelligenceCoverageRegistry,
    ProductCoverageRecord,
    ProductLifecycleStatus,
)


@dataclass(frozen=True)
class InsurerCoverageSummary:
    insurer_id: str
    product_count: int
    lifecycle_known_count: int
    lifecycle_unknown_count: int
    comparison_ready_product_count: int
    decision_support_ready_product_count: int


@dataclass(frozen=True)
class ProductCoverageSummary:
    product_reference: str
    insurer_id: str
    canonical_product_name: str
    uin: str
    lifecycle_status: ProductLifecycleStatus
    concept_count: int
    certified_concept_count: int
    comparison_ready_concept_count: int
    decision_support_ready_concept_count: int


@dataclass(frozen=True)
class ConceptCoverageMatrixRow:
    concept_id: str
    product_statuses: tuple[tuple[str, ConceptCoverageStatus], ...]


@dataclass(frozen=True)
class CoverageGap:
    gap_type: str
    subject_reference: str
    concept_id: str | None
    status: str
    explanation: str


@dataclass(frozen=True)
class CoverageReviewReport:
    insurer_summaries: tuple[InsurerCoverageSummary, ...]
    product_summaries: tuple[ProductCoverageSummary, ...]
    concept_matrix: tuple[ConceptCoverageMatrixRow, ...]
    gaps: tuple[CoverageGap, ...]


def _product_has_comparison_ready(product: ProductCoverageRecord) -> bool:
    return bool(product.comparison_ready_concept_ids)


def _product_has_decision_ready(product: ProductCoverageRecord) -> bool:
    return bool(product.decision_support_ready_concept_ids)


def build_coverage_review_report(
    registry: InsuranceIntelligenceCoverageRegistry,
) -> CoverageReviewReport:
    """Build a deterministic review report from one validated coverage registry."""

    if type(registry) is not InsuranceIntelligenceCoverageRegistry:
        raise TypeError("registry must be an exact InsuranceIntelligenceCoverageRegistry")

    insurer_summaries = []
    for insurer_id in registry.insurer_ids:
        products = registry.products_for_insurer(insurer_id)
        known = tuple(
            item for item in products
            if item.lifecycle_status is not ProductLifecycleStatus.STATUS_UNKNOWN
        )
        insurer_summaries.append(
            InsurerCoverageSummary(
                insurer_id=insurer_id,
                product_count=len(products),
                lifecycle_known_count=len(known),
                lifecycle_unknown_count=len(products) - len(known),
                comparison_ready_product_count=sum(
                    1 for item in products if _product_has_comparison_ready(item)
                ),
                decision_support_ready_product_count=sum(
                    1 for item in products if _product_has_decision_ready(item)
                ),
            )
        )

    product_summaries = tuple(
        ProductCoverageSummary(
            product_reference=product.product_reference,
            insurer_id=product.insurer_id,
            canonical_product_name=product.canonical_product_name,
            uin=product.uin,
            lifecycle_status=product.lifecycle_status,
            concept_count=len(product.concepts),
            certified_concept_count=sum(
                1 for item in product.concepts
                if item.status is ConceptCoverageStatus.CERTIFIED
            ),
            comparison_ready_concept_count=len(product.comparison_ready_concept_ids),
            decision_support_ready_concept_count=len(product.decision_support_ready_concept_ids),
        )
        for product in registry.products
    )

    concept_ids = tuple(
        sorted({concept.concept_id for product in registry.products for concept in product.concepts})
    )
    matrix = []
    for concept_id in concept_ids:
        statuses = []
        for product in registry.products:
            match = next(
                (item for item in product.concepts if item.concept_id == concept_id),
                None,
            )
            statuses.append(
                (
                    product.product_reference,
                    match.status if match is not None else ConceptCoverageStatus.NOT_COVERED,
                )
            )
        matrix.append(
            ConceptCoverageMatrixRow(
                concept_id=concept_id,
                product_statuses=tuple(statuses),
            )
        )

    gaps = []
    for product in registry.products:
        if product.lifecycle_status is ProductLifecycleStatus.STATUS_UNKNOWN:
            gaps.append(
                CoverageGap(
                    gap_type="LIFECYCLE_STATUS_UNKNOWN",
                    subject_reference=product.product_reference,
                    concept_id=None,
                    status=product.lifecycle_status.value,
                    explanation=(
                        "Product lifecycle is not yet supported by governed lifecycle evidence."
                    ),
                )
            )
        for concept in product.concepts:
            if concept.status in {
                ConceptCoverageStatus.NOT_COVERED,
                ConceptCoverageStatus.PARTIAL,
                ConceptCoverageStatus.SOURCE_LIMITED,
                ConceptCoverageStatus.BLOCKED,
                ConceptCoverageStatus.NOT_AUTOMATED,
            }:
                gaps.append(
                    CoverageGap(
                        gap_type="CONCEPT_COVERAGE_GAP",
                        subject_reference=product.product_reference,
                        concept_id=concept.concept_id,
                        status=concept.status.value,
                        explanation=(
                            "; ".join(concept.limitations)
                            if concept.limitations
                            else "Concept is not fully governed for downstream use."
                        ),
                    )
                )

    return CoverageReviewReport(
        insurer_summaries=tuple(insurer_summaries),
        product_summaries=product_summaries,
        concept_matrix=tuple(matrix),
        gaps=tuple(
            sorted(
                gaps,
                key=lambda item: (
                    item.gap_type,
                    item.subject_reference,
                    item.concept_id or "",
                    item.status,
                ),
            )
        ),
    )


def render_coverage_review_markdown(report: CoverageReviewReport) -> str:
    """Render a stable Markdown review view without introducing new facts."""

    if type(report) is not CoverageReviewReport:
        raise TypeError("report must be an exact CoverageReviewReport")

    lines = ["# Insurance Intelligence Coverage Review", "", "## Insurer Summary", ""]
    lines.append(
        "| Insurer | Products | Lifecycle known | Lifecycle unknown | Comparison-ready products | Decision-support-ready products |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")
    for item in report.insurer_summaries:
        lines.append(
            f"| {item.insurer_id} | {item.product_count} | {item.lifecycle_known_count} | "
            f"{item.lifecycle_unknown_count} | {item.comparison_ready_product_count} | "
            f"{item.decision_support_ready_product_count} |"
        )

    lines.extend(["", "## Product Coverage", ""])
    lines.append(
        "| Insurer | Product | UIN | Lifecycle | Concepts | Certified | Comparison-ready | Decision-support-ready |"
    )
    lines.append("|---|---|---|---|---:|---:|---:|---:|")
    for item in report.product_summaries:
        lines.append(
            f"| {item.insurer_id} | {item.canonical_product_name} | {item.uin} | "
            f"{item.lifecycle_status.value} | {item.concept_count} | {item.certified_concept_count} | "
            f"{item.comparison_ready_concept_count} | {item.decision_support_ready_concept_count} |"
        )

    product_refs = tuple(item.product_reference for item in report.product_summaries)
    lines.extend(["", "## Concept Coverage Matrix", ""])
    lines.append("| Concept | " + " | ".join(product_refs) + " |")
    lines.append("|---|" + "---|" * len(product_refs))
    for row in report.concept_matrix:
        by_product = dict(row.product_statuses)
        lines.append(
            "| " + row.concept_id + " | "
            + " | ".join(by_product[ref].value for ref in product_refs)
            + " |"
        )

    lines.extend(["", "## Coverage Gaps", ""])
    if not report.gaps:
        lines.append("No governed coverage gaps are currently recorded.")
    else:
        lines.append("| Gap | Product | Concept | Status | Explanation |")
        lines.append("|---|---|---|---|---|")
        for gap in report.gaps:
            explanation = gap.explanation.replace("|", "\\|")
            lines.append(
                f"| {gap.gap_type} | {gap.subject_reference} | {gap.concept_id or '-'} | "
                f"{gap.status} | {explanation} |"
            )

    return "\n".join(lines) + "\n"


__all__ = [
    "ConceptCoverageMatrixRow",
    "CoverageGap",
    "CoverageReviewReport",
    "InsurerCoverageSummary",
    "ProductCoverageSummary",
    "build_coverage_review_report",
    "render_coverage_review_markdown",
]
