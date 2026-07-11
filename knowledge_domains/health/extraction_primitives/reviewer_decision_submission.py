"""Immutable submission artifacts for completed human-review decisions.

This module is downstream of reviewer-decision records and remains upstream of
fact selection, entitlement, or publication.  It validates completed decisions,
binds them to the reviewed source/snapshot, and emits immutable submission
artifacts.  Re-submission creates a revision; it never mutates a prior artifact.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
    ReviewerDecisionRecordError,
)


class ReviewerDecisionSubmissionError(ValueError):
    """Raised when an immutable reviewer-decision submission is invalid."""


class ReviewerDecisionSubmissionContract:
    VERSION = "1.0"
    DOCUMENT_TYPE = "health_reviewer_decision_submission_document_v1"
    STATUS = "submitted_human_review"
    IMMUTABLE_GUARDRAIL = "submitted_review_only_no_canonical_fact"

    @classmethod
    def build_submission_document(
        cls,
        completed_decision_document: Mapping[str, Any],
        *,
        submitted_by: str,
        submitted_at: str,
        previous_submission_document: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new immutable submission artifact from completed decisions.

        The input decision document is not modified.  Every decision record must
        already be resolved and source/snapshot-bound by the D-2 contract.
        """
        try:
            ReviewerDecisionRecordContract.validate_decision_document(completed_decision_document)
        except ReviewerDecisionRecordError as exc:
            raise ReviewerDecisionSubmissionError(str(exc)) from exc
        cls._require_non_empty("submitted_by", submitted_by)
        cls._validate_iso_timestamp(submitted_at)

        records = list(completed_decision_document["decision_records"])
        if not records:
            raise ReviewerDecisionSubmissionError("cannot submit an empty decision document")
        pending = [record["decision_record_id"] for record in records if record.get("review_status") != ReviewerDecisionRecordContract.RESOLVED_STATUS]
        if pending:
            raise ReviewerDecisionSubmissionError("all decision records must be resolved before submission")

        previous_records = cls._validated_previous_records(
            previous_submission_document,
            completed_decision_document,
        )
        submitted_records = [
            cls._submitted_record(
                record,
                submitted_by=submitted_by,
                submitted_at=submitted_at,
                previous_record=previous_records.get(record["decision_record_id"]),
            )
            for record in records
        ]
        output = {
            "schema_version": "1.0",
            "submission_document_type": cls.DOCUMENT_TYPE,
            "submission_contract_version": cls.VERSION,
            "status": cls.STATUS,
            "source": dict(completed_decision_document["source"]),
            "input": {
                "decision_document_type": completed_decision_document["decision_document_type"],
                "decision_contract_version": completed_decision_document["decision_contract_version"],
                "input_decision_record_count": completed_decision_document["decision_record_count"],
            },
            "submitted_by": submitted_by,
            "submitted_at": submitted_at,
            "submission_id": cls._submission_id(completed_decision_document, submitted_by, submitted_at, previous_submission_document),
            "submitted_record_count": len(submitted_records),
            "submitted_records": submitted_records,
            "non_fact_guardrail": cls.IMMUTABLE_GUARDRAIL,
            "limitations": [
                "Submitted review decisions are immutable review artifacts; they do not create canonical facts, publication decisions, or entitlement decisions.",
                "Every submitted record remains bound to its reviewed source SHA-256 and review-group snapshot.",
                "A correction or changed decision must be emitted as a new revision artifact; prior submitted records remain unchanged.",
                "Fact selection, applicability, table/column binding, policy schedule binding, currentness, and legal interpretation remain outside this contract.",
            ],
        }
        cls.validate_submission_document(output)
        return output

    @classmethod
    def validate_submission_document(cls, document: Mapping[str, Any]) -> None:
        if not isinstance(document, Mapping):
            raise ReviewerDecisionSubmissionError("submission document must be an object")
        if document.get("submission_document_type") != cls.DOCUMENT_TYPE:
            raise ReviewerDecisionSubmissionError("unsupported submission_document_type")
        if document.get("submission_contract_version") != cls.VERSION:
            raise ReviewerDecisionSubmissionError("unsupported submission_contract_version")
        if document.get("status") != cls.STATUS:
            raise ReviewerDecisionSubmissionError("submission status must be submitted_human_review")
        if document.get("non_fact_guardrail") != cls.IMMUTABLE_GUARDRAIL:
            raise ReviewerDecisionSubmissionError("submission must block canonical fact creation")
        source = document.get("source")
        if not isinstance(source, Mapping) or not cls._valid_sha(source.get("sha256")):
            raise ReviewerDecisionSubmissionError("source.sha256 must be a valid SHA-256")
        cls._require_non_empty("submitted_by", document.get("submitted_by"))
        cls._validate_iso_timestamp(document.get("submitted_at"))
        if not isinstance(document.get("submission_id"), str) or not document["submission_id"].startswith("rsub_"):
            raise ReviewerDecisionSubmissionError("submission_id must be a non-empty rsub_ identifier")
        records = document.get("submitted_records")
        if not isinstance(records, list) or not records:
            raise ReviewerDecisionSubmissionError("submitted_records must be a non-empty list")
        if document.get("submitted_record_count") != len(records):
            raise ReviewerDecisionSubmissionError("submitted_record_count must equal submitted_records length")
        seen: set[str] = set()
        for record in records:
            cls._validate_submitted_record(record, source_sha256=source["sha256"])
            record_id = record["decision_record_id"]
            if record_id in seen:
                raise ReviewerDecisionSubmissionError("duplicate decision_record_id in submitted_records")
            seen.add(record_id)

    @classmethod
    def _validated_previous_records(
        cls,
        previous: Mapping[str, Any] | None,
        completed: Mapping[str, Any],
    ) -> dict[str, Mapping[str, Any]]:
        if previous is None:
            return {}
        cls.validate_submission_document(previous)
        previous_source = previous.get("source", {})
        if previous_source.get("sha256") != completed.get("source", {}).get("sha256"):
            raise ReviewerDecisionSubmissionError("previous submission source SHA-256 must match completed decision document")
        result: dict[str, Mapping[str, Any]] = {}
        for record in previous["submitted_records"]:
            result[record["decision_record_id"]] = record
        return result

    @classmethod
    def _submitted_record(
        cls,
        record: Mapping[str, Any],
        *,
        submitted_by: str,
        submitted_at: str,
        previous_record: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        base = json.loads(json.dumps(record))
        snapshot_fingerprint = cls._snapshot_fingerprint(base)
        if previous_record is not None:
            previous_fingerprint = previous_record.get("review_snapshot_fingerprint")
            if previous_fingerprint != snapshot_fingerprint:
                raise ReviewerDecisionSubmissionError("previous submitted record snapshot does not match current decision record")
            revision = int(previous_record["revision"]) + 1
            supersedes = previous_record["immutable_record_id"]
        else:
            revision = 1
            supersedes = None
        immutable_id = cls._immutable_record_id(base["decision_record_id"], snapshot_fingerprint, revision)
        base.update({
            "revision": revision,
            "immutable_record_id": immutable_id,
            "supersedes_immutable_record_id": supersedes,
            "review_snapshot_fingerprint": snapshot_fingerprint,
            "submitted_by": submitted_by,
            "submitted_at": submitted_at,
            "non_fact_guardrail": cls.IMMUTABLE_GUARDRAIL,
        })
        return base

    @classmethod
    def _validate_submitted_record(cls, record: Mapping[str, Any], *, source_sha256: str) -> None:
        # Reuse D-2 structural validation while preserving the stronger D-3 guardrail.
        d2_shape = dict(record)
        d2_shape["non_fact_guardrail"] = "review_decision_only_no_canonical_fact"
        try:
            ReviewerDecisionRecordContract.validate_decision_record(d2_shape)
        except ReviewerDecisionRecordError as exc:
            raise ReviewerDecisionSubmissionError(str(exc)) from exc
        if record.get("source_sha256") != source_sha256:
            raise ReviewerDecisionSubmissionError("submitted record source_sha256 must match document source")
        if record.get("non_fact_guardrail") != cls.IMMUTABLE_GUARDRAIL:
            raise ReviewerDecisionSubmissionError("submitted record must block canonical fact creation")
        if not isinstance(record.get("revision"), int) or record["revision"] < 1:
            raise ReviewerDecisionSubmissionError("revision must be a positive integer")
        if not isinstance(record.get("immutable_record_id"), str) or not record["immutable_record_id"].startswith("rsubrec_"):
            raise ReviewerDecisionSubmissionError("immutable_record_id must be an rsubrec_ identifier")
        supersedes = record.get("supersedes_immutable_record_id")
        if record["revision"] == 1 and supersedes is not None:
            raise ReviewerDecisionSubmissionError("revision 1 must not supersede another record")
        if record["revision"] > 1 and (not isinstance(supersedes, str) or not supersedes.startswith("rsubrec_")):
            raise ReviewerDecisionSubmissionError("revision > 1 must identify superseded immutable record")
        if not isinstance(record.get("review_snapshot_fingerprint"), str) or len(record["review_snapshot_fingerprint"]) != 64:
            raise ReviewerDecisionSubmissionError("review_snapshot_fingerprint must be SHA-256")
        cls._require_non_empty("submitted_by", record.get("submitted_by"))
        cls._validate_iso_timestamp(record.get("submitted_at"))

    @staticmethod
    def _snapshot_fingerprint(record: Mapping[str, Any]) -> str:
        stable = {
            "decision_record_id": record.get("decision_record_id"),
            "review_group_id": record.get("review_group_id"),
            "source_sha256": record.get("source_sha256"),
            "review_group_snapshot": record.get("review_group_snapshot"),
        }
        encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _immutable_record_id(decision_record_id: str, fingerprint: str, revision: int) -> str:
        digest = hashlib.sha256(f"submission|{decision_record_id}|{fingerprint}|{revision}".encode("utf-8")).hexdigest()[:16]
        return f"rsubrec_{digest}"

    @staticmethod
    def _submission_id(completed: Mapping[str, Any], submitted_by: str, submitted_at: str, previous: Mapping[str, Any] | None) -> str:
        payload = {
            "source_sha256": completed.get("source", {}).get("sha256"),
            "records": completed.get("decision_records"),
            "submitted_by": submitted_by,
            "submitted_at": submitted_at,
            "previous_submission_id": previous.get("submission_id") if isinstance(previous, Mapping) else None,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return "rsub_" + hashlib.sha256(encoded).hexdigest()[:16]

    @staticmethod
    def _valid_sha(value: Any) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())

    @staticmethod
    def _require_non_empty(name: str, value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ReviewerDecisionSubmissionError(f"{name} must be a non-empty string")

    @staticmethod
    def _validate_iso_timestamp(value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ReviewerDecisionSubmissionError("submitted_at must be ISO-8601")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReviewerDecisionSubmissionError("submitted_at must be ISO-8601") from exc
