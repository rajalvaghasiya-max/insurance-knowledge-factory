from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_reassure3_copayment_gap_preserves_exact_evidence_and_does_not_coerce() -> None:
    data = _load(
        "docs/architecture/niva_bupa_reassure_3_0_copayment_representation_gap_2026-08-24.json"
    )

    assert data["repeatability_classification"]["classification"] == "REPRESENTATION_GAP"
    assert data["governance"]["runtime_changed_during_initial_attempt"] is False
    assert data["governance"]["silent_semantic_coercion_performed"] is False

    candidates = {item["candidate_id"]: item for item in data["reviewed_candidate_inventory"]}
    assert candidates["candidate_page_44"]["candidate_text_sha256"] == (
        "37c05717baaf50fd15af0789332fc8dad9eadda19018b86755330041f0acc52d"
    )
    assert candidates["candidate_page_45"]["candidate_text_sha256"] == (
        "ffea1ca232b2297bafeca6c9856968b1136b7e8cf217a25aa01dc202e48a2f46"
    )
    assert candidates["candidate_page_6"]["candidate_text_sha256"] == (
        "8618196b8e6301231ea75f8f9166afa91ae2e158ec3fd5aa24b12c010adce973"
    )
    assert candidates["candidate_page_62"]["candidate_text_sha256"] == (
        "42f0ddcced22cc7ce18f757c01e8de8a679d8b0772ded9ce1854094eba94b4dc"
    )


def test_reassure3_copayment_gap_is_targeted_not_broad_rewrite() -> None:
    data = _load(
        "docs/architecture/niva_bupa_reassure_3_0_copayment_representation_gap_2026-08-24.json"
    )

    gap_ids = {item["gap_id"] for item in data["representation_gaps"]}
    assert gap_ids == {
        "REASSURE3_COPAY_GAP_01_ADDITIVE_CUMULATIVE_COMPOSITION",
        "REASSURE3_COPAY_GAP_02_ROOM_MATRIX_MULTISPAN_CALCULATION_BASIS",
    }
    assert data["repeatability_classification"]["architecture_failure_scope"] == (
        "TARGETED_GENERIC_EXTENSION_REQUIRED"
    )
    assert "explicit source-stated 0% percentage under a documented condition" in data[
        "pre_existing_shapes_that_reuse_cleanly"
    ]


def test_product5_result_follows_preregistered_v2_failure_rule() -> None:
    data = _load("docs/architecture/health_product5_repeatability_result_2026-08-24.json")

    assert data["pre_selection_runtime_baseline_commit"] == (
        "ee82220ef8ccca586f5e5760bf937c51644c712b"
    )
    assert data["target_concepts"]["waiting_period"]["classification"] == "REPRESENTATION_GAP"
    assert data["target_concepts"]["copayment"]["classification"] == "REPRESENTATION_GAP"
    assert data["primary_metrics"]["all_primary_metrics_zero"] is True
    assert data["protocol_outcome"]["classification"] == "REPEATABILITY_NOT_PROVEN"
    assert data["protocol_outcome"]["repeatability_proven"] is False
    assert data["protocol_outcome"]["repeatability_failed"] is True
    assert data["protocol_outcome"]["architecture_rework_triggered"] is False
    assert data["protocol_outcome"]["targeted_generic_extensions_earned"] is True


def test_product5_result_forbids_retroactive_or_semantically_lossy_rescoring() -> None:
    data = _load("docs/architecture/health_product5_repeatability_result_2026-08-24.json")
    non_actions = "\n".join(data["explicit_non_actions"])

    assert "do not relabel Personal Waiting Period as BENEFIT_SPECIFIC" in non_actions
    assert "do not flatten additional/cumulative copayment" in non_actions
    assert "do not certify the room-category matrix from page 62" in non_actions
    assert "do not retroactively rescore product4 or product5" in non_actions
