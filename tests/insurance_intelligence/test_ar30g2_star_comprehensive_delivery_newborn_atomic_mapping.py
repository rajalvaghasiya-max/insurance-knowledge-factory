from __future__ import annotations

import json
import re
from pathlib import Path


G1_PATH = Path(
    "docs/architecture/AR_3_0_G1_STAR_COMPREHENSIVE_EVIDENCE_INVENTORY.json"
)
G2_PATH = Path(
    "docs/architecture/AR_3_0_G2_STAR_COMPREHENSIVE_DELIVERY_NEWBORN_ATOMIC_MAPPING.json"
)
REGISTRATION_PATH = Path(
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/policy_wording_registration.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _registered_candidate_text() -> str:
    registration = _load(REGISTRATION_PATH)
    return _normalized(
        "\n".join(
            candidate["excerpt"]
            for candidate in registration["evidence_review"]["candidates"]
        )
    )


def test_g2_is_bound_to_g1_int02_and_the_same_immutable_policy_wording() -> None:
    g1 = _load(G1_PATH)
    g2 = _load(G2_PATH)

    pressure = next(
        unit
        for unit in g1["candidate_pressure_units"]
        if unit["pressure_id"] == "G1-INT-02"
    )

    assert g2["source_pressure_id"] == pressure["pressure_id"]
    assert g2["source_inventory_path"] == G1_PATH.as_posix()
    assert g2["source_registration_path"] == REGISTRATION_PATH.as_posix()
    assert g2["source_document_id"] == g1["source_authority"]["document_id"]
    assert g2["source_document_version_id"] == g1["source_authority"]["document_version_id"]
    assert g2["source_content_sha256"] == g1["source_authority"]["content_sha256"]


def test_g2_source_markers_exist_in_registered_policy_wording() -> None:
    g2 = _load(G2_PATH)
    candidate_text = _registered_candidate_text()

    assert len(g2["source_markers"]) >= 5
    for marker in g2["source_markers"]:
        assert _normalized(marker) in candidate_text, marker


def test_g2_decomposes_delivery_newborn_into_separate_atomic_roles() -> None:
    g2 = _load(G2_PATH)
    units = g2["atomic_normative_units"]

    assert len(units) == 11
    assert len({unit["unit_id"] for unit in units}) == len(units)
    roles = [unit["semantic_role"] for unit in units]

    assert "BENEFIT_SCOPE" in roles
    assert "DELIVERY_LIMIT_RULE" in roles
    assert "NEWBORN_LIMIT_RULE" in roles
    assert "WAITING_PERIOD_DURATION" in roles
    assert "WAITING_PERIOD_ANCHOR" in roles
    assert "CONTINUITY_CONDITION" in roles
    assert "RESET_TRIGGER" in roles
    assert "RESET_EFFECT" in roles
    assert roles.count("EXPENSE_EXCLUSION") == 2
    assert "BENEFIT_INTERACTION_EXCLUSION" in roles
    assert all(unit["binding_status"] == "CANDIDATE_NOT_GOVERNED" for unit in units)


def test_g2_preserves_post_claim_reset_as_explicit_stateful_relationships() -> None:
    g2 = _load(G2_PATH)
    units = {unit["unit_id"]: unit for unit in g2["atomic_normative_units"]}
    relationships = {
        (item["type"], item["from_unit"], item["to_unit"])
        for item in g2["relationships"]
    }

    assert units["G2-DNB-04"]["normalized_value"] == {
        "duration": 24,
        "unit": "months",
    }
    assert units["G2-DNB-08"]["normalized_value"] == {
        "duration": 24,
        "unit": "months",
        "reset_behavior": "RESTART_AFTER_TRIGGER",
    }
    assert ("TRIGGERS", "G2-DNB-07", "G2-DNB-08") in relationships
    assert ("RESTARTS", "G2-DNB-08", "G2-DNB-04") in relationships
    assert ("ANCHORS", "G2-DNB-05", "G2-DNB-04") in relationships
    assert ("CONDITIONS", "G2-DNB-06", "G2-DNB-04") in relationships


def test_g2_does_not_flatten_exclusions_or_invent_unreviewed_limit_values() -> None:
    g2 = _load(G2_PATH)
    units = {unit["unit_id"]: unit for unit in g2["atomic_normative_units"]}
    relationships = {
        (item["type"], item["from_unit"], item["to_unit"])
        for item in g2["relationships"]
    }

    for exclusion_id in ("G2-DNB-09", "G2-DNB-10", "G2-DNB-11"):
        assert ("EXCLUDES_FROM", exclusion_id, "G2-DNB-01") in relationships

    assert "normalized_value" not in units["G2-DNB-02"]
    assert "normalized_value" not in units["G2-DNB-03"]

    residue = {item["residue_id"]: item for item in g2["residue"]}
    assert "LIMIT_VALUE_PUBLICATION" in residue["G2-DNB-X01"]["blocks"]
    assert "LIMIT_VALUE_PUBLICATION" in residue["G2-DNB-X02"]["blocks"]
    assert "SECTION_COMPLETENESS" in residue["G2-DNB-X03"]["blocks"]


def test_g2_accounting_is_complete_without_claiming_publication_or_comparison_readiness() -> None:
    g2 = _load(G2_PATH)
    accounting = g2["accounting"]

    assert g2["status"] == "ATOMIC_MAPPING_PROPOSED_NOT_BOUND"
    assert accounting["unaccounted_mechanics"] == []
    assert set(accounting["g1_observed_mechanics"]) == (
        set(accounting["accounted_as_atomic_units"])
        | set(accounting["accounted_as_atomic_plus_residue"])
    )

    guardrails = " ".join(g2["guardrails"]).casefold()
    assert "does not publish a governed product fact" in guardrails
    assert "comparison readiness" in guardrails
    assert "explicit residue" in guardrails
    assert "no star-specific reasoning branch" in guardrails
