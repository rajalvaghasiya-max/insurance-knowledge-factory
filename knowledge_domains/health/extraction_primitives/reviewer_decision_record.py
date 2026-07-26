"""Durable human-review decision records for currency evidence review groups.

This module is deliberately downstream of review grouping but upstream of any
fact, entitlement, or publication process.  It records a human decision and
its source-hash-bound review context; it never creates a canonical fact.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping


class ReviewerDecisionRecordError(ValueError):
    """Raised when a reviewer-decision record breaks the governed contract."""


class ReviewerDecisionRecordContract:
    VERSION = "1.0"
    DOCUMENT_TYPE = "health_reviewer_decision_document_v1"
    REVIEW_INPUT_TYPE = "health_currency_candidate_review_document_v1"
    ALLOWED_DECISIONS = {"accept", "reject", "split_further", "defer"}
    PENDING_STATUS = "pending_review"
    RESOLVED_STATUS = "decision_recorded"

    @classmethod
    def build_pending_document(cls, review_document: Mapping[str, Any]) -> dict[str, Any]:
        cls._validate_review_document(review_document)
        source = dict(review_document["source"])
        records = [cls._pending_record(group, source) for group in review_document["review_groups"]]
        output = {
            "schema_version": "1.0",
            "decision_document_type": cls.DOCUMENT_TYPE,
            "decision_contract_version": cls.VERSION,
            "status": "pending_human_review" if records else "no_review_groups",
            "source": source,
            "input": {
                "review_type": review_document["review_type"],
                "review_layer": review_document["review_layer"],
                "review_layer_version": review_document["review_layer_version"],
                "input_review_group_count": review_document["review_group_count"],
            },
            "decision_record_count": len(records),
            "decision_records": records,
            "limitations": [
                "Decision records document human review only; they do not create canonical facts, publication decisions, or entitlement decisions.",
                "Every decision is bound to the reviewed source SHA-256 and review-group snapshot; a changed source requires a new review decision.",
                "Accepting a record means only that it may be considered by a later governed fact-selection process; it does not publish a fact.",
                "Applicability, table/column binding, policy schedule binding, currentness, and legal interpretation remain outside this contract.",
            ],
        }
        cls.validate_decision_document(output)
        return output

    @classmethod
    def build_resolved_record(
        cls,
        pending_record: Mapping[str, Any],
        *,
        decision: str,
        reviewer_identity: str,
        reviewed_at: str,
        review_rationale: str,
        selected_role: str | None = None,
        selected_benefit_scope: str | None = None,
        selected_band_scope: str | None = None,
    ) -> dict[str, Any]:
        record = dict(pending_record)
        record.update({
            "review_status": cls.RESOLVED_STATUS,
            "decision": decision,
            "selected_role": selected_role,
            "selected_benefit_scope": selected_benefit_scope,
            "selected_band_scope": selected_band_scope,
            "review_rationale": review_rationale,
            "reviewer_identity": reviewer_identity,
            "reviewed_at": reviewed_at,
        })
        cls.validate_decision_record(record)
        return record

    @classmethod
    def validate_decision_document(cls, document: Mapping[str, Any]) -> None:
        if not isinstance(document, Mapping):
            raise ReviewerDecisionRecordError("decision document must be an object")
        if document.get("decision_document_type") != cls.DOCUMENT_TYPE:
            raise ReviewerDecisionRecordError("unsupported decision_document_type")
        if document.get("decision_contract_version") != cls.VERSION:
            raise ReviewerDecisionRecordError("unsupported decision_contract_version")
        source = document.get("source")
        if not isinstance(source, Mapping) or not cls._valid_sha(source.get("sha256")):
            raise ReviewerDecisionRecordError("source.sha256 must be a 64-character SHA-256")
        records = document.get("decision_records")
        if not isinstance(records, list):
            raise ReviewerDecisionRecordError("decision_records must be a list")
        if document.get("decision_record_count") != len(records):
            raise ReviewerDecisionRecordError("decision_record_count must equal decision_records length")
        record_ids: set[str] = set()
        group_ids: set[str] = set()
        for record in records:
            cls.validate_decision_record(record)
            if record["decision_record_id"] in record_ids:
                raise ReviewerDecisionRecordError("duplicate decision_record_id")
            if record["review_group_id"] in group_ids:
                raise ReviewerDecisionRecordError("duplicate review_group_id")
            record_ids.add(record["decision_record_id"])
            group_ids.add(record["review_group_id"])
            if record["source_sha256"] != source["sha256"]:
                raise ReviewerDecisionRecordError("decision record source_sha256 must match document source")

    @classmethod
    def validate_decision_record(cls, record: Mapping[str, Any]) -> None:
        if not isinstance(record, Mapping):
            raise ReviewerDecisionRecordError("decision record must be an object")
        required_strings = ("decision_record_id", "review_group_id", "source_sha256", "non_fact_guardrail")
        for key in required_strings:
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ReviewerDecisionRecordError(f"{key} must be a non-empty string")
        if not cls._valid_sha(record["source_sha256"]):
            raise ReviewerDecisionRecordError("source_sha256 must be a 64-character SHA-256")
        if record.get("non_fact_guardrail") != "review_decision_only_no_canonical_fact":
            raise ReviewerDecisionRecordError("non_fact_guardrail must block canonical fact creation")
        snapshot = record.get("review_group_snapshot")
        if not isinstance(snapshot, Mapping):
            raise ReviewerDecisionRecordError("review_group_snapshot must be an object")
        if snapshot.get("group_id") != record.get("review_group_id"):
            raise ReviewerDecisionRecordError("review_group_snapshot.group_id must match review_group_id")
        if not isinstance(snapshot.get("normalized_value"), Mapping):
            raise ReviewerDecisionRecordError("review_group_snapshot.normalized_value must be an object")
        status = record.get("review_status")
        if status == cls.PENDING_STATUS:
            for key in ("decision", "selected_role", "selected_benefit_scope", "selected_band_scope", "review_rationale", "reviewer_identity", "reviewed_at"):
                if record.get(key) is not None:
                    raise ReviewerDecisionRecordError(f"pending review record must not set {key}")
            return
        if status != cls.RESOLVED_STATUS:
            raise ReviewerDecisionRecordError("review_status must be pending_review or decision_recorded")
        decision = record.get("decision")
        if decision not in cls.ALLOWED_DECISIONS:
            raise ReviewerDecisionRecordError("decision must be accept, reject, split_further, or defer")
        for key in ("review_rationale", "reviewer_identity", "reviewed_at"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ReviewerDecisionRecordError(f"resolved decision requires {key}")
        cls._validate_iso_timestamp(record["reviewed_at"])
        if decision == "accept":
            for key in ("selected_role", "selected_benefit_scope"):
                if not isinstance(record.get(key), str) or not record[key].strip():
                    raise ReviewerDecisionRecordError("accept decision requires selected_role and selected_benefit_scope")
        elif any(record.get(key) is not None for key in ("selected_role", "selected_benefit_scope", "selected_band_scope")):
            raise ReviewerDecisionRecordError("only accept decisions may set selected role or scope")

    @classmethod
    def _pending_record(cls, group: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
        group_id = group.get("group_id")
        if not isinstance(group_id, str) or not group_id:
            raise ReviewerDecisionRecordError("review group missing group_id")
        snapshot = {
            "group_id": group_id,
            "candidate_type": group.get("candidate_type"),
            "normalized_value": dict(group.get("normalized_value", {})),
            "inferred_scope": dict(group.get("inferred_scope", {})),
            "review_flags": list(group.get("review_flags", [])),
            "observed_role_hints": list(group.get("observed_role_hints", [])),
            "condition_hints": list(group.get("condition_hints", [])),
            "bounded_evidence_identity": group.get("bounded_evidence_identity"),
            "supporting_candidate_ids": [
                candidate.get("candidate_id")
                for candidate in group.get("supporting_candidates", [])
                if isinstance(candidate, Mapping) and isinstance(candidate.get("candidate_id"), str)
            ],
            # Preserve the source-bounded review basis. This remains evidence,
            # not a canonical fact or applicability conclusion.
            "bounded_evidence": copy.deepcopy(list(group.get("bounded_evidence", []))),
        }
        return {
            "decision_record_id": cls._record_id(group_id, source["sha256"]),
            "review_group_id": group_id,
            "review_status": cls.PENDING_STATUS,
            "decision": None,
            "selected_role": None,
            "selected_benefit_scope": None,
            "selected_band_scope": None,
            "review_rationale": None,
            "reviewer_identity": None,
            "reviewed_at": None,
            "source_sha256": source["sha256"],
            "review_group_snapshot": snapshot,
            "non_fact_guardrail": "review_decision_only_no_canonical_fact",
        }

    @staticmethod
    def _record_id(group_id: str, sha256: str) -> str:
        digest = hashlib.sha256(f"review_decision|{group_id}|{sha256}".encode("utf-8")).hexdigest()[:16]
        return f"rdec_{digest}"

    @staticmethod
    def _valid_sha(value: Any) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())

    @staticmethod
    def _validate_iso_timestamp(value: str) -> None:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReviewerDecisionRecordError("reviewed_at must be ISO-8601") from exc

    @classmethod
    def _validate_review_document(cls, document: Mapping[str, Any]) -> None:
        if not isinstance(document, Mapping):
            raise ReviewerDecisionRecordError("review document must be an object")
        if document.get("review_type") != cls.REVIEW_INPUT_TYPE:
            raise ReviewerDecisionRecordError("unsupported review_type")
        if document.get("status") not in {"review_records_generated", "no_supported_currency_candidates"}:
            raise ReviewerDecisionRecordError("unsupported review document status")
        source = document.get("source")
        if not isinstance(source, Mapping) or not cls._valid_sha(source.get("sha256")):
            raise ReviewerDecisionRecordError("review document source.sha256 must be valid")
        groups = document.get("review_groups")
        if not isinstance(groups, list):
            raise ReviewerDecisionRecordError("review_groups must be a list")
        if document.get("review_group_count") != len(groups):
            raise ReviewerDecisionRecordError("review_group_count must equal review_groups length")
