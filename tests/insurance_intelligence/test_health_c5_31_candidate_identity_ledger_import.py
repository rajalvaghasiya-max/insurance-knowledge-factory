from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/c5_31_import_candidate_identity_ledger.py"


def load_module():
    spec = importlib.util.spec_from_file_location("c5_31_import_candidate_identity_ledger", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_c5_31_source_blob_and_commit_are_pinned() -> None:
    m = load_module()
    assert m.SOURCE_BLOB_SHA1 == "3c75e3e7197176094ab57e01b90ddb5c3684b741"
    assert m.SOURCE_COMMIT_SHA == "57ea79f6de127e88d1bab384bdb35e7b7bf780c6"


def test_c5_31_builds_exact_150_unique_governed_identities() -> None:
    m = load_module()
    ledger, manifest = m.build()
    assert ledger["candidate_count"] == 150
    keys = [(r["insurer_key"], r["uin"], r["product_name"]) for r in ledger["candidates"]]
    assert len(keys) == 150
    assert len(set(keys)) == 150
    assert manifest["candidate_count"] == 150


def test_c5_31_distribution_matches_frozen_enumeration() -> None:
    m = load_module()
    ledger, manifest = m.build()
    expected = {"cholamandalam": 77, "magma": 16, "navi": 35, "shriram": 22}
    assert ledger["target_counts"] == expected
    assert manifest["target_counts"] == expected


def test_c5_31_selector_unsafe_fields_are_excluded() -> None:
    m = load_module()
    ledger, _ = m.build()
    forbidden = {"document_url", "source_url", "raw_url", "copayment", "waiting_period"}
    assert forbidden.isdisjoint(set(ledger["candidate_fields"]))
    assert ledger["raw_urls_present"] is False
    assert ledger["target_concepts_present"] is False


def test_c5_31_hash_is_deterministic() -> None:
    m = load_module()
    _, first = m.build()
    _, second = m.build()
    assert first["ledger_sha256"] == second["ledger_sha256"]
    assert len(first["ledger_sha256"]) == 64


def test_c5_31_keeps_eligibility_and_product14_closed() -> None:
    m = load_module()
    ledger, manifest = m.build()
    assert ledger["eligibility_adjudication_started"] is False
    assert ledger["selection_started"] is False
    assert ledger["semantic_review_started"] is False
    assert ledger["target_clause_reads"] == 0
    assert manifest["product14_selection_authorized"] is False
    assert manifest["target_clause_reads_authorized"] is False
