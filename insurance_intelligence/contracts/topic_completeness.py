"""Versioned executable contracts for generic topic completeness (MO-023I.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.evidence import EVIDENCE_ROLES, REQUIREMENT_STATUSES
from insurance_intelligence.contracts.reasoning_plan import AUTHORITY_REQUIREMENTS, DOMAIN_VALUES

SUPPORTED_CONTRACT_VERSION = "1.0"

COMPONENT_STATUSES = frozenset(
    {
        "SATISFIED",
        "SATISFIED_WITH_LIMITATIONS",
        "PARTIAL",
        "CONFLICTING",
        "MISSING",
        "NOT_APPLICABLE",
        "UNRESOLVED",
    }
)

COMPLETENESS_STATUSES = frozenset(
    {
        "COMPLETE",
        "COMPLETE_WITH_LIMITATIONS",
        "PARTIAL",
        "CONFLICTING",
        "NOT_AVAILABLE",
        "CLARIFICATION_REQUIRED",
        "INVALID_INPUT",
    }
)

CONFLICT_POLICIES = frozenset(
    {
        "BLOCK_ON_ANY_REQUIRED_COMPONENT_CONFLICT",
        "ALLOW_NON_MATERIAL_OPTIONAL_CONFLICTS",
    }
)

UNRESOLVED_APPLICABILITY_POLICIES = frozenset(
    {
        "REQUIRE_CLARIFICATION",
        "TREAT_AS_PARTIAL",
        "BLOCK_EXPLANATION",
    }
)

EXPLANATION_BLOCKING_STATUSES = frozenset(
    {"CONFLICTING", "NOT_AVAILABLE", "CLARIFICATION_REQUIRED", "INVALID_INPUT"}
)


class TopicCompletenessContractError(ValueError):
    """Raised when a topic-completeness contract is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TopicCompletenessContractError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise TopicCompletenessContractError(
            f"{label} must be one of {sorted(allowed)}; got {value!r}"
        )
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise TopicCompletenessContractError(f"{label} values must be unique")
    return result


def _confidence(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TopicCompletenessContractError("confidence must be a number")
    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise TopicCompletenessContractError("confidence must be between 0.0 and 1.0")
    return numeric


@dataclass(frozen=True)
class TopicComponentDefinition:
    component_id: str
    requirement_type: str
    required: bool
    acceptable_requirement_statuses: tuple[str, ...]
    acceptable_evidence_roles: tuple[str, ...]
    minimum_authority: str
    dependency_component_ids: tuple[str, ...]
    reason: str


def build_component_definition(
    *,
    component_id: str,
    requirement_type: str,
    required: bool,
    acceptable_requirement_statuses: Sequence[str],
    acceptable_evidence_roles: Sequence[str],
    minimum_authority: str,
    reason: str,
    dependency_component_ids: Sequence[str] = (),
) -> TopicComponentDefinition:
    if not isinstance(required, bool):
        raise TopicCompletenessContractError("required must be a boolean")

    requirement_statuses = _unique(
        acceptable_requirement_statuses, "acceptable_requirement_statuses"
    )
    if not requirement_statuses:
        raise TopicCompletenessContractError(
            "acceptable_requirement_statuses must not be empty"
        )
    for status in requirement_statuses:
        _member(status, REQUIREMENT_STATUSES, "acceptable_requirement_statuses[]")

    evidence_roles = _unique(acceptable_evidence_roles, "acceptable_evidence_roles")
    if not evidence_roles:
        raise TopicCompletenessContractError(
            "acceptable_evidence_roles must not be empty"
        )
    for role in evidence_roles:
        _member(role, EVIDENCE_ROLES, "acceptable_evidence_roles[]")

    component = TopicComponentDefinition(
        component_id=_text(component_id, "component_id"),
        requirement_type=_text(requirement_type, "requirement_type"),
        required=required,
        acceptable_requirement_statuses=requirement_statuses,
        acceptable_evidence_roles=evidence_roles,
        minimum_authority=_member(
            minimum_authority, AUTHORITY_REQUIREMENTS, "minimum_authority"
        ),
        dependency_component_ids=_unique(
            dependency_component_ids, "dependency_component_ids"
        ),
        reason=_text(reason, "reason"),
    )
    if component.component_id in component.dependency_component_ids:
        raise TopicCompletenessContractError("component cannot depend on itself")
    return component


@dataclass(frozen=True)
class TopicDefinition:
    contract_version: str
    topic_id: str
    topic_version: str
    domain: str
    components: tuple[TopicComponentDefinition, ...]
    minimum_required_components: int
    conflict_policy: str
    unresolved_applicability_policy: str


def _validate_dependencies(components: Sequence[TopicComponentDefinition]) -> None:
    component_ids = {component.component_id for component in components}
    adjacency = {
        component.component_id: component.dependency_component_ids
        for component in components
    }
    for component in components:
        unknown = set(component.dependency_component_ids) - component_ids
        if unknown:
            raise TopicCompletenessContractError(
                f"component {component.component_id} references unknown dependencies "
                f"{sorted(unknown)}"
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(component_id: str) -> None:
        if component_id in visiting:
            raise TopicCompletenessContractError(
                "component dependency graph must not contain cycles"
            )
        if component_id in visited:
            return
        visiting.add(component_id)
        for dependency_id in adjacency[component_id]:
            visit(dependency_id)
        visiting.remove(component_id)
        visited.add(component_id)

    for component_id in sorted(component_ids):
        visit(component_id)


def build_topic_definition(
    *,
    topic_id: str,
    topic_version: str,
    domain: str,
    components: Sequence[TopicComponentDefinition],
    minimum_required_components: int | None = None,
    conflict_policy: str = "BLOCK_ON_ANY_REQUIRED_COMPONENT_CONFLICT",
    unresolved_applicability_policy: str = "REQUIRE_CLARIFICATION",
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> TopicDefinition:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise TopicCompletenessContractError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}"
        )
    materialized = tuple(components)
    if not materialized:
        raise TopicCompletenessContractError("components must not be empty")
    if not all(isinstance(item, TopicComponentDefinition) for item in materialized):
        raise TopicCompletenessContractError(
            "components must contain TopicComponentDefinition values"
        )
    component_ids = [component.component_id for component in materialized]
    if len(component_ids) != len(set(component_ids)):
        raise TopicCompletenessContractError("component_id values must be unique")
    _validate_dependencies(materialized)

    required_count = sum(component.required for component in materialized)
    if required_count == 0:
        raise TopicCompletenessContractError(
            "topic definition must contain at least one required component"
        )
    minimum = required_count if minimum_required_components is None else minimum_required_components
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 0:
        raise TopicCompletenessContractError(
            "minimum_required_components must be a non-negative integer"
        )
    if minimum != required_count:
        raise TopicCompletenessContractError(
            "minimum_required_components must equal the number of required components"
        )

    return TopicDefinition(
        contract_version=contract_version,
        topic_id=_text(topic_id, "topic_id"),
        topic_version=_text(topic_version, "topic_version"),
        domain=_member(domain, DOMAIN_VALUES, "domain"),
        components=materialized,
        minimum_required_components=minimum,
        conflict_policy=_member(conflict_policy, CONFLICT_POLICIES, "conflict_policy"),
        unresolved_applicability_policy=_member(
            unresolved_applicability_policy,
            UNRESOLVED_APPLICABILITY_POLICIES,
            "unresolved_applicability_policy",
        ),
    )


@dataclass(frozen=True)
class TopicComponentResult:
    component_id: str
    status: str
    matched_requirement_ids: tuple[str, ...]
    matched_evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    confidence: float


def build_component_result(
    *,
    component_id: str,
    status: str,
    confidence: float,
    matched_requirement_ids: Sequence[str] = (),
    matched_evidence_ids: Sequence[str] = (),
    limitations: Sequence[str] = (),
) -> TopicComponentResult:
    validated_status = _member(status, COMPONENT_STATUSES, "status")
    requirement_ids = _unique(matched_requirement_ids, "matched_requirement_ids")
    evidence_ids = _unique(matched_evidence_ids, "matched_evidence_ids")
    validated_limitations = _unique(limitations, "limitations")

    if validated_status in {"SATISFIED", "SATISFIED_WITH_LIMITATIONS"}:
        if not requirement_ids:
            raise TopicCompletenessContractError(
                "satisfied component results must reference at least one requirement"
            )
        if not evidence_ids:
            raise TopicCompletenessContractError(
                "satisfied component results must reference at least one evidence item"
            )
    if validated_status == "SATISFIED_WITH_LIMITATIONS" and not validated_limitations:
        raise TopicCompletenessContractError(
            "SATISFIED_WITH_LIMITATIONS requires at least one limitation"
        )

    return TopicComponentResult(
        component_id=_text(component_id, "component_id"),
        status=validated_status,
        matched_requirement_ids=requirement_ids,
        matched_evidence_ids=evidence_ids,
        limitations=validated_limitations,
        confidence=_confidence(confidence),
    )


@dataclass(frozen=True)
class TopicCompletenessResult:
    contract_version: str
    topic_id: str
    topic_version: str
    request_id: str
    status: str
    component_results: tuple[TopicComponentResult, ...]
    missing_required_components: tuple[str, ...]
    conflicting_components: tuple[str, ...]
    unresolved_components: tuple[str, ...]
    limitations: tuple[str, ...]
    explanation_permitted: bool
    confidence: float


def build_completeness_result(
    *,
    definition: TopicDefinition,
    request_id: str,
    status: str,
    component_results: Sequence[TopicComponentResult],
    explanation_permitted: bool,
    confidence: float,
    missing_required_components: Sequence[str] = (),
    conflicting_components: Sequence[str] = (),
    unresolved_components: Sequence[str] = (),
    limitations: Sequence[str] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> TopicCompletenessResult:
    if not isinstance(definition, TopicDefinition):
        raise TopicCompletenessContractError("definition must be a TopicDefinition")
    if contract_version != definition.contract_version:
        raise TopicCompletenessContractError(
            "definition and result contract versions must match"
        )
    if not isinstance(explanation_permitted, bool):
        raise TopicCompletenessContractError(
            "explanation_permitted must be a boolean"
        )

    validated_status = _member(status, COMPLETENESS_STATUSES, "status")
    results = tuple(component_results)
    if not all(isinstance(item, TopicComponentResult) for item in results):
        raise TopicCompletenessContractError(
            "component_results must contain TopicComponentResult values"
        )

    definition_ids = {component.component_id for component in definition.components}
    required_ids = {
        component.component_id for component in definition.components if component.required
    }
    result_ids = [result.component_id for result in results]
    if len(result_ids) != len(set(result_ids)):
        raise TopicCompletenessContractError("component result IDs must be unique")
    unknown_results = set(result_ids) - definition_ids
    if unknown_results:
        raise TopicCompletenessContractError(
            f"component results reference unknown components {sorted(unknown_results)}"
        )

    missing = _unique(missing_required_components, "missing_required_components")
    conflicting = _unique(conflicting_components, "conflicting_components")
    unresolved = _unique(unresolved_components, "unresolved_components")
    for label, values in (
        ("missing_required_components", missing),
        ("conflicting_components", conflicting),
        ("unresolved_components", unresolved),
    ):
        unknown = set(values) - definition_ids
        if unknown:
            raise TopicCompletenessContractError(
                f"{label} references unknown components {sorted(unknown)}"
            )
    if not set(missing).issubset(required_ids):
        raise TopicCompletenessContractError(
            "missing_required_components may contain only required components"
        )

    status_by_id = {result.component_id: result.status for result in results}
    derived_missing = {
        component_id
        for component_id in required_ids
        if component_id not in status_by_id or status_by_id[component_id] == "MISSING"
    }
    derived_conflicting = {
        component_id
        for component_id, component_status in status_by_id.items()
        if component_status == "CONFLICTING"
    }
    derived_unresolved = {
        component_id
        for component_id, component_status in status_by_id.items()
        if component_status in {"PARTIAL", "UNRESOLVED"}
    }
    if set(missing) != derived_missing:
        raise TopicCompletenessContractError(
            "missing_required_components must exactly match required components that are absent or MISSING"
        )
    if set(conflicting) != derived_conflicting:
        raise TopicCompletenessContractError(
            "conflicting_components must exactly match CONFLICTING component results"
        )
    if set(unresolved) != derived_unresolved:
        raise TopicCompletenessContractError(
            "unresolved_components must exactly match PARTIAL or UNRESOLVED component results"
        )

    if validated_status == "COMPLETE":
        if set(result_ids) != definition_ids:
            raise TopicCompletenessContractError(
                "COMPLETE requires a result for every defined component"
            )
        if any(
            result.status not in {"SATISFIED", "NOT_APPLICABLE"}
            for result in results
        ):
            raise TopicCompletenessContractError(
                "COMPLETE requires every component to be SATISFIED or NOT_APPLICABLE"
            )
        if any(status_by_id[component_id] != "SATISFIED" for component_id in required_ids):
            raise TopicCompletenessContractError(
                "COMPLETE requires every required component to be SATISFIED"
            )
    if validated_status == "COMPLETE_WITH_LIMITATIONS":
        if missing or conflicting or unresolved:
            raise TopicCompletenessContractError(
                "COMPLETE_WITH_LIMITATIONS cannot list missing, conflicting, or unresolved components"
            )
        if not any(
            result.status == "SATISFIED_WITH_LIMITATIONS" for result in results
        ):
            raise TopicCompletenessContractError(
                "COMPLETE_WITH_LIMITATIONS requires at least one limited component"
            )
    if validated_status == "PARTIAL" and not (missing or unresolved):
        raise TopicCompletenessContractError(
            "PARTIAL requires a missing or unresolved component"
        )
    if validated_status == "CONFLICTING" and not conflicting:
        raise TopicCompletenessContractError(
            "CONFLICTING requires at least one conflicting component"
        )
    if validated_status == "NOT_AVAILABLE" and not missing:
        raise TopicCompletenessContractError(
            "NOT_AVAILABLE requires at least one missing required component"
        )
    if validated_status == "CLARIFICATION_REQUIRED" and not unresolved:
        raise TopicCompletenessContractError(
            "CLARIFICATION_REQUIRED requires at least one unresolved component"
        )

    if validated_status in EXPLANATION_BLOCKING_STATUSES and explanation_permitted:
        raise TopicCompletenessContractError(
            f"explanation_permitted cannot be true for {validated_status}"
        )
    if validated_status in {"COMPLETE", "COMPLETE_WITH_LIMITATIONS"} and not explanation_permitted:
        raise TopicCompletenessContractError(
            f"explanation_permitted must be true for {validated_status}"
        )

    return TopicCompletenessResult(
        contract_version=contract_version,
        topic_id=definition.topic_id,
        topic_version=definition.topic_version,
        request_id=_text(request_id, "request_id"),
        status=validated_status,
        component_results=results,
        missing_required_components=missing,
        conflicting_components=conflicting,
        unresolved_components=unresolved,
        limitations=_unique(limitations, "limitations"),
        explanation_permitted=explanation_permitted,
        confidence=_confidence(confidence),
    )
