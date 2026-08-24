import pytest

from insurance_intelligence.contracts.health_domain_registry import (
    ClaimAspect,
    DomainKnowledgeMaturity,
    DomainKnowledgeRecord,
    HealthDomainRegistryError,
    KnowledgePlane,
    ProductSemanticMaturity,
    ProductSemanticRecord,
    SemanticBlockingState,
    domain_knowledge_can_answer,
)


def test_claim_aspects_place_same_concept_in_different_planes():
    regulatory = ClaimAspect(
        aspect_id="ped.regulatory_definition",
        concept_id="health:ped",
        plane=KnowledgePlane.REGULATORY_LIFECYCLE,
        claim_type="regulatory_definition",
        authority_context="current effective IRDAI rule",
    )
    product = ClaimAspect(
        aspect_id="ped.product_waiting_implementation",
        concept_id="health:ped",
        plane=KnowledgePlane.PRODUCT_MECHANIC,
        claim_type="product_waiting_implementation",
        authority_context="current applicable product wording and schedule context",
    )
    assert regulatory.concept_id == product.concept_id
    assert regulatory.plane is not product.plane


def test_domain_knowledge_never_authorizes_instance_specific_answer():
    assert domain_knowledge_can_answer(instance_context_in_scope=False) is True
    assert domain_knowledge_can_answer(instance_context_in_scope=True) is False


def test_unknown_variant_space_cannot_be_closed():
    with pytest.raises(HealthDomainRegistryError, match="permanently true"):
        DomainKnowledgeRecord(
            concept_id="health:copayment",
            maturity=DomainKnowledgeMaturity.DK1_AUTHORITATIVE_DEFINITION_AVAILABLE,
            authoritative_definition_refs=("irdai:copayment",),
            unknown_variant_space_open=False,
        )


def test_product_semantic_blocking_state_is_not_a_maturity_score():
    record = ProductSemanticRecord(
        concept_id="health:waiting_period",
        semantic_variant_id="personal_underwriting_specific",
        product_reference="niva_bupa:reassure_3_0",
        product_version_reference="NBHHLIP26047V012526",
        blocking_state=SemanticBlockingState.REPRESENTATION_GAP,
        evidence_reference_ids=("candidate_page_33",),
    )
    assert record.maturity is None
    assert record.blocking_state is SemanticBlockingState.REPRESENTATION_GAP


def test_maturity_and_blocking_state_cannot_both_be_set():
    with pytest.raises(HealthDomainRegistryError, match="exactly one"):
        ProductSemanticRecord(
            concept_id="health:copayment",
            semantic_variant_id="room_category_matrix",
            product_reference="niva_bupa:reassure_3_0",
            product_version_reference="NBHHLIP26047V012526",
            maturity=ProductSemanticMaturity.PS1_EVIDENCE_OBSERVED,
            blocking_state=SemanticBlockingState.REPRESENTATION_GAP,
            evidence_reference_ids=("candidate_page_6", "candidate_page_62"),
        )


def test_representation_gap_requires_observed_evidence():
    with pytest.raises(HealthDomainRegistryError, match="requires observed evidence"):
        ProductSemanticRecord(
            concept_id="health:waiting_period",
            semantic_variant_id="personal_underwriting_specific",
            product_reference="niva_bupa:reassure_3_0",
            product_version_reference="NBHHLIP26047V012526",
            blocking_state=SemanticBlockingState.REPRESENTATION_GAP,
        )


def test_dk3_stays_general_even_when_explanation_ready():
    record = DomainKnowledgeRecord(
        concept_id="health:portability",
        maturity=DomainKnowledgeMaturity.DK3_EXPLANATION_READY,
        authoritative_definition_refs=("irdai:portability",),
        boundary_notes=(
            "General portability rights are distinct from a product's treatment of ported continuity.",
        ),
    )
    assert record.maturity is DomainKnowledgeMaturity.DK3_EXPLANATION_READY
    assert domain_knowledge_can_answer(instance_context_in_scope=True) is False
