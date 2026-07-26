"""Deterministic evaluator for generic topic completeness (MO-023I.3)."""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    RequirementResult,
    validate_output,
)
from insurance_intelligence.contracts.topic_completeness import (
    TopicCompletenessResult,
    TopicComponentDefinition,
    TopicComponentResult,
    TopicDefinition,
    build_completeness_result,
    build_component_result,
)


class TopicCompletenessEvaluationError(ValueError):
    """Raised when topic completeness cannot be evaluated safely."""


_UNRESOLVED_REQUIREMENT_STATUSES = frozenset(
    {
        "ENTITY_UNRESOLVED",
        "VERSION_UNRESOLVED",
        "FAILED_LINEAGE",
    }
)


def _authority_satisfied(
    component: TopicComponentDefinition,
    evidence: EvidencePackage,
) -> bool:
    return (
        component.minimum_authority == "ANY_GOVERNED"
        or evidence.authority_requirement == component.minimum_authority
    )


def _matching_evidence(
    component: TopicComponentDefinition,
    evidence_packages: tuple[EvidencePackage, ...],
) -> tuple[EvidencePackage, ...]:
    matches = [
        evidence
        for evidence in evidence_packages
        if evidence.field_or_topic == component.requirement_type
        and evidence.evidence_role in component.acceptable_evidence_roles
        and _authority_satisfied(component, evidence)
    ]
    return tuple(sorted(matches, key=lambda item: item.evidence_id))


def _requirement_results_for_evidence(
    evidence: tuple[EvidencePackage, ...],
    requirement_results: dict[str, RequirementResult],
) -> tuple[RequirementResult, ...]:
    ids = sorted({item.requirement_id for item in evidence})
    return tuple(
        requirement_results[requirement_id]
        for requirement_id in ids
        if requirement_id in requirement_results
    )


def _component_status(
    *,
    component: TopicComponentDefinition,
    matching_evidence: tuple[EvidencePackage, ...],
    requirement_results: tuple[RequirementResult, ...],
) -> tuple[str, tuple[str, ...]]:
    if not matching_evidence:
        return ("MISSING" if component.required else "NOT_APPLICABLE"), ()

    statuses = {result.status for result in requirement_results}
    if "CONFLICTING" in statuses:
        return "CONFLICTING", ("Resolved evidence contains an unresolved conflict.",)
    if statuses & _UNRESOLVED_REQUIREMENT_STATUSES:
        return "UNRESOLVED", (
            "Entity, version, or lineage resolution remains unresolved.",
        )
    if "PARTIALLY_SATISFIED" in statuses:
        return "PARTIAL", ("The component is only partially satisfied.",)

    accepted = set(component.acceptable_requirement_statuses)
    if not statuses or not statuses.issubset(accepted):
        return "MISSING", (
            "Available requirement results do not meet the component contract.",
        )

    limitations = sorted(
        {
            limitation
            for result in requirement_results
            for limitation in (
                result.missing_reason,
                *(() if result.authority_satisfied else ("Authority requirement not fully satisfied.",)),
                *(() if result.version_satisfied else ("Version requirement not fully satisfied.",)),
                *(() if result.lineage_satisfied else ("Lineage requirement not fully satisfied.",)),
            )
            if limitation
        }
    )
    if limitations or "SATISFIED_WITH_LIMITATIONS" in statuses:
        if not limitations:
            limitations.append("The component is satisfied with limitations.")
        return "SATISFIED_WITH_LIMITATIONS", tuple(limitations)
    return "SATISFIED", ()


def _apply_dependency_constraints(
    definition: TopicDefinition,
    results: tuple[TopicComponentResult, ...],
) -> tuple[TopicComponentResult, ...]:
    by_id = {result.component_id: result for result in results}
    adjusted: list[TopicComponentResult] = []

    for component in definition.components:
        result = by_id[component.component_id]
        blocked_dependencies = [
            dependency_id
            for dependency_id in component.dependency_component_ids
            if by_id[dependency_id].status
            not in {"SATISFIED", "SATISFIED_WITH_LIMITATIONS", "NOT_APPLICABLE"}
        ]
        if not blocked_dependencies or result.status in {"MISSING", "CONFLICTING"}:
            adjusted.append(result)
            continue

        adjusted.append(
            build_component_result(
                component_id=result.component_id,
                status="UNRESOLVED",
                matched_requirement_ids=result.matched_requirement_ids,
                matched_evidence_ids=result.matched_evidence_ids,
                limitations=(
                    *result.limitations,
                    "Blocked by unresolved dependencies: "
                    + ", ".join(sorted(blocked_dependencies)),
                ),
                confidence=min(result.confidence, 0.5),
            )
        )

    return tuple(adjusted)


def _derive_topic_status(
    definition: TopicDefinition,
    results: tuple[TopicComponentResult, ...],
) -> tuple[str, bool]:
    required_ids = {
        component.component_id
        for component in definition.components
        if component.required
    }
    required_results = [
        result for result in results if result.component_id in required_ids
    ]
    statuses = {result.status for result in required_results}

    if "CONFLICTING" in statuses:
        return "CONFLICTING", False
    if "UNRESOLVED" in statuses:
        if definition.unresolved_applicability_policy == "REQUIRE_CLARIFICATION":
            return "CLARIFICATION_REQUIRED", False
        return "PARTIAL", False
    if "PARTIAL" in statuses:
        return "PARTIAL", False
    if "MISSING" in statuses:
        if all(result.status == "MISSING" for result in required_results):
            return "NOT_AVAILABLE", False
        return "PARTIAL", False
    if "SATISFIED_WITH_LIMITATIONS" in statuses:
        return "COMPLETE_WITH_LIMITATIONS", True
    return "COMPLETE", True


def evaluate_topic_completeness(
    *,
    definition: TopicDefinition,
    evidence_output: EvidenceResolverOutput,
) -> TopicCompletenessResult:
    """Evaluate one generic topic definition against governed resolver output."""
    if not isinstance(definition, TopicDefinition):
        raise TopicCompletenessEvaluationError(
            "definition must be a TopicDefinition"
        )
    if not isinstance(evidence_output, EvidenceResolverOutput):
        raise TopicCompletenessEvaluationError(
            "evidence_output must be an EvidenceResolverOutput"
        )

    validate_output(evidence_output)
    requirement_by_id = {
        result.requirement_id: result
        for result in evidence_output.requirement_results
    }

    raw_results: list[TopicComponentResult] = []
    for component in definition.components:
        evidence = _matching_evidence(component, evidence_output.evidence_packages)
        requirements = _requirement_results_for_evidence(
            evidence,
            requirement_by_id,
        )
        status, limitations = _component_status(
            component=component,
            matching_evidence=evidence,
            requirement_results=requirements,
        )
        confidences = [item.confidence for item in evidence]
        confidences.extend(item.confidence for item in requirements)
        confidence = fmean(confidences) if confidences else 0.0

        raw_results.append(
            build_component_result(
                component_id=component.component_id,
                status=status,
                matched_requirement_ids=tuple(
                    result.requirement_id for result in requirements
                ),
                matched_evidence_ids=tuple(
                    item.evidence_id for item in evidence
                ),
                limitations=limitations,
                confidence=confidence,
            )
        )

    component_results = _apply_dependency_constraints(
        definition,
        tuple(raw_results),
    )
    topic_status, explanation_permitted = _derive_topic_status(
        definition,
        component_results,
    )

    required_ids = {
        component.component_id
        for component in definition.components
        if component.required
    }
    missing = tuple(
        result.component_id
        for result in component_results
        if result.component_id in required_ids and result.status == "MISSING"
    )
    conflicting = tuple(
        result.component_id
        for result in component_results
        if result.status == "CONFLICTING"
    )
    unresolved = tuple(
        result.component_id
        for result in component_results
        if result.status in {"PARTIAL", "UNRESOLVED"}
    )
    limitations = tuple(
        sorted(
            {
                limitation
                for result in component_results
                for limitation in result.limitations
            }
        )
    )
    required_confidences = [
        result.confidence
        for result in component_results
        if result.component_id in required_ids
    ]
    confidence = fmean(required_confidences) if required_confidences else 0.0

    return build_completeness_result(
        definition=definition,
        request_id=evidence_output.request_id,
        status=topic_status,
        component_results=component_results,
        missing_required_components=missing,
        conflicting_components=conflicting,
        unresolved_components=unresolved,
        limitations=limitations,
        explanation_permitted=explanation_permitted,
        confidence=confidence,
    )
