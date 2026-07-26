"""P2.5-G — register reviewed, reusable generic product sources.

This module deliberately sits above P2.5-F2.  It classifies a document by
approved reuse scope and source role, delegates byte hashing/text extraction to
the existing controlled registration component, and emits separate immutable
registrations.  It never derives a generic assertion from a private policy
schedule or from a brochure alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from factory_core.canonical.pilot_source_registration import (
    PilotSourceRegistration,
    PilotSourceRegistrationError,
    PilotSourceRegistrationResult,
)


class GenericSourceRegistrationError(ValueError):
    """Raised when a source bundle is unsafe for reusable knowledge."""


@dataclass(frozen=True)
class GenericSourceRegistrationBundleResult:
    bundle: Mapping[str, Any]
    registrations: tuple[PilotSourceRegistrationResult, ...]


_ALLOWED_ROLES: dict[str, frozenset[str]] = {
    "policy_wording": frozenset({"primary_legal"}),
    "product_benefit_table": frozenset({"primary_product_entitlement"}),
    "customer_information_sheet": frozenset({"corroborating_product"}),
    "prospectus": frozenset({"corroborating_legal"}),
    "brochure": frozenset({"discovery_only"}),
    "official_product_webpage_export": frozenset({"discovery_only"}),
}
_PRIVATE_OR_INSTANCE_TYPES = frozenset({
    "policy_schedule",
    "individual_policy_schedule",
    "renewal_notice",
    "endorsement",
    "claim_document",
    "medical_record",
    "group_policy_schedule",
    "group_member_certificate",
    "quote",
})


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GenericSourceRegistrationError(f"{label} must be a JSON object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GenericSourceRegistrationError(f"{label} must be a JSON array")
    return value


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenericSourceRegistrationError(f"{label} must be a non-empty string")
    return value.strip()


def _relative_path(value: object, label: str) -> str:
    raw = _nonempty(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise GenericSourceRegistrationError(f"{label} must be a safe repository-relative path")
    return path.as_posix()


class GenericSourceRegistration:
    """Creates a source-classified bundle from explicit public/generic PDFs."""

    def register_from_spec_file(
        self,
        *,
        spec_path: str | Path,
        repository_root: str | Path,
    ) -> GenericSourceRegistrationBundleResult:
        path = Path(spec_path)
        if not path.is_file():
            raise FileNotFoundError(f"Generic source registration specification was not found: {path}")
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GenericSourceRegistrationError(f"Invalid generic source registration JSON: {path}") from exc
        return self.register(spec=spec, repository_root=repository_root)

    def register(
        self,
        *,
        spec: Mapping[str, Any],
        repository_root: str | Path,
        page_text_extractor: Callable[[Path], Sequence[str]] | None = None,
        registered_at: str | None = None,
    ) -> GenericSourceRegistrationBundleResult:
        spec = _mapping(spec, "generic_source_registration_spec")
        if spec.get("schema_version") != "1.0":
            raise GenericSourceRegistrationError("generic_source_registration_spec.schema_version must be 1.0")
        if spec.get("registration_type") != "generic_source_registration_bundle_v1":
            raise GenericSourceRegistrationError(
                "generic_source_registration_spec.registration_type must be generic_source_registration_bundle_v1"
            )
        context = _mapping(spec.get("product_context"), "generic_source_registration_spec.product_context")
        if context.get("source_scope") != "reusable_generic":
            raise GenericSourceRegistrationError("product_context.source_scope must be reusable_generic")
        if context.get("reviewed_generic_source_confirmation") is not True:
            raise GenericSourceRegistrationError(
                "product_context.reviewed_generic_source_confirmation must be true"
            )
        normalized_context = {
            "insurer_id": _nonempty(context.get("insurer_id"), "product_context.insurer_id"),
            "product_id": _nonempty(context.get("product_id"), "product_context.product_id"),
            "product_display_name": _nonempty(
                context.get("product_display_name"), "product_context.product_display_name"
            ),
            "source_scope": "reusable_generic",
            "reviewed_generic_source_confirmation": True,
        }

        documents = _list(spec.get("documents"), "generic_source_registration_spec.documents")
        if not documents:
            raise GenericSourceRegistrationError("generic_source_registration_spec.documents must not be empty")

        registrations: list[PilotSourceRegistrationResult] = []
        classified_sources: list[dict[str, Any]] = []
        seen_document_ids: set[str] = set()
        has_primary = False
        registration_runner = PilotSourceRegistration()
        for index, raw_document in enumerate(documents):
            item = _mapping(raw_document, f"documents[{index}]")
            audience_scope = _nonempty(item.get("audience_scope"), f"documents[{index}].audience_scope")
            if audience_scope != "generic_public":
                raise GenericSourceRegistrationError(
                    f"documents[{index}].audience_scope must be generic_public; private or group-specific documents are blocked"
                )
            document_type = _nonempty(item.get("document_type"), f"documents[{index}].document_type")
            if document_type in _PRIVATE_OR_INSTANCE_TYPES:
                raise GenericSourceRegistrationError(
                    f"documents[{index}].document_type {document_type!r} is policy-instance/private and cannot enter reusable knowledge"
                )
            allowed_roles = _ALLOWED_ROLES.get(document_type)
            if allowed_roles is None:
                raise GenericSourceRegistrationError(
                    f"documents[{index}].document_type {document_type!r} is not approved for generic source registration"
                )
            authority_role = _nonempty(item.get("authority_role"), f"documents[{index}].authority_role")
            if authority_role not in allowed_roles:
                allowed = ", ".join(sorted(allowed_roles))
                raise GenericSourceRegistrationError(
                    f"documents[{index}].authority_role must be one of: {allowed} for {document_type}"
                )
            if authority_role.startswith("primary_"):
                has_primary = True

            document_id = _nonempty(item.get("document_id"), f"documents[{index}].document_id")
            if document_id in seen_document_ids:
                raise GenericSourceRegistrationError("document_id values must be unique within one bundle")
            seen_document_ids.add(document_id)

            registration_spec = {
                "schema_version": "1.0",
                "registration_type": "pilot_source_registration_v1",
                "document_id": document_id,
                "source_document_id": _nonempty(item.get("source_document_id"), f"documents[{index}].source_document_id"),
                "canonical_title": _nonempty(item.get("canonical_title"), f"documents[{index}].canonical_title"),
                "document_type": document_type,
                "document_path": _relative_path(item.get("document_path"), f"documents[{index}].document_path"),
                "extracted_text_output_path": _relative_path(
                    item.get("extracted_text_output_path"), f"documents[{index}].extracted_text_output_path"
                ),
                "evidence_markers": _list(item.get("evidence_markers"), f"documents[{index}].evidence_markers"),
                "source_issued_label": item.get("source_issued_label"),
            }
            try:
                result = registration_runner.register(
                    spec=registration_spec,
                    repository_root=repository_root,
                    page_text_extractor=page_text_extractor,
                    registered_at=registered_at,
                )
            except PilotSourceRegistrationError as exc:
                raise GenericSourceRegistrationError(str(exc)) from exc
            registrations.append(result)
            classified_sources.append({
                "document_id": document_id,
                "document_version_id": result.registration["document"]["document_version_id"],
                "authority_role": authority_role,
                "audience_scope": "generic_public",
                "registration_status": result.registration["registration_status"],
                "evidence_candidate_count": result.registration["evidence_review"]["candidate_count"],
                "registration_output_path": _relative_path(
                    item.get("registration_output_path"), f"documents[{index}].registration_output_path"
                ),
            })

        if not has_primary:
            raise GenericSourceRegistrationError(
                "A generic source bundle requires at least one primary_legal or primary_product_entitlement source"
            )

        now = registered_at or datetime.now(timezone.utc).isoformat()
        bundle = {
            "schema_version": "1.0",
            "registration_type": "generic_source_registration_bundle_v1",
            "registration_status": "generic_sources_registered_evidence_review_required",
            "product_context": normalized_context,
            "sources": classified_sources,
            "registered_at": now,
            "reuse_policy": {
                "allowed": "reusable_generic_source_only",
                "blocked": [
                    "policy_instance_documents",
                    "group_specific_schedules",
                    "member_certificates",
                    "quotes_tied_to_a_person_or_group",
                ],
                "brochure_usage": "discovery_only_not_sufficient_for_reusable_entitlement_assertion",
            },
            "notes": [
                "Each source remains a separately hashed immutable document version.",
                "Evidence candidates require human review before any legacy evidence binding or canonical lineage manifest.",
                "This bundle does not publish rules, modify conditional-rule artifacts, or infer a product benefit from a brochure.",
            ],
        }
        return GenericSourceRegistrationBundleResult(bundle=bundle, registrations=tuple(registrations))

    def write_outputs(
        self,
        result: GenericSourceRegistrationBundleResult,
        *,
        repository_root: str | Path,
        bundle_output_path: str | Path,
    ) -> Path:
        root = Path(repository_root)
        # Reuse strict safe path validation from this module rather than accepting arbitrary output locations.
        output_relative = _relative_path(str(bundle_output_path), "bundle_output_path")
        output_path = (root / output_relative).resolve()
        try:
            output_path.relative_to(root.resolve())
        except ValueError as exc:
            raise GenericSourceRegistrationError("bundle_output_path must remain under repository_root") from exc

        runner = PilotSourceRegistration()
        for source, registration_result in zip(result.bundle["sources"], result.registrations):
            # The extracted-text path is already carried by the nested registration spec. Use it directly.
            text_path = registration_result.registration["extracted_text"]["storage_locator"]
            runner.write_outputs(
                registration_result,
                repository_root=root,
                registration_output_path=source["registration_output_path"],
                extracted_text_output_path=text_path,
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(dict(result.bundle), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return output_path
