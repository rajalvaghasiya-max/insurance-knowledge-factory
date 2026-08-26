from __future__ import annotations

import json
from pathlib import Path


FREEZE_PATH = Path(
    "docs/architecture/health_product12_preregistration_v9_freeze.json"
)


def _freeze() -> dict:
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


def test_product12_freeze_is_pre_gate_a_and_unselected() -> None:
    record = _freeze()
    assertions = record["preregistration_assertions"]
    assert record["record_status"] == "LOCKED_BEFORE_PRODUCT12_GATE_A_EXECUTION"
    assert record["product_number"] == 12
    assert assertions["gate_a_started"] is False
    assert assertions["gate_b_started"] is False
    assert assertions["gate_c_started"] is False
    assert assertions["product_screening_started"] is False
    assert assertions["product_selected"] is False
    assert assertions["target_clause_reads"] == 0


def test_product12_freeze_pins_v2_and_blindness_boundary() -> None:
    assertions = _freeze()["preregistration_assertions"]
    assert assertions["selector_product_metadata_contract"] == (
        "blind_preselection_product_metadata_v2"
    )
    assert assertions["raw_url_or_anchor_selector_reads_allowed"] is False
    assert assertions["raw_parsed_file_path_selector_reads_allowed"] is False
    assert assertions["semantic_bucket_selector_reads_allowed"] is False
    assert assertions["source_ref_authority_or_currentness_use_allowed"] is False


def test_product12_freeze_preserves_gate_sequence_and_no_midrun_repair() -> None:
    record = _freeze()
    sequence = record["execution_sequence"]
    immutable = record["immutability"]
    assert sequence[:5] == [
        "merge preregistration with full suite green",
        "execute Gate A only",
        "freeze Gate A result before Gate B",
        "execute Gate B only if Gate A passes",
        "freeze Gate B result before Gate C",
    ]
    assert immutable["runtime_repair_during_initial_attempt"] is False
    assert immutable["selection_override"] is False
    assert immutable["product_or_version_substitution"] is False


def test_product11_and_motor_remain_closed() -> None:
    assertions = _freeze()["preregistration_assertions"]
    assert assertions["product11_reopen_or_retry_allowed"] is False
    assert assertions["motor_authorized"] is False
