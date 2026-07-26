"""Versioned executable contracts for generic governed-rule certification (MO-023J.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.evidence import EvidenceResolverOutput, validate_output
from insurance_intelligence.contracts.topic_completeness import (
    COMPLETENESS_STATUSES,
    COMPONENT_STATUSES,
    EXPLANATION_BLOCKING_STATUSES,
    TopicCompletenessResult,
)

SUPPORTED_CONTRACT_VERSION = "1.0"
CERTIFICATION_OUTCOMES = frozenset({"PASS", "FAIL", "BLOCKED"})


class RuleCertificationContractError(ValueError):
    """Raised when a governed-rule certification contract is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleCertificationContractError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise RuleCertificationContractError(
            f"{label} must be one of {sorted(allowed)}; got {value!r}"
        )
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise RuleCertificationContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class ComponentCertificationExpectation:
    component_id: str
    acceptable_statuses: tuple[str, ...]


def build_component_certification_expectation(
    *,
    component_id: str,
    acceptable_statuses: Sequence[str],
) -> ComponentCertificationExpectation:
    statuses = _unique(acceptable_statuses, "acceptable_statuses")
    if not statuses:
        raise RuleCertificationContractError("acceptable_statuses must not be empty")
    for status in statuses:
        _member(status, COMPONENT_STATUSES, "acceptable_statuses[]")
    return ComponentCertificationExpectation(
        component_id=_text(component_id, "component_id"),
        acceptable_statuses=statuses,
    )


@dataclass(frozen=True)
class RuleCertificationExpectation:
    contract_version: str
    certification_id: str
    governed_subject_reference: str
    topic_id: str
    topic_version: str
    expected_completeness_statuses: tuple[str, ...]
    expected_explanation_permitted: bool
    component_expectations: tuple[ComponentCertificationExpectation, ...]


def build_rule_certification_expectation(
    *,
    certification_id: str,
    governed_subject_reference: str,
    topic_id: str,
    topic_version: str,
    expected_completeness_statuses: Sequence[str],
    expected_explanation_permitted: bool,
    component_expectations: Sequence[ComponentCertificationExpectation],
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> RuleCertificationExpectation:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise RuleCertificationContractError(
            f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}"
        )
    if not isinstance(expected_explanation_permitted, bool):
        raise RuleCertificationContractError(
            "expected_explanation_permitted must be a boolean"
        )
    statuses = _unique(
        expected_completeness_statuses, "expected_completeness_statuses"
    )
    if not statuses:
        raise RuleCertificationContractError(
            "expected_completeness_statuses must not be empty"
        )
    for status in statuses:
        _member(status, COMPLETENESS_STATUSES, "expected_completeness_statuses[]")

    components = tuple(component_expectations)
    if not all(isinstance(item, ComponentCertificationExpectation) for item in components):
        raise RuleCertificationContractError(
            "component_expectations must contain ComponentCertificationExpectation values"
        )
    component_ids = [item.component_id for item in components]
    if len(component_ids) != len(set(component_ids)):
        raise RuleCertificationContractError(
            "component expectation IDs must be unique"
        )

    return RuleCertificationExpectation(
        contract_version=contract_version,
        certification_id=_text(certification_id, "certification_id"),
        governed_subject_reference=_text(
            governed_subject_reference, "governed_subject_reference"
        ),
        topic_id=_text(topic_id, "topic_id"),
        topic_version=_text(topic_version, "topic_version"),
        expected_completeness_statuses=statuses,
        expected_explanation_permitted=expected_explanation_permitted,
        component_expectations=components,
    )


@dataclass(frozen=True)
class ComponentCertificationCheck:
    component_id: str
    expected_statuses: tuple[str, ...]
    actual_status: str | None
    passed: bool


@dataclass(frozen=True)
class RuleCertificationResult:
    contract_version: str
    certification_id: str
    governed_subject_reference: str
    request_id: str
    resolution_id: str
    resolution_status: str
    evidence_sufficiency: str
    topic_id: str
    topic_version: str
    expected_completeness_statuses: tuple[str, ...]
    actual_completeness_status: str
    expected_explanation_permitted: bool
    actual_explanation_permitted: bool
    component_checks: tuple[ComponentCertificationCheck, ...]
    outcome: str
    failures: tuple[str, ...]
    limitations: tuple[str, ...]
    trace_references: tuple[str, ...]


def build_rule_certification_result(
    *,
    expectation: RuleCertificationExpectation,
    evidence_output: EvidenceResolverOutput,
    completeness_result: TopicCompletenessResult,
    trace_references: Sequence[str] = (),
    limitations: Sequence[str] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> RuleCertificationResult:
    if not isinstance(expectation, RuleCertificationExpectation):
        raise RuleCertificationContractError(
            "expectation must be a RuleCertificationExpectation"
        )
    if contract_version != expectation.contract_version:
        raise RuleCertificationContractError(
            "expectation and result contract versions must match"
        )
    if not isinstance(evidence_output, EvidenceResolverOutput):
        raise RuleCertificationContractError(
            "evidence_output must be an EvidenceResolverOutput"
        )
    if not isinstance(completeness_result, TopicCompletenessResult):
        raise RuleCertificationContractError(
            "completeness_result must be a TopicCompletenessResult"
        )
    validate_output(evidence_output)

    if completeness_result.request_id != evidence_output.request_id:
        raise RuleCertificationContractError(
            "evidence and completeness request IDs must match"
        )
    if completeness_result.topic_id != expectation.topic_id:
        raise RuleCertificationContractError(
            "expectation and completeness topic IDs must match"
        )
    if completeness_result.topic_version != expectation.topic_version:
        raise RuleCertificationContractError(
            "expectation and completeness topic versions must match"
        )

    actual_by_id = {
        component.component_id: component
        for component in completeness_result.component_results
    }
    checks = tuple(
        ComponentCertificationCheck(
            component_id=item.component_id,
            expected_statuses=item.acceptable_statuses,
            actual_status=(
                actual_by_id[item.component_id].status
                if item.component_id in actual_by_id
                else None
            ),
            passed=(
                item.component_id in actual_by_id
                and actual_by_id[item.component_id].status in item.acceptable_statuses
            ),
        )
        for item in expectation.component_expectations
    )

    failures: list[str] = []
    if completeness_result.status not in expectation.expected_completeness_statuses:
        failures.append(
            "Unexpected completeness status: " + completeness_result.status
        )
    if (
        completeness_result.explanation_permitted
        != expectation.expected_explanation_permitted
    ):
        failures.append("Explanation-permission expectation was not met.")
    failures.extend(
        f"Component expectation was not met: {check.component_id}"
        for check in checks
        if not check.passed
    )

    if not failures:
        outcome = "PASS"
    elif completeness_result.status in EXPLANATION_BLOCKING_STATUSES:
        outcome = "BLOCKED"
    else:
        outcome = "FAIL"

    combined_limitations = _unique(
        (
            *evidence_output.limitations,
            *completeness_result.limitations,
            *limitations,
        ),
        "limitations",
    )

    return RuleCertificationResult(
        contract_version=contract_version,
        certification_id=expectation.certification_id,
        governed_subject_reference=expectation.governed_subject_reference,
        request_id=evidence_output.request_id,
        resolution_id=evidence_output.resolution_id,
        resolution_status=evidence_output.resolution_status,
        evidence_sufficiency=evidence_output.sufficiency,
        topic_id=completeness_result.topic_id,
        topic_version=completeness_result.topic_version,
        expected_completeness_statuses=expectation.expected_completeness_statuses,
        actual_completeness_status=completeness_result.status,
        expected_explanation_permitted=expectation.expected_explanation_permitted,
        actual_explanation_permitted=completeness_result.explanation_permitted,
        component_checks=checks,
        outcome=_member(outcome, CERTIFICATION_OUTCOMES, "outcome"),
        failures=tuple(failures),
        limitations=combined_limitations,
        trace_references=_unique(trace_references, "trace_references"),
    )
