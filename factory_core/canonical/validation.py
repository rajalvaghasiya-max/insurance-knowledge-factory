"""Validation for P2.5-B canonical model v1."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Iterable, Sequence

from .models import (
    CanonicalBundle,
    KnowledgeAssertion,
    KnowledgeAssertionKind,
    PublicationStatus,
    ValidationStatus,
)


class CanonicalModelValidationError(ValueError):
    """Raised when a canonical bundle violates a model invariant."""


def _assert_nonempty(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalModelValidationError(f"{label} must be a non-empty string")


def _assert_sha256(value: object, label: str) -> None:
    _assert_nonempty(value, label)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
        raise CanonicalModelValidationError(f"{label} must be a 64-character SHA-256 hex digest")


def _assert_unique(items: Sequence[object], id_attribute: str, label: str) -> None:
    ids = [getattr(item, id_attribute) for item in items]
    duplicates = [identifier for identifier, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise CanonicalModelValidationError(f"Duplicate {label} IDs: {', '.join(sorted(duplicates))}")


def _assert_known(identifier: str, known: set[str], label: str) -> None:
    if identifier not in known:
        raise CanonicalModelValidationError(f"Unknown {label}: {identifier}")


def _validate_assertion_payload(assertion: KnowledgeAssertion) -> None:
    if not isinstance(assertion.payload, dict):
        raise CanonicalModelValidationError("KnowledgeAssertion.payload must be a plain dictionary")

    if assertion.assertion_kind is KnowledgeAssertionKind.SCALAR_FACT:
        for key in ("field_id", "value"):
            if key not in assertion.payload:
                raise CanonicalModelValidationError(
                    f"Scalar fact assertion {assertion.assertion_id} requires payload.{key}"
                )
    elif assertion.assertion_kind is KnowledgeAssertionKind.CONDITIONAL_RULE:
        for key in ("rule_id", "rule_type"):
            if key not in assertion.payload:
                raise CanonicalModelValidationError(
                    f"Conditional-rule assertion {assertion.assertion_id} requires payload.{key}"
                )
    else:  # defensive, for future enum extensions
        raise CanonicalModelValidationError(
            f"Unsupported assertion kind: {assertion.assertion_kind}"
        )


def validate_canonical_bundle(bundle: CanonicalBundle) -> dict:
    """Validate referential, evidence, and publication-state invariants.

    Returns a concise report suitable for test assertions or future adapters.
    The function never writes files and never modifies supplied records.
    """

    collections = (
        (bundle.insurers, "insurer_id", "insurer"),
        (bundle.product_identities, "product_id", "product identity"),
        (bundle.product_versions, "product_version_id", "product version"),
        (bundle.source_documents, "source_document_id", "source document"),
        (bundle.document_versions, "document_version_id", "document version"),
        (bundle.evidence_spans, "evidence_span_id", "evidence span"),
        (bundle.assertions, "assertion_id", "assertion"),
        (bundle.publication_decisions, "publication_decision_id", "publication decision"),
    )
    for records, identifier, label in collections:
        _assert_unique(records, identifier, label)

    insurer_ids = {item.insurer_id for item in bundle.insurers}
    product_ids = {item.product_id for item in bundle.product_identities}
    product_version_ids = {item.product_version_id for item in bundle.product_versions}
    source_document_ids = {item.source_document_id for item in bundle.source_documents}
    document_version_ids = {item.document_version_id for item in bundle.document_versions}
    evidence_span_ids = {item.evidence_span_id for item in bundle.evidence_spans}
    assertion_ids = {item.assertion_id for item in bundle.assertions}

    for insurer in bundle.insurers:
        _assert_nonempty(insurer.insurer_id, "Insurer.insurer_id")
        _assert_nonempty(insurer.legal_name, "Insurer.legal_name")

    for product in bundle.product_identities:
        _assert_nonempty(product.product_id, "ProductIdentity.product_id")
        _assert_known(product.insurer_id, insurer_ids, "ProductIdentity.insurer_id")
        _assert_nonempty(product.domain, "ProductIdentity.domain")
        _assert_nonempty(product.product_name, "ProductIdentity.product_name")

    for version in bundle.product_versions:
        _assert_nonempty(version.product_version_id, "ProductVersion.product_version_id")
        _assert_known(version.product_id, product_ids, "ProductVersion.product_id")

    for document in bundle.source_documents:
        _assert_nonempty(document.source_document_id, "SourceDocument.source_document_id")
        _assert_known(document.insurer_id, insurer_ids, "SourceDocument.insurer_id")
        if document.product_version_id is not None:
            _assert_known(document.product_version_id, product_version_ids, "SourceDocument.product_version_id")
        _assert_nonempty(document.document_type, "SourceDocument.document_type")
        _assert_nonempty(document.canonical_title, "SourceDocument.canonical_title")

    for version in bundle.document_versions:
        _assert_nonempty(version.document_version_id, "DocumentVersion.document_version_id")
        _assert_known(version.source_document_id, source_document_ids, "DocumentVersion.source_document_id")
        _assert_sha256(version.content_sha256, "DocumentVersion.content_sha256")
        _assert_nonempty(version.captured_at, "DocumentVersion.captured_at")

    for evidence in bundle.evidence_spans:
        _assert_nonempty(evidence.evidence_span_id, "EvidenceSpan.evidence_span_id")
        _assert_known(evidence.document_version_id, document_version_ids, "EvidenceSpan.document_version_id")
        if evidence.source_char_start < 0 or evidence.source_char_end <= evidence.source_char_start:
            raise CanonicalModelValidationError(
                "EvidenceSpan source_char range must be non-negative and end must exceed start"
            )
        _assert_sha256(evidence.text_sha256, "EvidenceSpan.text_sha256")
        _assert_nonempty(evidence.extraction_method, "EvidenceSpan.extraction_method")

    evidence_required_statuses = {
        ValidationStatus.EVIDENCE_ASSEMBLED,
        ValidationStatus.VERIFIED,
    }
    for assertion in bundle.assertions:
        _assert_nonempty(assertion.assertion_id, "KnowledgeAssertion.assertion_id")
        _assert_known(assertion.product_version_id, product_version_ids, "KnowledgeAssertion.product_version_id")
        _assert_nonempty(assertion.concept_id, "KnowledgeAssertion.concept_id")
        _validate_assertion_payload(assertion)
        for evidence_id in assertion.evidence_span_ids:
            _assert_known(evidence_id, evidence_span_ids, "KnowledgeAssertion.evidence_span_id")
        if assertion.validation_status in evidence_required_statuses and not assertion.evidence_span_ids:
            raise CanonicalModelValidationError(
                f"{assertion.validation_status.value} assertion {assertion.assertion_id} requires evidence"
            )
        if assertion.publication_status is PublicationStatus.AUTHORITATIVE:
            if assertion.validation_status is not ValidationStatus.VERIFIED:
                raise CanonicalModelValidationError(
                    f"Authoritative assertion {assertion.assertion_id} must be verified"
                )
            if not assertion.evidence_span_ids:
                raise CanonicalModelValidationError(
                    f"Authoritative assertion {assertion.assertion_id} requires evidence"
                )
            if assertion.source_artifact_sha256 is None:
                raise CanonicalModelValidationError(
                    f"Authoritative assertion {assertion.assertion_id} requires source_artifact_sha256"
                )
            _assert_sha256(assertion.source_artifact_sha256, "KnowledgeAssertion.source_artifact_sha256")

    for decision in bundle.publication_decisions:
        _assert_nonempty(decision.publication_decision_id, "PublicationDecision.publication_decision_id")
        _assert_known(decision.assertion_id, assertion_ids, "PublicationDecision.assertion_id")
        _assert_nonempty(decision.decided_at, "PublicationDecision.decided_at")
        _assert_nonempty(decision.decision_reason, "PublicationDecision.decision_reason")
        if decision.source_artifact_sha256 is not None:
            _assert_sha256(decision.source_artifact_sha256, "PublicationDecision.source_artifact_sha256")
        if decision.decision_status is PublicationStatus.AUTHORITATIVE:
            assertion = next(item for item in bundle.assertions if item.assertion_id == decision.assertion_id)
            if assertion.validation_status is not ValidationStatus.VERIFIED:
                raise CanonicalModelValidationError(
                    "An authoritative publication decision requires a verified assertion"
                )

    return {
        "schema_version": "1.0",
        "valid": True,
        "counts": {
            "insurers": len(bundle.insurers),
            "product_identities": len(bundle.product_identities),
            "product_versions": len(bundle.product_versions),
            "source_documents": len(bundle.source_documents),
            "document_versions": len(bundle.document_versions),
            "evidence_spans": len(bundle.evidence_spans),
            "assertions": len(bundle.assertions),
            "publication_decisions": len(bundle.publication_decisions),
        },
    }
