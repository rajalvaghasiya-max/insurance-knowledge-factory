"""P1.5a-1 — document identity resolution overlay.

Creates reviewable, non-mutating overlays connecting a durable product identity
reference, an immutable source-registration version, and a reviewed temporal
resolution. It never publishes insurance facts or infers currentness from UIN alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from factory_core.governance.document_currentness_evidence import (
    DocumentCurrentnessEvidenceError,
    DocumentCurrentnessEvidenceRecord,
)


class DocumentIdentityResolutionError(ValueError):
    """Raised when an identity overlay is incomplete, unsafe, or inconsistent."""


_ALLOWED_DOCUMENT_TYPES = frozenset({
    "policy_wording", "prospectus", "customer_information_sheet",
    "product_benefit_table", "brochure", "official_product_webpage_export", "other",
})
_ALLOWED_TEMPORAL_STATUSES = frozenset({
    "current", "current_observed_reviewed", "historical", "replaced",
    "compatibility_unverified", "unknown", "observation_failed",
})
_ALLOWED_RESOLUTION_STATUSES = frozenset({"resolved", "probable", "ambiguous", "unresolved"})
_ALLOWED_SIGNAL_TYPES = frozenset({
    "uin_exact_match", "canonical_title_match", "source_page_association",
    "issuer_label_match", "manual_document_review", "effective_date_match", "version_label_match",
})
_ALLOWED_SIGNAL_VERIFICATION = frozenset({
    "registration_metadata", "document_embedded_text", "source_page_metadata", "manual_reviewed",
})
_REUSABLE_CLASSIFICATION = "reusable_generic"
_ELIGIBLE = "eligible_for_evidence_review"
_BLOCKED = "blocked"
_IDENTITY_RECORD_TYPE = "product_identity_reference_v1"
_IDENTITY_RECORD_STATUS = "reviewed_product_identity_recorded_not_published"
_SOURCE_OBSERVATION_RECORD_TYPE = "source_observation_record_v1"
_SOURCE_OBSERVATION_RECORD_STATUS = "source_observation_recorded_review_required"
_ALLOWED_OBSERVATION_REVIEW_STATUSES = frozenset({
    "current_observed_reviewed", "compatibility_unverified", "replaced",
    "historical", "observation_failed",
})


@dataclass(frozen=True)
class DocumentIdentityResolutionResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise DocumentIdentityResolutionError(f"{label} must be a JSON object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise DocumentIdentityResolutionError(f"{label} must be a JSON array")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DocumentIdentityResolutionError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise DocumentIdentityResolutionError(f"{label} must be a safe repository-relative path")
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
        raise DocumentIdentityResolutionError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise DocumentIdentityResolutionError(f"{label} was not found: {relative_path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DocumentIdentityResolutionError(f"{label} is not valid JSON: {relative_path}") from exc
    return _mapping(parsed, label)


def _validate_uin(value: object, label: str) -> str:
    uin = _nonempty(value, label).upper()
    if len(uin) < 8 or any(ch.isspace() for ch in uin):
        raise DocumentIdentityResolutionError(f"{label} must be a compact UIN-like identifier")
    return uin


def _load_product_identity_reference(root: Path, raw: object) -> dict[str, str]:
    product_ref = _mapping(raw, "product_identity_reference")
    # Explicitly reject the P1.5a-0 placeholder shape. New overlays must use a record.
    if "identity_record_path" not in product_ref:
        raise DocumentIdentityResolutionError(
            "product_identity_reference.identity_record_path is required; "
            "manual placeholder references are not allowed in new overlays"
        )
    record_path = _safe_relative_path(
        product_ref.get("identity_record_path"),
        "product_identity_reference.identity_record_path",
    )
    record = _load_json(root, record_path, "product_identity_reference record")
    if record.get("record_type") != _IDENTITY_RECORD_TYPE:
        raise DocumentIdentityResolutionError(
            "product identity record must be product_identity_reference_v1"
        )
    if record.get("record_status") != _IDENTITY_RECORD_STATUS:
        raise DocumentIdentityResolutionError(
            "product identity record must be reviewed_product_identity_recorded_not_published"
        )
    if record.get("reviewed_by_human") is not True:
        raise DocumentIdentityResolutionError("product identity record must be human-reviewed")
    if record.get("identity_resolution_status") != "resolved":
        raise DocumentIdentityResolutionError("product identity record must be resolved")
    identity = _mapping(record.get("product_identity"), "product identity record.product_identity")
    resolved = {
        "entity_id": _nonempty(identity.get("entity_id"), "product identity record.entity_id"),
        "insurer_id": _nonempty(identity.get("insurer_id"), "product identity record.insurer_id"),
        "product_id": _nonempty(identity.get("product_id"), "product identity record.product_id"),
        "canonical_product_name": _nonempty(
            identity.get("canonical_product_name"),
            "product identity record.canonical_product_name",
        ),
        "uin": _validate_uin(identity.get("uin"), "product identity record.uin"),
        "identity_record_path": record_path,
        "identity_record_sha256": _sha256_file((root / record_path).resolve()),
    }
    expected_entity = f"{resolved['insurer_id']}:{resolved['product_id']}"
    if resolved["entity_id"] != expected_entity:
        raise DocumentIdentityResolutionError(
            "product identity record entity_id must equal insurer_id:product_id"
        )
    return resolved


def _classification_for_version(root: Path, classification_path: str | None, version_id: str) -> str | None:
    if not classification_path:
        return None
    classification = _load_json(root, classification_path, "classification_manifest")
    docs = _list(classification.get("documents"), "classification_manifest.documents")
    for item in docs:
        row = _mapping(item, "classification_manifest.documents[]")
        if row.get("document_version_id") == version_id:
            return _nonempty(row.get("classification"), "classification document classification")
    raise DocumentIdentityResolutionError("classification_manifest does not contain the registered document_version_id")


def _require_iso_datetime(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DocumentIdentityResolutionError(f"{label} must be an ISO-8601 timestamp") from exc
    return raw


def _validate_source_observation_review(
    *,
    root: Path,
    raw: object,
    registration_path: str,
    document: Mapping[str, Any],
    temporal_status: str,
) -> dict[str, Any] | None:
    """Bind a human temporal review to one immutable source-observation record.

    The source-observation record remains evidence only.  This function accepts a
    temporal result only when a human has explicitly reviewed that record for the
    same registered document version; it never infers currentness from bytes.
    """
    if raw is None:
        if temporal_status in {"current_observed_reviewed", "observation_failed"}:
            raise DocumentIdentityResolutionError(
                f"{temporal_status} requires source_observation_review"
            )
        return None

    review = _mapping(raw, "source_observation_review")
    record_path = _safe_relative_path(
        review.get("observation_record_path"),
        "source_observation_review.observation_record_path",
    )
    record = _load_json(root, record_path, "source_observation_review record")
    if record.get("record_type") != _SOURCE_OBSERVATION_RECORD_TYPE:
        raise DocumentIdentityResolutionError(
            "source observation record must be source_observation_record_v1"
        )
    if record.get("record_status") != _SOURCE_OBSERVATION_RECORD_STATUS:
        raise DocumentIdentityResolutionError(
            "source observation record must be source_observation_recorded_review_required"
        )
    registered = _mapping(record.get("registered_document"), "source_observation_review record.registered_document")
    expected = {
        "document_id": _nonempty(document.get("document_id"), "registration.document.document_id"),
        "document_version_id": _nonempty(document.get("document_version_id"), "registration.document.document_version_id"),
        "content_sha256": _nonempty(document.get("content_sha256"), "registration.document.content_sha256"),
        "registration_path": registration_path,
    }
    for field, value in expected.items():
        if registered.get(field) != value:
            raise DocumentIdentityResolutionError(
                f"source observation record {field} must match the overlay registered document"
            )

    byte_comparison = _mapping(record.get("byte_comparison"), "source_observation_review record.byte_comparison")
    comparison_status = _nonempty(
        byte_comparison.get("status"), "source_observation_review record.byte_comparison.status"
    )
    if comparison_status not in {"byte_identical_observed", "bytes_changed_observed", "observation_failed"}:
        raise DocumentIdentityResolutionError("source observation record has unsupported byte comparison status")

    reviewed_by_human = review.get("reviewed_by_human")
    if reviewed_by_human is not True:
        raise DocumentIdentityResolutionError("source_observation_review.reviewed_by_human must be true")
    reviewed_at = _require_iso_datetime(
        review.get("reviewed_at"), "source_observation_review.reviewed_at"
    )
    reviewed_temporal_status = _nonempty(
        review.get("reviewed_temporal_status"), "source_observation_review.reviewed_temporal_status"
    )
    if reviewed_temporal_status not in _ALLOWED_OBSERVATION_REVIEW_STATUSES:
        raise DocumentIdentityResolutionError("unsupported source_observation_review.reviewed_temporal_status")
    if reviewed_temporal_status != temporal_status:
        raise DocumentIdentityResolutionError(
            "source_observation_review.reviewed_temporal_status must match documents[].temporal_status"
        )
    rationale = _nonempty(
        review.get("review_rationale"), "source_observation_review.review_rationale"
    )

    if reviewed_temporal_status == "current_observed_reviewed" and comparison_status != "byte_identical_observed":
        raise DocumentIdentityResolutionError(
            "current_observed_reviewed requires a byte_identical_observed source observation"
        )
    if reviewed_temporal_status == "observation_failed" and comparison_status != "observation_failed":
        raise DocumentIdentityResolutionError(
            "observation_failed requires an observation_failed source observation"
        )

    return {
        "observation_record_path": record_path,
        "observation_record_sha256": _sha256_file((root / record_path).resolve()),
        "observation_id": _nonempty(record.get("observation_id"), "source_observation_review record.observation_id"),
        "byte_comparison_status": comparison_status,
        "reviewed_by_human": True,
        "reviewed_at": reviewed_at,
        "reviewed_temporal_status": reviewed_temporal_status,
        "review_rationale": rationale,
    }



def _validate_currentness_evidence(
    *,
    root: Path,
    raw: object,
    registration_path: str,
    document: Mapping[str, Any],
    observation_review: Mapping[str, Any] | None,
    temporal_status: str,
) -> dict[str, Any] | None:
    """Bind promotion to structured, immutable currentness evidence.

    The evidence record remains evidence only. The overlay is still the only
    temporal decision-maker; this guard merely prevents reviewer-only promotion.
    """
    if raw is None:
        if temporal_status == "current_observed_reviewed":
            raise DocumentIdentityResolutionError(
                "current_observed_reviewed requires currentness_evidence_path"
            )
        return None
    if temporal_status != "current_observed_reviewed":
        raise DocumentIdentityResolutionError(
            "currentness_evidence_path is only supported for current_observed_reviewed"
        )
    evidence_path = _safe_relative_path(raw, "currentness_evidence_path")
    try:
        return DocumentCurrentnessEvidenceRecord.load_and_validate_for_overlay(
            repository_root=root,
            evidence_path=evidence_path,
            registration_path=registration_path,
            document=document,
            observation_review=observation_review,
        )
    except DocumentCurrentnessEvidenceError as exc:
        raise DocumentIdentityResolutionError(str(exc)) from exc


def _validate_signals(signals: list[Any], *, resolution_status: str, temporal_status: str) -> list[dict[str, str]]:
    if not signals:
        raise DocumentIdentityResolutionError("identity_signals must not be empty")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    has_uin = False
    has_manual = False
    has_temporal = False
    for index, raw in enumerate(signals):
        item = _mapping(raw, f"identity_signals[{index}]")
        signal_type = _nonempty(item.get("signal_type"), f"identity_signals[{index}].signal_type")
        verification = _nonempty(item.get("verification"), f"identity_signals[{index}].verification")
        evidence_reference = _nonempty(item.get("evidence_reference"), f"identity_signals[{index}].evidence_reference")
        if signal_type not in _ALLOWED_SIGNAL_TYPES:
            raise DocumentIdentityResolutionError(f"unsupported signal_type {signal_type!r}")
        if verification not in _ALLOWED_SIGNAL_VERIFICATION:
            raise DocumentIdentityResolutionError(f"unsupported signal verification {verification!r}")
        key = (signal_type, evidence_reference)
        if key in seen:
            raise DocumentIdentityResolutionError("identity_signals must not contain duplicate type/reference pairs")
        seen.add(key)
        has_uin = has_uin or signal_type == "uin_exact_match"
        has_manual = has_manual or verification == "manual_reviewed"
        has_temporal = has_temporal or signal_type in {"effective_date_match", "version_label_match"}
        normalized.append({"signal_type": signal_type, "verification": verification, "evidence_reference": evidence_reference})
    if resolution_status == "resolved" and not (has_uin and has_manual):
        raise DocumentIdentityResolutionError("resolved requires both a uin_exact_match signal and at least one manual_reviewed signal")
    if temporal_status == "current" and not has_temporal:
        raise DocumentIdentityResolutionError("current temporal_status requires effective_date_match or version_label_match evidence")
    return normalized


class DocumentIdentityResolutionOverlay:
    """Builds a reviewable, non-mutating document identity overlay."""

    def build_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path) -> DocumentIdentityResolutionResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Overlay specification was not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DocumentIdentityResolutionError(f"Invalid overlay specification JSON: {path}") from exc
        return self.build(spec=_mapping(raw, "overlay_spec"), repository_root=repository_root)

    def build(self, *, spec: Mapping[str, Any], repository_root: str | Path, resolved_at: str | None = None) -> DocumentIdentityResolutionResult:
        root = Path(repository_root).resolve()
        spec = _mapping(spec, "overlay_spec")
        if spec.get("schema_version") != "1.0":
            raise DocumentIdentityResolutionError("overlay_spec.schema_version must be 1.0")
        if spec.get("overlay_type") != "document_identity_resolution_overlay_v1":
            raise DocumentIdentityResolutionError("overlay_spec.overlay_type must be document_identity_resolution_overlay_v1")
        if spec.get("reviewed_by_human") is not True:
            raise DocumentIdentityResolutionError("overlay_spec.reviewed_by_human must be true")

        product = _load_product_identity_reference(root, spec.get("product_identity_reference"))
        documents = _list(spec.get("documents"), "overlay_spec.documents")
        if not documents:
            raise DocumentIdentityResolutionError("overlay_spec.documents must not be empty")

        seen_versions: set[str] = set()
        output_docs: list[dict[str, Any]] = []
        for index, raw in enumerate(documents):
            item = _mapping(raw, f"documents[{index}]")
            registration_path = _safe_relative_path(item.get("registration_path"), f"documents[{index}].registration_path")
            registration = _load_json(root, registration_path, f"registration[{index}]")
            document = _mapping(registration.get("document"), f"registration[{index}].document")
            version_id = _nonempty(document.get("document_version_id"), f"registration[{index}].document.document_version_id")
            if version_id in seen_versions:
                raise DocumentIdentityResolutionError("documents must not repeat document_version_id")
            seen_versions.add(version_id)
            document_type = _nonempty(document.get("document_type"), f"registration[{index}].document.document_type")
            if document_type not in _ALLOWED_DOCUMENT_TYPES:
                raise DocumentIdentityResolutionError(f"unsupported document_type {document_type!r}")
            temporal_status = _nonempty(item.get("temporal_status"), f"documents[{index}].temporal_status")
            resolution_status = _nonempty(item.get("resolution_status"), f"documents[{index}].resolution_status")
            if temporal_status not in _ALLOWED_TEMPORAL_STATUSES:
                raise DocumentIdentityResolutionError(f"unsupported temporal_status {temporal_status!r}")
            if resolution_status not in _ALLOWED_RESOLUTION_STATUSES:
                raise DocumentIdentityResolutionError(f"unsupported resolution_status {resolution_status!r}")
            rationale = _nonempty(item.get("review_rationale"), f"documents[{index}].review_rationale")
            signals = _validate_signals(
                _list(item.get("identity_signals"), f"documents[{index}].identity_signals"),
                resolution_status=resolution_status, temporal_status=temporal_status,
            )
            classification_path = None
            source_classification = None
            if item.get("classification_manifest_path") is not None:
                classification_path = _safe_relative_path(item.get("classification_manifest_path"), f"documents[{index}].classification_manifest_path")
                source_classification = _classification_for_version(root, classification_path, version_id)
            observation_review = _validate_source_observation_review(
                root=root,
                raw=item.get("source_observation_review"),
                registration_path=registration_path,
                document=document,
                temporal_status=temporal_status,
            )
            currentness_evidence = _validate_currentness_evidence(
                root=root,
                raw=item.get("currentness_evidence_path"),
                registration_path=registration_path,
                document=document,
                observation_review=observation_review,
                temporal_status=temporal_status,
            )
            reusable_generic = source_classification == _REUSABLE_CLASSIFICATION
            evidence_review_eligibility = _ELIGIBLE if resolution_status == "resolved" and reusable_generic else _BLOCKED
            current_entitlement_publication_eligibility = (
                "eligible"
                if evidence_review_eligibility == _ELIGIBLE
                and temporal_status in {"current", "current_observed_reviewed"}
                else "blocked"
            )

            capture_out = None
            if item.get("capture_provenance") is not None:
                capture_raw = _mapping(item.get("capture_provenance"), f"documents[{index}].capture_provenance")
                capture_out = {}
                for field in ("source_url", "source_page_url", "capture_reference"):
                    if capture_raw.get(field) is not None:
                        capture_out[field] = _nonempty(capture_raw.get(field), f"documents[{index}].capture_provenance.{field}")
            output_docs.append({
                "document_version_link": {
                    "document_id": _nonempty(document.get("document_id"), f"registration[{index}].document.document_id"),
                    "document_version_id": version_id,
                    "source_document_id": _nonempty(document.get("source_document_id"), f"registration[{index}].document.source_document_id"),
                    "content_sha256": _nonempty(document.get("content_sha256"), f"registration[{index}].document.content_sha256"),
                    "document_type": document_type,
                    "source_issued_label": document.get("source_issued_label"),
                    "registration_path": registration_path,
                    "registration_sha256": _sha256_file((root / registration_path).resolve()),
                    "classification_manifest_path": classification_path,
                    "source_classification": source_classification,
                    "capture_provenance": capture_out,
                },
                "identity_resolution": {
                    "resolution_status": resolution_status,
                    "temporal_status": temporal_status,
                    "identity_signals": signals,
                    "review_rationale": rationale,
                    "evidence_review_eligibility": evidence_review_eligibility,
                    "current_entitlement_publication_eligibility": current_entitlement_publication_eligibility,
                    "source_observation_review": observation_review,
                    "currentness_evidence": currentness_evidence,
                },
            })
        manifest = {
            "schema_version": "1.0",
            "overlay_type": "document_identity_resolution_overlay_v1",
            "overlay_status": "reviewed_document_identity_resolution_recorded_not_published",
            "product_identity_reference": product,
            "documents": output_docs,
            "guardrails": [
                "This overlay is non-mutating and does not replace source registration, document classification, canonical projection, or publication artifacts.",
                "A matching UIN is a strong product-identity signal but does not establish document-version compatibility by itself.",
                "Only resolved reusable-generic documents are eligible for evidence review.",
                "Historical, replaced, compatibility-unverified, unknown, and observation-failed documents cannot establish current product entitlement publication.",
                "A source-observation record is evidence only. It can affect temporal status only through an explicit human review bound to the same immutable registered document version.",
                "current_observed_reviewed additionally requires a valid immutable currentness-evidence record with positive official currentness proof; reviewer assertion alone is insufficient.",
                "This overlay records identity and temporal review; it does not itself publish a product fact or legal conclusion.",
            ],
            "reviewed_by_human": True,
            "resolved_at": resolved_at or datetime.now(timezone.utc).isoformat(),
        }
        return DocumentIdentityResolutionResult(manifest=manifest)

    def write_output(self, result: DocumentIdentityResolutionResult, *, repository_root: str | Path, output_path: str | Path) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise DocumentIdentityResolutionError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
