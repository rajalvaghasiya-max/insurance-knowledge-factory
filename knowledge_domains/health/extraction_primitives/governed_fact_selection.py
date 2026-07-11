"""Deterministic, non-publishing selection gate for submitted human reviews.

This module consumes only immutable reviewer-decision submission artifacts.  It
revalidates their source binding and converts supported accepted review records
into *selected governed fact artifacts*.  These artifacts remain upstream of a
canonical fact store, entitlement logic, and customer-facing publication.

V0.1 is intentionally narrow: it selects currency sub-limits / limits from the
reviewed currency workflow and defers other semantic categories until the
Health Field Registry defines their canonical representation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Mapping

from knowledge_domains.health.field_registry.selection_policy import HealthFieldSelectionPolicy

from knowledge_domains.health.extraction_primitives.reviewer_decision_submission import (
    ReviewerDecisionSubmissionContract,
    ReviewerDecisionSubmissionError,
)


class GovernedFactSelectionError(ValueError):
    """Raised when a submission cannot safely enter the fact-selection gate."""


class GovernedFactSelectionContract:
    VERSION = "1.0"
    DOCUMENT_TYPE = "health_governed_fact_selection_document_v1"
    STATUS = "selection_completed_not_published"
    NON_PUBLICATION_GUARDRAIL = "selected_governed_fact_not_published"

    SELECTED = "selected_governed_fact"
    ELIGIBLE = "eligible_for_selection"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    ALLOWED_SELECTION_STATUSES = {SELECTED, ELIGIBLE, DEFERRED, BLOCKED}

    # Deliberately narrow until field-registry rules are approved.
    SUPPORTED_ROLE_TO_FIELD = {
        "sub_limit_or_limit": "currency_sub_limit",
    }

    @classmethod
    def build_selection_document(
        cls,
        submission_document: Mapping[str, Any],
        *,
        selected_at: str,
        selector_identity: str,
    ) -> dict[str, Any]:
        """Build a deterministic selection artifact without publishing facts.

        Selection is allowed only for accepted, immutable, source-bound records
        matching the V0.1 currency-sub-limit policy.  Other reviewed records are
        explicitly deferred or blocked; no value is silently discarded.
        """
        try:
            ReviewerDecisionSubmissionContract.validate_submission_document(submission_document)
        except ReviewerDecisionSubmissionError as exc:
            raise GovernedFactSelectionError(str(exc)) from exc
        cls._require_non_empty("selector_identity", selector_identity)
        cls._validate_iso_timestamp(selected_at)

        source = dict(submission_document["source"])
        cls._validate_selection_source(source)
        records = submission_document["submitted_records"]
        selections = [
            cls._selection_record(
                record,
                source=source,
                submission_id=submission_document["submission_id"],
            )
            for record in records
        ]
        output = {
            "schema_version": "1.0",
            "selection_document_type": cls.DOCUMENT_TYPE,
            "selection_contract_version": cls.VERSION,
            "status": cls.STATUS,
            "source": source,
            "input": {
                "submission_document_type": submission_document["submission_document_type"],
                "submission_contract_version": submission_document["submission_contract_version"],
                "submission_id": submission_document["submission_id"],
                "submitted_at": submission_document["submitted_at"],
                "submitted_record_count": submission_document["submitted_record_count"],
            },
            "selector_identity": selector_identity,
            "selected_at": selected_at,
            "selection_record_count": len(selections),
            "selection_records": selections,
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
            "non_publication_guardrail": cls.NON_PUBLICATION_GUARDRAIL,
            "limitations": [
                "This is a governed fact-selection artifact, not a canonical fact-store write.",
                "No selection record is customer-facing or eligible for an entitlement decision.",
                "Currentness, policy applicability beyond reviewed scope, conflict resolution, and legal interpretation remain outside this gate.",
                "Only field mappings explicitly defined by the approved Health Field Registry selection policy are selected; unsupported reviewed categories are explicitly deferred.",
            ],
        }
        cls.validate_selection_document(output)
        return output

    @classmethod
    def validate_selection_document(cls, document: Mapping[str, Any]) -> None:
        if not isinstance(document, Mapping):
            raise GovernedFactSelectionError("selection document must be an object")
        if document.get("selection_document_type") != cls.DOCUMENT_TYPE:
            raise GovernedFactSelectionError("unsupported selection_document_type")
        if document.get("selection_contract_version") != cls.VERSION:
            raise GovernedFactSelectionError("unsupported selection_contract_version")
        if document.get("status") != cls.STATUS:
            raise GovernedFactSelectionError("selection status must be selection_completed_not_published")
        if document.get("publication_state") != "not_published":
            raise GovernedFactSelectionError("selection document must not be published")
        if document.get("entitlement_state") != "not_evaluated":
            raise GovernedFactSelectionError("selection document must not evaluate entitlement")
        if document.get("non_publication_guardrail") != cls.NON_PUBLICATION_GUARDRAIL:
            raise GovernedFactSelectionError("selection document must block publication")
        source = document.get("source")
        if not isinstance(source, Mapping):
            raise GovernedFactSelectionError("source must be an object")
        cls._validate_selection_source(source)
        inp = document.get("input")
        if not isinstance(inp, Mapping) or not isinstance(inp.get("submission_id"), str) or not inp["submission_id"].startswith("rsub_"):
            raise GovernedFactSelectionError("input.submission_id must be an rsub_ identifier")
        cls._require_non_empty("selector_identity", document.get("selector_identity"))
        cls._validate_iso_timestamp(document.get("selected_at"))
        records = document.get("selection_records")
        if not isinstance(records, list) or not records:
            raise GovernedFactSelectionError("selection_records must be a non-empty list")
        if document.get("selection_record_count") != len(records):
            raise GovernedFactSelectionError("selection_record_count must equal selection_records length")
        seen: set[str] = set()
        for record in records:
            cls._validate_selection_record(record, source_sha256=source["sha256"], submission_id=inp["submission_id"])
            key = record["selection_record_id"]
            if key in seen:
                raise GovernedFactSelectionError("duplicate selection_record_id")
            seen.add(key)

    @classmethod
    def _selection_record(
        cls,
        submitted_record: Mapping[str, Any],
        *,
        source: Mapping[str, Any],
        submission_id: str,
    ) -> dict[str, Any]:
        decision = submitted_record["decision"]
        snapshot = submitted_record["review_group_snapshot"]
        normalized = dict(snapshot["normalized_value"])
        base = {
            "selection_record_id": cls._selection_record_id(submission_id, submitted_record["immutable_record_id"]),
            "source_submission_id": submission_id,
            "source_immutable_record_id": submitted_record["immutable_record_id"],
            "source_decision_record_id": submitted_record["decision_record_id"],
            "source_sha256": source["sha256"],
            "review_snapshot_fingerprint": submitted_record["review_snapshot_fingerprint"],
            "review_decision": decision,
            "normalized_value": normalized,
            "selected_role": submitted_record.get("selected_role"),
            "selected_benefit_scope": submitted_record.get("selected_benefit_scope"),
            "selected_band_scope": submitted_record.get("selected_band_scope"),
            "publication_state": "not_published",
            "entitlement_state": "not_evaluated",
        }

        if decision != "accept":
            base.update({
                "selection_status": cls.BLOCKED if decision == "reject" else cls.DEFERRED,
                "canonical_field_key": None,
                "governed_fact_id": None,
                "selection_reason": f"review decision is {decision}; no accepted value is available for fact selection",
            })
            return base

        field_key = HealthFieldSelectionPolicy.field_for_role(submitted_record.get("selected_role"))
        if field_key is None:
            base.update({
                "selection_status": cls.DEFERRED,
                "canonical_field_key": None,
                "governed_fact_id": None,
                "selection_reason": "accepted review is outside the approved Health Field Registry selection policy",
            })
            return base
        if not cls._currency_value_is_supported(normalized):
            base.update({
                "selection_status": cls.BLOCKED,
                "canonical_field_key": None,
                "governed_fact_id": None,
                "selection_reason": "accepted review has an unsupported normalized currency value",
            })
            return base
        scope_error = HealthFieldSelectionPolicy.validate_selection_scope(
            field_key=field_key,
            benefit_scope=submitted_record.get("selected_benefit_scope"),
            band_scope=submitted_record.get("selected_band_scope"),
        )
        if scope_error:
            base.update({
                "selection_status": cls.BLOCKED,
                "canonical_field_key": None,
                "governed_fact_id": None,
                "selection_reason": scope_error,
            })
            return base

        fact_id = cls._governed_fact_id(
            source_sha256=source["sha256"],
            immutable_record_id=submitted_record["immutable_record_id"],
            field_key=field_key,
        )
        base.update({
            "selection_status": cls.SELECTED,
            "canonical_field_key": field_key,
            "governed_fact_id": fact_id,
            "selection_reason": f"accepted immutable review record matches the approved Health Field Registry policy for {field_key}",
        })
        return base

    @classmethod
    def _validate_selection_record(cls, record: Mapping[str, Any], *, source_sha256: str, submission_id: str) -> None:
        if not isinstance(record, Mapping):
            raise GovernedFactSelectionError("selection record must be an object")
        for key in ("selection_record_id", "source_submission_id", "source_immutable_record_id", "source_decision_record_id", "source_sha256", "review_snapshot_fingerprint", "review_decision", "selection_status", "selection_reason", "publication_state", "entitlement_state"):
            cls._require_non_empty(key, record.get(key))
        if record.get("source_submission_id") != submission_id:
            raise GovernedFactSelectionError("selection record source_submission_id must match input submission")
        if record.get("source_sha256") != source_sha256:
            raise GovernedFactSelectionError("selection record source_sha256 must match source")
        if record.get("selection_status") not in cls.ALLOWED_SELECTION_STATUSES:
            raise GovernedFactSelectionError("unsupported selection_status")
        if record.get("publication_state") != "not_published" or record.get("entitlement_state") != "not_evaluated":
            raise GovernedFactSelectionError("selection record must remain unpublished and not evaluated")
        if not cls._currency_value_is_supported(record.get("normalized_value")):
            raise GovernedFactSelectionError("selection record normalized_value must be supported INR currency")
        status = record["selection_status"]
        if status == cls.SELECTED:
            if record.get("canonical_field_key") not in HealthFieldSelectionPolicy.supported_field_keys():
                raise GovernedFactSelectionError("selected record has unsupported canonical_field_key")
            if not cls._non_empty_string(record.get("governed_fact_id")):
                raise GovernedFactSelectionError("selected record requires governed_fact_id")
            scope_error = HealthFieldSelectionPolicy.validate_selection_scope(
                field_key=record.get("canonical_field_key"),
                benefit_scope=record.get("selected_benefit_scope"),
                band_scope=record.get("selected_band_scope"),
            )
            if scope_error:
                raise GovernedFactSelectionError(scope_error)
        elif record.get("canonical_field_key") is not None or record.get("governed_fact_id") is not None:
            raise GovernedFactSelectionError("non-selected record must not set canonical_field_key or governed_fact_id")

    @classmethod
    def _validate_selection_source(cls, source: Mapping[str, Any]) -> None:
        if not cls._valid_sha(source.get("sha256")):
            raise GovernedFactSelectionError("source.sha256 must be a valid SHA-256")
        for key in ("entity_id", "insurer_id", "document_type", "source_document_id"):
            cls._require_non_empty(f"source.{key}", source.get(key))

    @staticmethod
    def _currency_value_is_supported(value: Any) -> bool:
        return (
            isinstance(value, Mapping)
            and value.get("kind") == "currency"
            and value.get("unit") == "INR"
            and isinstance(value.get("value"), int)
            and value["value"] > 0
        )

    @staticmethod
    def _selection_record_id(submission_id: str, immutable_record_id: str) -> str:
        digest = hashlib.sha256(f"selection|{submission_id}|{immutable_record_id}".encode("utf-8")).hexdigest()[:16]
        return f"fsel_{digest}"

    @staticmethod
    def _governed_fact_id(*, source_sha256: str, immutable_record_id: str, field_key: str) -> str:
        digest = hashlib.sha256(f"fact-candidate|{source_sha256}|{immutable_record_id}|{field_key}".encode("utf-8")).hexdigest()[:16]
        return f"gfact_{digest}"

    @staticmethod
    def _valid_sha(value: Any) -> bool:
        return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())

    @staticmethod
    def _non_empty_string(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    @classmethod
    def _require_non_empty(cls, name: str, value: Any) -> None:
        if not cls._non_empty_string(value):
            raise GovernedFactSelectionError(f"{name} must be a non-empty string")

    @staticmethod
    def _validate_iso_timestamp(value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            raise GovernedFactSelectionError("selected_at must be ISO-8601")
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GovernedFactSelectionError("selected_at must be ISO-8601") from exc
