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
    "knowledge/factory/registry_backed/aditya_birla_health_activ_one/"
    "generic_rule_certification/capacity_ordering_publication_case.json"
)
CURRENT_SHA = "38bb879030d905bd6f90915915f1c2e22e27ebe5bc980bba766c69c7ecd90a16"
DERIVATION_SHA = "01cde101c59e4c22250638cd75c6f846d6a7823feebb1bf392a413b4c9e34554"


def _load_spec() -> dict:
    return json.loads(PUBLICATION_CASE_PATH.read_text(encoding="utf-8"))


def _build_chain():
    spec = _load_spec()
    case = load_rule_certification_case_file(Path(spec["certification_case_path"]))
    certification = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
        trace_references=("certification:activ_one_capacity_ordering",),
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


def test_capacity_ordering_certification_is_current_source_anchored_and_bounded():
    _, case, certification, _, _, _ = _build_chain()

    assert certification.outcome == "PASS"
    assert certification.actual_completeness_status == "COMPLETE"
    assert certification.actual_explanation_permitted is True
    assert {item.lineage.source_artifact_sha256 for item in case.evidence_output.evidence_packages} == {CURRENT_SHA}
    assert {item.lineage.governed_record_sha256 for item in case.evidence_output.evidence_packages} == {DERIVATION_SHA}
    assert any("does not calculate claim payment" in item.lower() for item in certification.limitations)
    assert any("next capacity" in item.lower() and "payment" in item.lower() for item in certification.limitations)


def test_capacity_ordering_publication_preserves_asserted_vs_derived_basis():
    _, _, _, decision, _, publication = _build_chain()

    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    by_id = {item.component_id: item for item in publication.semantic_components}
    assert by_id["applicability_scope"].semantic_basis == "ASSERTED"
    assert by_id["eligibility_criteria"].semantic_basis == "DERIVED"
    assert by_id["eligible_consequence"].semantic_basis == "DERIVED"
    assert by_id["ineligible_consequence"].semantic_basis == "DERIVED"
    assert by_id["eligible_consequence"].derivation_references == (
        "derivation:activ-one-capacity-ordering:next-capacity",
    )


def test_authoritative_capacity_ordering_publication_does_not_claim_payment():
    spec, _, certification, _, _, publication = _build_chain()

    assert publication.publication_status == "AUTHORITATIVE"
    assert publication.topic_id == "eligibility_and_consequence"
    assert publication.certification_id == "activ_one_capacity_ordering_eligibility"
    assert publication.limitations == certification.limitations
    assert any("does not calculate claim payment" in item.lower() for item in publication.limitations)
    assert any("selected next capacity" in item.lower() and "payment" in item.lower() for item in spec["guardrails"])
    assert publication.publication_receipt_id.startswith("publication_receipt_")
