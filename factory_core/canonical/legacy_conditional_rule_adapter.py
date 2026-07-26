"""Read-only projection of published conditional-rule artifacts into Canonical Model v1.

P2.5-C does not migrate or rewrite legacy artifacts.  It creates a separate,
validated canonical projection only when a lineage manifest binds every cited
legacy evidence record to an immutable document version and text-span hash.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

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


class LegacyConditionalRuleProjectionError(ValueError):
    """Raised when legacy artifacts cannot be projected truthfully."""


@dataclass(frozen=True)
class CanonicalProductContext:
    """Explicit identity context required for a legacy projection.

    A legacy conditional-rule artifact provides an ``entity_id`` but does not
    establish product-version identity or insurer legal name.  The caller must
    provide those values explicitly rather than allowing this adapter to guess.
    """

    insurer_id: str
    insurer_legal_name: str
    insurer_type: str | None
    product_id: str
    product_name: str
    domain: str
    product_version_id: str
    product_version_label: str | None = None
    product_uin: str | None = None
    product_family_name: str | None = None


@dataclass(frozen=True)
class CanonicalProjection:
    """Validated canonical projection and immutable source metadata."""

    bundle: CanonicalBundle
    report: Mapping[str, Any]


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _require_nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LegacyConditionalRuleProjectionError(f"{label} must be a non-empty string")
    return value


def _require_sha256(value: object, label: str) -> str:
    value = _require_nonempty_string(value, label)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
        raise LegacyConditionalRuleProjectionError(f"{label} must be a 64-character SHA-256 hex digest")
    return value


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise LegacyConditionalRuleProjectionError(f"{label} must be a JSON object")
    return value


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise LegacyConditionalRuleProjectionError(f"{label} must be a JSON array")
    return value


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{_sha256_text('|'.join(parts))[:16]}"


def _json_load_with_hash(path: str | Path) -> tuple[Path, Mapping[str, Any], str]:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Required input was not found: {file_path}")
    raw = file_path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LegacyConditionalRuleProjectionError(f"Invalid JSON input: {file_path}") from exc
    return file_path, _require_mapping(parsed, str(file_path)), _sha256_bytes(raw)


def _range_from(value: object, label: str) -> tuple[int, int]:
    item = _require_mapping(value, label)
    start = item.get("start")
    end = item.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
        raise LegacyConditionalRuleProjectionError(f"{label} must contain a valid start/end range")
    return start, end


def _rule_evidence_records(rule: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    evidence = _require_mapping(rule.get("evidence"), "rule.evidence")
    primary = _require_mapping(evidence.get("primary_evidence"), "rule.evidence.primary_evidence")
    corroborating = _require_list(evidence.get("corroborating_evidence", []), "rule.evidence.corroborating_evidence")
    return (primary,) + tuple(_require_mapping(item, "corroborating evidence") for item in corroborating)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def canonical_bundle_to_dict(bundle: CanonicalBundle) -> dict[str, Any]:
    """Serialize a CanonicalBundle without changing its semantic values."""

    def serialize(records: Sequence[Any]) -> list[dict[str, Any]]:
        return [_to_jsonable(asdict(record)) for record in records]

    return {
        "insurers": serialize(bundle.insurers),
        "product_identities": serialize(bundle.product_identities),
        "product_versions": serialize(bundle.product_versions),
        "source_documents": serialize(bundle.source_documents),
        "document_versions": serialize(bundle.document_versions),
        "evidence_spans": serialize(bundle.evidence_spans),
        "assertions": serialize(bundle.assertions),
        "publication_decisions": serialize(bundle.publication_decisions),
    }


class LegacyConditionalRuleAdapter:
    """Projects one published conditional-rule artifact into Canonical Model v1."""

    def project_from_files(
        self,
        *,
        rules_path: str | Path,
        publication_receipt_path: str | Path,
        lineage_manifest_path: str | Path,
        context: CanonicalProductContext,
    ) -> CanonicalProjection:
        rules_file, rules_artifact, rules_sha256 = _json_load_with_hash(rules_path)
        receipt_file, receipt, receipt_sha256 = _json_load_with_hash(publication_receipt_path)
        manifest_file, manifest, manifest_sha256 = _json_load_with_hash(lineage_manifest_path)
        projection = self.project(
            rules_artifact=rules_artifact,
            publication_receipt=receipt,
            lineage_manifest=manifest,
            context=context,
            rules_sha256=rules_sha256,
            receipt_sha256=receipt_sha256,
            source_paths={
                "rules_path": str(rules_file),
                "publication_receipt_path": str(receipt_file),
                "lineage_manifest_path": str(manifest_file),
            },
            lineage_manifest_sha256=manifest_sha256,
        )
        return projection

    def project(
        self,
        *,
        rules_artifact: Mapping[str, Any],
        publication_receipt: Mapping[str, Any],
        lineage_manifest: Mapping[str, Any],
        context: CanonicalProductContext,
        rules_sha256: str,
        receipt_sha256: str,
        source_paths: Mapping[str, str] | None = None,
        lineage_manifest_sha256: str | None = None,
    ) -> CanonicalProjection:
        """Create a canonical projection without writing legacy inputs."""
        self._validate_context(context)
        _require_sha256(rules_sha256, "rules_sha256")
        _require_sha256(receipt_sha256, "receipt_sha256")
        if lineage_manifest_sha256 is not None:
            _require_sha256(lineage_manifest_sha256, "lineage_manifest_sha256")

        rules = _require_list(rules_artifact.get("rules"), "rules_artifact.rules")
        if not rules:
            raise LegacyConditionalRuleProjectionError("rules_artifact.rules must not be empty")
        self._validate_authoritative_artifact(rules_artifact, publication_receipt, rules)

        documents, spans = self._build_lineage_indexes(lineage_manifest)
        source_documents: dict[str, SourceDocument] = {}
        document_versions: dict[str, DocumentVersion] = {}
        evidence_spans: dict[str, EvidenceSpan] = {}
        assertions: list[KnowledgeAssertion] = []
        decisions: list[PublicationDecision] = []

        for raw_rule in rules:
            rule = _require_mapping(raw_rule, "rules_artifact.rules item")
            rule_id = _require_nonempty_string(rule.get("rule_id"), "rule.rule_id")
            rule_type = _require_nonempty_string(rule.get("rule_type"), "rule.rule_type")
            concept_id = _require_nonempty_string(rule.get("concept_id"), "rule.concept_id")

            canonical_evidence_ids: list[str] = []
            for evidence in _rule_evidence_records(rule):
                span, source_document, document_version = self._resolve_evidence(
                    evidence=evidence,
                    documents=documents,
                    spans=spans,
                    context=context,
                )
                source_documents[source_document.source_document_id] = source_document
                document_versions[document_version.document_version_id] = document_version
                evidence_spans[span.evidence_span_id] = span
                canonical_evidence_ids.append(span.evidence_span_id)

            assertion_id = _stable_id("ka", rules_sha256, rule_id)
            assertion_payload = {
                "rule_id": rule_id,
                "rule_type": rule_type,
                "effect": rule.get("effect"),
                "applies_when": rule.get("applies_when", []),
                "coverage_scope": rule.get("coverage_scope", []),
                "unresolved_ambiguities": rule.get("unresolved_ambiguities", []),
            }
            assertion = KnowledgeAssertion(
                assertion_id=assertion_id,
                product_version_id=context.product_version_id,
                concept_id=concept_id,
                assertion_kind=KnowledgeAssertionKind.CONDITIONAL_RULE,
                payload=assertion_payload,
                evidence_span_ids=tuple(dict.fromkeys(canonical_evidence_ids)),
                validation_status=ValidationStatus.VERIFIED,
                publication_status=PublicationStatus.AUTHORITATIVE,
                source_artifact_sha256=rules_sha256,
            )
            assertions.append(assertion)
            decisions.append(
                PublicationDecision(
                    publication_decision_id=_stable_id("pd", receipt_sha256, assertion_id),
                    assertion_id=assertion_id,
                    decision_status=PublicationStatus.AUTHORITATIVE,
                    decided_at=_require_nonempty_string(publication_receipt.get("published_at"), "publication_receipt.published_at"),
                    decision_reason="Legacy authoritative publication receipt verified; canonical projection only.",
                    source_artifact_sha256=receipt_sha256,
                )
            )

        bundle = CanonicalBundle(
            insurers=(Insurer(context.insurer_id, context.insurer_legal_name, context.insurer_type),),
            product_identities=(
                ProductIdentity(
                    product_id=context.product_id,
                    insurer_id=context.insurer_id,
                    domain=context.domain,
                    product_name=context.product_name,
                    uin=context.product_uin,
                    product_family_name=context.product_family_name,
                ),
            ),
            product_versions=(
                ProductVersion(
                    product_version_id=context.product_version_id,
                    product_id=context.product_id,
                    version_label=context.product_version_label,
                ),
            ),
            source_documents=tuple(sorted(source_documents.values(), key=lambda item: item.source_document_id)),
            document_versions=tuple(sorted(document_versions.values(), key=lambda item: item.document_version_id)),
            evidence_spans=tuple(sorted(evidence_spans.values(), key=lambda item: item.evidence_span_id)),
            assertions=tuple(sorted(assertions, key=lambda item: item.assertion_id)),
            publication_decisions=tuple(sorted(decisions, key=lambda item: item.publication_decision_id)),
        )
        validation_report = validate_canonical_bundle(bundle)
        report = {
            "schema_version": "1.0",
            "projection_type": "legacy_conditional_rule_to_canonical_v1",
            "projection_status": "validated_read_only_projection",
            "source_artifacts": {
                "rules_sha256": rules_sha256,
                "publication_receipt_sha256": receipt_sha256,
                "lineage_manifest_sha256": lineage_manifest_sha256,
                **dict(source_paths or {}),
            },
            "legacy_entity_id": rules_artifact.get("entity_id"),
            "legacy_field": rules_artifact.get("field"),
            "validated_bundle": validation_report,
            "mapping_counts": {
                "legacy_rules": len(rules),
                "canonical_assertions": len(bundle.assertions),
                "canonical_evidence_spans": len(bundle.evidence_spans),
                "canonical_document_versions": len(bundle.document_versions),
                "publication_decisions": len(bundle.publication_decisions),
            },
            "notes": [
                "Legacy artifacts were read only and remain authoritative in their existing location.",
                "Every cited evidence record was bound through the supplied lineage manifest.",
                "This projection does not republish, mutate, or supersede the legacy conditional-rule artifact.",
            ],
        }
        return CanonicalProjection(bundle=bundle, report=report)

    def write_projection(self, projection: CanonicalProjection, output_path: str | Path) -> Path:
        """Write only the separate canonical projection requested by the caller."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "report": dict(projection.report),
            "canonical_bundle": canonical_bundle_to_dict(projection.bundle),
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def _validate_context(self, context: CanonicalProductContext) -> None:
        for label, value in (
            ("context.insurer_id", context.insurer_id),
            ("context.insurer_legal_name", context.insurer_legal_name),
            ("context.product_id", context.product_id),
            ("context.product_name", context.product_name),
            ("context.domain", context.domain),
            ("context.product_version_id", context.product_version_id),
        ):
            _require_nonempty_string(value, label)

    def _validate_authoritative_artifact(
        self,
        rules_artifact: Mapping[str, Any],
        receipt: Mapping[str, Any],
        rules: Sequence[Any],
    ) -> None:
        if rules_artifact.get("authority_mode") != "authoritative_conditional_rules":
            raise LegacyConditionalRuleProjectionError("rules artifact is not authoritative_conditional_rules")
        if receipt.get("authority_mode") != "authoritative_conditional_rules":
            raise LegacyConditionalRuleProjectionError("publication receipt is not authoritative_conditional_rules")
        if receipt.get("verification_passed") is not True:
            raise LegacyConditionalRuleProjectionError("publication receipt verification_passed must be true")
        for field in ("entity_id", "field"):
            left = _require_nonempty_string(rules_artifact.get(field), f"rules_artifact.{field}")
            right = _require_nonempty_string(receipt.get(field), f"publication_receipt.{field}")
            if left != right:
                raise LegacyConditionalRuleProjectionError(f"Receipt {field} does not match rules artifact")
        artifact_rule_ids = [_require_nonempty_string(_require_mapping(item, "rule").get("rule_id"), "rule.rule_id") for item in rules]
        if len(set(artifact_rule_ids)) != len(artifact_rule_ids):
            raise LegacyConditionalRuleProjectionError("rules artifact contains duplicate rule_id values")
        receipt_rule_ids = _require_list(receipt.get("rule_ids"), "publication_receipt.rule_ids")
        if set(receipt_rule_ids) != set(artifact_rule_ids) or len(receipt_rule_ids) != len(artifact_rule_ids):
            raise LegacyConditionalRuleProjectionError("Publication receipt rule_ids do not exactly match rules artifact")

    def _build_lineage_indexes(
        self,
        manifest: Mapping[str, Any],
    ) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
        if manifest.get("schema_version") != "1.0":
            raise LegacyConditionalRuleProjectionError("lineage manifest schema_version must be 1.0")
        raw_documents = _require_list(manifest.get("documents"), "lineage_manifest.documents")
        raw_spans = _require_list(manifest.get("evidence_spans"), "lineage_manifest.evidence_spans")
        documents: dict[str, Mapping[str, Any]] = {}
        spans: dict[str, Mapping[str, Any]] = {}
        for raw in raw_documents:
            item = _require_mapping(raw, "lineage document")
            document_id = _require_nonempty_string(item.get("document_id"), "lineage document.document_id")
            if document_id in documents:
                raise LegacyConditionalRuleProjectionError(f"Duplicate lineage document_id: {document_id}")
            for key in ("source_document_id", "document_version_id", "content_sha256", "captured_at", "document_type", "canonical_title"):
                _require_nonempty_string(item.get(key), f"lineage document.{key}")
            _require_sha256(item.get("content_sha256"), "lineage document.content_sha256")
            documents[document_id] = item
        for raw in raw_spans:
            item = _require_mapping(raw, "lineage evidence span")
            evidence_id = _require_nonempty_string(item.get("evidence_id"), "lineage evidence span.evidence_id")
            if evidence_id in spans:
                raise LegacyConditionalRuleProjectionError(f"Duplicate lineage evidence_id: {evidence_id}")
            document_id = _require_nonempty_string(item.get("document_id"), "lineage evidence span.document_id")
            if document_id not in documents:
                raise LegacyConditionalRuleProjectionError(f"Lineage span references unknown document_id: {document_id}")
            _require_nonempty_string(item.get("document_version_id"), "lineage evidence span.document_version_id")
            _require_sha256(item.get("text_sha256"), "lineage evidence span.text_sha256")
            _require_nonempty_string(item.get("extraction_method"), "lineage evidence span.extraction_method")
            _range_from(item.get("source_char_range"), "lineage evidence span.source_char_range")
            spans[evidence_id] = item
        return documents, spans

    def _resolve_evidence(
        self,
        *,
        evidence: Mapping[str, Any],
        documents: Mapping[str, Mapping[str, Any]],
        spans: Mapping[str, Mapping[str, Any]],
        context: CanonicalProductContext,
    ) -> tuple[EvidenceSpan, SourceDocument, DocumentVersion]:
        evidence_id = _require_nonempty_string(evidence.get("evidence_id"), "legacy evidence.evidence_id")
        document_id = _require_nonempty_string(evidence.get("document_id"), "legacy evidence.document_id")
        legacy_document_type = _require_nonempty_string(evidence.get("document_type"), "legacy evidence.document_type")
        start, end = _range_from(evidence.get("source_char_range"), "legacy evidence.source_char_range")
        manifest_span = spans.get(evidence_id)
        if manifest_span is None:
            raise LegacyConditionalRuleProjectionError(
                f"No lineage manifest evidence span exists for legacy evidence_id: {evidence_id}"
            )
        if manifest_span.get("document_id") != document_id:
            raise LegacyConditionalRuleProjectionError(f"Lineage document mismatch for evidence_id: {evidence_id}")
        manifest_start, manifest_end = _range_from(manifest_span.get("source_char_range"), "lineage evidence span.source_char_range")
        if (manifest_start, manifest_end) != (start, end):
            raise LegacyConditionalRuleProjectionError(f"Lineage character range mismatch for evidence_id: {evidence_id}")
        manifest_document = documents[document_id]
        if manifest_document.get("document_version_id") != manifest_span.get("document_version_id"):
            raise LegacyConditionalRuleProjectionError(f"Lineage document version mismatch for evidence_id: {evidence_id}")
        if manifest_document.get("document_type") != legacy_document_type:
            raise LegacyConditionalRuleProjectionError(f"Lineage document type mismatch for evidence_id: {evidence_id}")

        source_document = SourceDocument(
            source_document_id=manifest_document["source_document_id"],
            insurer_id=context.insurer_id,
            document_type=manifest_document["document_type"],
            canonical_title=manifest_document["canonical_title"],
            product_version_id=context.product_version_id,
            source_url=manifest_document.get("source_url"),
        )
        document_version = DocumentVersion(
            document_version_id=manifest_document["document_version_id"],
            source_document_id=manifest_document["source_document_id"],
            content_sha256=manifest_document["content_sha256"],
            captured_at=manifest_document["captured_at"],
            effective_from=manifest_document.get("effective_from"),
            effective_to=manifest_document.get("effective_to"),
            storage_locator=manifest_document.get("storage_locator"),
        )
        source_page = manifest_span.get("source_page")
        if source_page is not None and (not isinstance(source_page, int) or source_page < 1):
            raise LegacyConditionalRuleProjectionError(f"lineage evidence span.source_page must be a positive integer for evidence_id: {evidence_id}")
        span = EvidenceSpan(
            evidence_span_id=_stable_id("es", manifest_span["document_version_id"], evidence_id),
            document_version_id=manifest_span["document_version_id"],
            source_char_start=start,
            source_char_end=end,
            text_sha256=manifest_span["text_sha256"],
            extraction_method=manifest_span["extraction_method"],
            source_page=source_page,
        )
        return span, source_document, document_version
