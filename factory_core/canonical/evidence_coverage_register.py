"""P2.8-A — read-only registry-backed evidence coverage register.

This module derives a coverage view from governed artifacts. It does not create
facts, modify reviews, publish assertions, or evaluate policy rules.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


class EvidenceCoverageRegisterError(ValueError):
    """Raised when governed coverage inputs are incomplete or inconsistent."""


@dataclass(frozen=True)
class EvidenceCoverageRegisterResult:
    manifest: Mapping[str, Any]


_ALLOWED_APPLICABILITY = {
    "explicitly_present",
    "explicitly_not_applicable",
    "not_stated",
    "unknown_pending_evidence",
}


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceCoverageRegisterError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise EvidenceCoverageRegisterError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceCoverageRegisterError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise EvidenceCoverageRegisterError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


def _load_json(root: Path, relative_path: str, label: str) -> tuple[Mapping[str, Any], str]:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise EvidenceCoverageRegisterError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise FileNotFoundError(f"{label} was not found: {relative_path}")
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceCoverageRegisterError(f"{label} is not valid UTF-8 JSON") from exc
    return _mapping(parsed, label), sha256(raw).hexdigest()


def _stable_id(prefix: str, *parts: str) -> str:
    return f"{prefix}_{sha256('|'.join(parts).encode('utf-8')).hexdigest()[:16]}"


def _classification_index(root: Path, path: str) -> tuple[dict[str, Mapping[str, Any]], str]:
    manifest, manifest_sha = _load_json(root, path, "classification_manifest")
    if manifest.get("classification_status") != "reviewed_document_classifications_recorded_not_published":
        raise EvidenceCoverageRegisterError("classification_manifest is not reviewed")
    result: dict[str, Mapping[str, Any]] = {}
    for raw in _items(manifest.get("documents"), "classification_manifest.documents"):
        item = _mapping(raw, "classification_manifest.documents[]")
        version_id = _text(item.get("document_version_id"), "classification.document_version_id")
        if version_id in result:
            raise EvidenceCoverageRegisterError("classification document_version_id must be unique")
        result[version_id] = item
    return result, manifest_sha


def _resolve_classification_registrations(
    root: Path,
    classifications: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    registrations: dict[str, Mapping[str, Any]] = {}
    for version_id, entry in classifications.items():
        registration_path = _safe_relative_path(entry.get("registration_path"), "classification.registration_path")
        registration, _ = _load_json(root, registration_path, f"registration[{version_id}]")
        document = _mapping(registration.get("document"), f"registration[{version_id}].document")
        if document.get("document_version_id") != version_id:
            raise EvidenceCoverageRegisterError(f"registration document version mismatch for {version_id}")
        registrations[version_id] = registration
    return registrations


def _classify_authority(
    authoritative_concept_ids: set[str],
    authoritative: list[Mapping[str, Any]],
    projections: list[Mapping[str, Any]],
) -> tuple[str, list[Mapping[str, Any]]]:
    authoritative_matches = [
        item for item in authoritative if item["concept_id"] in authoritative_concept_ids
    ]
    if authoritative_matches:
        return "authoritative", authoritative_matches
    projection_matches = [
        item for item in projections if item["concept_id"] in authoritative_concept_ids
    ]
    if projection_matches:
        return "evidence_assembled_unpublished", projection_matches
    return "no_authoritative_assertion", []


def _concept_reconciliation_index(
    raw_reconciliations: object,
    catalog_ids: set[str],
) -> dict[str, Mapping[str, Any]]:
    """Return explicit reviewed source-concept mappings keyed by coverage concept.

    Reconciliation is intentionally exact and spec-declared. It never attempts
    fuzzy or lexical matching between old feature IDs and canonical concept IDs.
    """
    reconciliations = _items(raw_reconciliations, "product.concept_reconciliations")
    result: dict[str, Mapping[str, Any]] = {}
    seen_authoritative_ids: set[str] = set()
    seen_applicability_ids: set[str] = set()

    for raw in reconciliations:
        item = _mapping(raw, "concept_reconciliations[]")
        coverage_concept_id = _text(
            item.get("coverage_concept_id"),
            "concept_reconciliation.coverage_concept_id",
        )
        if coverage_concept_id not in catalog_ids:
            raise EvidenceCoverageRegisterError(
                "concept reconciliation coverage_concept_id must exist in concept_catalog"
            )
        if coverage_concept_id in result:
            raise EvidenceCoverageRegisterError(
                "concept reconciliation coverage_concept_id must be unique"
            )

        authoritative_ids = {
            _text(value, "concept_reconciliation.authoritative_concept_ids[]")
            for value in _items(
                item.get("authoritative_concept_ids", []),
                "concept_reconciliation.authoritative_concept_ids",
            )
        }
        applicability_ids = {
            _text(value, "concept_reconciliation.applicability_feature_ids[]")
            for value in _items(
                item.get("applicability_feature_ids", []),
                "concept_reconciliation.applicability_feature_ids",
            )
        }
        if not authoritative_ids and not applicability_ids:
            raise EvidenceCoverageRegisterError(
                "concept reconciliation requires authoritative_concept_ids or applicability_feature_ids"
            )
        if seen_authoritative_ids.intersection(authoritative_ids):
            raise EvidenceCoverageRegisterError(
                "authoritative source concept ids may map to only one coverage concept"
            )
        if seen_applicability_ids.intersection(applicability_ids):
            raise EvidenceCoverageRegisterError(
                "applicability source feature ids may map to only one coverage concept"
            )

        seen_authoritative_ids.update(authoritative_ids)
        seen_applicability_ids.update(applicability_ids)
        result[coverage_concept_id] = {
            "authoritative_concept_ids": authoritative_ids,
            "applicability_feature_ids": applicability_ids,
        }
    return result


class EvidenceCoverageRegister:
    """Builds a separate, read-only coverage register from governed artifacts."""

    def build_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
    ) -> EvidenceCoverageRegisterResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Coverage register specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceCoverageRegisterError("Coverage register specification is not valid UTF-8 JSON") from exc
        return self.build(spec=_mapping(spec, "coverage_register_spec"), repository_root=repository_root)

    def build(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        built_at: str | None = None,
    ) -> EvidenceCoverageRegisterResult:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"repository_root was not found: {root}")
        if spec.get("schema_version") != "1.0":
            raise EvidenceCoverageRegisterError("coverage_register_spec.schema_version must be 1.0")
        if spec.get("register_type") != "registry_backed_evidence_coverage_register_v1":
            raise EvidenceCoverageRegisterError("coverage_register_spec.register_type is invalid")
        if spec.get("reviewed_by_human") is not True:
            raise EvidenceCoverageRegisterError("coverage_register_spec.reviewed_by_human must be true")

        products = _items(spec.get("products"), "products")
        if not products:
            raise EvidenceCoverageRegisterError("products must be non-empty")

        seen_versions: set[str] = set()
        output_products: list[dict[str, Any]] = []

        for product_index, raw_product in enumerate(products):
            product = _mapping(raw_product, f"products[{product_index}]")
            product_version_id = _text(product.get("product_version_id"), "product.product_version_id")
            if product_version_id in seen_versions:
                raise EvidenceCoverageRegisterError("products.product_version_id must be unique")
            seen_versions.add(product_version_id)

            classification_path = _safe_relative_path(
                product.get("classification_manifest_path"), "product.classification_manifest_path"
            )
            classifications, classification_sha = _classification_index(root, classification_path)
            _resolve_classification_registrations(root, classifications)

            catalog = _items(product.get("concept_catalog"), "product.concept_catalog")
            if not catalog:
                raise EvidenceCoverageRegisterError("product.concept_catalog must be non-empty")
            catalog_ids: list[str] = []
            catalog_metadata: dict[str, Mapping[str, Any]] = {}
            for raw_concept in catalog:
                concept = _mapping(raw_concept, "concept_catalog[]")
                concept_id = _text(concept.get("concept_id"), "concept_catalog.concept_id")
                if concept_id in catalog_metadata:
                    raise EvidenceCoverageRegisterError("concept_catalog.concept_id must be unique within product")
                catalog_ids.append(concept_id)
                catalog_metadata[concept_id] = concept
            reconciliations = _concept_reconciliation_index(
                product.get("concept_reconciliations", []),
                set(catalog_ids),
            )

            authoritative: list[dict[str, Any]] = []
            for raw_source in _items(product.get("authoritative_sources", []), "product.authoritative_sources"):
                source = _mapping(raw_source, "authoritative_sources[]")
                artifact_path = _safe_relative_path(source.get("artifact_path"), "authoritative_source.artifact_path")
                receipt_path = _safe_relative_path(source.get("receipt_path"), "authoritative_source.receipt_path")
                artifact, artifact_sha = _load_json(root, artifact_path, "authoritative_artifact")
                receipt, _ = _load_json(root, receipt_path, "authoritative_receipt")
                if artifact.get("artifact_type") != "canonical_authoritative_generic_legal_assertions_v1":
                    raise EvidenceCoverageRegisterError("authoritative artifact type is invalid")
                if artifact.get("publication_status") != "authoritative":
                    raise EvidenceCoverageRegisterError("authoritative artifact is not authoritative")
                if receipt.get("receipt_type") != "canonical_authoritative_publication_receipt_v1":
                    raise EvidenceCoverageRegisterError("authoritative receipt type is invalid")
                if receipt.get("artifact_sha256") != artifact_sha:
                    raise EvidenceCoverageRegisterError("authoritative receipt artifact hash mismatch")
                if artifact.get("product_version_id") != product_version_id or receipt.get("product_version_id") != product_version_id:
                    raise EvidenceCoverageRegisterError("authoritative artifact product version mismatch")
                spans = {
                    _text(item.get("evidence_span_id"), "authoritative.evidence_span_id"): _mapping(item, "authoritative.evidence_span")
                    for item in _items(artifact.get("evidence_spans"), "authoritative_artifact.evidence_spans")
                }
                for raw_assertion in _items(artifact.get("assertions"), "authoritative_artifact.assertions"):
                    assertion = _mapping(raw_assertion, "authoritative_assertion")
                    if assertion.get("publication_status") != "authoritative":
                        raise EvidenceCoverageRegisterError("non-authoritative assertion in authoritative artifact")
                    if assertion.get("product_version_id") != product_version_id:
                        raise EvidenceCoverageRegisterError("authoritative assertion product version mismatch")
                    concept_id = _text(assertion.get("concept_id"), "authoritative_assertion.concept_id")
                    evidence_ids = [_text(item, "authoritative_assertion.evidence_span_ids[]") for item in _items(assertion.get("evidence_span_ids"), "authoritative_assertion.evidence_span_ids")]
                    if not evidence_ids:
                        raise EvidenceCoverageRegisterError("authoritative assertion requires evidence spans")
                    document_versions: list[str] = []
                    for evidence_id in evidence_ids:
                        span = spans.get(evidence_id)
                        if span is None:
                            raise EvidenceCoverageRegisterError("authoritative assertion references missing evidence span")
                        version_id = _text(span.get("document_version_id"), "authoritative_evidence.document_version_id")
                        entry = classifications.get(version_id)
                        if entry is None:
                            raise EvidenceCoverageRegisterError("authoritative evidence document version is absent from classification")
                        if entry.get("classification") != "reusable_generic" or entry.get("reuse_action") != "reusable_evidence_candidate":
                            raise EvidenceCoverageRegisterError("authoritative evidence is not reusable generic")
                        document_versions.append(version_id)
                    authoritative.append({
                        "concept_id": concept_id,
                        "assertion_id": _text(assertion.get("assertion_id"), "authoritative_assertion.assertion_id"),
                        "artifact_path": artifact_path,
                        "artifact_sha256": artifact_sha,
                        "evidence_span_ids": evidence_ids,
                        "document_version_ids": sorted(set(document_versions)),
                    })

            projections: list[dict[str, Any]] = []
            for raw_source in _items(product.get("unpublished_projection_sources", []), "product.unpublished_projection_sources"):
                source = _mapping(raw_source, "unpublished_projection_sources[]")
                projection_path = _safe_relative_path(source.get("projection_path"), "projection_source.projection_path")
                projection, projection_sha = _load_json(root, projection_path, "canonical_projection")
                report = _mapping(projection.get("projection_report"), "canonical_projection.projection_report")
                if report.get("projection_status") != "validated_read_only_canonical_projection_not_published":
                    raise EvidenceCoverageRegisterError("projection is not validated unpublished")
                bundle = _mapping(projection.get("canonical_bundle"), "canonical_projection.canonical_bundle")
                for raw_assertion in _items(bundle.get("assertions"), "canonical_projection.assertions"):
                    assertion = _mapping(raw_assertion, "canonical_projection.assertion")
                    if assertion.get("publication_status") != "unpublished":
                        continue
                    if assertion.get("product_version_id") != product_version_id:
                        raise EvidenceCoverageRegisterError("projection assertion product version mismatch")
                    projections.append({
                        "concept_id": _text(assertion.get("concept_id"), "projection_assertion.concept_id"),
                        "assertion_id": _text(assertion.get("assertion_id"), "projection_assertion.assertion_id"),
                        "projection_path": projection_path,
                        "projection_sha256": projection_sha,
                    })

            applicability_path_raw = product.get("feature_applicability_path")
            applicability_by_feature: dict[str, Mapping[str, Any]] = {}
            assessment_reference: dict[str, Any] | None = None
            if applicability_path_raw is not None:
                applicability_path = _safe_relative_path(applicability_path_raw, "feature_applicability_path")
                assessment, assessment_sha = _load_json(root, applicability_path, "feature_applicability")
                if assessment.get("artifact_type") != "generic_feature_applicability_assessment_v1":
                    raise EvidenceCoverageRegisterError("feature applicability artifact type is invalid")
                if assessment.get("assessment_status") != "reviewed_not_published":
                    raise EvidenceCoverageRegisterError("feature applicability assessment is not reviewed_not_published")
                if assessment.get("product_version_id") != product_version_id:
                    raise EvidenceCoverageRegisterError("feature applicability product version mismatch")
                reviewed_ids = [_text(item, "reviewed_source_document_version_ids[]") for item in _items(assessment.get("reviewed_source_document_version_ids"), "reviewed_source_document_version_ids")]
                resolved_ids = sorted(set(reviewed_ids).intersection(classifications.keys()))
                unresolved_ids = sorted(set(reviewed_ids).difference(classifications.keys()))
                integrity = "registry_resolved" if not unresolved_ids else "partially_unresolved"
                assessment_reference = {
                    "path": applicability_path,
                    "sha256": assessment_sha,
                    "review_integrity_status": integrity,
                    "resolved_document_version_ids": resolved_ids,
                    "unresolved_document_version_ids": unresolved_ids,
                }
                for raw_feature in _items(assessment.get("features"), "feature_applicability.features"):
                    feature = _mapping(raw_feature, "feature_applicability.feature")
                    feature_id = _text(feature.get("feature_id"), "feature_applicability.feature_id")
                    status = _text(feature.get("applicability_status"), "feature_applicability.applicability_status")
                    if status not in _ALLOWED_APPLICABILITY:
                        raise EvidenceCoverageRegisterError("feature applicability status is invalid")
                    applicability_by_feature[feature_id] = feature

            entries: list[dict[str, Any]] = []
            for concept_id in catalog_ids:
                reconciliation = reconciliations.get(concept_id, {})
                authoritative_concept_ids = set(
                    reconciliation.get("authoritative_concept_ids", {concept_id})
                )
                applicability_feature_ids = set(
                    reconciliation.get("applicability_feature_ids", {concept_id})
                )
                # Exact identity is the default. A reviewed reconciliation may map
                # legacy feature IDs or another canonical source concept to this
                # coverage concept, but never by heuristic matching.
                if not reconciliation:
                    authoritative_concept_ids = {concept_id}
                    applicability_feature_ids = {concept_id}

                authority_status, support = _classify_authority(
                    authoritative_concept_ids,
                    authoritative,
                    projections,
                )
                matched_features = [
                    applicability_by_feature[feature_id]
                    for feature_id in sorted(applicability_feature_ids)
                    if feature_id in applicability_by_feature
                ]
                if len(matched_features) > 1:
                    raise EvidenceCoverageRegisterError(
                        "multiple applicability features map to one coverage concept"
                    )
                feature = matched_features[0] if matched_features else None
                if feature is None:
                    applicability_status = "not_assessed"
                    applicability_review_integrity_status = "not_reviewed"
                    gap_reason = _text(
                        catalog_metadata[concept_id].get("not_assessed_reason"),
                        "concept_catalog.not_assessed_reason",
                    )
                    next_evidence_requirement = catalog_metadata[concept_id].get("default_next_evidence_requirement")
                else:
                    applicability_status = _text(feature.get("applicability_status"), "feature.applicability_status")
                    applicability_review_integrity_status = (
                        assessment_reference["review_integrity_status"]
                        if assessment_reference
                        else "not_reviewed"
                    )
                    if applicability_status == "unknown_pending_evidence":
                        gap_reason = _text(feature.get("reviewed_statement"), "feature.reviewed_statement")
                        next_evidence_requirement = [
                            _text(item, "feature.required_evidence_types[]")
                            for item in _items(feature.get("required_evidence_types"), "feature.required_evidence_types")
                        ]
                    elif applicability_status == "not_stated":
                        gap_reason = _text(feature.get("reviewed_statement"), "feature.reviewed_statement")
                        next_evidence_requirement = "no_conclusion_from_silence"
                    else:
                        gap_reason = None
                        next_evidence_requirement = None

                if authority_status == "authoritative":
                    coverage_state = "authoritative"
                    integrity = "registry_resolved"
                    # A not_stated feature may deliberately defer to the
                    # authoritative assertion; it is not a coverage gap.
                    if applicability_status == "not_stated":
                        gap_reason = None
                        next_evidence_requirement = "not_required_for_authority_status"
                elif authority_status == "evidence_assembled_unpublished":
                    coverage_state = "evidence_assembled_unpublished"
                    integrity = "registry_resolved"
                elif feature is not None:
                    coverage_state = "applicability_reviewed"
                    integrity = applicability_review_integrity_status
                else:
                    coverage_state = "not_assessed"
                    integrity = applicability_review_integrity_status

                entries.append({
                    "concept_id": concept_id,
                    "coverage_state": coverage_state,
                    "knowledge_authority_status": authority_status,
                    "applicability_status": applicability_status,
                    "review_integrity_status": integrity,
                    "applicability_review_integrity_status": applicability_review_integrity_status,
                    "source_concept_ids": {
                        "authoritative_concept_ids": sorted(authoritative_concept_ids),
                        "applicability_feature_ids": sorted(applicability_feature_ids),
                    },
                    "supporting_artifacts": support,
                    "gap_reason": gap_reason,
                    "next_evidence_requirement": next_evidence_requirement,
                })

            output_products.append({
                "product_version_id": product_version_id,
                "classification_manifest_path": classification_path,
                "classification_manifest_sha256": classification_sha,
                "feature_applicability_assessment": assessment_reference,
                "concepts": entries,
            })

        return EvidenceCoverageRegisterResult(manifest={
            "schema_version": "1.0",
            "register_type": "registry_backed_evidence_coverage_register_v1",
            "register_status": "read_only_coverage_register_built",
            "built_at": built_at or datetime.now(timezone.utc).isoformat(),
            "products": output_products,
            "guardrails": [
                "The register is derived read-only from governed artifacts and does not publish, mutate, or evaluate rules.",
                "Not assessed and unknown pending evidence are distinct states; neither may be treated as a negative product conclusion.",
                "An authoritative legal mechanism does not establish an unproven product entitlement value.",
                "Feature applicability review integrity is registry_resolved only when every reviewed document version is present in the reviewed classification manifest.",       
                "Concept reconciliation is explicit, reviewed, and exact; it never uses fuzzy matching or rewrites source artifacts.",
                "Legacy coverage scores and unmanaged reports are not inputs to this register.",
            ],
        })

    def write_output(
        self,
        result: EvidenceCoverageRegisterResult,
        *,
        repository_root: str | Path,
        output_path: str | Path,
    ) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise EvidenceCoverageRegisterError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target