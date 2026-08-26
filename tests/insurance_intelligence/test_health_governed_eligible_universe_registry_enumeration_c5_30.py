from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "docs/architecture/health_governed_eligible_universe_registry_enumeration_c5_30_2026-08-26.json"


def load() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_c5_30_freezes_clean_terminal_page_proof() -> None:
    doc = load()
    op = doc["operator_validation"]
    assert op["pages_scanned"] == 31
    assert op["terminal_page"] == 31
    assert op["terminal_page_row_count"] == 20
    assert op["requested_page_delta"] == 60
    assert op["terminal_reason"] == "ROW_COUNT_BELOW_REQUESTED_DELTA"


def test_c5_30_page_audit_is_contiguous_and_terminal_only_on_last_page() -> None:
    audit = load()["page_audit"]
    assert [row["cur"] for row in audit] == list(range(1, 32))
    assert all(row["row_count"] == 60 for row in audit[:-1])
    assert audit[-1]["row_count"] == 20
    assert len({row["sha256"] for row in audit}) == 31


def test_c5_30_stable_counts_total_150() -> None:
    doc = load()
    assert doc["frozen_target_counts"] == {
        "cholamandalam": 77,
        "magma": 16,
        "navi": 35,
        "shriram": 22,
    }
    assert sum(doc["frozen_target_counts"].values()) == 150
    assert doc["candidate_count"] == 150


def test_c5_30_does_not_overclaim_candidate_identity_ledger() -> None:
    doc = load()
    assert doc["candidate_identity_ledger_frozen"] is False
    assert doc["next_authorized_action"] == "IMPORT_AND_HASH_COMPLETE_150_CANDIDATE_IDENTITY_LEDGER_FROM_CLEAN_C5_30_OUTPUT_ONLY"


def test_c5_30_keeps_product14_and_semantics_closed() -> None:
    doc = load()
    assert doc["eligibility_adjudication_started"] is False
    assert doc["selection_started"] is False
    assert doc["semantic_review_started"] is False
    assert doc["target_clause_reads"] == 0
    assert doc["product14_selection_authorized"] is False
