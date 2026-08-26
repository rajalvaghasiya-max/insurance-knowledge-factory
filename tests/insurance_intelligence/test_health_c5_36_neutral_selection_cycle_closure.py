from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "evidence/c5_35_object_type_capture.txt"
C5_35 = ROOT / "docs/architecture/health_c5_35_object_type_evidence_path_result_2026-08-26.json"
C5_36 = ROOT / "docs/architecture/health_c5_36_neutral_selection_cycle_closure_2026-08-26.json"
EXPECTED_EVIDENCE_BLOB_SHA1 = "f592e9570c288d0f984a7257fec0c16049d35bff"


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def load_capture() -> dict:
    text = EVIDENCE.read_text(encoding="utf-8")
    begin = "C5_35_OBJECT_TYPE_CAPTURE_BEGIN\n"
    end = "\nC5_35_OBJECT_TYPE_CAPTURE_END"
    assert begin in text and end in text
    return json.loads(text.split(begin, 1)[1].split(end, 1)[0])


def test_c5_35_evidence_is_exact_preserved_blob() -> None:
    assert git_blob_sha1(EVIDENCE) == EXPECTED_EVIDENCE_BLOB_SHA1
    result = json.loads(C5_35.read_text(encoding="utf-8"))
    assert result["source_evidence"]["source_blob_sha1"] == EXPECTED_EVIDENCE_BLOB_SHA1
    assert result["source_evidence"]["preservation_method"] == "EXACT_GIT_BLOB_IDENTITY_COPY"


def test_c5_35_capture_proves_zero_of_131_exact_uin_matches() -> None:
    capture = load_capture()
    assert capture["candidate_count"] == 131
    assert capture["all_131_processed"] is True
    assert capture["query_status_counts"] == {"NO_MATCH": 131}
    assert capture["exact_match_type_counts"] == {}


def test_c5_35_capture_preserves_preselection_integrity() -> None:
    capture = load_capture()
    assert capture["candidate_status_changes"] == 0
    assert capture["adjudication_started"] is False
    assert capture["selection_started"] is False
    assert capture["semantic_review_started"] is False
    assert capture["target_clause_reads"] == 0


def test_c5_36_ceiling_claim_is_scoped_not_universal() -> None:
    closure = json.loads(C5_36.read_text(encoding="utf-8"))
    assert closure["decision"] == "STRICT_BLIND_SELECTION_PREDICATE_EVIDENCE_CEILING_REACHED"
    scope = closure["decision_scope"]
    assert "frozen Product #14 candidate universe" in scope
    assert "not a universal impossibility claim" in scope


def test_c5_36_forbids_selector_and_external_certifier_semantic_relaxation() -> None:
    closure = json.loads(C5_36.read_text(encoding="utf-8"))
    boundaries = closure["contamination_boundaries"]
    assert boundaries["selector_semantic_content_access_is_not_a_permissible_relaxation"] is True
    assert boundaries["external_certification_may_not_establish_eligibility_from_target_semantic_content"] is True
    assert boundaries["target_adjacent_coverage_description_may_not_be_used_to_classify_object_type"] is True
    assert boundaries["moving_semantic_content_review_outside_selector_does_not_remove_contamination"] is True


def test_c5_36_closes_product14_and_neutral_selection_cycle() -> None:
    closure = json.loads(C5_36.read_text(encoding="utf-8"))
    assert closure["product14"]["status"] == "NOT_STARTED_NOT_SCORED"
    assert closure["product14"]["selection_started"] is False
    assert closure["product14"]["target_clause_reads"] == 0
    assert closure["product15_automatic_authorization"] is False
    assert closure["additional_object_type_source_hunt_authorized"] is False
    assert closure["neutral_selection_hardening_cycle_closed"] is True
    assert closure["next_program_boundary"] == "RETURN_TO_INSURANCE_INTELLIGENCE_ROADMAP_ASSERTION_ADVISORY_BOUNDARY"
