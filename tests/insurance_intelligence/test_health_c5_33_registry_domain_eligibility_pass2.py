from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/c5_33_health_eligibility_certification_pass2.py"
OUT = ROOT / "docs/architecture/health_c5_33_registry_domain_eligibility_pass2.json"
EXPECTED_PASS1_BLOB = "44c3614993da168e4808b2f603527f55c0b3d43e"
EXPECTED_LEDGER_SHA256 = "cec7620abde012982844beb212892db13cdf509177fc4d5fae9145d752f8a0a2"


def generate() -> dict:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(OUT.read_text(encoding="utf-8"))


def test_pass2_is_bound_to_frozen_pass1_and_ledger() -> None:
    doc = generate()
    assert doc["source_pass1_git_blob_sha1"] == EXPECTED_PASS1_BLOB
    assert doc["source_ledger_sha256"] == EXPECTED_LEDGER_SHA256
    assert doc["candidate_count"] == 150
    assert doc["all_150_processed"] is True


def test_domain_is_established_for_every_candidate_from_health_register_provenance() -> None:
    doc = generate()
    for row in doc["adjudications"]:
        domain = next(a for a in row["predicate_attestations"] if a["predicate_id"] == "domain")
        assert domain["normalized_value"] == "HEALTH"
        assert domain["certification_decision"] == "PASS"
        assert domain["ambiguity_conflict_status"] == "NONE"
        assert domain["authority_scope"] == "IRDAI_STRUCTURED_HEALTH_PRODUCT_REGISTER"


def test_pass2_preserves_pass1_candidate_outcomes() -> None:
    doc = generate()
    assert doc["status_counts"] == {
        "INELIGIBLE_FAIL_CLOSED": 19,
        "PENDING_EVIDENCE": 131,
    }
    assert doc["pending_candidate_count"] == 131
    assert doc["eligible_candidate_count"] is None
    assert doc["final_universe_frozen"] is False


def test_non_archived_is_not_promoted_to_currently_offered() -> None:
    doc = generate()
    assert "Non-Archived" in doc["decision_policy"]["current_offering_rule"]
    pending = [row for row in doc["adjudications"] if row["status"] == "PENDING_EVIDENCE"]
    assert pending
    for row in pending:
        current = next(a for a in row["predicate_attestations"] if a["predicate_id"] == "current_offering")
        assert current["normalized_value"] == "UNKNOWN"
        assert current["certification_decision"] == "PENDING_EVIDENCE"


def test_pass2_does_not_overreach_other_unresolved_predicates() -> None:
    doc = generate()
    assert doc["resolved_in_this_pass"] == ["domain"]
    assert set(doc["explicitly_not_resolved_in_this_pass"]) == {
        "benefit_basis",
        "insurance_object_type",
        "current_offering",
    }
    pending = [row for row in doc["adjudications"] if row["status"] == "PENDING_EVIDENCE"]
    for row in pending:
        by_id = {a["predicate_id"]: a for a in row["predicate_attestations"]}
        for predicate_id in ("benefit_basis", "insurance_object_type", "current_offering"):
            assert by_id[predicate_id]["certification_decision"] == "PENDING_EVIDENCE"


def test_product14_and_target_semantics_remain_closed() -> None:
    doc = generate()
    assert doc["product14_selection_authorized"] is False
    assert doc["selection_started"] is False
    assert doc["semantic_review_started"] is False
    assert doc["target_clause_reads"] == 0
    assert doc["next_step"] == "RESOLVE_REMAINING_PENDING_NON_TARGET_PREDICATES_WITH_GOVERNED_EVIDENCE_ONLY"
