from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "docs" / "architecture" / "health_product9_operator_path_guardrail_2026-08-25.json"


def _guardrail() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_guardrail_only_narrows_locked_v6_protocol() -> None:
    payload = _guardrail()

    assert payload["parent_protocol_commit"] == "71cf561a078aa75dbdc637c79ab7b709f7ad5e1e"
    assert payload["changes_parent_selection_rules"] is False
    assert payload["changes_candidate_pool"] is False
    assert payload["changes_direct_source_roots"] is False
    assert payload["changes_projection_contract"] is False


def test_operator_must_classify_destination_before_rendering_body() -> None:
    boundary = _guardrail()["operator_visibility_boundary"]

    assert boundary["raw_page_or_document_body_may_be_rendered_before_metadata_classification"] is False
    assert boundary["target_concept_text_may_be_rendered_before_product_selection_merge"] is False
    assert "destination page body" in boundary["pre_render_classification_must_not_consume"]
    assert "destination PDF text" in boundary["pre_render_classification_must_not_consume"]
    assert boundary["unknown_destination_rule"] == "DO_NOT_RENDER_AND_FAIL_CLOSED_FOR_THAT_PATH"
    assert "unknown_or_unclassifiable_destination" in boundary["prohibited_destination_classes_before_selection_merge"]


def test_preregistered_403_roots_are_logged_without_search_fallback() -> None:
    observations = _guardrail()["root_availability_observations_before_first_insurer_render"]
    by_root = {item["root"]: item for item in observations}

    assert by_root["https://irdai.gov.in/non-life-insurers1"]["result"] == "PREREGISTERED_ROOT_UNAVAILABLE_403"
    assert by_root["https://irdai.gov.in/health-insurers1"]["result"] == "PREREGISTERED_ROOT_UNAVAILABLE_403"
    assert by_root["https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount"]["result"] == "PREREGISTERED_ROOT_AVAILABLE"
    assert all(item["fallback_search_used"] is False for item in observations)


def test_candidate_order_is_preregistered_and_semantically_blind() -> None:
    provenance = _guardrail()["candidate_order_provenance"]

    assert provenance["semantic_content_used_to_establish_order"] is False
    assert provenance["order"] == [
        "Cholamandalam MS General Insurance Company Limited",
        "Magma General Insurance Limited",
        "Navi General Insurance Limited",
        "Shriram General Insurance Company Limited",
    ]
    assert provenance["order_change_authorized_during_run"] is False


def test_no_insurer_or_target_content_was_seen_before_guardrail_lock() -> None:
    state = _guardrail()["current_run_state"]

    assert state == {
        "product9_selected": False,
        "first_insurer_origin_rendered": False,
        "product_document_opened": False,
        "target_clause_read_count": 0,
        "search_fallback_count": 0,
    }
