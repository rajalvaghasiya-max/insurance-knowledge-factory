from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.rule_certification import (
    CERTIFICATION_OUTCOMES,
    RuleCertificationContractError,
    build_component_certification_expectation,
    build_rule_certification_expectation,
    build_rule_certification_result,
)
from insurance_intelligence.contracts.topic_completeness import (
    build_component_definition,
    build_component_result,
    build_completeness_result,
    build_topic_definition,
)
from insurance_intelligence.rule_certification import RuleCertificationResult


def _definition():
    return build_topic_definition(
        topic_id="conditional_obligation",
        topic_version="1.0",
        domain="health",
        components=(
            build_component_definition(
                component_id="obligation_value",
                requirement_type="OBLIGATION_VALUE",
                required=True,
                acceptable_requirement_statuses=("SATISFIED",),
                acceptable_evidence_roles=("DEFINING",),
                minimum_authority="AUTHORITATIVE",
                reason="Resolve the governed obligation value.",
            ),
            build_component_definition(
                component_id="trigger_condition",
                requirement_type="TRIGGER_CONDITION",
                required=True,
                acceptable_requirement_statuses=("SATISFIED",),
                acceptable_evidence_roles=("QUALIFYING",),
                minimum_authority="AUTHORITATIVE",
                reason="Resolve the governed trigger.",
            ),
        ),
    )


def _evidence_output(**overrides):
    values = dict(
        contract_version="1.0",
        request_id="request-1",
        resolution_id="resolution-1",
        evidence_packages=(),
        requirement_results=(),
        entity_resolutions=(),
        document_resolutions=(),
        conflicts=(),
        missing_evidence=(),
        sufficiency="COMPLETE",
        limitations=(),
        resolution_trace=(),
        resolution_status="RESOLVED",
        confidence=1.0,
    )
    values.update(overrides)
    return EvidenceResolverOutput(**values)


def _completeness(
    *,
    status="COMPLETE",
    explanation_permitted=True,
    value_status="SATISFIED",
    trigger_status="SATISFIED",
    request_id="request-1",
):
    definition = _definition()

    def component(component_id, component_status, suffix):
        satisfied = component_status in {"SATISFIED", "SATISFIED_WITH_LIMITATIONS"}
        limitations = (
            ("Limited evidence.",)
            if component_status == "SATISFIED_WITH_LIMITATIONS"
            else ()
        )
        return build_component_result(
            component_id=component_id,
            status=component_status,
            matched_requirement_ids=((f"req-{suffix}",) if satisfied else ()),
            matched_evidence_ids=((f"evidence-{suffix}",) if satisfied else ()),
            limitations=limitations,
            confidence=1.0 if satisfied else 0.0,
        )

    results = (
        component("obligation_value", value_status, "value"),
        component("trigger_condition", trigger_status, "trigger"),
    )
    missing = tuple(
        item.component_id for item in results if item.status == "MISSING"
    )
    conflicting = tuple(
        item.component_id for item in results if item.status == "CONFLICTING"
    )
    unresolved = tuple(
        item.component_id
        for item in results
        if item.status in {"PARTIAL", "UNRESOLVED"}
    )
    return build_completeness_result(
        definition=definition,
        request_id=request_id,
        status=status,
        component_results=results,
        missing_required_components=missing,
        conflicting_components=conflicting,
        unresolved_components=unresolved,
        limitations=(),
        explanation_permitted=explanation_permitted,
        confidence=1.0 if status == "COMPLETE" else 0.0,
    )


def _expectation(
    *,
    statuses=("COMPLETE",),
    explanation=True,
    value_statuses=("SATISFIED",),
    trigger_statuses=("SATISFIED",),
):
    return build_rule_certification_expectation(
        certification_id="certification-1",
        governed_subject_reference="governed-rule:generic-1",
        topic_id="conditional_obligation",
        topic_version="1.0",
        expected_completeness_statuses=statuses,
        expected_explanation_permitted=explanation,
        component_expectations=(
            build_component_certification_expectation(
                component_id="obligation_value",
                acceptable_statuses=value_statuses,
            ),
            build_component_certification_expectation(
                component_id="trigger_condition",
                acceptable_statuses=trigger_statuses,
            ),
        ),
    )


def test_certification_outcomes_are_closed_and_explicit():
    assert CERTIFICATION_OUTCOMES == {"PASS", "FAIL", "BLOCKED"}


def test_builds_versioned_expectation_with_component_status_sets():
    expectation = _expectation(
        statuses=("COMPLETE", "COMPLETE_WITH_LIMITATIONS"),
        value_statuses=("SATISFIED", "SATISFIED_WITH_LIMITATIONS"),
    )

    assert expectation.contract_version == "1.0"
    assert expectation.topic_id == "conditional_obligation"
    assert expectation.component_expectations[0].acceptable_statuses == (
        "SATISFIED",
        "SATISFIED_WITH_LIMITATIONS",
    )


def test_rejects_empty_and_invalid_component_status_expectations():
    with pytest.raises(RuleCertificationContractError, match="must not be empty"):
        build_component_certification_expectation(
            component_id="obligation_value",
            acceptable_statuses=(),
        )

    with pytest.raises(RuleCertificationContractError, match="must be one of"):
        build_component_certification_expectation(
            component_id="obligation_value",
            acceptable_statuses=("UNKNOWN",),
        )


def test_rejects_duplicate_component_expectations():
    component = build_component_certification_expectation(
        component_id="obligation_value",
        acceptable_statuses=("SATISFIED",),
    )
    with pytest.raises(RuleCertificationContractError, match="must be unique"):
        build_rule_certification_expectation(
            certification_id="certification-1",
            governed_subject_reference="governed-rule:generic-1",
            topic_id="conditional_obligation",
            topic_version="1.0",
            expected_completeness_statuses=("COMPLETE",),
            expected_explanation_permitted=True,
            component_expectations=(component, component),
        )


def test_matching_execution_produces_pass_with_trace_and_snapshots():
    result = build_rule_certification_result(
        expectation=_expectation(),
        evidence_output=_evidence_output(),
        completeness_result=_completeness(),
        trace_references=("trace:resolver", "trace:completeness"),
    )

    assert isinstance(result, RuleCertificationResult)
    assert result.outcome == "PASS"
    assert result.failures == ()
    assert result.request_id == "request-1"
    assert result.resolution_id == "resolution-1"
    assert result.resolution_status == "RESOLVED"
    assert result.evidence_sufficiency == "COMPLETE"
    assert result.trace_references == ("trace:resolver", "trace:completeness")
    assert all(check.passed for check in result.component_checks)


def test_non_blocking_expectation_mismatch_produces_fail():
    result = build_rule_certification_result(
        expectation=_expectation(statuses=("COMPLETE_WITH_LIMITATIONS",)),
        evidence_output=_evidence_output(),
        completeness_result=_completeness(),
    )

    assert result.outcome == "FAIL"
    assert result.failures == ("Unexpected completeness status: COMPLETE",)


def test_unexpected_blocking_result_produces_blocked():
    result = build_rule_certification_result(
        expectation=_expectation(),
        evidence_output=_evidence_output(
            sufficiency="CONFLICTING",
            resolution_status="CONFLICTING",
        ),
        completeness_result=_completeness(
            status="CONFLICTING",
            explanation_permitted=False,
            trigger_status="CONFLICTING",
        ),
    )

    assert result.outcome == "BLOCKED"
    assert "Unexpected completeness status: CONFLICTING" in result.failures
    assert "Explanation-permission expectation was not met." in result.failures


def test_expected_blocking_behaviour_can_be_certified_as_pass():
    result = build_rule_certification_result(
        expectation=_expectation(
            statuses=("CONFLICTING",),
            explanation=False,
            trigger_statuses=("CONFLICTING",),
        ),
        evidence_output=_evidence_output(
            sufficiency="CONFLICTING",
            resolution_status="CONFLICTING",
        ),
        completeness_result=_completeness(
            status="CONFLICTING",
            explanation_permitted=False,
            trigger_status="CONFLICTING",
        ),
    )

    assert result.outcome == "PASS"
    assert result.failures == ()


def test_missing_expected_component_result_is_a_failure():
    completeness = _completeness()
    completeness = replace(
        completeness,
        component_results=(completeness.component_results[0],),
    )

    result = build_rule_certification_result(
        expectation=_expectation(),
        evidence_output=_evidence_output(),
        completeness_result=completeness,
    )

    trigger_check = next(
        check for check in result.component_checks if check.component_id == "trigger_condition"
    )
    assert trigger_check.actual_status is None
    assert trigger_check.passed is False
    assert result.outcome == "FAIL"


def test_rejects_request_topic_and_version_mismatches():
    with pytest.raises(RuleCertificationContractError, match="request IDs must match"):
        build_rule_certification_result(
            expectation=_expectation(),
            evidence_output=_evidence_output(),
            completeness_result=_completeness(request_id="different-request"),
        )

    with pytest.raises(RuleCertificationContractError, match="topic IDs must match"):
        build_rule_certification_result(
            expectation=replace(_expectation(), topic_id="coverage_limit"),
            evidence_output=_evidence_output(),
            completeness_result=_completeness(),
        )

    with pytest.raises(RuleCertificationContractError, match="topic versions must match"):
        build_rule_certification_result(
            expectation=replace(_expectation(), topic_version="2.0"),
            evidence_output=_evidence_output(),
            completeness_result=_completeness(),
        )


def test_combines_governed_limitations_deterministically():
    result = build_rule_certification_result(
        expectation=_expectation(),
        evidence_output=_evidence_output(limitations=("Resolver limitation.",)),
        completeness_result=replace(
            _completeness(),
            limitations=("Completeness limitation.",),
        ),
        limitations=("Certification limitation.",),
    )

    assert result.limitations == (
        "Resolver limitation.",
        "Completeness limitation.",
        "Certification limitation.",
    )


def test_rejects_duplicate_trace_and_limitation_references():
    with pytest.raises(RuleCertificationContractError, match="trace_references values must be unique"):
        build_rule_certification_result(
            expectation=_expectation(),
            evidence_output=_evidence_output(),
            completeness_result=_completeness(),
            trace_references=("trace:1", "trace:1"),
        )

    with pytest.raises(RuleCertificationContractError, match="limitations values must be unique"):
        build_rule_certification_result(
            expectation=_expectation(),
            evidence_output=_evidence_output(limitations=("Same.",)),
            completeness_result=_completeness(),
            limitations=("Same.",),
        )
