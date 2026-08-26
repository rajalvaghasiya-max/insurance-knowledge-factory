from __future__ import annotations

import json
from pathlib import Path


FREEZE_PATH = Path(
    "docs/architecture/health_identity_currentness_acquisition_repair_v1_freeze.json"
)


def _load() -> dict:
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


def test_repair_is_prospective_health_only_and_does_not_preregister_product13() -> None:
    record = _load()
    assert record["record_status"] == "PROSPECTIVE_REPAIR_IMPLEMENTED_PENDING_GREEN_MERGE"
    assert record["domain"] == "health"
    integrity = record["historical_integrity"]
    assert integrity["product11_changed_or_retried"] is False
    assert integrity["product12_changed_or_retried"] is False
    assert integrity["product13_preregistration_authorized_before_this_repair_merges_green"] is False
    assert integrity["motor_authorized"] is False


def test_repair_keeps_v2_and_adds_raw_location_free_currentness_companion() -> None:
    record = _load()
    implementation = record["implementation"]
    assert implementation["selector_product_contract"] == "blind_preselection_product_metadata_v2"
    assert implementation["selector_currentness_companion_contract"] == (
        "blind_product_identity_currentness_evidence_v1"
    )
    blindness = record["provenance_and_blindness"]
    for key in (
        "selector_raw_url_fields",
        "selector_raw_anchor_fields",
        "selector_raw_parsed_path_fields",
        "selector_page_body_fields",
        "selector_screenshot_fields",
        "selector_semantic_bucket_fields",
        "target_clause_reads",
    ):
        assert blindness[key] == 0


def test_source_ref_is_not_authority_or_currentness_by_itself() -> None:
    record = _load()
    blindness = record["provenance_and_blindness"]
    assert blindness["source_ref_is_authority_evidence_by_itself"] is False
    assert blindness["source_ref_is_currentness_evidence_by_itself"] is False
    assert (
        blindness[
            "authority_scope_must_be_explicitly_supplied_by_authorized_machine_side_acquisition_context"
        ]
        is True
    )
    assert blindness["currentness_status_must_be_explicitly_observed_in_artifact_text"] is True


def test_ambiguous_identity_and_currentness_fail_closed() -> None:
    record = _load()
    rules = record["identity_and_currentness_rules"]
    assert rules["missing_currentness"] == "not_observed"
    assert rules["conflicting_currentness"] == "ambiguous"
    assert rules["multiple_or_cross_product_binding"] == "ambiguous_identity_binding"
    assert rules["missing_product_or_uin"] == "insufficient_identity_evidence"
    assert rules["ambiguous_identity_or_currentness_may_be_selected"] is False
