"""P1.9C governed reusable product-knowledge records.

This contract converts only content-reviewed and approved package templates
into reusable governed product-knowledge records. It remains non-publishing:
no customer-specific entitlement, no claim assessment, no pricing conclusion,
and no direct customer answer is produced by this artifact.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


class GovernedReusableProductKnowledgeRecordError(ValueError):
    """Raised when reusable product knowledge records cannot be created."""


APPROVE_DECISION = "approve_for_reusable_knowledge_creation"
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
        raise GovernedReusableProductKnowledgeRecordError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GovernedReusableProductKnowledgeRecordError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedReusableProductKnowledgeRecordError(f"{label} must be a non-empty string")
    return value.strip()


def _stable_id(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{sha256(raw).hexdigest()[:16]}"


def _validate_human_content(content: Mapping[str, Any], package_key: str) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for field in REQUIRED_STRING_FIELDS:
        clean[field] = _text(content.get(field), f"{package_key}.human_authored_content.{field}")
    for field in REQUIRED_LIST_FIELDS:
        values = _items(content.get(field), f"{package_key}.human_authored_content.{field}")
        if not values:
            raise GovernedReusableProductKnowledgeRecordError(f"{package_key}.{field} must not be empty")
        clean[field] = [_text(value, f"{package_key}.{field}[]") for value in values]
    return clean


def _validate_package_template_document(package_templates: Mapping[str, Any]) -> Mapping[str, Any]:
    doc = _mapping(package_templates, "package_templates")
    if doc.get("schema_version") != "1.0":
        raise GovernedReusableProductKnowledgeRecordError("package_templates.schema_version must be 1.0")
    if doc.get("document_type") != "health_governed_product_knowledge_package_template_document_v1":
        raise GovernedReusableProductKnowledgeRecordError("package_templates.document_type is invalid")
    if doc.get("status") != "governed_product_knowledge_package_templates_prepared_pending_human_content_review":
        raise GovernedReusableProductKnowledgeRecordError("package templates are not in expected pending-review state")
    if doc.get("non_publication_guardrail") != "template_only_no_reusable_knowledge_publication_entitlement_or_customer_answer":
        raise GovernedReusableProductKnowledgeRecordError("package template document guardrail is invalid")
    return doc


def _validate_content_review_submission(content_review_submission: Mapping[str, Any], package_doc: Mapping[str, Any]) -> Mapping[str, Any]:
    doc = _mapping(content_review_submission, "content_review_submission")
    if doc.get("schema_version") != "1.0":
        raise GovernedReusableProductKnowledgeRecordError("content_review_submission.schema_version must be 1.0")
    if doc.get("document_type") != "health_governed_product_knowledge_content_review_submission_v1":
        raise GovernedReusableProductKnowledgeRecordError("content_review_submission.document_type is invalid")
    if doc.get("status") != "human_content_review_decisions_recorded_not_reusable_knowledge":
        raise GovernedReusableProductKnowledgeRecordError("content review submission is not in expected recorded state")
    if doc.get("source_package_template_document_id") != package_doc.get("template_document_id"):
        raise GovernedReusableProductKnowledgeRecordError("content review submission does not belong to supplied package templates")
    if doc.get("non_publication_guardrail") != "content_review_submission_only_no_reusable_knowledge_publication_entitlement_or_customer_answer":
        raise GovernedReusableProductKnowledgeRecordError("content review submission guardrail is invalid")
    return doc


def _validate_source_facts(value: object, package_key: str) -> list[Any]:
    facts = _items(value, f"{package_key}.source_facts")
    if not facts:
        raise GovernedReusableProductKnowledgeRecordError(f"{package_key}.source_facts must not be empty")
    validated: list[Any] = []
    for index, fact in enumerate(facts):
        entry = _mapping(fact, f"{package_key}.source_facts[{index}]")
        _text(entry.get("governed_fact_id"), f"{package_key}.source_facts[{index}].governed_fact_id")
        validated.append(entry)
    return validated


def _validate_source_evidence(value: object, package_key: str) -> list[Any]:
    evidence = _items(value, f"{package_key}.source_evidence")
    if not evidence:
        raise GovernedReusableProductKnowledgeRecordError(f"{package_key}.source_evidence must not be empty")
    validated: list[Any] = []
    for index, item in enumerate(evidence):
        entry = _mapping(item, f"{package_key}.source_evidence[{index}]")
        _text(entry.get("bounded_evidence_identity"), f"{package_key}.source_evidence[{index}].bounded_evidence_identity")
        validated.append(entry)
    return validated


def _validate_package_template(package: Mapping[str, Any]) -> dict[str, Any]:
    package_key = _text(package.get("package_key"), "package.package_key")
    if package.get("content_review_status") != "pending_human_authoring_and_review":
        raise GovernedReusableProductKnowledgeRecordError(f"{package_key} content review status is invalid")
    if package.get("reusable_knowledge_state") != "template_only_not_created":
        raise GovernedReusableProductKnowledgeRecordError(f"{package_key} reusable knowledge state is invalid")
    if package.get("publication_state") != "not_published":
        raise GovernedReusableProductKnowledgeRecordError(f"{package_key} publication state is invalid")
    if package.get("entitlement_state") != "not_evaluated":
        raise GovernedReusableProductKnowledgeRecordError(f"{package_key} entitlement state is invalid")
    if package.get("non_publication_guardrail") != "package_template_only_no_reusable_knowledge_publication_or_entitlement":
        raise GovernedReusableProductKnowledgeRecordError(f"{package_key} package guardrail is invalid")
    return {
        "package_key": package_key,
        "package_template_id": _text(package.get("package_template_id"), f"{package_key}.package_template_id"),
        "title": _text(package.get("title"), f"{package_key}.title"),
        "package_intent": _text(package.get("package_intent"), f"{package_key}.package_intent"),
        "human_reviewed_content": _validate_human_content(_mapping(package.get("human_authored_content"), f"{package_key}.human_authored_content"), package_key),
        "source_facts": _validate_source_facts(package.get("source_facts"), package_key),
        "source_publication_decisions": list(_items(package.get("source_publication_decisions"), f"{package_key}.source_publication_decisions")),
        "source_evidence": _validate_source_evidence(package.get("source_evidence"), package_key),
    }


class GovernedReusableProductKnowledgeRecordContract:
    """Creates non-publishing reusable governed product-knowledge records."""

    @classmethod
    def create_records(
        cls,
        *,
        package_templates: Mapping[str, Any],
        content_review_submission: Mapping[str, Any],
        created_by: str,
        created_at: str,
    ) -> dict[str, Any]:
        package_doc = _validate_package_template_document(package_templates)
        review_doc = _validate_content_review_submission(content_review_submission, package_doc)
        created_by = _text(created_by, "created_by")
        created_at = _text(created_at, "created_at")

        package_by_key: dict[str, dict[str, Any]] = {}
        for item in _items(package_doc.get("packages"), "package_templates.packages"):
            validated_package = _validate_package_template(_mapping(item, "packages[]"))
            package_key = validated_package["package_key"]
            if package_key in package_by_key:
                raise GovernedReusableProductKnowledgeRecordError(
                    f"duplicate package_key in package_templates.packages: {package_key}"
                )
            package_by_key[package_key] = validated_package
        if not package_by_key:
            raise GovernedReusableProductKnowledgeRecordError("no package templates available")

        decisions = [_mapping(item, "submitted_decisions[]") for item in _items(review_doc.get("submitted_decisions"), "content_review_submission.submitted_decisions")]
        approved_decisions: list[Mapping[str, Any]] = []
        for decision in decisions:
            package_key = _text(decision.get("package_key"), "decision.package_key")
            if package_key not in package_by_key:
                raise GovernedReusableProductKnowledgeRecordError(f"review decision references unknown package: {package_key}")
            if decision.get("decision") != APPROVE_DECISION:
                continue
            if decision.get("reusable_knowledge_state") != "approved_for_creation_not_created":
                raise GovernedReusableProductKnowledgeRecordError(f"{package_key} approval state is invalid")
            if decision.get("publication_state") != "not_published" or decision.get("entitlement_state") != "not_evaluated":
                raise GovernedReusableProductKnowledgeRecordError(f"{package_key} decision has invalid non-publication states")
            if decision.get("non_publication_guardrail") != "content_review_decision_only_no_reusable_knowledge_publication_or_entitlement":
                raise GovernedReusableProductKnowledgeRecordError(f"{package_key} decision guardrail is invalid")
            approved_decisions.append(decision)

        if not approved_decisions:
            raise GovernedReusableProductKnowledgeRecordError("no approved package content decisions available")

        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for decision in approved_decisions:
            package_key = _text(decision.get("package_key"), "decision.package_key")
            if package_key in seen:
                raise GovernedReusableProductKnowledgeRecordError(f"duplicate approved decision for package: {package_key}")
            seen.add(package_key)
            package = package_by_key[package_key]
            if decision.get("package_template_id") != package["package_template_id"]:
                raise GovernedReusableProductKnowledgeRecordError(f"{package_key} package template id mismatch")
            payload_for_record_id = {
                "source_package_template_document_id": package_doc.get("template_document_id"),
                "source_content_review_submission_id": review_doc.get("content_review_submission_id"),
                "package_key": package_key,
                "content_review_decision_id": decision.get("content_review_decision_id"),
            }
            records.append({
                "reusable_knowledge_record_id": _stable_id("gpkrec", payload_for_record_id),
                "record_type": "governed_reusable_product_knowledge_record_v1",
                "package_key": package_key,
                "title": package["title"],
                "package_intent": package["package_intent"],
                "product_knowledge_scope": "health_product_package_explanation",
                "human_reviewed_content": package["human_reviewed_content"],
                "source_facts": package["source_facts"],
                "source_publication_decisions": package["source_publication_decisions"],
                "source_evidence": package["source_evidence"],
                "source_content_review_decision": {
                    "content_review_decision_id": _text(decision.get("content_review_decision_id"), f"{package_key}.content_review_decision_id"),
                    "decision": APPROVE_DECISION,
                    "reviewer_rationale": _text(decision.get("reviewer_rationale"), f"{package_key}.reviewer_rationale"),
                    "reviewer_identity": _text(decision.get("reviewer_identity"), f"{package_key}.reviewer_identity"),
                    "reviewed_at": _text(decision.get("reviewed_at"), f"{package_key}.reviewed_at"),
                },
                "reusable_knowledge_state": "created_as_governed_reusable_product_knowledge",
                "publication_state": "not_published",
                "entitlement_state": "not_evaluated",
                "customer_answer_state": "not_created",
                "source_lineage": {
                    "source_package_template_document_id": package_doc.get("template_document_id"),
                    "source_content_review_submission_id": review_doc.get("content_review_submission_id"),
                    "source_publication_review_packet_id": package_doc.get("source_publication_review_packet_id"),
                    "source_publication_decision_submission_id": package_doc.get("source_publication_decision_submission_id"),
                },
                "non_publication_guardrail": "reusable_product_knowledge_record_no_publication_entitlement_or_customer_answer",
            })

        records.sort(key=lambda record: record["package_key"])

        payload_for_document_id = {
            "source_package_template_document_id": package_doc.get("template_document_id"),
            "source_content_review_submission_id": review_doc.get("content_review_submission_id"),
            "record_keys": [record["package_key"] for record in records],
        }
        return {
            "schema_version": "1.0",
            "document_type": "health_governed_reusable_product_knowledge_records_document_v1",
            "status": "governed_reusable_product_knowledge_records_created_not_published",
            "record_document_id": _stable_id("gpkdoc", payload_for_document_id),
            "created_by": created_by,
            "created_at": created_at,
            "source_package_template_document_id": _text(package_doc.get("template_document_id"), "package_templates.template_document_id"),
            "source_content_review_submission_id": _text(review_doc.get("content_review_submission_id"), "content_review_submission_id"),
            "source_publication_review_packet_id": package_doc.get("source_publication_review_packet_id"),
            "source_publication_decision_submission_id": package_doc.get("source_publication_decision_submission_id"),
            "approved_package_count": len(approved_decisions),
            "record_count": len(records),
            "records": records,
            "readiness": {
                "dependency_validation": "passed",
                "reusable_product_knowledge_records": "created",
                "publication": "not_published",
                "entitlement": "not_evaluated",
                "customer_answer": "not_created",
            },
            "non_publication_guardrail": "reusable_product_knowledge_records_only_no_publication_entitlement_or_customer_answer",
            "limitations": [
                "Records are created only from packages approved_for_reusable_knowledge_creation.",
                "These records are reusable governed product knowledge, but they are not legal publication artifacts.",
                "These records do not determine customer-specific entitlement, pricing, claim admissibility, or recommendation suitability.",
                "Customer answers must use a later answer-routing step that combines these records with customer-specific policy schedule or uploaded document evidence when required.",
            ],
        }
