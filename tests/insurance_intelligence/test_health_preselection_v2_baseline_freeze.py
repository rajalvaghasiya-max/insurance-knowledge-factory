from __future__ import annotations

import json
from pathlib import Path

from factory_core.governance.preselection_metadata_projection import (
    BlindPreselectionMetadataProjector,
    BlindPreselectionMetadataProjectorV2,
)


FREEZE_PATH = Path(
    "docs/architecture/health_preselection_blindness_boundary_v2_baseline_freeze_2026-08-26.json"
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


def test_freeze_pins_exact_repair_merge_and_test_attestation() -> None:
    record = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert record["record_status"] == "FROZEN_PROSPECTIVE_BASELINE"
    assert record["repair_merge"]["pr_number"] == 165
    assert record["repair_merge"]["merge_commit"] == (
        "ad5183e8e2b3a871b10df9d052c127feb806c3c5"
    )
    assert record["verification"]["local_full_suite_result"] == "3091 passed"
    assert record["verification"]["mergeability_was_not_treated_as_test_evidence"] is True


def test_v2_freeze_forbids_raw_selector_location_fields() -> None:
    record = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    boundary = record["frozen_boundary"]
    assert boundary["raw_url_may_enter_selector_context"] is False
    assert boundary["raw_anchor_text_may_enter_selector_context"] is False
    assert boundary["raw_parsed_file_path_may_enter_selector_context"] is False
    assert boundary["raw_page_or_product_signal_output_may_enter_selector_context"] is False
    assert boundary["semantic_bucket_presence_or_counts_may_enter_selector_context"] is False
    assert boundary["source_ref_is_selector_authority_or_currentness_evidence"] is False

    projection = BlindPreselectionMetadataProjectorV2.project(_signals()).to_dict()
    text = json.dumps(projection, sort_keys=True)
    assert "https://example.test/health/products" not in text
    assert "workspace/parsed/example.json" not in text
    assert "source_url" not in projection
    assert projection["source_ref"].startswith("src_sha256:")


def test_v1_is_preserved_for_historical_replay_while_v2_is_future_only() -> None:
    record = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    assert record["frozen_boundary"]["v1_retained_unchanged_for_historical_replay"] is True
    assert record["immutability"]["repair_applies_only_to_future_experiments"] is True
    assert record["immutability"]["product11_may_be_reopened_or_retried"] is False

    v1 = BlindPreselectionMetadataProjector.project(_signals()).to_dict()
    v2 = BlindPreselectionMetadataProjectorV2.project(_signals()).to_dict()
    assert v1["projection_type"] == "blind_preselection_product_metadata_v1"
    assert v1["source_url"] == "https://example.test/health/products"
    assert v2["projection_type"] == "blind_preselection_product_metadata_v2"
    assert "source_url" not in v2


def test_freeze_does_not_authorize_next_health_experiment_or_motor() -> None:
    record = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    gate = record["future_experiment_gate"]
    assert gate["next_health_experiment_authorized_by_this_freeze_alone"] is False
    assert gate["motor_authorized"] is False
    assert "new immutable preregistration with a new Health product number" in gate[
        "required_before_next_health_experiment"
    ]
    assert "protocol explicitly names blind_preselection_product_metadata_v2" in gate[
        "required_before_next_health_experiment"
    ]
