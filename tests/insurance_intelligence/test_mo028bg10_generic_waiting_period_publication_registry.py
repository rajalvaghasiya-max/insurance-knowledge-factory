import json
from pathlib import Path

import pytest

from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_current import (
    ACTIV_ONE_NXT_COVERAGE as PRE_GENERALIZATION_ACTIV,
)
from insurance_intelligence.coverage_registry.health_generalized_current import (
    HEALTH_COVERAGE_REGISTRY,
    WAITING_PERIOD_PUBLICATIONS,
)
from insurance_intelligence.generic_knowledge.waiting_period_publication import (
    WaitingPeriodPublicationError,
    project_waiting_period_publication_to_coverage,
)


MANIFEST_PATH = Path(
    "knowledge/factory/migrations/health_waiting_period_publication_manifest_v1.json"
)
REVIEW_DECISION_PATH = Path(
    "docs/architecture/ACTIV_ONE_NXT_WAITING_PERIOD_REVIEW_DECISION.json"
)
PUBLICATION_MODULE = Path(
    "insurance_intelligence/generic_knowledge/waiting_period_publication.py"
)
GENERALIZED_REGISTRY_MODULE = Path(
    "insurance_intelligence/coverage_registry/health_generalized_current.py"
)
ACTIV_REFERENCE = "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324"
STAR_REFERENCE = "pv_star_health_star_comprehensive_shahlip26044v092526"


def _manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _review_decision():
    return json.loads(REVIEW_DECISION_PATH.read_text(encoding="utf-8"))


def _waiting(product):
    return next(item for item in product.concepts if item.concept_id == "waiting_periods")


def test_manifest_contains_both_human_approved_waiting_period_publications():
    manifest = _manifest()
    assert manifest["record_type"] == "generic_waiting_period_publication_manifest_v1"
    refs = {entry["product_reference"] for entry in manifest["entries"]}
    assert refs == set(WAITING_PERIOD_PUBLICATIONS) == {STAR_REFERENCE, ACTIV_REFERENCE}


def test_activ_manifest_entry_requires_approved_human_review() -> None:
    decision = _review_decision()
    assert decision["review_status"] == "APPROVED_FOR_GOVERNED_PROJECTION"
    assert decision["reviewed_by_human"] is True
    assert decision["adjudication_status"] == "HUMAN_APPROVED_REVIEW_DECISION"
    activ_entry = next(
        item for item in _manifest()["entries"] if item["product_reference"] == ACTIV_REFERENCE
    )
    assert activ_entry["review_status"] == "APPROVED"
    assert activ_entry["certification_as_of_date"] == "2026-08-10"


def test_both_generic_publications_are_eligible_and_published():
    assert len(WAITING_PERIOD_PUBLICATIONS) == 2
    for publication in WAITING_PERIOD_PUBLICATIONS.values():
        assert publication.published
        assert publication.eligibility.blockers == ()
        assert publication.semantic_facts
        assert publication.evidence_reference_ids


def test_both_products_are_certified_for_waiting_period_comparison():
    for product_reference in (STAR_REFERENCE, ACTIV_REFERENCE):
        product = HEALTH_COVERAGE_REGISTRY.get_product(product_reference)
        assert product is not None
        waiting = _waiting(product)
        assert waiting.status is ConceptCoverageStatus.CERTIFIED
        assert waiting.comparison_ready is True
        assert waiting.decision_support_ready is False
        assert waiting.evidence_reference_ids


def test_star_generic_publication_preserves_three_base_mechanics():
    publication = WAITING_PERIOD_PUBLICATIONS[STAR_REFERENCE]
    facts = {fact.value["waiting_period_type"]: fact.value for fact in publication.semantic_facts}
    assert facts["PRE_EXISTING_DISEASE"]["duration_value"] == 36
    assert facts["PRE_EXISTING_DISEASE"]["duration_unit"] == "MONTHS"
    assert facts["SPECIFIC_DISEASE_PROCEDURE"]["duration_value"] == 24
    assert facts["INITIAL"]["duration_value"] == 30


def test_activ_generic_publication_preserves_reviewed_base_mechanics():
    publication = WAITING_PERIOD_PUBLICATIONS[ACTIV_REFERENCE]
    facts = {fact.value["waiting_period_type"]: fact.value for fact in publication.semantic_facts}
    ped = facts["PRE_EXISTING_DISEASE"]
    assert ped["duration_value"] == 3
    assert ped["duration_unit"] == "YEARS"
    assert "policy schedule" in ped["schedule_dependency"].casefold()
    assert "product benefit table" in ped["schedule_dependency"].casefold()
    assert facts["SPECIFIC_DISEASE_PROCEDURE"]["duration_value"] == 24
    assert facts["INITIAL"]["duration_value"] == 30


def test_registry_evidence_is_projected_from_generic_publications():
    for product_reference, publication in WAITING_PERIOD_PUBLICATIONS.items():
        product = HEALTH_COVERAGE_REGISTRY.get_product(product_reference)
        waiting = _waiting(product)
        assert waiting.evidence_reference_ids == publication.evidence_reference_ids


def test_publications_bind_exact_governed_dependencies():
    for publication in WAITING_PERIOD_PUBLICATIONS.values():
        binding = publication.dependency_binding
        assert binding.ontology_version == "waiting_periods_v1"
        assert binding.source_document_id
        assert binding.source_document_version
        assert binding.source_hash_sha256
        assert binding.review_decision_version


def test_pre_generalization_snapshot_remains_historically_unchanged():
    waiting = _waiting(PRE_GENERALIZATION_ACTIV)
    assert waiting.status is ConceptCoverageStatus.NOT_AUTOMATED
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False


def test_generic_publication_module_contains_no_product_identity_branching():
    source = PUBLICATION_MODULE.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "star_health",
        "star_comprehensive",
        "shahlip",
        "aditya_birla_health",
        "activ_one_nxt",
        "adihlip",
    ):
        assert forbidden not in source


def test_generalized_registry_projection_contains_no_product_specific_imports_or_branches():
    source = GENERALIZED_REGISTRY_MODULE.read_text(encoding="utf-8").casefold()
    for forbidden in (
        "star_comprehensive_coverage",
        "activ_one_nxt_coverage",
        "star_health",
        "star_comprehensive",
        "shahlip",
        "aditya_birla_health",
        "activ_one_nxt",
        "adihlip",
        "if insurer ==",
        "if insurer_id ==",
        "if product ==",
        "if product_id ==",
        "if product_reference ==",
        "if product_reference in (",
    ):
        assert forbidden not in source
    assert "product_reference" in source


def test_blocked_publication_cannot_promote_registry():
    product_reference, publication = next(iter(WAITING_PERIOD_PUBLICATIONS.items()))
    product = HEALTH_COVERAGE_REGISTRY.get_product(product_reference)
    blocked = type(publication)(
        publication_id=publication.publication_id,
        applicability_product_reference=publication.applicability_product_reference,
        semantic_facts=publication.semantic_facts,
        evidence_reference_ids=publication.evidence_reference_ids,
        dependency_binding=publication.dependency_binding,
        eligibility=type(publication.eligibility)(
            status=type(publication.eligibility.status).BLOCKED,
            concept=publication.eligibility.concept,
            applicability=publication.eligibility.applicability,
            dependency_binding=publication.eligibility.dependency_binding,
            blockers=publication.eligibility.blockers,
        ),
    )
    with pytest.raises(WaitingPeriodPublicationError):
        project_waiting_period_publication_to_coverage(product, blocked)
