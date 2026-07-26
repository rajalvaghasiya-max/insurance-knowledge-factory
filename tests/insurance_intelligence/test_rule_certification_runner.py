from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
    TraceEvent,
)
from insurance_intelligence.contracts.rule_certification import (
    build_component_certification_expectation,
    build_rule_certification_expectation,
)
from insurance_intelligence.rule_certification.runner import (
    RuleCertificationRunnerError,
    run_rule_certification,
)
from insurance_intelligence.topic_completeness.catalogue import (
    build_default_topic_registry,
)
from insurance_intelligence.topic_completeness.registry import (
    TopicCompletenessRegistry,
)


def _lineage() -> Lineage:
    return Lineage(
        source_artifact_path="source.pdf",
        source_artifact_sha256="a" * 64,
        governed_record_path="record.json",
        governed_record_sha256="b" * 64,
        binding_reference="binding:1",
        projection_reference="projection:1",
        lineage_status="VERIFIED",
    )


def _evidence(
    evidence_id: str,
    requirement_id: str,
    field_or_topic: str,
) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference="subject:generic",
        governed_entity_reference="entity:generic",
        field_or_topic=field_or_topic,
        claim=f"Claim for {field_or_topic}",
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="document:generic",
        document_version="1.0",
        effective_from=None,
        effective_to=None,
        page=1,
        section="Section 1",
        source_excerpt="Governed excerpt.",
        normalized_fact_reference=f"fact:{field_or_topic}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(),
        retrieval_basis=("topic_match",),
        confidence=1.0,
    )


def _requirement(requirement_id: str, status: str = "SATISFIED") -> RequirementResult:
    return RequirementResult(
        requirement_id=requirement_id,
        status=status,
        matched_evidence_ids=(f"ev:{requirement_id}",),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def _trace(trace_id: str, sequence: int) -> TraceEvent:
    return TraceEvent(
        trace_id=trace_id,
        sequence=sequence,
        event_type="RESOLUTION_COMPLETED",
        requirement_id=None,
        subject_reference="subject:generic",
        repository=None,
        candidate_reference=None,
        decision="accepted",
        basis="governed",
        source_paths=(),
        order_marker=f"{sequence:04d}",
    )


def _complete_output() -> EvidenceResolverOutput:
    requirements = (
        ("req:value", "OBLIGATION_VALUE"),
        ("req:trigger", "TRIGGER_CONDITION"),
        ("req:scope", "APPLICABILITY_SCOPE"),
    )
    return EvidenceResolverOutput(
        contract_version="1.0",
        request_id="request-1",
        resolution_id="resolution-1",
        evidence_packages=tuple(
            _evidence(f"ev:{requirement_id}", requirement_id, field)
            for requirement_id, field in requirements
        ),
        requirement_results=tuple(
            _requirement(requirement_id) for requirement_id, _ in requirements
        ),
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=(),
        sufficiency="COMPLETE",
        limitations=(),
        resolution_trace=(_trace("trace-1", 1), _trace("trace-2", 2)),
        resolution_status="RESOLVED",
        confidence=1.0,
    )


def _expectation(
    *,
    completeness_statuses: tuple[str, ...] = ("COMPLETE",),
    explanation_permitted: bool = True,
):
    return build_rule_certification_expectation(
        certification_id="certification-1",
        governed_subject_reference="subject:generic",
        topic_id="conditional_obligation",
        topic_version="1.0",
        expected_completeness_statuses=completeness_statuses,
        expected_explanation_permitted=explanation_permitted,
        component_expectations=(
            build_component_certification_expectation(
                component_id="obligation_value",
                acceptable_statuses=("SATISFIED",),
            ),
            build_component_certification_expectation(
                component_id="trigger_condition",
                acceptable_statuses=("SATISFIED",),
            ),
            build_component_certification_expectation(
                component_id="applicability_scope",
                acceptable_statuses=("SATISFIED",),
            ),
        ),
    )


def test_runner_executes_complete_certification_case():
    result = run_rule_certification(
        expectation=_expectation(),
        evidence_output=_complete_output(),
    )

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert all(check.passed for check in result.component_checks)


def test_runner_uses_exact_topic_version_from_expectation():
    registry = build_default_topic_registry()

    result = run_rule_certification(
        expectation=_expectation(),
        evidence_output=_complete_output(),
        registry=registry,
    )

    assert result.topic_id == "conditional_obligation"
    assert result.topic_version == "1.0"


def test_runner_derives_fail_for_nonblocking_expectation_mismatch():
    result = run_rule_certification(
        expectation=_expectation(completeness_statuses=("PARTIAL",)),
        evidence_output=_complete_output(),
    )

    assert result.outcome == "FAIL"
    assert result.failures == ("Unexpected completeness status: COMPLETE",)


def test_runner_derives_blocked_for_unexpected_blocking_result():
    output = replace(
        _complete_output(),
        evidence_packages=(),
        requirement_results=(),
        sufficiency="MISSING",
        resolution_status="NOT_RESOLVED",
    )

    result = run_rule_certification(
        expectation=_expectation(),
        evidence_output=output,
    )

    assert result.outcome == "BLOCKED"
    assert result.actual_completeness_status == "NOT_AVAILABLE"
    assert result.actual_explanation_permitted is False


def test_runner_can_pass_expected_blocking_behaviour():
    output = replace(
        _complete_output(),
        evidence_packages=(),
        requirement_results=(),
        sufficiency="MISSING",
        resolution_status="NOT_RESOLVED",
    )
    expectation = build_rule_certification_expectation(
        certification_id="certification-blocked",
        governed_subject_reference="subject:generic",
        topic_id="conditional_obligation",
        topic_version="1.0",
        expected_completeness_statuses=("NOT_AVAILABLE",),
        expected_explanation_permitted=False,
        component_expectations=(
            build_component_certification_expectation(
                component_id="obligation_value",
                acceptable_statuses=("MISSING",),
            ),
            build_component_certification_expectation(
                component_id="trigger_condition",
                acceptable_statuses=("MISSING",),
            ),
            build_component_certification_expectation(
                component_id="applicability_scope",
                acceptable_statuses=("MISSING",),
            ),
        ),
    )

    result = run_rule_certification(
        expectation=expectation,
        evidence_output=output,
    )

    assert result.outcome == "PASS"
    assert result.failures == ()


def test_runner_derives_trace_references_from_resolution_trace():
    result = run_rule_certification(
        expectation=_expectation(),
        evidence_output=_complete_output(),
    )

    assert result.trace_references == ("trace-1", "trace-2")


def test_runner_accepts_explicit_trace_references_and_limitations():
    result = run_rule_certification(
        expectation=_expectation(),
        evidence_output=_complete_output(),
        trace_references=("external-trace",),
        limitations=("Certification fixture limitation.",),
    )

    assert result.trace_references == ("external-trace",)
    assert result.limitations == ("Certification fixture limitation.",)


def test_runner_enforces_domain_consistency():
    with pytest.raises(
        RuleCertificationRunnerError,
        match="requested domain does not match",
    ):
        run_rule_certification(
            expectation=_expectation(),
            evidence_output=_complete_output(),
            domain="motor",
        )


def test_runner_wraps_unknown_topic_version():
    expectation = replace(_expectation(), topic_version="9.9")

    with pytest.raises(RuleCertificationRunnerError, match="topic not registered"):
        run_rule_certification(
            expectation=expectation,
            evidence_output=_complete_output(),
        )


def test_runner_rejects_invalid_boundary_inputs():
    with pytest.raises(RuleCertificationRunnerError, match="expectation must be"):
        run_rule_certification(
            expectation=object(),  # type: ignore[arg-type]
            evidence_output=_complete_output(),
        )

    with pytest.raises(RuleCertificationRunnerError, match="evidence_output must be"):
        run_rule_certification(
            expectation=_expectation(),
            evidence_output=object(),  # type: ignore[arg-type]
        )

    with pytest.raises(RuleCertificationRunnerError, match="registry must be"):
        run_rule_certification(
            expectation=_expectation(),
            evidence_output=_complete_output(),
            registry=object(),  # type: ignore[arg-type]
        )


def test_runner_rejects_duplicate_explicit_trace_references():
    with pytest.raises(RuleCertificationRunnerError, match="trace_references values"):
        run_rule_certification(
            expectation=_expectation(),
            evidence_output=_complete_output(),
            trace_references=("trace-1", "trace-1"),
        )


def test_runner_does_not_mutate_expectation_output_or_registry():
    expectation = _expectation()
    output = _complete_output()
    registry = build_default_topic_registry()
    registry_snapshot = registry.all_definitions()

    run_rule_certification(
        expectation=expectation,
        evidence_output=output,
        registry=registry,
    )

    assert expectation == _expectation()
    assert output == _complete_output()
    assert registry.all_definitions() == registry_snapshot


def test_runner_accepts_custom_registry_with_matching_definition():
    default_registry = build_default_topic_registry()
    custom_registry = TopicCompletenessRegistry()
    custom_registry.register(
        default_registry.get("conditional_obligation", "1.0"),
        active=True,
    )

    result = run_rule_certification(
        expectation=_expectation(),
        evidence_output=_complete_output(),
        registry=custom_registry,
    )

    assert result.outcome == "PASS"
