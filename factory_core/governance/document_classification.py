"""P2.5-F3 — document classification, privacy scope, and reuse policy.

This module is deliberately source-agnostic. It classifies reviewed documents
before they can be used as reusable evidence, and captures privacy-safe
knowledge-gap signals without retaining private clause text or identifiers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class DocumentClassificationError(ValueError):
    """Raised when a classification or knowledge-gap record is unsafe."""


CLASSIFICATIONS = frozenset({
    "reusable_generic",
    "restricted_policy_instance",
    "restricted_group_specific",
    "restricted_member_specific",
    "discovery_only",
    "unknown_requires_review",
})

REUSE_ACTIONS = frozenset({
    "reusable_evidence_candidate",
    "session_scoped_evidence_only",
    "group_scoped_evidence_only",
    "member_scoped_evidence_only",
    "discovery_only",
    "blocked_pending_review",
})

PRIVATE_CLASSIFICATIONS = frozenset({
    "restricted_policy_instance",
    "restricted_group_specific",
    "restricted_member_specific",
})

_ALLOWED_DOCUMENT_TYPES = frozenset({
    "policy_wording",
    "prospectus",
    "customer_information_sheet",
    "product_benefit_table",
    "brochure",
    "policy_schedule",
    "renewal_notice",
    "endorsement",
    "claim_document",
    "medical_record",
    "group_schedule",
    "member_certificate",
    "quote",
    "other",
})

_BLOCKED_GAP_KEYS = frozenset({
    "raw_clause_text", "excerpt", "policy_number", "member_id", "customer_name", "email", "phone", "address", "premium_amount"})


@dataclass(frozen=True)
class DocumentClassificationResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise DocumentClassificationError(f"{label} must be a JSON object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise DocumentClassificationError(f"{label} must be a JSON array")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocumentClassificationError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise DocumentClassificationError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(root: Path, relative_path: str, label: str) -> Mapping[str, Any]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DocumentClassificationError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise DocumentClassificationError(f"{label} was not found: {relative_path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DocumentClassificationError(f"{label} is not valid JSON: {relative_path}") from exc
    return _mapping(parsed, label)


def _expected_action(classification: str) -> str:
    return {
        "reusable_generic": "reusable_evidence_candidate",
        "restricted_policy_instance": "session_scoped_evidence_only",
        "restricted_group_specific": "group_scoped_evidence_only",
        "restricted_member_specific": "member_scoped_evidence_only",
        "discovery_only": "discovery_only",
        "unknown_requires_review": "blocked_pending_review",
    }[classification]


def _validate_document_class_pair(document_type: str, classification: str) -> None:
    generic_legal = {"policy_wording", "prospectus", "customer_information_sheet", "product_benefit_table"}
    private_types = {"policy_schedule", "renewal_notice", "endorsement", "claim_document", "medical_record", "group_schedule", "member_certificate", "quote"}
    if document_type in generic_legal and classification not in {"reusable_generic", "unknown_requires_review"}:
        raise DocumentClassificationError(f"{document_type} may only be reusable_generic or unknown_requires_review")
    if document_type == "brochure" and classification not in {"discovery_only", "unknown_requires_review"}:
        raise DocumentClassificationError("brochure may only be discovery_only or unknown_requires_review")
    if document_type in private_types and classification == "reusable_generic":
        raise DocumentClassificationError(f"{document_type} must never be classified reusable_generic")


class DocumentClassificationPolicy:
    """Creates reviewed, non-mutating document governance manifests."""

    def classify_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path) -> DocumentClassificationResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Classification specification was not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DocumentClassificationError(f"Invalid classification specification JSON: {path}") from exc
        return self.classify(spec=_mapping(raw, "classification_spec"), repository_root=repository_root)

    def classify(self, *, spec: Mapping[str, Any], repository_root: str | Path, classified_at: str | None = None) -> DocumentClassificationResult:
        root = Path(repository_root).resolve()
        spec = _mapping(spec, "classification_spec")
        if spec.get("schema_version") != "1.0":
            raise DocumentClassificationError("classification_spec.schema_version must be 1.0")
        if spec.get("classification_type") != "document_classification_reuse_policy_v1":
            raise DocumentClassificationError("classification_spec.classification_type must be document_classification_reuse_policy_v1")
        if spec.get("reviewed_by_human") is not True:
            raise DocumentClassificationError("classification_spec.reviewed_by_human must be true")

        documents = _list(spec.get("documents"), "classification_spec.documents")
        if not documents:
            raise DocumentClassificationError("classification_spec.documents must not be empty")
        seen_doc_ids: set[str] = set()
        classified: list[dict[str, Any]] = []
        for index, raw in enumerate(documents):
            item = _mapping(raw, f"documents[{index}]")
            registration_path = _safe_relative_path(item.get("registration_path"), f"documents[{index}].registration_path")
            registration = _load_json(root, registration_path, f"registration[{index}]")
            document = _mapping(registration.get("document"), f"registration[{index}].document")
            doc_id = _nonempty(document.get("document_id"), f"registration[{index}].document.document_id")
            if doc_id in seen_doc_ids:
                raise DocumentClassificationError("document_id values must be unique")
            seen_doc_ids.add(doc_id)
            document_type = _nonempty(document.get("document_type"), f"registration[{index}].document.document_type")
            if document_type not in _ALLOWED_DOCUMENT_TYPES:
                raise DocumentClassificationError(f"unsupported document_type {document_type!r}")
            classification = _nonempty(item.get("classification"), f"documents[{index}].classification")
            if classification not in CLASSIFICATIONS:
                raise DocumentClassificationError(f"unsupported classification {classification!r}")
            _validate_document_class_pair(document_type, classification)
            requested_action = _nonempty(item.get("reuse_action"), f"documents[{index}].reuse_action")
            if requested_action not in REUSE_ACTIONS:
                raise DocumentClassificationError(f"unsupported reuse_action {requested_action!r}")
            expected = _expected_action(classification)
            if requested_action != expected:
                raise DocumentClassificationError(f"reuse_action for {classification} must be {expected}")
            rationale = _nonempty(item.get("review_rationale"), f"documents[{index}].review_rationale")
            content_hash = _nonempty(document.get("content_sha256"), f"registration[{index}].document.content_sha256")
            version_id = _nonempty(document.get("document_version_id"), f"registration[{index}].document.document_version_id")
            classified.append({
                "document_id": doc_id,
                "document_version_id": version_id,
                "document_type": document_type,
                "content_sha256": content_hash,
                "registration_path": registration_path,
                "registration_sha256": _sha256_file((root / registration_path).resolve()),
                "classification": classification,
                "reuse_action": requested_action,
                "review_rationale": rationale,
                "private_source": classification in PRIVATE_CLASSIFICATIONS,
                "reusable_knowledge_eligible": classification == "reusable_generic",
            })

        manifest = {
            "schema_version": "1.0",
            "classification_type": "document_classification_reuse_policy_v1",
            "classification_status": "reviewed_document_classifications_recorded_not_published",
            "documents": classified,
            "knowledge_gap_policy": {
                "private_source_may_trigger_gap": True,
                "private_source_may_not_supply_reusable_evidence": True,
                "required_research_source_scope": "reusable_generic",
                "blocked_fields": sorted(_BLOCKED_GAP_KEYS),
                "publication_requires_reviewed_public_evidence": True,
            },
            "guardrails": [
                "Document classification is a reviewable policy decision and is hash-bound to the registered document version.",
                "Restricted policy-, group-, and member-specific documents are never reusable generic evidence.",
                "Discovery-only documents cannot establish a legal entitlement or reusable legal assertion on their own.",
                "Unknown documents remain blocked pending review.",
                "This manifest does not alter raw documents, extraction artifacts, rules, evidence bindings, or authority state.",
            ],
            "reviewed_by_human": True,
            "classified_at": classified_at or datetime.now(timezone.utc).isoformat(),
        }
        return DocumentClassificationResult(manifest=manifest)

    def write_output(self, result: DocumentClassificationResult, *, repository_root: str | Path, output_path: str | Path) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise DocumentClassificationError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    def capture_knowledge_gap(self, *, source_document_id: str, source_classification: str, gap: Mapping[str, Any]) -> Mapping[str, Any]:
        """Validate an anonymized research candidate; it never persists raw source text."""
        if source_classification not in CLASSIFICATIONS:
            raise DocumentClassificationError("source_classification is unsupported")
        payload = _mapping(gap, "knowledge_gap")
        if source_classification not in PRIVATE_CLASSIFICATIONS and source_classification != "unknown_requires_review":
            raise DocumentClassificationError("knowledge-gap capture is reserved for restricted or unknown source documents")
        blocked = sorted(set(payload).intersection(_BLOCKED_GAP_KEYS))
        if blocked:
            raise DocumentClassificationError("knowledge-gap payload contains blocked private fields: " + ", ".join(blocked))
        term = _nonempty(payload.get("normalized_term"), "knowledge_gap.normalized_term")
        context = _nonempty(payload.get("normalized_context"), "knowledge_gap.normalized_context")
        family = _nonempty(payload.get("product_family"), "knowledge_gap.product_family")
        return {
            "schema_version": "1.0",
            "record_type": "privacy_safe_knowledge_gap_candidate_v1",
            "status": "research_required_not_knowledge",
            "source_document_id": _nonempty(source_document_id, "source_document_id"),
            "source_classification": source_classification,
            "normalized_term": term,
            "normalized_context": context,
            "product_family": family,
            "research_source_scope_required": "reusable_generic",
            "publication_requires_reviewed_public_evidence": True,
        }
