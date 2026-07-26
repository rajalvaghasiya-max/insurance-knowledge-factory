"""Reusable insurer-independent certification fixtures (MO-023J.3)."""

from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.contracts.rule_certification import (
    RuleCertificationExpectation,
    build_component_certification_expectation,
    build_rule_certification_expectation,
)


@dataclass(frozen=True)
class RuleCertificationCaseFixture:
    """One deterministic certification input and its expected runner outcome."""

    case_id: str
    description: str
    domain: str
    expectation: RuleCertificationExpectation
    evidence_output: EvidenceResolverOutput
    expected_outcome: str


def _lineage() -> Lineage:
    return Lineage(
        source_artifact_path="fixtures/source.txt",
        source_artifact_sha256="a" * 64,
        governed_record_path="fixtures/governed.json",
        governed_record_sha256="b" * 64,
        binding_reference="binding:generic",
        projection_reference="projection:generic",
        lineage_status="VERIFIED",
    )


def _requirement(
    requirement_id: str,
    *,
    status: str = "SATISFIED",
    evidence_id: str | None = None,
    missing_reason: str | None = None,
) -> RequirementResult:
    return RequirementResult(
        requirement_id=requirement_id,
        status=status,
        matched_evidence_ids=((evidence_id,) if evidence_id is not None else ()),
        rejected_candidate_ids=(),
        missing_reason=missing_reason,
        authority_satisfied=status not in {"MISSING", "ENTITY_UNRESOLVED", "VERSION_UNRESOLVED", "FAILED_LINEAGE"},
        version_satisfied=status not in {"VERSION_UNRESOLVED"},
        lineage_satisfied=status not in {"FAILED_LINEAGE"},
        conflict_status="UNRESOLVED" if status == "CONFLICTING" else "NONE",
        confidence=1.0 if status == "SATISFIED" else 0.5,
    )


def _evidence(
    evidence_id: str,
    requirement_id: str,
    field_or_topic: str,
    *,
    claim: str,
) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference="subject:generic",
        governed_entity_reference="entity:generic",
        field_or_topic=field_or_topic,
        claim=claim,
        evidence_role="DEFINING",
        source_type="GOVERNED_FIXTURE",
        document_reference="document:generic",
        document_version="1.0",
        effective_from=None,
        effective_to=None,
        page=None,
        section="Generic certification fixture",
        source_excerpt=claim,
        normalized_fact_reference=f"fact:{requirement_id}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(),
        retrieval_basis=("generic_fixture",),
        confidence=1.0,
    )


def _output(
    case_id: str,
    *,
    evidence: tuple[EvidencePackage, ...],
    requirements: tuple[RequirementResult, ...],
    sufficiency: str,
    resolution_status: str,
    limitations: tuple[str, ...] = (),
) -> EvidenceResolverOutput:
    return EvidenceResolverOutput(
        contract_version="1.0",
        request_id=f"request:{case_id}",
        resolution_id=f"resolution:{case_id}",
        evidence_packages=evidence,
        requirement_results=requirements,
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=tuple(
            result.requirement_id for result in requirements if result.status == "MISSING"
        ),
        sufficiency=sufficiency,
        limitations=limitations,
        resolution_trace=(),
        resolution_status=resolution_status,
        confidence=1.0 if resolution_status == "RESOLVED" else 0.5,
    )


def _component(component_id: str, *statuses: str):
    return build_component_certification_expectation(
        component_id=component_id,
        acceptable_statuses=statuses,
    )


def build_complete_conditional_obligation_case() -> RuleCertificationCaseFixture:
    case_id = "generic_complete_conditional_obligation"
    fields = (
        ("obligation_value", "OBLIGATION_VALUE"),
        ("trigger_condition", "TRIGGER_CONDITION"),
        ("applicability_scope", "APPLICABILITY_SCOPE"),
    )
    evidence = tuple(
        _evidence(f"evidence:{component}", f"requirement:{component}", field, claim=f"Resolved {component}.")
        for component, field in fields
    )
    requirements = tuple(
        _requirement(f"requirement:{component}", evidence_id=f"evidence:{component}")
        for component, _ in fields
    )
    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference="rule:generic:conditional-obligation",
        topic_id="conditional_obligation",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(_component(component, "SATISFIED") for component, _ in fields),
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description="A complete conditional obligation with every required semantic component.",
        domain="health",
        expectation=expectation,
        evidence_output=_output(
            case_id,
            evidence=evidence,
            requirements=requirements,
            sufficiency="COMPLETE",
            resolution_status="RESOLVED",
        ),
        expected_outcome="PASS",
    )


def build_partial_coverage_limit_case() -> RuleCertificationCaseFixture:
    case_id = "generic_partial_coverage_limit"
    present = (
        ("covered_subject", "COVERED_SUBJECT"),
        ("limit_value", "LIMIT_VALUE"),
        ("applicability_scope", "APPLICABILITY_SCOPE"),
    )
    evidence = tuple(
        _evidence(f"evidence:{component}", f"requirement:{component}", field, claim=f"Resolved {component}.")
        for component, field in present
    )
    requirements = (
        *tuple(
            _requirement(f"requirement:{component}", evidence_id=f"evidence:{component}")
            for component, _ in present
        ),
        _requirement(
            "requirement:limit_basis",
            status="MISSING",
            missing_reason="The limit basis was not available.",
        ),
    )
    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference="rule:generic:coverage-limit",
        topic_id="coverage_limit",
        topic_version="1.0",
        expected_completeness_statuses=("PARTIAL",),
        expected_explanation_permitted=False,
        component_expectations=(
            _component("covered_subject", "SATISFIED"),
            _component("limit_value", "SATISFIED"),
            _component("limit_basis", "MISSING"),
            _component("applicability_scope", "SATISFIED"),
        ),
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description="A coverage limit missing the required basis on which the limit applies.",
        domain="health",
        expectation=expectation,
        evidence_output=_output(
            case_id,
            evidence=evidence,
            requirements=requirements,
            sufficiency="PARTIAL",
            resolution_status="PARTIALLY_RESOLVED",
            limitations=("The limit basis remains unavailable.",),
        ),
        expected_outcome="PASS",
    )


def build_conflicting_waiting_period_case() -> RuleCertificationCaseFixture:
    case_id = "generic_conflicting_waiting_period"
    fields = (
        ("waiting_period_duration", "WAITING_PERIOD_DURATION"),
        ("waiting_period_subject", "WAITING_PERIOD_SUBJECT"),
        ("start_basis", "WAITING_PERIOD_START_BASIS"),
        ("applicability_scope", "APPLICABILITY_SCOPE"),
    )
    evidence = tuple(
        _evidence(f"evidence:{component}", f"requirement:{component}", field, claim=f"Resolved {component}.")
        for component, field in fields
    )
    requirements = tuple(
        _requirement(
            f"requirement:{component}",
            status="CONFLICTING" if component == "waiting_period_duration" else "SATISFIED",
            evidence_id=f"evidence:{component}",
        )
        for component, _ in fields
    )
    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference="rule:generic:waiting-period",
        topic_id="waiting_period",
        topic_version="1.0",
        expected_completeness_statuses=("CONFLICTING",),
        expected_explanation_permitted=False,
        component_expectations=(
            _component("waiting_period_duration", "CONFLICTING"),
            _component("waiting_period_subject", "SATISFIED"),
            _component("start_basis", "SATISFIED"),
            _component("applicability_scope", "SATISFIED"),
        ),
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description="A waiting period whose required duration evidence remains conflicting.",
        domain="health",
        expectation=expectation,
        evidence_output=_output(
            case_id,
            evidence=evidence,
            requirements=requirements,
            sufficiency="CONFLICTING",
            resolution_status="CONFLICTING",
            limitations=("The waiting-period duration conflict is unresolved.",),
        ),
        expected_outcome="PASS",
    )


def build_blocked_missing_waiting_period_case() -> RuleCertificationCaseFixture:
    case_id = "generic_blocked_missing_waiting_period"
    required_components = (
        "waiting_period_duration",
        "waiting_period_subject",
        "start_basis",
        "applicability_scope",
    )
    requirements = tuple(
        _requirement(
            f"requirement:{component}",
            status="MISSING",
            missing_reason=f"Missing {component}.",
        )
        for component in required_components
    )
    expectation = build_rule_certification_expectation(
        certification_id=case_id,
        governed_subject_reference="rule:generic:missing-waiting-period",
        topic_id="waiting_period",
        topic_version="1.0",
        expected_completeness_statuses=("COMPLETE",),
        expected_explanation_permitted=True,
        component_expectations=tuple(
            _component(component, "SATISFIED") for component in required_components
        ),
    )
    return RuleCertificationCaseFixture(
        case_id=case_id,
        description="A deliberately unmet certification expectation that must be blocked safely.",
        domain="health",
        expectation=expectation,
        evidence_output=_output(
            case_id,
            evidence=(),
            requirements=requirements,
            sufficiency="MISSING",
            resolution_status="NOT_RESOLVED",
            limitations=("No required waiting-period evidence was resolved.",),
        ),
        expected_outcome="BLOCKED",
    )


def generic_rule_certification_cases() -> tuple[RuleCertificationCaseFixture, ...]:
    """Return all generic cases in deterministic case-id order."""
    cases = (
        build_complete_conditional_obligation_case(),
        build_partial_coverage_limit_case(),
        build_conflicting_waiting_period_case(),
        build_blocked_missing_waiting_period_case(),
    )
    return tuple(sorted(cases, key=lambda item: item.case_id))
