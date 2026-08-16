from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.authoritative_publication.gate import (
    create_authoritative_publication,
)
from insurance_intelligence.contracts.authoritative_publication import (
    build_authoritative_publication_input,
    build_governed_publication_projection,
    build_governed_semantic_component,
)
from insurance_intelligence.contracts.publication_decision import (
    build_publication_decision_input,
)
from insurance_intelligence.publication_decision.evaluator import (
    evaluate_publication_decision,
)
from insurance_intelligence.rule_certification.case_loader import (
    load_rule_certification_case_file,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification


PUBLICATION_CASE_PATH = Path(
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/"
    "generic_rule_certification/restoration_claim_sequence_publication_case.json"
)
CURRENT_SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"


def _load_spec() -> dict:
    return json.loads(PUBLICATION_CASE_PATH.read_text(encoding="utf-8"))


def _build_chain():
    spec = _load_spec()
    case = load_rule_certification_case_file(Path(spec["certification_case_path"]))
    certification = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
        trace_references=("certification:bajaj_my_health_care_restoration_claim_sequence",),
    )

    decision_spec = spec["publication_decision"]
    decision = evaluate_publication_decision(
        build_publication_decision_input(
            decision_id=decision_spec["decision_id"],
            governed_subject_reference=certification.governed_subject_reference,
            certification_result=certification,
            requested_status=decision_spec["requested_status"],
            decision_reasons=decision_spec["decision_reasons"],
            limitations=certification.limitations,
            evidence_trace_references=decision_spec["evidence_trace_references"],
            decision_authority=decision_spec["decision_authority"],
        )
    )

    projection_spec = spec["governed_projection"]
    projection = build_governed_publication_projection(
        projection_id=projection_spec["projection_id"],
        governed_subject_reference=decision.governed_subject_reference,
        certification_id=decision.certification_id,
        topic_id=decision.topic_id,
        topic_version=decision.topic_version,
        semantic_components=tuple(
            build_governed_semantic_component(
                component_id=item["component_id"],
                status="SATISFIED",
                evidence_references=item["evidence_references"],
                semantic_basis=item["semantic_basis"],
                derivation_references=item["derivation_references"],
            )
            for item in projection_spec["semantic_components"]
        ),
        limitations=decision.limitations,
        evidence_trace_references=decision.evidence_trace_references,
        certification_trace_references=decision.certification_trace_references,
    )

    publication_spec = spec["authoritative_publication"]
    publication = create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id=publication_spec["publication_id"],
            publication_decision=decision,
            governed_projection=projection,
            publication_authority=publication_spec["publication_authority"],
        )
    )
    return spec, case, certification, decision, projection, publication


def test_restoration_claim_sequence_certification_is_bounded_and_current_source_anchored():
    _, case, certification, _, _, _ = _build_chain()

    assert certification.outcome == "PASS"
    assert certification.actual_completeness_status == "COMPLETE"
    assert certification.actual_explanation_permitted is True
    assert {item.lineage.source_artifact_sha256 for item in case.evidence_output.evidence_packages} == {CURRENT_SHA}
    assert any("activation trigger remains unresolved" in item for item in certification.limitations)
    assert any("restored amount remains unresolved" in item for item in certification.limitations)


def test_publication_decision_preserves_unresolved_restoration_residue():
    _, _, certification, decision, projection, _ = _build_chain()

    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    assert decision.limitations == certification.limitations == projection.limitations
    assert any("same-illness parenthetical scope remains unresolved" in item for item in decision.limitations)
    assert any("positive later-claim entitlement must not be inferred" in item.lower() for item in decision.limitations)


def test_authoritative_publication_preserves_asserted_vs_derived_semantic_basis():
    _, _, _, _, _, publication = _build_chain()

    by_id = {item.component_id: item for item in publication.semantic_components}
    assert by_id["eligibility_criteria"].semantic_basis == "ASSERTED"
    assert by_id["applicability_scope"].semantic_basis == "ASSERTED"
    assert by_id["eligible_consequence"].semantic_basis == "ASSERTED"
    assert by_id["ineligible_consequence"].semantic_basis == "DERIVED"
    assert by_id["ineligible_consequence"].derivation_references == (
        "derivation:bajaj-mhc-restoration:triggering-claim-overflow",
    )


def test_authoritative_publication_claim_boundary_stays_narrow():
    spec, _, _, _, _, publication = _build_chain()

    assert publication.publication_status == "AUTHORITATIVE"
    assert publication.topic_id == "eligibility_and_consequence"
    assert publication.certification_id == "bajaj_my_health_care_restoration_claim_sequence_eligibility"
    assert any("does not publish the exact activation trigger" in item for item in spec["guardrails"])
    assert any("cross-insurer restoration generalization" in item for item in spec["guardrails"])
    assert publication.publication_receipt_id.startswith("publication_receipt_")
