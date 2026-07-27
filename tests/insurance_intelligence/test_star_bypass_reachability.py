from pathlib import Path

from insurance_intelligence.bypass_inventory import (
    STAR_COMPREHENSIVE_PILOT_ID,
    build_default_bypass_inventory,
)
from insurance_intelligence.contracts.bypass_inventory import (
    BypassDisposition,
    BypassPathKind,
    BypassReachability,
)


PILOT_RUNTIME_PATHS = (
    Path("insurance_intelligence/orchestration/star_comprehensive_pilot.py"),
    Path("insurance_intelligence/orchestration/service.py"),
    Path("scripts/run_certified_product_response_pilot.py"),
    Path("scripts/run_full_knowledge_to_explanation_certification.py"),
    Path("scripts/run_intelligence_response.py"),
)

LEGACY_RUNTIME_TOKENS = (
    "recommend_products",
    "build_recommendation_context",
    "compare_products",
    "knowledge/health/recommendations",
    "knowledge\\health\\recommendations",
    "knowledge/health/comparisons",
    "knowledge\\health\\comparisons",
    "knowledge/health/explanations",
    "knowledge\\health\\explanations",
)


def test_certified_star_runtime_does_not_reference_legacy_paths():
    for path in PILOT_RUNTIME_PATHS:
        text = path.read_text(encoding="utf-8").lower()
        assert not any(token.lower() in text for token in LEGACY_RUNTIME_TOKENS), path


def test_every_recommendation_capable_star_entry_has_safe_disposition():
    inventory = build_default_bypass_inventory()
    entries = [
        item
        for item in inventory.for_pilot(STAR_COMPREHENSIVE_PILOT_ID)
        if item.recommendation_capable
    ]
    assert entries
    assert all(
        item.disposition in {
            BypassDisposition.ROUTED,
            BypassDisposition.BLOCKED,
            BypassDisposition.EXPLICITLY_DEFERRED,
            BypassDisposition.REMOVED,
        }
        for item in entries
    )
    assert all(item.reachability is not BypassReachability.ACTIVE_UNGOVERNED for item in entries)


def test_legacy_executable_utilities_are_explicitly_deferred_and_unreachable():
    inventory = build_default_bypass_inventory()
    entries = [
        item for item in inventory.entries
        if item.path_kind is BypassPathKind.EXECUTABLE_UTILITY
    ]
    assert {item.repository_path for item in entries} == {
        "scripts/build_recommendation_context.py",
        "scripts/compare_products.py",
        "scripts/recommend_products.py",
    }
    assert all(item.disposition is BypassDisposition.EXPLICITLY_DEFERRED for item in entries)
    assert all(item.reachability is BypassReachability.CERTIFIED_PILOT_UNREACHABLE for item in entries)


def test_static_recommendation_artifacts_are_not_certified_inputs():
    inventory = build_default_bypass_inventory()
    entries = [
        item for item in inventory.entries
        if item.path_kind is BypassPathKind.STATIC_ARTIFACT
    ]
    assert entries
    assert all(item.disposition is BypassDisposition.EXPLICITLY_DEFERRED for item in entries)
    assert all(item.reachability is BypassReachability.STATIC_ARTIFACT_UNREACHABLE for item in entries)
    certified_runtime_text = "\n".join(
        path.read_text(encoding="utf-8") for path in PILOT_RUNTIME_PATHS
    )
    assert all(item.repository_path not in certified_runtime_text for item in entries)


def test_governed_decision_gate_is_the_active_certified_control():
    inventory = build_default_bypass_inventory()
    controls = [
        item for item in inventory.entries
        if item.path_kind is BypassPathKind.GOVERNED_CONTROL
    ]
    assert len(controls) == 1
    assert controls[0].repository_path == "insurance_intelligence/decision/gate.py"
    assert controls[0].disposition is BypassDisposition.ROUTED
    assert controls[0].reachability is BypassReachability.ACTIVE_GOVERNED
