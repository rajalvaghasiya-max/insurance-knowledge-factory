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


def test_manifest_contains_only_human_approved_waiting_period_publications():
    manifest = _manifest()
    assert manifest["record_type"] == "generic_waiting_period_publication_manifest_v1"
    refs = {entry["product_reference"] for entry in manifest["entries"]}
    assert refs == set(WAITING_PERIOD_PUBLICATIONS) == {STAR_REFERENCE}
    assert ACTIV_REFERENCE not in refs


def test_star_generic_publication_is_eligible_and_published():
    publication = WAITING_PERIOD_PUBLICATIONS[STAR_REFERENCE]
    assert publication.published
    assert publication.eligibility.blockers == ()
    assert publication.semantic_facts
    assert publication.evidence_reference_ids


def test_star_is_certified_for_waiting_period_comparison():
    product = HEALTH_COVERAGE_REGISTRY.get_product(STAR_REFERENCE)
    assert product is not None
    waiting = _waiting(product)
    assert waiting.status is ConceptCoverageStatus.CERTIFIED
    assert waiting.comparison_ready is True
    assert waiting.decision_support_ready is False
    assert waiting.evidence_reference_ids


def test_activ_remains_not_automated_until_human_review_and_publication():
    product = HEALTH_COVERAGE_REGISTRY.get_product(ACTIV_REFERENCE)
    assert product is not None
    waiting = _waiting(product)
    assert waiting.status is ConceptCoverageStatus.NOT_AUTOMATED
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    assert ACTIV_REFERENCE not in WAITING_PERIOD_PUBLICATIONS


def test_activ_review_decision_is_explicitly_pending_human_approval():
    decision = _review_decision()
    assert decision["review_status"] == "PENDING_HUMAN_APPROVAL"
    assert decision["reviewed_by_human"] is False
    assert decision["adjudication_status"] == "PROPOSED_REVIEW_DECISION"
    boundary = decision["publication_boundary"]
    assert boundary["human_base_clause_review_approved"] is False
    assert boundary["runtime_publication_created"] is False
    assert boundary["authoritative_publication_created"] is False
    assert boundary["coverage_registry_promoted"] is False


def test_activ_proposed_review_keeps_base_and_modifier_candidates_separate():
    decision = _review_decision()
    by_type = {item["waiting_period_type"]: item for item in decision["decisions"]}
    assert set(by_type) == {
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
        "INITIAL",
    }
    assert by_type["PRE_EXISTING_DISEASE"]["base_candidate_ids"] == [
        "wp_candidate_124e9d18ecae07d9ed02"
    ]
    assert by_type["SPECIFIC_DISEASE_PROCEDURE"]["base_candidate_ids"] == [
        "wp_candidate_124e9d18ecae07d9ed02"
    ]
    assert by_type["INITIAL"]["base_candidate_ids"] == [
        "wp_candidate_b962d57da994bcbe774f"
    ]
    rejected_reasons = " ".join(
        rejected["reason"]
        for item in decision["decisions"]
        for rejected in item["rejected_candidates"]
    ).casefold()
    assert "optional cover" in rejected_reasons
    assert "chronic-care" in rejected_reasons or "chronic-care benefit" in rejected_reasons


def test_star_generic_publication_preserves_three_base_mechanics():
    publication = WAITING_PERIOD_PUBLICATIONS[STAR_REFERENCE]
    facts = {fact.value["waiting_period_type"]: fact.value for fact in publication.semantic_facts}
    assert facts["PRE_EXISTING_DISEASE"]["duration_value"] == 36
    assert facts["PRE_EXISTING_DISEASE"]["duration_unit"] == "MONTHS"
    assert facts["SPECIFIC_DISEASE_PROCEDURE"]["duration_value"] == 24
    assert facts["INITIAL"]["duration_value"] == 30


def test_registry_evidence_is_projected_from_star_generic_publication():
    publication = WAITING_PERIOD_PUBLICATIONS[STAR_REFERENCE]
    product = HEALTH_COVERAGE_REGISTRY.get_product(STAR_REFERENCE)
    waiting = _waiting(product)
    assert waiting.evidence_reference_ids == publication.evidence_reference_ids


def test_publication_binds_exact_governed_dependencies():
    publication = WAITING_PERIOD_PUBLICATIONS[STAR_REFERENCE]
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
