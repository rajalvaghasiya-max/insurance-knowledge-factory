"""Focused tests for the Star Health Comprehensive governed foundation
package (MO-006B).

Star has no executable governed specifications yet -- the required
evidence (a real SHA-256 for any candidate source document, and
human-reviewed identity verification) does not exist anywhere in this
repository. These tests validate only what was actually produced this
order: an honest identity review packet and a non-executable draft
identity specification. They deliberately do not duplicate the real
contract classes' own validation logic -- they call the real,
unmodified ProductIdentityReference contract directly wherever a
contract-level assertion is needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from factory_core.governance.product_identity_reference import (
    ProductIdentityReference,
    ProductIdentityReferenceError,
)

REVIEW_PACKET_PATH = "docs/architecture/star_health_star_comprehensive_identity_review_packet.json"
DRAFT_IDENTITY_SPEC_PATH = "docs/architecture/star_health_star_comprehensive_product_identity_reference_spec.json"


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_identity_review_packet_does_not_claim_human_review():
    packet = _load(REVIEW_PACKET_PATH)
    assert packet["old_pipeline_identity_audit_result"]["is_human_review"] is False
    assert packet["status"] == "awaiting_human_identity_decision"
    assert "human_decision_required" in packet
    assert packet["human_decision_required"]


def test_identity_review_packet_uin_evidence_matches_source_citation():
    packet = _load(REVIEW_PACKET_PATH)
    uin = packet["uin_candidate"]
    assert uin["candidate_status"] == "format_valid_candidate"
    assert uin["exact_source_location"]["source_type"] == "prospectus"
    assert uin["exact_source_location"]["page_number"] == 2
    assert uin["value"] in uin["evidence_text"]


def test_identity_review_packet_discloses_missing_source_hash():
    packet = _load(REVIEW_PACKET_PATH)
    for document_type in ("policy_wording", "prospectus", "brochure"):
        entry = packet["source_url_and_provenance"][document_type]
        assert entry["sha256"] is None
        assert entry["sha256_available"] is False
    assert any("SHA-256" in item for item in packet["conflicts_or_uncertainty"])


def test_identity_review_packet_flags_uin_source_document_mismatch():
    """The UIN candidate was found in the prospectus, not the preferred
    policy_wording document -- the packet must disclose this explicitly
    rather than silently treating the two documents as interchangeable."""
    packet = _load(REVIEW_PACKET_PATH)
    assert any("prospectus" in item.lower() and "policy wording" in item.lower() for item in packet["conflicts_or_uncertainty"])


def test_draft_identity_specification_is_honest():
    draft = _load(DRAFT_IDENTITY_SPEC_PATH)
    assert draft["reviewed_by_human"] is False
    assert draft["identity_evidence"] == []
    assert draft["record_type"] != "product_identity_reference_v1"


def test_draft_identity_specification_fails_closed_against_real_contract():
    """The real, unmodified ProductIdentityReference contract must reject
    the Star draft outright -- proving no fabricated identity data could
    be silently accepted."""
    with pytest.raises(ProductIdentityReferenceError, match="record_type must be product_identity_reference_v1"):
        ProductIdentityReference().build_from_spec_file(
            spec_path=DRAFT_IDENTITY_SPEC_PATH, repository_root="."
        )


def test_no_premature_executable_star_specifications_exist():
    """Guard test: this order must not have authored resolved/executable
    generic_source_registration, document_classification,
    document_identity_resolution, or migration_manifest specifications
    for Star, since their required governed evidence (a real source
    SHA-256 and human identity approval) does not exist. Only the
    review packet and the non-executable draft identity spec should be
    present."""
    star_files = sorted(str(p) for p in Path("docs/architecture").glob("star_health_star_comprehensive_*"))
    assert star_files == sorted([
        DRAFT_IDENTITY_SPEC_PATH,
        REVIEW_PACKET_PATH,
    ])


def test_no_star_specific_runner_script_exists():
    """Star must execute, if and when it becomes ready, through the
    existing generic scripts/run_governed_product_migration.py -- never
    through a dedicated Star runner."""
    star_runners = list(Path("scripts").glob("run_star_*.py"))
    assert star_runners == [], f"unexpected Star-specific runner script(s): {star_runners}"
