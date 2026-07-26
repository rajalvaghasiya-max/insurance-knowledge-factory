from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.rule_certification.aditya_birla_health import (
    ACTIV_ONE_POLICY_INTELLIGENCE_PATH,
    ACTIV_ONE_POLICY_WORDING_PATH,
    ACTIV_ONE_SPECIFIED_WAITING_PERIOD_REFERENCE,
    build_activ_one_specified_disease_waiting_period_case,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification


def test_activ_one_replication_case_passes_unchanged_generic_runner():
    case = build_activ_one_specified_disease_waiting_period_case()

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == "PASS"
    assert result.completeness_result.status == "COMPLETE"
    assert result.completeness_result.explanation_permitted is True
    assert result.failure_reasons == ()
    assert case.expected_outcome == result.outcome


def test_activ_one_replication_uses_waiting_period_topic_without_generic_changes():
    case = build_activ_one_specified_disease_waiting_period_case()

    assert case.expectation.topic_id == "waiting_period"
    assert case.expectation.topic_version == "1.0"
    assert case.domain == "health"
    assert case.expectation.governed_subject_reference == (
        ACTIV_ONE_SPECIFIED_WAITING_PERIOD_REFERENCE
    )

    component_ids = tuple(
        expectation.component_id
        for expectation in case.expectation.component_expectations
    )
    assert component_ids == (
        "waiting_period_duration",
        "waiting_period_subject",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
        "exception_condition",
    )


def test_activ_one_replication_preserves_exact_rule_semantics():
    case = build_activ_one_specified_disease_waiting_period_case()
    claims = {package.field_or_topic: package.claim for package in case.evidence_output.evidence_packages}

    assert "24 months" in claims["WAITING_PERIOD_DURATION"]
    assert "listed conditions" in claims["WAITING_PERIOD_SUBJECT"]
    assert "inception of the first policy" in claims["WAITING_PERIOD_START_BASIS"]
    assert "enhanced sum insured" in claims["APPLICABILITY_SCOPE"]
    assert "Portability continuity credit" in claims["CONTINUITY_OR_CREDIT_RULE"]
    assert "accident" in claims["EXCEPTION_CONDITION"]


def test_activ_one_replication_uses_primary_policy_wording_traceability():
    case = build_activ_one_specified_disease_waiting_period_case()

    for package in case.evidence_output.evidence_packages:
        assert package.subject_reference == "product:aditya_birla_health:activ_one"
        assert package.source_type == "POLICY_WORDING"
        assert package.page == 10
        assert package.document_version == "ADIHLIP24097V012324"
        assert package.lineage.source_artifact_path == ACTIV_ONE_POLICY_WORDING_PATH
        assert package.lineage.governed_record_path == ACTIV_ONE_POLICY_INTELLIGENCE_PATH
        assert package.authority_requirement == "AUTHORITATIVE"
        assert package.lineage.lineage_status == "VERIFIED"
        assert "primary_legal_policy_wording" in package.retrieval_basis


def test_activ_one_replication_has_no_star_or_generic_infrastructure_coupling():
    case = build_activ_one_specified_disease_waiting_period_case()
    serialized = repr(case).lower()

    assert "star_health" not in serialized
    assert "star comprehensive" not in serialized
    assert "conditional_obligation" not in serialized
    assert "coverage_limit" not in serialized


def test_activ_one_replication_preserves_safety_limitations():
    case = build_activ_one_specified_disease_waiting_period_case()
    limitations = " ".join(case.evidence_output.limitations).lower()

    assert "does not itself publish" in limitations
    assert "does not guarantee claim payment" in limitations
    assert "admissibility" in limitations


def test_activ_one_replication_case_is_deterministic():
    first = build_activ_one_specified_disease_waiting_period_case()
    second = build_activ_one_specified_disease_waiting_period_case()

    assert first == second
    assert run_rule_certification(
        expectation=first.expectation,
        evidence_output=first.evidence_output,
        domain=first.domain,
    ) == run_rule_certification(
        expectation=second.expectation,
        evidence_output=second.evidence_output,
        domain=second.domain,
    )


def test_activ_one_replication_case_is_immutable():
    case = build_activ_one_specified_disease_waiting_period_case()

    with pytest.raises(FrozenInstanceError):
        case.case_id = "changed"
