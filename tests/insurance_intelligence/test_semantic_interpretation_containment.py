from __future__ import annotations

import json
from dataclasses import fields, replace

import pytest

from insurance_intelligence.contracts.semantic_interpretation import (
    CompetingInterpretation,
    ConceptCandidate,
    GovernedSemanticInterpretation,
    InterpreterProvenance,
    ScenarioFact,
    audit_artifact_as_dict,
)
from insurance_intelligence.semantic_interpretation.validator import (
    RESOLUTION_CONFIDENCE_THRESHOLD,
    SemanticInterpretationValidationError,
    build_audit_artifact,
    build_clarification_route,
    validate_interpretation,
)


def provenance() -> InterpreterProvenance:
    return InterpreterProvenance(
        interpreter_version="gsi-contract-test-v1",
        model_name="not-invoked-p0",
        config_id="p0-test-config",
        input_sha256="a" * 64,
    )


def resolved() -> GovernedSemanticInterpretation:
    return GovernedSemanticInterpretation(
        contract_version="1.0",
        request_id="request-1",
        interpretation_status="RESOLVED",
        confidence=0.93,
        primary_intent="understand_policy_term",
        requested_outcome="POLICY_FACT_EXPLANATION",
        governed_concept_candidates=(ConceptCandidate("room_rent_limit", 0.94),),
        selected_concept_id="room_rent_limit",
        requested_semantic_fact="excess_consequence",
        scenario_facts=(ScenarioFact("room_type", "deluxe"),),
        request_authority_class="ASSERTIVE",
        ambiguity_reasons=(),
        competing_interpretations=(),
        provenance=provenance(),
    )


def test_resolved_interpretation_requires_deterministic_validation_marker() -> None:
    validated = validate_interpretation(resolved())
    assert validated.interpretation.selected_concept_id == "room_rent_limit"
    assert validated.validator_version == "1.1"
    assert validated.resolution_threshold_applied == RESOLUTION_CONFIDENCE_THRESHOLD


def test_interpreter_proposal_cannot_supply_or_lower_resolution_threshold() -> None:
    field_names = {field.name for field in fields(GovernedSemanticInterpretation)}
    assert "resolution_threshold" not in field_names
    assert RESOLUTION_CONFIDENCE_THRESHOLD == 0.80


def test_low_confidence_cannot_silently_become_resolved() -> None:
    proposal = replace(resolved(), confidence=0.79)
    with pytest.raises(
        SemanticInterpretationValidationError,
        match="below governed resolution threshold",
    ):
        validate_interpretation(proposal)


def test_selected_concept_must_itself_clear_resolution_threshold() -> None:
    proposal = replace(
        resolved(),
        governed_concept_candidates=(ConceptCandidate("room_rent_limit", 0.79),),
    )
    with pytest.raises(
        SemanticInterpretationValidationError,
        match="selected concept confidence",
    ):
        validate_interpretation(proposal)


def test_ambiguous_interpretation_is_non_executable_and_routes_to_clarification() -> None:
    proposal = replace(
        resolved(),
        interpretation_status="AMBIGUOUS",
        confidence=0.66,
        primary_intent="understand_policy_effect",
        requested_outcome=None,
        governed_concept_candidates=(
            ConceptCandidate("room_rent_limit", 0.66),
            ConceptCandidate("benefit_sub_limit", 0.64),
        ),
        selected_concept_id=None,
        requested_semantic_fact=None,
        ambiguity_reasons=("multiple governed concepts remain plausible",),
        competing_interpretations=(
            CompetingInterpretation(
                primary_intent="understand_policy_effect",
                requested_outcome="POLICY_FACT_EXPLANATION",
                concept_id="room_rent_limit",
                requested_semantic_fact="excess_consequence",
                confidence=0.66,
            ),
            CompetingInterpretation(
                primary_intent="understand_policy_effect",
                requested_outcome="POLICY_FACT_EXPLANATION",
                concept_id="benefit_sub_limit",
                requested_semantic_fact="applicability",
                confidence=0.64,
            ),
        ),
    )
    validated = validate_interpretation(proposal)
    route = build_clarification_route(validated)
    assert route.clarification_required is True
    assert route.interpretation_status == "AMBIGUOUS"
    assert route.candidate_concept_ids == ("room_rent_limit", "benefit_sub_limit")


def test_unresolved_interpretation_cannot_smuggle_executable_fact() -> None:
    proposal = replace(
        resolved(),
        interpretation_status="UNRESOLVED",
        confidence=0.2,
        primary_intent=None,
        requested_outcome=None,
        selected_concept_id=None,
        requested_semantic_fact="excess_consequence",
        ambiguity_reasons=("intent could not be safely resolved",),
    )
    with pytest.raises(
        SemanticInterpretationValidationError,
        match="cannot request an executable semantic fact",
    ):
        validate_interpretation(proposal)


def test_claim_payment_outcome_is_structurally_outside_executable_domain() -> None:
    proposal = replace(resolved(), requested_outcome="CLAIM_PAYMENT_OUTCOME")
    with pytest.raises(
        SemanticInterpretationValidationError,
        match="outside the executable domain",
    ):
        validate_interpretation(proposal)


def test_claim_admissibility_outcome_is_structurally_outside_executable_domain() -> None:
    proposal = replace(resolved(), requested_outcome="CLAIM_ADMISSIBILITY")
    with pytest.raises(
        SemanticInterpretationValidationError,
        match="outside the executable domain",
    ):
        validate_interpretation(proposal)


def test_unknown_outcome_fails_closed_because_domain_is_allow_list() -> None:
    proposal = replace(resolved(), requested_outcome="NEW_UNREVIEWED_OUTCOME")
    with pytest.raises(
        SemanticInterpretationValidationError,
        match="outside the executable domain",
    ):
        validate_interpretation(proposal)


def test_resolved_interpretation_cannot_retain_hidden_competing_reading() -> None:
    proposal = replace(
        resolved(),
        competing_interpretations=(
            CompetingInterpretation(
                primary_intent="alternate",
                requested_outcome="INSURANCE_MECHANICS_EXPLANATION",
                concept_id="room_rent_limit",
                requested_semantic_fact="mechanics",
                confidence=0.7,
            ),
        ),
    )
    with pytest.raises(
        SemanticInterpretationValidationError,
        match="cannot retain ambiguity",
    ):
        validate_interpretation(proposal)


def test_audit_artifact_is_execution_linked_and_json_serializable() -> None:
    validated = validate_interpretation(resolved())
    artifact = build_audit_artifact(
        artifact_id="interpretation-artifact-1",
        execution_id="execution-1",
        validated=validated,
        failure_origin="NONE",
        failure_code="SUCCESS",
        failure_detail="interpretation validated",
        created_at="2026-10-07T16:45:00Z",
    )
    serialized = audit_artifact_as_dict(artifact)
    assert serialized["execution_id"] == "execution-1"
    assert serialized["request_id"] == "request-1"
    assert serialized["failure_attribution"]["origin"] == "NONE"
    assert serialized["validated_interpretation"]["resolution_threshold_applied"] == 0.80
    assert json.loads(json.dumps(serialized))["validated_interpretation"][
        "interpretation"
    ]["provenance"]["input_sha256"] == "a" * 64


def test_failure_origin_is_bounded_for_benchmark_attribution() -> None:
    validated = validate_interpretation(resolved())
    with pytest.raises(SemanticInterpretationValidationError, match="failure_origin"):
        build_audit_artifact(
            artifact_id="interpretation-artifact-1",
            execution_id="execution-1",
            validated=validated,
            failure_origin="UNKNOWN_LAYER",
            created_at="2026-10-07T16:45:00Z",
        )
