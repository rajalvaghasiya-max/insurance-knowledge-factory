from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationContractError,
    build_authoritative_publication_input,
    build_governed_publication_projection,
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.publication_decision import PublicationDecisionResult


def decision() -> PublicationDecisionResult:
    return PublicationDecisionResult(
        contract_version="1.0",
        decision_id="decision-1",
        governed_subject_reference="product:generic:plan-a",
        certification_id="cert-1",
        certification_outcome="PASS",
        topic_id="coverage_limit",
        topic_version="1.0",
        requested_status="PUBLISH",
        decision_status="PUBLISH",
        decision_reasons=("Certified semantics are eligible for publication.",),
        limitations=("This does not guarantee claim payment.",),
        certification_trace_references=("cert-trace-1",),
        evidence_trace_references=("evidence-trace-1",),
        decision_authority="governance-board",
        publication_permitted=True,
        authoritative_publication_created=False,
        failures=(),
    )


def component(component_id: str = "limit_value"):
    return build_governed_semantic_component(
        component_id=component_id,
        status="SATISFIED",
        evidence_references=(f"evidence:{component_id}",),
    )


def projection(**overrides):
    values = dict(
        projection_id="projection-1",
        governed_subject_reference="product:generic:plan-a",
        certification_id="cert-1",
        topic_id="coverage_limit",
        topic_version="1.0",
        semantic_components=(component(),),
        limitations=("This does not guarantee claim payment.",),
        evidence_trace_references=("evidence-trace-1",),
        certification_trace_references=("cert-trace-1",),
    )
    values.update(overrides)
    return build_governed_publication_projection(**values)


def test_component_requires_evidence_and_is_frozen():
    with pytest.raises(AuthoritativePublicationContractError, match="must not be empty"):
        build_governed_semantic_component(
            component_id="limit_value", status="SATISFIED", evidence_references=()
        )
    item = component()
    assert item.semantic_basis == "ASSERTED"
    assert item.derivation_references == ()
    with pytest.raises(FrozenInstanceError):
        item.status = "CHANGED"  # type: ignore[misc]


def test_derived_component_requires_derivation_trace():
    with pytest.raises(AuthoritativePublicationContractError, match="require derivation_references"):
        build_governed_semantic_component(
            component_id="ineligible_consequence",
            status="SATISFIED",
            evidence_references=("evidence:claim-sequence",),
            semantic_basis="DERIVED",
        )

    item = build_governed_semantic_component(
        component_id="ineligible_consequence",
        status="SATISFIED",
        evidence_references=("evidence:claim-sequence",),
        semantic_basis="DERIVED",
        derivation_references=("derivation:restoration:triggering-claim",),
    )
    assert item.semantic_basis == "DERIVED"
    assert item.derivation_references == ("derivation:restoration:triggering-claim",)


def test_asserted_component_rejects_derivation_trace_and_unknown_basis():
    with pytest.raises(AuthoritativePublicationContractError, match="must not carry derivation_references"):
        build_governed_semantic_component(
            component_id="eligibility_criteria",
            status="SATISFIED",
            evidence_references=("evidence:eligibility",),
            semantic_basis="ASSERTED",
            derivation_references=("derivation:unexpected",),
        )
    with pytest.raises(AuthoritativePublicationContractError, match="semantic_basis"):
        build_governed_semantic_component(
            component_id="eligibility_criteria",
            status="SATISFIED",
            evidence_references=("evidence:eligibility",),
            semantic_basis="COMPUTED",
        )


def test_projection_requires_components_and_unique_component_ids():
    with pytest.raises(AuthoritativePublicationContractError, match="must not be empty"):
        projection(semantic_components=())
    with pytest.raises(AuthoritativePublicationContractError, match="must be unique"):
        projection(semantic_components=(component(), component()))


def test_projection_requires_both_trace_types():
    with pytest.raises(AuthoritativePublicationContractError, match="evidence_trace"):
        projection(evidence_trace_references=())
    with pytest.raises(AuthoritativePublicationContractError, match="certification_trace"):
        projection(certification_trace_references=())


def test_input_preserves_validated_decision_and_projection():
    result = build_authoritative_publication_input(
        publication_id="publication-1",
        publication_decision=decision(),
        governed_projection=projection(),
        publication_authority="governance-board",
    )
    assert result.publication_decision.decision_status == "PUBLISH"
    assert result.governed_projection.projection_id == "projection-1"
    with pytest.raises(FrozenInstanceError):
        result.publication_id = "changed"  # type: ignore[misc]


def test_input_rejects_unknown_contract_version_and_unvalidated_values():
    with pytest.raises(AuthoritativePublicationContractError, match="contract_version"):
        build_authoritative_publication_input(
            publication_id="publication-1",
            publication_decision=decision(),
            governed_projection=projection(),
            publication_authority="governance-board",
            contract_version="2.0",
        )
    with pytest.raises(AuthoritativePublicationContractError, match="PublicationDecisionResult"):
        build_authoritative_publication_input(
            publication_id="publication-1",
            publication_decision=object(),  # type: ignore[arg-type]
            governed_projection=projection(),
            publication_authority="governance-board",
        )
