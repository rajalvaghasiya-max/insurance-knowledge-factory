"""Reviewed binding of generic legal insurance conditions.

This module binds reusable *mechanism-level* legal conditions from approved
generic sources. It intentionally cannot create a Plan / room-category / ICU-limit
entitlement: those require separately reviewed Product Benefit Table or CIS evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class GenericLegalConditionBindingError(ValueError):
    """Raised when a reviewed generic legal binding is incomplete or unsafe."""


@dataclass(frozen=True)
class GenericLegalConditionBindingResult:
    manifest: Mapping[str, Any]


_ALLOWED_ASSERTION_TYPES = frozenset({
    "room_rent_rateable_proportion_condition",
    "icu_proportionate_deduction_exception",
    "conditional_copayment_rule",
})
_BLOCKED_ENTITLEMENT_WORDS = ("room_category_constraint", "room_rent_limit", "icu_room_rent_exception")


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GenericLegalConditionBindingError(f"{label} must be a JSON object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GenericLegalConditionBindingError(f"{label} must be a JSON array")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenericLegalConditionBindingError(f"{label} must be a non-empty string")
    return value.strip()


def _safe_relative_path(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise GenericLegalConditionBindingError(f"{label} must be a safe repository-relative path")
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
        raise GenericLegalConditionBindingError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise GenericLegalConditionBindingError(f"{label} was not found: {relative_path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GenericLegalConditionBindingError(f"{label} is not valid JSON: {relative_path}") from exc
    return _mapping(parsed, label)


def _candidate_index(registration: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
    candidates = _list(review.get("candidates"), "registration.evidence_review.candidates")
    result: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(candidates):
        candidate = _mapping(raw, f"registration.evidence_review.candidates[{index}]")
        candidate_id = _nonempty(candidate.get("candidate_id"), f"candidate[{index}].candidate_id")
        result[candidate_id] = candidate
    return result


class GenericLegalConditionBinding:
    """Builds a non-published reviewed binding manifest for generic legal conditions."""

    def bind_from_spec_file(self, *, spec_path: str | Path, repository_root: str | Path) -> GenericLegalConditionBindingResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Binding specification was not found: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GenericLegalConditionBindingError(f"Invalid binding specification JSON: {path}") from exc
        return self.bind(spec=_mapping(raw, "binding_spec"), repository_root=repository_root)

    def bind(self, *, spec: Mapping[str, Any], repository_root: str | Path, bound_at: str | None = None) -> GenericLegalConditionBindingResult:
        root = Path(repository_root).resolve()
        spec = _mapping(spec, "binding_spec")
        if spec.get("schema_version") != "1.0":
            raise GenericLegalConditionBindingError("binding_spec.schema_version must be 1.0")
        if spec.get("binding_type") != "generic_legal_condition_binding_v1":
            raise GenericLegalConditionBindingError("binding_spec.binding_type must be generic_legal_condition_binding_v1")
        if spec.get("reviewed_by_human") is not True:
            raise GenericLegalConditionBindingError("binding_spec.reviewed_by_human must be true")

        bundle_path = _safe_relative_path(spec.get("generic_source_bundle_path"), "generic_source_bundle_path")
        bundle = _load_json(root, bundle_path, "generic_source_bundle")
        if bundle.get("registration_type") != "generic_source_registration_bundle_v1":
            raise GenericLegalConditionBindingError("generic_source_bundle must be a P2.5-G registration bundle")
        context = _mapping(bundle.get("product_context"), "generic_source_bundle.product_context")
        if context.get("source_scope") != "reusable_generic":
            raise GenericLegalConditionBindingError("generic source bundle must have reusable_generic scope")

        source_records: dict[str, tuple[Mapping[str, Any], Mapping[str, Any]]] = {}
        for index, raw_source in enumerate(_list(bundle.get("sources"), "generic_source_bundle.sources")):
            source = _mapping(raw_source, f"generic_source_bundle.sources[{index}]")
            doc_id = _nonempty(source.get("document_id"), f"sources[{index}].document_id")
            role = _nonempty(source.get("authority_role"), f"sources[{index}].authority_role")
            registration_path = _safe_relative_path(source.get("registration_output_path"), f"sources[{index}].registration_output_path")
            registration = _load_json(root, registration_path, f"source_registration[{doc_id}]")
            if registration.get("registration_status") != "source_registered_evidence_review_required":
                raise GenericLegalConditionBindingError(f"source_registration[{doc_id}] is not review-ready")
            document = _mapping(registration.get("document"), f"source_registration[{doc_id}].document")
            if document.get("document_id") != doc_id:
                raise GenericLegalConditionBindingError(f"source registration document_id mismatch for {doc_id}")
            if document.get("document_version_id") != source.get("document_version_id"):
                raise GenericLegalConditionBindingError(f"source registration document_version_id mismatch for {doc_id}")
            source_records[doc_id] = (source, registration)

        assertions = _list(spec.get("assertions"), "binding_spec.assertions")
        if not assertions:
            raise GenericLegalConditionBindingError("binding_spec.assertions must not be empty")
        seen_ids: set[str] = set()
        bound_assertions: list[dict[str, Any]] = []
        for index, raw_assertion in enumerate(assertions):
            assertion = _mapping(raw_assertion, f"assertions[{index}]")
            assertion_id = _nonempty(assertion.get("assertion_id"), f"assertions[{index}].assertion_id")
            if assertion_id in seen_ids:
                raise GenericLegalConditionBindingError("assertion_id values must be unique")
            seen_ids.add(assertion_id)
            assertion_type = _nonempty(assertion.get("assertion_type"), f"assertions[{index}].assertion_type")
            if assertion_type not in _ALLOWED_ASSERTION_TYPES:
                raise GenericLegalConditionBindingError(f"assertion_type {assertion_type!r} is not permitted by the generic legal condition binding contract")
            semantic_key = _nonempty(assertion.get("semantic_key"), f"assertions[{index}].semantic_key")
            if any(word in semantic_key for word in _BLOCKED_ENTITLEMENT_WORDS):
                raise GenericLegalConditionBindingError("generic legal condition binding cannot bind a room/ICU entitlement; acquire a Product Benefit Table or CIS")
            statement = _nonempty(assertion.get("reviewed_statement"), f"assertions[{index}].reviewed_statement")
            selections = _list(assertion.get("evidence_selections"), f"assertions[{index}].evidence_selections")
            if not selections:
                raise GenericLegalConditionBindingError(f"assertions[{index}] requires at least one evidence selection")

            bound_evidence: list[dict[str, Any]] = []
            primary_count = 0
            for selection_index, raw_selection in enumerate(selections):
                selection = _mapping(raw_selection, f"assertions[{index}].evidence_selections[{selection_index}]")
                doc_id = _nonempty(selection.get("document_id"), "evidence_selection.document_id")
                if doc_id not in source_records:
                    raise GenericLegalConditionBindingError(f"evidence selection references unregistered source {doc_id!r}")
                source, registration = source_records[doc_id]
                role = source["authority_role"]
                if role == "discovery_only":
                    raise GenericLegalConditionBindingError("discovery-only sources cannot bind a reusable legal assertion")
                if role == "primary_legal":
                    primary_count += 1
                candidate_id = _nonempty(selection.get("candidate_id"), "evidence_selection.candidate_id")
                candidates = _candidate_index(registration)
                if candidate_id not in candidates:
                    raise GenericLegalConditionBindingError(f"candidate {candidate_id!r} not found for {doc_id}")
                candidate = candidates[candidate_id]
                expected_hash = _nonempty(selection.get("candidate_text_sha256"), "evidence_selection.candidate_text_sha256")
                actual_hash = _nonempty(candidate.get("text_sha256"), "candidate.text_sha256")
                if expected_hash != actual_hash:
                    raise GenericLegalConditionBindingError(f"candidate text hash mismatch for {doc_id}:{candidate_id}")
                range_value = _mapping(candidate.get("source_char_range"), "candidate.source_char_range")
                bound_evidence.append({
                    "document_id": doc_id,
                    "document_version_id": source["document_version_id"],
                    "authority_role": role,
                    "candidate_id": candidate_id,
                    "source_page": candidate.get("source_page"),
                    "source_char_range": {"start": range_value.get("start"), "end": range_value.get("end")},
                    "candidate_text_sha256": actual_hash,
                })
            if primary_count != 1:
                raise GenericLegalConditionBindingError(f"assertions[{index}] requires exactly one primary_legal evidence selection")
            bound_assertions.append({
                "assertion_id": assertion_id,
                "assertion_type": assertion_type,
                "semantic_key": semantic_key,
                "reviewed_statement": statement,
                "scope": "reusable_generic_product_legal_condition",
                "evidence": bound_evidence,
                "publication_status": "bound_not_published",
            })

        timestamp = bound_at or datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema_version": "1.0",
            "binding_type": "generic_legal_condition_binding_v1",
            "binding_status": "reviewed_generic_legal_conditions_bound_not_published",
            "product_context": {
                "insurer_id": context.get("insurer_id"),
                "product_id": context.get("product_id"),
                "product_display_name": context.get("product_display_name"),
                "source_scope": "reusable_generic",
            },
            "generic_source_bundle_path": bundle_path,
            "generic_source_bundle_sha256": _sha256_file((root / bundle_path).resolve()),
            "assertions": bound_assertions,
            "bound_at": timestamp,
            "reviewed_by_human": True,
            "guardrails": [
                "No policy-instance or group-specific source may be selected.",
                "At least one primary legal source is required for each assertion.",
                "Brochure/discovery-only sources cannot establish reusable legal assertions.",
                "Generic legal condition binding binds legal mechanisms only; product entitlement values remain blocked pending Product Benefit Table or CIS evidence.",
                "This manifest does not publish or modify any conditional-rule artifact.",
            ],
        }
        return GenericLegalConditionBindingResult(manifest=manifest)

    def write_output(self, result: GenericLegalConditionBindingResult, *, repository_root: str | Path, output_path: str | Path) -> Path:
        root = Path(repository_root).resolve()
        relative = _safe_relative_path(str(output_path), "output_path")
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise GenericLegalConditionBindingError("output_path must remain under repository_root") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result.manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target
