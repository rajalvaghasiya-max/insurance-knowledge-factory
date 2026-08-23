import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "docs/architecture/hdfc_ergo_optima_secure_v8_copayment_nonapplication_binding_spec.json"


def test_hdfc_nonapplication_spec_binds_only_operational_page_44_clause() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert spec["binding_type"] == "copayment_nonapplication_binding_v1"
    assert spec["reviewed_by_human"] is True
    assert len(spec["rules"]) == 1

    rule = spec["rules"][0]
    selection = rule["evidence_selections"][0]
    assert selection == {
        "document_id": "hdfc_ergo_optima_secure_policy_wording_v8",
        "candidate_id": "candidate_page_44",
        "candidate_text_sha256": "66157d6b8ae478e7e46d0d40f19d00a87db7f949e14197b56bf08a5cf8cce743",
    }
    assert "No co-payment shall apply" in rule["reviewed_statement"]
    assert "0%" not in rule["reviewed_statement"]


def test_hdfc_definition_only_page_3_is_recorded_but_not_selected() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    governance = spec["governance"]
    assert governance["definition_only_candidate_page_3_selected"] is False
    assert governance["definition_only_candidate_page_3_sha256"] == (
        "f8aeeccd32b501fc93b2bc699fcd04d43f239a1e40aacc8475c7152ea3f1d0e1"
    )
    selected_ids = {
        selection["candidate_id"]
        for rule in spec["rules"]
        for selection in rule["evidence_selections"]
    }
    assert "candidate_page_3" not in selected_ids


def test_hdfc_nonapplication_spec_preserves_fail_closed_governance() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    governance = spec["governance"]
    assert governance["zero_percent_obligation_manufacturing_authorized"] is False
    assert governance["publication_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False
    assert governance["claim_payment_inference_authorized"] is False
