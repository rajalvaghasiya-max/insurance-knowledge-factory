from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/architecture/health_c5_34_object_type_evidence_acquisition_contract_2026-08-26.json"


def load() -> dict:
    return json.loads(DOC.read_text(encoding="utf-8"))


def test_c5_34_is_bound_to_c5_33_merge_and_pending_population() -> None:
    doc = load()
    assert doc["base_merge_anchor"] == "c6896474bdbcde0fc178a75d5d6c18335528a05c"
    assert doc["predecessor_expected_state"] == {
        "candidate_count": 150,
        "ineligible_fail_closed": 19,
        "pending_evidence": 131,
        "target_clause_reads": 0,
        "product14_selection_authorized": False,
    }


def test_object_type_uses_structured_irdai_register_and_exact_uin_only() -> None:
    doc = load()
    assert doc["predicate_scope"] == "insurance_object_type"
    assert doc["required_value_for_eligibility"] == "MAIN_PRODUCT"
    assert doc["authoritative_source_class"] == "IRDAI_NON_LIFE_INSURANCE_PRODUCTS_STRUCTURED_REGISTER"
    basis = doc["evidence_basis"]
    assert basis["establishability"] == "REGULATOR_METADATA_ESTABLISHABLE"
    assert basis["structured_field"] == "Type Of Product"
    assert basis["join_key"] == "exact UIN"
    assert basis["uin_shape_is_not_evidence"] is True


def test_acquisition_is_exhaustive_and_does_not_stop_after_first_candidate() -> None:
    doc = load()
    scope = doc["acquisition_scope"]
    assert scope["candidate_population"] == "all 131 C5.33 PENDING_EVIDENCE candidates"
    assert scope["must_query_every_pending_candidate"] is True
    assert scope["stop_at_first_match_for_universe"] is False
    assert scope["exact_uin_match_required"] is True
    assert scope["product_name_only_match_forbidden"] is True


def test_c5_34_capture_excludes_semantics_and_target_fields() -> None:
    doc = load()
    capture = doc["capture_contract"]
    assert capture["one_record_per_pending_candidate"] is True
    assert capture["raw_semantic_document_content_allowed"] is False
    assert capture["target_semantic_fields_allowed"] is False
    assert capture["copayment_fields_allowed"] is False
    assert capture["waiting_period_fields_allowed"] is False


def test_c5_34_does_not_adjudicate_or_guess_object_type() -> None:
    doc = load()
    adjudication = doc["adjudication_not_authorized_in_c5_34"]
    assert adjudication["candidate_status_changes"] is False
    assert adjudication["main_product_pass_decisions"] is False
    assert adjudication["add_on_fail_decisions"] is False
    assert adjudication["unknown_fail_closed_decisions"] is False
    rules = " ".join(doc["fail_closed_acquisition_rules"]).casefold()
    assert "do not infer object type from product name" in rules
    assert "no_match remains unresolved" in rules


def test_product14_runtime_and_target_semantics_remain_closed() -> None:
    doc = load()
    anti = doc["anti_contamination"]
    assert anti["target_clause_reads"] == 0
    assert anti["semantic_review_started"] is False
    assert anti["runtime_changed"] is False
    assert anti["projection_changed"] is False
    assert doc["product14_selection_authorized"] is False
    assert doc["target_clause_reads_authorized"] is False
    assert doc["runtime_change_authorized"] is False
    assert doc["motor_authorized"] is False
