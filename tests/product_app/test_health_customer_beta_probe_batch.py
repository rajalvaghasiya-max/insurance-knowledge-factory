from __future__ import annotations

from collections import Counter
from pathlib import Path

from scripts.run_health_customer_v0_beta_probe import DEFAULT_MANIFEST, _load_manifest

ROOT = Path(__file__).resolve().parents[2]


def test_beta_probe_batch_01_shape_and_scope() -> None:
    manifest, conversations = _load_manifest(ROOT / DEFAULT_MANIFEST)

    assert manifest["evidence_role"] == "BETA_DIAGNOSTIC_ONLY"
    assert manifest["holdout_eligible"] is False
    assert manifest["case_count"] == 10
    assert manifest["conversation_count"] == 5
    assert len(conversations) == 5

    cases = [case for conversation in conversations for case in conversation["cases"]]
    assert len(cases) == 10
    assert all(len(conversation["cases"]) == 2 for conversation in conversations)
    assert all(conversation["cases"][1]["prior_context_required"] is True for conversation in conversations)

    counts = Counter(case["concept_area"] for case in cases)
    assert counts == {
        "waiting_period": 2,
        "restoration": 2,
        "room_rent_limit": 2,
        "bariatric_surgery": 2,
        "copayment": 2,
    }

    assert all(case["case_id"].startswith("beta01-") for case in cases)
    assert all("reference" not in case for case in cases)
