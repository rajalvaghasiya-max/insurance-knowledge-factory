from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_PRODUCT_VARIANT_ID,
    ACTIV_ONE_NXT_RESTORATION_EVIDENCE,
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.catalogue import RESTORATION_CONCEPT_ID
from insurance_intelligence.benefits.contracts import (
    MechanicValueType,
    ProductBenefitImplementation,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_SPEC = (
    REPO_ROOT
    / "docs"
    / "architecture"
    / "aditya_birla_activ_one_product_identity_reference_spec.json"
)

EXPECTED_POLICY_SHA256 = (
    "d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451"
)
EXPECTED_PROSPECTUS_SHA256 = (
    "8923d6457d368c9d80d097032a7b784c65b30ba07ae68ea7474af7569332fa56"
)


def _identity() -> dict:
    return json.loads(IDENTITY_SPEC.read_text(encoding="utf-8"))["product_identity"]


def _mechanics() -> dict[str, object]:
    return {
        item.dimension_id: item
        for item in ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics
    }


def test_hg4_uses_governed_product_identity_not_historical_identity_output() -> None:
    identity = _identity()
    finding = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION

    assert identity == {
        "entity_id": "aditya_birla_health:activ_one",
        "insurer_id": "aditya_birla_health",
        "product_id": "activ_one",
        "canonical_product_name": "Activ One",
        "uin": "ADIHLIP24097V012324",
    }
    assert finding.insurer_id == identity["insurer_id"]
    assert finding.product_id == identity["product_id"]
    assert identity["uin"].casefold() in ACTIV_ONE_NXT_PRODUCT_VARIANT_ID.casefold()


def test_hg4_restoration_result_is_typed_governed_product_benefit() -> None:
    finding = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION

    assert isinstance(finding, ProductBenefitImplementation)
    assert finding.concept_id == RESTORATION_CONCEPT_ID
    assert finding.marketing_name == "Super Reload"
    assert finding.is_governed_for_use is True
    assert finding.product_variant_id == ACTIV_ONE_NXT_PRODUCT_VARIANT_ID


def test_hg4_evidence_is_bound_to_byte_verified_authoritative_documents() -> None:
    evidence = {
        item.authority_type: item for item in ACTIV_ONE_NXT_RESTORATION_EVIDENCE
    }

    assert set(evidence) == {"policy_wording", "prospectus"}
    assert evidence["policy_wording"].source_sha256 == EXPECTED_POLICY_SHA256
    assert evidence["prospectus"].source_sha256 == EXPECTED_PROSPECTUS_SHA256

    assert "Section C.8 Super Reload" in evidence["policy_wording"].evidence_locator
    assert "page 30" in evidence["policy_wording"].evidence_locator
    assert "page 46" in evidence["policy_wording"].evidence_locator
    assert "Section C.10 Super Reload" in evidence["prospectus"].evidence_locator
    assert "page 3" in evidence["prospectus"].evidence_locator
    assert "page 10" in evidence["prospectus"].evidence_locator

    assert evidence["policy_wording"].bounded_evidence_identity
    assert evidence["prospectus"].bounded_evidence_identity


def test_hg4_typed_mechanics_preserve_core_super_reload_semantics() -> None:
    mechanics = _mechanics()

    restoration = mechanics["restoration_percentage"]
    assert restoration.value_type is MechanicValueType.PERCENTAGE
    assert restoration.value == 100
    assert restoration.unit == "percent_of_base_sum_insured_per_activation"

    frequency = mechanics["restoration_count_per_policy_period"]
    assert frequency.value_type is MechanicValueType.ENUM
    assert frequency.value == "unlimited_during_policy_year"

    trigger = mechanics["trigger_requirement"]
    assert trigger.value == (
        "base_sum_insured_and_accumulated_super_credit_exhausted_or_insufficient_for_claim"
    )

    assert mechanics["same_hospitalization_use"].value is True
    assert mechanics["first_claim_use"].value is True
    assert mechanics["subsequent_hospitalization_use"].value is True
    assert mechanics["policy_year_reset"].value is True


def test_hg4_policy_wording_controls_scope_and_single_claim_limit() -> None:
    mechanics = _mechanics()

    scope = mechanics["covered_section_scope"]
    assert scope.evidence_reference_ids == (
        "ev_activ_one_nxt_super_reload_policy_wording",
    )
    assert scope.value == (
        "C.1 Hospitalization Treatment, C.4 Domiciliary Hospitalization, "
        "C.5 Home Health Care, C.6 AYUSH Treatment and C.7 Organ Donor Expenses"
    )

    per_claim = mechanics["maximum_liability_per_claim_percentage"]
    assert per_claim.value == 100
    assert per_claim.unit == "percent_of_base_sum_insured"
    assert per_claim.evidence_reference_ids == (
        "ev_activ_one_nxt_super_reload_policy_wording",
    )


def test_hg4_does_not_invent_unsupported_restoration_mechanics() -> None:
    mechanics = _mechanics()
    finding = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION

    assert "same_illness_use" not in mechanics
    assert "relapse_window_days" not in mechanics
    assert "carry_over_between_policy_years" not in mechanics

    assert any(
        "related-versus-unrelated illness" in item for item in finding.exclusions
    )
    assert any("carry-forward" in item for item in finding.exclusions)
    assert any("claim-payment conclusion" in item for item in finding.exclusions)


def test_hg4_finding_preserves_evidence_lineage_for_every_mechanic() -> None:
    finding = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION
    evidence_ids = {
        item.evidence_reference_id for item in finding.evidence_references
    }

    assert evidence_ids == {
        "ev_activ_one_nxt_super_reload_policy_wording",
        "ev_activ_one_nxt_super_reload_prospectus",
    }
    for mechanic in finding.mechanics:
        assert mechanic.evidence_reference_ids
        assert set(mechanic.evidence_reference_ids) <= evidence_ids
