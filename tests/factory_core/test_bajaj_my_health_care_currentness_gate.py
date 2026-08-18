from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = (
    REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "bajaj_my_health_care_currentness_gate_2026-08-18.json"
)


def test_bajaj_currentness_gate_is_compatible_and_resumable() -> None:
    gate = json.loads(GATE_PATH.read_text(encoding="utf-8"))

    assert set(gate) == {"status", "evidence", "blocker", "resume_condition"}
    assert gate["status"] == "COMPATIBLE"

    evidence = gate["evidence"]
    assert evidence["product_name"] == "My Health Care Plan (Plan 1)"
    assert evidence["uin"] == "BAJHLIP26074V022526"
    assert evidence["document_type"] == "policy_wording"
    assert evidence["official_document_index"].startswith("https://www.bajajgeneralinsurance.com/")
    assert evidence["official_policy_wording"].endswith("My-Health-Care-Plan1-PW.pdf")
    assert evidence["observed_at"] == "2026-08-18"

    # Currentness compatibility is deliberately not equivalent to governed-artifact registration.
    assert "byte-compared" in gate["blocker"]
    assert "registry-backed" in gate["blocker"]
    assert "Capture the current policy-wording artifact" in gate["resume_condition"]
