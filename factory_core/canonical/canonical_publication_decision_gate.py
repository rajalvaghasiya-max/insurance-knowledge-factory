"""P2.5-J — publication eligibility gate for canonical generic legal assertions.

This gate is deliberately non-mutating. It reviews an existing canonical projection
and emits a separate decision artifact. A separate publisher is still required before
any assertion becomes authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


class CanonicalPublicationDecisionGateError(ValueError):
    """Raised when a canonical projection is not eligible for publication review."""


@dataclass(frozen=True)
class CanonicalPublicationDecisionGateResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise CanonicalPublicationDecisionGateError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CanonicalPublicationDecisionGateError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalPublicationDecisionGateError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise CanonicalPublicationDecisionGateError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _load_json(root: Path, relative_path: str, label: str) -> tuple[Mapping[str, Any], str]:
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise CanonicalPublicationDecisionGateError(f"{label} must remain under repository_root") from exc
    if not target.is_file():
        raise FileNotFoundError(f"{label} was not found: {relative_path}")
    raw = target.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CanonicalPublicationDecisionGateError(f"{label} is not valid UTF-8 JSON") from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]}"


class CanonicalPublicationDecisionGate:
    """Approves eligible generic legal assertions for a later authoritative publisher."""

    def decide_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path) -> CanonicalPublicationDecisionGateResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Publication decision specification was not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CanonicalPublicationDecisionGateError("Publication decision specification is not valid JSON") from exc
        return self.decide(spec=_mapping(raw, "publication_decision_spec"), repository_root=repository_root)

    def decide(self, *, spec: Mapping[str, Any], repository_root: str | Path, decided_at: str | None = None) -> CanonicalPublicationDecisionGateResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")
        if spec.get("schema_version") != "1.0":
            raise CanonicalPublicationDecisionGateError("publication_decision_spec.schema_version must be 1.0")
        if spec.get("gate_type") != "canonical_publication_decision_gate_v1":
            raise CanonicalPublicationDecisionGateError("publication_decision_spec.gate_type is invalid")
        if spec.get("reviewed_by_human") is not True:
            raise CanonicalPublicationDecisionGateError("publication_decision_spec.reviewed_by_human must be true")

        projection_path = _safe_relative_path(spec.get("canonical_projection_path"), "canonical_projection_path")
        classification_path = _safe_relative_path(spec.get("classification_manifest_path"), "classification_manifest_path")
        projection, projection_sha = _load_json(root, projection_path, "canonical_projection")
        classification, classification_sha = _load_json(root, classification_path, "classification_manifest")

        report = _mapping(projection.get("projection_report"), "canonical_projection.projection_report")
        if report.get("projection_status") != "validated_read_only_canonical_projection_not_published":
            raise CanonicalPublicationDecisionGateError("canonical projection is not a validated unpublished projection")
        canonical = _mapping(projection.get("canonical_bundle"), "canonical_projection.canonical_bundle")
        if classification.get("classification_status") != "reviewed_document_classifications_recorded_not_published":
            raise CanonicalPublicationDecisionGateError("classification manifest is not reviewed")

        expected_version = _text(spec.get("product_version_id"), "product_version_id")
        approved_types = set(_items(spec.get("approved_rule_types"), "approved_rule_types"))
        if not approved_types or not all(isinstance(item, str) and item for item in approved_types):
            raise CanonicalPublicationDecisionGateError("approved_rule_types must contain non-empty strings")
        requested_ids = [_text(item, "assertion_ids[]") for item in _items(spec.get("assertion_ids"), "assertion_ids")]
        if len(requested_ids) != len(set(requested_ids)):
            raise CanonicalPublicationDecisionGateError("assertion_ids must be unique")

        docs = {}
        for raw in _items(classification.get("documents"), "classification_manifest.documents"):
            item = _mapping(raw, "classification_manifest.documents[]")
            docs[_text(item.get("document_id"), "classification.document_id")] = item

        bindings = {}
        for raw in _items(spec.get("source_document_bindings"), "source_document_bindings"):
            item = _mapping(raw, "source_document_bindings[]")
            source_id = _text(item.get("source_document_id"), "source_document_binding.source_document_id")
            if source_id in bindings:
                raise CanonicalPublicationDecisionGateError("source_document_bindings must have unique source_document_id values")
            bindings[source_id] = {
                "document_id": _text(item.get("document_id"), "source_document_binding.document_id"),
                "document_version_id": _text(item.get("document_version_id"), "source_document_binding.document_version_id"),
            }

        source_docs = {_text(item.get("source_document_id"), "source_document.source_document_id"): _mapping(item, "source_document")
                       for item in _items(canonical.get("source_documents"), "canonical_bundle.source_documents")}
        doc_versions = {_text(item.get("document_version_id"), "document_version.document_version_id"): _mapping(item, "document_version")
                        for item in _items(canonical.get("document_versions"), "canonical_bundle.document_versions")}
        spans = {_text(item.get("evidence_span_id"), "evidence_span.evidence_span_id"): _mapping(item, "evidence_span")
                 for item in _items(canonical.get("evidence_spans"), "canonical_bundle.evidence_spans")}
        prior_decisions = {_text(item.get("assertion_id"), "publication_decision.assertion_id"): _mapping(item, "publication_decision")
                           for item in _items(canonical.get("publication_decisions"), "canonical_bundle.publication_decisions")}
        assertions = {_text(item.get("assertion_id"), "assertion.assertion_id"): _mapping(item, "assertion")
                      for item in _items(canonical.get("assertions"), "canonical_bundle.assertions")}

        decisions: list[dict[str, Any]] = []
        for assertion_id in requested_ids:
            assertion = assertions.get(assertion_id)
            if assertion is None:
                raise CanonicalPublicationDecisionGateError(f"requested assertion is missing: {assertion_id}")
            if assertion.get("assertion_kind") != "conditional_rule":
                raise CanonicalPublicationDecisionGateError(f"{assertion_id} is not a conditional_rule")
            if assertion.get("product_version_id") != expected_version:
                raise CanonicalPublicationDecisionGateError(f"product version mismatch for {assertion_id}")
            if assertion.get("validation_status") != "evidence_assembled":
                raise CanonicalPublicationDecisionGateError(f"{assertion_id} is not evidence_assembled")
            if assertion.get("publication_status") != "unpublished":
                raise CanonicalPublicationDecisionGateError(f"{assertion_id} is not unpublished")
            payload = _mapping(assertion.get("payload"), "assertion.payload")
            rule_type = _text(payload.get("rule_type"), "assertion.payload.rule_type")
            if rule_type not in approved_types:
                raise CanonicalPublicationDecisionGateError(f"rule_type is not approved for this gate: {rule_type}")
            if payload.get("scope") != "reusable_generic_product_legal_condition":
                raise CanonicalPublicationDecisionGateError(f"{assertion_id} does not have reusable generic legal scope")
            prior = prior_decisions.get(assertion_id)
            if prior is None or prior.get("decision_status") != "unpublished":
                raise CanonicalPublicationDecisionGateError(f"{assertion_id} lacks an unpublished canonical decision")

            evidence_ids = _items(assertion.get("evidence_span_ids"), "assertion.evidence_span_ids")
            if not evidence_ids:
                raise CanonicalPublicationDecisionGateError(f"{assertion_id} has no evidence spans")
            primary_legal = 0
            for evidence_id in evidence_ids:
                span = spans.get(_text(evidence_id, "evidence_span_id"))
                if span is None:
                    raise CanonicalPublicationDecisionGateError(f"missing evidence span for {assertion_id}")
                version = doc_versions.get(_text(span.get("document_version_id"), "span.document_version_id"))
                if version is None:
                    raise CanonicalPublicationDecisionGateError(f"missing document version for {assertion_id}")
                source_id = _text(version.get("source_document_id"), "document_version.source_document_id")
                source = source_docs.get(source_id)
                if source is None:
                    raise CanonicalPublicationDecisionGateError(f"missing source document for {assertion_id}")
                binding = bindings.get(source_id)
                if binding is None:
                    raise CanonicalPublicationDecisionGateError(f"source document binding is missing for {source_id}")
                if binding["document_version_id"] != version.get("document_version_id"):
                    raise CanonicalPublicationDecisionGateError(f"source document version binding mismatch for {source_id}")
                classification_entry = docs.get(binding["document_id"])
                if classification_entry is None:
                    raise CanonicalPublicationDecisionGateError(f"classification is missing for {binding['document_id']}")
                if classification_entry.get("document_version_id") != version.get("document_version_id"):
                    raise CanonicalPublicationDecisionGateError(f"classification document version mismatch for {binding['document_id']}")
                if classification_entry.get("classification") != "reusable_generic" or classification_entry.get("reuse_action") != "reusable_evidence_candidate":
                    raise CanonicalPublicationDecisionGateError(f"source is not eligible for publication: {binding['document_id']}")
                document_type = source.get("document_type")
                if document_type == "policy_wording":
                    primary_legal += 1
                if document_type in {"brochure", "policy_schedule", "renewal_notice", "endorsement", "claim_document", "medical_record", "group_schedule", "member_certificate", "quote"}:
                    raise CanonicalPublicationDecisionGateError(f"blocked document type in publication evidence: {document_type}")
            if primary_legal != 1:
                raise CanonicalPublicationDecisionGateError(f"{assertion_id} requires exactly one primary policy-wording evidence span")

            decisions.append({
                "publication_decision_id": _stable_id("pg", assertion_id, projection_sha, "eligible"),
                "assertion_id": assertion_id,
                "eligibility_status": "eligible_for_authoritative_publication",
                "current_publication_status": "unpublished",
                "decision_reason": "Reviewed canonical generic legal assertion has reusable generic evidence, one policy-wording primary span, and no blocked source dependency.",
                "decided_at": decided_at or datetime.now(timezone.utc).isoformat(),
                "source_projection_sha256": projection_sha,
                "next_required_action": "authoritative_publisher_required",
            })

        return CanonicalPublicationDecisionGateResult(manifest={
            "schema_version": "1.0",
            "gate_type": "canonical_publication_decision_gate_v1",
            "decision_status": "reviewed_assertions_eligible_not_published",
            "canonical_projection_path": projection_path,
            "canonical_projection_sha256": projection_sha,
            "classification_manifest_path": classification_path,
            "classification_manifest_sha256": classification_sha,
            "product_version_id": expected_version,
            "decisions": decisions,
            "guardrails": [
                "This gate is read-only and does not change canonical assertion publication_status.",
                "Only reviewed, evidence_assembled, unpublished conditional rules may be assessed.",
                "All evidence must trace to reusable_generic classifications with reusable_evidence_candidate action.",
                "Exactly one policy-wording primary evidence span is required for each approved assertion.",
                "Plan-specific room-category, room-rent-limit, and ICU-limit entitlement assertions are outside this gate.",
                "A separate authoritative publisher is required before any assertion becomes authoritative.",
            ],
        })

    def write_output(self, result: CanonicalPublicationDecisionGateResult, *, repository_root: str | Path, output_path: str | Path) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise CanonicalPublicationDecisionGateError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
