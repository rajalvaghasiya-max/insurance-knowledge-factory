
"""P1.9A.1 — immutable publication-review decision submission for packet items.

This contract records a human approval/defer/reject decision against every item in a
prepared P1.9A publication-review packet. It is intentionally non-publishing:
approved items are only eligible inputs for later governed reusable knowledge work.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


class PublicationReviewDecisionSubmissionError(ValueError):
    """Raised when a publication-review decision submission is invalid."""


_ALLOWED_DECISIONS = {
    "approve_for_governed_publication",
    "defer",
    "reject",
}


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PublicationReviewDecisionSubmissionError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise PublicationReviewDecisionSubmissionError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicationReviewDecisionSubmissionError(f"{label} must be a non-empty string")
    return value.strip()


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]}"


def packet_sha256(packet_document: Mapping[str, Any]) -> str:
    """Stable digest of the parsed packet document."""
    canonical = json.dumps(packet_document, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


class PublicationReviewDecisionSubmissionContract:
    """Creates a separate immutable decision artifact for a prepared review packet."""

    @staticmethod
    def build_template(*, packet_document: Mapping[str, Any], prepared_by: str, prepared_at: str) -> dict[str, Any]:
        packet = _mapping(packet_document, "publication_review_packet")
        PublicationReviewDecisionSubmissionContract._validate_packet(packet)
        items = _items(packet.get("packet_items"), "publication_review_packet.packet_items")
        return {
            "schema_version": "1.0",
            "decision_document_type": "health_publication_review_decision_spec_v1",
            "status": "template_pending_human_decision",
            "source_publication_review_packet_id": packet["publication_review_packet_id"],
            "source_publication_review_packet_sha256": packet_sha256(packet),
            "reviewed_by_human": False,
            "reviewer_identity": "",
            "reviewed_at": "",
            "prepared_by": _text(prepared_by, "prepared_by"),
            "prepared_at": _text(prepared_at, "prepared_at"),
            "decision_count": len(items),
            "decisions": [
                {
                    "packet_item_id": _text(item.get("packet_item_id"), "packet_item.packet_item_id"),
                    "canonical_fact_id": _text(
                        _mapping(item.get("canonical_fact"), "packet_item.canonical_fact").get("canonical_fact_id"),
                        "packet_item.canonical_fact.canonical_fact_id",
                    ),
                    "decision": "defer",
                    "rationale": "Pending human publication review.",
                }
                for item in items
            ],
            "non_publication_guardrail": "template_only_no_approval_publication_or_reusable_knowledge",
        }

    @staticmethod
    def record(*, packet_document: Mapping[str, Any], decision_spec: Mapping[str, Any]) -> dict[str, Any]:
        packet = _mapping(packet_document, "publication_review_packet")
        spec = _mapping(decision_spec, "publication_review_decision_spec")
        PublicationReviewDecisionSubmissionContract._validate_packet(packet)

        if spec.get("schema_version") != "1.0":
            raise PublicationReviewDecisionSubmissionError("publication_review_decision_spec.schema_version must be 1.0")
        if spec.get("decision_document_type") != "health_publication_review_decision_spec_v1":
            raise PublicationReviewDecisionSubmissionError("publication_review_decision_spec.decision_document_type is invalid")
        if spec.get("reviewed_by_human") is not True:
            raise PublicationReviewDecisionSubmissionError("publication_review_decision_spec.reviewed_by_human must be true")

        packet_id = _text(packet.get("publication_review_packet_id"), "publication_review_packet.publication_review_packet_id")
        if _text(spec.get("source_publication_review_packet_id"), "source_publication_review_packet_id") != packet_id:
            raise PublicationReviewDecisionSubmissionError("source publication-review packet ID does not match")
        packet_hash = packet_sha256(packet)
        if _text(spec.get("source_publication_review_packet_sha256"), "source_publication_review_packet_sha256") != packet_hash:
            raise PublicationReviewDecisionSubmissionError("source publication-review packet SHA-256 does not match")

        reviewer_identity = _text(spec.get("reviewer_identity"), "reviewer_identity")
        reviewed_at = _text(spec.get("reviewed_at"), "reviewed_at")
        packet_items = _items(packet.get("packet_items"), "publication_review_packet.packet_items")
        decisions = _items(spec.get("decisions"), "publication_review_decision_spec.decisions")
        if len(decisions) != len(packet_items):
            raise PublicationReviewDecisionSubmissionError("decision count must exactly match packet item count")

        item_by_id: dict[str, Mapping[str, Any]] = {}
        for raw in packet_items:
            item = _mapping(raw, "publication_review_packet.packet_items[]")
            item_id = _text(item.get("packet_item_id"), "packet_item.packet_item_id")
            if item_id in item_by_id:
                raise PublicationReviewDecisionSubmissionError("publication-review packet has duplicate packet_item_id")
            if item.get("review_status") != "awaiting_publication_review":
                raise PublicationReviewDecisionSubmissionError(f"packet item is not awaiting publication review: {item_id}")
            eligibility = _mapping(item.get("publication_eligibility"), "packet_item.publication_eligibility")
            if eligibility.get("eligibility_status") != "eligible_for_publication_review":
                raise PublicationReviewDecisionSubmissionError(f"packet item is not eligible for publication review: {item_id}")
            item_by_id[item_id] = item

        recorded: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in decisions:
            decision = _mapping(raw, "publication_review_decision_spec.decisions[]")
            item_id = _text(decision.get("packet_item_id"), "decision.packet_item_id")
            if item_id in seen:
                raise PublicationReviewDecisionSubmissionError("decision packet_item_id values must be unique")
            seen.add(item_id)
            item = item_by_id.get(item_id)
            if item is None:
                raise PublicationReviewDecisionSubmissionError(f"decision packet_item_id is not in source packet: {item_id}")
            outcome = _text(decision.get("decision"), "decision.decision")
            if outcome not in _ALLOWED_DECISIONS:
                raise PublicationReviewDecisionSubmissionError("decision.decision is invalid")
            rationale = _text(decision.get("rationale"), "decision.rationale")
            canonical_fact = _mapping(item.get("canonical_fact"), "packet_item.canonical_fact")
            publication_eligibility = _mapping(item.get("publication_eligibility"), "packet_item.publication_eligibility")
            review_lineage = _mapping(item.get("review_lineage"), "packet_item.review_lineage")
            recorded.append({
                "publication_review_decision_id": _stable_id(
                    "prdec",
                    packet_hash,
                    item_id,
                    outcome,
                    rationale,
                    reviewer_identity,
                    reviewed_at,
                ),
                "packet_item_id": item_id,
                "canonical_fact_id": _text(canonical_fact.get("canonical_fact_id"), "canonical_fact.canonical_fact_id"),
                "governed_fact_id": _text(canonical_fact.get("governed_fact_id"), "canonical_fact.governed_fact_id"),
                "decision": outcome,
                "rationale": rationale,
                "reviewer_identity": reviewer_identity,
                "reviewed_at": reviewed_at,
                "source_packet_lineage": {
                    "publication_review_packet_id": packet_id,
                    "publication_review_packet_sha256": packet_hash,
                    "eligibility_record_id": _text(publication_eligibility.get("eligibility_record_id"), "publication_eligibility.eligibility_record_id"),
                    "source_submission_id": _text(review_lineage.get("source_submission_id"), "review_lineage.source_submission_id"),
                    "source_immutable_record_id": _text(review_lineage.get("source_immutable_record_id"), "review_lineage.source_immutable_record_id"),
                    "source_decision_record_id": _text(review_lineage.get("source_decision_record_id"), "review_lineage.source_decision_record_id"),
                    "review_group_id": _text(review_lineage.get("review_group_id"), "review_lineage.review_group_id"),
                },
                "publication_state": "not_published",
                "reusable_knowledge_state": "not_created",
                "entitlement_state": "not_evaluated",
                "non_publication_guardrail": "decision_record_only_no_publication_or_reusable_knowledge",
            })

        if set(item_by_id) != seen:
            raise PublicationReviewDecisionSubmissionError("every packet item must receive exactly one decision")

        counts = {outcome: sum(1 for record in recorded if record["decision"] == outcome) for outcome in sorted(_ALLOWED_DECISIONS)}
        submission_id = _stable_id(
            "prsub",
            packet_hash,
            reviewer_identity,
            reviewed_at,
            json.dumps(recorded, sort_keys=True, separators=(",", ":")),
        )
        return {
            "schema_version": "1.0",
            "submission_document_type": "health_publication_review_decision_submission_document_v1",
            "status": "human_publication_review_decisions_recorded_not_published",
            "source_publication_review_packet_id": packet_id,
            "source_publication_review_packet_sha256": packet_hash,
            "reviewer_identity": reviewer_identity,
            "reviewed_at": reviewed_at,
            "submission_id": submission_id,
            "submitted_decision_count": len(recorded),
            "decision_counts": counts,
            "submitted_decisions": recorded,
            "non_publication_guardrail": "decision_submission_only_no_publication_reusable_knowledge_or_entitlement",
            "limitations": [
                "Approved items are approved only for a later governed reusable knowledge package; this artifact does not publish facts.",
                "Deferred and rejected items must not enter reusable knowledge.",
                "A changed human decision must be recorded in a new decision submission; earlier artifacts remain unchanged.",
                "Customer-specific entitlement, policy schedule selection, claims assessment, and legal advice remain outside this contract.",
            ],
        }

    @staticmethod
    def _validate_packet(packet: Mapping[str, Any]) -> None:
        if packet.get("schema_version") != "1.0":
            raise PublicationReviewDecisionSubmissionError("publication_review_packet.schema_version must be 1.0")
        if packet.get("status") != "publication_review_packet_prepared_pending_human_review":
            raise PublicationReviewDecisionSubmissionError("publication_review_packet is not pending human review")
        _text(packet.get("publication_review_packet_id"), "publication_review_packet.publication_review_packet_id")
        items = _items(packet.get("packet_items"), "publication_review_packet.packet_items")
        if not items:
            raise PublicationReviewDecisionSubmissionError("publication_review_packet requires packet_items")
