import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = ROOT / "docs/architecture/health_product6_selection_abort_2026-08-24.json"


def _record():
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def test_product6_is_aborted_before_selection_or_semantic_scoring():
    record = _record()
    experiment = record["experiment"]
    assert experiment["product_number"] == 6
    assert experiment["product_selected"] is False
    assert experiment["selection_record_committed"] is False
    assert experiment["semantic_scoring_started"] is False
    assert experiment["repeatability_outcome_assigned"] is False


def test_abort_records_nonzero_preselection_target_clause_reads():
    reason = _record()["abort_reason"]
    assert reason["classification"] == "PRESELECTION_PROTOCOL_CONTAMINATION"
    assert reason["failed_primary_metric"] == "preselection_target_clause_reads"
    assert reason["metric_value"] == 2
    assert reason["intentional_semantic_selection"] is False
    assert reason["semantic_content_used_to_choose_product"] is False


def test_product6_cannot_be_used_as_repeatability_or_motor_gate_result():
    governance = _record()["governance_decision"]
    assert governance["product6_must_not_be_selected_or_scored"] is True
    assert governance["product6_is_not_a_repeatability_result"] is True
    assert governance["historical_product5_result_unchanged"] is True
    assert governance["post_hc1_baseline_unchanged"] is True
    assert governance["runtime_or_semantic_extension_authorized"] is False
    assert governance["motor_readiness_authorized"] is False


def test_replacement_attempt_requires_product7_and_acko_exclusion():
    next_attempt = _record()["next_neutral_attempt_requirements"]
    assert next_attempt["new_product_number_required"] is True
    assert next_attempt["next_product_number"] == 7
    assert next_attempt["ACKO_must_be_excluded_from_next_selection"] is True
    assert "Do not open policy wordings, prospectuses, CIS documents, proposal forms" in next_attempt["metadata_source_restriction"]
    assert next_attempt["selection_record_must_merge_before_any_selected_product_document_is_opened"] is True


def test_acko_candidate_uins_are_only_metadata_progress_not_selection():
    record = _record()
    candidates = record["metadata_progress_before_abort"]["candidate_identity_observations"]
    assert {item["uin"] for item in candidates} == {
        "ACKHLIP20183V011920",
        "ACKHLIP21105V012021",
        "ACKHLIP23114V012223",
        "ACKHLIP23202V012223",
        "ACKHLIP25037V012425",
        "ACKHLIP26036V012526",
        "ACKHLIP27040V012627",
    }
    assert all(item["repository_exact_uin_hit"] is False for item in candidates)
    assert record["metadata_progress_before_abort"]["archived_lower_uin_observation"]["uin"] == "ACKHLIP20039V012021"
