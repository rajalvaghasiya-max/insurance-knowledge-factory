"""Governed Activ One NXT Super Reload implementation for MO-025D."""
from __future__ import annotations

from datetime import date

from insurance_intelligence.benefits.catalogue import (
    RESTORATION_BENEFIT_CONCEPT,
    RESTORATION_CONCEPT_ID,
)
from insurance_intelligence.benefits.contracts import (
    BenefitAvailability,
    BenefitEvidenceReference,
    BenefitImplementationType,
    BenefitMechanic,
    MechanicValueType,
    ProductBenefitImplementation,
    PublicationStatus,
    ReviewStatus,
)

ACTIV_ONE_NXT_PRODUCT_VARIANT_ID = "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324"

_POLICY_EVIDENCE_ID = "ev_activ_one_nxt_super_reload_policy_wording"
_PROSPECTUS_EVIDENCE_ID = "ev_activ_one_nxt_super_reload_prospectus"

ACTIV_ONE_NXT_RESTORATION_EVIDENCE = (
    BenefitEvidenceReference(
        evidence_reference_id=_POLICY_EVIDENCE_ID,
        source_document_id="aditya_birla_health_activ_one_policy_wording_adihlip24097v012324",
        source_sha256="d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451",
        authority_type="policy_wording",
        evidence_locator="Activ One NXT, Section C.8 Super Reload, policy wording page 30; Annexure III Product Benefit Table, page 46",
        bounded_evidence_identity="bounded:activ_one_nxt:super_reload:policy_wording:adihlip24097v012324",
    ),
    BenefitEvidenceReference(
        evidence_reference_id=_PROSPECTUS_EVIDENCE_ID,
        source_document_id="aditya_birla_health_activ_one_prospectus_adihlip24097v012324",
        source_sha256="8923d6457d368c9d80d097032a7b784c65b30ba07ae68ea7474af7569332fa56",
        authority_type="prospectus",
        evidence_locator="Section C.10 Super Reload, prospectus page 3; Super Reload Illustration (NXT Plan), page 10",
        bounded_evidence_identity="bounded:activ_one_nxt:super_reload:prospectus:adihlip24097v012324",
    ),
)

_ALL_EVIDENCE_IDS = (_POLICY_EVIDENCE_ID, _PROSPECTUS_EVIDENCE_ID)

ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION = ProductBenefitImplementation(
    implementation_id="benefit_impl:aditya_birla_health:activ_one_nxt:super_reload:v1",
    concept_id=RESTORATION_CONCEPT_ID,
    insurer_id="aditya_birla_health",
    product_id="activ_one",
    product_variant_id=ACTIV_ONE_NXT_PRODUCT_VARIANT_ID,
    marketing_name="Super Reload",
    availability=BenefitAvailability.INCLUDED,
    implementation_type=BenefitImplementationType.BUILT_IN,
    mechanics=(
        BenefitMechanic(
            dimension_id="restoration_percentage",
            value_type=MechanicValueType.PERCENTAGE,
            value=100,
            unit="percent_of_base_sum_insured_per_activation",
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="restoration_count_per_policy_period",
            value_type=MechanicValueType.ENUM,
            value="unlimited_during_policy_year",
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="trigger_requirement",
            value_type=MechanicValueType.ENUM,
            value="base_sum_insured_and_accumulated_super_credit_exhausted_or_insufficient_for_claim",
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="trigger_timing",
            value_type=MechanicValueType.ENUM,
            value="within_admissible_claim_when_available_capacity_is_insufficient",
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="same_hospitalization_use",
            value_type=MechanicValueType.BOOLEAN,
            value=True,
            applicability={"basis": "may contribute within the claim that triggers insufficiency"},
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="subsequent_hospitalization_use",
            value_type=MechanicValueType.BOOLEAN,
            value=True,
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="first_claim_use",
            value_type=MechanicValueType.BOOLEAN,
            value=True,
            applicability={"qualification": "as specified in the Policy Schedule or Product Benefit Table"},
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="partial_restoration_use",
            value_type=MechanicValueType.BOOLEAN,
            value=True,
            evidence_reference_ids=(_PROSPECTUS_EVIDENCE_ID,),
        ),
        BenefitMechanic(
            dimension_id="maximum_liability_per_claim_percentage",
            value_type=MechanicValueType.PERCENTAGE,
            value=100,
            unit="percent_of_base_sum_insured",
            evidence_reference_ids=(_POLICY_EVIDENCE_ID,),
        ),
        BenefitMechanic(
            dimension_id="covered_section_scope",
            value_type=MechanicValueType.TEXT,
            value="C.1 Hospitalization Treatment, C.4 Domiciliary Hospitalization, C.5 Home Health Care, C.6 AYUSH Treatment and C.7 Organ Donor Expenses",
            evidence_reference_ids=(_POLICY_EVIDENCE_ID,),
        ),
        BenefitMechanic(
            dimension_id="utilization_sequence",
            value_type=MechanicValueType.TEXT,
            value="Base Sum Insured -> Super Credit (if applicable) -> Super Reload -> Cancer Booster (if applicable)",
            evidence_reference_ids=(_POLICY_EVIDENCE_ID,),
        ),
        BenefitMechanic(
            dimension_id="policy_year_reset",
            value_type=MechanicValueType.BOOLEAN,
            value=True,
            applicability={"basis": "frequency and availability are defined per Policy Year"},
            evidence_reference_ids=_ALL_EVIDENCE_IDS,
        ),
        BenefitMechanic(
            dimension_id="floater_operation",
            value_type=MechanicValueType.ENUM,
            value="available_for_any_or_all_insured_persons_subject_to_policy_schedule",
            evidence_reference_ids=(_POLICY_EVIDENCE_ID,),
        ),
    ),
    evidence_references=ACTIV_ONE_NXT_RESTORATION_EVIDENCE,
    behaviour_signature_id="bsig:activ_one_nxt:super_reload:100pct_unlimited_exhausted_or_insufficient_same_claim",
    conditions=(
        "The underlying claim must be admissible under one of the listed covered sections.",
        "The Base Sum Insured and accumulated Super Credit, if applicable, must be exhausted or insufficient for the claim.",
        "First-claim availability remains subject to the Policy Schedule or Product Benefit Table.",
        "The governed implementation is limited to the Activ One NXT variant.",
    ),
    limitations=(
        "Maximum liability from Super Reload under a single claim is the Base Sum Insured.",
        "Super Reload does not increase the amount used to calculate accumulated Super Credit.",
        "Variant applicability and in-force benefits remain controlled by the Policy Schedule.",
    ),
    exclusions=(
        "No related-versus-unrelated illness restriction is asserted because the governing clause does not state one.",
        "No carry-forward between policy years is asserted because the governing clause does not state one.",
        "No entitlement or claim-payment conclusion is created by this catalogue record.",
    ),
    review_status=ReviewStatus.APPROVED,
    publication_status=PublicationStatus.PUBLISHED,
    effective_from=date(2025, 1, 1),
)

ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.validate_against(RESTORATION_BENEFIT_CONCEPT)

__all__ = [
    "ACTIV_ONE_NXT_PRODUCT_VARIANT_ID",
    "ACTIV_ONE_NXT_RESTORATION_EVIDENCE",
    "ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION",
]
