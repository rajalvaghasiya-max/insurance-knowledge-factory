from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLOSURE = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_waiting_period_option_domain_certification_closure_2026-08-22.json"


def _closure() -> dict:
    return json.loads(CLOSURE.read_text(encoding="utf-8"))


def test_ped_and_specific_disease_option_domains_are_certified_without_scalar_resolution() -> None:
    record = _closure()
    cases = {item["waiting_period_type"]: item for item in record["certified_option_domains"]}
    assert set(cases) == {"PRE_EXISTING_DISEASE", "SPECIFIC_DISEASE_PROCEDURE"}
    for item in cases.values():
        assert item["outcome"] == "PASS"
        assert item["completeness"] == "COMPLETE"
        assert item["explanation_permitted"] is True
        assert item["options"] == ["1 YEARS", "2 YEARS", "3 YEARS"]
        assert item["selected_duration_resolved"] is False


def test_closure_preserves_exact_dual_evidence_identity() -> None:
    evidence = _closure()["evidence_identity"]
    assert evidence["mechanism"] == {
        "candidate_id": "candidate_page_20",
        "source_page": 20,
        "candidate_text_sha256": "5261b13c20af365078c7ec1a4b43e742fd1890257a57fa5858d6314eff87aef2",
    }
    assert evidence["option_domain"] == {
        "candidate_id": "candidate_page_53",
        "source_page": 53,
        "candidate_text_sha256": "b362111414b124bbcc62cd3b33d0eafe7d01b5f9305fa079cdd156ee92b8cc40",
    }


def test_only_maternity_and_baby_care_remain_unresolved_for_this_milestone() -> None:
    record = _closure()
    assert record["remaining_waiting_period_families"] == ["MATERNITY", "BABY_CARE"]
    registry = record["coverage_registry"]
    assert registry["waiting_period_concept_status"] == "PARTIAL"
    assert registry["comparison_ready"] is False
    assert registry["decision_support_ready"] is False
