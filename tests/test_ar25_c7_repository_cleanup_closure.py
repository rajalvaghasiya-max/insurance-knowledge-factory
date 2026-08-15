from pathlib import Path

from scripts.audit_historical_intelligence_artifacts import audit as audit_historical_artifacts
from scripts.audit_repository_cleanup_candidates import audit as audit_cleanup_candidates


REPO_ROOT = Path(".")
EXPECTED_FIREWALL_FIXTURES = {
    "knowledge/health/comparisons/star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison.json",
    "knowledge/health/recommendations/young_family__star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison_recommendation.json",
    "knowledge/health/explanations/young_family__star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison_explanation.json",
}


def test_repository_cleanup_audit_has_no_remaining_candidates() -> None:
    assert audit_cleanup_candidates(REPO_ROOT) == ()


def test_historical_intelligence_outputs_are_fully_dispositioned() -> None:
    findings = audit_historical_artifacts(REPO_ROOT)
    assert {item.path for item in findings} == EXPECTED_FIREWALL_FIXTURES
    assert all(item.disposition == "RETAIN_FIREWALL_FIXTURE" for item in findings)


def test_cleanup_governance_records_cover_c1_through_c6() -> None:
    required = (
        "docs/architecture/ACTIVE_AND_HISTORICAL_ARCHITECTURE_CLASSIFICATION.md",
        "docs/architecture/AR_2_5_C3_FIRST_PHYSICAL_CLEANUP.md",
        "docs/architecture/AR_2_5_C4_LEGACY_RUNTIME_FIREWALL.md",
        "docs/architecture/AR_2_5_C5_KNOWLEDGE_DOMAINS_SUCCESSION_FIREWALL.md",
        "docs/architecture/AR_2_5_C6_HISTORICAL_ARTIFACT_DISPOSITION.md",
    )
    missing = tuple(path for path in required if not Path(path).is_file())
    assert missing == ()
