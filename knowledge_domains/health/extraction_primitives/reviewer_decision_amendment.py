"""Controlled amendment of completed reviewer-decision documents.

This workflow creates a new completed decision artifact with exactly one resolved
record amended. It never mutates the source artifact and remains upstream of
immutable submission, fact selection, entitlement, and publication.
"""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Mapping

from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
    ReviewerDecisionRecordError,
)


class ReviewerDecisionAmendmentError(ValueError):
    """Raised when a completed reviewer-decision document cannot be amended safely."""


class ReviewerDecisionAmendmentWorkflow:
    VERSION = "1.0"
    READY_FOR_SUBMISSION_STATUS = "ready_for_submission"
    ALLOWED_ROLES = {
        "sum_insured",
        "sub_limit_or_limit",
        "deductible",
        "premium",
        "monetary_amount_unresolved",
    }

    @classmethod
    def amend_resolved_record(
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
        """Copy a completed decision artifact and amend exactly one resolved decision.

        The review-group snapshot, source SHA, and record identity remain unchanged.
        A later immutable submission must reference the prior submission so the
        amendment becomes an explicit revision rather than an overwrite.
        """
        try:
            ReviewerDecisionRecordContract.validate_decision_document(decision_document)
        except ReviewerDecisionRecordError as exc:
            raise ReviewerDecisionAmendmentError(str(exc)) from exc

        if decision_document.get("status") != cls.READY_FOR_SUBMISSION_STATUS:
            raise ReviewerDecisionAmendmentError(
                "amendment input must have status ready_for_submission"
            )
        cls._require_non_empty("decision_record_id", decision_record_id)
        cls._require_non_empty("reviewer_identity", reviewer_identity)
        cls._require_non_empty("review_rationale", review_rationale)
        cls._validate_iso_timestamp(reviewed_at)
        cls._validate_requested_fields(
            decision=decision,
            selected_role=selected_role,
            selected_benefit_scope=selected_benefit_scope,
            selected_band_scope=selected_band_scope,
        )

        output = copy.deepcopy(dict(decision_document))
        records = output["decision_records"]
        matches = [
            index for index, record in enumerate(records)
            if isinstance(record, Mapping)
            and record.get("decision_record_id") == decision_record_id
        ]
        if len(matches) != 1:
            raise ReviewerDecisionAmendmentError(
                "decision_record_id must resolve to exactly one record"
            )

        index = matches[0]
        prior = dict(records[index])
        if prior.get("review_status") != ReviewerDecisionRecordContract.RESOLVED_STATUS:
            raise ReviewerDecisionAmendmentError(
                "only decision_recorded records can be amended"
            )

        amended = dict(prior)
        amended.update({
            "review_status": ReviewerDecisionRecordContract.RESOLVED_STATUS,
            "decision": decision,
            "selected_role": selected_role,
            "selected_benefit_scope": selected_benefit_scope,
            "selected_band_scope": selected_band_scope,
            "review_rationale": review_rationale.strip(),
            "reviewer_identity": reviewer_identity.strip(),
            "reviewed_at": reviewed_at,
        })
        try:
            ReviewerDecisionRecordContract.validate_decision_record(amended)
        except ReviewerDecisionRecordError as exc:
            raise ReviewerDecisionAmendmentError(str(exc)) from exc

        records[index] = amended
        history = list(output.get("decision_amendment_history", []))
        history.append({
            "amendment_workflow_version": cls.VERSION,
            "decision_record_id": decision_record_id,
            "prior_decision": prior.get("decision"),
            "prior_selected_role": prior.get("selected_role"),
            "prior_selected_benefit_scope": prior.get("selected_benefit_scope"),
            "prior_selected_band_scope": prior.get("selected_band_scope"),
            "prior_review_rationale": prior.get("review_rationale"),
            "prior_reviewer_identity": prior.get("reviewer_identity"),
            "prior_reviewed_at": prior.get("reviewed_at"),
            "amended_decision": decision,
            "amended_by": reviewer_identity.strip(),
            "amended_at": reviewed_at,
            "amendment_rationale": review_rationale.strip(),
            "source_sha256": prior.get("source_sha256"),
            "review_group_snapshot": copy.deepcopy(prior.get("review_group_snapshot")),
            "non_fact_guardrail": "review_decision_amendment_only_no_canonical_fact",
        })
        output["decision_amendment_history"] = history
        output["decision_amendment_workflow_version"] = cls.VERSION
        output["status"] = cls.READY_FOR_SUBMISSION_STATUS
        output["non_fact_guardrail"] = "review_decision_document_only_no_canonical_fact"
        limitations = list(output.get("limitations", []))
        note = (
            "This amendment workflow emits a new completed decision artifact with one "
            "source- and snapshot-bound decision revised; it does not submit immutable "
            "decisions, create canonical facts, or publish policy information."
        )
        if note not in limitations:
            limitations.append(note)
        output["limitations"] = limitations

        try:
            ReviewerDecisionRecordContract.validate_decision_document(output)
        except ReviewerDecisionRecordError as exc:
            raise ReviewerDecisionAmendmentError(str(exc)) from exc
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
        if decision not in ReviewerDecisionRecordContract.ALLOWED_DECISIONS:
            raise ReviewerDecisionAmendmentError(
                "decision must be accept, reject, split_further, or defer"
            )
        if decision == "accept":
            if selected_role not in cls.ALLOWED_ROLES:
                allowed = ", ".join(sorted(cls.ALLOWED_ROLES))
                raise ReviewerDecisionAmendmentError(
                    f"accept decision selected_role must be one of: {allowed}"
                )
            cls._require_non_empty("selected_benefit_scope", selected_benefit_scope)
            if selected_band_scope is not None:
                cls._require_non_empty("selected_band_scope", selected_band_scope)
            return
        if any(value is not None for value in (
            selected_role, selected_benefit_scope, selected_band_scope
        )):
            raise ReviewerDecisionAmendmentError(
                "reject, split_further, and defer must not set selected role or scope"
            )

    @staticmethod
    def _require_non_empty(name: str, value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ReviewerDecisionAmendmentError(f"{name} must be a non-empty string")

    @staticmethod
    def _validate_iso_timestamp(value: str) -> None:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReviewerDecisionAmendmentError(
                "reviewed_at must be ISO-8601"
            ) from exc
