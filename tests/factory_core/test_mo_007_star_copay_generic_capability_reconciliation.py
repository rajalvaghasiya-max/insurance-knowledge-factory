"""Report-integrity tests for MO-007 (Star copay generic capability
reconciliation), amended after the authoritative artifact bundle was
supplied and reviewed. These validate the machine-readable report's
internal consistency and honesty -- they do not test any Star copay
production logic, since none has been approved, executed, or created."""
from __future__ import annotations

import json
from pathlib import Path

REPORT_PATH = "docs/architecture/mo_007_star_copay_generic_capability_reconciliation.json"

_APPROVED_DISPOSITIONS = {
    "REUSE_AS_IS",
    "REUSE_WITH_NORMALIZATION",
    "SUPERSEDED",
    "INVALID_GOVERNED_DATA",
    "FUTURE_STAGE_ONLY",
}
_REQUIRED_ARTIFACTS = {
    "docs/architecture/star_health_star_comprehensive_conditional_copayment_binding_spec.json",
    "docs/architecture/star_health_star_comprehensive_conditional_copayment_canonical_projection_spec.json",
    "docs/architecture/star_health_star_comprehensive_conditional_copayment_publication_decision_spec.json",
    "docs/architecture/star_health_star_comprehensive_conditional_copayment_authoritative_publication_spec.json",
    "examples/star_health_star_comprehensive_conditional_copayment_binding_spec.json",
    "examples/star_health_star_comprehensive_conditional_copayment_canonical_projection_spec.json",
    "examples/star_health_star_comprehensive_conditional_copayment_publication_decision_spec.json",
    "examples/star_health_star_comprehensive_conditional_copayment_authoritative_publication_spec.json",
    "docs/architecture/P2_7_A_STAR_COMPREHENSIVE_SOURCE_REGISTRATION_AND_CLASSIFICATION.md",
    "docs/architecture/P2_7_B_IMPLEMENTATION.md",
    "docs/architecture/P2_7_C_GENERIC_LEGAL_CONDITION_BINDING_EXTENSION.md",
    "docs/architecture/P2_7_D_STAR_COMPREHENSIVE_CANONICAL_PROJECTION.md",
    "docs/architecture/P2_7_E_STAR_COMPREHENSIVE_PUBLICATION_ELIGIBILITY.md",
}
_REQUIRED_CAPABILITIES = {
    "fixed_percentage_financial_effect",
    "numeric_threshold_condition",
    "age_at_entry_semantic",
    "continuous_renewal_exception",
    "policy_section_applicability_scope",
    "multiple_applicable_sections",
    "exception_overriding_primary_trigger",
    "evidence_lineage",
    "product_identity_binding",
    "document_identity_binding",
    "compatibility_unverified_temporal_state",
    "blocked_current_entitlement_publication",
}
_APPROVED_CAPABILITY_ASSESSMENTS = {
    "SUPPORTED",
    "SUPPORTED_WITH_EXISTING_CONFIGURATION",
    "GENERIC_CAPABILITY_GAP",
    "NOT_YET_EVALUATED",
}


def _load_report() -> dict:
    return json.loads(Path(REPORT_PATH).read_text(encoding="utf-8"))


def test_all_13_artifacts_received_a_disposition():
    report = _load_report()
    reviewed = {item["artifact"] for item in report["artifact_reviews"]}
    missing = _REQUIRED_ARTIFACTS - reviewed
    assert missing == set(), f"artifacts with no disposition recorded: {missing}"
    assert len(report["artifact_reviews"]) == 13


def test_only_approved_disposition_values_are_used():
    report = _load_report()
    for item in report["artifact_reviews"]:
        assert item["disposition"] in _APPROVED_DISPOSITIONS, (
            f"{item['artifact']} uses an unapproved disposition: {item['disposition']}"
        )


def test_not_reviewable_absent_disposition_is_no_longer_used():
    """The amendment requires real dispositions now that the authoritative
    bundle has been supplied -- NOT_REVIEWABLE_ARTIFACT_ABSENT must not
    appear anywhere in the amended report."""
    report_text = Path(REPORT_PATH).read_text(encoding="utf-8")
    assert "NOT_REVIEWABLE_ARTIFACT_ABSENT" not in report_text


def test_each_artifact_review_has_required_fields():
    required_fields = {
        "artifact",
        "disposition",
        "reason",
        "contract_validity",
        "source_lineage_status",
        "identity_consistency",
        "source_sha_consistency",
        "rule_completeness",
        "exception_completeness",
        "scope_completeness",
        "temporal_governance_status",
        "publication_boundary_status",
        "recommended_action",
    }
    report = _load_report()
    for item in report["artifact_reviews"]:
        missing = required_fields - set(item.keys())
        assert missing == set(), f"{item['artifact']} missing fields: {missing}"


def test_duplicate_authority_has_been_addressed():
    report = _load_report()
    duplicate_review = report["duplicate_authority_review"]
    assert duplicate_review["result"] == "byte_identical_duplicates_all_four_pairs"
    assert duplicate_review["authoritative_location"] == "docs/architecture/"
    assert "examples/" in duplicate_review["action_taken"]
    example_dispositions = {
        item["disposition"] for item in report["artifact_reviews"] if item["artifact"].startswith("examples/")
    }
    assert example_dispositions == {"SUPERSEDED"}


def test_all_required_generic_capabilities_received_an_assessment():
    report = _load_report()
    assessed = {item["capability"] for item in report["capability_assessment"]}
    missing = _REQUIRED_CAPABILITIES - assessed
    assert missing == set(), f"capabilities with no assessment recorded: {missing}"


def test_only_approved_capability_assessment_values_are_used():
    report = _load_report()
    for item in report["capability_assessment"]:
        assert item["assessment"] in _APPROVED_CAPABILITY_ASSESSMENTS, (
            f"{item['capability']} uses an unapproved assessment value: {item['assessment']}"
        )


def test_no_unsupported_current_entitlement_approval_is_recorded():
    """The report must never claim current-entitlement publication is
    anything other than blocked for Star, and the one artifact that
    could eventually set publication_status=authoritative must be
    explicitly marked as not executed in this order."""
    report = _load_report()
    assert report["publication_boundary_findings"]["current_entitlement_publication_eligibility"] == "blocked"
    report_text = Path(REPORT_PATH).read_text(encoding="utf-8")
    assert '"current_entitlement_publication_eligibility": "eligible"' not in report_text

    authoritative_publication_item = next(
        item for item in report["artifact_reviews"]
        if item["artifact"] == "docs/architecture/star_health_star_comprehensive_conditional_copayment_authoritative_publication_spec.json"
    )
    assert authoritative_publication_item["disposition"] == "FUTURE_STAGE_ONLY"
    assert "not_executed" in authoritative_publication_item["publication_boundary_status"]


def test_approved_star_identity_and_sha256_remain_unchanged():
    manifest = json.loads(
        Path("docs/architecture/star_health_star_comprehensive_migration_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["entity_id"] == "star_health:star_comprehensive"
    assert manifest["expected_source_sha256"] == "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"


def test_report_status_is_complete_and_no_gaps_recorded():
    report = _load_report()
    assert report["overall_status"] == "COMPLETE"
    assert report["generic_capability_gaps"] == []


def test_any_declared_generic_gap_contains_evidence():
    report = _load_report()
    for gap in report["generic_capability_gaps"]:
        assert isinstance(gap, dict)
        assert gap.get("evidence"), f"gap entry missing evidence: {gap}"


def test_production_specialization_findings_are_classified():
    report = _load_report()
    allowed_classifications = {
        "governed_data",
        "documentation",
        "test_fixture",
        "generic_test_case",
        "prohibited_product_specific_production_logic",
    }
    assert report["production_specialization_findings"], "expected at least one production-code search finding"
    for finding in report["production_specialization_findings"]:
        assert finding["classification"] in allowed_classifications
        assert finding["file"]
        assert isinstance(finding["line"], int)


def test_normalization_required_artifacts_do_not_claim_contract_success():
    """Artifacts flagged REUSE_WITH_NORMALIZATION must not simultaneously
    claim their contract already validates successfully -- that would
    contradict the normalization requirement."""
    report = _load_report()
    for item in report["artifact_reviews"]:
        if item["disposition"] == "REUSE_WITH_NORMALIZATION":
            assert "fails closed" in item["contract_validity"].lower() or "depends" in item["contract_validity"].lower()
