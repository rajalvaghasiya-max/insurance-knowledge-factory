from __future__ import annotations

import copy

import pytest

from factory_core.governance.review_risk_routing import (
    ReviewRiskRoutingContract,
    ReviewRiskRoutingError,
)


SHA = "a" * 64


def _document(flags_by_group: list[list[str]]) -> dict:
    groups = []
    for index, flags in enumerate(flags_by_group, start=1):
        groups.append({
            "group_id": f"group_{index}",
            "review_flags": flags,
        })
    return {
        "schema_version": "1.0",
        "review_type": "health_currency_candidate_review_document_v1",
        "review_layer": "currency_candidate_review",
        "review_group_count": len(groups),
        "source": {"sha256": SHA, "entity_id": "example:product"},
        "review_groups": groups,
    }


def test_routes_transparent_risk_tiers_without_adjudication():
    result = ReviewRiskRoutingContract.route(_document([
        ["role_selection_required"],
        ["role_selection_required", "repeated_same_amount"],
        ["role_selection_required", "benefit_scope_unresolved"],
        ["role_selection_required", "conflicting_role_hints"],
    ])).manifest

    assert [row["risk_tier"] for row in result["routing_records"]] == [
        "low", "medium", "high", "critical"
    ]
    assert [row["review_route"] for row in result["routing_records"]] == [
        "light_review", "standard_review", "senior_review", "dual_or_senior_review"
    ]
    assert all(row["adjudication_status"] == "not_adjudicated" for row in result["routing_records"])
    assert all(row["publication_state"] == "not_published" for row in result["routing_records"])


def test_workload_summary_counts_tiers_and_routes():
    result = ReviewRiskRoutingContract.route(_document([
        ["role_selection_required"],
        ["role_selection_required"],
        ["role_selection_required", "table_layout_binding_possible"],
    ])).manifest
    assert result["workload_summary"]["tier_counts"] == {
        "critical": 0, "high": 1, "medium": 0, "low": 2
    }
    assert result["workload_summary"]["route_counts"]["light_review"] == 2
    assert result["workload_summary"]["route_counts"]["senior_review"] == 1


def test_critical_signal_dominates_lower_risk_flags():
    result = ReviewRiskRoutingContract.route(_document([[
        "role_selection_required",
        "repeated_same_amount",
        "benefit_scope_unresolved",
        "possible_benefit_limit_despite_role_hint",
    ]])).manifest
    row = result["routing_records"][0]
    assert row["risk_tier"] == "critical"
    assert row["risk_reasons"] == ["possible_benefit_limit_despite_role_hint"]


def test_unknown_review_flag_fails_closed():
    with pytest.raises(ReviewRiskRoutingError, match="unknown review flag"):
        ReviewRiskRoutingContract.route(_document([[
            "role_selection_required", "new_unreviewed_semantic_risk"
        ]]))


def test_routing_is_deterministic_and_source_bound():
    first = ReviewRiskRoutingContract.route(_document([[
        "role_selection_required", "repeated_across_pages"
    ]])).manifest["routing_records"][0]
    second = ReviewRiskRoutingContract.route(_document([[
        "role_selection_required", "repeated_across_pages"
    ]])).manifest["routing_records"][0]
    assert first["routing_record_id"] == second["routing_record_id"]
    assert first["source_sha256"] == SHA


def test_validation_rejects_attempt_to_turn_routing_into_publication():
    result = ReviewRiskRoutingContract.route(_document([["role_selection_required"]])).manifest
    tampered = copy.deepcopy(result)
    tampered["routing_records"][0]["publication_state"] = "published"
    with pytest.raises(ReviewRiskRoutingError, match="must not publish"):
        ReviewRiskRoutingContract.validate(tampered)


def test_validation_rejects_attempt_to_adjudicate_evidence():
    result = ReviewRiskRoutingContract.route(_document([["role_selection_required"]])).manifest
    tampered = copy.deepcopy(result)
    tampered["routing_records"][0]["adjudication_status"] = "accepted"
    with pytest.raises(ReviewRiskRoutingError, match="must not adjudicate"):
        ReviewRiskRoutingContract.validate(tampered)
