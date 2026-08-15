from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    PublicationBlockerCode,
    ResidueRecord,
    blocker_for_residue,
)


G2_PATH = Path(
    "docs/architecture/AR_3_0_G2_STAR_COMPREHENSIVE_DELIVERY_NEWBORN_ATOMIC_MAPPING.json"
)
G3_PATH = Path(
    "docs/architecture/AR_3_0_G3_STAR_COMPREHENSIVE_DELIVERY_NEWBORN_GENERIC_MAPPING.json"
)
G4_PATH = Path(
    "docs/architecture/AR_3_0_G4_STAR_COMPREHENSIVE_COMPARISON_READINESS_PRESSURE.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_g4_pressure_is_bound_to_certified_g2_and_g3_artifacts() -> None:
    g4 = _load(G4_PATH)

    assert g4["source_g2_path"] == G2_PATH.as_posix()
    assert g4["source_g3_path"] == G3_PATH.as_posix()
    assert G2_PATH.exists()
    assert G3_PATH.exists()
    assert g4["product_reference"] == "star_health:star_comprehensive"
    assert g4["comparison_subject"] == "delivery_newborn"


def test_g4_preserves_cross_family_interactions_instead_of_flattening_features() -> None:
    g4 = _load(G4_PATH)
    interactions = {item["interaction_id"]: item for item in g4["mapped_interactions"]}

    assert set(g4["represented_families"]) >= {
        "benefit_scope",
        "waiting_periods",
        "benefit_limits",
        "expense_exclusions",
        "benefit_interactions",
        "event_triggered_reset_relationship",
    }
    assert interactions["G4-DNB-I03"]["state"] == "MAPPED_AS_RELATIONSHIP"
    assert set(interactions["G4-DNB-I03"]["families"]) == {
        "benefit_event",
        "waiting_periods",
    }
    assert interactions["G4-DNB-I05"]["state"] == "MAPPED_WITH_MATERIAL_RESIDUE"


def test_g4_carries_every_material_g2_residue_forward() -> None:
    g2 = _load(G2_PATH)
    g4 = _load(G4_PATH)

    g2_residue_ids = {item["residue_id"] for item in g2["residue"]}
    carried = {item["source_residue_id"] for item in g4["material_residue"]}

    assert carried == g2_residue_ids
    assert all(item["material"] is True for item in g4["material_residue"])
    assert all(
        item["accounting_state"] == "DEFERRED_WITH_REASON"
        for item in g4["material_residue"]
    )
    assert all(
        item["blocker_code"] == "MATERIAL_RESIDUE"
        for item in g4["material_residue"]
    )


def test_generic_residue_contract_converts_material_deferred_residue_to_blocker() -> None:
    applicability = ApplicabilityKey(product_reference="star_health:star_comprehensive")
    residue = ResidueRecord(
        residue_id="g4_delivery_limit_rows",
        normative_unit_id="G2-DNB-02",
        concept="benefit_limits",
        applicability=applicability,
        accounting_state=AccountingState.DEFERRED_WITH_REASON,
        reason="Exact per-delivery limit rows remain unresolved.",
        material=True,
    )

    blocker = blocker_for_residue(residue)

    assert blocker is not None
    assert blocker.code is PublicationBlockerCode.MATERIAL_RESIDUE
    assert blocker.normative_unit_ids == ("G2-DNB-02",)
    assert blocker.applicability.product_reference == "star_health:star_comprehensive"


def test_g4_material_residue_dominates_comparison_readiness() -> None:
    g4 = _load(G4_PATH)
    readiness = g4["readiness_assessment"]

    assert readiness["semantic_mapping_complete_for_represented_slice"] is True
    assert readiness["cross_family_relationships_preserved"] is True
    assert readiness["material_residue_present"] is True
    assert readiness["limit_values_complete"] is False
    assert readiness["section_completeness_established"] is False
    assert readiness["publication_ready"] is False
    assert readiness["comparison_ready"] is False
    assert readiness["customer_applicability_ready"] is False
    assert readiness["net_product_direction_permitted"] is False
    assert readiness["decision"] == "BLOCKED_BY_MATERIAL_RESIDUE"


def test_g4_does_not_authorize_new_contract_or_product_specific_reasoning() -> None:
    g4 = _load(G4_PATH)
    result = g4["architecture_result"]
    dominance = " ".join(g4["dominance_rules"]).casefold()

    assert result["new_generic_contract_required"] is False
    assert result["star_specific_runtime_logic_required"] is False
    assert result["existing_generic_residue_and_blocker_contracts_sufficient"] is True
    assert "mapped does not imply comparison-ready" in dominance
    assert "no winner, rank, recommendation, or net product direction" in dominance
