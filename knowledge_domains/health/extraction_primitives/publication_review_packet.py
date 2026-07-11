"""P1.9A — non-publishing packet for human review of eligible canonical facts.

The contract creates a reviewable snapshot from existing immutable artifacts. It does
not approve facts, publish knowledge, write an operational store, or create
plain-language explanations.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any, Mapping


class PublicationReviewPacketError(ValueError):
    """Raised when immutable inputs cannot be safely joined into a review packet."""


class PublicationReviewPacketContract:
    VERSION = "1.0"
    DOCUMENT_TYPE = "health_publication_review_packet_document_v1"
    STATUS = "publication_review_packet_prepared_pending_human_review"
    ITEM_STATUS = "awaiting_publication_review"
    GUARDRAIL = "review_packet_only_no_approval_publication_or_reusable_knowledge"
    ELIGIBLE_STATUS = "eligible_for_publication_review"

    @classmethod
    def build_packet(
        cls,
        *,
        materialization_document: Mapping[str, Any],
        eligibility_document: Mapping[str, Any],
        reviewer_submission_document: Mapping[str, Any],
        candidate_review_document: Mapping[str, Any],
        prepared_by: str,
        prepared_at: str,
    ) -> dict[str, Any]:
        cls._require_non_empty("prepared_by", prepared_by)
        cls._validate_iso_timestamp(prepared_at, "prepared_at")
        cls._validate_materialization(materialization_document)
        cls._validate_eligibility(eligibility_document)
        cls._validate_submission(reviewer_submission_document)
        cls._validate_candidate_review(candidate_review_document)

        source = dict(materialization_document["source"])
        cls._assert_same_source(source, eligibility_document.get("source"), "eligibility_document.source")
        cls._assert_same_source(source, reviewer_submission_document.get("source"), "reviewer_submission_document.source")
        cls._assert_same_source(source, candidate_review_document.get("source"), "candidate_review_document.source")

        if eligibility_document.get("input", {}).get("materialization_id") != materialization_document.get("materialization_id"):
            raise PublicationReviewPacketError("eligibility document must reference input materialization_id")
        if materialization_document.get("input", {}).get("source_submission_id") != reviewer_submission_document.get("submission_id"):
            raise PublicationReviewPacketError("materialization document must reference reviewer submission_id")

        canonical_by_id = {fact.get("canonical_fact_id"): fact for fact in materialization_document["canonical_facts"]}
        if len(canonical_by_id) != len(materialization_document["canonical_facts"]):
            raise PublicationReviewPacketError("materialization canonical_fact_id values must be unique")
        eligible_records = [
            record for record in eligibility_document["eligibility_records"]
            if record.get("record_kind") == "canonical_fact" and record.get("eligibility_status") == cls.ELIGIBLE_STATUS
        ]
        eligibility_by_fact_id = {record.get("canonical_fact_id"): record for record in eligible_records}
        if len(eligibility_by_fact_id) != len(eligible_records):
            raise PublicationReviewPacketError("eligible canonical_fact_id values must be unique")
        if set(eligibility_by_fact_id) != set(canonical_by_id):
            raise PublicationReviewPacketError("eligible canonical facts must exactly match materialized canonical facts")

        submission_by_decision_id = {
            record.get("decision_record_id"): record for record in reviewer_submission_document["submitted_records"]
        }
        if len(submission_by_decision_id) != len(reviewer_submission_document["submitted_records"]):
            raise PublicationReviewPacketError("submission decision_record_id values must be unique")
        group_by_id = {group.get("group_id"): group for group in candidate_review_document["review_groups"]}
        if len(group_by_id) != len(candidate_review_document["review_groups"]):
            raise PublicationReviewPacketError("candidate review group_id values must be unique")

        items: list[dict[str, Any]] = []
        for fact_id in sorted(canonical_by_id):
            fact = canonical_by_id[fact_id]
            eligibility = eligibility_by_fact_id[fact_id]
            lineage = cls._mapping(fact.get("review_lineage"), "canonical_fact.review_lineage")
            decision_id = cls._require_non_empty("review_lineage.source_decision_record_id", lineage.get("source_decision_record_id"))
            submission = submission_by_decision_id.get(decision_id)
            if submission is None:
                raise PublicationReviewPacketError("canonical fact source_decision_record_id missing from reviewer submission")
            if submission.get("decision") != "accept":
                raise PublicationReviewPacketError("publication review packet requires accepted reviewer submission record")
            if submission.get("source_sha256") != source.get("sha256"):
                raise PublicationReviewPacketError("submission source SHA must match materialized source")
            if submission.get("immutable_record_id") != lineage.get("source_immutable_record_id"):
                raise PublicationReviewPacketError("canonical fact lineage immutable record must match reviewer submission")
            review_group_id = cls._require_non_empty("reviewer_submission.review_group_id", submission.get("review_group_id"))
            group = group_by_id.get(review_group_id)
            if group is None:
                raise PublicationReviewPacketError("reviewer submission review_group_id missing from candidate review")
            snapshot = cls._mapping(submission.get("review_group_snapshot"), "reviewer_submission.review_group_snapshot")
            if snapshot.get("group_id") != review_group_id:
                raise PublicationReviewPacketError("reviewer submission snapshot group_id must match review_group_id")
            if snapshot.get("bounded_evidence_identity") != group.get("bounded_evidence_identity"):
                raise PublicationReviewPacketError("reviewer submission bounded evidence identity must match candidate review group")
            if snapshot.get("normalized_value") != group.get("normalized_value"):
                raise PublicationReviewPacketError("reviewer submission normalized value must match candidate review group")
            if group.get("normalized_value") != fact.get("normalized_value"):
                raise PublicationReviewPacketError("candidate review normalized value must match canonical fact")

            item = {
                "packet_item_id": cls._item_id(fact_id, eligibility.get("eligibility_record_id"), submission.get("immutable_record_id")),
                "review_status": cls.ITEM_STATUS,
                "canonical_fact": cls._fact_snapshot(fact),
                "publication_eligibility": cls._eligibility_snapshot(eligibility),
                "review_lineage": {
                    "source_submission_id": reviewer_submission_document.get("submission_id"),
                    "source_decision_record_id": submission.get("decision_record_id"),
                    "source_immutable_record_id": submission.get("immutable_record_id"),
                    "review_group_id": review_group_id,
                    "review_snapshot_fingerprint": submission.get("review_snapshot_fingerprint"),
                    "reviewer_identity": submission.get("reviewer_identity"),
                    "reviewed_at": submission.get("reviewed_at"),
                    "review_rationale": submission.get("review_rationale"),
                },
                "bounded_evidence": {
                    "bounded_evidence_identity": group.get("bounded_evidence_identity"),
                    "supporting_pages": list(group.get("supporting_pages", [])),
                    "evidence_items": list(group.get("bounded_evidence", [])),
                    "candidate_review_artifact": {
                        "review_group_id": review_group_id,
                        "review_type": candidate_review_document.get("review_type"),
                        "review_layer": candidate_review_document.get("review_layer"),
                    },
                },
                "publication_state": "not_published",
                "entitlement_state": "not_evaluated",
                "reusable_knowledge_state": "not_created",
                "non_publication_guardrail": cls.GUARDRAIL,
            }
            items.append(item)

        output = {
            "schema_version": "1.0",
            "packet_document_type": cls.DOCUMENT_TYPE,
            "packet_contract_version": cls.VERSION,
            "status": cls.STATUS,
            "source": source,
            "input": {
                "materialization_id": materialization_document.get("materialization_id"),
                "eligibility_assessment_id": eligibility_document.get("eligibility_assessment_id"),
                "reviewer_submission_id": reviewer_submission_document.get("submission_id"),
                "candidate_review_type": candidate_review_document.get("review_type"),
                "canonical_fact_count": materialization_document.get("canonical_fact_count"),
                "eligible_canonical_fact_count": len(eligible_records),
            },
            "prepared_by": prepared_by,
            "prepared_at": prepared_at,
            "publication_review_packet_id": cls._packet_id(
                source_sha256=source.get("sha256"),
                materialization_id=materialization_document.get("materialization_id"),
                eligibility_id=eligibility_document.get("eligibility_assessment_id"),
                submission_id=reviewer_submission_document.get("submission_id"),
                prepared_by=prepared_by,
                prepared_at=prepared_at,
                item_ids=[item["packet_item_id"] for item in items],
            ),
            "packet_item_count": len(items),
            "packet_items": items,
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "reusable_knowledge_state": "not_created",
            "non_publication_guardrail": cls.GUARDRAIL,
            "limitations": [
                "This packet is a read-only review snapshot. It does not approve, reject, defer, publish, or write reusable knowledge.",
                "Plain-language explanations, examples, customer-facing text, and recommendation logic are outside this contract.",
                "A later immutable human decision artifact is required before any reusable knowledge package can be created.",
            ],
        }
        cls.validate_packet(output)
        return output

    @classmethod
    def validate_packet(cls, packet: Mapping[str, Any]) -> None:
        if not isinstance(packet, Mapping):
            raise PublicationReviewPacketError("publication review packet must be an object")
        if packet.get("packet_document_type") != cls.DOCUMENT_TYPE:
            raise PublicationReviewPacketError("unsupported packet_document_type")
        if packet.get("packet_contract_version") != cls.VERSION:
            raise PublicationReviewPacketError("unsupported packet_contract_version")
        if packet.get("status") != cls.STATUS:
            raise PublicationReviewPacketError("invalid publication review packet status")
        if packet.get("publication_state") != "not_published" or packet.get("entitlement_state") != "not_evaluated":
            raise PublicationReviewPacketError("packet must remain not_published and not_evaluated")
        if packet.get("reusable_knowledge_state") != "not_created":
            raise PublicationReviewPacketError("packet must not create reusable knowledge")
        if packet.get("non_publication_guardrail") != cls.GUARDRAIL:
            raise PublicationReviewPacketError("packet must carry non-publication guardrail")
        cls._require_non_empty("prepared_by", packet.get("prepared_by"))
        cls._validate_iso_timestamp(packet.get("prepared_at"), "prepared_at")
        cls._require_prefixed_id("publication_review_packet_id", packet.get("publication_review_packet_id"), "prpkt_")
        items = packet.get("packet_items")
        if not isinstance(items, list) or not items:
            raise PublicationReviewPacketError("packet_items must be a non-empty list")
        if packet.get("packet_item_count") != len(items):
            raise PublicationReviewPacketError("packet_item_count must match packet_items")
        seen: set[str] = set()
        for item in items:
            cls._validate_item(item)
            item_id = item["packet_item_id"]
            if item_id in seen:
                raise PublicationReviewPacketError("duplicate packet_item_id")
            seen.add(item_id)

    @classmethod
    def _validate_item(cls, item: Mapping[str, Any]) -> None:
        if not isinstance(item, Mapping):
            raise PublicationReviewPacketError("packet item must be an object")
        cls._require_prefixed_id("packet_item_id", item.get("packet_item_id"), "prpktitem_")
        if item.get("review_status") != cls.ITEM_STATUS:
            raise PublicationReviewPacketError("packet item must remain awaiting_publication_review")
        if item.get("publication_state") != "not_published" or item.get("entitlement_state") != "not_evaluated":
            raise PublicationReviewPacketError("packet item must remain not_published and not_evaluated")
        if item.get("reusable_knowledge_state") != "not_created":
            raise PublicationReviewPacketError("packet item must not create reusable knowledge")
        if item.get("non_publication_guardrail") != cls.GUARDRAIL:
            raise PublicationReviewPacketError("packet item must carry non-publication guardrail")
        fact = cls._mapping(item.get("canonical_fact"), "packet_item.canonical_fact")
        cls._require_prefixed_id("canonical_fact_id", fact.get("canonical_fact_id"), "cfact_")
        eligibility = cls._mapping(item.get("publication_eligibility"), "packet_item.publication_eligibility")
        if eligibility.get("eligibility_status") != cls.ELIGIBLE_STATUS:
            raise PublicationReviewPacketError("packet item eligibility status must be eligible_for_publication_review")
        if eligibility.get("canonical_fact_id") != fact.get("canonical_fact_id"):
            raise PublicationReviewPacketError("packet item canonical fact must match eligibility fact")
        evidence = cls._mapping(item.get("bounded_evidence"), "packet_item.bounded_evidence")
        cls._require_non_empty("bounded_evidence_identity", evidence.get("bounded_evidence_identity"))
        if not isinstance(evidence.get("evidence_items"), list) or not evidence["evidence_items"]:
            raise PublicationReviewPacketError("packet item requires bounded evidence items")

    @classmethod
    def _validate_materialization(cls, doc: Mapping[str, Any]) -> None:
        if not isinstance(doc, Mapping) or doc.get("materialization_document_type") != "health_canonical_fact_materialization_document_v1":
            raise PublicationReviewPacketError("unsupported canonical fact materialization document")
        if doc.get("status") != "materialized_not_published":
            raise PublicationReviewPacketError("materialization must remain materialized_not_published")
        if not isinstance(doc.get("canonical_facts"), list) or not doc["canonical_facts"]:
            raise PublicationReviewPacketError("materialization must contain canonical_facts")

    @classmethod
    def _validate_eligibility(cls, doc: Mapping[str, Any]) -> None:
        if not isinstance(doc, Mapping) or doc.get("eligibility_document_type") != "health_fact_publication_eligibility_document_v1":
            raise PublicationReviewPacketError("unsupported publication eligibility document")
        if doc.get("status") != "publication_eligibility_assessed_not_published":
            raise PublicationReviewPacketError("eligibility document must remain not published")
        if not isinstance(doc.get("eligibility_records"), list):
            raise PublicationReviewPacketError("eligibility document requires eligibility_records")

    @classmethod
    def _validate_submission(cls, doc: Mapping[str, Any]) -> None:
        if not isinstance(doc, Mapping) or doc.get("submission_document_type") != "health_reviewer_decision_submission_document_v1":
            raise PublicationReviewPacketError("unsupported reviewer decision submission")
        if doc.get("status") != "submitted_human_review":
            raise PublicationReviewPacketError("reviewer decision submission must be submitted_human_review")
        if not isinstance(doc.get("submitted_records"), list) or not doc["submitted_records"]:
            raise PublicationReviewPacketError("reviewer decision submission requires submitted_records")

    @classmethod
    def _validate_candidate_review(cls, doc: Mapping[str, Any]) -> None:
        if not isinstance(doc, Mapping) or doc.get("review_type") != "health_currency_candidate_review_document_v1":
            raise PublicationReviewPacketError("unsupported candidate review document")
        if doc.get("status") != "review_records_generated":
            raise PublicationReviewPacketError("candidate review must be review_records_generated")
        if not isinstance(doc.get("review_groups"), list) or not doc["review_groups"]:
            raise PublicationReviewPacketError("candidate review requires review_groups")

    @staticmethod
    def _fact_snapshot(fact: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "canonical_fact_id": fact.get("canonical_fact_id"),
            "governed_fact_id": fact.get("governed_fact_id"),
            "entity_id": fact.get("entity_id"),
            "canonical_field_key": fact.get("canonical_field_key"),
            "normalized_value": dict(fact.get("normalized_value", {})),
            "benefit_scope": fact.get("benefit_scope"),
            "applicability": dict(fact.get("applicability", {})),
            "source_document": dict(fact.get("source_document", {})),
        }

    @staticmethod
    def _eligibility_snapshot(record: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "eligibility_record_id": record.get("eligibility_record_id"),
            "canonical_fact_id": record.get("canonical_fact_id"),
            "eligibility_status": record.get("eligibility_status"),
            "eligibility_reason": record.get("eligibility_reason"),
            "validation_checks": dict(record.get("validation_checks", {})),
        }

    @classmethod
    def _assert_same_source(cls, expected: Mapping[str, Any], actual: Any, label: str) -> None:
        source = cls._mapping(actual, label)
        for key in ("entity_id", "sha256", "document_type"):
            if source.get(key) != expected.get(key):
                raise PublicationReviewPacketError(f"{label}.{key} must match materialized source")

    @staticmethod
    def _mapping(value: Any, label: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise PublicationReviewPacketError(f"{label} must be an object")
        return value

    @staticmethod
    def _require_non_empty(label: str, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise PublicationReviewPacketError(f"{label} must be a non-empty string")
        return value.strip()

    @classmethod
    def _require_prefixed_id(cls, label: str, value: Any, prefix: str) -> str:
        raw = cls._require_non_empty(label, value)
        if not raw.startswith(prefix):
            raise PublicationReviewPacketError(f"{label} must be a {prefix} identifier")
        return raw

    @staticmethod
    def _validate_iso_timestamp(value: Any, label: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise PublicationReviewPacketError(f"{label} must be ISO-8601")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise PublicationReviewPacketError(f"{label} must be ISO-8601") from exc

    @staticmethod
    def _item_id(fact_id: Any, eligibility_id: Any, immutable_record_id: Any) -> str:
        value = f"publication-review-item|{fact_id}|{eligibility_id}|{immutable_record_id}"
        return "prpktitem_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _packet_id(*, source_sha256: Any, materialization_id: Any, eligibility_id: Any, submission_id: Any, prepared_by: str, prepared_at: str, item_ids: list[str]) -> str:
        value = "|".join(map(str, [source_sha256, materialization_id, eligibility_id, submission_id, prepared_by, prepared_at, *sorted(item_ids)]))
        return "prpkt_" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
