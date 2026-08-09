from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
)
from insurance_intelligence.topic_completeness.adapter import (
    TopicCompletenessAdapterError,
    evaluate_registered_topic,
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


def _evidence(evidence_id: str, requirement_id: str, topic: str) -> EvidencePackage:
    return EvidencePackage(
        evidence_id=evidence_id,
        requirement_id=requirement_id,
        subject_reference="subject:generic",
        governed_entity_reference="entity:generic",
        field_or_topic=topic,
        claim=f"Claim for {topic}",
        evidence_role="DEFINING",
        source_type="POLICY_WORDING",
        document_reference="document:generic",
        document_version="1.0",
        effective_from=None,
        effective_to=None,
        page=1,
        section="Section 1",
        source_excerpt="Governed source excerpt.",
        normalized_fact_reference=f"fact:{topic}",
        authority_rank=1,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=_lineage(),
        retrieval_basis=("topic_match",),
        confidence=1.0,
    )


def _requirement(requirement_id: str) -> RequirementResult:
    return RequirementResult(
        requirement_id=requirement_id,
        status="SATISFIED",
        matched_evidence_ids=(f"ev:{requirement_id}",),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=True,
        conflict_status="NONE",
        confidence=1.0,
    )


def _complete_conditional_output() -> EvidenceResolverOutput:
    pairs = (
        ("value", "OBLIGATION_VALUE"),
        ("trigger", "TRIGGER_CONDITION"),
        ("scope", "APPLICABILITY_SCOPE"),
    )
    evidence = tuple(
        _evidence(f"ev:{name}", f"req:{name}", topic)
        for name, topic in pairs
    )
    requirements = tuple(_requirement(f"req:{name}") for name, _ in pairs)
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


def test_adapter_uses_default_registry_and_active_version():
    result = evaluate_registered_topic(
        topic_id="conditional_obligation",
        evidence_output=_complete_conditional_output(),
    )

    assert result.topic_id == "conditional_obligation"
    assert result.topic_version == "1.0"
    assert result.status == "COMPLETE"
    assert result.explanation_permitted is True


def test_adapter_supports_exact_version_lookup():
    result = evaluate_registered_topic(
        topic_id="conditional_obligation",
        topic_version="1.0",
        evidence_output=_complete_conditional_output(),
        registry=build_default_topic_registry(),
    )

    assert result.topic_version == "1.0"


def test_adapter_enforces_requested_domain():
    with pytest.raises(TopicCompletenessAdapterError, match="domain does not match"):
        evaluate_registered_topic(
            topic_id="conditional_obligation",
            domain="motor",
            evidence_output=_complete_conditional_output(),
        )


def test_adapter_rejects_unknown_topic():
    with pytest.raises(TopicCompletenessAdapterError, match="topic not registered"):
        evaluate_registered_topic(
            topic_id="unknown_topic",
            evidence_output=_complete_conditional_output(),
        )


def test_adapter_rejects_unknown_exact_version():
    with pytest.raises(TopicCompletenessAdapterError, match="topic not registered"):
        evaluate_registered_topic(
            topic_id="conditional_obligation",
            topic_version="9.9",
            evidence_output=_complete_conditional_output(),
        )


@pytest.mark.parametrize("topic_id", ["", "   ", None])
def test_adapter_rejects_invalid_topic_id(topic_id):
    with pytest.raises(TopicCompletenessAdapterError, match="topic_id"):
        evaluate_registered_topic(
            topic_id=topic_id,
            evidence_output=_complete_conditional_output(),
        )


def test_adapter_rejects_invalid_registry_type():
    with pytest.raises(TopicCompletenessAdapterError, match="registry"):
        evaluate_registered_topic(
            topic_id="conditional_obligation",
            evidence_output=_complete_conditional_output(),
            registry=object(),
        )


def test_adapter_rejects_invalid_evidence_output_type():
    with pytest.raises(TopicCompletenessAdapterError, match="evidence_output"):
        evaluate_registered_topic(
            topic_id="conditional_obligation",
            evidence_output=object(),
        )


def test_adapter_wraps_evidence_contract_validation_failures():
    invalid = replace(_complete_conditional_output(), contract_version="9.9")

    with pytest.raises(TopicCompletenessAdapterError, match="contract_version"):
        evaluate_registered_topic(
            topic_id="conditional_obligation",
            evidence_output=invalid,
        )


def test_adapter_does_not_mutate_custom_registry_or_evidence_output():
    registry = build_default_topic_registry()
    before_definitions = registry.all_definitions()
    before_active = tuple(
        (definition.topic_id, registry.active_version(definition.topic_id))
        for definition in before_definitions
    )
    evidence_output = _complete_conditional_output()

    result = evaluate_registered_topic(
        topic_id="conditional_obligation",
        evidence_output=evidence_output,
        registry=registry,
    )

    assert result.request_id == evidence_output.request_id
    assert registry.all_definitions() == before_definitions
    assert tuple(
        (definition.topic_id, registry.active_version(definition.topic_id))
        for definition in before_definitions
    ) == before_active
    assert evidence_output == _complete_conditional_output()


def test_adapter_propagates_ambiguous_unversioned_lookup_as_adapter_error():
    default = build_default_topic_registry().get("conditional_obligation")
    second = replace(default, topic_version="2.0")
    registry = TopicCompletenessRegistry((default, second))

    with pytest.raises(TopicCompletenessAdapterError, match="ambiguous"):
        evaluate_registered_topic(
            topic_id="conditional_obligation",
            evidence_output=_complete_conditional_output(),
            registry=registry,
        )
