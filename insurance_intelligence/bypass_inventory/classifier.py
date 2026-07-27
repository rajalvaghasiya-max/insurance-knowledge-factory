from __future__ import annotations

from insurance_intelligence.contracts.bypass_inventory import (
    BypassDisposition,
    BypassInventory,
    BypassInventoryEntry,
    BypassPathKind,
    BypassReachability,
    build_inventory,
)

STAR_COMPREHENSIVE_PILOT_ID = "star_health:star_comprehensive:conditional_copayment"


def _entry(
    *,
    path_id: str,
    repository_path: str,
    path_kind: BypassPathKind,
    recommendation_capable: bool,
    disposition: BypassDisposition,
    reachability: BypassReachability,
    rationale: str,
    evidence_refs: tuple[str, ...],
) -> BypassInventoryEntry:
    return BypassInventoryEntry(
        path_id=path_id,
        repository_path=repository_path,
        path_kind=path_kind,
        recommendation_capable=recommendation_capable,
        disposition=disposition,
        reachability=reachability,
        certified_pilots=(STAR_COMPREHENSIVE_PILOT_ID,),
        evidence_refs=evidence_refs,
        rationale=rationale,
    )


def build_default_bypass_inventory() -> BypassInventory:
    """Return the deterministic P2.6 inventory.

    The inventory classifies discovered recommendation-capable paths. It does not
    execute, import, delete, route, or modify any legacy path or static artifact.
    """

    entries = (
        _entry(
            path_id="governed_decision_safety_gate",
            repository_path="insurance_intelligence/decision/gate.py",
            path_kind=BypassPathKind.GOVERNED_CONTROL,
            recommendation_capable=False,
            disposition=BypassDisposition.ROUTED,
            reachability=BypassReachability.ACTIVE_GOVERNED,
            rationale="Certified response paths require a validated DecisionGateOutput before explanation or response assembly.",
            evidence_refs=(
                "insurance_intelligence/contracts/explanation.py",
                "insurance_intelligence/contracts/response.py",
                "tests/insurance_intelligence/test_decision_gate.py",
            ),
        ),
        _entry(
            path_id="legacy_recommendation_context_cli",
            repository_path="scripts/build_recommendation_context.py",
            path_kind=BypassPathKind.EXECUTABLE_UTILITY,
            recommendation_capable=True,
            disposition=BypassDisposition.EXPLICITLY_DEFERRED,
            reachability=BypassReachability.CERTIFIED_PILOT_UNREACHABLE,
            rationale="Standalone CLI utility; no certified Star pilot entry point imports or invokes this module.",
            evidence_refs=(
                "scripts/build_recommendation_context.py",
                "insurance_intelligence/orchestration/star_comprehensive_pilot.py",
                "scripts/run_certified_product_response_pilot.py",
            ),
        ),
        _entry(
            path_id="legacy_product_comparison_cli",
            repository_path="scripts/compare_products.py",
            path_kind=BypassPathKind.EXECUTABLE_UTILITY,
            recommendation_capable=True,
            disposition=BypassDisposition.EXPLICITLY_DEFERRED,
            reachability=BypassReachability.CERTIFIED_PILOT_UNREACHABLE,
            rationale="Standalone comparison CLI can emit recommendation-like output but is not reachable from the certified Star pilot.",
            evidence_refs=(
                "scripts/compare_products.py",
                "insurance_intelligence/orchestration/service.py",
                "scripts/run_intelligence_response.py",
            ),
        ),
        _entry(
            path_id="legacy_product_recommendation_cli",
            repository_path="scripts/recommend_products.py",
            path_kind=BypassPathKind.EXECUTABLE_UTILITY,
            recommendation_capable=True,
            disposition=BypassDisposition.EXPLICITLY_DEFERRED,
            reachability=BypassReachability.CERTIFIED_PILOT_UNREACHABLE,
            rationale="Standalone recommendation CLI remains test-covered but has no governed Star pilot caller.",
            evidence_refs=(
                "scripts/recommend_products.py",
                "tests/test_recommend_products.py",
                "insurance_intelligence/orchestration/star_comprehensive_pilot.py",
            ),
        ),
        _entry(
            path_id="legacy_comparison_artifact",
            repository_path="knowledge/health/comparisons/star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison.json",
            path_kind=BypassPathKind.STATIC_ARTIFACT,
            recommendation_capable=True,
            disposition=BypassDisposition.EXPLICITLY_DEFERRED,
            reachability=BypassReachability.STATIC_ARTIFACT_UNREACHABLE,
            rationale="Static historical comparison artifact exists but is not read by the certified Star runtime.",
            evidence_refs=(
                "knowledge/health/comparisons/star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison.json",
                "insurance_intelligence/orchestration/star_comprehensive_pilot.py",
            ),
        ),
        _entry(
            path_id="legacy_recommendation_artifact",
            repository_path="knowledge/health/recommendations/young_family__star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison_recommendation.json",
            path_kind=BypassPathKind.STATIC_ARTIFACT,
            recommendation_capable=True,
            disposition=BypassDisposition.EXPLICITLY_DEFERRED,
            reachability=BypassReachability.STATIC_ARTIFACT_UNREACHABLE,
            rationale="Static REVIEW_REQUIRED recommendation artifact is not consumed by the certified Star runtime.",
            evidence_refs=(
                "knowledge/health/recommendations/young_family__star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison_recommendation.json",
                "insurance_intelligence/orchestration/service.py",
            ),
        ),
        _entry(
            path_id="legacy_explanation_artifact",
            repository_path="knowledge/health/explanations/young_family__star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison_explanation.json",
            path_kind=BypassPathKind.STATIC_ARTIFACT,
            recommendation_capable=True,
            disposition=BypassDisposition.EXPLICITLY_DEFERRED,
            reachability=BypassReachability.STATIC_ARTIFACT_UNREACHABLE,
            rationale="Static explanation artifact carries recommendation status metadata but is not a certified response input.",
            evidence_refs=(
                "knowledge/health/explanations/young_family__star_health_star_comprehensive__vs__aditya_birla_health_activ_one_comparison_explanation.json",
                "insurance_intelligence/response/service.py",
            ),
        ),
        _entry(
            path_id="legacy_recommendation_unit_test",
            repository_path="tests/test_recommend_products.py",
            path_kind=BypassPathKind.TEST_PATH,
            recommendation_capable=False,
            disposition=BypassDisposition.EXPLICITLY_DEFERRED,
            reachability=BypassReachability.TEST_ONLY,
            rationale="Test-only caller exercises the standalone legacy recommendation utility and cannot produce certified pilot output.",
            evidence_refs=("tests/test_recommend_products.py",),
        ),
    )
    return build_inventory(
        inventory_id="policyscna-p2-6-recommendation-bypass-inventory",
        inventory_version="1.0.0",
        entries=entries,
    )
