"""Governed interaction decision units for MO-027F2.

This layer groups per-dimension MO-027F alignment findings only where MO-026 already
records a MATERIAL or CRITICAL interaction between dimensions. It preserves each
source finding unchanged, exposes missing linked dimensions, and never computes
claim admissibility, an aggregate score, a net product direction, or a recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.assessment_contracts import InteractionSeverity
from insurance_intelligence.decision_support.dimension_alignment import (
    DimensionAlignmentFinding,
)


class InteractionClusterError(ValueError):
    """Raised when an interaction decision unit violates a governance invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InteractionClusterError(f"{field_name} must be non-empty text")
    return value.strip()


class InteractionDecisionUnitStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE_LINKED_DIMENSION = "INCOMPLETE_LINKED_DIMENSION"


@dataclass(frozen=True)
class InteractionDecisionUnit:
    unit_id: str
    product_reference: str
    dimension_ids: tuple[str, ...]
    findings: tuple[DimensionAlignmentFinding, ...]
    missing_linked_dimension_ids: tuple[str, ...]
    status: InteractionDecisionUnitStatus
    explanation: str
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in ("unit_id", "product_reference", "explanation", "contract_version"):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.dimension_ids, tuple) or len(self.dimension_ids) < 2:
            raise InteractionClusterError("interaction unit requires at least two dimension ids")
        if not all(isinstance(item, str) and item.strip() for item in self.dimension_ids):
            raise InteractionClusterError("dimension_ids must contain non-empty text")
        if len(self.dimension_ids) != len(set(self.dimension_ids)):
            raise InteractionClusterError("dimension_ids must not contain duplicates")
        if not isinstance(self.findings, tuple) or not self.findings:
            raise InteractionClusterError("findings must be a non-empty tuple")
        if not all(type(item) is DimensionAlignmentFinding for item in self.findings):
            raise InteractionClusterError(
                "findings must contain exact DimensionAlignmentFinding values"
            )
        if any(item.product_reference != self.product_reference for item in self.findings):
            raise InteractionClusterError(
                "all interaction-unit findings must belong to the same product"
            )
        finding_ids = tuple(item.dimension_id for item in self.findings)
        if len(finding_ids) != len(set(finding_ids)):
            raise InteractionClusterError("findings must not duplicate dimensions")
        if not set(finding_ids).issubset(set(self.dimension_ids)):
            raise InteractionClusterError(
                "finding dimensions must be contained in interaction-unit dimensions"
            )
        if not isinstance(self.missing_linked_dimension_ids, tuple) or not all(
            isinstance(item, str) and item.strip() for item in self.missing_linked_dimension_ids
        ):
            raise InteractionClusterError(
                "missing_linked_dimension_ids must contain non-empty text values"
            )
        if len(self.missing_linked_dimension_ids) != len(set(self.missing_linked_dimension_ids)):
            raise InteractionClusterError(
                "missing_linked_dimension_ids must not contain duplicates"
            )
        expected_missing = set(self.dimension_ids) - set(finding_ids)
        if expected_missing != set(self.missing_linked_dimension_ids):
            raise InteractionClusterError(
                "missing_linked_dimension_ids must exactly match dimensions absent from findings"
            )
        if not isinstance(self.status, InteractionDecisionUnitStatus):
            raise InteractionClusterError("status must be an InteractionDecisionUnitStatus")
        expected_status = (
            InteractionDecisionUnitStatus.INCOMPLETE_LINKED_DIMENSION
            if self.missing_linked_dimension_ids
            else InteractionDecisionUnitStatus.COMPLETE
        )
        if self.status is not expected_status:
            raise InteractionClusterError(
                "interaction-unit status must reflect whether linked dimensions are missing"
            )

        object.__setattr__(self, "dimension_ids", tuple(sorted(self.dimension_ids)))
        object.__setattr__(
            self,
            "findings",
            tuple(sorted(self.findings, key=lambda item: item.dimension_id)),
        )
        object.__setattr__(
            self,
            "missing_linked_dimension_ids",
            tuple(sorted(self.missing_linked_dimension_ids)),
        )


def _material_edges(
    findings: tuple[DimensionAlignmentFinding, ...],
) -> tuple[tuple[str, str], ...]:
    edges: set[tuple[str, str]] = set()
    for finding in findings:
        for interaction in finding.interaction_references:
            if interaction.severity not in {
                InteractionSeverity.MATERIAL,
                InteractionSeverity.CRITICAL,
            }:
                continue
            pair = tuple(sorted((finding.dimension_id, interaction.target_dimension_id)))
            if pair[0] != pair[1]:
                edges.add(pair)
    return tuple(sorted(edges))


def build_interaction_decision_units(
    *,
    product_reference: str,
    findings: tuple[DimensionAlignmentFinding, ...],
) -> tuple[InteractionDecisionUnit, ...]:
    """Build connected decision units from governed material/critical interactions."""

    product_reference = _required_text(product_reference, "product_reference")
    if not isinstance(findings, tuple) or not all(
        type(item) is DimensionAlignmentFinding for item in findings
    ):
        raise InteractionClusterError(
            "findings must contain exact DimensionAlignmentFinding values"
        )
    if any(item.product_reference != product_reference for item in findings):
        raise InteractionClusterError("all findings must belong to product_reference")
    ids = tuple(item.dimension_id for item in findings)
    if len(ids) != len(set(ids)):
        raise InteractionClusterError("findings must not duplicate dimensions")

    edges = _material_edges(findings)
    if not edges:
        return ()

    adjacency: dict[str, set[str]] = {}
    for left, right in edges:
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)

    finding_map = {item.dimension_id: item for item in findings}
    visited: set[str] = set()
    units: list[InteractionDecisionUnit] = []

    for start in sorted(adjacency):
        if start in visited:
            continue
        stack = [start]
        component: set[str] = set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            visited.add(node)
            stack.extend(sorted(adjacency.get(node, ()), reverse=True))

        component_ids = tuple(sorted(component))
        component_findings = tuple(
            finding_map[dimension_id]
            for dimension_id in component_ids
            if dimension_id in finding_map
        )
        missing = tuple(
            dimension_id
            for dimension_id in component_ids
            if dimension_id not in finding_map
        )
        status = (
            InteractionDecisionUnitStatus.INCOMPLETE_LINKED_DIMENSION
            if missing
            else InteractionDecisionUnitStatus.COMPLETE
        )
        if missing:
            explanation = (
                "These dimensions are connected by governed material or critical interactions, "
                "but at least one linked dimension is absent from the current alignment set. "
                "The available findings must not be interpreted independently or as a complete interaction analysis."
            )
        else:
            explanation = (
                "These dimensions are connected by governed material or critical interactions and "
                "must be interpreted together. The unit preserves local findings without computing "
                "claim admissibility or an aggregate product verdict."
            )

        units.append(
            InteractionDecisionUnit(
                unit_id=(
                    "interaction_unit:"
                    + product_reference.replace(":", "_")
                    + ":"
                    + "__".join(component_ids)
                ),
                product_reference=product_reference,
                dimension_ids=component_ids,
                findings=component_findings,
                missing_linked_dimension_ids=missing,
                status=status,
                explanation=explanation,
            )
        )

    return tuple(sorted(units, key=lambda item: item.dimension_ids))


__all__ = [
    "InteractionClusterError",
    "InteractionDecisionUnit",
    "InteractionDecisionUnitStatus",
    "build_interaction_decision_units",
]
