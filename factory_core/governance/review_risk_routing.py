"""Generic, read-only review-risk routing for governed evidence review groups.

This contract classifies review workload by transparent deterministic signals. It
never accepts/rejects evidence, creates a fact, changes applicability/currentness,
or authorizes publication.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping


class ReviewRiskRoutingError(ValueError):
    """Raised when review-risk routing input is incomplete or unsafe."""


@dataclass(frozen=True)
class ReviewRiskRoutingResult:
    manifest: Mapping[str, Any]


_TIER_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_ROUTE_BY_TIER = {
    "low": "light_review",
    "medium": "standard_review",
    "high": "senior_review",
    "critical": "dual_or_senior_review",
}

_CRITICAL_FLAGS = frozenset({
    "conflicting_role_hints",
    "possible_benefit_limit_despite_role_hint",
})
_HIGH_FLAGS = frozenset({
    "unresolved_role_hint",
    "benefit_scope_unresolved",
    "schedule_or_band_binding_unverified",
    "sum_insured_band_scope_unresolved",
    "table_layout_binding_possible",
})
_MEDIUM_FLAGS = frozenset({
    "repeated_same_amount",
    "repeated_across_pages",
    "benefit_scope_inferred_for_grouping",
})
# Structural review flags that do not increase risk by themselves.
_NEUTRAL_FLAGS = frozenset({"role_selection_required"})
_KNOWN_FLAGS = _CRITICAL_FLAGS | _HIGH_FLAGS | _MEDIUM_FLAGS | _NEUTRAL_FLAGS


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReviewRiskRoutingError(f"{label} must be an object")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewRiskRoutingError(f"{label} must be a non-empty string")
    return value.strip()


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReviewRiskRoutingError(f"{label} must be a list")
    return value


def _valid_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


class ReviewRiskRoutingContract:
    """Assigns transparent review tiers without adjudicating evidence."""

    SCHEMA_VERSION = "1.0"
    ROUTING_TYPE = "governed_review_risk_routing_v1"

    @classmethod
    def route(cls, review_document: Mapping[str, Any]) -> ReviewRiskRoutingResult:
        document = _mapping(review_document, "review_document")
        source = _mapping(document.get("source"), "review_document.source")
        source_sha = source.get("sha256")
        if not _valid_sha(source_sha):
            raise ReviewRiskRoutingError("review_document.source.sha256 must be a 64-character SHA-256")

        groups = _list(document.get("review_groups"), "review_document.review_groups")
        if document.get("review_group_count") != len(groups):
            raise ReviewRiskRoutingError("review_group_count must equal review_groups length")

        routed: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for index, raw_group in enumerate(groups):
            group = _mapping(raw_group, f"review_groups[{index}]")
            group_id = _text(group.get("group_id"), f"review_groups[{index}].group_id")
            if group_id in seen_ids:
                raise ReviewRiskRoutingError("review group ids must be unique")
            seen_ids.add(group_id)

            flags = [_text(value, f"review_groups[{index}].review_flags[]") for value in _list(group.get("review_flags"), f"review_groups[{index}].review_flags")]
            unknown = sorted(set(flags) - _KNOWN_FLAGS)
            if unknown:
                raise ReviewRiskRoutingError(
                    "unknown review flag(s) require explicit routing-policy review: " + ", ".join(unknown)
                )

            tier, reasons = cls._tier(flags)
            routed.append({
                "review_group_id": group_id,
                "risk_tier": tier,
                "review_route": _ROUTE_BY_TIER[tier],
                "risk_reasons": reasons,
                "source_sha256": source_sha,
                "routing_record_id": cls._record_id(source_sha, group_id, tier, reasons),
                "adjudication_status": "not_adjudicated",
                "publication_state": "not_published",
            })

        counts = Counter(item["risk_tier"] for item in routed)
        route_counts = Counter(item["review_route"] for item in routed)
        manifest = {
            "schema_version": cls.SCHEMA_VERSION,
            "routing_type": cls.ROUTING_TYPE,
            "routing_status": "review_risk_routes_assigned_not_adjudicated",
            "source": dict(source),
            "input": {
                "review_type": document.get("review_type"),
                "review_layer": document.get("review_layer"),
                "review_group_count": len(groups),
            },
            "routing_record_count": len(routed),
            "routing_records": routed,
            "workload_summary": {
                "tier_counts": {tier: counts.get(tier, 0) for tier in ("critical", "high", "medium", "low")},
                "route_counts": {route: route_counts.get(route, 0) for route in (
                    "dual_or_senior_review", "senior_review", "standard_review", "light_review"
                )},
            },
            "guardrails": [
                "Risk routing is review orchestration only and does not accept or reject evidence.",
                "No routing tier creates a canonical fact, product applicability decision, entitlement decision, or publication decision.",
                "Unknown review flags fail closed until the generic routing policy is explicitly extended.",
                "All routing records remain bound to the source SHA-256 and review-group identity.",
            ],
        }
        cls.validate(manifest)
        return ReviewRiskRoutingResult(manifest=manifest)

    @staticmethod
    def _tier(flags: list[str]) -> tuple[str, list[str]]:
        unique = set(flags)
        critical = sorted(unique & _CRITICAL_FLAGS)
        if critical:
            return "critical", critical
        high = sorted(unique & _HIGH_FLAGS)
        if high:
            return "high", high
        medium = sorted(unique & _MEDIUM_FLAGS)
        if medium:
            return "medium", medium
        return "low", ["no_material_ambiguity_flags"]

    @staticmethod
    def _record_id(source_sha: str, group_id: str, tier: str, reasons: list[str]) -> str:
        payload = json.dumps({"sha": source_sha, "group": group_id, "tier": tier, "reasons": reasons}, sort_keys=True)
        return "rrisk_" + sha256(payload.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def validate(cls, manifest: Mapping[str, Any]) -> None:
        document = _mapping(manifest, "routing_manifest")
        if document.get("schema_version") != cls.SCHEMA_VERSION:
            raise ReviewRiskRoutingError("unsupported routing schema_version")
        if document.get("routing_type") != cls.ROUTING_TYPE:
            raise ReviewRiskRoutingError("unsupported routing_type")
        if document.get("routing_status") != "review_risk_routes_assigned_not_adjudicated":
            raise ReviewRiskRoutingError("routing_status must remain non-adjudicating")
        records = _list(document.get("routing_records"), "routing_records")
        if document.get("routing_record_count") != len(records):
            raise ReviewRiskRoutingError("routing_record_count must equal routing_records length")
        for record in records:
            row = _mapping(record, "routing_record")
            tier = row.get("risk_tier")
            if tier not in _TIER_ORDER or row.get("review_route") != _ROUTE_BY_TIER[tier]:
                raise ReviewRiskRoutingError("routing record tier/route is invalid")
            if row.get("adjudication_status") != "not_adjudicated":
                raise ReviewRiskRoutingError("routing records must not adjudicate evidence")
            if row.get("publication_state") != "not_published":
                raise ReviewRiskRoutingError("routing records must not publish knowledge")
            if not _valid_sha(row.get("source_sha256")):
                raise ReviewRiskRoutingError("routing record source_sha256 is invalid")


__all__ = ["ReviewRiskRoutingContract", "ReviewRiskRoutingError", "ReviewRiskRoutingResult"]
