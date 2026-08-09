from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.contracts.topic_completeness import (
    build_component_definition,
    build_topic_definition,
)
from insurance_intelligence.topic_completeness.evaluator import (
    TopicCompletenessEvaluationError,
    evaluate_topic_completeness,
)


def _component(
    component_id: str,
    requirement_type: str,
    *,
    required: bool = True,
    dependencies: tuple[str, ...] = (),
):
    return build_component_definition(
        component_id=component_id,
        requirement_type=requirement_type,
        required=required,
        acceptable_requirement_statuses=(
            "SATISFIED",
            "SATISFIED_WITH_LIMITATIONS",
        ),
        acceptable_evidence_roles=("SUPPORTING", "QUALIFYING"),
        minimum_authority="AUTHORITATIVE",
        dependency_component_ids=dependencies,
        reason=f"Resolve {component_id}.",
    )


def _definition(*, unresolved_policy: str = "REQUIRE_CLARIFICATION"):
    return build_topic_definition(
        topic_id="generic_conditional_obligation",
        topic_version="1.0",
        domain="health",
        components=(
            _component("obligation_value", "obligation_value"),
            _component("trigger_condition", "trigger_condition"),
            _component(
                "exception_condition",
                "exception_condition",
                dependencies=("trigger_condition",),
            ),
            _component("worked_example", "worked_example", required=False),
        ),
        unresolved_applicability_policy=unresolved_policy,
    )


def _lineage():
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
    topic: str,
    *,
    role: str = "SUPPORTING",
    authority: str = "AUTHORITATIVE",
    confidence: float = 1.0,
):
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference="product:generic",
        governed_entity_reference="entity:generic",
        field_or_topic=topic,
        claim=f"Claim for {topic}",
        evidence_role=role,
        source_type="POLICY_WORDING",
        document_reference="document:1",
        document_version="1.0",
        effective_from=None,
        effective_to=None,
        page=1,
        section="Section 1",
        source_excerpt="Governed source excerpt.",
        normalized_fact_reference=f"fact:{topic}",
        authority_rank=1,
        authority_requirement=authority,
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(),
        retrieval_basis=("topic_match",),
        confidence=confidence,
    )


def _requirement(
    requirement_id: str,
    *,
    status: str = "SATISFIED",
    confidence: float = 1.0,
    missing_reason: str | None = None,
    authority_satisfied: bool = True,
    version_satisfied: bool = True,
    lineage_satisfied: bool = True,
):
    return RequirementResult(
        requirement_id=requirement_id,
        status=status,
        matched_evidence_ids=(f"ev:{requirement_id}",),
        rejected_candidate_ids=(),
        missing_reason=missing_reason,
        authority_satisfied=authority_satisfied,
        version_satisfied=version_satisfied,
        lineage_satisfied=lineage_satisfied,
        conflict_status="NONE",
        confidence=confidence,
    )


def _output(
    *,
    evidence: tuple[EvidencePackage, ...],
    requirements: tuple[RequirementResult, ...],
):
    return EvidenceResolverOutput(
        contract_version="1.0",
        request_id="request-1",
        resolution_id="resolution-1",
        evidence_packages=evidence,
        requirement_results=requirements,
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


def _complete_output():
    evidence = (
        _evidence("ev:value", "req:value", "obligation_value"),
        _evidence("ev:trigger", "req:trigger", "trigger_condition"),
        _evidence("ev:exception", "req:exception", "exception_condition"),
    )
    requirements = (
        _requirement("req:value"),
        _requirement("req:trigger"),
        _requirement("req:exception"),
    )
    return _output(evidence=evidence, requirements=requirements)


def test_evaluates_complete_generic_topic():
    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=_complete_output(),
    )

    assert result.status == "COMPLETE"
    assert result.explanation_permitted is True
    assert result.missing_required_components == ()
    assert result.conflicting_components == ()
    assert result.unresolved_components == ()
    assert result.request_id == "request-1"


def test_optional_component_without_evidence_is_not_applicable():
    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=_complete_output(),
    )

    worked_example = next(
        item for item in result.component_results
        if item.component_id == "worked_example"
    )
    assert worked_example.status == "NOT_APPLICABLE"


def test_missing_one_required_component_produces_partial_result():
    output = _complete_output()
    output = replace(
        output,
        evidence_packages=tuple(
            item for item in output.evidence_packages
            if item.field_or_topic != "exception_condition"
        ),
        requirement_results=tuple(
            item for item in output.requirement_results
            if item.requirement_id != "req:exception"
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    assert result.status == "PARTIAL"
    assert result.explanation_permitted is False
    assert result.missing_required_components == ("exception_condition",)


def test_all_required_components_missing_produces_not_available():
    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=_output(evidence=(), requirements=()),
    )

    assert result.status == "NOT_AVAILABLE"
    assert result.explanation_permitted is False
    assert set(result.missing_required_components) == {
        "obligation_value",
        "trigger_condition",
        "exception_condition",
    }


def test_conflicting_requirement_blocks_explanation():
    output = _complete_output()
    output = replace(
        output,
        requirement_results=tuple(
            replace(item, status="CONFLICTING")
            if item.requirement_id == "req:trigger"
            else item
            for item in output.requirement_results
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    assert result.status == "CONFLICTING"
    assert result.explanation_permitted is False
    assert result.conflicting_components == ("trigger_condition",)


def test_unresolved_requirement_requires_clarification():
    output = _complete_output()
    output = replace(
        output,
        requirement_results=tuple(
            replace(item, status="VERSION_UNRESOLVED")
            if item.requirement_id == "req:trigger"
            else item
            for item in output.requirement_results
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    assert result.status == "CLARIFICATION_REQUIRED"
    assert "trigger_condition" in result.unresolved_components


def test_unresolved_policy_can_produce_partial_instead_of_clarification():
    output = _complete_output()
    output = replace(
        output,
        requirement_results=tuple(
            replace(item, status="ENTITY_UNRESOLVED")
            if item.requirement_id == "req:trigger"
            else item
            for item in output.requirement_results
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(unresolved_policy="TREAT_AS_PARTIAL"),
        evidence_output=output,
    )

    assert result.status == "PARTIAL"
    assert result.explanation_permitted is False


def test_dependency_becomes_unresolved_when_prerequisite_is_missing():
    output = _complete_output()
    output = replace(
        output,
        evidence_packages=tuple(
            item for item in output.evidence_packages
            if item.field_or_topic != "trigger_condition"
        ),
        requirement_results=tuple(
            item for item in output.requirement_results
            if item.requirement_id != "req:trigger"
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    exception = next(
        item for item in result.component_results
        if item.component_id == "exception_condition"
    )
    assert exception.status == "UNRESOLVED"
    assert "trigger_condition" in exception.limitations[-1]


def test_incorrect_evidence_role_is_not_accepted():
    output = _complete_output()
    output = replace(
        output,
        evidence_packages=tuple(
            replace(item, evidence_role="BACKGROUND")
            if item.field_or_topic == "obligation_value"
            else item
            for item in output.evidence_packages
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    assert "obligation_value" in result.missing_required_components


def test_incorrect_authority_is_not_accepted():
    output = _complete_output()
    output = replace(
        output,
        evidence_packages=tuple(
            replace(item, authority_requirement="SUPPORTING")
            if item.field_or_topic == "obligation_value"
            else item
            for item in output.evidence_packages
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    assert "obligation_value" in result.missing_required_components


def test_requirement_status_outside_component_contract_is_missing():
    output = _complete_output()
    output = replace(
        output,
        requirement_results=tuple(
            replace(item, status="NOT_APPLICABLE")
            if item.requirement_id == "req:value"
            else item
            for item in output.requirement_results
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    assert "obligation_value" in result.missing_required_components


def test_satisfied_with_limitations_produces_complete_with_limitations():
    output = _complete_output()
    output = replace(
        output,
        requirement_results=tuple(
            replace(
                item,
                status="SATISFIED_WITH_LIMITATIONS",
                missing_reason="Policy schedule was not supplied.",
                confidence=0.8,
            )
            if item.requirement_id == "req:exception"
            else item
            for item in output.requirement_results
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    assert result.status == "COMPLETE_WITH_LIMITATIONS"
    assert result.explanation_permitted is True
    assert "Policy schedule was not supplied." in result.limitations


def test_confidence_is_deterministic_mean_of_required_components():
    output = _complete_output()
    output = replace(
        output,
        evidence_packages=tuple(
            replace(item, confidence=0.8)
            if item.field_or_topic == "obligation_value"
            else item
            for item in output.evidence_packages
        ),
        requirement_results=tuple(
            replace(item, confidence=0.6)
            if item.requirement_id == "req:value"
            else item
            for item in output.requirement_results
        ),
    )

    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=output,
    )

    assert result.confidence == pytest.approx((0.7 + 1.0 + 1.0) / 3)


def test_evidence_and_requirement_references_are_preserved():
    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=_complete_output(),
    )

    value = next(
        item for item in result.component_results
        if item.component_id == "obligation_value"
    )
    assert value.matched_requirement_ids == ("req:value",)
    assert value.matched_evidence_ids == ("ev:value",)


def test_evaluation_is_independent_of_insurer_and_product_names():
    result = evaluate_topic_completeness(
        definition=_definition(),
        evidence_output=_complete_output(),
    )

    serialized = repr(result).lower()
    assert "star" not in serialized
    assert "aditya" not in serialized
    assert "bajaj" not in serialized


def test_rejects_invalid_definition_type():
    with pytest.raises(
        TopicCompletenessEvaluationError,
        match="definition must be",
    ):
        evaluate_topic_completeness(  # type: ignore[arg-type]
            definition=object(),
            evidence_output=_complete_output(),
        )


def test_rejects_invalid_evidence_output_type():
    with pytest.raises(
        TopicCompletenessEvaluationError,
        match="evidence_output must be",
    ):
        evaluate_topic_completeness(  # type: ignore[arg-type]
            definition=_definition(),
            evidence_output=object(),
        )
