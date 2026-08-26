from __future__ import annotations

import json
from pathlib import Path

from factory_core.governance.preselection_metadata_projection import (
    BlindPreselectionMetadataProjector,
)


PROTOCOL_PATH = Path(
    "docs/architecture/health_post_hc1_neutral_cold_start_protocol_v8_product11.json"
)
ABORT_PATH = Path(
    "docs/architecture/health_product11_gate_c_preselection_contract_abort_2026-08-26.json"
)


def _signals() -> dict:
    return {
        "insurer_id": "example_insurer",
        "url": "https://example.test/health/products",
        "content_hash": "abc123",
        "page_intent": "article_or_product_related",
        "asset_scope": "product_related",
        "classification_rules_version": "1.0",
        "product_names": [{"name": "Example Health Plan"}],
        "uins": ["EXAHLIP26001V012526"],
        "uin_candidates": [
            {
                "uin": "EXAHLIP26001V012526",
                "candidate_status": "format_valid_candidate",
                "extraction_method": "product_uin_label",
                "source": {
                    "source_parsed_file": "workspace/parsed/example.json",
                    "insurer_id": "example_insurer",
                    "url": "https://example.test/health/products",
                    "content_hash": "abc123",
                },
            }
        ],
    }


def test_frozen_v8_gate_c_forbids_raw_url_at_selector_boundary() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    gate_c = protocol["gate_c_neutral_selection"]
    assert gate_c["selector_product_metadata_input_contract"] == (
        "blind_preselection_product_metadata_v1"
    )
    assert gate_c["selector_may_receive_raw_url_or_anchor_text"] is False
    assert protocol["freeze"]["runtime_change_allowed_during_initial_attempt"] is False
    assert gate_c["selection_override_authorized"] is False


def test_frozen_preselection_projection_requires_and_emits_raw_urls() -> None:
    projection = BlindPreselectionMetadataProjector.project(_signals()).to_dict()
    assert projection["projection_type"] == "blind_preselection_product_metadata_v1"
    assert projection["source_url"] == "https://example.test/health/products"
    assert projection["uin_candidates"][0]["source"]["url"] == (
        "https://example.test/health/products"
    )


def test_gate_c_contract_requirements_are_mutually_incompatible_without_change() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    gate_c = protocol["gate_c_neutral_selection"]
    projection = BlindPreselectionMetadataProjector.project(_signals()).to_dict()

    assert gate_c["selector_product_metadata_input_contract"] == projection["projection_type"]
    assert gate_c["selector_may_receive_raw_url_or_anchor_text"] is False
    assert isinstance(projection["source_url"], str) and projection["source_url"].startswith("https://")
    assert isinstance(projection["uin_candidates"][0]["source"]["url"], str)


def test_abort_preserves_completed_gates_and_proves_gate_c_never_started() -> None:
    record = json.loads(ABORT_PATH.read_text(encoding="utf-8"))
    experiment = record["experiment"]
    decision = record["gate_decision"]
    metrics = record["blindness_and_method_metrics"]

    assert experiment["gate_a_status"] == "PASS"
    assert experiment["gate_b_status"] == "PASS"
    assert experiment["gate_c_status"] == "NOT_STARTED"
    assert experiment["final_experiment_status"] == "EXPERIMENT_UNSCORED"
    assert decision["gate_b_pass_reversed"] is False
    assert decision["gate_c_started"] is False
    assert decision["product_screening_started"] is False
    assert decision["product_selected"] is False
    assert decision["semantic_repeatability_scored"] is False
    assert metrics["gate_c_selector_raw_url_reads"] == 0
    assert metrics["preselection_target_clause_reads"] == 0
    assert record["historical_integrity"]["motor_authorized"] is False
