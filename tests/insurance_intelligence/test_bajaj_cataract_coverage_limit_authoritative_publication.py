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
    "generic_rule_certification/"
    "cataract_si_up_to_10_lakh_coverage_limit_publication_case.json"
)
CURRENT_SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"


def _load_spec() -> dict:
    return json.loads(PUBLICATION_CASE_PATH.read_text(encoding="utf-8"))


def _build_publication_chain():
    spec = _load_spec()
    certification_path = Path(spec["certification_case_path"])
    case = load_rule_certification_case_file(certification_path)
    certification = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
        trace_references=(
            "certification:bajaj_my_health_care_cataract_si_up_to_10_lakh_coverage_limit",
        ),
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


def test_bajaj_cataract_publication_case_is_data_only_current_and_bounded():
    spec, case, _, _, _, _ = _build_publication_chain()

    evidence = case.evidence_output.evidence_packages
    assert {item.lineage.source_artifact_sha256 for item in evidence} == {CURRENT_SHA}
    assert spec["publication_decision"]["requested_status"] == "PUBLISH"
    assert {
        item["component_id"] for item in spec["governed_projection"]["semantic_components"]
    } == {
        item.component_id for item in case.expectation.component_expectations
    }
    assert any("waiting-period duration" in item for item in spec["guardrails"])
    assert any("SI above INR 10 lakh 'Actual' branch" in item for item in spec["guardrails"])
    assert any("Family Visit" in item for item in spec["guardrails"])
    assert any("product-wide governed readiness" in item for item in spec["guardrails"])


def test_bajaj_cataract_reaches_publish_decision_without_dropping_limitations():
    _, _, certification, decision, projection, _ = _build_publication_chain()

    assert certification.outcome == "PASS"
    assert decision.requested_status == "PUBLISH"
    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    assert decision.authoritative_publication_created is False
    assert decision.failures == ()
    assert decision.limitations == certification.limitations == projection.limitations
    assert any("waiting-period duration" in item for item in decision.limitations)
    assert any("SI above INR 10 lakh 'Actual' branch" in item for item in decision.limitations)


def test_bajaj_cataract_creates_bounded_authoritative_publication():
    _, case, _, decision, _, publication = _build_publication_chain()

    assert publication.publication_status == "AUTHORITATIVE"
    assert publication.governed_subject_reference == case.expectation.governed_subject_reference
    assert (
        publication.certification_id
        == "bajaj_my_health_care_cataract_si_up_to_10_lakh_coverage_limit"
    )
    assert publication.topic_id == "coverage_limit"
    assert publication.topic_version == "1.0"
    assert publication.limitations == decision.limitations
    assert publication.evidence_trace_references == decision.evidence_trace_references
    assert publication.certification_trace_references == decision.certification_trace_references
    assert {item.component_id for item in publication.semantic_components} == {
        "covered_subject",
        "limit_value",
        "limit_basis",
        "applicability_scope",
    }
    assert all(item.status == "SATISFIED" for item in publication.semantic_components)
    evidence_ids = {item.evidence_id for item in case.evidence_output.evidence_packages}
    assert all(
        set(item.evidence_references).issubset(evidence_ids)
        for item in publication.semantic_components
    )
    assert publication.publication_receipt_id.startswith("publication_receipt_")
