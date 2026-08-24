"""Governed binding for personal / underwriting-specific waiting-period mechanics."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from insurance_intelligence.benefits.personal_underwriting_waiting_period import (
    PersonalUnderwritingWaitingPeriodMechanic,
)
from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodDurationUnit,
    WaitingPeriodStartBasis,
)


class PersonalUnderwritingWaitingPeriodBindingError(ValueError):
    pass


@dataclass(frozen=True)
class PersonalUnderwritingWaitingPeriodBindingResult:
    manifest: Mapping[str, Any]


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise PersonalUnderwritingWaitingPeriodBindingError(f"{label} must be a JSON object")
    return value


def _items(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise PersonalUnderwritingWaitingPeriodBindingError(f"{label} must be a JSON array")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonalUnderwritingWaitingPeriodBindingError(f"{label} must be non-empty text")
    return value.strip()


def _safe_path(value: object, label: str) -> str:
    raw = _text(value, label)
    path = Path(raw)
    if path.is_absolute() or ":" in raw[:3] or ".." in path.parts:
        raise PersonalUnderwritingWaitingPeriodBindingError(f"{label} must be repository-relative")
    return path.as_posix()


def _load(root: Path, relative: str, label: str) -> Mapping[str, Any]:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PersonalUnderwritingWaitingPeriodBindingError(f"{label} must remain under repository_root") from exc
    if not path.is_file():
        raise PersonalUnderwritingWaitingPeriodBindingError(f"{label} not found: {relative}")
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PersonalUnderwritingWaitingPeriodBindingError(f"{label} is not valid JSON") from exc


def _serialize(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, tuple):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return value


class PersonalUnderwritingWaitingPeriodBinding:
    def bind(self, *, spec: Mapping[str, Any], repository_root: str | Path, bound_at: str | None = None) -> PersonalUnderwritingWaitingPeriodBindingResult:
        root = Path(repository_root).resolve()
        if spec.get("schema_version") != "1.0":
            raise PersonalUnderwritingWaitingPeriodBindingError("schema_version must be 1.0")
        if spec.get("binding_type") != "personal_underwriting_waiting_period_binding_v1":
            raise PersonalUnderwritingWaitingPeriodBindingError("unsupported binding_type")
        if spec.get("reviewed_by_human") is not True:
            raise PersonalUnderwritingWaitingPeriodBindingError("reviewed_by_human must be true")

        bundle_path = _safe_path(spec.get("generic_source_bundle_path"), "generic_source_bundle_path")
        bundle = _load(root, bundle_path, "generic_source_bundle")
        if bundle.get("registration_type") != "generic_source_registration_bundle_v1":
            raise PersonalUnderwritingWaitingPeriodBindingError("generic source bundle is not review-ready")
        context = _mapping(bundle.get("product_context"), "generic_source_bundle.product_context")
        if context.get("source_scope") != "reusable_generic":
            raise PersonalUnderwritingWaitingPeriodBindingError("source_scope must be reusable_generic")

        sources = {
            _text(src.get("document_id"), "source.document_id"): src
            for src in (_mapping(raw, "source") for raw in _items(bundle.get("sources"), "sources"))
        }
        selection = _mapping(spec.get("evidence_selection"), "evidence_selection")
        document_id = _text(selection.get("document_id"), "evidence_selection.document_id")
        candidate_id = _text(selection.get("candidate_id"), "evidence_selection.candidate_id")
        expected_hash = _text(selection.get("candidate_text_sha256"), "evidence_selection.candidate_text_sha256")
        source = sources.get(document_id)
        if source is None or source.get("authority_role") != "primary_legal":
            raise PersonalUnderwritingWaitingPeriodBindingError("primary_legal source is required")

        registration_path = _safe_path(source.get("registration_output_path"), "source.registration_output_path")
        registration = _load(root, registration_path, f"registration[{document_id}]")
        review = _mapping(registration.get("evidence_review"), "registration.evidence_review")
        candidates = {
            _text(c.get("candidate_id"), "candidate.candidate_id"): c
            for c in (_mapping(raw, "candidate") for raw in _items(review.get("candidates"), "candidates"))
        }
        candidate = candidates.get(candidate_id)
        if candidate is None:
            raise PersonalUnderwritingWaitingPeriodBindingError(f"candidate not found: {candidate_id}")
        actual_hash = _text(candidate.get("text_sha256"), "candidate.text_sha256")
        if actual_hash != expected_hash:
            raise PersonalUnderwritingWaitingPeriodBindingError("candidate text hash mismatch")

        raw_mechanic = _mapping(spec.get("mechanic"), "mechanic")
        evidence_ref = f"{document_id}:{candidate_id}:{actual_hash}"
        try:
            duration_unit = WaitingPeriodDurationUnit(_text(raw_mechanic.get("maximum_duration_unit"), "maximum_duration_unit"))
            start_basis = WaitingPeriodStartBasis(_text(raw_mechanic.get("start_basis"), "start_basis"))
        except ValueError as exc:
            raise PersonalUnderwritingWaitingPeriodBindingError("unsupported waiting-period enum value") from exc
        mechanic = PersonalUnderwritingWaitingPeriodMechanic(
            maximum_duration_value=raw_mechanic.get("maximum_duration_value"),
            maximum_duration_unit=duration_unit,
            start_basis=start_basis,
            applies_to=tuple(_text(v, "mechanic.applies_to[]") for v in _items(raw_mechanic.get("applies_to"), "mechanic.applies_to")),
            evidence_reference_ids=(evidence_ref,),
            instance_resolution_dependency=_text(raw_mechanic.get("instance_resolution_dependency"), "instance_resolution_dependency"),
        )
        manifest = {
            "schema_version": "1.0",
            "binding_type": "personal_underwriting_waiting_period_binding_v1",
            "binding_status": "reviewed_personal_underwriting_waiting_period_bound_not_published",
            "binding_id": _text(spec.get("binding_id"), "binding_id"),
            "product_context": {
                "insurer_id": context.get("insurer_id"),
                "product_id": context.get("product_id"),
                "product_display_name": context.get("product_display_name"),
            },
            "generic_source_bundle_path": bundle_path,
            "mechanic": _serialize(asdict(mechanic)),
            "evidence": {
                "document_id": document_id,
                "candidate_id": candidate_id,
                "candidate_text_sha256": actual_hash,
                "source_page": candidate.get("source_page"),
            },
            "publication_status": "bound_not_published",
            "bound_at": bound_at or datetime.now(timezone.utc).isoformat(),
            "reviewed_by_human": True,
            "guardrails": [
                "The maximum duration is an upper bound, not a customer-specific scalar.",
                "Affected conditions and actual duration require policy-instance underwriting evidence.",
                "This binding does not determine eligibility, claim payment, comparison, or recommendation readiness.",
            ],
        }
        return PersonalUnderwritingWaitingPeriodBindingResult(manifest=manifest)


__all__ = [
    "PersonalUnderwritingWaitingPeriodBinding",
    "PersonalUnderwritingWaitingPeriodBindingError",
    "PersonalUnderwritingWaitingPeriodBindingResult",
]
