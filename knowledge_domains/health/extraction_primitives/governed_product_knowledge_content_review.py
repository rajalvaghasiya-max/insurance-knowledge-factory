"""P1.9B.1 governed product-knowledge content review submission.

This contract is intentionally non-publishing. It records human review
choices for authored governed product-knowledge package templates. It does
not create reusable knowledge, publish facts, evaluate entitlement, or answer
customer questions.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


class GovernedProductKnowledgeContentReviewError(ValueError):
    """Raised when package content review cannot be prepared or recorded."""


APPROVE_DECISION = "approve_for_reusable_knowledge_creation"
VALID_REVIEW_DECISIONS = {APPROVE_DECISION, "defer", "reject"}

REQUIRED_STRING_FIELDS = (
    "plain_language_explanation",
    "simple_example",
    "practical_implication",
)
REQUIRED_LIST_FIELDS = (
    "applicability_notes",
    "cautions_and_limitations",
    "user_answer_boundaries",
)


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GovernedProductKnowledgeContentReviewError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GovernedProductKnowledgeContentReviewError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedProductKnowledgeContentReviewError(f"{label} must be a non-empty string")
    return value.strip()


def _stable_id(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{sha256(raw).hexdigest()[:16]}"


def _content_readiness(content: Mapping[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    for field in REQUIRED_STRING_FIELDS:
        value = content.get(field)
        if not isinstance(value, str) or not value.strip():
            missing.append(field)
    for field in REQUIRED_LIST_FIELDS:
        value = content.get(field)
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
            missing.append(field)
    return {
        "status": "complete" if not missing else "incomplete",
        "missing_or_empty_fields": missing,
    }


def _validate_template_document(package_templates: Mapping[str, Any]) -> Mapping[str, Any]:
    doc = _mapping(package_templates, "package_templates")
    if doc.get("schema_version") != "1.0":
        raise GovernedProductKnowledgeContentReviewError("package_templates.schema_version must be 1.0")
    if doc.get("document_type") != "health_governed_product_knowledge_package_template_document_v1":
        raise GovernedProductKnowledgeContentReviewError("package_templates.document_type is invalid")
    if doc.get("status") != "governed_product_knowledge_package_templates_prepared_pending_human_content_review":
        raise GovernedProductKnowledgeContentReviewError("package templates are not pending human content review")
    if doc.get("non_publication_guardrail") != "template_only_no_reusable_knowledge_publication_entitlement_or_customer_answer":
        raise GovernedProductKnowledgeContentReviewError("package template guardrail is invalid")
    return doc


def _validate_package_template(package: Mapping[str, Any]) -> dict[str, Any]:
    package_key = _text(package.get("package_key"), "package.package_key")
    if package.get("content_review_status") != "pending_human_authoring_and_review":
        raise GovernedProductKnowledgeContentReviewError(f"{package_key} is not pending human content review")
    if package.get("reusable_knowledge_state") != "template_only_not_created":
        raise GovernedProductKnowledgeContentReviewError(f"{package_key} reusable knowledge state is invalid")
    if package.get("publication_state") != "not_published":
        raise GovernedProductKnowledgeContentReviewError(f"{package_key} publication state is invalid")
    if package.get("entitlement_state") != "not_evaluated":
        raise GovernedProductKnowledgeContentReviewError(f"{package_key} entitlement state is invalid")
    if package.get("non_publication_guardrail") != "package_template_only_no_reusable_knowledge_publication_or_entitlement":
        raise GovernedProductKnowledgeContentReviewError(f"{package_key} package guardrail is invalid")
    readiness = _content_readiness(_mapping(package.get("human_authored_content"), f"{package_key}.human_authored_content"))
    return {
        "package_key": package_key,
        "package_template_id": _text(package.get("package_template_id"), f"{package_key}.package_template_id"),
        "title": _text(package.get("title"), f"{package_key}.title"),
        "content_readiness": readiness,
        "source_fact_count": len(_items(package.get("source_facts"), f"{package_key}.source_facts")),
        "source_decision_count": len(_items(package.get("source_publication_decisions"), f"{package_key}.source_publication_decisions")),
        "source_evidence_count": len(_items(package.get("source_evidence"), f"{package_key}.source_evidence")),
    }


class GovernedProductKnowledgeContentReviewContract:
    """Builds and records non-publishing review submissions for authored package content."""

    @classmethod
    def build_review_template(
        cls,
        *,
        package_templates: Mapping[str, Any],
        prepared_by: str,
        prepared_at: str,
    ) -> dict[str, Any]:
        doc = _validate_template_document(package_templates)
        prepared_by = _text(prepared_by, "prepared_by")
        prepared_at = _text(prepared_at, "prepared_at")
        packages = [_mapping(item, "packages[]") for item in _items(doc.get("packages"), "package_templates.packages")]
        if not packages:
            raise GovernedProductKnowledgeContentReviewError("package template document has no packages")

        review_items: list[dict[str, Any]] = []
        complete_count = 0
        for package in packages:
            summary = _validate_package_template(package)
            if summary["content_readiness"]["status"] == "complete":
                complete_count += 1
            review_items.append({
                "content_review_item_id": _stable_id("gpkcritem", {
                    "template_document_id": doc.get("template_document_id"),
                    "package_template_id": summary["package_template_id"],
                    "package_key": summary["package_key"],
                }),
                **summary,
                "recommended_decision": APPROVE_DECISION if summary["content_readiness"]["status"] == "complete" else "defer",
                "reviewer_decision": "defer",
                "reviewer_rationale": "Pending human content review.",
                "reviewer_identity": "",
                "reviewed_at": "",
                "non_publication_guardrail": "content_review_template_item_only_no_reusable_knowledge_publication_or_entitlement",
            })

        payload_for_id = {
            "template_document_id": doc.get("template_document_id"),
            "source_publication_decision_submission_id": doc.get("source_publication_decision_submission_id"),
            "package_keys": [item["package_key"] for item in review_items],
        }
        return {
            "schema_version": "1.0",
            "document_type": "health_governed_product_knowledge_content_review_template_v1",
            "status": "content_review_template_prepared_pending_human_review",
            "content_review_template_id": _stable_id("gpkcrtmpl", payload_for_id),
            "prepared_by": prepared_by,
            "prepared_at": prepared_at,
            "source_package_template_document_id": _text(doc.get("template_document_id"), "package_templates.template_document_id"),
            "source_publication_review_packet_id": _text(doc.get("source_publication_review_packet_id"), "source_publication_review_packet_id"),
            "source_publication_decision_submission_id": _text(doc.get("source_publication_decision_submission_id"), "source_publication_decision_submission_id"),
            "package_count": len(review_items),
            "complete_content_package_count": complete_count,
            "review_items": review_items,
            "readiness": {
                "dependency_validation": "passed",
                "content_readiness": "complete" if complete_count == len(review_items) else "incomplete",
                "reusable_knowledge_creation": "blocked_until_human_content_review_submission",
            },
            "non_publication_guardrail": "content_review_template_only_no_reusable_knowledge_publication_entitlement_or_customer_answer",
            "limitations": [
                "This template records proposed content review decisions only.",
                "A later recorded submission is required before reusable product knowledge can be prepared.",
                "This artifact does not publish facts, create reusable knowledge, make customer-specific entitlement decisions, or answer users.",
            ],
        }

    @classmethod
    def record_review_submission(
        cls,
        *,
        package_templates: Mapping[str, Any],
        content_review_template: Mapping[str, Any],
        submitted_by: str,
        submitted_at: str,
    ) -> dict[str, Any]:
        package_doc = _validate_template_document(package_templates)
        review_template = _mapping(content_review_template, "content_review_template")
        submitted_by = _text(submitted_by, "submitted_by")
        submitted_at = _text(submitted_at, "submitted_at")

        if review_template.get("schema_version") != "1.0":
            raise GovernedProductKnowledgeContentReviewError("content_review_template.schema_version must be 1.0")
        if review_template.get("document_type") != "health_governed_product_knowledge_content_review_template_v1":
            raise GovernedProductKnowledgeContentReviewError("content_review_template.document_type is invalid")
        if review_template.get("status") != "content_review_template_prepared_pending_human_review":
            raise GovernedProductKnowledgeContentReviewError("content review template is not pending review")
        if review_template.get("source_package_template_document_id") != package_doc.get("template_document_id"):
            raise GovernedProductKnowledgeContentReviewError("content review template does not belong to the supplied package templates")
        if review_template.get("non_publication_guardrail") != "content_review_template_only_no_reusable_knowledge_publication_entitlement_or_customer_answer":
            raise GovernedProductKnowledgeContentReviewError("content review template guardrail is invalid")

        package_summaries = {
            _text(package.get("package_key"), "package.package_key"): _validate_package_template(_mapping(package, "package"))
            for package in _items(package_doc.get("packages"), "package_templates.packages")
        }
        review_items = [_mapping(item, "review_items[]") for item in _items(review_template.get("review_items"), "content_review_template.review_items")]
        if len(review_items) != len(package_summaries):
            raise GovernedProductKnowledgeContentReviewError("content review item count does not match package count")

        seen: set[str] = set()
        recorded_items: list[dict[str, Any]] = []
        decision_counts = {APPROVE_DECISION: 0, "defer": 0, "reject": 0}
        for item in review_items:
            package_key = _text(item.get("package_key"), "review_item.package_key")
            if package_key in seen:
                raise GovernedProductKnowledgeContentReviewError(f"duplicate review item for package: {package_key}")
            seen.add(package_key)
            package_summary = package_summaries.get(package_key)
            if package_summary is None:
                raise GovernedProductKnowledgeContentReviewError(f"review item references unknown package: {package_key}")

            decision = _text(item.get("reviewer_decision"), f"{package_key}.reviewer_decision")
            if decision not in VALID_REVIEW_DECISIONS:
                raise GovernedProductKnowledgeContentReviewError(f"{package_key} has invalid reviewer decision: {decision}")
            reviewer_identity = _text(item.get("reviewer_identity"), f"{package_key}.reviewer_identity")
            reviewed_at = _text(item.get("reviewed_at"), f"{package_key}.reviewed_at")
            rationale = _text(item.get("reviewer_rationale"), f"{package_key}.reviewer_rationale")

            if decision == APPROVE_DECISION and package_summary["content_readiness"]["status"] != "complete":
                missing = ", ".join(package_summary["content_readiness"]["missing_or_empty_fields"])
                raise GovernedProductKnowledgeContentReviewError(f"{package_key} cannot be approved with incomplete content: {missing}")

            decision_counts[decision] += 1
            recorded_items.append({
                "content_review_decision_id": _stable_id("gpkcrdec", {
                    "content_review_template_id": review_template.get("content_review_template_id"),
                    "package_key": package_key,
                    "decision": decision,
                    "reviewer_identity": reviewer_identity,
                    "reviewed_at": reviewed_at,
                }),
                "source_content_review_item_id": _text(item.get("content_review_item_id"), f"{package_key}.content_review_item_id"),
                "package_key": package_key,
                "package_template_id": package_summary["package_template_id"],
                "decision": decision,
                "reviewer_rationale": rationale,
                "reviewer_identity": reviewer_identity,
                "reviewed_at": reviewed_at,
                "content_readiness": package_summary["content_readiness"],
                "reusable_knowledge_state": "approved_for_creation_not_created" if decision == APPROVE_DECISION else "blocked",
                "publication_state": "not_published",
                "entitlement_state": "not_evaluated",
                "source_lineage": {
                    "source_package_template_document_id": package_doc.get("template_document_id"),
                    "source_content_review_template_id": review_template.get("content_review_template_id"),
                    "source_publication_review_packet_id": package_doc.get("source_publication_review_packet_id"),
                    "source_publication_decision_submission_id": package_doc.get("source_publication_decision_submission_id"),
                },
                "non_publication_guardrail": "content_review_decision_only_no_reusable_knowledge_publication_or_entitlement",
            })

        missing = sorted(set(package_summaries) - seen)
        if missing:
            raise GovernedProductKnowledgeContentReviewError(f"packages missing content review decision: {', '.join(missing)}")

        payload_for_id = {
            "content_review_template_id": review_template.get("content_review_template_id"),
            "source_package_template_document_id": package_doc.get("template_document_id"),
            "decision_counts": decision_counts,
        }
        return {
            "schema_version": "1.0",
            "document_type": "health_governed_product_knowledge_content_review_submission_v1",
            "status": "human_content_review_decisions_recorded_not_reusable_knowledge",
            "content_review_submission_id": _stable_id("gpkcrsub", payload_for_id),
            "submitted_by": submitted_by,
            "submitted_at": submitted_at,
            "source_package_template_document_id": _text(package_doc.get("template_document_id"), "package_templates.template_document_id"),
            "source_content_review_template_id": _text(review_template.get("content_review_template_id"), "content_review_template_id"),
            "source_publication_review_packet_id": package_doc.get("source_publication_review_packet_id"),
            "source_publication_decision_submission_id": package_doc.get("source_publication_decision_submission_id"),
            "submitted_decision_count": len(recorded_items),
            "decision_counts": decision_counts,
            "submitted_decisions": recorded_items,
            "readiness": {
                "approved_for_reusable_knowledge_creation_count": decision_counts[APPROVE_DECISION],
                "reusable_knowledge_creation": "allowed_for_approved_packages_but_not_performed_by_this_artifact"
                if decision_counts[APPROVE_DECISION] else "blocked_no_approved_packages",
            },
            "non_publication_guardrail": "content_review_submission_only_no_reusable_knowledge_publication_entitlement_or_customer_answer",
            "limitations": [
                "This artifact records human content review decisions only.",
                "Approved packages may be used by a later bounded step to create reusable governed product knowledge.",
                "This artifact itself does not create reusable knowledge, publish facts, evaluate entitlement, price a policy, assess a claim, or answer a customer.",
                "Deferred and rejected packages must remain blocked unless a later immutable review submission changes the decision.",
            ],
        }
