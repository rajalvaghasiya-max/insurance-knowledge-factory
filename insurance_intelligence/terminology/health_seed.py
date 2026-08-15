"""Governed Health terminology seed set for MO-024C.

This module defines the first reusable Health-domain canonical concept vocabulary.
It is intentionally small and high-value. The entries are language-routing assets,
not policy facts: they identify what concept a user is referring to, but do not
state whether a particular product contains the concept or how it applies.
"""
from __future__ import annotations

from insurance_intelligence.contracts.terminology import CanonicalConceptFamily
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
)


def _concept(
    concept_id: str,
    canonical_name: str,
    definition: str,
    *,
    concept_type: str,
    aliases: tuple[str, ...] = (),
    customer_phrases: tuple[str, ...] = (),
    insurer_terms: tuple[str, ...] = (),
    not_synonyms: tuple[str, ...] = (),
    ambiguity_group: str | None = None,
    downstream_topic: str | None = None,
) -> CanonicalConceptDefinition:
    return CanonicalConceptDefinition(
        concept=CanonicalConceptFamily(
            concept_family_id=concept_id,
            canonical_name=canonical_name,
            definition=definition,
            domain="health",
        ),
        concept_type=concept_type,
        aliases=aliases,
        customer_phrases=customer_phrases,
        insurer_terms=insurer_terms,
        not_synonyms=not_synonyms,
        ambiguity_group=ambiguity_group,
        downstream_topic=downstream_topic,
    )


HEALTH_CONCEPTS_V1: tuple[CanonicalConceptDefinition, ...] = (
    _concept(
        "health:concept:copayment",
        "Co-payment",
        "A cost-sharing concept where the insured bears a specified share of an admissible claim amount when the governed terms apply.",
        concept_type="COST_SHARING",
        aliases=("copay", "co pay", "co-payment", "co payment"),
        customer_phrases=("percentage I pay on a claim", "share of the claim I have to pay", "amount I pay myself"),
        insurer_terms=("co-pay",),
        ambiguity_group="health:ambiguity:out_of_pocket_cost_sharing",
        downstream_topic="conditional_copayment",
    ),
    _concept(
        "health:concept:deductible",
        "Deductible",
        "A cost-sharing concept where a specified amount must be borne before or outside the insurer's payable portion, subject to the governed terms.",
        concept_type="COST_SHARING",
        aliases=("deductible amount",),
        customer_phrases=("amount I pay before insurance starts paying", "amount I pay myself"),
        ambiguity_group="health:ambiguity:out_of_pocket_cost_sharing",
        downstream_topic="deductible",
    ),
    _concept(
        "health:concept:room_rent_limit",
        "Room rent limit",
        "A coverage-limit concept governing the eligible room category or room-charge amount under the policy terms.",
        concept_type="LIMIT",
        aliases=("room rent cap", "room rent sub-limit", "room category limit"),
        customer_phrases=("limit on hospital room", "which room can I take", "room eligibility"),
        downstream_topic="room_rent_limit",
    ),
    _concept(
        "health:concept:waiting_period",
        "Waiting period",
        "An eligibility-timing concept requiring a specified period to pass before stated coverage becomes available, subject to the policy terms.",
        concept_type="WAITING_PERIOD",
        aliases=("waiting time", "coverage waiting period"),
        customer_phrases=("how long before this is covered", "when does this coverage start"),
        downstream_topic="waiting_period",
    ),
    _concept(
        "health:concept:pre_existing_disease",
        "Pre-existing disease",
        "A health-insurance concept referring to a condition treated as pre-existing under the applicable governed definition.",
        concept_type="ELIGIBILITY",
        aliases=("PED", "pre existing disease", "pre-existing condition", "pre existing condition"),
        customer_phrases=("illness I already had before buying the policy",),
        downstream_topic="pre_existing_disease",
    ),
    _concept(
        "health:concept:restoration",
        "Restoration of sum insured",
        "A benefit concept under which available cover may be replenished or restored when the governed conditions are satisfied.",
        concept_type="BENEFIT",
        aliases=("restoration benefit", "restore benefit", "sum insured restoration"),
        customer_phrases=("does my cover come back after a claim",),
        not_synonyms=("recharge", "recharge benefit", "refill", "refill benefit", "reinstatement"),
        downstream_topic="restoration",
    ),
    _concept(
        "health:concept:sum_insured",
        "Sum insured",
        "The governed coverage amount that defines the principal monetary limit of protection, subject to applicable terms and sub-limits.",
        concept_type="COVERAGE",
        aliases=("SI", "cover amount", "coverage amount"),
        customer_phrases=("how much am I insured for", "total health cover"),
        downstream_topic="sum_insured",
    ),
    _concept(
        "health:concept:sub_limit",
        "Sub-limit",
        "A limit concept that caps coverage for a specified benefit, service, condition, category, or expense below the broader coverage amount.",
        concept_type="LIMIT",
        aliases=("sublimit", "sub limit", "benefit cap"),
        customer_phrases=("separate limit for this benefit", "cap inside my total cover"),
        downstream_topic="sub_limit",
    ),
    _concept(
        "health:concept:exclusion",
        "Exclusion",
        "A coverage-boundary concept identifying circumstances, treatments, conditions, expenses, or events that are not covered under the governed terms.",
        concept_type="EXCLUSION",
        aliases=("policy exclusion", "excluded expense", "not covered item"),
        customer_phrases=("what is not covered", "when will the policy not cover me"),
        downstream_topic="exclusion",
    ),
    _concept(
        "health:concept:network_hospital",
        "Network hospital",
        "A claim-process concept identifying a hospital that participates in the insurer's or administrator's governed network for applicable services.",
        concept_type="CLAIM_PROCESS",
        aliases=("network provider", "empanelled hospital", "cashless hospital"),
        customer_phrases=("hospital in insurer network",),
        downstream_topic="network_hospital",
    ),
    _concept(
        "health:concept:cashless_claim",
        "Cashless claim",
        "A claim-process concept where eligible hospital expenses may be settled directly with the healthcare provider under the applicable process and policy terms.",
        concept_type="CLAIM_PROCESS",
        aliases=("cashless", "cashless treatment", "cashless hospitalization"),
        customer_phrases=("can the insurer pay the hospital directly",),
        downstream_topic="cashless_claim",
    ),
    _concept(
        "health:concept:reimbursement_claim",
        "Reimbursement claim",
        "A claim-process concept where the insured first incurs eligible expenses and subsequently seeks reimbursement under the applicable process and policy terms.",
        concept_type="CLAIM_PROCESS",
        aliases=("reimbursement", "reimbursement basis"),
        customer_phrases=("I paid the hospital and want to claim it back",),
        downstream_topic="reimbursement_claim",
    ),
)


def build_health_concept_registry_v1() -> CanonicalConceptRegistry:
    """Return the immutable first governed Health concept registry snapshot."""
    return CanonicalConceptRegistry(HEALTH_CONCEPTS_V1)
