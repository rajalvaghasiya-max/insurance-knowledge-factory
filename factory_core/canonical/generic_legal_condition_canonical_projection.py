"""P2.5-I — read-only canonical projection of reviewed generic legal conditions.

Projects P2.5-H1 binding manifests into Canonical Model v1 only when every cited
source is classified reusable_generic. This module deliberately does not publish
assertions and cannot create product entitlement values.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .legacy_conditional_rule_adapter import canonical_bundle_to_dict
from .models import (
    CanonicalBundle,
    DocumentVersion,
    EvidenceSpan,
    Insurer,
    KnowledgeAssertion,
    KnowledgeAssertionKind,
    ProductIdentity,
    ProductVersion,
    PublicationDecision,
    PublicationStatus,
    SourceDocument,
    ValidationStatus,
)
from .validation import validate_canonical_bundle


class GenericLegalConditionCanonicalProjectionError(ValueError):
    """Raised when a generic legal assertion cannot be projected safely."""


@dataclass(frozen=True)
class GenericLegalConditionCanonicalProjectionResult:
    bundle: CanonicalBundle
    report: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GenericLegalConditionCanonicalProjectionError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GenericLegalConditionCanonicalProjectionError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenericLegalConditionCanonicalProjectionError(f"{label} must be a non-empty string")
    return value.strip()


def _sha256_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]}"


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise GenericLegalConditionCanonicalProjectionError(
            f"{label} must be a safe repository-relative path"
        )
    return path.as_posix()


def _resolve(root: Path, relative_path: str, label: str) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise GenericLegalConditionCanonicalProjectionError(f"{label} must remain under repository_root") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"{label} was not found: {relative_path}")
    return candidate


def _load_json(root: Path, relative_path: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = _resolve(root, relative_path, label)
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GenericLegalConditionCanonicalProjectionError(f"{label} is not valid UTF-8 JSON") from exc
    return _mapping(data, label), _sha256_bytes(raw)


def _context(raw: object) -> Mapping[str, str | None]:
    value = _mapping(raw, "projection_spec.product_context")
    required = (
        "insurer_id", "insurer_legal_name", "product_id", "product_name",
        "domain", "product_version_id",
    )
    result: dict[str, str | None] = {key: _text(value.get(key), f"product_context.{key}") for key in required}
    for key in ("insurer_type", "product_version_label", "product_uin", "product_family_name"):
        raw_value = value.get(key)
        result[key] = None if raw_value is None else _text(raw_value, f"product_context.{key}")
    return result


def _candidate_map(registration: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    entries = _items(review.get("candidates"), "registration.evidence_review.candidates")
    result: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(entries):
        item = _mapping(raw, f"registration.evidence_review.candidates[{index}]")
        result[_text(item.get("candidate_id"), "candidate.candidate_id")] = item
    return result


class GenericLegalConditionCanonicalProjection:
    """Creates a separate, non-authoritative canonical projection."""

    def project_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path) -> GenericLegalConditionCanonicalProjectionResult:
        spec_file = Path(spec_path)
        if not spec_file.is_file():
            raise FileNotFoundError(f"Projection specification was not found: {spec_file}")
        try:
            spec = json.loads(spec_file.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GenericLegalConditionCanonicalProjectionError("Projection specification is not valid JSON") from exc
        return self.project(spec=_mapping(spec, "projection_spec"), repository_root=repository_root)

    def project(self, *, spec: Mapping[str, Any], repository_root: str | Path, projected_at: str | None = None) -> GenericLegalConditionCanonicalProjectionResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")
        if spec.get("schema_version") != "1.0":
            raise GenericLegalConditionCanonicalProjectionError("projection_spec.schema_version must be 1.0")
        if spec.get("projection_type") != "generic_legal_condition_canonical_projection_v1":
            raise GenericLegalConditionCanonicalProjectionError("projection_spec.projection_type is invalid")
        if spec.get("reviewed_by_human") is not True:
            raise GenericLegalConditionCanonicalProjectionError("projection_spec.reviewed_by_human must be true")

        context = _context(spec.get("product_context"))
        binding_path = _safe_relative_path(spec.get("binding_manifest_path"), "binding_manifest_path")
        classification_path = _safe_relative_path(spec.get("classification_manifest_path"), "classification_manifest_path")
        binding, binding_sha = _load_json(root, binding_path, "binding_manifest")
        classification, classification_sha = _load_json(root, classification_path, "classification_manifest")

        if binding.get("binding_type") != "generic_legal_condition_binding_v1":
            raise GenericLegalConditionCanonicalProjectionError("binding_manifest must be a P2.5-H1 binding")
        if binding.get("binding_status") != "reviewed_generic_legal_conditions_bound_not_published":
            raise GenericLegalConditionCanonicalProjectionError("binding_manifest is not a reviewed bound-not-published artifact")
        if classification.get("classification_status") != "reviewed_document_classifications_recorded_not_published":
            raise GenericLegalConditionCanonicalProjectionError("classification_manifest is not reviewed")

        classifications: dict[str, Mapping[str, Any]] = {}
        for index, raw in enumerate(_items(classification.get("documents"), "classification_manifest.documents")):
            entry = _mapping(raw, f"documents[{index}]")
            doc_id = _text(entry.get("document_id"), "classification.document_id")
            classifications[doc_id] = entry

        bundle_path = _safe_relative_path(binding.get("generic_source_bundle_path"), "binding_manifest.generic_source_bundle_path")
        bundle, bundle_sha = _load_json(root, bundle_path, "generic_source_bundle")
        if binding.get("generic_source_bundle_sha256") != bundle_sha:
            raise GenericLegalConditionCanonicalProjectionError("generic source bundle hash mismatch")
        product_context = _mapping(bundle.get("product_context"), "generic_source_bundle.product_context")
        for key in ("insurer_id", "product_id"):
            if product_context.get(key) != context[key]:
                raise GenericLegalConditionCanonicalProjectionError(f"product context mismatch for {key}")

        registrations: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
        for index, raw_source in enumerate(_items(bundle.get("sources"), "generic_source_bundle.sources")):
            source = _mapping(raw_source, f"sources[{index}]")
            doc_id = _text(source.get("document_id"), "source.document_id")
            reg_path = _safe_relative_path(source.get("registration_output_path"), "source.registration_output_path")
            registration, _ = _load_json(root, reg_path, f"registration[{doc_id}]")
            document = _mapping(registration.get("document"), f"registration[{doc_id}].document")
            if document.get("document_id") != doc_id or document.get("document_version_id") != source.get("document_version_id"):
                raise GenericLegalConditionCanonicalProjectionError(f"registration identity mismatch for {doc_id}")
            registrations[doc_id] = (source, registration)

        source_docs: dict[str, SourceDocument] = {}
        doc_versions: dict[str, DocumentVersion] = {}
        spans: dict[str, EvidenceSpan] = {}
        assertions: list[KnowledgeAssertion] = []
        decisions: list[PublicationDecision] = []
        bound_assertions = _items(binding.get("assertions"), "binding_manifest.assertions")
        if not bound_assertions:
            raise GenericLegalConditionCanonicalProjectionError("binding_manifest.assertions must not be empty")

        for index, raw_assertion in enumerate(bound_assertions):
            item = _mapping(raw_assertion, f"binding.assertions[{index}]")
            binding_assertion_id = _text(item.get("assertion_id"), "binding.assertion_id")
            assertion_type = _text(item.get("assertion_type"), "binding.assertion_type")
            semantic_key = _text(item.get("semantic_key"), "binding.semantic_key")
            statement = _text(item.get("reviewed_statement"), "binding.reviewed_statement")
            if item.get("publication_status") != "bound_not_published":
                raise GenericLegalConditionCanonicalProjectionError("only bound_not_published assertions may be projected")
            evidence_ids: list[str] = []
            primary_seen = 0
            for evidence_index, raw_evidence in enumerate(_items(item.get("evidence"), "binding.assertion.evidence")):
                evidence = _mapping(raw_evidence, f"binding.assertion.evidence[{evidence_index}]")
                doc_id = _text(evidence.get("document_id"), "binding.evidence.document_id")
                if doc_id not in registrations:
                    raise GenericLegalConditionCanonicalProjectionError(f"binding references an unregistered document: {doc_id}")
                classification_entry = classifications.get(doc_id)
                if classification_entry is None:
                    raise GenericLegalConditionCanonicalProjectionError(f"document classification is missing for {doc_id}")
                if classification_entry.get("classification") != "reusable_generic" or classification_entry.get("reuse_action") != "reusable_evidence_candidate":
                    raise GenericLegalConditionCanonicalProjectionError(f"document {doc_id} is not eligible for reusable canonical projection")
                source, registration = registrations[doc_id]
                if evidence.get("document_version_id") != source.get("document_version_id"):
                    raise GenericLegalConditionCanonicalProjectionError(f"document version mismatch in bound evidence for {doc_id}")
                authority_role = _text(evidence.get("authority_role"), "binding.evidence.authority_role")
                if authority_role == "primary_legal":
                    primary_seen += 1
                if authority_role == "discovery_only":
                    raise GenericLegalConditionCanonicalProjectionError("discovery-only evidence is not eligible")
                candidate_id = _text(evidence.get("candidate_id"), "binding.evidence.candidate_id")
                candidate = _candidate_map(registration).get(candidate_id)
                if candidate is None:
                    raise GenericLegalConditionCanonicalProjectionError(f"candidate missing from registration: {doc_id}:{candidate_id}")
                if candidate.get("text_sha256") != evidence.get("candidate_text_sha256"):
                    raise GenericLegalConditionCanonicalProjectionError(f"candidate text hash mismatch: {doc_id}:{candidate_id}")
                bound_range = _mapping(evidence.get("source_char_range"), "binding.evidence.source_char_range")
                candidate_range = _mapping(candidate.get("source_char_range"), "candidate.source_char_range")
                if bound_range != candidate_range:
                    raise GenericLegalConditionCanonicalProjectionError(f"candidate source range mismatch: {doc_id}:{candidate_id}")
                document = _mapping(registration.get("document"), "registration.document")
                source_document_id = _text(document.get("source_document_id"), "registration.document.source_document_id")
                source_docs.setdefault(source_document_id, SourceDocument(
                    source_document_id=source_document_id,
                    insurer_id=context["insurer_id"] or "",
                    document_type=_text(document.get("document_type"), "registration.document.document_type"),
                    canonical_title=_text(document.get("canonical_title"), "registration.document.canonical_title"),
                    product_version_id=context["product_version_id"],
                ))
                document_version_id = _text(document.get("document_version_id"), "registration.document.document_version_id")
                doc_versions.setdefault(document_version_id, DocumentVersion(
                    document_version_id=document_version_id,
                    source_document_id=source_document_id,
                    content_sha256=_text(document.get("content_sha256"), "registration.document.content_sha256"),
                    captured_at=_text(registration.get("registered_at"), "registration.registered_at"),
                    storage_locator=_text(document.get("storage_locator"), "registration.document.storage_locator"),
                ))
                extracted_text = _mapping(registration.get("extracted_text"), "registration.extracted_text")
                span_id = _stable_id("esp", document_version_id, candidate_id, str(candidate_range.get("start")), str(candidate_range.get("end")), _text(candidate.get("text_sha256"), "candidate.text_sha256"))
                spans.setdefault(span_id, EvidenceSpan(
                    evidence_span_id=span_id,
                    document_version_id=document_version_id,
                    source_char_start=int(candidate_range.get("start")),
                    source_char_end=int(candidate_range.get("end")),
                    text_sha256=_text(candidate.get("text_sha256"), "candidate.text_sha256"),
                    extraction_method=_text(extracted_text.get("extraction_method"), "registration.extracted_text.extraction_method"),
                    source_page=candidate.get("source_page"),
                ))
                evidence_ids.append(span_id)
            if primary_seen != 1:
                raise GenericLegalConditionCanonicalProjectionError(f"{binding_assertion_id} requires exactly one primary legal evidence span")
            canonical_assertion_id = _stable_id("ka", binding_assertion_id, binding_sha)
            assertions.append(KnowledgeAssertion(
                assertion_id=canonical_assertion_id,
                product_version_id=context["product_version_id"] or "",
                concept_id=semantic_key,
                assertion_kind=KnowledgeAssertionKind.CONDITIONAL_RULE,
                payload={
                    "rule_id": binding_assertion_id,
                    "rule_type": assertion_type,
                    "reviewed_statement": statement,
                    "source_binding_assertion_id": binding_assertion_id,
                    "scope": "reusable_generic_product_legal_condition",
                },
                evidence_span_ids=tuple(evidence_ids),
                validation_status=ValidationStatus.EVIDENCE_ASSEMBLED,
                publication_status=PublicationStatus.UNPUBLISHED,
                source_artifact_sha256=binding_sha,
            ))
            decisions.append(PublicationDecision(
                publication_decision_id=_stable_id("pd", canonical_assertion_id, "unpublished"),
                assertion_id=canonical_assertion_id,
                decision_status=PublicationStatus.UNPUBLISHED,
                decided_at=projected_at or datetime.now(timezone.utc).isoformat(),
                decision_reason="Projected from reviewed generic legal binding; publication authority has not been granted.",
                source_artifact_sha256=binding_sha,
            ))

        canonical = CanonicalBundle(
            insurers=(Insurer(context["insurer_id"] or "", context["insurer_legal_name"] or "", context["insurer_type"]),),
            product_identities=(ProductIdentity(context["product_id"] or "", context["insurer_id"] or "", context["domain"] or "", context["product_name"] or "", context["product_uin"], context["product_family_name"]),),
            product_versions=(ProductVersion(context["product_version_id"] or "", context["product_id"] or "", context["product_version_label"]),),
            source_documents=tuple(source_docs.values()),
            document_versions=tuple(doc_versions.values()),
            evidence_spans=tuple(spans.values()),
            assertions=tuple(assertions),
            publication_decisions=tuple(decisions),
        )
        validation = validate_canonical_bundle(canonical)
        report = {
            "schema_version": "1.0",
            "projection_type": "generic_legal_condition_canonical_projection_v1",
            "projection_status": "validated_read_only_canonical_projection_not_published",
            "binding_manifest_path": binding_path,
            "binding_manifest_sha256": binding_sha,
            "classification_manifest_path": classification_path,
            "classification_manifest_sha256": classification_sha,
            "generic_source_bundle_sha256": bundle_sha,
            "validation": validation,
            "guardrails": [
                "Only documents classified reusable_generic with reuse_action reusable_evidence_candidate may be projected.",
                "Discovery-only, restricted policy-instance, group-specific, unclassified, or hash-mismatched documents are rejected.",
                "All projected assertions remain unpublished and non-authoritative.",
                "This projection cannot create room-category, room-rent-limit, or ICU-limit entitlement values.",
                "The projection writes a separate derived artifact and does not modify source registrations, binding manifests, or conditional-rule artifacts.",
            ],
        }
        return GenericLegalConditionCanonicalProjectionResult(bundle=canonical, report=report)

    def write_output(self, result: GenericLegalConditionCanonicalProjectionResult, *, repository_root: str | Path, output_path: str | Path) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise GenericLegalConditionCanonicalProjectionError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "canonical_bundle": canonical_bundle_to_dict(result.bundle),
            "projection_report": dict(result.report),
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
