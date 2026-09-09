from pathlib import Path

from insurance_intelligence.authoritative_publication.governed import (
    build_governed_authoritative_publication,
)
from insurance_intelligence.publication_decision.governed import (
    build_governed_publication_context,
    build_governed_publication_decision,
)


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_SPEC_PATH = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/v2/"
    "governance/bajaj_my_health_care_v2_lab_radiology_copay_publication_spec.json"
)
BAJAJ_V2_COPAY_BINDING_PATH = (
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/v2/"
    "generic_legal_condition_binding/bajaj_my_health_care_v2_copayment_binding.json"
)
BAJAJ_LAB_ASSERTION_ID = (
    "ga_bajaj_my_health_care_lab_radiology_unapproved_reimbursement_copay_v1"
)


def _attributes(publication) -> dict[str, str]:
    result: dict[str, str] = {}
    for component in publication.semantic_components:
        for attribute in component.semantic_attributes:
            result[attribute.key] = attribute.value
    return result


def test_bounded_bajaj_lab_assertion_certifies_from_restored_governed_lineage() -> None:
    _, case, certification = build_governed_publication_context(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=ROOT,
    )

    assert case.case_id == f"conditional_copayment:{BAJAJ_LAB_ASSERTION_ID}"
    assert certification.outcome == "PASS"
    assert certification.actual_completeness_status == "COMPLETE"
    assert certification.actual_explanation_permitted is True
    assert certification.governed_subject_reference == f"assertion:{BAJAJ_LAB_ASSERTION_ID}"
    assert certification.trace_references == (BAJAJ_V2_COPAY_BINDING_PATH,)
    assert any("bound_not_published" in item for item in certification.limitations)
    assert any("policy-specific co-payment options" in item for item in certification.limitations)


def test_bajaj_publication_decision_resolves_only_publication_state_boundary() -> None:
    decision = build_governed_publication_decision(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=ROOT,
    )

    assert decision.decision_status == "PUBLISH"
    assert decision.publication_permitted is True
    assert decision.authoritative_publication_created is False
    assert decision.certification_trace_references == (BAJAJ_V2_COPAY_BINDING_PATH,)
    assert decision.authorization_id == (
        "publication-boundary:bajaj-my-health-care-v2:lab-radiology-copay"
    )
    assert len(decision.resolved_certification_limitations) == 1
    assert "bound_not_published" in decision.resolved_certification_limitations[0]
    assert all("bound_not_published" not in item for item in decision.limitations)
    assert any("policy-specific co-payment options" in item for item in decision.limitations)
    assert any("claim payment" in item for item in decision.limitations)


def test_bajaj_authoritative_publication_preserves_certified_structured_semantics() -> None:
    publication = build_governed_authoritative_publication(
        publication_spec_path=PUBLICATION_SPEC_PATH,
        repository_root=ROOT,
    )
    attributes = _attributes(publication)

    assert publication.publication_status == "AUTHORITATIVE"
    assert publication.governed_subject_reference == f"assertion:{BAJAJ_LAB_ASSERTION_ID}"
    assert publication.certification_trace_references == (BAJAJ_V2_COPAY_BINDING_PATH,)
    assert publication.authorization_id == (
        "publication-boundary:bajaj-my-health-care-v2:lab-radiology-copay"
    )
    assert attributes["rate"] == "20% of the admissible claim amount"
    assert "not pre-approved" in attributes["trigger_condition"]
    assert attributes["applicability_scope"] == (
        "For Doctor Prescribed Investigations - Pathology & Radiology"
    )
    assert any("policy-specific co-payment options" in item for item in publication.limitations)
    assert any("claim payment" in item for item in publication.limitations)
    for component in publication.semantic_components:
        assert component.evidence_references
        for attribute in component.semantic_attributes:
            assert set(attribute.evidence_references) <= set(component.evidence_references)


def test_bajaj_publication_requires_no_product_specific_publication_module() -> None:
    assert not (ROOT / "insurance_intelligence/publication_decision/bajaj.py").exists()
    assert not (ROOT / "insurance_intelligence/authoritative_publication/bajaj.py").exists()
