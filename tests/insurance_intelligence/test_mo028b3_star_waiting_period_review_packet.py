from pathlib import Path

from scripts.render_star_waiting_period_review_packet import (
    OUTPUT_PATH,
    REGISTERED_SOURCE_PATH,
    _render,
)
from insurance_intelligence.benefits.waiting_period_evidence_audit import (
    EvidenceAuditStatus,
    audit_all_waiting_period_candidates,
    load_registered_source,
)


def test_registered_source_exists_and_all_waiting_periods_require_review() -> None:
    assert REGISTERED_SOURCE_PATH.is_file()
    results = audit_all_waiting_period_candidates(load_registered_source(REGISTERED_SOURCE_PATH))
    assert len(results) == 3
    assert all(item.status is EvidenceAuditStatus.REVIEW_REQUIRED for item in results)
    assert all(item.candidates for item in results)


def test_review_packet_is_explicitly_non_publication_and_fail_closed() -> None:
    rendered = _render()
    assert "evidence-review material only" in rendered
    assert "No candidate is approved, published, or available for runtime" in rendered
    assert "reviewer must identify the exact base exclusion clause" in rendered
    assert "NOT_AUTOMATED" in rendered


def test_review_packet_contains_all_three_exclusion_markers_and_candidate_hashes() -> None:
    rendered = _render()
    for marker in ("Code Excl 01", "Code Excl 02", "Code Excl 03"):
        assert marker in rendered
    results = audit_all_waiting_period_candidates(load_registered_source(REGISTERED_SOURCE_PATH))
    for result in results:
        for candidate in result.candidates:
            assert candidate.candidate_id in rendered
            assert str(candidate.source_page) in rendered
            assert candidate.text_sha256 in rendered
            assert candidate.excerpt.rstrip() in rendered


def test_committed_review_packet_matches_deterministic_renderer_when_present() -> None:
    if not OUTPUT_PATH.is_file():
        return
    assert OUTPUT_PATH.read_text(encoding="utf-8") == _render()
