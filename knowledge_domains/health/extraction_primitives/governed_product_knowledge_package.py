"""P1.9B governed reusable product-knowledge package templates.

This contract is intentionally non-publishing. It converts only approved
publication-review packet items into package templates that still require
human-authored explanation/example/cautions and later content approval.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping


class GovernedProductKnowledgePackageError(ValueError):
    """Raised when a governed product-knowledge package cannot be prepared."""


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GovernedProductKnowledgePackageError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GovernedProductKnowledgePackageError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedProductKnowledgePackageError(f"{label} must be a non-empty string")
    return value.strip()


def _stable_id(prefix: str, payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return f"{prefix}_{sha256(raw).hexdigest()[:16]}"


def _copy_packet_fact(packet_item: Mapping[str, Any]) -> dict[str, Any]:
    fact = _mapping(packet_item.get("canonical_fact"), "packet_item.canonical_fact")
    return {
        "packet_item_id": _text(packet_item.get("packet_item_id"), "packet_item.packet_item_id"),
        "canonical_fact_id": _text(fact.get("canonical_fact_id"), "canonical_fact.canonical_fact_id"),
        "governed_fact_id": _text(fact.get("governed_fact_id"), "canonical_fact.governed_fact_id"),
        "canonical_field_key": _text(fact.get("canonical_field_key"), "canonical_fact.canonical_field_key"),
        "benefit_scope": _text(fact.get("benefit_scope"), "canonical_fact.benefit_scope"),
        "normalized_value": _mapping(fact.get("normalized_value"), "canonical_fact.normalized_value"),
        "applicability": _mapping(fact.get("applicability"), "canonical_fact.applicability"),
        "source_document": _mapping(fact.get("source_document"), "canonical_fact.source_document"),
    }


def _copy_evidence(packet_item: Mapping[str, Any]) -> dict[str, Any]:
    bounded = _mapping(packet_item.get("bounded_evidence"), "packet_item.bounded_evidence")
    return {
        "bounded_evidence_identity": _text(bounded.get("bounded_evidence_identity"), "bounded_evidence_identity"),
        "supporting_pages": list(_items(bounded.get("supporting_pages"), "bounded_evidence.supporting_pages")),
        "evidence_items": list(_items(bounded.get("evidence_items"), "bounded_evidence.evidence_items")),
    }


class GovernedProductKnowledgePackageContract:
    """Builds non-publishing product-knowledge package templates from approved facts."""

    @classmethod
    def build_template(
        cls,
        *,
        publication_review_packet: Mapping[str, Any],
        publication_decision_submission: Mapping[str, Any],
        package_spec: Mapping[str, Any],
        prepared_by: str,
        prepared_at: str,
    ) -> dict[str, Any]:
        packet = _mapping(publication_review_packet, "publication_review_packet")
        submission = _mapping(publication_decision_submission, "publication_decision_submission")
        spec = _mapping(package_spec, "package_spec")
        prepared_by = _text(prepared_by, "prepared_by")
        prepared_at = _text(prepared_at, "prepared_at")

        if packet.get("schema_version") != "1.0":
            raise GovernedProductKnowledgePackageError("publication_review_packet.schema_version must be 1.0")
        if packet.get("status") != "publication_review_packet_prepared_pending_human_review":
            raise GovernedProductKnowledgePackageError("publication review packet is not in the expected prepared state")
        if packet.get("non_publication_guardrail") != "review_packet_only_no_approval_publication_or_reusable_knowledge":
            raise GovernedProductKnowledgePackageError("publication review packet guardrail is invalid")
        packet_id = _text(packet.get("publication_review_packet_id"), "publication_review_packet_id")

        if submission.get("schema_version") != "1.0":
            raise GovernedProductKnowledgePackageError("decision_submission.schema_version must be 1.0")
        if submission.get("status") != "human_publication_review_decisions_recorded_not_published":
            raise GovernedProductKnowledgePackageError("decision submission is not a recorded non-publishing review")
        if submission.get("source_publication_review_packet_id") != packet_id:
            raise GovernedProductKnowledgePackageError("decision submission does not belong to the supplied packet")
        if submission.get("non_publication_guardrail") != "decision_submission_only_no_publication_reusable_knowledge_or_entitlement":
            raise GovernedProductKnowledgePackageError("decision submission guardrail is invalid")

        if spec.get("schema_version") != "1.0":
            raise GovernedProductKnowledgePackageError("package_spec.schema_version must be 1.0")
        if spec.get("spec_type") != "health_governed_product_knowledge_package_template_spec_v1":
            raise GovernedProductKnowledgePackageError("package_spec.spec_type is invalid")

        packet_items = {
            _text(item.get("packet_item_id"), "packet_item.packet_item_id"): _mapping(item, "packet_item")
            for item in _items(packet.get("packet_items"), "publication_review_packet.packet_items")
        }
        decisions = {
            _text(item.get("packet_item_id"), "submitted_decision.packet_item_id"): _mapping(item, "submitted_decision")
            for item in _items(submission.get("submitted_decisions"), "decision_submission.submitted_decisions")
        }
        approved_ids = {
            packet_item_id
            for packet_item_id, decision in decisions.items()
            if decision.get("decision") == "approve_for_governed_publication"
        }
        if not approved_ids:
            raise GovernedProductKnowledgePackageError("no approved decisions available for package template")

        package_defs = _items(spec.get("packages"), "package_spec.packages")
        seen: set[str] = set()
        packages: list[dict[str, Any]] = []
        for raw_package in package_defs:
            package_def = _mapping(raw_package, "package_spec.packages[]")
            package_key = _text(package_def.get("package_key"), "package.package_key")
            title = _text(package_def.get("title"), "package.title")
            package_item_ids = [_text(item, "package.packet_item_ids[]") for item in _items(package_def.get("packet_item_ids"), "package.packet_item_ids")]
            if not package_item_ids:
                raise GovernedProductKnowledgePackageError(f"{package_key} must include at least one packet item")
            if len(package_item_ids) != len(set(package_item_ids)):
                raise GovernedProductKnowledgePackageError(f"{package_key} has duplicate packet_item_ids")
            source_facts: list[dict[str, Any]] = []
            source_evidence: list[dict[str, Any]] = []
            source_decisions: list[dict[str, Any]] = []
            for packet_item_id in package_item_ids:
                if packet_item_id in seen:
                    raise GovernedProductKnowledgePackageError(f"approved packet item appears in multiple packages: {packet_item_id}")
                packet_item = packet_items.get(packet_item_id)
                if packet_item is None:
                    raise GovernedProductKnowledgePackageError(f"package packet item is missing from packet: {packet_item_id}")
                decision = decisions.get(packet_item_id)
                if decision is None:
                    raise GovernedProductKnowledgePackageError(f"package packet item is missing from decision submission: {packet_item_id}")
                if decision.get("decision") != "approve_for_governed_publication":
                    raise GovernedProductKnowledgePackageError(f"package packet item is not approved: {packet_item_id}")
                if decision.get("publication_state") != "not_published" or decision.get("entitlement_state") != "not_evaluated":
                    raise GovernedProductKnowledgePackageError(f"approved item has invalid non-publication states: {packet_item_id}")
                if decision.get("reusable_knowledge_state") != "not_created":
                    raise GovernedProductKnowledgePackageError(f"approved item already has reusable knowledge state: {packet_item_id}")
                seen.add(packet_item_id)
                source_facts.append(_copy_packet_fact(packet_item))
                source_evidence.append({"packet_item_id": packet_item_id, **_copy_evidence(packet_item)})
                source_decisions.append({
                    "packet_item_id": packet_item_id,
                    "publication_review_decision_id": _text(decision.get("publication_review_decision_id"), "publication_review_decision_id"),
                    "decision": "approve_for_governed_publication",
                    "rationale": _text(decision.get("rationale"), "decision.rationale"),
                    "reviewer_identity": _text(decision.get("reviewer_identity"), "decision.reviewer_identity"),
                    "reviewed_at": _text(decision.get("reviewed_at"), "decision.reviewed_at"),
                    "source_packet_lineage": _mapping(decision.get("source_packet_lineage"), "decision.source_packet_lineage"),
                })
            payload_for_id = {
                "packet_id": packet_id,
                "decision_submission_id": submission.get("submission_id"),
                "package_key": package_key,
                "packet_item_ids": package_item_ids,
            }
            packages.append({
                "package_template_id": _stable_id("gpkpt", payload_for_id),
                "package_key": package_key,
                "title": title,
                "package_intent": _text(package_def.get("package_intent"), "package.package_intent"),
                "source_facts": source_facts,
                "source_publication_decisions": source_decisions,
                "source_evidence": source_evidence,
                "human_authored_content": {
                    "plain_language_explanation": "",
                    "simple_example": "",
                    "practical_implication": "",
                    "applicability_notes": [],
                    "cautions_and_limitations": [],
                    "user_answer_boundaries": [],
                },
                "content_review_status": "pending_human_authoring_and_review",
                "reusable_knowledge_state": "template_only_not_created",
                "publication_state": "not_published",
                "entitlement_state": "not_evaluated",
                "non_publication_guardrail": "package_template_only_no_reusable_knowledge_publication_or_entitlement",
            })

        missing = sorted(approved_ids - seen)
        if missing:
            raise GovernedProductKnowledgePackageError(f"approved packet items not covered by package spec: {', '.join(missing)}")
        extra = sorted(seen - approved_ids)
        if extra:
            raise GovernedProductKnowledgePackageError(f"package spec includes non-approved packet items: {', '.join(extra)}")

        output_payload = {
            "packet_id": packet_id,
            "decision_submission_id": submission.get("submission_id"),
            "package_keys": [pkg["package_key"] for pkg in packages],
            "approved_packet_item_count": len(approved_ids),
        }
        return {
            "schema_version": "1.0",
            "document_type": "health_governed_product_knowledge_package_template_document_v1",
            "status": "governed_product_knowledge_package_templates_prepared_pending_human_content_review",
            "template_document_id": _stable_id("gpkptdoc", output_payload),
            "prepared_by": prepared_by,
            "prepared_at": prepared_at,
            "source_publication_review_packet_id": packet_id,
            "source_publication_review_packet_sha256": submission.get("source_publication_review_packet_sha256"),
            "source_publication_decision_submission_id": _text(submission.get("submission_id"), "decision_submission.submission_id"),
            "approved_packet_item_count": len(approved_ids),
            "package_count": len(packages),
            "packages": packages,
            "readiness": {
                "dependency_validation": "passed",
                "content_readiness": "pending_human_authored_explanation_example_implication_cautions",
                "reusable_knowledge_creation": "blocked_until_content_review",
            },
            "non_publication_guardrail": "template_only_no_reusable_knowledge_publication_entitlement_or_customer_answer",
            "limitations": [
                "Templates are generated only from approve_for_governed_publication decisions.",
                "Human-authored explanations, examples, implications, applicability notes, and cautions must be filled and reviewed before reusable product knowledge is created.",
                "This artifact does not publish facts or make customer-specific entitlement decisions.",
                "Deferred and rejected publication-review items are excluded from all packages.",
            ],
        }
