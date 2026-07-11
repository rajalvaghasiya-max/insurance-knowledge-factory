"""Controlled filling of one pending reviewer-decision record.

This module is intentionally upstream of immutable submission and fact selection.
It copies a pending decision document, resolves exactly one pending record using the
D-2 contract, and writes a new decision document.  The input is never mutated.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
    ReviewerDecisionRecordError,
)


class ReviewerDecisionFillError(ValueError):
    """Raised when a reviewer-fill request is invalid or unsafe."""


class ReviewerDecisionFillWorkflow:
    """Safe one-record update workflow for pending reviewer decisions."""

    VERSION = "1.0"
    ALLOWED_ROLES = {
        "sum_insured",
        "sub_limit_or_limit",
        "deductible",
        "premium",
        "monetary_amount_unresolved",
    }
    PENDING_DOCUMENT_STATUS = "pending_human_review"
    IN_PROGRESS_DOCUMENT_STATUS = "in_progress_human_review"
    READY_FOR_SUBMISSION_STATUS = "ready_for_submission"

    @classmethod
    def fill_pending_record(
        cls,
        decision_document: Mapping[str, Any],
        *,
        decision_record_id: str,
        decision: str,
        reviewer_identity: str,
        reviewed_at: str,
        review_rationale: str,
        selected_role: str | None = None,
        selected_benefit_scope: str | None = None,
        selected_band_scope: str | None = None,
    ) -> dict[str, Any]:
        """Return a copied decision document with exactly one pending record resolved.

        This function does not submit, publish, or create canonical facts.  A resolved
        record cannot be edited through this workflow; corrections must be handled via
        a new decision artifact / immutable submission revision flow.
        """
        try:
            ReviewerDecisionRecordContract.validate_decision_document(decision_document)
        except ReviewerDecisionRecordError as exc:
            raise ReviewerDecisionFillError(str(exc)) from exc

        cls._require_non_empty("decision_record_id", decision_record_id)
        cls._require_non_empty("reviewer_identity", reviewer_identity)
        cls._require_non_empty("review_rationale", review_rationale)
        if decision not in ReviewerDecisionRecordContract.ALLOWED_DECISIONS:
            raise ReviewerDecisionFillError("decision must be accept, reject, split_further, or defer")

        cls._validate_requested_fields(
            decision=decision,
            selected_role=selected_role,
            selected_benefit_scope=selected_benefit_scope,
            selected_band_scope=selected_band_scope,
        )

        output = copy.deepcopy(dict(decision_document))
        records = output.get("decision_records", [])
        target_indexes = [
            index for index, record in enumerate(records)
            if isinstance(record, Mapping) and record.get("decision_record_id") == decision_record_id
        ]
        if not target_indexes:
            raise ReviewerDecisionFillError("decision_record_id was not found in decision document")
        if len(target_indexes) != 1:
            raise ReviewerDecisionFillError("decision_record_id must resolve to exactly one record")

        index = target_indexes[0]
        pending_record = records[index]
        if pending_record.get("review_status") != ReviewerDecisionRecordContract.PENDING_STATUS:
            raise ReviewerDecisionFillError("only pending_review records can be filled; resolved records are immutable in this workflow")

        try:
            records[index] = ReviewerDecisionRecordContract.build_resolved_record(
                pending_record,
                decision=decision,
                reviewer_identity=reviewer_identity.strip(),
                reviewed_at=reviewed_at,
                review_rationale=review_rationale.strip(),
                selected_role=selected_role,
                selected_benefit_scope=selected_benefit_scope,
                selected_band_scope=selected_band_scope,
            )
        except ReviewerDecisionRecordError as exc:
            raise ReviewerDecisionFillError(str(exc)) from exc

        output["status"] = cls._document_status(records)
        output["decision_fill_workflow_version"] = cls.VERSION
        output["non_fact_guardrail"] = "review_decision_document_only_no_canonical_fact"
        output["limitations"] = cls._with_fill_limitation(output.get("limitations"))

        # Guarantees that fields outside the target record remain byte-equivalent in
        # semantic content and all D-2 source/snapshot constraints still hold.
        try:
            ReviewerDecisionRecordContract.validate_decision_document(output)
        except ReviewerDecisionRecordError as exc:
            raise ReviewerDecisionFillError(str(exc)) from exc
        return output

    @classmethod
    def _validate_requested_fields(
        cls,
        *,
        decision: str,
        selected_role: str | None,
        selected_benefit_scope: str | None,
        selected_band_scope: str | None,
    ) -> None:
        if decision == "accept":
            if selected_role not in cls.ALLOWED_ROLES:
                allowed = ", ".join(sorted(cls.ALLOWED_ROLES))
                raise ReviewerDecisionFillError(f"accept decision selected_role must be one of: {allowed}")
            cls._require_non_empty("selected_benefit_scope", selected_benefit_scope)
            if selected_band_scope is not None:
                cls._require_non_empty("selected_band_scope", selected_band_scope)
            return
        if any(value is not None for value in (selected_role, selected_benefit_scope, selected_band_scope)):
            raise ReviewerDecisionFillError("reject, split_further, and defer must not set selected role or scope")

    @classmethod
    def _document_status(cls, records: list[Mapping[str, Any]]) -> str:
        resolved_count = sum(
            1 for record in records
            if record.get("review_status") == ReviewerDecisionRecordContract.RESOLVED_STATUS
        )
        if resolved_count == 0:
            return cls.PENDING_DOCUMENT_STATUS
        if resolved_count == len(records):
            return cls.READY_FOR_SUBMISSION_STATUS
        return cls.IN_PROGRESS_DOCUMENT_STATUS

    @staticmethod
    def _require_non_empty(name: str, value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ReviewerDecisionFillError(f"{name} must be a non-empty string")

    @staticmethod
    def _with_fill_limitation(existing: Any) -> list[str]:
        items = list(existing) if isinstance(existing, list) else []
        note = (
            "This workflow resolves one pending reviewer decision at a time; it does not "
            "submit immutable decisions, create canonical facts, or publish policy information."
        )
        if note not in items:
            items.append(note)
        return items
