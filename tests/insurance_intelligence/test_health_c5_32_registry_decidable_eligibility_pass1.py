from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/c5_32_health_eligibility_certification_pass1.py"
OUT = ROOT / "docs/architecture/health_c5_32_registry_decidable_eligibility_pass1.json"
EXPECTED_SHA = "cec7620abde012982844beb212892db13cdf509177fc4d5fae9145d752f8a0a2"


def generate() -> dict:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(OUT.read_text(encoding="utf-8"))


def test_pass1_is_bound_to_frozen_c5_31_ledger_hash() -> None:
    doc = generate()
    assert doc["source_ledger_sha256"] == EXPECTED_SHA
    assert doc["candidate_count"] == 150
    assert doc["all_150_processed"] is True


def test_pass1_preserves_frozen_insurer_distribution() -> None:
    doc = generate()
    assert doc["insurer_counts"] == {
        "cholamandalam": 77,
        "magma": 16,
        "navi": 35,
        "shriram": 22,
    }


def test_explicit_group_rows_fail_only_coverage_arrangement() -> None:
    doc = generate()
    groups = [r for r in doc["adjudications"] if r["registry_type_of_product"].casefold() == "group"]
    assert groups
    for row in groups:
        assert row["status"] == "INELIGIBLE_FAIL_CLOSED"
        assert row["decisive_predicate"] == "coverage_arrangement"
        coverage = next(a for a in row["predicate_attestations"] if a["predicate_id"] == "coverage_arrangement")
        assert coverage["normalized_value"] == "GROUP"
        assert coverage["certification_decision"] == "FAIL"


def test_non_group_rows_are_not_guessed_eligible() -> None:
    doc = generate()
    nongroups = [r for r in doc["adjudications"] if r["registry_type_of_product"].casefold() != "group"]
    assert nongroups
    assert all(r["status"] == "PENDING_EVIDENCE" for r in nongroups)
    assert doc["eligible_candidate_count"] is None
    assert doc["final_universe_frozen"] is False


def test_pass1_does_not_infer_target_or_non_target_semantics_from_names() -> None:
    doc = generate()
    forbidden = " ".join(doc["decision_policy"]["forbidden_inferences"]).casefold()
    assert "benefit basis" in forbidden
    assert "product name" in forbidden
    assert "copayment" in forbidden
    assert "waiting-period" in forbidden


def test_product14_and_semantics_remain_closed() -> None:
    doc = generate()
    assert doc["product14_selection_authorized"] is False
    assert doc["selection_started"] is False
    assert doc["semantic_review_started"] is False
    assert doc["target_clause_reads"] == 0
    assert doc["next_step"] == "RESOLVE_PENDING_NON_TARGET_PREDICATES_WITH_GOVERNED_EVIDENCE_ONLY"
