from __future__ import annotations

import json
import re
from pathlib import Path


INVENTORY_PATH = Path(
    "docs/architecture/AR_3_0_G1_STAR_COMPREHENSIVE_EVIDENCE_INVENTORY.json"
)
REGISTRATION_PATH = Path(
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_source_registration/policy_wording_registration.json"
)

APPROVED_DOCUMENT_ID = "star_health_star_comprehensive_policy_wording_v1"
APPROVED_DOCUMENT_VERSION_ID = (
    "docver_star_health_star_comprehensive_policy_wording_v1_b1dbe8fb78646f75"
)
APPROVED_CONTENT_SHA256 = (
    "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _registered_candidate_text(registration: dict) -> str:
    candidates = registration["evidence_review"]["candidates"]
    assert candidates
    return _normalized("\n".join(candidate["excerpt"] for candidate in candidates))


def test_g1_inventory_is_bound_to_the_registered_immutable_policy_wording() -> None:
    inventory = _load(INVENTORY_PATH)
    registration = _load(REGISTRATION_PATH)

    source = inventory["source_authority"]
    document = registration["document"]

    assert source["registration_path"] == REGISTRATION_PATH.as_posix()
    assert source["document_id"] == document["document_id"] == APPROVED_DOCUMENT_ID
    assert (
        source["document_version_id"]
        == document["document_version_id"]
        == APPROVED_DOCUMENT_VERSION_ID
    )
    assert source["content_sha256"] == document["content_sha256"] == APPROVED_CONTENT_SHA256
    assert source["document_type"] == document["document_type"] == "policy_wording"
    assert source["authority_role"] == "PRIMARY_LEGAL_EVIDENCE_CANDIDATE"


def test_every_g1_pressure_unit_has_real_markers_in_registered_policy_wording() -> None:
    inventory = _load(INVENTORY_PATH)
    registration = _load(REGISTRATION_PATH)
    candidate_text = _registered_candidate_text(registration)

    pressure_units = inventory["candidate_pressure_units"]
    assert {unit["pressure_id"] for unit in pressure_units} == {
        "G1-WP-01",
        "G1-WP-02",
        "G1-WP-03",
        "G1-INT-01",
        "G1-LIM-01",
        "G1-INT-02",
    }

    for unit in pressure_units:
        assert unit["source_markers"], unit["pressure_id"]
        assert unit["observed_mechanics"], unit["pressure_id"]
        assert unit["g1_disposition"].endswith("NOT_A_GOVERNED_FACT")
        for marker in unit["source_markers"]:
            assert _normalized(marker) in candidate_text, (
                f"{unit['pressure_id']} marker missing from registered policy wording: {marker!r}"
            )


def test_g1_keeps_transitional_intelligence_and_coverage_audit_non_authoritative() -> None:
    inventory = _load(INVENTORY_PATH)
    locators = {item["path"]: item for item in inventory["transitional_locator_only"]}

    assert (
        "knowledge/health/star_health/star_comprehensive/intelligence/product_intelligence.json"
        in locators
    )
    assert (
        "knowledge/health/star_health/star_comprehensive/intelligence/policy_intelligence.json"
        in locators
    )
    assert (
        "knowledge/health/coverage_audits/star_health_star_comprehensive_coverage_audit.json"
        in locators
    )

    assert all(item["authority"] is False for item in locators.values())
    assert all("DO_NOT" in item["prohibited_use"] for item in locators.values())


def test_g1_inventory_does_not_claim_publication_or_comparison_readiness() -> None:
    inventory = _load(INVENTORY_PATH)

    assert inventory["status"] == "EVIDENCE_INVENTORIED_NOT_YET_BOUND"
    guardrails = " ".join(inventory["g1_guardrails"]).casefold()
    assert "does not assert publication" in guardrails
    assert "comparison readiness" in guardrails
    assert "atomic normative units in g2" in guardrails
    assert "no new generic abstraction is authorized" in guardrails


def test_g1_prioritizes_interaction_pressure_before_simple_waiting_period_scalars() -> None:
    inventory = _load(INVENTORY_PATH)

    assert inventory["recommended_g2_order"][:3] == [
        "G1-INT-02",
        "G1-INT-01",
        "G1-LIM-01",
    ]
    assert inventory["recommended_g2_order"][-1] == "G1-WP-01"
