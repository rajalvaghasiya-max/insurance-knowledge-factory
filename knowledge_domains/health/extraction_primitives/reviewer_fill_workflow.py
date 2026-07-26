"""Reviewer-fill workflow guidance for source-bound review decision records.

This module prepares a read-only worklist for human reviewers.  It is downstream
of pending reviewer-decision records and upstream of any decision entry,
submission, fact selection, entitlement, or publication.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from knowledge_domains.health.extraction_primitives.reviewer_decision_record import (
    ReviewerDecisionRecordContract,
    ReviewerDecisionRecordError,
)


class ReviewerFillWorkflowError(ValueError):
    """Raised when a reviewer-fill worklist cannot be built safely."""


class ReviewerFillWorkflow:
    """Build a deterministic, read-only human-review worklist."""

    VERSION = "1.0"
    DOCUMENT_TYPE = "health_reviewer_fill_worklist_document_v1"
    STATUS = "ready_for_human_review"
    NON_FACT_GUARDRAIL = "review_worklist_only_no_canonical_fact"
    ALLOWED_DECISIONS = ("accept", "reject", "split_further", "defer")
    ALLOWED_ROLES_FOR_ACCEPT = (
        "sum_insured",
        "sub_limit_or_limit",
        "deductible",
        "premium",
        "monetary_amount_unresolved",
    )

    @classmethod
    def build_worklist_document(cls, pending_decision_document: Mapping[str, Any]) -> dict[str, Any]:
        """Create a read-only worklist from a wholly pending D-2 decision document.

        The source document is not mutated.  This method intentionally does not
        accept decisions or create a completed decision document.
        """
        try:
            ReviewerDecisionRecordContract.validate_decision_document(pending_decision_document)
        except ReviewerDecisionRecordError as exc:
            raise ReviewerFillWorkflowError(str(exc)) from exc

        records = pending_decision_document.get("decision_records", [])
        if pending_decision_document.get("status") != "pending_human_review":
            raise ReviewerFillWorkflowError("worklist input must have status pending_human_review")
        if not records:
            raise ReviewerFillWorkflowError("worklist input must contain at least one pending decision record")
        non_pending = [r.get("decision_record_id") for r in records if r.get("review_status") != ReviewerDecisionRecordContract.PENDING_STATUS]
        if non_pending:
            raise ReviewerFillWorkflowError("worklist input must contain only pending decision records")

        items = [cls._build_item(record) for record in records]
        output = {
            "schema_version": "1.0",
            "workflow_document_type": cls.DOCUMENT_TYPE,
            "workflow_version": cls.VERSION,
            "status": cls.STATUS,
            "source": copy.deepcopy(dict(pending_decision_document["source"])),
            "input": {
                "decision_document_type": pending_decision_document["decision_document_type"],
                "decision_contract_version": pending_decision_document["decision_contract_version"],
                "input_decision_record_count": pending_decision_document["decision_record_count"],
            },
            "workflow_rules": {
                "allowed_decisions": list(cls.ALLOWED_DECISIONS),
                "accept_requires": [
                    "selected_role",
                    "selected_benefit_scope",
                    "review_rationale",
                    "reviewer_identity",
                    "reviewed_at",
                ],
                "non_accept_requires": ["review_rationale", "reviewer_identity", "reviewed_at"],
                "selected_band_scope_rule": "required only when the reviewer confirms a specific sum-insured band; otherwise leave null and explain why in the rationale.",
                "allowed_roles_for_accept": list(cls.ALLOWED_ROLES_FOR_ACCEPT),
                "source_binding_rule": "Review only the source SHA-256 and review-group snapshot embedded in each item. A changed source requires a new review workflow.",
                "publication_rule": "No review action creates, updates, or publishes a canonical fact.",
            },
            "work_item_count": len(items),
            "work_items": items,
            "non_fact_guardrail": cls.NON_FACT_GUARDRAIL,
            "limitations": [
                "This worklist guides human review only; it does not record decisions, create completed decision records, or submit immutable decisions.",
                "Scope and role hints are evidence-navigation aids, not legal interpretation or automatic applicability decisions.",
                "A reviewer must inspect the bounded source evidence and, where schedule/band binding is flagged, the original document layout before accepting a record.",
                "Fact selection, entitlement, currentness, policy schedule binding, and publication remain outside this workflow.",
            ],
        }
        cls.validate_worklist_document(output)
        return output

    @classmethod
    def validate_worklist_document(cls, document: Mapping[str, Any]) -> None:
        if not isinstance(document, Mapping):
            raise ReviewerFillWorkflowError("worklist document must be an object")
        if document.get("workflow_document_type") != cls.DOCUMENT_TYPE:
            raise ReviewerFillWorkflowError("unsupported workflow_document_type")
        if document.get("workflow_version") != cls.VERSION:
            raise ReviewerFillWorkflowError("unsupported workflow_version")
        if document.get("status") != cls.STATUS:
            raise ReviewerFillWorkflowError("worklist status must be ready_for_human_review")
        if document.get("non_fact_guardrail") != cls.NON_FACT_GUARDRAIL:
            raise ReviewerFillWorkflowError("worklist must block canonical fact creation")
        source = document.get("source")
        if not isinstance(source, Mapping) or not ReviewerDecisionRecordContract._valid_sha(source.get("sha256")):
            raise ReviewerFillWorkflowError("source.sha256 must be a valid SHA-256")
        rules = document.get("workflow_rules")
        if not isinstance(rules, Mapping) or rules.get("allowed_decisions") != list(cls.ALLOWED_DECISIONS):
            raise ReviewerFillWorkflowError("workflow_rules must expose the controlled decision set")
        items = document.get("work_items")
        if not isinstance(items, list) or not items:
            raise ReviewerFillWorkflowError("work_items must be a non-empty list")
        if document.get("work_item_count") != len(items):
            raise ReviewerFillWorkflowError("work_item_count must equal work_items length")
        ids: set[str] = set()
        for item in items:
            cls._validate_work_item(item, source["sha256"])
            if item["decision_record_id"] in ids:
                raise ReviewerFillWorkflowError("duplicate decision_record_id in work_items")
            ids.add(item["decision_record_id"])

    @classmethod
    def _build_item(cls, record: Mapping[str, Any]) -> dict[str, Any]:
        snapshot = copy.deepcopy(dict(record["review_group_snapshot"]))
        flags = list(snapshot.get("review_flags", []))
        return {
            "decision_record_id": record["decision_record_id"],
            "review_group_id": record["review_group_id"],
            "source_sha256": record["source_sha256"],
            "review_context": {
                "normalized_value": snapshot.get("normalized_value"),
                "inferred_scope": snapshot.get("inferred_scope"),
                "review_flags": flags,
                "observed_role_hints": copy.deepcopy(snapshot.get("observed_role_hints", [])),
                "condition_hints": copy.deepcopy(snapshot.get("condition_hints", [])),
                "bounded_evidence_identity": snapshot.get("bounded_evidence_identity"),
                "supporting_candidate_ids": snapshot.get("supporting_candidate_ids", []),
                # Exact page-level evidence is intentionally available to the
                # reviewer; no decision may rely on an amount-only summary.
                "bounded_evidence": copy.deepcopy(snapshot.get("bounded_evidence", [])),
            },
            "reviewer_checklist": cls._checklist(flags, snapshot),
            "decision_entry_contract": {
                "decision": "choose exactly one from: accept, reject, split_further, defer",
                "accept": {
                    "required": ["selected_role", "selected_benefit_scope", "review_rationale", "reviewer_identity", "reviewed_at"],
                    "optional": ["selected_band_scope"],
                },
                "reject_split_further_defer": {
                    "required": ["review_rationale", "reviewer_identity", "reviewed_at"],
                    "must_be_null": ["selected_role", "selected_benefit_scope", "selected_band_scope"],
                },
            },
            "non_fact_guardrail": cls.NON_FACT_GUARDRAIL,
        }

    @classmethod
    def _checklist(cls, flags: list[Any], snapshot: Mapping[str, Any]) -> list[str]:
        checklist = [
            "Inspect the original bounded source evidence for this exact review group.",
            "Confirm that the source SHA-256 matches the document being reviewed.",
            "Do not infer product-wide applicability from a single clause or amount.",
        ]
        flag_set = {flag for flag in flags if isinstance(flag, str)}
        if "schedule_or_band_binding_unverified" in flag_set:
            checklist.append("Inspect the original PDF layout/table and verify the amount-to-band binding before accepting.")
        if "possible_benefit_limit_despite_role_hint" in flag_set:
            checklist.append("Re-evaluate the monetary role against nearby benefit wording; do not accept a premium role merely from a distant keyword.")
        if "benefit_scope_unresolved" in flag_set:
            checklist.append("Use defer or split_further when benefit scope cannot be resolved from the governed evidence.")
        inferred_scope = snapshot.get("inferred_scope")
        if isinstance(inferred_scope, Mapping) and inferred_scope.get("scope_inference_requires_review"):
            checklist.append("Treat inferred benefit and band scope as a navigation hint, not an authoritative classification.")
        return checklist

    @classmethod
    def _validate_work_item(cls, item: Mapping[str, Any], source_sha256: str) -> None:
        if not isinstance(item, Mapping):
            raise ReviewerFillWorkflowError("work item must be an object")
        for key in ("decision_record_id", "review_group_id", "source_sha256", "non_fact_guardrail"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ReviewerFillWorkflowError(f"work item {key} must be a non-empty string")
        if item.get("source_sha256") != source_sha256:
            raise ReviewerFillWorkflowError("work item source_sha256 must match document source")
        if item.get("non_fact_guardrail") != cls.NON_FACT_GUARDRAIL:
            raise ReviewerFillWorkflowError("work item must block canonical fact creation")
        context = item.get("review_context")
        if not isinstance(context, Mapping) or not isinstance(context.get("normalized_value"), Mapping):
            raise ReviewerFillWorkflowError("work item requires normalized review context")
        if not isinstance(context.get("bounded_evidence"), list):
            raise ReviewerFillWorkflowError("work item bounded_evidence must be a list")
        checklist = item.get("reviewer_checklist")
        if not isinstance(checklist, list) or not checklist or not all(isinstance(entry, str) and entry.strip() for entry in checklist):
            raise ReviewerFillWorkflowError("work item reviewer_checklist must be a non-empty string list")
